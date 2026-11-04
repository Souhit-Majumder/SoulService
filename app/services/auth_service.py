"""Password hashing and login checks."""
import hashlib
import hmac
import secrets
import sqlite3

from app.repositories import user_respository as users

ITERATIONS = 200_000

ROLE_LABELS = {"caterer": "Caterer", "recipient": "NGO", "admin": "Admin"}


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
