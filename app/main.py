"""REST API for the bilingual, locally-hosted FINEC S.A. core banking simulator."""
from contextlib import asynccontextmanager
from io import StringIO
from pathlib import Path
import csv
import os
import shutil
from typing import Literal

from fastapi import Depends, FastAPI, HTTPException, Header, Query
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, ConfigDict
from .database import ROOT, DB_PATH, connection, one, rows, transaction
from .security import login, logout, authenticate, require, ROLE_PERMISSIONS, stamp
from .seed import seed, BRANCHES
from .services import (DomainError, audit, create_operation, decide_operation, request_loan,
                       decide_loan, repay_loan, verify_ledger, ref)


@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield


app = FastAPI(title="FINEC | Core Banking Experience — DEMO", version="1.0.0", lifespan=lifespan,
              description="Synthetic banking simulation. NOT regulated, production-ready or connected to real funds.")
app.mount("/assets", StaticFiles(directory=str(ROOT / "web")), name="assets")


@app.exception_handler(DomainError)
async def domain_exception(request, exc):
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=400, content={"detail": str(exc)})


def current_user(authorization: str = Header(default="")):
    return authenticate(authorization.removeprefix("Bearer ") if authorization.startswith("Bearer ") else "")


def guarded(user, scope):
    require(user, scope)


class SignIn(BaseModel):
    username: str
    password: str


class CustomerCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    email: str = Field(default="", max_length=120)
    national_id: str = Field(default="", max_length=80)
    kind: Literal["individual", "business"] = "individual"
    branch_id: int = 1
    occupation: str = Field(default="", max_length=120)
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] = "LOW"


class KYCUpdate(BaseModel):
    status: Literal["verified", "rejected", "pending"]
    risk_level: Literal["LOW", "MEDIUM", "HIGH"] | None = None


class AccountCreate(BaseModel):
    customer_id: int
    product: Literal["savings", "current", "daily", "blocked"]


class StatusUpdate(BaseModel):
    status: Literal["active", "frozen", "closed"]


class NewOperation(BaseModel):
    kind: Literal["deposit", "collection", "withdrawal", "transfer", "mobile_out"]
    amount: int = Field(gt=0, le=100_000_000)
    source_account_id: int | None = None
    destination_account_id: int | None = None
    channel: str = Field(default="branch", max_length=50)
    note: str = Field(default="", max_length=300)
    request_key: str | None = Field(default=None, max_length=90)


class Decision(BaseModel):
    decision: Literal["approve", "reject"]


class NewLoan(BaseModel):
    customer_id: int
    account_id: int
    product: Literal["commercial", "agriculture", "school", "consumption", "equipment", "health"]
    principal: int = Field(ge=1000, le=50_000_000)
    rate: float = Field(ge=0, le=40)
    term_months: int = Field(ge=1, le=120)


class Payment(BaseModel):
    amount: int = Field(gt=0)


class AlertReview(BaseModel):
    status: Literal["reviewed", "escalated", "open"]


class ParameterUpdate(BaseModel):
    value: int = Field(ge=100_000, le=100_000_000)


@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ok", "mode": "SYNTHETIC DEMO", "version": "1.0.0"}


@app.post("/api/auth/login")
def sign_in(payload: SignIn):
    token = login(payload.username, payload.password)
    return {"token": token}


@app.post("/api/auth/logout")
def sign_out(user=Depends(current_user), authorization: str = Header(default="")):
    logout(authorization.removeprefix("Bearer "))
    return {"ok": True}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {**user, "permissions": sorted(ROLE_PERMISSIONS[user["role"]])}


@app.get("/api/branches")
def branches(user=Depends(current_user)):
    with connection() as db:
        return rows(db, """SELECT b.*, COUNT(DISTINCT c.id) AS customers, COUNT(DISTINCT a.id) AS accounts
            FROM branches b LEFT JOIN customers c ON c.branch_id=b.id
            LEFT JOIN accounts a ON a.branch_id=b.id GROUP BY b.id ORDER BY b.id""")


@app.get("/api/customers")
def customers(search: str = "", user=Depends(current_user)):
    with connection() as db:
        return rows(db, """SELECT c.*,b.name AS branch_name, COUNT(a.id) AS account_count
            FROM customers c JOIN branches b ON b.id=c.branch_id LEFT JOIN accounts a ON a.customer_id=c.id
            WHERE c.full_name LIKE ? OR c.customer_no LIKE ? OR c.phone LIKE ?
            GROUP BY c.id ORDER BY c.id DESC""", tuple([f"%{search[:70]}%"] * 3))


