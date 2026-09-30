"""Comprehensive round-trip persistence tests for all Phase 2 domain entities."""

from datetime import datetime, timezone
from decimal import Decimal
import sqlite3

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
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SelectionRepository,
    SportRepository,
)


def test_complete_domain_hierarchy_round_trip(test_db: Database, test_conn: sqlite3.Connection) -> None:
    """Verify end-to-end round trip for the entire domain entity graph:

    Sport -> League -> Fixture -> Market -> Selection
    Validates:
    - Exact instant preservation of timezone-aware datetimes
    - Lossless Decimal line and odds preservation
    - FixtureStatus preservation
    - Bookmaker implied probability calculation after retrieval
    - Domain equality and immutability invariants
    """
    sport_repo = SportRepository(test_conn)
    league_repo = LeagueRepository(test_conn)
    fixture_repo = FixtureRepository(test_conn)
    market_repo = MarketRepository(test_conn)
    selection_repo = SelectionRepository(test_conn)

    # 1. Sport
    sport = Sport("football")
    sport_repo.save(sport)
    retrieved_sport = sport_repo.get(sport.name)
    assert retrieved_sport == sport
    assert retrieved_sport.name == "football"

    # 2. League
    league = League(name="Premier League", sport=retrieved_sport, country="England", league_id="EPL")
    league_repo.save(league)
    retrieved_league = league_repo.get(league.identity)
    assert retrieved_league == league
    assert retrieved_league.sport == sport
    assert retrieved_league.identity == "EPL"

    # 3. Fixture
    kickoff = datetime(2026, 11, 25, 20, 0, tzinfo=timezone.utc)
    fixture = Fixture(
        fixture_id="FIX-UCL-2026",
        sport=retrieved_sport,
        league=retrieved_league,
        home_team="Arsenal",
        away_team="Bayern Munich",
        scheduled_start_time=kickoff,
        status=FixtureStatus.SCHEDULED,
    )
    fixture_repo.save(fixture)
    retrieved_fixture = fixture_repo.get(fixture.fixture_id)
    assert retrieved_fixture == fixture
    assert retrieved_fixture.scheduled_start_time == kickoff
    assert retrieved_fixture.scheduled_start_time.tzinfo == timezone.utc
    assert retrieved_fixture.status == FixtureStatus.SCHEDULED
    assert retrieved_fixture.is_unstarted is True
    assert retrieved_fixture.league.sport == retrieved_sport

    # 4. Market
    market = Market(
        name="Both Teams To Score",
        fixture=retrieved_fixture,
        market_id="MKT-BTTS-01",
        line=None,
    )
    market_repo.save(market)
    retrieved_market = market_repo.get(market.identity)
    assert retrieved_market == market
    assert retrieved_market.fixture_id == fixture.fixture_id
    assert retrieved_market.line is None

    # Market with Decimal Line
    ou_market = Market(
        name="Total Goals",
        fixture=retrieved_fixture,
        market_id="MKT-TOTAL-25",
        line=Decimal("2.5"),
    )
    market_repo.save(ou_market)
    retrieved_ou = market_repo.get(ou_market.identity)
    assert retrieved_ou == ou_market
    assert retrieved_ou.line == Decimal("2.5")
    assert isinstance(retrieved_ou.line, Decimal)

    # 5. Selection
    selection = Selection(
        name="BTTS Yes",
        market=retrieved_market,
        selection_id="SEL-BTTS-YES",
        odds=Odds("1.75"),
    )
    selection_repo.save(selection)
    retrieved_selection = selection_repo.get(selection.identity)
    assert retrieved_selection == selection
    assert retrieved_selection.market == market
    assert retrieved_selection.odds == Odds("1.75")
    assert retrieved_selection.odds.value == Decimal("1.75")
    assert retrieved_selection.odds.bookmaker_implied_probability == Decimal(1) / Decimal("1.75")
