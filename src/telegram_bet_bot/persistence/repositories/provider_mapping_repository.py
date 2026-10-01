"""Repository for durable external-to-internal provider identity mappings."""

from datetime import datetime, timezone
import sqlite3

from telegram_bet_bot.persistence.exceptions import PersistenceError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class ProviderMappingRepository(BaseRepository):
    """Persistence repository for provider identity mappings.

    Manages durable mapping between (provider_name, entity_type, external_id)
    and internal canonical domain identity.
    Participates in transaction boundaries owned by the service layer.
    """

    VALID_ENTITY_TYPES = {"SPORT", "LEAGUE", "FIXTURE", "MARKET", "SELECTION"}

    def save_mapping(
        self,
        provider_name: str,
        entity_type: str,
        external_id: str,
        internal_id: str,
        created_at: datetime | None = None,
    ) -> None:
        """Persist or update an identity mapping (deterministic upsert).

        Raises:
            PersistenceError: If validation fails or database error occurs.
        """
        clean_provider = provider_name.strip() if provider_name else ""
        clean_type = entity_type.strip().upper() if entity_type else ""
        clean_ext = external_id.strip() if external_id else ""
        clean_int = internal_id.strip() if internal_id else ""

        if not clean_provider:
            raise PersistenceError("Provider name must be a non-empty string.")
        if clean_type not in self.VALID_ENTITY_TYPES:
            raise PersistenceError(
                f"Invalid entity type '{entity_type}'. Must be one of: {sorted(self.VALID_ENTITY_TYPES)}"
            )
        if not clean_ext:
            raise PersistenceError("External ID must be a non-empty string.")
        if not clean_int:
            raise PersistenceError("Internal ID must be a non-empty string.")

        timestamp = (
            created_at.astimezone(timezone.utc).isoformat()
            if created_at is not None
            else datetime.now(timezone.utc).isoformat()
        )

        query = """
        INSERT INTO provider_identity_mappings (
            provider_name, entity_type, external_id, internal_id, created_at
        ) VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(provider_name, entity_type, external_id) DO UPDATE SET
            internal_id = excluded.internal_id;
        """
        try:
            self.connection.execute(
                query,
                (clean_provider, clean_type, clean_ext, clean_int, timestamp),
            )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "ProviderIdentityMapping", f"{clean_provider}:{clean_type}:{clean_ext}")

    def get_internal_id(
        self,
        provider_name: str,
        entity_type: str,
        external_id: str,
    ) -> str | None:
        """Retrieve internal domain ID for a provider external ID, or None if not found."""
        clean_provider = provider_name.strip() if provider_name else ""
        clean_type = entity_type.strip().upper() if entity_type else ""
        clean_ext = external_id.strip() if external_id else ""

        query = """
        SELECT internal_id FROM provider_identity_mappings
        WHERE provider_name = ? AND entity_type = ? AND external_id = ?;
        """
        cursor = self.connection.execute(query, (clean_provider, clean_type, clean_ext))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_external_id(
        self,
        provider_name: str,
        entity_type: str,
        internal_id: str,
    ) -> str | None:
        """Retrieve the primary external ID mapped to an internal domain entity."""
        clean_provider = provider_name.strip() if provider_name else ""
        clean_type = entity_type.strip().upper() if entity_type else ""
        clean_int = internal_id.strip() if internal_id else ""

        query = """
        SELECT external_id FROM provider_identity_mappings
        WHERE provider_name = ? AND entity_type = ? AND internal_id = ?
        ORDER BY created_at ASC;
        """
        cursor = self.connection.execute(query, (clean_provider, clean_type, clean_int))
        row = cursor.fetchone()
        return row[0] if row else None

    def list_external_ids(
        self,
        provider_name: str,
        entity_type: str,
        internal_id: str,
    ) -> list[str]:
        """List all external IDs from a given provider mapped to an internal domain entity."""
        clean_provider = provider_name.strip() if provider_name else ""
        clean_type = entity_type.strip().upper() if entity_type else ""
        clean_int = internal_id.strip() if internal_id else ""

        query = """
        SELECT external_id FROM provider_identity_mappings
        WHERE provider_name = ? AND entity_type = ? AND internal_id = ?
        ORDER BY created_at ASC;
        """
        cursor = self.connection.execute(query, (clean_provider, clean_type, clean_int))
        return [row[0] for row in cursor.fetchall()]

    def exists(
        self,
        provider_name: str,
        entity_type: str,
        external_id: str,
    ) -> bool:
        """Check whether an identity mapping exists."""
        return self.get_internal_id(provider_name, entity_type, external_id) is not None

    def count(self, provider_name: str | None = None, entity_type: str | None = None) -> int:
        """Count mappings, optionally filtered by provider and/or entity type."""
        clauses = []
        params = []
        if provider_name:
            clauses.append("provider_name = ?")
            params.append(provider_name.strip())
        if entity_type:
            clauses.append("entity_type = ?")
            params.append(entity_type.strip().upper())

        where_clause = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        query = f"SELECT count(*) FROM provider_identity_mappings {where_clause};"
        cursor = self.connection.execute(query, tuple(params))
        row = cursor.fetchone()
        return row[0] if row else 0

    def delete_mapping(
        self,
        provider_name: str,
        entity_type: str,
        external_id: str,
    ) -> bool:
        """Delete an identity mapping. Returns True if a record was deleted."""
        clean_provider = provider_name.strip() if provider_name else ""
        clean_type = entity_type.strip().upper() if entity_type else ""
        clean_ext = external_id.strip() if external_id else ""

        query = """
        DELETE FROM provider_identity_mappings
        WHERE provider_name = ? AND entity_type = ? AND external_id = ?;
        """
        cursor = self.connection.execute(query, (clean_provider, clean_type, clean_ext))
        return cursor.rowcount > 0
