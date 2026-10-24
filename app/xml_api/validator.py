from pathlib import Path
from lxml import etree

from app.xml_api.exceptions import XMLValidationError



SCHEMA_PATH = (
    Path(__file__).resolve().parent
    / "schemas"
)


def load_schema(filename: str="common.xsd") -> etree.XMLSchema:
    schema_path = (SCHEMA_PATH / filename).resolve()

    if schema_path.parent != SCHEMA_PATH.resolve() or schema_path.suffix != ".xsd":
        raise ValueError("Invalid schema filename.")
    
    schema_document = etree.parse(str(schema_path))
    return etree.XMLSchema(schema_document)


def validate_xml(
    xml_document: etree._Element,
    schema: etree.XMLSchema,
) -> bool:
    if not schema.validate(xml_document):
        raise XMLValidationError(
            "The request does not conform to the required XML schema."
        )

    return True

