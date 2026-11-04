import sqlite3

from app.config import BASE_DIR, DATABASE_PATH


def initialize_database() -> None:
    schema_path = BASE_DIR / "app" / "database" / "schema.sql"
    schema = schema_path.read_text(encoding="utf-8")

    connection = sqlite3.connect(DATABASE_PATH)

    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(schema)
        # Upgrade existing local databases without erasing food or requests.
        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "contact_phone" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN contact_phone TEXT NOT NULL DEFAULT ''")
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully.")
