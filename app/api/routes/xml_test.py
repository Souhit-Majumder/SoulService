from typing import Annotated
from fastapi import APIRouter, Body, Response

from app.xml_api.validator import load_schema
from app.xml_api.parser import parse_xml
from app.xml_api.validator import validate_xml
from app.xml_api.responses import xml_response, xml_error_response
from app.xml_api.exceptions import MalformedXMLError, XMLValidationError



MAX_XML_SIZE = 1 * 1024 * 1024  # 1 MB


router = APIRouter()

schema = load_schema()
@router.post("/validate_xml_schema")
async def validate_xml_schema(
    xml_content: Annotated[str,Body(media_type="application/xml")]
):
    if len(xml_content.encode("utf-8")) > MAX_XML_SIZE:
        return xml_response(
            status="error",
            message="Request body too large.",
            error={
                "code": "REQUEST_TOO_LARGE",
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

    
    return xml_response(
        status="success",
        message="XML is valid.",
    )

