"""Service-layer errors mapped to HTTP responses in routes."""


class IngestionError(Exception):
    """Base class for CSV ingestion failures."""

    def __init__(self, message: str, *, details: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class InvalidFileTypeError(IngestionError):
    pass


class CsvValidationError(IngestionError):
    pass


class EmptyCsvError(IngestionError):
    pass


class InvestigationNotFoundError(Exception):
    """Raised when an investigation or upload_id cannot be found."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class UploadContentNotFoundError(Exception):
    """Raised when raw uploaded content cannot be loaded from storage."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
