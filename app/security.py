"""Demo authentication and role mapping. Requires replacement before production."""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException
from .database import one, transaction

ROLE_PERMISSIONS = {
    "admin": {"customers.write", "accounts.write", "operations.write", "operations.approve", "loans.write", "loans.approve", "kyc.write", "alerts.write", "settings.write"},
    "teller": {"customers.write", "accounts.write", "operations.write"},
    "credit": {"customers.write", "loans.write"},
    "manager": {"operations.approve", "loans.approve"},
    "compliance": {"kyc.write", "alerts.write", "accounts.write"},
    "auditor": set(),
}


def stamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def password_hash(password, salt):
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), 200_000).hex()


def generate_password(password):
    salt = secrets.token_hex(16)
    return salt, password_hash(password, salt)


def login(username, password):
    with transaction() as db:
        user = one(db, "SELECT * FROM users WHERE username=?", (username,))
        if not user or not hmac.compare_digest(password_hash(password, user["salt"]), user["password_hash"]):
            raise HTTPException(401, "Invalid credentials")
        token = secrets.token_urlsafe(36)
        token_digest = hashlib.sha256(token.encode()).hexdigest()
        expires = (datetime.now(timezone.utc) + timedelta(hours=8)).isoformat(timespec="seconds")
        db.execute("INSERT INTO sessions VALUES (?,?,?)", (token_digest, user["id"], expires))
        db.execute("DELETE FROM sessions WHERE expires_at < ?", (stamp(),))
        return token


def authenticate(token):
    if not token:
        raise HTTPException(401, "Authentication required")
    with transaction() as db:
        user = one(db, """SELECT u.id,u.username,u.full_name,u.role,u.branch_id FROM users u
            JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?""",
            (hashlib.sha256(token.encode()).hexdigest(), stamp()))
    if not user:
        raise HTTPException(401, "Session expired. Log in again.")
    return user


def require(user, permission):
    if permission not in ROLE_PERMISSIONS[user["role"]]:
        raise HTTPException(403, "Insufficient permissions for this action")


def logout(token):
    with transaction() as db:
        db.execute("DELETE FROM sessions WHERE token_hash=?", (hashlib.sha256(token.encode()).hexdigest(),))
