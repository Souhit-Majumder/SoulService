import pytest
from pathlib import Path
from lxml import etree

from app.xml_api.parser import parse_xml
from app.xml_api.validator import load_schema, validate_xml

from app.xml_api.exceptions import XMLValidationError, MalformedXMLError
from app.xml_api.serializer import serialize_response


def test_common_schema_compiles():
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "app" / "xml_api" / "schemas" / "common.xsd"

    xsd_document = etree.parse(str(schema_path))
    schema = etree.XMLSchema(xsd_document)

    assert schema is not None


def test_valid_response_passes_schema():
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "app" / "xml_api" / "schemas" / "common.xsd"

    schema = etree.XMLSchema(etree.parse(str(schema_path)))

    xml = etree.fromstring(b"""
        <response>
            <status>success</status>
            <message>Listing retrieved.</message>
            <data/>
            <error/>
        </response>
    """)

    assert schema.validate(xml)


def test_invalid_status_fails_schema():
    project_root = Path(__file__).resolve().parents[1]
    schema_path = project_root / "app" / "xml_api" / "schemas" / "common.xsd"

    schema = etree.XMLSchema(etree.parse(str(schema_path)))

    xml = etree.fromstring(b"""
        <response>
            <status>pending</status>
            <message>Listing retrieved.</message>
            <data/>
            <error/>
        </response>
    """)

    assert not schema.validate(xml)


def test_parser_accepts_well_formed_xml():
    root = parse_xml(b"<message>Hello</message>")
    assert root.tag == "message"

    
def test_parser_rejects_malformed_xml():
    with pytest.raises(MalformedXMLError):
        parse_xml(b"<message>Hello</wrong>")


def test_validator_accepts_valid_response():
    schema = load_schema()
    xml_document = parse_xml(b"""
        <response>
            <status>success</status>
            <message>Listing retrieved.</message>
            <data/>
            <error/>
        </response>
    """)

    assert validate_xml(xml_document, schema)


def test_validator_rejects_invalid_status():
    schema = load_schema()
    xml_document = parse_xml(b"""
        <response>
            <status>pending</status>
            <message>Listing retrieved.</message>
            <data/>
            <error/>
        </response>
    """)

    with pytest.raises(XMLValidationError):
        validate_xml(xml_document, schema)


def test_serializer_produces_valid_xml():
    xml_bytes = serialize_response(
        status="success",
        message="Listing retrieved.",
        data={"title": "Fresh vegetables", "quantity": 10},
    )

    root = etree.fromstring(xml_bytes)

    assert root.tag == "response"
    assert root.findtext("status") == "success"
    assert root.findtext("message") == "Listing retrieved."
    assert root.findtext("data/title") == "Fresh vegetables"
    assert root.findtext("data/quantity") == "10"
    assert root.find("error") is not None


def test_serializer_escapes_special_characters():
    xml_bytes = serialize_response(
        status="success",
        message="Food & supplies",
        data={"title": "Bread <and> fruit"},
    )

    root = etree.fromstring(xml_bytes)

    assert root.findtext("message") == "Food & supplies"
    assert root.findtext("data/title") == "Bread <and> fruit"