@app.post("/api/customers", status_code=201)
def add_customer(payload: CustomerCreate, user=Depends(current_user)):
    guarded(user, "customers.write")
    with transaction() as db:
        if not one(db, "SELECT id FROM branches WHERE id=?", (payload.branch_id,)):
            raise DomainError("Unknown branch")
        customer_no = ref("FC")
        db.execute("""INSERT INTO customers(customer_no,full_name,phone,email,national_id,kind,branch_id,
            risk_level,occupation,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)""",
            (customer_no, payload.full_name.strip(), payload.phone, payload.email, payload.national_id,
             payload.kind, payload.branch_id, payload.risk_level, payload.occupation, stamp()))
        cid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        audit(db,user["id"],"customer.created","customer",cid,{"number":customer_no})
        return one(db,"SELECT * FROM customers WHERE id=?",(cid,))


@app.patch("/api/customers/{customer_id}/kyc")
def update_kyc(customer_id: int, payload: KYCUpdate, user=Depends(current_user)):
    guarded(user, "kyc.write")
    with transaction() as db:
        if not one(db,"SELECT id FROM customers WHERE id=?",(customer_id,)):
            raise DomainError("Customer not found")
        db.execute("""UPDATE customers SET kyc_status=?,risk_level=COALESCE(?,risk_level) WHERE id=?""",
                   (payload.status, payload.risk_level, customer_id))
        audit(db,user["id"],"customer.kyc_changed","customer",customer_id,payload.model_dump())
        return one(db,"SELECT * FROM customers WHERE id=?",(customer_id,))


@app.get("/api/accounts")
def accounts(search: str = "", user=Depends(current_user)):
    with connection() as db:
        return rows(db, """SELECT a.*,c.full_name AS customer_name,c.customer_no,c.kyc_status,b.name AS branch_name
            FROM accounts a JOIN customers c ON c.id=a.customer_id JOIN branches b ON b.id=a.branch_id
            WHERE a.account_no LIKE ? OR c.full_name LIKE ? ORDER BY a.id DESC""",
            (f"%{search[:70]}%", f"%{search[:70]}%"))


@app.post("/api/accounts", status_code=201)
def add_account(payload: AccountCreate, user=Depends(current_user)):
    guarded(user, "accounts.write")
    with transaction() as db:
        customer = one(db,"SELECT * FROM customers WHERE id=?",(payload.customer_id,))
        if not customer:
            raise DomainError("Customer not found")
        if customer["kyc_status"] != "verified":
            raise DomainError("Verify KYC before opening an account")
        number = "237" + str(customer["branch_id"]).zfill(2) + str(uuid_part()).zfill(9)
        db.execute("""INSERT INTO accounts(account_no,customer_id,branch_id,product,status,created_at)
            VALUES(?,?,?,?,?,?)""",(number,payload.customer_id,customer["branch_id"],payload.product,"active",stamp()))
        aid = db.execute("SELECT last_insert_rowid()").fetchone()[0]
        audit(db,user["id"],"account.created","account",aid,{"number":number,"product":payload.product})
        return one(db,"SELECT * FROM accounts WHERE id=?",(aid,))


def uuid_part():
    import secrets
    return secrets.randbelow(900_000_000)+100_000_000


@app.patch("/api/accounts/{account_id}/status")
def account_status(account_id: int, payload: StatusUpdate, user=Depends(current_user)):
    guarded(user,"accounts.write")
    with transaction() as db:
        account = one(db,"SELECT * FROM accounts WHERE id=?",(account_id,))
        if not account:
            raise DomainError("Account not found")
        if payload.status == "closed" and account["balance"] != 0:
            raise DomainError("Cannot close an account with remaining funds")
        db.execute("UPDATE accounts SET status=? WHERE id=?",(payload.status, account_id))
        audit(db,user["id"],"account.status_changed","account",account_id,payload.model_dump())
        return one(db,"SELECT * FROM accounts WHERE id=?",(account_id,))


@app.get("/api/operations")
def operations(status: str = "", user=Depends(current_user)):
    with connection() as db:
        return rows(db,"""SELECT o.*,sa.account_no AS source_no,da.account_no AS destination_no,
           u.full_name AS creator_name FROM operations o
           LEFT JOIN accounts sa ON sa.id=o.source_account_id
           LEFT JOIN accounts da ON da.id=o.destination_account_id
           LEFT JOIN users u ON u.id=o.created_by
           WHERE (?='' OR o.status=?) ORDER BY o.id DESC LIMIT 300""",(status,status))


