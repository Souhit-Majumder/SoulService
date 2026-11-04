from app.services.auth_service import hash_password, verify_password
from tests.conftest import CATERER, NGO, csrf, login, logout


def test_password_hash_roundtrip():
    stored = hash_password("secret")
    assert "secret" not in stored
    assert verify_password("secret", stored)
    assert not verify_password("wrong", stored)


def test_login_page_loads(client):
    assert client.get("/login").status_code == 200


def test_caterer_login_and_logout(client):
    response = login(client, CATERER)
    assert response.status_code == 303 and response.headers["location"] == "/dashboard"
    page = client.get("/dashboard")
    assert "Green Leaf Catering" in page.text and "Requests waiting for you" in page.text
    logout(client)
    assert client.get("/dashboard").status_code == 303  # sent back to login


def test_ngo_sees_ngo_dashboard(client):
    login(client, NGO)
    page = client.get("/dashboard")
    assert "Your requests" in page.text and "/food/new" not in page.text


def test_wrong_password_shows_error(client):
    response = login(client, CATERER, "nope")
    assert response.status_code == 401
    assert "don&#39;t match" in response.text or "don't match" in response.text
    assert client.get("/dashboard").status_code == 303  # still logged out


def test_unknown_email_gives_same_error(client):
    assert login(client, "nobody@example.com").status_code == 401


def test_dashboard_requires_login(client):
    response = client.get("/dashboard")
    assert response.status_code == 303 and response.headers["location"].startswith("/login")


def test_login_without_csrf_token_rejected(client):
    client.post("/login", data={"email": CATERER, "password": "SoulDemo123!"})
    assert client.get("/dashboard").status_code == 303


def test_open_redirect_blocked(client):
    token = csrf(client)
    response = client.post("/login", data={"email": CATERER, "password": "SoulDemo123!",
                                           "csrf_token": token, "next": "https://evil.example"})
    assert response.headers["location"] == "/dashboard"
