"""Business rules for the request -> accept -> collect journey."""
import sqlite3
from datetime import datetime

from app.repositories import listing_respository as listings
from app.repositories import request_respository as requests_repo
from app.services.errors import ServiceError

# Messages written by our own database triggers/constraints; safe to show.
_TRIGGER_MESSAGES = (
    "Only recipients can request food listings",
    "A user cannot request their own food listing",
    "Cannot accept request - listing is unavailable or expired",
    "Only an accepted request can be picked up",
    "Listing is not reserved or pickup deadline has passed",
)


def _from_integrity_error(exc: sqlite3.IntegrityError) -> ServiceError:
    text = str(exc)
    if "UNIQUE" in text:
        return ServiceError(
            "That request can't go ahead: there is already an active request.",
            "CONFLICT", 409,
        )
    for message in _TRIGGER_MESSAGES:
        if message in text:
            return ServiceError(message + ".", "LISTING_UNAVAILABLE", 409)
    return ServiceError("The action could not be completed.", "CONFLICT", 409)


def _load_request(conn: sqlite3.Connection, request_id: int) -> dict:
    req = requests_repo.get_request(conn, request_id)
    if not req:
        raise ServiceError("That request was not found.", "REQUEST_NOT_FOUND", 404)
    return req


def _owned_by_caterer(conn, user, request_id) -> dict:
    req = _load_request(conn, request_id)
    if user["role"] != "caterer" or req["caterer_id"] != user["user_id"]:
        # Same message as "not found" so people can't probe other accounts' data.
        raise ServiceError("That request was not found.", "REQUEST_NOT_FOUND", 404)
    return req


def request_food(conn: sqlite3.Connection, user: dict, food_id: int) -> None:
    """An NGO asks for a listing."""
    if user["role"] != "recipient":
        raise ServiceError("Only NGO accounts can request food.", "FORBIDDEN", 403)
    listing = listings.get_listing(conn, food_id)
    if not listing:
        raise ServiceError("That food listing was not found.", "LISTING_NOT_FOUND", 404)
    if listing["status"] != "available":
        raise ServiceError("Sorry, that food is no longer available.", "LISTING_UNAVAILABLE", 409)
    if listing["pickup_deadline"] <= datetime.now().strftime("%Y-%m-%d %H:%M:%S"):
        raise ServiceError("The pickup deadline for that food has passed.", "LISTING_UNAVAILABLE", 409)
    try:
        requests_repo.create_request(conn, food_id, user["user_id"])
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        text = str(exc)
        if "UNIQUE" in text:
            raise ServiceError("You have already requested this food.", "CONFLICT", 409)
        raise _from_integrity_error(exc)


def accept_request(conn: sqlite3.Connection, user: dict, request_id: int) -> None:
    """The caterer picks one NGO. The food becomes reserved and other requests are declined."""
    req = _owned_by_caterer(conn, user, request_id)
    if req["status"] != "pending":
        raise ServiceError("That request has already been handled.", "CONFLICT", 409)
    try:
        requests_repo.set_status(conn, request_id, "accepted")  # trigger reserves the food
        requests_repo.reject_other_pending(conn, req["food_id"], request_id)
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise _from_integrity_error(exc)


def reject_request(conn: sqlite3.Connection, user: dict, request_id: int) -> None:
    req = _owned_by_caterer(conn, user, request_id)
    if req["status"] != "pending":
        raise ServiceError("That request has already been handled.", "CONFLICT", 409)
    requests_repo.set_status(conn, request_id, "rejected")
    conn.commit()


def cancel_request(conn: sqlite3.Connection, user: dict, request_id: int) -> None:
    """The NGO changes its mind. If it was accepted, a trigger re-opens the food."""
    req = _load_request(conn, request_id)
    if user["role"] != "recipient" or req["recipient_id"] != user["user_id"]:
        raise ServiceError("That request was not found.", "REQUEST_NOT_FOUND", 404)
    if req["status"] not in ("pending", "accepted"):
        raise ServiceError("That request can no longer be cancelled.", "CONFLICT", 409)
    requests_repo.set_status(conn, request_id, "cancelled")
    conn.commit()


def confirm_collection(conn: sqlite3.Connection, user: dict, request_id: int) -> None:
    """The caterer confirms the NGO has collected the food."""
    req = _owned_by_caterer(conn, user, request_id)
    if req["status"] != "accepted":
        raise ServiceError("Only an accepted request can be marked as collected.", "CONFLICT", 409)
    try:
        requests_repo.set_status(conn, request_id, "picked_up")  # trigger marks the food collected
        conn.commit()
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise _from_integrity_error(exc)
