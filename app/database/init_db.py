import sqlite3

from app.config import BASE_DIR, DATABASE_PATH


def initialize_database() -> None:
    schema_path = BASE_DIR / "app" / "database" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
