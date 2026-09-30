"""Persistence layer domain exceptions."""


class PersistenceError(Exception):
    """Base exception for all persistence layer errors."""


class DatabaseInitializationError(PersistenceError):
    """Raised when database schema initialization fails."""


class EntityNotFoundError(PersistenceError):
    """Raised when an expected persisted entity is not found in the database."""


class DuplicateEntityError(PersistenceError):
    """Raised when an operation violates unique or primary key constraints."""


class ReferentialIntegrityError(PersistenceError):
    """Raised when an operation violates foreign key constraints."""
