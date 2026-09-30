"""Repository for Market domain entities."""

from decimal import Decimal
import sqlite3

from telegram_bet_bot.domain import Market
from telegram_bet_bot.persistence.exceptions import EntityNotFoundError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class MarketRepository(BaseRepository):
    """Persistence repository for Market entities."""

    def save(self, market: Market) -> None:
        """Persist or update a Market entity (deterministic upsert).

        Preserves Decimal line values losslessly as strings.

        Raises:
            ReferentialIntegrityError: If the associated Fixture does not exist.
        """
        line_str = str(market.line) if market.line is not None else None
        query = """
        INSERT INTO markets (identity, name, fixture_id, market_id, line)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(identity) DO UPDATE SET
            name = excluded.name,
            fixture_id = excluded.fixture_id,
            market_id = excluded.market_id,
            line = excluded.line;
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        market.identity,
                        market.name,
                        market.fixture_id,
                        market.market_id,
                        line_str,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Market", market.identity)

    def create(self, market: Market) -> None:
        """Insert a new Market entity.

        Raises:
            DuplicateEntityError: If a market with the same identity already exists.
            ReferentialIntegrityError: If the associated Fixture does not exist.
        """
        line_str = str(market.line) if market.line is not None else None
        query = """
        INSERT INTO markets (identity, name, fixture_id, market_id, line)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        market.identity,
                        market.name,
                        market.fixture_id,
                        market.market_id,
                        line_str,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Market", market.identity)

    def _row_to_market(self, row: sqlite3.Row) -> Market:
        """Map a database row to a pure domain Market entity."""
        line = Decimal(row["line"]) if row["line"] is not None else None
        return Market(
            name=row["name"],
            fixture=row["fixture_id"],
            market_id=row["market_id"],
            line=line,
        )

    def get_by_identity(self, identity: str) -> Market | None:
        """Retrieve a Market by its canonical identity, or None if not found."""
        query = """
        SELECT identity, name, fixture_id, market_id, line
        FROM markets
        WHERE identity = ?;
        """
        cursor = self.connection.execute(query, (identity.strip(),))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_market(row)

    def get(self, identity: str) -> Market:
        """Retrieve a Market by its identity or raise EntityNotFoundError."""
        market = self.get_by_identity(identity)
        if market is None:
            raise EntityNotFoundError(f"Market with identity '{identity}' was not found.")
        return market

    def list_by_fixture(self, fixture_id: str) -> list[Market]:
        """Retrieve all markets associated with a given fixture."""
        query = """
        SELECT identity, name, fixture_id, market_id, line
        FROM markets
        WHERE fixture_id = ?
        ORDER BY name ASC;
        """
        cursor = self.connection.execute(query, (fixture_id.strip(),))
        return [self._row_to_market(row) for row in cursor.fetchall()]

    def delete(self, identity: str) -> bool:
        """Delete a Market by its identity.

        Returns True if deleted, False if not found.
        Cascades deletion to associated selections.
        """
        query = "DELETE FROM markets WHERE identity = ?;"
        try:
            with self.connection:
                cursor = self.connection.execute(query, (identity.strip(),))
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Market", identity)
            return False
