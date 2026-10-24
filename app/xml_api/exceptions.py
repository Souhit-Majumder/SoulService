
class XMLValidationError(Exception):
    """Raised when XML does not conform to the required schema."""


class MalformedXMLError(Exception):
    """Raised when the input is not well-formed XML."""
