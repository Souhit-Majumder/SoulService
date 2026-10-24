import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lxml import etree
from app.xml_api.validator import load_schema, validate_xml
from app.xml_api.exceptions import XMLValidationError

schema = load_schema("listing.xsd")

valid_xml = b"""
<create_listing>
    <food_name>Vegetable Rice</food_name>
    <description>Freshly prepared vegetable rice</description>
    <quantity>15</quantity>
    <unit>portions</unit>
    <prepared_at>2026-10-17T11:30:00</prepared_at>
    <pickup_deadline>2026-10-17T14:00:00</pickup_deadline>
    <pickup_location>Manipal, Karnataka</pickup_location>
    <dietary_infos>
        <dietary_info>vegetarian</dietary_info>
    </dietary_infos>
    <allergens>
        <allergen>peanuts</allergen>
    </allergens>
</create_listing>
"""

document = etree.fromstring(valid_xml)

if schema.validate(document):
    print("Valid listing accepted.")
else:
    print("Valid listing rejected:")
    print(schema.error_log)


invalid_xml = b"""
<create_listing>
    <food_name>Vegetable Rice</food_name>
    <description>Freshly prepared vegetable rice</description>
    <quantity>0</quantity>
    <unit>portions</unit>
    <prepared_at>2026-10-17T11:30:00</prepared_at>
    <pickup_deadline>2026-10-17T14:00:00</pickup_deadline>
    <pickup_location>Manipal, Karnataka</pickup_location>
    <dietary_infos/>
    <allergens/>
</create_listing>
"""

invalid_document = etree.fromstring(invalid_xml)

if schema.validate(invalid_document):
    print("Invalid listing was incorrectly accepted.")
else:
    print("Invalid listing rejected, as expected.")
    print(schema.error_log)


document = etree.fromstring(valid_xml)

try:
    validate_xml(document, schema)
    print("Valid listing accepted.")
except XMLValidationError as exc:
    print(f"Valid listing rejected: {exc}")