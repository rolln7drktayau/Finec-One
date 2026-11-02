"""Domain services: balanced general ledger, retail banking, loans, compliance and audit.

IMPORTANT: This application is a simulated workflow, not regulatory-certified software.
"""
import hashlib
import json
import math
import uuid
from fastapi import HTTPException
from .database import one, rows
from .security import stamp


class DomainError(Exception):
    """Business-rule violation; translated to HTTP 400 by the API layer."""


def ref(prefix):
    return f"{prefix}-{uuid.uuid4().hex[:10].upper()}"


def audit(db, actor, action, entity, entity_id, payload):
    """Append chained hashes to make retrospective modification detectable (not immutable)."""
    last = one(db, "SELECT event_hash FROM audit_log ORDER BY id DESC LIMIT 1")
    previous = last["event_hash"] if last else "GENESIS"
    timestamp = stamp()
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    digest = hashlib.sha256(f"{previous}|{actor}|{action}|{entity}|{entity_id}|{serialized}|{timestamp}".encode()).hexdigest()
    db.execute("""INSERT INTO audit_log(actor_id,action,entity,entity_id,payload,created_at,prev_hash,event_hash)
        VALUES (?,?,?,?,?,?,?,?)""", (actor, action, entity, str(entity_id), serialized, timestamp, previous, digest))


def validate_audit_chain(db):
    prior = "GENESIS"
    for event in rows(db, "SELECT * FROM audit_log ORDER BY id"):
        expected = hashlib.sha256(f"{prior}|{event['actor_id']}|{event['action']}|{event['entity']}|{event['entity_id']}|{event['payload']}|{event['created_at']}".encode()).hexdigest()
        if prior != event["prev_hash"] or expected != event["event_hash"]:
            return False
        prior = expected
    return True


def post_journal(db, description, actor_id, lines, operation_id=None):
    """Atomic, balanced journal posting. Debit and credit use positive integer XAF."""
    if len(lines) < 2 or sum(x[2] for x in lines) != sum(x[3] for x in lines):
        raise DomainError("Unbalanced journal entry")
    if any(min(x[2], x[3]) < 0 or (x[2] > 0) == (x[3] > 0) for x in lines):
        raise DomainError("Invalid journal line")
    reference = ref("JE")
    db.execute("INSERT INTO journal_entries(reference,operation_id,description,created_by,created_at) VALUES(?,?,?,?,?)",
               (reference, operation_id, description, actor_id, stamp()))
    journal_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    deltas = {}
    for code, account_id, debit, credit in lines:
        if not one(db, "SELECT code FROM ledger_accounts WHERE code=?", (code,)):
            raise DomainError(f"Unknown ledger code: {code}")
        if account_id is not None and code != "2100":
            raise DomainError("Customer account lines must use deposit liability GL 2100")
        db.execute("INSERT INTO journal_lines(journal_id,code,customer_account_id,debit,credit) VALUES (?,?,?,?,?)",
                   (journal_id, code, account_id, debit, credit))
        if account_id is not None:
            deltas[account_id] = deltas.get(account_id, 0) + credit - debit
    for account_id, delta in deltas.items():
        account = one(db, "SELECT balance FROM accounts WHERE id=?", (account_id,))
        if not account or account["balance"] + delta < 0:
            raise DomainError("Insufficient available balance")
        db.execute("UPDATE accounts SET balance=balance+? WHERE id=?", (delta, account_id))
    return journal_id


def account_or_error(db, account_id, active=True):
    account = one(db, """SELECT a.*,c.full_name,c.kyc_status,c.risk_level
        FROM accounts a JOIN customers c ON c.id=a.customer_id WHERE a.id=?""", (account_id,))
    if not account:
        raise DomainError("Account not found")
    if active and account["status"] != "active":
        raise DomainError("Account is not active")
    return account


def verified(account):
    if account["kyc_status"] != "verified":
        raise DomainError("Customer KYC must be verified before this transaction")


def operation_lines(kind, amount, src_id, dst_id):
    """Use actual double entries; external/mobile destinations are only simulation ledgers."""
    if kind in ("deposit", "collection"):
        return [("1000", None, amount, 0), ("2100", dst_id, 0, amount)]
    if kind == "withdrawal":
        return [("2100", src_id, amount, 0), ("1000", None, 0, amount)]
    if kind == "transfer":
        return [("2100", src_id, amount, 0), ("2100", dst_id, 0, amount)]
    if kind == "mobile_out":
        return [("2100", src_id, amount, 0), ("2200", None, 0, amount)]
    raise DomainError("Unsupported transaction type")


