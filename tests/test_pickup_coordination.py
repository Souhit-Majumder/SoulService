"""Pickup directions and role-protected contact details."""
from tests.conftest import CATERER, NGO, csrf, login, logout, post, request_ids


def test_caterer_contact_only_visible_after_acceptance(client):
    login(client, CATERER)
    response = post(client, '/profile/contact', page='/dashboard', phone='+91 98765 43210')
    assert response.status_code == 303
    assert '+91 98765 43210' in client.get('/dashboard').text
    logout(client)
    assert '+91 98765 43210' not in client.get('/food').text
    login(client, NGO)
    assert '+91 98765 43210' not in client.get('/dashboard').text
    post(client, '/food/1/request')
    assert '+91 98765 43210' not in client.get('/dashboard').text
    logout(client)
    login(client, CATERER)
    rid = request_ids(client.get('/dashboard').text, 'accept')[0]
    post(client, f'/requests/{rid}/accept', page='/dashboard')
    logout(client)
    login(client, NGO)
    page = client.get('/dashboard').text
    assert 'Call caterer:' in page and '+91 98765 43210' in page
    assert 'google.com/maps/search/' in page and 'Get directions' in page


def test_ngo_cannot_edit_caterer_contact(client):
    login(client, NGO)
    response = post(client, '/profile/contact', phone='+91 9999999999')
    assert response.status_code == 303


def test_invalid_contact_is_rejected(client):
    login(client, CATERER)
    post(client, '/profile/contact', page='/dashboard', phone='javascript:alert(1)')
    page = client.get('/dashboard').text
    assert 'Enter a valid contact number' in page
    assert 'value="javascript:alert(1)"' not in page
