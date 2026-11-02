"""Deterministic DEMO fixtures. No customer names or balances are real FINEC data."""
import random
from .database import init_schema, transaction, one
from .security import generate_password, stamp
from .services import post_journal, audit, request_loan, create_operation, decide_loan

BRANCHES = [
    (1,"Akwa","Douala","AKW"), (2,"Bonabéri","Douala","BON"),
    (3,"Yaoundé – Mendong","Yaoundé","YDE"), (4,"Bafia","Bafia","BAF"),
    (5,"Bépanda","Douala","BEP"), (6,"Village – Ndogpassi","Douala","VIL"),
    (7,"Dschang","Dschang","DSC")]
ACCOUNTS_GL = [
    ("1000","Cash on hand (simulation)","asset"),
    ("1300","Loans receivable (simulation)","asset"),
    ("2100","Customer deposits payable","liability"),
    ("2200","External payment clearing (simulation)","liability"),
    ("3000","Demo opening capital","equity"),
    ("4100","Loan interest income (simulation)","income")]
USERS = [
    ("admin","Administration démo","admin",1),
    ("agent","Agent de caisse","teller",1),
    ("credit","Gestionnaire de crédits","credit",1),
    ("manager","Responsable d'agence","manager",1),
    ("conformite","Responsable conformité","compliance",1),
    ("auditeur","Auditeur interne","auditor",1),
]
CUSTOMERS = [
    ("Amina NDEMO","individual",1,"LOW"),("Cédric KAMBE","individual",1,"LOW"),
    ("Atelier Mbessa SARL","business",1,"MEDIUM"),("Grâce TCHINDA","individual",2,"LOW"),
    ("Coopérative Horizon","business",3,"MEDIUM"),("Boris MENDO","individual",3,"LOW"),
    ("Élise NJOU","individual",4,"LOW"),("Nadia FOMBA","individual",5,"HIGH"),
    ("Marché Soleil SARL","business",6,"MEDIUM"),("Patrick TALA","individual",7,"LOW"),
    ("Nour BESSALA","individual",1,"LOW"),("Inès NZE","individual",3,"LOW"),
    ("Union des Cultivateurs","business",7,"MEDIUM"),("Amadou NKOA","individual",2,"LOW"),
    ("Reine MOUTÉ","individual",5,"LOW"),("Luc BIKOI","individual",4,"LOW")]


def seed(force=False):
    init_schema()
    with transaction() as db:
        if one(db, "SELECT id FROM users LIMIT 1"):
            return False
        for branch in BRANCHES:
            db.execute("INSERT INTO branches(id,name,city,code) VALUES(?,?,?,?)", branch)
        for entry in ACCOUNTS_GL:
            db.execute("INSERT INTO ledger_accounts(code,label,category) VALUES(?,?,?)", entry)
        for username, full_name, role, branch_id in USERS:
            salt, digest = generate_password("Demo2026!")
            db.execute("INSERT INTO users(username,full_name,role,branch_id,salt,password_hash) VALUES(?,?,?,?,?,?)",
                       (username, full_name, role, branch_id, salt, digest))
        db.execute("INSERT INTO parameters VALUES ('approval_threshold_xaf','1000000')")
        db.execute("INSERT INTO parameters VALUES ('alert_threshold_xaf','2000000')")
        db.execute("INSERT INTO parameters VALUES ('demo_mode','true')")
        post_journal(db, "Synthetic demo opening capital", 1,
                     [("1000", None, 300_000_000, 0), ("3000", None, 0, 300_000_000)])
        rng = random.Random(108)
        for i, (name, kind, branch_id, risk) in enumerate(CUSTOMERS, start=1):
            status = "pending" if i in (8, 14) else "verified"
            db.execute("""INSERT INTO customers(customer_no,full_name,phone,email,national_id,kind,
                branch_id,kyc_status,risk_level,occupation,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (f"FC-{i:06d}", name, f"+237 6{rng.randrange(50000000,99999999)}", "", f"DEMO-ID-{i:06d}",
                 kind, branch_id, status, risk, "Synthetic demo profile", stamp()))
            types = ["current"] if kind == "business" else ["savings"]
            if i in (1, 4, 6, 11):
                types.append("daily")
            if i in (2, 10):
                types.append("blocked")
            for j, product in enumerate(types):
                db.execute("""INSERT INTO accounts(account_no,customer_id,branch_id,product,status,balance,created_at)
                    VALUES(?,?,?,?,?,?,?)""",
                    (f"237{branch_id:02d}{i:05d}{j+1:02d}", i, branch_id, product, "active", 0, stamp()))
                acc = db.execute("SELECT last_insert_rowid()").fetchone()[0]
                opening = rng.randrange(150_000, 4_500_000, 1000)
                if i in (1, 2):
                    opening = max(opening, 2_500_000)
                post_journal(db, "Synthetic initial client funds", 1,
                             [("1000", None, opening, 0), ("2100", acc, 0, opening)])
        # Model pending workflow: only fictional high-value transfer request.
        acc1 = one(db,"SELECT id FROM accounts WHERE customer_id=1 AND product='savings'")["id"]
        acc2 = one(db,"SELECT id FROM accounts WHERE customer_id=2 AND product='savings'")["id"]
        create_operation(db,2,kind="transfer",amount=1_000_000,
                         source_account_id=acc1,destination_account_id=acc2, note="Synthetic pending maker-checker example")
        acc3 = one(db,"SELECT id FROM accounts WHERE customer_id=3")["id"]
        request_loan(db,3,3,acc3,"commercial",3_500_000,12.0,18)
        acc5 = one(db,"SELECT id FROM accounts WHERE customer_id=5")["id"]
        request_loan(db,3,5,acc5,"agriculture",1_400_000,10.5,12)
        # An already-approved synthetic credit demonstrates a live loan portfolio.
        sample_loan = request_loan(db,3,2,acc2,"school",600_000,0.0,12)
        decide_loan(db,sample_loan["id"],4,"approve")
        # A large pending transfer creates a visible synthetic compliance alert.
        create_operation(db,2,kind="transfer",amount=2_100_000,
                         source_account_id=acc2,destination_account_id=acc1,
                         note="Synthetic large transfer for compliance review")
        # Posted demo transactions for a living dashboard.
        create_operation(db,2,kind="deposit",amount=250_000,destination_account_id=acc2,note="Synthetic branch deposit")
        create_operation(db,2,kind="collection",amount=50_000,destination_account_id=acc1,channel="daily_collection")
        create_operation(db,2,kind="transfer",amount=75_000,source_account_id=acc1,destination_account_id=acc2)
        audit(db,1,"database.seeded","system",1,{"synthetic_only":True,"version":"1.0"})
    return True