@app.post("/api/operations", status_code=201)
def new_operation(payload: NewOperation, user=Depends(current_user)):
    guarded(user,"operations.write")
    with transaction() as db:
        return create_operation(db,user["id"],**payload.model_dump())


@app.post("/api/operations/{operation_id}/decision")
def operation_decision(operation_id: int, payload: Decision, user=Depends(current_user)):
    guarded(user,"operations.approve")
    with transaction() as db:
        return decide_operation(db,operation_id,user["id"],payload.decision)


@app.get("/api/loans")
def loans(user=Depends(current_user)):
    with connection() as db:
        return rows(db,"""SELECT l.*,c.full_name AS customer_name,a.account_no FROM loans l
          JOIN customers c ON c.id=l.customer_id JOIN accounts a ON a.id=l.account_id
          ORDER BY l.id DESC""")


@app.post("/api/loans", status_code=201)
def new_loan(payload: NewLoan, user=Depends(current_user)):
    guarded(user,"loans.write")
    with transaction() as db:
        return request_loan(db,user["id"],payload.customer_id,payload.account_id,
                            payload.product,payload.principal,payload.rate,payload.term_months)


@app.post("/api/loans/{loan_id}/decision")
def loan_decision(loan_id: int, payload: Decision, user=Depends(current_user)):
    guarded(user,"loans.approve")
    with transaction() as db:
        return decide_loan(db,loan_id,user["id"],payload.decision)


@app.post("/api/loans/{loan_id}/repay")
def loan_repay(loan_id: int, payload: Payment, user=Depends(current_user)):
    guarded(user,"operations.write")
    with transaction() as db:
        return repay_loan(db,loan_id,user["id"],payload.amount)


@app.get("/api/alerts")
def get_alerts(user=Depends(current_user)):
    with connection() as db:
        return rows(db,"""SELECT al.*,c.full_name AS customer_name,o.reference AS operation_reference
            FROM alerts al LEFT JOIN customers c ON c.id=al.customer_id
            LEFT JOIN operations o ON o.id=al.operation_id ORDER BY al.id DESC""")


@app.patch("/api/alerts/{alert_id}")
def review_alert(alert_id: int, payload: AlertReview, user=Depends(current_user)):
    guarded(user,"alerts.write")
    with transaction() as db:
        if not one(db,"SELECT id FROM alerts WHERE id=?",(alert_id,)):
            raise DomainError("Alert not found")
        db.execute("UPDATE alerts SET status=?,handled_by=? WHERE id=?",(payload.status,user["id"],alert_id))
        audit(db,user["id"],"alert.updated","alert",alert_id,payload.model_dump())
        return one(db,"SELECT * FROM alerts WHERE id=?",(alert_id,))


@app.get("/api/audit")
def audit_events(limit: int=Query(default=100,ge=1,le=500),user=Depends(current_user)):
    with connection() as db:
        return rows(db,"""SELECT e.*,u.username AS actor FROM audit_log e LEFT JOIN users u ON u.id=e.actor_id
           ORDER BY e.id DESC LIMIT ?""",(limit,))


@app.get("/api/reports/ledger")
def general_ledger(user=Depends(current_user)):
    with connection() as db:
        return rows(db,"""SELECT la.code,la.label,la.category,
            COALESCE(SUM(jl.debit),0) AS debit,COALESCE(SUM(jl.credit),0) AS credit
            FROM ledger_accounts la LEFT JOIN journal_lines jl ON la.code=jl.code
            GROUP BY la.code ORDER BY la.code""")


@app.get("/api/reports/check")
def consistency_check(user=Depends(current_user)):
    with connection() as db:
        return verify_ledger(db)


