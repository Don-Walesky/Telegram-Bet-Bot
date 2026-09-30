"""Tests for the SportsDataProvider protocol and MockSportsDataProvider."""

import pytest

from telegram_bet_bot.ingestion.exceptions import (
    MalformedProviderDataError,
    ProviderUnavailableError,
)
from telegram_bet_bot.ingestion.mock_provider import MockSportsDataProvider
from telegram_bet_bot.ingestion.provider import SportsDataProvider


def test_mock_provider_implements_protocol() -> None:
    """Verify MockSportsDataProvider satisfies the SportsDataProvider protocol."""
    provider = MockSportsDataProvider()
    assert isinstance(provider, SportsDataProvider)


def test_mock_provider_returns_deterministic_sports() -> None:
    """Verify mock provider returns consistent, valid sports."""
    provider = MockSportsDataProvider()
    sports = provider.get_sports()
    sport_names = {s.name for s in sports}

    assert len(sports) >= 3
    assert "football" in sport_names
    assert "basketball" in sport_names
    assert "tennis" in sport_names


def test_mock_provider_returns_leagues_and_filters() -> None:
    """Verify mock provider supplies leagues and respects sport filters."""
    provider = MockSportsDataProvider()
    all_leagues = provider.get_leagues()
    assert len(all_leagues) >= 4

    football_leagues = provider.get_leagues(sport_name="football")
    assert len(football_leagues) >= 2
    assert all(l.sport_name == "football" for l in football_leagues)

    nba_leagues = provider.get_leagues(sport_name="basketball")
    assert len(nba_leagues) == 1
    assert nba_leagues[0].name == "NBA"


def test_mock_provider_returns_fixtures_and_filters() -> None:
    """Verify mock provider supplies fixtures and filters properly."""
    provider = MockSportsDataProvider()
    all_fixtures = provider.get_fixtures()
    assert len(all_fixtures) >= 4

    tennis_fixtures = provider.get_fixtures(sport_name="tennis")
    assert len(tennis_fixtures) == 1
    assert tennis_fixtures[0].home_team == "Carlos Alcaraz"

    epl_fixtures = provider.get_fixtures(league_id="league-epl-01")
    assert len(epl_fixtures) == 1
    assert epl_fixtures[0].home_team == "Arsenal"


def test_mock_provider_returns_markets_and_selections() -> None:
    """Verify mock provider supplies markets and associated selections."""
    provider = MockSportsDataProvider()
    markets = provider.get_markets("fix-fb-epl-001")
    assert len(markets) == 2

    mkt_ids = {m.external_id for m in markets}
    assert "mkt-fb-epl-001-1x2" in mkt_ids

    selections = provider.get_selections("mkt-fb-epl-001-1x2")
    assert len(selections) == 3
    sel_names = {s.name for s in selections}
    assert sel_names == {"Arsenal", "Draw", "Chelsea"}


def test_mock_provider_returns_fixture_bundle() -> None:
    """Verify mock provider supplies a complete hierarchical fixture bundle."""
    provider = MockSportsDataProvider()
    bundle = provider.get_fixture_bundle("fix-fb-epl-001")
    assert bundle is not None
    assert bundle.fixture.external_id == "fix-fb-epl-001"
    assert bundle.sport.name == "football"
    assert bundle.league.name == "Premier League"
    assert len(bundle.markets) == 2
    assert len(bundle.selections) == 5

    missing_bundle = provider.get_fixture_bundle("nonexistent-fixture")
    assert missing_bundle is None


def test_mock_provider_upcoming_fixture_bundles() -> None:
    """Verify mock provider returns all upcoming fixture bundles."""
    provider = MockSportsDataProvider()
    bundles = provider.get_upcoming_fixture_bundles()
    assert len(bundles) >= 4

    football_bundles = provider.get_upcoming_fixture_bundles(sport_name="football")
    assert len(football_bundles) == 2
    assert all(b.sport.name == "football" for b in football_bundles)


def test_mock_provider_failure_injection() -> None:
    """Verify mock provider simulates service outage and malformed payloads."""
    unavailable_provider = MockSportsDataProvider(simulate_unavailable=True)
    with pytest.raises(ProviderUnavailableError, match="service unreachable"):
        unavailable_provider.get_sports()

    with pytest.raises(ProviderUnavailableError, match="service unreachable"):
        unavailable_provider.get_upcoming_fixture_bundles()

    malformed_provider = MockSportsDataProvider(simulate_malformed=True)
    with pytest.raises(MalformedProviderDataError, match="malformed payload"):
        malformed_provider.get_sports()

    with pytest.raises(MalformedProviderDataError, match="malformed payload"):
        malformed_provider.get_fixture_bundle("fix-fb-epl-001")
