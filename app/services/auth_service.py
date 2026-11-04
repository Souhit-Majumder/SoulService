"""Password hashing and login checks."""
import hashlib
import hmac
import re
import secrets
import sqlite3

from app.repositories import user_respository as users
from app.services.errors import ServiceError

ITERATIONS = 200_000

ROLE_LABELS = {"caterer": "Caterer", "recipient": "NGO", "admin": "Admin"}
REGISTRATION_ROLES = {"caterer": "caterer", "ngo": "recipient"}
EMAIL_PATTERN = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")


def hash_password(password: str) -> str:
    """Store passwords as salt + PBKDF2 hash, never as plain text."""
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


def authenticate(conn: sqlite3.Connection, email: str, password: str) -> dict | None:
    """Return the user if email + password are right, otherwise None."""
    user = users.get_by_email(conn, email.strip())
    if user and verify_password(password, user["password_hash"]):
        return user
    # Hash anyway so a wrong email takes about as long as a wrong password.
    if not user:
        hash_password(password)
    return None


def register(conn: sqlite3.Connection, kind: str, name: str, email: str,
             password: str, confirm_password: str) -> int:
    """Create a caterer or NGO account after validating the public form."""
    role = REGISTRATION_ROLES.get(kind)
    if role is None:
        raise ServiceError("Choose a caterer or NGO account.")

    name = name.strip()
    email = email.strip().lower()
    if len(name) < 2 or len(name) > 100:
        raise ServiceError("Enter an organization name between 2 and 100 characters.")
    if len(email) > 254 or not EMAIL_PATTERN.fullmatch(email):
        raise ServiceError("Enter a valid email address.")
    if len(password) < 12 or len(password) > 128:
        raise ServiceError("Use a password between 12 and 128 characters.")
    if password != confirm_password:
        raise ServiceError("The passwords do not match.")
    if users.get_by_email(conn, email):
        raise ServiceError("An account with that email already exists. Log in instead.", status_code=409)

    try:
        user_id = users.create_user(conn, name, email, hash_password(password), role)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise ServiceError("An account with that email already exists. Log in instead.", status_code=409)
    return user_id
