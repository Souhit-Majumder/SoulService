from fastapi import Response
from lxml import etree

from app.xml_api.exceptions import MalformedXMLError


def parse_xml(xml_content: bytes) -> etree._Element:
    try:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            recover=False,
            huge_tree=False,
        )
        root = etree.fromstring(xml_content, parser=parser)

        if root.getroottree().docinfo.doctype:
            raise MalformedXMLError(
                "DOCTYPE declarations are not allowed."
            )
        return root
    
    except etree.XMLSyntaxError as exc:
        raise MalformedXMLError(
            "The XML provided is not well-formed."
        ) from exc
