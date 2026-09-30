"""Custom exceptions for the fixture and market ingestion subsystem."""


class IngestionError(Exception):
    """Base exception for all ingestion failures."""


class ProviderError(IngestionError):
    """Raised when an external sports-data provider fails or is unreachable."""


class ProviderUnavailableError(ProviderError):
    """Raised when the external data provider service cannot be reached."""


class MalformedProviderDataError(ProviderError):
    """Raised when provider data is missing required structural attributes or is unparseable."""


class NormalizationError(IngestionError):
    """Raised when provider data violates domain contracts or cannot be normalized."""
