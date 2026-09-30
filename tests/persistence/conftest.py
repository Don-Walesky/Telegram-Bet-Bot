"""Pytest fixtures for persistence layer tests."""

from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest

from telegram_bet_bot.domain import (
    FOOTBALL,
    Fixture,
    FixtureStatus,
    League,
    Market,
    Odds,
    Selection,
    Sport,
)
from telegram_bet_bot.persistence import Database


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Provide a freshly initialized SQLite Database instance backed by a temporary file."""
    db_file = tmp_path / "test_app.db"
    db = Database(db_path=db_file)
    db.initialize()
    return db


@pytest.fixture
def test_conn(test_db: Database) -> Iterator[sqlite3.Connection]:
    """Provide an active SQLite connection to the temporary test database."""
    with test_db.connection() as conn:
        yield conn


@pytest.fixture
def sample_sport() -> Sport:
    """Provide a standard Sport instance for persistence tests."""
    return FOOTBALL


@pytest.fixture
def sample_league(sample_sport: Sport) -> League:
    """Provide a standard League instance for persistence tests."""
    return League(
        name="Premier League",
        sport=sample_sport,
        country="England",
        league_id="EPL",
    )


@pytest.fixture
def sample_fixture(sample_sport: Sport, sample_league: League) -> Fixture:
    """Provide a standard Fixture instance for persistence tests."""
    start_time = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    return Fixture(
        fixture_id="FIX-TEST-001",
        sport=sample_sport,
        league=sample_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=start_time,
        status=FixtureStatus.SCHEDULED,
    )


@pytest.fixture
def sample_market(sample_fixture: Fixture) -> Market:
    """Provide a standard Market instance for persistence tests."""
    return Market(
        name="Total Goals Over/Under",
        fixture=sample_fixture,
        market_id="MKT-OU-25",
        line=Decimal("2.5"),
    )


@pytest.fixture
def sample_selection(sample_market: Market) -> Selection:
    """Provide a standard Selection instance for persistence tests."""
    return Selection(
        name="Over 2.5 Goals",
        market=sample_market,
        selection_id="SEL-OU-OVER",
        odds=Odds("1.95"),
    )
