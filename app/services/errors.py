class ServiceError(Exception):
    """A problem the user can understand (bad input, not allowed, conflict...).

    `code` matches the error codes in docs/api-contract.md and `status_code`
    is the HTTP status the XML API should answer with.
    """

    def __init__(self, message: str, code: str = "VALIDATION_ERROR", status_code: int = 422):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
