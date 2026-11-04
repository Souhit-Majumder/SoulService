"""SQL for the users table. Repositories only talk to the database."""
import sqlite3


def get_by_email(conn: sqlite3.Connection, email: str) -> dict | None:
    row = conn.execute(
        "SELECT * FROM users WHERE lower(email) = lower(?)", (email,)
    ).fetchone()
    return dict(row) if row else None


def get_by_id(conn: sqlite3.Connection, user_id: int) -> dict | None:
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def create_user(conn: sqlite3.Connection, name: str, email: str, password_hash: str, role: str) -> int:
    cursor = conn.execute(
        "INSERT INTO users (name, email, password_hash, role) VALUES (?, ?, ?, ?)",
        (name, email, password_hash, role),
    )
    return cursor.lastrowid
