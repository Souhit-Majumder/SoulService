import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# The database file. Tests set SOULSERVICE_DB to use a temporary database.
DATABASE_PATH = Path(os.environ.get("SOULSERVICE_DB", BASE_DIR / "soulservice.db"))

# Used to sign the login cookie. Change this for any real deployment.
SECRET_KEY = os.environ.get("SOULSERVICE_SECRET", "dev-only-secret-change-me")

# Password shared by the demo accounts (see app/database/seed.py).
DEMO_PASSWORD = "SoulDemo123!"
