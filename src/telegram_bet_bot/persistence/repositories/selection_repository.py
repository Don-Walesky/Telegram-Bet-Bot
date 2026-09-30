"""Repository for Selection domain entities."""

from decimal import Decimal
import sqlite3

from telegram_bet_bot.domain import Market, Odds, Selection
from telegram_bet_bot.persistence.exceptions import EntityNotFoundError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class SelectionRepository(BaseRepository):
    """Persistence repository for Selection entities."""

    def save(self, selection: Selection) -> None:
        """Persist or update a Selection entity (deterministic upsert).

        Preserves Decimal odds values losslessly as strings.

        Raises:
            ReferentialIntegrityError: If the associated Market does not exist.
        """
        odds_str = str(selection.odds.decimal_value) if selection.odds is not None else None
        query = """
        INSERT INTO selections (identity, name, market_identity, selection_id, odds)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(identity) DO UPDATE SET
            name = excluded.name,
            market_identity = excluded.market_identity,
            selection_id = excluded.selection_id,
            odds = excluded.odds;
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        selection.identity,
                        selection.name,
                        selection.market.identity,
                        selection.selection_id,
                        odds_str,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Selection", selection.identity)

    def create(self, selection: Selection) -> None:
        """Insert a new Selection entity.

        Raises:
            DuplicateEntityError: If a selection with the same identity already exists.
            ReferentialIntegrityError: If the associated Market does not exist.
        """
        odds_str = str(selection.odds.decimal_value) if selection.odds is not None else None
        query = """
        INSERT INTO selections (identity, name, market_identity, selection_id, odds)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        selection.identity,
                        selection.name,
                        selection.market.identity,
                        selection.selection_id,
                        odds_str,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Selection", selection.identity)

    def _row_to_selection(self, row: sqlite3.Row) -> Selection:
        """Map a joined database row to a pure domain Selection entity."""
        line = Decimal(row["line"]) if row["line"] is not None else None
        market = Market(
            name=row["market_name"],
            fixture=row["fixture_id"],
            market_id=row["market_id"],
            line=line,
        )
        odds = Odds(Decimal(row["odds"])) if row["odds"] is not None else None
        return Selection(
            name=row["name"],
            market=market,
            selection_id=row["selection_id"],
            odds=odds,
        )

    def get_by_identity(self, identity: str) -> Selection | None:
        """Retrieve a Selection by its canonical identity, or None if not found."""
        query = """
        SELECT s.identity, s.name, s.selection_id, s.odds,
               m.identity AS market_identity, m.name AS market_name,
               m.fixture_id, m.market_id, m.line
        FROM selections s
        JOIN markets m ON s.market_identity = m.identity
        WHERE s.identity = ?;
        """
        cursor = self.connection.execute(query, (identity.strip(),))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_selection(row)

    def get(self, identity: str) -> Selection:
        """Retrieve a Selection by its identity or raise EntityNotFoundError."""
        selection = self.get_by_identity(identity)
        if selection is None:
            raise EntityNotFoundError(f"Selection with identity '{identity}' was not found.")
        return selection

    def list_by_market(self, market_identity: str) -> list[Selection]:
        """Retrieve all selections associated with a given market."""
        query = """
        SELECT s.identity, s.name, s.selection_id, s.odds,
               m.identity AS market_identity, m.name AS market_name,
               m.fixture_id, m.market_id, m.line
        FROM selections s
        JOIN markets m ON s.market_identity = m.identity
        WHERE s.market_identity = ?
        ORDER BY s.name ASC;
        """
        cursor = self.connection.execute(query, (market_identity.strip(),))
        return [self._row_to_selection(row) for row in cursor.fetchall()]

    def delete(self, identity: str) -> bool:
        """Delete a Selection by its identity.

        Returns True if deleted, False if not found.
        """
        query = "DELETE FROM selections WHERE identity = ?;"
        try:
            with self.connection:
                cursor = self.connection.execute(query, (identity.strip(),))
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Selection", identity)
            return False
