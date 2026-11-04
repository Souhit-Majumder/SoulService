"""Business rules for posting and withdrawing food listings."""
import sqlite3
from datetime import datetime

from app.repositories import listing_respository as listings
from app.repositories import request_respository as requests_repo
from app.services.errors import ServiceError

DIETARY_OPTIONS = ["vegetarian", "vegan", "jain", "halal", "gluten-free"]
ALLERGEN_OPTIONS = ["peanuts", "tree nuts", "milk", "eggs", "gluten", "soy"]
UNIT_OPTIONS = ["portions", "packets", "pieces", "kg", "trays"]

DB_FORMAT = "%Y-%m-%d %H:%M:%S"


def _invalid(message: str) -> ServiceError:
    return ServiceError(message, "VALIDATION_ERROR", 422)


def _clean_text(value: str | None, label: str, max_length: int) -> str:
    text = (value or "").strip()
    if not text:
        raise _invalid(f"{label} is required.")
    if len(text) > max_length:
        raise _invalid(f"{label} must be {max_length} characters or fewer.")
    return text


def _clean_tags(values: list[str], allowed: list[str], label: str) -> list[str]:
    tags = []
    for value in values:
        tag = value.strip().lower()
        if tag not in allowed:
            raise _invalid(f"'{value}' is not a recognised {label}.")
        if tag not in tags:
            tags.append(tag)
    return tags


def create_listing(conn: sqlite3.Connection, user: dict, payload: dict) -> int:
    """Check a new listing against the business rules, then save it."""
    if user["role"] != "caterer":
        raise ServiceError("Only caterers can post food.", "FORBIDDEN", 403)

    quantity = payload.get("quantity")
    if not isinstance(quantity, int) or quantity < 1 or quantity > 10000:
        raise _invalid("Quantity must be a whole number between 1 and 10,000.")

    prepared_at: datetime = payload["prepared_at"]
    pickup_deadline: datetime = payload["pickup_deadline"]
    if pickup_deadline <= prepared_at:
        raise _invalid("The pickup deadline must be later than the preparation time.")
    if pickup_deadline <= datetime.now():
        raise _invalid("The pickup deadline must be in the future.")

    data = {
        "food_name": _clean_text(payload.get("food_name"), "Food name", 100),
        "description": _clean_text(payload.get("description"), "Description", 500),
        "pickup_location": _clean_text(payload.get("pickup_location"), "Pickup location", 200),
        "unit": _clean_text(payload.get("unit"), "Unit", 30),
        "quantity": quantity,
        "prepared_at": prepared_at.strftime(DB_FORMAT),
        "pickup_deadline": pickup_deadline.strftime(DB_FORMAT),
        "dietary": _clean_tags(payload.get("dietary", []), DIETARY_OPTIONS, "dietary option"),
        "allergens": _clean_tags(payload.get("allergens", []), ALLERGEN_OPTIONS, "allergen"),
    }

    try:
        food_id = listings.create_listing(conn, user["user_id"], data)
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        raise _invalid("The listing could not be saved. Please check the details.")
    return food_id


def withdraw_listing(conn: sqlite3.Connection, user: dict, food_id: int) -> None:
    """A caterer takes back a listing nobody has been promised yet."""
    listing = listings.get_listing(conn, food_id)
    if not listing or listing["caterer_id"] != user["user_id"]:
        raise ServiceError("That listing was not found.", "LISTING_NOT_FOUND", 404)
    if listing["status"] != "available":
        raise ServiceError(
            "Only listings that are still available can be withdrawn.", "CONFLICT", 409
        )
    listings.set_status(conn, food_id, "cancelled")
    requests_repo.reject_all_pending(conn, food_id)
    conn.commit()
