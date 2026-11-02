"""SQLite persistence and transactional helpers. All monetary amounts are XAF integers."""
from contextlib import contextmanager
from pathlib import Path
import os
import sqlite3

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("FINEC_DB_PATH", ROOT / "finec_demo.sqlite3"))


@contextmanager
def connection():
    """One connection per operation, guaranteed closed after use."""
    db = sqlite3.connect(DB_PATH, timeout=15, isolation_level=None)
    try:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=15000")
        yield db
    finally:
        db.close()


@contextmanager
def transaction():
    """Serialize all ledger postings to prevent double spending and torn writes."""
    with connection() as db:
        db.execute("BEGIN IMMEDIATE")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise


def rows(db, sql, params=()):
    return [dict(x) for x in db.execute(sql, params).fetchall()]


def one(db, sql, params=()):
    result = db.execute(sql, params).fetchone()
    return dict(result) if result else None


SCHEMA = """
CREATE TABLE IF NOT EXISTS branches (
 id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, city TEXT NOT NULL, code TEXT NOT NULL UNIQUE);
CREATE TABLE IF NOT EXISTS users (
 id INTEGER PRIMARY KEY, username TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('admin','teller','credit','manager','compliance','auditor')),
 branch_id INTEGER REFERENCES branches(id), salt TEXT NOT NULL, password_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS sessions (
 token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS customers (
 id INTEGER PRIMARY KEY, customer_no TEXT NOT NULL UNIQUE, full_name TEXT NOT NULL,
 phone TEXT NOT NULL, email TEXT NOT NULL DEFAULT '', national_id TEXT NOT NULL DEFAULT '',
 kind TEXT NOT NULL CHECK(kind IN ('individual','business')), branch_id INTEGER REFERENCES branches(id),
 kyc_status TEXT NOT NULL CHECK(kyc_status IN ('pending','verified','rejected')) DEFAULT 'pending',
 risk_level TEXT NOT NULL CHECK(risk_level IN ('LOW','MEDIUM','HIGH')) DEFAULT 'LOW',
 occupation TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS accounts (
 id INTEGER PRIMARY KEY, account_no TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL REFERENCES customers(id),
 branch_id INTEGER NOT NULL REFERENCES branches(id), product TEXT NOT NULL CHECK(product IN ('savings','current','daily','blocked')),
 status TEXT NOT NULL CHECK(status IN ('active','frozen','closed')) DEFAULT 'active',
 balance INTEGER NOT NULL DEFAULT 0 CHECK(balance>=0), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS ledger_accounts (
 code TEXT PRIMARY KEY, label TEXT NOT NULL, category TEXT NOT NULL CHECK(category IN ('asset','liability','equity','income')));
CREATE TABLE IF NOT EXISTS journal_entries (
 id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, operation_id INTEGER,
 description TEXT NOT NULL, created_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS journal_lines (
 id INTEGER PRIMARY KEY, journal_id INTEGER NOT NULL REFERENCES journal_entries(id),
 code TEXT NOT NULL REFERENCES ledger_accounts(code), customer_account_id INTEGER REFERENCES accounts(id),
 debit INTEGER NOT NULL DEFAULT 0 CHECK(debit>=0), credit INTEGER NOT NULL DEFAULT 0 CHECK(credit>=0),
 CHECK ((debit>0 AND credit=0) OR (credit>0 AND debit=0)));
CREATE TABLE IF NOT EXISTS operations (
 id INTEGER PRIMARY KEY, reference TEXT NOT NULL UNIQUE, kind TEXT NOT NULL,
 source_account_id INTEGER REFERENCES accounts(id), destination_account_id INTEGER REFERENCES accounts(id),
 amount INTEGER NOT NULL CHECK(amount>0), channel TEXT NOT NULL DEFAULT 'branch',
 status TEXT NOT NULL CHECK(status IN ('pending','posted','rejected')),
 created_by INTEGER REFERENCES users(id), approved_by INTEGER REFERENCES users(id),
 created_at TEXT NOT NULL, decided_at TEXT, note TEXT NOT NULL DEFAULT '', request_key TEXT UNIQUE);
CREATE TABLE IF NOT EXISTS loans (
 id INTEGER PRIMARY KEY, loan_no TEXT NOT NULL UNIQUE, customer_id INTEGER NOT NULL REFERENCES customers(id),
 account_id INTEGER NOT NULL REFERENCES accounts(id), product TEXT NOT NULL,
 principal INTEGER NOT NULL CHECK(principal>0), outstanding INTEGER NOT NULL CHECK(outstanding>=0),
 rate REAL NOT NULL CHECK(rate>=0), term_months INTEGER NOT NULL CHECK(term_months>0),
 monthly_payment INTEGER NOT NULL, status TEXT NOT NULL CHECK(status IN ('pending','active','rejected','paid')),
 created_by INTEGER REFERENCES users(id), approved_by INTEGER REFERENCES users(id),
 created_at TEXT NOT NULL, decided_at TEXT);
CREATE TABLE IF NOT EXISTS loan_payments (
 id INTEGER PRIMARY KEY, loan_id INTEGER NOT NULL REFERENCES loans(id), principal INTEGER NOT NULL,
 interest INTEGER NOT NULL, journal_id INTEGER NOT NULL REFERENCES journal_entries(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS alerts (
 id INTEGER PRIMARY KEY, customer_id INTEGER REFERENCES customers(id), operation_id INTEGER REFERENCES operations(id),
 severity TEXT NOT NULL, reason TEXT NOT NULL, status TEXT NOT NULL CHECK(status IN ('open','reviewed','escalated')) DEFAULT 'open',
 handled_by INTEGER REFERENCES users(id), created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS audit_log (
 id INTEGER PRIMARY KEY, actor_id INTEGER REFERENCES users(id), action TEXT NOT NULL, entity TEXT NOT NULL,
 entity_id TEXT NOT NULL, payload TEXT NOT NULL, created_at TEXT NOT NULL, prev_hash TEXT NOT NULL, event_hash TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS parameters (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_operations_date ON operations(created_at);
CREATE INDEX IF NOT EXISTS ix_journal_lines_account ON journal_lines(customer_account_id);
CREATE INDEX IF NOT EXISTS ix_audit_date ON audit_log(created_at);
"""


def init_schema():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.executescript(SCHEMA)
