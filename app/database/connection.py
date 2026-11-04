import sqlite3

from collections.abc import Generator
from app.config import DATABASE_PATH


def get_connection() -> sqlite3.Connection:
    # check_same_thread=False: FastAPI may use a different worker thread for
    # the dependency and the route, so SQLite must allow that.
    connection = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 5000")
    return connection


def get_db() -> Generator[sqlite3.Connection, None, None]:
    connection = get_connection()
    try:
        yield connection
    finally:
        connection.close()
