from contextlib import closing

import pytest

from app.database.connection import get_connection
from app.services.auth_service import verify_password
from tests.conftest import CATERER, csrf, login, logout


PASSWORD = "ExamplePass123!"


def registration_data(client, kind, **overrides):
    data = {
        "csrf_token": csrf(client, f"/register/{kind}"),
        "name": "New Community Kitchen",
        "email": "new@example.org",
        "password": PASSWORD,
        "confirm_password": PASSWORD,
    }
    data.update(overrides)
    return data


def test_role_selection_and_account_forms(client):
    selection = client.get("/register")
    assert selection.status_code == 200
    assert "/register/caterer" in selection.text and "/register/ngo" in selection.text
    assert "Caterer or food business name" in client.get("/register/caterer").text
    ngo_form = client.get("/register/ngo")
    assert "NGO name" in ngo_form.text and "Register as an NGO" in ngo_form.text
    assert client.get("/register/admin").status_code == 404


@pytest.mark.parametrize("kind,role,next_link", [
    ("caterer", "caterer", "/food/new"),
    ("ngo", "recipient", "/food"),
])
def test_registration_signs_in_and_shows_role_specific_onboarding(client, kind, role, next_link):
    response = client.post(f"/register/{kind}", data=registration_data(
        client, kind, email=" New@Example.org "))
    assert response.status_code == 303 and response.headers["location"] == "/onboarding"

    with closing(get_connection()) as conn:
        row = conn.execute("SELECT name, email, password_hash, role FROM users WHERE email = ?",
                           ("new@example.org",)).fetchone()
    assert row["name"] == "New Community Kitchen"
    assert row["role"] == role
    assert PASSWORD not in row["password_hash"] and verify_password(PASSWORD, row["password_hash"])

    welcome = client.get("/onboarding")
    assert welcome.status_code == 200 and next_link in welcome.text
    assert "New Community Kitchen" in client.get("/dashboard").text
    assert client.get("/food/new").status_code == (200 if role == "caterer" else 303)
    logout(client)
    assert login(client, "new@example.org", PASSWORD).status_code == 303
    assert "New Community Kitchen" in client.get("/dashboard").text


@pytest.mark.parametrize("overrides,message", [
    ({"name": "A"}, "organization name"),
    ({"email": "bad-email"}, "valid email"),
    ({"password": "too-short", "confirm_password": "too-short"}, "12 and 128"),
    ({"confirm_password": "DifferentPass123!"}, "do not match"),
])
def test_invalid_registration_keeps_user_on_form_without_creating_account(client, overrides, message):
    response = client.post("/register/ngo", data=registration_data(client, "ngo", **overrides))
    assert response.status_code == 422 and message in response.text
    assert f'value="{overrides.get("name", "New Community Kitchen")}"' in response.text
    assert PASSWORD not in response.text
    with closing(get_connection()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email = 'new@example.org'").fetchone()[0] == 0


def test_duplicate_email_is_rejected_case_insensitively(client):
    response = client.post("/register/ngo", data=registration_data(
        client, "ngo", email=CATERER.upper()))
    assert response.status_code == 409 and "already exists" in response.text


def test_registration_requires_csrf_and_onboarding_requires_login(client):
    assert client.get("/onboarding").status_code == 303
    response = client.post("/register/ngo", data={
        "name": "New Community Kitchen", "email": "new@example.org",
        "password": PASSWORD, "confirm_password": PASSWORD,
    })
    assert response.status_code == 303 and response.headers["location"] == "/register/ngo"
    with closing(get_connection()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE email = 'new@example.org'").fetchone()[0] == 0


def test_signed_in_users_are_sent_to_dashboard(client):
    login(client, CATERER)
    assert client.get("/register").headers["location"] == "/dashboard"
    assert client.get("/register/ngo").headers["location"] == "/dashboard"
