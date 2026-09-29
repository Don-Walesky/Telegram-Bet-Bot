"""Unit tests for Fixture entity and FixtureStatus enum."""

from datetime import datetime, timezone, timedelta
import pytest
from telegram_bet_bot.domain import (
    BASKETBALL,
    FOOTBALL,
    DomainValidationError,
    Fixture,
    FixtureStatus,
    League,
)


@pytest.fixture
def valid_league() -> League:
    """Provide a standard league fixture for tests."""
    return League(name="Premier League", sport=FOOTBALL, country="England", league_id="EPL")


@pytest.fixture
def valid_start_time() -> datetime:
    """Provide a valid timezone-aware kickoff time."""
    return datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)


def test_fixture_valid_construction(valid_league: League, valid_start_time: datetime) -> None:
    """Verify normal Fixture construction with default and explicit status."""
    fixture = Fixture(
        fixture_id="FIX-101",
        sport=FOOTBALL,
        league=valid_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=valid_start_time,
    )
    assert fixture.fixture_id == "FIX-101"
    assert fixture.sport == FOOTBALL
    assert fixture.league == valid_league
    assert fixture.home_team == "Arsenal"
    assert fixture.away_team == "Chelsea"
    assert fixture.scheduled_start_time == valid_start_time
    assert fixture.status == FixtureStatus.SCHEDULED
    assert fixture.is_unstarted is True
    assert str(fixture) == "Arsenal vs Chelsea (Premier League)"


@pytest.mark.parametrize("invalid_id", ["", "   ", None, 101])
def test_fixture_invalid_id_raises(
    invalid_id: object, valid_league: League, valid_start_time: datetime
) -> None:
    """Verify empty or non-string fixture_id raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Fixture identity must be a non-empty string"):
        Fixture(
            fixture_id=invalid_id,  # type: ignore[arg-type]
            sport=FOOTBALL,
            league=valid_league,
            home_team="Arsenal",
            away_team="Chelsea",
            scheduled_start_time=valid_start_time,
        )


@pytest.mark.parametrize("home, away", [
    ("Arsenal", "Arsenal"),
    ("Arsenal", "arsenal"),
    ("  Arsenal  ", "arsenal"),
    ("Chelsea FC", "chelsea fc"),
])
def test_fixture_identical_participants_raises(
    home: str, away: str, valid_league: League, valid_start_time: datetime
) -> None:
    """Verify identical home and away participants (case-insensitive) raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Home and away participants cannot be identical"):
        Fixture(
            fixture_id="FIX-1",
            sport=FOOTBALL,
            league=valid_league,
            home_team=home,
            away_team=away,
            scheduled_start_time=valid_start_time,
        )


@pytest.mark.parametrize("empty_team", ["", "   ", None])
def test_fixture_empty_participants_raises(
    empty_team: object, valid_league: League, valid_start_time: datetime
) -> None:
    """Verify that empty or non-string participant names are rejected."""
    with pytest.raises(DomainValidationError, match="participant must be a non-empty string"):
        Fixture(
            fixture_id="FIX-1",
            sport=FOOTBALL,
            league=valid_league,
            home_team=empty_team,  # type: ignore[arg-type]
            away_team="Chelsea",
            scheduled_start_time=valid_start_time,
        )


def test_fixture_mismatched_sport_raises(valid_league: League, valid_start_time: datetime) -> None:
    """Verify that a fixture sport differing from the league sport raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="does not match fixture sport"):
        Fixture(
            fixture_id="FIX-1",
            sport=BASKETBALL,  # Mismatch: league is FOOTBALL
            league=valid_league,
            home_team="Lakers",
            away_team="Celtics",
            scheduled_start_time=valid_start_time,
        )


def test_fixture_naive_datetime_rejected(valid_league: League) -> None:
    """Verify that naive datetimes (lacking timezone information) are strictly rejected."""
    naive_dt = datetime(2026, 10, 15, 15, 0)  # No tzinfo
    with pytest.raises(DomainValidationError, match="must be a timezone-aware datetime"):
        Fixture(
            fixture_id="FIX-1",
            sport=FOOTBALL,
            league=valid_league,
            home_team="Arsenal",
            away_team="Chelsea",
            scheduled_start_time=naive_dt,
        )


def test_fixture_non_datetime_rejected(valid_league: League) -> None:
    """Verify non-datetime start time raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Scheduled start time must be a datetime"):
        Fixture(
            fixture_id="FIX-1",
            sport=FOOTBALL,
            league=valid_league,
            home_team="Arsenal",
            away_team="Chelsea",
            scheduled_start_time="2026-10-15T15:00:00Z",  # type: ignore[arg-type]
        )


@pytest.mark.parametrize(
    "status, expected_unstarted",
    [
        (FixtureStatus.SCHEDULED, True),
        (FixtureStatus.IN_PLAY, False),
        (FixtureStatus.FINISHED, False),
        (FixtureStatus.POSTPONED, False),
        (FixtureStatus.CANCELLED, False),
    ],
)
def test_fixture_status_and_is_unstarted(
    status: FixtureStatus,
    expected_unstarted: bool,
    valid_league: League,
    valid_start_time: datetime,
) -> None:
    """Verify is_unstarted behavior across all lifecycle fixture statuses."""
    fixture = Fixture(
        fixture_id="FIX-STATUS",
        sport=FOOTBALL,
        league=valid_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=valid_start_time,
        status=status,
    )
    assert fixture.status == status
    assert fixture.is_unstarted is expected_unstarted
    assert status.is_unstarted is expected_unstarted


def test_fixture_value_semantics(valid_league: League, valid_start_time: datetime) -> None:
    """Verify equality and hash behavior for Fixture instances."""
    f1 = Fixture(
        fixture_id="FIX-1",
        sport=FOOTBALL,
        league=valid_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=valid_start_time,
    )
    f2 = Fixture(
        fixture_id="FIX-1",
        sport=FOOTBALL,
        league=valid_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=valid_start_time,
    )
    f3 = Fixture(
        fixture_id="FIX-2",
        sport=FOOTBALL,
        league=valid_league,
        home_team="Liverpool",
        away_team="Everton",
        scheduled_start_time=valid_start_time,
    )
    assert f1 == f2
    assert f1 != f3
    assert hash(f1) == hash(f2)
    assert len({f1, f2, f3}) == 2
