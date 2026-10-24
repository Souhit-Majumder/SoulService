from fastapi import Response

from app.xml_api.serializer import serialize_response
from app.xml_api.exceptions import MalformedXMLError, XMLValidationError


def xml_response(
    status: str,
    message: str,
    data: dict | None = None,
    error: dict | None = None,
    status_code: int = 200,
) -> Response:
    xml_content = serialize_response(
        status=status,
        message=message,
        data=data,
        error=error,
    )
    return Response(
        content=xml_content,
        status_code=status_code,
        media_type="application/xml",
    )


def xml_error_response(exc: Exception) -> Response:
    if isinstance(exc, MalformedXMLError):
        return xml_response(
            status="error",
            message="Invalid XML.",
            error={
                "code": "MALFORMED_XML",
                "details": "The request body is not well-formed XML.",
            },
            status_code=400,
        )

    if isinstance(exc, XMLValidationError):
        return xml_response(
            status="error",
            message="XML validation failed.",
            error={
                "code": "XML_SCHEMA_INVALID",
                "details": "The XML does not conform to the required XML schema.",
            },
            status_code=422,
        )

    return xml_response(
        status="error",
        message="An internal server error occurred.",
        error={
            "code": "INTERNAL_ERROR",
            "details": "The server could not complete the request.",
        },
        status_code=500,
    )