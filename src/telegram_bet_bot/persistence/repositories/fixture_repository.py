"""Repository for Fixture domain entities."""

from datetime import datetime, timezone
import sqlite3
from typing import Union

from telegram_bet_bot.domain import Fixture, FixtureStatus, League, Sport
from telegram_bet_bot.persistence.exceptions import EntityNotFoundError, PersistenceError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class FixtureRepository(BaseRepository):
    """Persistence repository for Fixture entities."""

    def _serialize_start_time(self, dt: datetime) -> str:
        """Convert a timezone-aware datetime to a canonical UTC ISO-8601 string.

        Raises:
            PersistenceError: If dt is naive.
        """
        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise PersistenceError(
                f"Cannot persist naive datetime: scheduled start time '{dt}' must be timezone-aware."
            )
        return dt.astimezone(timezone.utc).isoformat()

    def _deserialize_start_time(self, raw_str: str) -> datetime:
        """Reconstruct a timezone-aware UTC datetime from an ISO-8601 string.

        Raises:
            PersistenceError: If the stored timestamp is naive or cannot be parsed.
        """
        try:
            dt = datetime.fromisoformat(raw_str)
        except (ValueError, TypeError) as err:
            raise PersistenceError(
                f"Malformed timestamp stored in database: '{raw_str}' cannot be parsed as ISO-8601 datetime."
            ) from err

        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise PersistenceError(
                f"Corrupted database record: stored timestamp '{raw_str}' is naive (lacks timezone offset). "
                "The persistence boundary strictly rejects naive timestamps."
            )
        return dt.astimezone(timezone.utc)

    def save(self, fixture: Fixture) -> None:
        """Persist or update a Fixture entity (deterministic upsert).

        Raises:
            ReferentialIntegrityError: If the associated Sport or League does not exist.
            PersistenceError: If scheduled_start_time is naive.
        """
        start_time_str = self._serialize_start_time(fixture.scheduled_start_time)
        query = """
        INSERT INTO fixtures (
            fixture_id, sport_name, league_identity,
            home_team, away_team, scheduled_start_time, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(fixture_id) DO UPDATE SET
            sport_name = excluded.sport_name,
            league_identity = excluded.league_identity,
            home_team = excluded.home_team,
            away_team = excluded.away_team,
            scheduled_start_time = excluded.scheduled_start_time,
            status = excluded.status;
        """
        try:
            self.connection.execute(
                query,
                (
                    fixture.fixture_id,
                    fixture.sport.name,
                    fixture.league.identity,
                    fixture.home_team,
                    fixture.away_team,
                    start_time_str,
                    fixture.status.value,
                ),
            )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Fixture", fixture.fixture_id)

    def create(self, fixture: Fixture) -> None:
        """Insert a new Fixture entity.

        Raises:
            DuplicateEntityError: If a fixture with the same fixture_id already exists.
            ReferentialIntegrityError: If the associated Sport or League does not exist.
            PersistenceError: If scheduled_start_time is naive.
        """
        start_time_str = self._serialize_start_time(fixture.scheduled_start_time)
        query = """
        INSERT INTO fixtures (
            fixture_id, sport_name, league_identity,
            home_team, away_team, scheduled_start_time, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """
        try:
            self.connection.execute(
                query,
                (
                    fixture.fixture_id,
                    fixture.sport.name,
                    fixture.league.identity,
                    fixture.home_team,
                    fixture.away_team,
                    start_time_str,
                    fixture.status.value,
                ),
            )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Fixture", fixture.fixture_id)

    def _row_to_fixture(self, row: sqlite3.Row) -> Fixture:
        """Map a joined database row to a pure domain Fixture entity."""
        sport = Sport(row["sport_name"])
        league = League(
            name=row["league_name"],
            sport=sport,
            country=row["league_country"],
            league_id=row["league_league_id"],
        )
        scheduled_time = self._deserialize_start_time(row["scheduled_start_time"])
        status = FixtureStatus(row["status"])
        return Fixture(
            fixture_id=row["fixture_id"],
            sport=sport,
            league=league,
            home_team=row["home_team"],
            away_team=row["away_team"],
            scheduled_start_time=scheduled_time,
            status=status,
        )

    def get_by_id(self, fixture_id: str) -> Fixture | None:
        """Retrieve a Fixture by its fixture_id, or None if not found."""
        query = """
        SELECT f.fixture_id, f.home_team, f.away_team, f.scheduled_start_time, f.status,
               s.name AS sport_name,
               l.identity AS league_identity, l.name AS league_name,
               l.country AS league_country, l.league_id AS league_league_id
        FROM fixtures f
        JOIN sports s ON f.sport_name = s.name
        JOIN leagues l ON f.league_identity = l.identity
        WHERE f.fixture_id = ?;
        """
        cursor = self.connection.execute(query, (fixture_id.strip(),))
        row = cursor.fetchone()
        if row is None:
            return None
        return self._row_to_fixture(row)

    def get(self, fixture_id: str) -> Fixture:
        """Retrieve a Fixture by its fixture_id or raise EntityNotFoundError."""
        fixture = self.get_by_id(fixture_id)
        if fixture is None:
            raise EntityNotFoundError(f"Fixture with identity '{fixture_id}' was not found.")
        return fixture

    def list_all(self) -> list[Fixture]:
        """Retrieve all persisted fixtures ordered by kickoff time."""
        query = """
        SELECT f.fixture_id, f.home_team, f.away_team, f.scheduled_start_time, f.status,
               s.name AS sport_name,
               l.identity AS league_identity, l.name AS league_name,
               l.country AS league_country, l.league_id AS league_league_id
        FROM fixtures f
        JOIN sports s ON f.sport_name = s.name
        JOIN leagues l ON f.league_identity = l.identity
        ORDER BY f.scheduled_start_time ASC;
        """
        cursor = self.connection.execute(query)
        return [self._row_to_fixture(row) for row in cursor.fetchall()]

    def list_by_sport(self, sport: Union[Sport, str]) -> list[Fixture]:
        """Retrieve all fixtures for a given sport ordered by kickoff time."""
        sport_name = sport.name if isinstance(sport, Sport) else sport.strip().lower()
        query = """
        SELECT f.fixture_id, f.home_team, f.away_team, f.scheduled_start_time, f.status,
               s.name AS sport_name,
               l.identity AS league_identity, l.name AS league_name,
               l.country AS league_country, l.league_id AS league_league_id
        FROM fixtures f
        JOIN sports s ON f.sport_name = s.name
        JOIN leagues l ON f.league_identity = l.identity
        WHERE s.name = ?
        ORDER BY f.scheduled_start_time ASC;
        """
        cursor = self.connection.execute(query, (sport_name,))
        return [self._row_to_fixture(row) for row in cursor.fetchall()]

    def list_by_league(self, league_identity: str) -> list[Fixture]:
        """Retrieve all fixtures for a given league ordered by kickoff time."""
        query = """
        SELECT f.fixture_id, f.home_team, f.away_team, f.scheduled_start_time, f.status,
               s.name AS sport_name,
               l.identity AS league_identity, l.name AS league_name,
               l.country AS league_country, l.league_id AS league_league_id
        FROM fixtures f
        JOIN sports s ON f.sport_name = s.name
        JOIN leagues l ON f.league_identity = l.identity
        WHERE l.identity = ?
        ORDER BY f.scheduled_start_time ASC;
        """
        cursor = self.connection.execute(query, (league_identity.strip(),))
        return [self._row_to_fixture(row) for row in cursor.fetchall()]

    def list_by_status(self, status: Union[FixtureStatus, str]) -> list[Fixture]:
        """Retrieve all fixtures matching a specific lifecycle status."""
        status_val = status.value if isinstance(status, FixtureStatus) else status.strip().upper()
        query = """
        SELECT f.fixture_id, f.home_team, f.away_team, f.scheduled_start_time, f.status,
               s.name AS sport_name,
               l.identity AS league_identity, l.name AS league_name,
               l.country AS league_country, l.league_id AS league_league_id
        FROM fixtures f
        JOIN sports s ON f.sport_name = s.name
        JOIN leagues l ON f.league_identity = l.identity
        WHERE f.status = ?
        ORDER BY f.scheduled_start_time ASC;
        """
        cursor = self.connection.execute(query, (status_val,))
        return [self._row_to_fixture(row) for row in cursor.fetchall()]

    def delete(self, fixture_id: str) -> bool:
        """Delete a Fixture by its fixture_id.

        Returns True if deleted, False if not found.
        Cascades deletion to associated markets and selections.
        """
        query = "DELETE FROM fixtures WHERE fixture_id = ?;"
        try:
            cursor = self.connection.execute(query, (fixture_id.strip(),))
            return cursor.rowcount > 0
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "Fixture", fixture_id)
            return False
