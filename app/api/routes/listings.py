from typing import Annotated
from datetime import datetime

from fastapi import APIRouter, Body

from app.xml_api.parser import parse_xml
from app.xml_api.validator import load_schema, validate_xml
from app.xml_api.exceptions import MalformedXMLError, XMLValidationError
from app.xml_api.responses import xml_response, xml_error_response

router = APIRouter()
schema = load_schema("listing.xsd")

MAX_XML_SIZE = 1 * 1024 * 1024  # 1 MB


@router.post("/", summary="Create a food listing")
async def create_listing(
    xml_content: Annotated[str, Body(media_type="application/xml")]
):
    if len(xml_content.encode("utf-8")) > MAX_XML_SIZE:
        return xml_response(
            status="error",
            message="Request body too large.",
            error={
                "code": "PAYLOAD_TOO_LARGE",
                "details": "The XML request must not exceed 1 MB.",
            },
            status_code=413,
        )
    
    try:
        root = parse_xml(xml_content.encode("utf-8"))
    except MalformedXMLError as exc:
        return xml_error_response(exc)

    try:
        validate_xml(root, schema)
    except XMLValidationError as exc:
        return xml_error_response(exc)


    prepared_at = datetime.fromisoformat(root.findtext("prepared_at"))
    pickup_deadline = datetime.fromisoformat(root.findtext("pickup_deadline"))

    if pickup_deadline <= prepared_at:
        return xml_response(
            status="error",
            message="Invalid listing data.",
            error={
                "code": "VALIDATION_ERROR",
                "details": "The pickup deadline must be later than the preparation time.",
            },
            status_code=422,
        )

    return xml_response(
        status="success",
        message="Listing data validated successfully.",
        data={
            "validation": "passed",
        },
        status_code=200,
    )