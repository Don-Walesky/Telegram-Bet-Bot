"""End-to-end integration tests for Phase 4 ingestion pipeline."""

from decimal import Decimal
from telegram_bet_bot.domain import FixtureStatus
from telegram_bet_bot.ingestion.mock_provider import MockSportsDataProvider
from telegram_bet_bot.ingestion.service import FixtureIngestionService
from telegram_bet_bot.persistence import Database
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SelectionRepository,
    SportRepository,
)


def test_end_to_end_ingestion_pipeline(test_db: Database) -> None:
    """Prove Provider -> Normalization -> Domain -> Repositories -> SQLite works end-to-end."""
    provider = MockSportsDataProvider()
    service = FixtureIngestionService(db=test_db, provider=provider)

    # 1. Run full upcoming ingestion
    summary = service.ingest_upcoming_fixtures()
    assert summary.fixtures_count >= 4
    assert len(summary.results) == summary.fixtures_count

    # 2. Open fresh independent connection to temporary SQLite database
    with test_db.connection() as conn:
        sport_repo = SportRepository(conn)
        league_repo = LeagueRepository(conn)
        fixture_repo = FixtureRepository(conn)
        market_repo = MarketRepository(conn)
        selection_repo = SelectionRepository(conn)

        # A. Verify Sports
        football = sport_repo.get("football")
        basketball = sport_repo.get("basketball")
        tennis = sport_repo.get("tennis")
        assert football.name == "football"
        assert basketball.name == "basketball"
        assert tennis.name == "tennis"

        # B. Verify League (canonical internal domain identity)
        epl = league_repo.get("football:premier_league")
        assert epl.name == "Premier League"
        assert epl.sport == football
        assert epl.country == "England"
        assert epl.identity != "league-epl-01"

        # C. Verify Fixture (canonical internal domain identity)
        expected_fix_id = "football:premier_league:arsenal_vs_chelsea:20261120"
        fixture = fixture_repo.get(expected_fix_id)
        assert fixture.sport == football
        assert fixture.league == epl
        assert fixture.home_team == "Arsenal"
        assert fixture.away_team == "Chelsea"
        assert fixture.scheduled_start_time.tzinfo is not None
        assert fixture.status == FixtureStatus.SCHEDULED
        assert fixture.is_unstarted is True
        assert fixture.fixture_id != "fix-fb-epl-001"

        # D. Verify Market with Decimal Line
        markets = market_repo.list_by_fixture(expected_fix_id)
        assert len(markets) == 2
        ou_market = next(m for m in markets if m.name == "Total Goals")
        assert ou_market.line == Decimal("2.5")
        assert ou_market.identity != "mkt-fb-epl-001-ou25"
        assert ou_market.identity == f"{expected_fix_id}:total_goals:2.5"

        # E. Verify Selection with Decimal Odds
        selections = selection_repo.list_by_market(ou_market.identity)
        assert len(selections) == 2
        over_sel = next(s for s in selections if s.name == "Over 2.5")
        assert over_sel.odds is not None
        assert over_sel.odds.decimal_value == Decimal("1.80")
        assert over_sel.odds.implied_probability == Decimal("1") / Decimal("1.80")
        assert over_sel.identity != "sel-fb-epl-001-o25"
        assert over_sel.identity == f"{ou_market.identity}:over_2.5"


def test_sport_filtered_ingestion_pipeline(test_db: Database) -> None:
    """Verify selective ingestion for a single sport filter."""
    provider = MockSportsDataProvider()
    service = FixtureIngestionService(db=test_db, provider=provider)

    summary = service.ingest_upcoming_fixtures(sport_name="basketball")
    assert summary.fixtures_count == 1
    assert summary.sports_count == 1

    with test_db.connection() as conn:
        fixtures = FixtureRepository(conn).list_all()
        assert len(fixtures) == 1
        assert fixtures[0].sport.name == "basketball"
        assert fixtures[0].home_team == "Los Angeles Lakers"
        assert fixtures[0].fixture_id == "basketball:nba:los_angeles_lakers_vs_boston_celtics:20261122"
