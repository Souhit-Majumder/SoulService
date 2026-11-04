"""Keep four demo accounts and usable sample listings available at startup."""
import sqlite3
import sys
from datetime import datetime, timedelta

from app.config import DATABASE_PATH, DEMO_PASSWORD
from app.database.connection import get_connection
from app.database.init_db import initialize_database
from app.repositories import listing_respository as listings
from app.repositories import user_respository as users
from app.services.auth_service import hash_password

DEMO_USERS = [
    ("Green Leaf Catering", "caterer@soulservice.test", "caterer"),
    ("Udupi Spice Kitchen", "caterer2@soulservice.test", "caterer"),
    ("Hope Foundation", "ngo@soulservice.test", "recipient"),
    ("Annapurna Trust", "ngo2@soulservice.test", "recipient"),
]


def _listing(hours_ago: float, hours_left: float, **fields) -> dict:
    now = datetime.now().replace(microsecond=0)
    return {
        "prepared_at": now - timedelta(hours=hours_ago),
        "pickup_deadline": now + timedelta(hours=hours_left),
        "dietary": [], "allergens": [], **fields,
    }


def seed_demo_data(conn: sqlite3.Connection) -> None:
    password_hash = None
    for name, email, role in DEMO_USERS:
        if not users.get_by_email(conn, email):
            if password_hash is None:
                password_hash = hash_password(DEMO_PASSWORD)
            users.create_user(conn, name, email, password_hash, role)

    green = users.get_by_email(conn, "caterer@soulservice.test")["user_id"]
    udupi = users.get_by_email(conn, "caterer2@soulservice.test")["user_id"]
    fmt = "%Y-%m-%d %H:%M:%S"
    samples = [
        ("vegetable-pulao", green, _listing(
            1, 5, food_name="Vegetable pulao",
            description="Fragrant pulao with carrots, peas and beans, left over from a corporate lunch.",
            pickup_location="MIT Campus, Manipal", quantity=40, unit="portions",
            dietary=["vegetarian"], allergens=["milk"])),
        ("chapati-and-dal", green, _listing(
            2, 4, food_name="Chapati and dal",
            description="Soft chapatis with yellow dal tadka, packed in boxes.",
            pickup_location="Tiger Circle, Manipal", quantity=25, unit="packets",
            dietary=["vegetarian", "jain"], allergens=["gluten"])),
        ("idli-and-sambar", udupi, _listing(
            1, 6, food_name="Idli and sambar",
            description="Steamed idlis with coconut chutney and sambar from a wedding breakfast.",
            pickup_location="Car Street, Udupi", quantity=60, unit="portions",
            dietary=["vegan", "vegetarian"], allergens=[])),
        ("fresh-fruit-cups", udupi, _listing(
            0.5, 3, food_name="Fresh fruit cups",
            description="Mixed seasonal fruit in sealed cups, kept chilled.",
            pickup_location="Udupi City Bus Stand", quantity=30, unit="pieces",
            dietary=["vegan", "vegetarian", "gluten-free"], allergens=[])),
    ]
    now = datetime.now().replace(microsecond=0).strftime(fmt)
    for key, caterer_id, data in samples:
        data = {**data,
                "prepared_at": data["prepared_at"].strftime(fmt),
                "pickup_deadline": data["pickup_deadline"].strftime(fmt),
                "demo_key": key}

        # Recognize samples created before demo_key was introduced. Matching all
        # identifying fields avoids tagging unrelated food from a demo account.
        conn.execute(
            """UPDATE food_listings SET demo_key = ?
               WHERE demo_key IS NULL AND caterer_id = ? AND food_name = ?
                 AND food_description = ? AND pickup_location = ?
                 AND quantity = ? AND unit = ?""",
            (key, caterer_id, data["food_name"], data["description"],
             data["pickup_location"], data["quantity"], data["unit"]),
        )
        active = conn.execute(
            """SELECT 1 FROM food_listings
               WHERE demo_key = ? AND status = 'available' AND pickup_deadline > ?
               LIMIT 1""", (key, now),
        ).fetchone()
        if active:
            continue

        # Reuse an expired, unrequested sample so routine restarts do not grow
        # the database. A sample with requests keeps its original history.
        reusable = conn.execute(
            """SELECT f.food_id FROM food_listings f
               WHERE f.demo_key = ? AND f.status = 'available'
                 AND NOT EXISTS (SELECT 1 FROM listing_requests r WHERE r.food_id = f.food_id)
               ORDER BY f.food_id DESC LIMIT 1""", (key,),
        ).fetchone()
        if reusable:
            conn.execute(
                """UPDATE food_listings SET prepared_date = ?, pickup_deadline = ?
                   WHERE food_id = ?""",
                (data["prepared_at"], data["pickup_deadline"], reusable["food_id"]),
            )
        else:
            listings.create_listing(conn, caterer_id, data)
    conn.commit()


def reset_database() -> None:
    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()
    initialize_database()
    conn = get_connection()
    try:
        seed_demo_data(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    if "--reset" in sys.argv:
        reset_database()
        print("Database reset and demo data added.")
    else:
        initialize_database()
        conn = get_connection()
        try:
            seed_demo_data(conn)
        finally:
            conn.close()
        print("Demo data added (existing data was kept).")
