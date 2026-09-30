"""Repository for League domain entities."""

import sqlite3
from typing import Union
from telegram_bet_bot.domain import League, Sport
from telegram_bet_bot.persistence.exceptions import EntityNotFoundError
from telegram_bet_bot.persistence.repositories.base import (
    BaseRepository,
    handle_integrity_error,
)


class LeagueRepository(BaseRepository):
    """Persistence repository for League entities."""

    def save(self, league: League) -> None:
        """Persist or update a League entity (deterministic upsert).

        Raises:
            ReferentialIntegrityError: If the associated Sport does not exist in the database.
        """
        query = """
        INSERT INTO leagues (identity, name, sport_name, country, league_id)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(identity) DO UPDATE SET
            name = excluded.name,
            sport_name = excluded.sport_name,
            country = excluded.country,
            league_id = excluded.league_id;
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        league.identity,
                        league.name,
                        league.sport.name,
                        league.country,
                        league.league_id,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "League", league.identity)

    def create(self, league: League) -> None:
        """Insert a new League entity.

        Raises:
            DuplicateEntityError: If a league with the same identity already exists.
            ReferentialIntegrityError: If the associated Sport does not exist in the database.
        """
        query = """
        INSERT INTO leagues (identity, name, sport_name, country, league_id)
        VALUES (?, ?, ?, ?, ?);
        """
        try:
            with self.connection:
                self.connection.execute(
                    query,
                    (
                        league.identity,
                        league.name,
                        league.sport.name,
                        league.country,
                        league.league_id,
                    ),
                )
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "League", league.identity)

    def get_by_identity(self, identity: str) -> League | None:
        """Retrieve a League entity by its canonical identity, or None if not found."""
        query = """
        SELECT l.identity, l.name, l.country, l.league_id, s.name AS sport_name
        FROM leagues l
        JOIN sports s ON l.sport_name = s.name
        WHERE l.identity = ?;
        """
        cursor = self.connection.execute(query, (identity.strip(),))
        row = cursor.fetchone()
        if row is None:
            return None
        sport = Sport(row["sport_name"])
        return League(
            name=row["name"],
            sport=sport,
            country=row["country"],
            league_id=row["league_id"],
        )

    def get(self, identity: str) -> League:
        """Retrieve a League entity or raise EntityNotFoundError."""
        league = self.get_by_identity(identity)
        if league is None:
            raise EntityNotFoundError(f"League with identity '{identity}' was not found.")
        return league

    def list_all(self) -> list[League]:
        """Retrieve all persisted leagues."""
        query = """
        SELECT l.identity, l.name, l.country, l.league_id, s.name AS sport_name
        FROM leagues l
        JOIN sports s ON l.sport_name = s.name
        ORDER BY s.name ASC, l.name ASC;
        """
        cursor = self.connection.execute(query)
        leagues: list[League] = []
        for row in cursor.fetchall():
            sport = Sport(row["sport_name"])
            leagues.append(
                League(
                    name=row["name"],
                    sport=sport,
                    country=row["country"],
                    league_id=row["league_id"],
                )
            )
        return leagues

    def list_by_sport(self, sport: Union[Sport, str]) -> list[League]:
        """Retrieve all leagues associated with a given sport."""
        sport_name = sport.name if isinstance(sport, Sport) else sport.strip().lower()
        query = """
        SELECT l.identity, l.name, l.country, l.league_id, s.name AS sport_name
        FROM leagues l
        JOIN sports s ON l.sport_name = s.name
        WHERE s.name = ?
        ORDER BY l.name ASC;
        """
        cursor = self.connection.execute(query, (sport_name,))
        leagues: list[League] = []
        for row in cursor.fetchall():
            sp = Sport(row["sport_name"])
            leagues.append(
                League(
                    name=row["name"],
                    sport=sp,
                    country=row["country"],
                    league_id=row["league_id"],
                )
            )
        return leagues

    def delete(self, identity: str) -> bool:
        """Delete a League by identity.

        Returns True if deleted, False if not found.
        Raises ReferentialIntegrityError if fixtures reference this league.
        """
        query = "DELETE FROM leagues WHERE identity = ?;"
        try:
            with self.connection:
                cursor = self.connection.execute(query, (identity.strip(),))
                return cursor.rowcount > 0
        except sqlite3.IntegrityError as err:
            handle_integrity_error(err, "League", identity)
            return False
