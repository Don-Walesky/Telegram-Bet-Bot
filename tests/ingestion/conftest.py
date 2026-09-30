"""Pytest fixtures for Phase 4 ingestion tests."""

from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import sqlite3
import pytest

from telegram_bet_bot.ingestion.mock_provider import MockSportsDataProvider
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderFixtureBundle,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.normalizer import ProviderDataNormalizer
from telegram_bet_bot.persistence import Database


@pytest.fixture
def test_db(tmp_path: Path) -> Database:
    """Provide a fresh, temporary SQLite Database with initialized schema."""
    db_file = tmp_path / "test_ingestion.db"
    db = Database(db_path=db_file)
    db.initialize()
    return db


@pytest.fixture
def test_conn(test_db: Database):
    """Provide an active connection to the temporary database."""
    with test_db.connection() as conn:
        yield conn


@pytest.fixture
def mock_provider() -> MockSportsDataProvider:
    """Provide a clean MockSportsDataProvider instance."""
    return MockSportsDataProvider()


@pytest.fixture
def normalizer() -> ProviderDataNormalizer:
    """Provide a ProviderDataNormalizer instance."""
    return ProviderDataNormalizer()


@pytest.fixture
def sample_bundle() -> ProviderFixtureBundle:
    """Provide a standalone valid ProviderFixtureBundle for testing."""
    sport = ProviderSport(name="football", external_id="ext-sport-1")
    league = ProviderLeague(
        name="Champions League",
        sport_name="football",
        country="Europe",
        external_id="ext-league-1",
    )
    fixture = ProviderFixture(
        external_id="ext-fix-100",
        sport_name="football",
        league_id="ext-league-1",
        home_team="Bayern Munich",
        away_team="Real Madrid",
        start_time=datetime(2026, 12, 1, 20, 0, tzinfo=timezone.utc),
        status="SCHEDULED",
    )
    market = ProviderMarket(
        name="Match Winner",
        fixture_external_id="ext-fix-100",
        external_id="ext-mkt-100-mw",
        line=None,
    )
    sel_home = ProviderSelection(
        name="Bayern Munich",
        market_external_id="ext-mkt-100-mw",
        external_id="ext-sel-100-h",
        odds=Decimal("2.40"),
    )
    sel_away = ProviderSelection(
        name="Real Madrid",
        market_external_id="ext-mkt-100-mw",
        external_id="ext-sel-100-a",
        odds=Decimal("2.90"),
    )

    return ProviderFixtureBundle(
        fixture=fixture,
        sport=sport,
        league=league,
        markets=[market],
        selections=[sel_home, sel_away],
    )
