"""Checks on the database rules (constraints and triggers) written in schema.sql."""
import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.database import connection as db_connection
from app.database import init_db
from app.database.connection import get_connection
from app.database.seed import seed_demo_data
from app.main import app


@pytest.fixture()
def conn(client):
    c = get_connection()
    yield c
    c.close()


def _user(conn, email):
    return conn.execute("SELECT user_id FROM users WHERE email=?", (email,)).fetchone()[0]


def _request(conn, food=1, ngo="ngo@soulservice.test"):
    return conn.execute("INSERT INTO listing_requests (food_id, recipient_id) VALUES (?, ?)",
                        (food, _user(conn, ngo))).lastrowid


def _food_status(conn, food=1):
    return conn.execute("SELECT status FROM food_listings WHERE food_id=?", (food,)).fetchone()[0]


def test_demo_data_present(conn):
    assert conn.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(DISTINCT demo_key) FROM food_listings").fetchone()[0] == 4


def test_startup_seeds_and_migrates_existing_database(tmp_path, monkeypatch):
    database_path = tmp_path / "legacy.db"
    schema = (init_db.BASE_DIR / "app" / "database" / "schema.sql").read_text()
    with sqlite3.connect(database_path) as legacy:
        legacy.executescript(schema.replace("    demo_key TEXT,\n", ""))
    monkeypatch.setattr(db_connection, "DATABASE_PATH", database_path)
    monkeypatch.setattr(init_db, "DATABASE_PATH", database_path)

    for _ in range(2):
        with TestClient(app):
            with sqlite3.connect(database_path) as current:
                assert current.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 4
                assert current.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0] == 4
                assert current.execute(
                    "SELECT COUNT(DISTINCT demo_key) FROM food_listings"
                ).fetchone()[0] == 4


def test_startup_restores_missing_sample_alongside_user_listing(conn):
    conn.execute(
        """INSERT INTO food_listings
           (caterer_id, food_name, food_description, pickup_location, quantity,
            unit, prepared_date, pickup_deadline)
           VALUES (1, 'My own meal', 'User listing', 'Manipal', 5, 'portions',
                   datetime('now', 'localtime'), datetime('now', 'localtime', '+1 day'))"""
    )
    conn.execute("DELETE FROM food_listings WHERE demo_key = 'vegetable-pulao'")

    seed_demo_data(conn)
    assert conn.execute("SELECT COUNT(*) FROM food_listings WHERE demo_key IS NOT NULL").fetchone()[0] == 4
    assert conn.execute("SELECT COUNT(*) FROM food_listings WHERE food_name = 'My own meal'").fetchone()[0] == 1
    seed_demo_data(conn)
    assert conn.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0] == 5


def test_startup_recognizes_and_refreshes_legacy_samples_in_place(conn):
    conn.execute(
        """UPDATE food_listings
           SET demo_key = NULL,
               prepared_date = datetime('now', 'localtime', '-2 hours'),
               pickup_deadline = datetime('now', 'localtime', '-1 hour')
           WHERE food_id IN (1, 2, 3, 4)"""
    )
    seed_demo_data(conn)
    assert conn.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0] == 4
    assert conn.execute(
        """SELECT COUNT(*) FROM food_listings WHERE demo_key IS NOT NULL
           AND pickup_deadline > datetime('now', 'localtime')"""
    ).fetchone()[0] == 4


def test_startup_preserves_demo_listing_with_request_history(conn):
    request_id = _request(conn)
    conn.execute(
        """UPDATE food_listings
           SET prepared_date = datetime('now', 'localtime', '-2 hours'),
               pickup_deadline = datetime('now', 'localtime', '-1 hour')
           WHERE food_id = 1"""
    )
    seed_demo_data(conn)
    assert conn.execute("SELECT COUNT(*) FROM food_listings").fetchone()[0] == 5
    assert conn.execute("SELECT food_id FROM listing_requests WHERE request_id = ?", (request_id,)).fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM food_listings WHERE demo_key = 'vegetable-pulao'").fetchone()[0] == 2


def test_passwords_are_not_stored_in_plain_text(conn):
    hashes = [r[0] for r in conn.execute("SELECT password_hash FROM users")]
    assert all("SoulDemo123!" not in h and h.startswith("pbkdf2_sha256$") for h in hashes)


def test_caterer_cannot_request_food(conn):
    with pytest.raises(sqlite3.IntegrityError, match="Only recipients"):
        conn.execute("INSERT INTO listing_requests (food_id, recipient_id) VALUES (3, ?)",
                     (_user(conn, "caterer@soulservice.test"),))


def test_duplicate_active_request_blocked(conn):
    _request(conn)
    with pytest.raises(sqlite3.IntegrityError):
        _request(conn)


def test_zero_quantity_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO food_listings (caterer_id, food_name, food_description, pickup_location, quantity, unit,"
            " prepared_date, pickup_deadline) VALUES (1, 'x', 'x', 'x', 0, 'portions',"
            " '2030-01-01 10:00:00', '2030-01-01 12:00:00')")


def test_deadline_before_preparation_rejected(conn):
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO food_listings (caterer_id, food_name, food_description, pickup_location, quantity, unit,"
            " prepared_date, pickup_deadline) VALUES (1, 'x', 'x', 'x', 5, 'portions',"
            " '2030-01-01 12:00:00', '2030-01-01 10:00:00')")


def test_accept_reserves_then_pickup_marks_collected(conn):
    rid = _request(conn)
    conn.execute("UPDATE listing_requests SET status='accepted' WHERE request_id=?", (rid,))
    assert _food_status(conn) == "reserved"
    conn.execute("UPDATE listing_requests SET status='picked_up' WHERE request_id=?", (rid,))
    assert _food_status(conn) == "picked_up"


def test_cannot_pick_up_a_request_that_was_never_accepted(conn):
    rid = _request(conn)
    with pytest.raises(sqlite3.IntegrityError, match="accepted request"):
        conn.execute("UPDATE listing_requests SET status='picked_up' WHERE request_id=?", (rid,))


def test_only_one_accepted_request_per_listing(conn):
    first, second = _request(conn), _request(conn, ngo="ngo2@soulservice.test")
    conn.execute("UPDATE listing_requests SET status='accepted' WHERE request_id=?", (first,))
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute("UPDATE listing_requests SET status='accepted' WHERE request_id=?", (second,))


def test_cancelling_accepted_request_reopens_food(conn):
    rid = _request(conn)
    conn.execute("UPDATE listing_requests SET status='accepted' WHERE request_id=?", (rid,))
    conn.execute("UPDATE listing_requests SET status='cancelled' WHERE request_id=?", (rid,))
    assert _food_status(conn) == "available"
