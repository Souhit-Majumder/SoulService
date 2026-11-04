import secrets
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, Request

from app.database.connection import get_db
from app.repositories import user_respository as users
from app.services import listing_service
from app.services.errors import ServiceError
from app.web.helpers import flash
from app.xml_api.exceptions import MalformedXMLError, XMLValidationError
from app.xml_api.parser import parse_xml
from app.xml_api.responses import xml_error_response, xml_response
from app.xml_api.validator import load_schema, validate_xml

router = APIRouter()
schema = load_schema("listing.xsd")

MAX_XML_SIZE = 1 * 1024 * 1024  # 1 MB


def _error(status_code: int, code: str, message: str, details: str):
    return xml_response(
        status="error",
        message=message,
        error={"code": code, "details": details},
        status_code=status_code,
    )


def _to_naive_local(value: str) -> datetime:
    """xs:dateTime -> a plain local datetime (timezone-aware values are converted)."""
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def _payload_from_xml(root) -> dict:
    return {
        "food_name": root.findtext("food_name"),
        "description": root.findtext("description"),
        "quantity": int(root.findtext("quantity").strip()),
        "unit": root.findtext("unit"),
        "prepared_at": _to_naive_local(root.findtext("prepared_at")),
        "pickup_deadline": _to_naive_local(root.findtext("pickup_deadline")),
        "pickup_location": root.findtext("pickup_location"),
        "dietary": [e.text or "" for e in root.findall("dietary_infos/dietary_info")],
        "allergens": [e.text or "" for e in root.findall("allergens/allergen")],
    }


@router.post(
    "",
    summary="Create a food listing",
    openapi_extra={
        "requestBody": {
            "required": True,
            "content": {"application/xml": {"schema": {"type": "string"}}},
        }
    },
)
@router.post("/", include_in_schema=False)
async def create_listing(request: Request, conn: sqlite3.Connection = Depends(get_db)):
    # 1. Who is asking? (contract section 9.4, rule 9)
    user_id = request.session.get("user_id")
    user = users.get_by_id(conn, user_id) if user_id else None
    if not user:
        return _error(401, "UNAUTHORIZED", "Authentication required.", "Please log in first.")
    if user["role"] != "caterer":
        return _error(403, "FORBIDDEN", "Not allowed.", "Only caterers can create food listings.")

    # 2. Protect against forged requests from other websites (CSRF).
    sent_token = request.headers.get("x-csrf-token", "")
    expected_token = request.session.get("csrf", "")
    if not expected_token or not secrets.compare_digest(sent_token, expected_token):
        return _error(403, "FORBIDDEN", "Not allowed.", "The security token is missing or invalid.")

    # 3. Is the request the right kind of thing?
    if "xml" not in request.headers.get("content-type", "").lower():
        return _error(415, "VALIDATION_ERROR", "Unsupported media type.",
                      "Send the listing as application/xml.")
    body = await request.body()
    if len(body) > MAX_XML_SIZE:
        return _error(413, "PAYLOAD_TOO_LARGE", "Request body too large.",
                      "The XML request must not exceed 1 MB.")

    # 4. Parse and check the XML against listing.xsd (nothing is saved yet).
    try:
        root = parse_xml(body)
    except MalformedXMLError as exc:
        return xml_error_response(exc)
    try:
        validate_xml(root, schema)
    except XMLValidationError as exc:
        return xml_error_response(exc)

    # 5. Business rules + saving. Schema validation and business rules stay separate.
    try:
        payload = _payload_from_xml(root)
        listing_id = listing_service.create_listing(conn, user, payload)
    except ValueError:
        return _error(422, "VALIDATION_ERROR", "Invalid listing data.",
                      "One of the date or number values could not be read.")
    except ServiceError as exc:
        return _error(exc.status_code, exc.code, "Invalid listing data.", exc.message)

    flash(request, "Food posted! NGOs can now see and request it.")
    return xml_response(
        status="success",
        message="Food listing created successfully.",
        data={"listing_id": listing_id},
        status_code=201,
    )
