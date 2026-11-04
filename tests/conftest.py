import os
import re
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

# Use a throwaway database for the whole test run (must be set before importing the app).
_tmp = tempfile.mkdtemp()
os.environ["SOULSERVICE_DB"] = str(Path(_tmp) / "test.db")

import pytest
from fastapi.testclient import TestClient

from app.database.seed import reset_database
from app.main import app

PASSWORD = "SoulDemo123!"
CATERER = "caterer@soulservice.test"    # Green Leaf Catering: owns seeded listings 1 and 2
CATERER2 = "caterer2@soulservice.test"  # Udupi Spice Kitchen: owns seeded listings 3 and 4
NGO = "ngo@soulservice.test"
NGO2 = "ngo2@soulservice.test"


@pytest.fixture()
def client():
    reset_database()  # every test starts from the same demo data
    with TestClient(app, follow_redirects=False) as c:
        yield c


def csrf(client, path="/login") -> str:
    page = client.get(path)
    return re.search(r'name="csrf_token" value="([^"]+)"', page.text).group(1)


def login(client, email, password=PASSWORD):
    token = csrf(client)
    return client.post("/login", data={"email": email, "password": password, "csrf_token": token})


def logout(client):
    client.post("/logout", data={"csrf_token": csrf(client, "/food")})


def post(client, url, page="/food", **data):
    """POST a form the way the browser would, including the CSRF token."""
    return client.post(url, data={"csrf_token": csrf(client, page), **data})


def request_ids(html, action):
    return [int(i) for i in re.findall(rf"/requests/(\d+)/{action}", html)]


def listing_xml(name="Test Rice", qty=10, hours_ahead=3, extra=""):
    now = datetime.now().replace(microsecond=0)
    prepared = now.isoformat()
    deadline = (now + timedelta(hours=hours_ahead)).isoformat()
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<create_listing>
  <food_name>{name}</food_name><description>Tasty &amp; fresh</description>
  <quantity>{qty}</quantity><unit>portions</unit>
  <prepared_at>{prepared}</prepared_at><pickup_deadline>{deadline}</pickup_deadline>
  <pickup_location>Manipal</pickup_location>
  <dietary_infos><dietary_info>vegetarian</dietary_info></dietary_infos>
  <allergens><allergen>peanuts</allergen></allergens>{extra}
</create_listing>"""


def api_post_listing(client, xml, token=None, content_type="application/xml"):
    token = token if token is not None else csrf(client, "/food")
    return client.post("/api/v1/listings", content=xml.encode(),
                       headers={"Content-Type": content_type, "X-CSRF-Token": token})
