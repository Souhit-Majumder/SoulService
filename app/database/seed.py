"""Demo data: four accounts and a few food listings, so the app is never empty.

Run `python -m app.database.seed --reset` to wipe the database and start fresh
(handy right before a demo, because pickup deadlines are relative to "now").
"""
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
    password_hash = hash_password(DEMO_PASSWORD)
    for name, email, role in DEMO_USERS:
        if not users.get_by_email(conn, email):
            users.create_user(conn, name, email, password_hash, role)
    conn.commit()

    if listings.count_listings(conn) > 0:
        return

    green = users.get_by_email(conn, "caterer@soulservice.test")["user_id"]
    udupi = users.get_by_email(conn, "caterer2@soulservice.test")["user_id"]
    fmt = "%Y-%m-%d %H:%M:%S"
    samples = [
        (green, _listing(
            1, 5, food_name="Vegetable pulao",
            description="Fragrant pulao with carrots, peas and beans, left over from a corporate lunch.",
            pickup_location="MIT Campus, Manipal", quantity=40, unit="portions",
            dietary=["vegetarian"], allergens=["milk"])),
        (green, _listing(
            2, 4, food_name="Chapati and dal",
            description="Soft chapatis with yellow dal tadka, packed in boxes.",
            pickup_location="Tiger Circle, Manipal", quantity=25, unit="packets",
            dietary=["vegetarian", "jain"], allergens=["gluten"])),
        (udupi, _listing(
            1, 6, food_name="Idli and sambar",
            description="Steamed idlis with coconut chutney and sambar from a wedding breakfast.",
            pickup_location="Car Street, Udupi", quantity=60, unit="portions",
            dietary=["vegan", "vegetarian"], allergens=[])),
        (udupi, _listing(
            0.5, 3, food_name="Fresh fruit cups",
            description="Mixed seasonal fruit in sealed cups, kept chilled.",
            pickup_location="Udupi City Bus Stand", quantity=30, unit="pieces",
            dietary=["vegan", "vegetarian", "gluten-free"], allergens=[])),
    ]
    for caterer_id, data in samples:
        data = {**data,
                "prepared_at": data["prepared_at"].strftime(fmt),
                "pickup_deadline": data["pickup_deadline"].strftime(fmt)}
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
