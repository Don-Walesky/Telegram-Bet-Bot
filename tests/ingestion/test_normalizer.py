"""Tests for ProviderDataNormalizer converting provider DTOs into pure domain entities."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from telegram_bet_bot.domain import FixtureStatus
from telegram_bet_bot.ingestion.exceptions import NormalizationError
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.normalizer import ProviderDataNormalizer


def test_normalize_sport(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider sport produces a canonical domain Sport."""
    ps = ProviderSport(name="Football", external_id="s1")
    sport = normalizer.normalize_sport(ps)
    assert sport.name == "football"

    with pytest.raises(NormalizationError, match="non-empty string"):
        normalizer.normalize_sport(ProviderSport(name="   "))

    with pytest.raises(NormalizationError):
        normalizer.normalize_sport("not-a-provider-sport")  # type: ignore


def test_normalize_league(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider league preserves associated domain Sport."""
    ps = ProviderSport(name="football")
    sport = normalizer.normalize_sport(ps)

    pl = ProviderLeague(name="Premier League", sport_name="football", country="England", external_id="epl")
    league = normalizer.normalize_league(pl, sport)
    assert league.name == "Premier League"
    assert league.sport == sport
    assert league.country == "England"
    assert league.identity == "epl"

    with pytest.raises(NormalizationError, match="non-empty string"):
        normalizer.normalize_league(ProviderLeague(name="", sport_name="football"), sport)


def test_normalize_fixture_success(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider fixture produces a pure domain Fixture."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="epl-id"), sport)

    pf = ProviderFixture(
        external_id="fix-1",
        sport_name="football",
        league_id="epl-id",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        status="SCHEDULED",
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.fixture_id == "fix-1"
    assert fixture.sport == sport
    assert fixture.league == league
    assert fixture.home_team == "Arsenal"
    assert fixture.away_team == "Chelsea"
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    assert fixture.status == FixtureStatus.SCHEDULED


def test_normalize_fixture_converts_non_utc_offset_to_utc(normalizer: ProviderDataNormalizer) -> None:
    """Verify non-UTC timezone offsets are preserved and converted to UTC."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)

    # 17:00 at UTC+2 is 15:00 UTC
    offset_tz = timezone(timedelta(hours=2))
    start_time = datetime(2026, 10, 15, 17, 0, tzinfo=offset_tz)

    pf = ProviderFixture(
        external_id="fix-tz",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time=start_time,
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    assert fixture.scheduled_start_time.tzinfo == timezone.utc


def test_normalize_fixture_parses_iso_string_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify ISO-8601 strings with offsets are converted to timezone-aware UTC datetimes."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)

    pf = ProviderFixture(
        external_id="fix-iso",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time="2026-10-15T15:00:00+00:00",
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.scheduled_start_time.tzinfo is not None
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)


def test_normalize_fixture_rejects_naive_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify naive datetimes and naive ISO strings are rejected by normalizer."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)

    # 1. Naive Python datetime
    naive_dt = datetime(2026, 10, 15, 15, 0)
    pf1 = ProviderFixture(
        external_id="fix-naive-1",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time=naive_dt,
    )
    with pytest.raises(NormalizationError, match="naive"):
        normalizer.normalize_fixture(pf1, sport, league)

    # 2. Naive ISO-8601 string (no offset, no 'Z')
    pf2 = ProviderFixture(
        external_id="fix-naive-2",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time="2026-10-15T15:00:00",
    )
    with pytest.raises(NormalizationError, match="naive"):
        normalizer.normalize_fixture(pf2, sport, league)


def test_normalize_fixture_rejects_malformed_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify corrupted timestamp strings raise NormalizationError."""
    with pytest.raises(NormalizationError, match="Malformed"):
        normalizer.normalize_start_time("invalid-datetime-string")

    with pytest.raises(NormalizationError, match="empty"):
        normalizer.normalize_start_time("   ")

    with pytest.raises(NormalizationError, match="None"):
        normalizer.normalize_start_time(None)


def test_normalize_fixture_rejects_identical_participants(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizer rejects fixtures where home and away teams are identical."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)

    pf = ProviderFixture(
        external_id="fix-same-teams",
        sport_name="football",
        league_id="l1",
        home_team="Arsenal",
        away_team="Arsenal",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="Home and away participants cannot be identical"):
        normalizer.normalize_fixture(pf, sport, league)


def test_normalize_fixture_rejects_sport_league_mismatch(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizer rejects fixture if sport does not match league's sport."""
    football = normalizer.normalize_sport(ProviderSport(name="football"))
    basketball = normalizer.normalize_sport(ProviderSport(name="basketball"))
    nba_league = normalizer.normalize_league(ProviderLeague(name="NBA", sport_name="basketball"), basketball)

    pf = ProviderFixture(
        external_id="fix-mismatch",
        sport_name="football",
        league_id="nba",
        home_team="A",
        away_team="B",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="does not match fixture sport"):
        normalizer.normalize_fixture(pf, football, nba_league)


def test_normalize_market_and_line(normalizer: ProviderDataNormalizer) -> None:
    """Verify market line normalization preserves Decimal precision and rejects invalid lines."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="f1",
            sport_name="football",
            league_id="l1",
            home_team="A",
            away_team="B",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )

    # Valid market with line
    pm1 = ProviderMarket(name="Total Goals", fixture_external_id="f1", external_id="m1", line=Decimal("2.5"))
    m1 = normalizer.normalize_market(pm1, fixture)
    assert m1.line == Decimal("2.5")
    assert m1.identity == "m1"

    # Valid market with None line
    pm2 = ProviderMarket(name="Match Winner", fixture_external_id="f1", external_id="m2", line=None)
    m2 = normalizer.normalize_market(pm2, fixture)
    assert m2.line is None

    # Invalid non-finite line
    pm_nan = ProviderMarket(name="Bad Market", fixture_external_id="f1", line="NaN")
    with pytest.raises(NormalizationError, match="finite"):
        normalizer.normalize_market(pm_nan, fixture)


def test_normalize_selection_and_odds(normalizer: ProviderDataNormalizer) -> None:
    """Verify selection odds normalization creates valid Odds and rejects invalid values."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="f1",
            sport_name="football",
            league_id="l1",
            home_team="A",
            away_team="B",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )
    market = normalizer.normalize_market(
        ProviderMarket(name="MW", fixture_external_id="f1", external_id="m1"),
        fixture,
    )

    # Valid selection with odds
    ps1 = ProviderSelection(name="Arsenal", market_external_id="m1", external_id="s1", odds=Decimal("2.10"))
    sel1 = normalizer.normalize_selection(ps1, market)
    assert sel1.odds is not None
    assert sel1.odds.decimal_value == Decimal("2.10")
    assert sel1.odds.implied_probability == Decimal("1") / Decimal("2.10")

    # Valid selection with None odds
    ps2 = ProviderSelection(name="Arsenal", market_external_id="m1", external_id="s2", odds=None)
    sel2 = normalizer.normalize_selection(ps2, market)
    assert sel2.odds is None

    # Invalid odds < 1.01
    ps_low = ProviderSelection(name="Bad", market_external_id="m1", odds=Decimal("0.95"))
    with pytest.raises(NormalizationError, match="greater than 1.0"):
        normalizer.normalize_selection(ps_low, market)

    # Invalid non-finite odds
    ps_inf = ProviderSelection(name="Bad", market_external_id="m1", odds="Infinity")
    with pytest.raises(NormalizationError, match="finite"):
        normalizer.normalize_selection(ps_inf, market)
