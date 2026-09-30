"""Tests for SportRepository."""

import sqlite3
import pytest

from telegram_bet_bot.domain import BASKETBALL, FOOTBALL, TENNIS, League, Sport
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import LeagueRepository, SportRepository


def test_sport_save_and_retrieve(test_conn: sqlite3.Connection, sample_sport: Sport) -> None:
    """Verify saving a Sport and retrieving it by canonical identity."""
    repo = SportRepository(test_conn)
    repo.save(sample_sport)

    retrieved = repo.get_by_identity("football")
    assert retrieved is not None
    assert retrieved == sample_sport
    assert retrieved.name == "football"


def test_sport_save_upsert_behavior(test_conn: sqlite3.Connection, sample_sport: Sport) -> None:
    """Verify saving an existing Sport updates the record without creating duplicate rows."""
    repo = SportRepository(test_conn)
    repo.save(sample_sport)
    repo.save(Sport("FOOTBALL"))

    all_sports = repo.list_all()
    assert len(all_sports) == 1
    assert all_sports[0] == sample_sport


def test_sport_create_and_duplicate_error(test_conn: sqlite3.Connection, sample_sport: Sport) -> None:
    """Verify create inserts a new entity and raises DuplicateEntityError on duplicates."""
    repo = SportRepository(test_conn)
    repo.create(sample_sport)

    with pytest.raises(DuplicateEntityError, match="Sport with identity 'football' already exists"):
        repo.create(sample_sport)


def test_sport_get_missing_raises_entity_not_found(test_conn: sqlite3.Connection) -> None:
    """Verify get raises EntityNotFoundError when identity is missing."""
    repo = SportRepository(test_conn)
    assert repo.get_by_identity("nonexistent") is None

    with pytest.raises(EntityNotFoundError, match="Sport with identity 'nonexistent' was not found"):
        repo.get("nonexistent")


def test_sport_list_all_and_exists(test_conn: sqlite3.Connection) -> None:
    """Verify listing all sports and existence checking."""
    repo = SportRepository(test_conn)
    assert repo.exists("football") is False

    repo.save(TENNIS)
    repo.save(BASKETBALL)
    repo.save(FOOTBALL)

    assert repo.exists("football") is True
    assert repo.exists("FOOTBALL") is True
    assert repo.exists("volleyball") is False

    sports = repo.list_all()
    assert len(sports) == 3
    assert [s.name for s in sports] == ["basketball", "football", "tennis"]


def test_sport_delete_and_foreign_key_protection(test_conn: sqlite3.Connection) -> None:
    """Verify deleting unreferenced sport succeeds, but referenced sport raises ReferentialIntegrityError."""
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)

    sport_repo.save(FOOTBALL)
    sport_repo.save(TENNIS)

    # Delete unreferenced sport
    assert sport_repo.delete("tennis") is True
    assert sport_repo.exists("tennis") is False

    # Create league referencing football
    league = League(name="Premier League", sport=FOOTBALL, league_id="EPL")
    league_repo.save(league)

    # Deleting football must fail because EPL references it
    with pytest.raises(ReferentialIntegrityError, match="Cannot persist Sport"):
        sport_repo.delete("football")