@app.get("/api/reports/dashboard")
def dashboard(user=Depends(current_user)):
    with connection() as db:
        scalar = lambda sql: db.execute(sql).fetchone()[0]
        total_deposits = scalar("SELECT COALESCE(SUM(balance),0) FROM accounts")
        loans = scalar("SELECT COALESCE(SUM(outstanding),0) FROM loans WHERE status='active'")
        counts = {
            "clients":scalar("SELECT COUNT(*) FROM customers"),
            "active_accounts":scalar("SELECT COUNT(*) FROM accounts WHERE status='active'"),
            "deposits":total_deposits,
            "loan_portfolio":loans,
            "branches":scalar("SELECT COUNT(*) FROM branches"),
            "transactions":scalar("SELECT COUNT(*) FROM operations WHERE status='posted'"),
            "pending":scalar("SELECT COUNT(*) FROM operations WHERE status='pending'")+scalar("SELECT COUNT(*) FROM loans WHERE status='pending'"),
            "alerts":scalar("SELECT COUNT(*) FROM alerts WHERE status='open'"),
            "kyc_pending":scalar("SELECT COUNT(*) FROM customers WHERE kyc_status='pending'"),
        }
        branch_stats = rows(db,"""SELECT b.name,b.code,COUNT(DISTINCT c.id) AS customers,
              COALESCE((SELECT SUM(a.balance) FROM accounts a WHERE a.branch_id=b.id),0) AS deposits
              FROM branches b LEFT JOIN customers c ON c.branch_id=b.id GROUP BY b.id ORDER BY b.id""")
        product_stats = rows(db,"SELECT product,COUNT(*) AS count,SUM(balance) AS deposits FROM accounts GROUP BY product")
        daily = rows(db,"""SELECT substr(created_at,1,10) AS day, SUM(amount) AS amount,COUNT(*) AS count
              FROM operations WHERE status='posted' GROUP BY substr(created_at,1,10) ORDER BY day DESC LIMIT 14""")
        return {"kpis":counts,"branches":branch_stats,"products":product_stats,"activity":list(reversed(daily))}


@app.get("/api/reports/account/{account_id}")
def account_statement(account_id: int,user=Depends(current_user)):
    with connection() as db:
        if not one(db,"SELECT id FROM accounts WHERE id=?",(account_id,)):
            raise DomainError("Account not found")
        return rows(db,"""SELECT je.reference,je.description,je.created_at,jl.debit,jl.credit
            FROM journal_lines jl JOIN journal_entries je ON je.id=jl.journal_id
            WHERE jl.customer_account_id=? ORDER BY je.id DESC LIMIT 500""",(account_id,))


@app.get("/api/reports/export/{dataset}")
def export_csv(dataset: Literal["customers","accounts","operations","loans","ledger","audit"],user=Depends(current_user)):
    with connection() as db:
        sql = {
            "customers":"SELECT customer_no,full_name,kind,phone,kyc_status,risk_level,branch_id FROM customers",
            "accounts":"SELECT account_no,customer_id,product,status,balance,branch_id FROM accounts",
            "operations":"SELECT reference,kind,amount,channel,status,created_by,created_at FROM operations",
            "loans":"SELECT loan_no,customer_id,product,principal,outstanding,rate,term_months,status FROM loans",
            "ledger":"SELECT je.reference,je.created_at,jl.code,jl.customer_account_id,jl.debit,jl.credit FROM journal_lines jl JOIN journal_entries je ON je.id=jl.journal_id ORDER BY je.id",
            "audit":"SELECT id,actor_id,action,entity,entity_id,created_at,prev_hash,event_hash FROM audit_log",
        }[dataset]
        data = rows(db,sql)
    output=StringIO()
    if data:
        writer=csv.DictWriter(output, fieldnames=list(data[0]))
        writer.writeheader()
        writer.writerows(data)
    return Response(content="\ufeff"+output.getvalue(),media_type="text/csv; charset=utf-8",
                    headers={"Content-Disposition":f"attachment; filename=finec_demo_{dataset}.csv"})


@app.get("/api/settings")
def settings(user=Depends(current_user)):
    with connection() as db:
        return {x["key"]:x["value"] for x in rows(db,"SELECT * FROM parameters")}


@app.patch("/api/settings/{key}")
def update_settings(key: Literal["approval_threshold_xaf","alert_threshold_xaf"],
                    payload: ParameterUpdate,user=Depends(current_user)):
    guarded(user,"settings.write")
    # UI settings are descriptive only; operational thresholds are kept fixed intentionally
    # so they cannot silently diverge from business rules in this sample.
    raise HTTPException(501,"Threshold editing requires policy-engine integration; demo values are read-only")


@app.get("/api/catalog")
def catalog(user=Depends(current_user)):
    return {
        "accounts":[{"key":"savings","annual_rate_example":5.0},{"key":"current","annual_rate_example":None},
                    {"key":"daily","annual_rate_example":None},{"key":"blocked","annual_rate_example":None}],
        "loans":[{"key":p,"rate_example":v} for p,v in
                  [("commercial",12.0),("agriculture",10.5),("school",0.0),("consumption",14.0),
                   ("equipment",11.0),("health",9.0)]],
        "integrations":[{"name":p,"status":"sandbox_only"} for p in
                        ("Orange Money","MTN MoMo","Western Union","MoneyGram","RIA","BEAC / payment rails")],
        "disclaimer":"Examples are not contractual pricing; no external transaction can be executed."
    }