def create_operation(db, actor_id, *, kind, amount, source_account_id=None,
                     destination_account_id=None, channel="branch", note="", request_key=None):
    if kind not in ("deposit", "collection", "withdrawal", "transfer", "mobile_out"):
        raise DomainError("Unsupported transaction type")
    if not isinstance(amount, int) or isinstance(amount, bool) or amount <= 0 or amount > 100_000_000:
        raise DomainError("Amount must be between 1 and 100,000,000 XAF")
    if request_key:
        existing = one(db, "SELECT * FROM operations WHERE request_key=?", (request_key,))
        if existing:
            if (existing["kind"] != kind or existing["amount"] != amount or
                existing["source_account_id"] != source_account_id or
                existing["destination_account_id"] != destination_account_id):
                raise DomainError("Idempotency key reused with different transaction")
            return existing
    src = account_or_error(db, source_account_id) if source_account_id else None
    dst = account_or_error(db, destination_account_id) if destination_account_id else None
    if kind in ("deposit", "collection") and (src or not dst):
        raise DomainError("Deposit requires destination account only")
    if kind in ("withdrawal", "mobile_out") and (not src or dst):
        raise DomainError("Withdrawal/mobile transfer requires source account only")
    if kind == "transfer" and (not src or not dst or src["id"] == dst["id"]):
        raise DomainError("Transfer requires two different accounts")
    if src:
        verified(src)
        if src["balance"] < amount:
            raise DomainError("Insufficient available balance")
    if dst:
        verified(dst)
        if dst["product"] == "blocked" and kind == "transfer":
            raise DomainError("Blocked savings product does not accept internal transfers in this demo")
    if src and src["product"] == "blocked":
        raise DomainError("Blocked savings cannot be debited")
    pending = bool(src and amount >= 1_000_000)
    operation_reference = ref("OP")
    db.execute("""INSERT INTO operations(reference,kind,source_account_id,destination_account_id,amount,
        channel,status,created_by,created_at,note,request_key) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
        (operation_reference, kind, source_account_id, destination_account_id, amount, channel,
         "pending" if pending else "posted", actor_id, stamp(), note[:300], request_key))
    operation_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    if not pending:
        post_journal(db, f"{kind} / {operation_reference}", actor_id,
                     operation_lines(kind, amount, source_account_id, destination_account_id), operation_id)
    if amount >= 2_000_000 or (src or dst)["risk_level"] == "HIGH":
        db.execute("INSERT INTO alerts(customer_id,operation_id,severity,reason,created_at) VALUES(?,?,?,?,?)",
                   ((src or dst)["customer_id"], operation_id, "HIGH" if amount >= 2_000_000 else "MEDIUM",
                    "Large amount — manual compliance review" if amount >= 2_000_000 else "High-risk customer transaction", stamp()))
    audit(db, actor_id, "operation.created", "operation", operation_id,
          {"kind": kind, "amount": amount, "status": "pending" if pending else "posted"})
    return one(db, "SELECT * FROM operations WHERE id=?", (operation_id,))


def decide_operation(db, op_id, actor_id, decision):
    op = one(db, "SELECT * FROM operations WHERE id=?", (op_id,))
    if not op or op["status"] != "pending":
        raise DomainError("Pending operation not found")
    if op["created_by"] == actor_id:
        raise DomainError("Maker-checker rule: you cannot approve your own request")
    if decision not in ("approve", "reject"):
        raise DomainError("Invalid decision")
    if decision == "approve":
        src = account_or_error(db, op["source_account_id"]) if op["source_account_id"] else None
        dst = account_or_error(db, op["destination_account_id"]) if op["destination_account_id"] else None
        if src:
            verified(src)
        if dst:
            verified(dst)
        post_journal(db, f"{op['kind']} / {op['reference']}", actor_id,
                     operation_lines(op["kind"], op["amount"], op["source_account_id"], op["destination_account_id"]), op_id)
    db.execute("UPDATE operations SET status=?,approved_by=?,decided_at=? WHERE id=?",
               ("posted" if decision == "approve" else "rejected", actor_id, stamp(), op_id))
    audit(db, actor_id, f"operation.{decision}", "operation", op_id, {"reference": op["reference"]})
    return one(db, "SELECT * FROM operations WHERE id=?", (op_id,))


def payment_amount(principal, rate, months):
    monthly_rate = rate / 1200
    if not monthly_rate:
        return math.ceil(principal / months)
    return math.ceil(principal * monthly_rate / (1 - (1 + monthly_rate) ** -months))


def request_loan(db, actor_id, customer_id, account_id, product, principal, rate, months):
    products = ("commercial", "agriculture", "school", "consumption", "equipment", "health")
    if product not in products or not isinstance(principal, int) or not 1000 <= principal <= 50_000_000:
        raise DomainError("Invalid loan product or amount")
    if not 0 <= rate <= 40 or not 1 <= months <= 120:
        raise DomainError("Invalid annual rate or term")
    account = account_or_error(db, account_id)
    verified(account)
    if account["product"] == "blocked":
        raise DomainError("Blocked savings cannot be used for a loan disbursement")
    if account["customer_id"] != customer_id:
        raise DomainError("Loan account does not belong to the customer")
    number = ref("LN")
    installment = payment_amount(principal, rate, months)
    db.execute("""INSERT INTO loans(loan_no,customer_id,account_id,product,principal,outstanding,rate,
        term_months,monthly_payment,status,created_by,created_at)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (number, customer_id, account_id, product, principal, principal, rate, months, installment,
         "pending", actor_id, stamp()))
    loan_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]
    audit(db, actor_id, "loan.requested", "loan", loan_id,
          {"principal": principal, "annual_rate": rate, "term": months})
    return one(db, "SELECT * FROM loans WHERE id=?", (loan_id,))


