"""SQL for food listings (plus their dietary tags and allergens)."""
import sqlite3

_SELECT = """
SELECT f.*, u.name AS caterer_name,
    (SELECT GROUP_CONCAT(dietary_info, ',') FROM listing_dietary_infos d
        WHERE d.food_id = f.food_id) AS dietary,
    (SELECT GROUP_CONCAT(allergen, ',') FROM listing_allergens a
        WHERE a.food_id = f.food_id) AS allergens,
    (SELECT COUNT(*) FROM listing_requests r
        WHERE r.food_id = f.food_id AND r.status = 'pending') AS pending_count
FROM food_listings f
JOIN users u ON u.user_id = f.caterer_id
"""

NOT_EXPIRED = "f.pickup_deadline > datetime('now', 'localtime')"


def _to_dict(row: sqlite3.Row) -> dict:
    item = dict(row)
    item["dietary"] = item["dietary"].split(",") if item["dietary"] else []
    item["allergens"] = item["allergens"].split(",") if item["allergens"] else []
    return item


def create_listing(conn: sqlite3.Connection, caterer_id: int, data: dict) -> int:
    cursor = conn.execute(
        """INSERT INTO food_listings
           (caterer_id, food_name, food_description, pickup_location,
            quantity, unit, prepared_date, pickup_deadline)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            caterer_id, data["food_name"], data["description"], data["pickup_location"],
            data["quantity"], data["unit"], data["prepared_at"], data["pickup_deadline"],
        ),
    )
    food_id = cursor.lastrowid
    conn.executemany(
        "INSERT INTO listing_dietary_infos (food_id, dietary_info) VALUES (?, ?)",
        [(food_id, tag) for tag in data["dietary"]],
    )
    conn.executemany(
        "INSERT INTO listing_allergens (food_id, allergen) VALUES (?, ?)",
        [(food_id, tag) for tag in data["allergens"]],
    )
    return food_id


def get_listing(conn: sqlite3.Connection, food_id: int) -> dict | None:
    row = conn.execute(_SELECT + " WHERE f.food_id = ?", (food_id,)).fetchone()
    return _to_dict(row) if row else None


def list_available(conn: sqlite3.Connection, search: str = "", dietary: str = "") -> list[dict]:
    """Listings people can still request: available and not past their deadline."""
    sql = _SELECT + f" WHERE f.status = 'available' AND {NOT_EXPIRED}"
    params: list = []
    if search:
        like = f"%{search}%"
        sql += " AND (f.food_name LIKE ? OR f.food_description LIKE ? OR f.pickup_location LIKE ?)"
        params += [like, like, like]
    if dietary:
        sql += (" AND EXISTS (SELECT 1 FROM listing_dietary_infos d "
                "WHERE d.food_id = f.food_id AND d.dietary_info = ?)")
        params.append(dietary)
    sql += " ORDER BY f.pickup_deadline ASC"
    return [_to_dict(r) for r in conn.execute(sql, params).fetchall()]


def list_by_caterer(conn: sqlite3.Connection, caterer_id: int) -> list[dict]:
    rows = conn.execute(
        _SELECT + " WHERE f.caterer_id = ? ORDER BY f.created_at DESC, f.food_id DESC",
        (caterer_id,),
    ).fetchall()
    return [_to_dict(r) for r in rows]


def set_status(conn: sqlite3.Connection, food_id: int, status: str) -> None:
    conn.execute("UPDATE food_listings SET status = ? WHERE food_id = ?", (status, food_id))


def count_listings(conn: sqlite3.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0]


def public_stats(conn: sqlite3.Connection) -> dict:
    """Numbers shown on the home page."""
    available = conn.execute(
        f"SELECT COUNT(*) AS n, COALESCE(SUM(quantity), 0) AS q FROM food_listings f "
        f"WHERE f.status = 'available' AND {NOT_EXPIRED}"
    ).fetchone()
    shared = conn.execute(
        "SELECT COALESCE(SUM(quantity), 0) FROM food_listings WHERE status = 'picked_up'"
    ).fetchone()[0]
    caterers = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'caterer'").fetchone()[0]
    recipients = conn.execute("SELECT COUNT(*) FROM users WHERE role = 'recipient'").fetchone()[0]
    return {
        "available_listings": available["n"],
        "available_portions": available["q"],
        "portions_shared": shared,
        "caterers": caterers,
        "recipients": recipients,
    }
