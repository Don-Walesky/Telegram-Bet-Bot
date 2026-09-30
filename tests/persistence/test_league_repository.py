"""Tests for LeagueRepository."""

import sqlite3
import pytest

from telegram_bet_bot.domain import BASKETBALL, FOOTBALL, League, Sport
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import LeagueRepository, SportRepository


def test_league_save_and_retrieve_with_sport(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify saving a League and retrieving it preserves the associated Sport."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(sample_sport)
    league_repo.save(sample_league)

    retrieved = league_repo.get_by_identity("EPL")
    assert retrieved is not None
    assert retrieved == sample_league
    assert retrieved.name == "Premier League"
    assert retrieved.country == "England"
    assert retrieved.league_id == "EPL"
    assert retrieved.identity == "EPL"
    assert retrieved.sport == sample_sport


def test_league_default_identity_derivation(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
) -> None:
    """Verify leagues without explicit league_id persist and retrieve with derived identity."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(sample_sport)
    league = League(name="La Liga", sport=sample_sport, country="Spain")
    league_repo.save(league)

    retrieved = league_repo.get_by_identity("football:la_liga")
    assert retrieved is not None
    assert retrieved == league
    assert retrieved.identity == "football:la_liga"
    assert retrieved.country == "Spain"
    assert retrieved.league_id is None


def test_league_save_upsert_behavior(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify saving an updated League modifies attributes without adding duplicate rows."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(sample_sport)
    league_repo.save(sample_league)

    updated_league = League(
        name="English Premier League",
        sport=sample_sport,
        country="UK",
        league_id="EPL",
    )
    league_repo.save(updated_league)

    leagues = league_repo.list_all()
    assert len(leagues) == 1
    assert leagues[0].name == "English Premier League"
    assert leagues[0].country == "UK"


def test_league_create_duplicate_raises(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify create raises DuplicateEntityError when identity already exists."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(sample_sport)
    league_repo.create(sample_league)

    with pytest.raises(DuplicateEntityError, match="League with identity 'EPL' already exists"):
        league_repo.create(sample_league)


def test_league_foreign_key_violation_raises(
    test_conn: sqlite3.Connection,
) -> None:
    """Verify saving a League for a nonexistent sport raises ReferentialIntegrityError."""
    league_repo = LeagueRepository(test_conn)
    unpersisted_sport = Sport("rugby")
    league = League(name="Top 14", sport=unpersisted_sport, league_id="TOP14")

    with pytest.raises(ReferentialIntegrityError, match="Cannot persist League 'TOP14'"):
        league_repo.save(league)


def test_league_get_missing_raises_entity_not_found(test_conn: sqlite3.Connection) -> None:
    """Verify get raises EntityNotFoundError for missing identity."""
    league_repo = LeagueRepository(test_conn)
    assert league_repo.get_by_identity("MISSING") is None

    with pytest.raises(EntityNotFoundError, match="League with identity 'MISSING' was not found"):
        league_repo.get("MISSING")


def test_league_list_by_sport(test_conn: sqlite3.Connection) -> None:
    """Verify listing leagues filtered by sport."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(FOOTBALL)
    sport_repo.save(BASKETBALL)

    league_repo.save(League(name="Premier League", sport=FOOTBALL, league_id="EPL"))
    league_repo.save(League(name="Serie A", sport=FOOTBALL, league_id="SERIEA"))
    league_repo.save(League(name="NBA", sport=BASKETBALL, league_id="NBA"))

    football_leagues = league_repo.list_by_sport(FOOTBALL)
    assert len(football_leagues) == 2
    assert [l.identity for l in football_leagues] == ["EPL", "SERIEA"]

    basketball_leagues = league_repo.list_by_sport("basketball")
    assert len(basketball_leagues) == 1
    assert basketball_leagues[0].identity == "NBA"
