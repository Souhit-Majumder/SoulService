"""The six functions, one at a time, and then the whole story end to end."""
from tests.conftest import (CATERER, CATERER2, NGO, NGO2, api_post_listing, listing_xml,
                            login, logout, post, request_ids)


# ---------- Function 2 & 3: post food and browse food ----------

def test_browse_is_public_and_shows_demo_food(client):
    page = client.get("/food")
    assert page.status_code == 200
    assert "Vegetable pulao" in page.text and "Idli and sambar" in page.text


def test_search_and_dietary_filter(client):
    assert "Idli" not in client.get("/food?q=pulao").text
    only_jain = client.get("/food?diet=jain").text
    assert "Chapati and dal" in only_jain and "Vegetable pulao" not in only_jain
    assert "No listings match" in client.get("/food?q=zzzz").text


def test_caterer_posts_food_via_xml_and_it_is_saved(client):
    login(client, CATERER)
    response = api_post_listing(client, listing_xml("Lemon rice"))
    assert response.status_code == 201 and "<listing_id>" in response.text
    dash = client.get("/dashboard").text                            # on the dashboard (with success message)
    assert "Lemon rice" in dash and "Food posted!" in dash
    assert "Lemon rice" in client.get("/food").text                 # and on the browse page


def test_special_characters_are_escaped_on_the_page(client):
    login(client, CATERER)
    api_post_listing(client, listing_xml("Dal &amp; &lt;script&gt;x&lt;/script&gt;"))
    page = client.get("/food").text
    assert "<script>x" not in page and "&lt;script&gt;x" in page


def test_api_requires_login(client):
    client.get("/login")
    assert api_post_listing(client, listing_xml(), token="x").status_code == 401


def test_api_rejects_ngo(client):
    login(client, NGO)
    response = api_post_listing(client, listing_xml())
    assert response.status_code == 403 and "FORBIDDEN" in response.text


def test_api_rejects_bad_csrf_token(client):
    login(client, CATERER)
    assert api_post_listing(client, listing_xml(), token="forged").status_code == 403


def test_api_rejects_wrong_content_type(client):
    login(client, CATERER)
    assert api_post_listing(client, listing_xml(), content_type="text/plain").status_code == 415


def test_api_rejects_malformed_and_schema_invalid_xml(client):
    login(client, CATERER)
    assert api_post_listing(client, "<create_listing>").status_code == 400
    assert api_post_listing(client, listing_xml(qty=0)).status_code == 422


def test_api_rejects_xxe_attack(client):
    login(client, CATERER)
    evil = ('<?xml version="1.0"?><!DOCTYPE x [<!ENTITY e SYSTEM "file:///etc/passwd">]>'
            + listing_xml().split("?>", 1)[1])
    assert api_post_listing(client, evil).status_code == 400


def test_api_business_rules(client):
    login(client, CATERER)
    r = api_post_listing(client, listing_xml(hours_ahead=-1))
    assert r.status_code == 422 and "later" in r.text
    r = api_post_listing(client, listing_xml(name="   "))
    assert r.status_code == 422 and "Food name is required" in r.text
    r = api_post_listing(client, listing_xml().replace("peanuts", "kryptonite"))
    assert r.status_code == 422 and "allergen" in r.text


def test_new_food_page_is_caterer_only(client):
    assert client.get("/food/new").status_code == 303        # not logged in
    login(client, NGO)
    assert client.get("/food/new").status_code == 303        # wrong role
    logout(client)
    login(client, CATERER)
    assert client.get("/food/new").status_code == 200


# ---------- Function 4: request food ----------

def test_ngo_requests_food_and_sees_it(client):
    login(client, NGO)
    assert post(client, "/food/1/request").status_code == 303
    browse = client.get("/food").text
    assert "Requested ✓" in browse and "Request sent!" in browse
    assert "Awaiting response" in client.get("/dashboard").text


def test_duplicate_request_gives_friendly_error(client):
    login(client, NGO)
    post(client, "/food/1/request")
    post(client, "/food/1/request")
    assert "already requested" in client.get("/food").text


