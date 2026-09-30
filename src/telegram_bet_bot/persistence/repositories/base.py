"""Base repository definitions and shared persistence helpers."""

import sqlite3
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    PersistenceError,
    ReferentialIntegrityError,
)


def handle_integrity_error(
    err: sqlite3.IntegrityError,
    entity_name: str,
    entity_id: str,
) -> None:
    """Analyze sqlite3.IntegrityError and raise specific domain persistence exceptions.

    Distinguishes foreign key constraint violations from unique/primary key duplicates.
    """
    err_str = str(err).upper()
    error_code = getattr(err, "sqlite_errorname", "")

    if "FOREIGN KEY" in err_str or error_code == "SQLITE_CONSTRAINT_FOREIGNKEY":
        raise ReferentialIntegrityError(
            f"Cannot persist {entity_name} '{entity_id}': referenced entity does not exist ({err})."
        ) from err

    if "UNIQUE" in err_str or "PRIMARY KEY" in err_str or error_code in {
        "SQLITE_CONSTRAINT_UNIQUE",
        "SQLITE_CONSTRAINT_PRIMARYKEY",
    }:
        raise DuplicateEntityError(
            f"{entity_name} with identity '{entity_id}' already exists ({err})."
        ) from err

    raise PersistenceError(
        f"Database integrity constraint failed while persisting {entity_name} '{entity_id}': {err}"
    ) from err


class BaseRepository:
    """Base repository holding an active, configured SQLite connection."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    @property
    def connection(self) -> sqlite3.Connection:
        """Return the active SQLite connection."""
        return self._connection
