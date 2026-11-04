"""SQL for listing_requests (an NGO asking for a food listing)."""
import sqlite3

_SELECT = """
SELECT r.request_id, r.food_id, r.recipient_id, r.status, r.created_at,
       f.food_name, f.pickup_location, f.pickup_deadline, f.quantity, f.unit,
       f.caterer_id, f.status AS food_status,
       rec.name AS recipient_name, c.name AS caterer_name,
       c.contact_phone AS caterer_phone
FROM listing_requests r
JOIN food_listings f ON f.food_id = r.food_id
JOIN users rec ON rec.user_id = r.recipient_id
JOIN users c ON c.user_id = f.caterer_id
"""


def create_request(conn: sqlite3.Connection, food_id: int, recipient_id: int) -> int:
    cursor = conn.execute(
        "INSERT INTO listing_requests (food_id, recipient_id) VALUES (?, ?)",
        (food_id, recipient_id),
    )
    return cursor.lastrowid


def get_request(conn: sqlite3.Connection, request_id: int) -> dict | None:
    row = conn.execute(_SELECT + " WHERE r.request_id = ?", (request_id,)).fetchone()
    return dict(row) if row else None


def list_for_recipient(conn: sqlite3.Connection, recipient_id: int) -> list[dict]:
    rows = conn.execute(
        _SELECT + " WHERE r.recipient_id = ? ORDER BY r.created_at DESC, r.request_id DESC",
        (recipient_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def list_for_caterer(conn: sqlite3.Connection, caterer_id: int) -> list[dict]:
    rows = conn.execute(
        _SELECT + " WHERE f.caterer_id = ? ORDER BY r.created_at ASC, r.request_id ASC",
        (caterer_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def active_food_ids(conn: sqlite3.Connection, recipient_id: int) -> set[int]:
    """Listings this recipient has already requested (pending or accepted)."""
    rows = conn.execute(
        "SELECT food_id FROM listing_requests "
        "WHERE recipient_id = ? AND status IN ('pending', 'accepted')",
        (recipient_id,),
    ).fetchall()
    return {r["food_id"] for r in rows}


def set_status(conn: sqlite3.Connection, request_id: int, status: str) -> None:
    conn.execute("UPDATE listing_requests SET status = ? WHERE request_id = ?", (status, request_id))


def reject_other_pending(conn: sqlite3.Connection, food_id: int, keep_request_id: int) -> None:
    conn.execute(
        "UPDATE listing_requests SET status = 'rejected' "
        "WHERE food_id = ? AND status = 'pending' AND request_id != ?",
        (food_id, keep_request_id),
    )


def reject_all_pending(conn: sqlite3.Connection, food_id: int) -> None:
    conn.execute(
        "UPDATE listing_requests SET status = 'rejected' WHERE food_id = ? AND status = 'pending'",
        (food_id,),
    )