def decide_loan(db, loan_id, actor_id, decision):
    loan = one(db, "SELECT * FROM loans WHERE id=?", (loan_id,))
    if not loan or loan["status"] != "pending":
        raise DomainError("Pending loan not found")
    if loan["created_by"] == actor_id:
        raise DomainError("Maker-checker rule: you cannot approve your own loan")
    if decision not in ("approve", "reject"):
        raise DomainError("Invalid decision")
    if decision == "approve":
        account = account_or_error(db, loan["account_id"])
        verified(account)
        post_journal(db, "Loan disbursement " + loan["loan_no"], actor_id,
                     [("1300", None, loan["principal"], 0),
                      ("2100", loan["account_id"], 0, loan["principal"])])
    db.execute("UPDATE loans SET status=?,approved_by=?,decided_at=? WHERE id=?",
               ("active" if decision == "approve" else "rejected", actor_id, stamp(), loan_id))
    audit(db, actor_id, "loan." + decision, "loan", loan_id, {"principal": loan["principal"]})
    return one(db, "SELECT * FROM loans WHERE id=?", (loan_id,))


def repay_loan(db, loan_id, actor_id, amount):
    loan = one(db, "SELECT * FROM loans WHERE id=?", (loan_id,))
    if not loan or loan["status"] != "active":
        raise DomainError("Active loan not found")
    if not isinstance(amount, int) or amount <= 0:
        raise DomainError("Repayment amount must be positive")
    account = account_or_error(db, loan["account_id"])
    verified(account)
    # Simplified DEMO rule: one month's interest per repayment, no daily accrual.
    interest = round(loan["outstanding"] * loan["rate"] / 1200)
    if amount <= interest or amount > loan["outstanding"] + interest:
        raise DomainError(f"Repayment must exceed simulated interest and not exceed {loan['outstanding'] + interest} XAF")
    if account["balance"] < amount:
        raise DomainError("Insufficient funds for loan repayment")
    principal_paid = amount - interest
    lines = [("2100", loan["account_id"], amount, 0), ("1300", None, 0, principal_paid)]
    if interest:
        lines.append(("4100", None, 0, interest))
    journal_id = post_journal(db, "Loan repayment " + loan["loan_no"], actor_id, lines)
    outstanding = loan["outstanding"] - principal_paid
    db.execute("UPDATE loans SET outstanding=?,status=? WHERE id=?",
               (outstanding, "paid" if outstanding == 0 else "active", loan_id))
    db.execute("INSERT INTO loan_payments(loan_id,principal,interest,journal_id,created_at) VALUES(?,?,?,?,?)",
               (loan_id, principal_paid, interest, journal_id, stamp()))
    audit(db, actor_id, "loan.repaid", "loan", loan_id,
          {"amount": amount, "principal": principal_paid, "interest": interest})
    return {"principal_paid": principal_paid, "interest_paid": interest, "outstanding": outstanding}


def verify_ledger(db):
    """Detect double-entry imbalance and customer account balance mismatches."""
    entries = rows(db, """SELECT je.id,COALESCE(SUM(jl.debit),0) AS debit,COALESCE(SUM(jl.credit),0) AS credit
        FROM journal_entries je LEFT JOIN journal_lines jl ON jl.journal_id=je.id GROUP BY je.id""")
    issues = [f"Journal {e['id']} is unbalanced" for e in entries if e["debit"] != e["credit"]]
    for a in rows(db, """SELECT a.id,a.balance, COALESCE(SUM(jl.credit-jl.debit),0) AS ledger_balance
        FROM accounts a LEFT JOIN journal_lines jl ON jl.customer_account_id=a.id GROUP BY a.id"""):
        if a["balance"] != a["ledger_balance"]:
            issues.append(f"Account {a['id']} balance differs from journal")
    return {"balanced": not issues, "entries_checked": len(entries), "issues": issues,
            "audit_chain_valid": validate_audit_chain(db)}
