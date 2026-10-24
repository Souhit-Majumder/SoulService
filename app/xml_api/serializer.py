
from lxml import etree


def serialize_response(
    status: str,
    message: str,
    data: dict | None = None,
    error: dict | None = None,
) -> bytes:
    root = etree.Element("response")

    etree.SubElement(root, "status").text = status
    etree.SubElement(root, "message").text = message

    data_element = etree.SubElement(root, "data")
    if data:
        for key, value in data.items():
            etree.SubElement(data_element, key).text = str(value)

    error_element = etree.SubElement(root, "error")
    if error:
        for key in ("code", "details"):
            if key in error:
                etree.SubElement(error_element, key).text = str(error[key])

    return etree.tostring(
        root,
        encoding="UTF-8",
        xml_declaration=True,
        pretty_print=True,
    )
