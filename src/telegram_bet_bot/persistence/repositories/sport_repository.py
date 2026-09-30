"""Repository for Sport domain entities."""

import sqlite3
from telegram_bet_bot.domain import Sport
from telegram_bet_bot.persistence.exceptions import EntityNotFoundError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class SportRepository(BaseRepository):
    """Persistence repository for Sport entities."""

    def save(self, sport: Sport) -> None:
        """Persist or update a Sport entity (deterministic upsert)."""
        query = """
        INSERT INTO sports (identity, name)
        VALUES (?, ?)
        ON CONFLICT(identity) DO UPDATE SET
            name = excluded.name;
        """
        try:
            self.connection.execute(query, (sport.name, sport.name))
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Sport", sport.name)

    def create(self, sport: Sport) -> None:
        """Insert a new Sport entity.

        Raises:
            DuplicateEntityError: If a sport with the same identity already exists.
        """
        query = "INSERT INTO sports (identity, name) VALUES (?, ?);"
        try:
            self.connection.execute(query, (sport.name, sport.name))
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Sport", sport.name)

    def get_by_identity(self, identity: str) -> Sport | None:
        """Retrieve a Sport entity by canonical identity/name, or None if not found."""
        query = "SELECT name FROM sports WHERE identity = ? OR name = ?;"
        normalized_identity = identity.strip().lower()
        cursor = self.connection.execute(query, (normalized_identity, normalized_identity))
        row = cursor.fetchone()
        if row is None:
            return None
        return Sport(row["name"])

    def get(self, identity: str) -> Sport:
        """Retrieve a Sport entity or raise EntityNotFoundError."""
        sport = self.get_by_identity(identity)
        if sport is None:
            raise EntityNotFoundError(f"Sport with identity '{identity}' was not found.")
        return sport

    def list_all(self) -> list[Sport]:
        """Retrieve all persisted Sport entities sorted by canonical name."""
        query = "SELECT name FROM sports ORDER BY name ASC;"
        cursor = self.connection.execute(query)
        return [Sport(row["name"]) for row in cursor.fetchall()]

    def exists(self, identity: str) -> bool:
        """Check whether a sport with the given identity exists."""
        query = "SELECT 1 FROM sports WHERE identity = ? OR name = ? LIMIT 1;"
        normalized = identity.strip().lower()
        cursor = self.connection.execute(query, (normalized, normalized))
        return cursor.fetchone() is not None

    def delete(self, identity: str) -> bool:
        """Delete a Sport entity by identity.

        Returns True if a record was deleted, False if none matched.
        Raises ReferentialIntegrityError if leagues reference this sport.
        """
        query = "DELETE FROM sports WHERE identity = ? OR name = ?;"
        normalized = identity.strip().lower()
        try:
            cursor = self.connection.execute(query, (normalized, normalized))
            return cursor.rowcount > 0
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Sport", identity)
            return False