def test_caterer_cannot_request(client):
    login(client, CATERER)
    post(client, "/food/3/request")
    assert "Only NGO accounts" in client.get("/food").text


def test_form_post_without_csrf_token_is_ignored(client):
    login(client, NGO)
    client.post("/food/1/request", data={})
    assert "No requests yet" in client.get("/dashboard").text


# ---------- Functions 5 & 6: accept and confirm collection ----------

def test_full_journey(client):
    # 1. A caterer posts food
    login(client, CATERER)
    assert api_post_listing(client, listing_xml("Journey stew", qty=12)).status_code == 201
    logout(client)
    new_id = 5  # four seeded listings come first

    # 2. Two NGOs request it
    for email in (NGO, NGO2):
        login(client, email)
        assert post(client, f"/food/{new_id}/request").status_code == 303
        logout(client)

    # 3. The caterer accepts the first request; the other is declined automatically
    login(client, CATERER)
    dash = client.get("/dashboard").text
    assert dash.count("would like") == 2
    rid = request_ids(dash, "accept")[0]
    assert post(client, f"/requests/{rid}/accept", page="/dashboard").status_code == 303
    dash = client.get("/dashboard").text
    assert "is reserved for" in dash and "Confirm collection" in dash and dash.count("would like") == 0
    assert "Journey stew" not in client.get("/food").text          # reserved food leaves the list

    # 4. The caterer confirms collection
    assert post(client, f"/requests/{rid}/collect", page="/dashboard").status_code == 303
    dash = client.get("/dashboard").text
    assert "Collection confirmed" in dash and "Collected" in dash

    # 5. Each NGO sees the right outcome
    logout(client)
    login(client, NGO)
    assert "Collected" in client.get("/dashboard").text
    logout(client)
    login(client, NGO2)
    assert "Declined" in client.get("/dashboard").text


def test_caterer_can_decline_a_request(client):
    login(client, NGO)
    post(client, "/food/1/request")
    logout(client)
    login(client, CATERER)
    rid = request_ids(client.get("/dashboard").text, "reject")[0]
    post(client, f"/requests/{rid}/reject", page="/dashboard")
    logout(client)
    login(client, NGO)
    assert "Declined" in client.get("/dashboard").text


def test_ngo_cancelling_accepted_request_reopens_food(client):
    login(client, NGO)
    post(client, "/food/1/request")
    logout(client)
    login(client, CATERER)
    rid = request_ids(client.get("/dashboard").text, "accept")[0]
    post(client, f"/requests/{rid}/accept", page="/dashboard")
    assert "/food/1/request" not in client.get("/food").text       # reserved
    logout(client)
    login(client, NGO)
    post(client, f"/requests/{rid}/cancel", page="/dashboard")
    assert "Cancelled" in client.get("/dashboard").text
    assert "/food/1/request" in client.get("/food").text           # available again


def test_other_caterer_cannot_accept_someone_elses_request(client):
    login(client, NGO)
    post(client, "/food/1/request")                                # food 1 belongs to CATERER
    logout(client)
    login(client, CATERER)
    rid = request_ids(client.get("/dashboard").text, "accept")[0]
    logout(client)
    login(client, CATERER2)
    post(client, f"/requests/{rid}/accept", page="/dashboard")
    assert "was not found" in client.get("/dashboard").text


def test_ngo_cannot_confirm_collection(client):
    login(client, NGO)
    post(client, "/food/1/request")
    rid = request_ids(client.get("/dashboard").text, "cancel")[0]
    post(client, f"/requests/{rid}/collect", page="/dashboard")
    assert "was not found" in client.get("/dashboard").text


def test_withdraw_listing(client):
    login(client, CATERER)
    post(client, "/food/1/withdraw", page="/dashboard")
    assert "Listing withdrawn" in client.get("/dashboard").text
    assert "/food/1/request" not in client.get("/food").text


def test_unknown_page_shows_friendly_404(client):
    r = client.get("/nope")
    assert r.status_code == 404 and "find that page" in r.text
