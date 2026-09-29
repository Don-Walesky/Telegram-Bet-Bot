"""Domain exceptions for Telegram Bet Bot."""


class DomainError(Exception):
    """Base exception for all domain-level errors."""


class DomainValidationError(DomainError):
    """Raised when a domain entity or value object violates invariant constraints."""


class InvalidOddsError(DomainValidationError):
    """Raised when odds are non-numeric, <= 1.0, NaN, infinite, or otherwise invalid."""
