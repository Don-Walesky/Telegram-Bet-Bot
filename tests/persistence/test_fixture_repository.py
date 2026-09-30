"""Tests for FixtureRepository."""

from datetime import datetime, timedelta, timezone
import sqlite3
import pytest

from telegram_bet_bot.domain import (
    BASKETBALL,
    FOOTBALL,
    Fixture,
    FixtureStatus,
    League,
    Sport,
)
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    PersistenceError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    SportRepository,
)


def _seed_sport_and_league(
    conn: sqlite3.Connection,
    sport: Sport,
    league: League,
) -> None:
    SportRepository(conn).save(sport)
    LeagueRepository(conn).save(league)


def test_fixture_save_and_retrieve_all_fields(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify persisting and retrieving a Fixture reconstructs all domain fields and relationships."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    fixture_repo.save(sample_fixture)

    retrieved = fixture_repo.get_by_id(sample_fixture.fixture_id)
    assert retrieved is not None
    assert retrieved == sample_fixture
    assert retrieved.fixture_id == sample_fixture.fixture_id
    assert retrieved.sport == sample_sport
    assert retrieved.league == sample_league
    assert retrieved.home_team == "Arsenal"
    assert retrieved.away_team == "Chelsea"
    assert retrieved.scheduled_start_time == sample_fixture.scheduled_start_time
    assert retrieved.status == FixtureStatus.SCHEDULED
    assert retrieved.is_unstarted is True


def test_fixture_timezone_aware_datetime_round_trip(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify timezone-aware datetimes with non-UTC offsets preserve the exact instant in UTC."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    # 17:00 at UTC+2 is identical to 15:00 UTC
    offset_tz = timezone(timedelta(hours=2))
    start_time = datetime(2026, 10, 15, 17, 0, tzinfo=offset_tz)

    fixture = Fixture(
        fixture_id="FIX-TZ-TEST",
        sport=sample_sport,
        league=sample_league,
        home_team="Real Madrid",
        away_team="Barcelona",
        scheduled_start_time=start_time,
    )
    fixture_repo.save(fixture)

    retrieved = fixture_repo.get("FIX-TZ-TEST")
    assert retrieved.scheduled_start_time.tzinfo is not None
    # Compare instants (datetime equality checks matching timestamps)
    assert retrieved.scheduled_start_time == start_time
    assert retrieved.scheduled_start_time.tzinfo == timezone.utc


def test_fixture_naive_datetime_rejected_at_persistence_boundary(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify naive datetimes without timezone information are rejected by the repository."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    naive_dt = datetime(2026, 10, 15, 15, 0)
    with pytest.raises(PersistenceError, match="must be timezone-aware"):
        # Use object.__new__ to simulate a malformed/bypassed object
        raw_fix = object.__new__(Fixture)
        object.__setattr__(raw_fix, "fixture_id", "FIX-NAIVE")
        object.__setattr__(raw_fix, "sport", sample_sport)
        object.__setattr__(raw_fix, "league", sample_league)
        object.__setattr__(raw_fix, "home_team", "A")
        object.__setattr__(raw_fix, "away_team", "B")
        object.__setattr__(raw_fix, "scheduled_start_time", naive_dt)
        object.__setattr__(raw_fix, "status", FixtureStatus.SCHEDULED)
        fixture_repo.save(raw_fix)


def test_corrupted_database_naive_timestamp_rejected_on_read(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify corrupted database records with naive timestamps are rejected when read.

    Deliberately inserts a naive ISO-8601 timestamp string directly into the fixtures table
    (bypassing repository write validation) and confirms FixtureRepository raises PersistenceError.
    """
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    # Insert a corrupted row with a naive timestamp (no 'Z' or offset like '+00:00')
    test_conn.execute(
        """
        INSERT INTO fixtures (
            fixture_id, sport_name, league_identity,
            home_team, away_team, scheduled_start_time, status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?);
        """,
        (
            "FIX-CORRUPT-TS",
            sample_sport.name,
            sample_league.identity,
            "Arsenal",
            "Chelsea",
            "2026-10-15T15:00:00",
            "SCHEDULED",
        ),
    )

    with pytest.raises(PersistenceError, match="naive"):
        fixture_repo.get("FIX-CORRUPT-TS")

    with pytest.raises(PersistenceError, match="naive"):
        fixture_repo.get_by_id("FIX-CORRUPT-TS")


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
def test_fixture_status_round_trip(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    status: FixtureStatus,
    expected_unstarted: bool,
) -> None:
    """Verify all FixtureStatus values round-trip accurately and preserve is_unstarted behavior."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    fix_id = f"FIX-STATUS-{status.value}"
    fixture = Fixture(
        fixture_id=fix_id,
        sport=sample_sport,
        league=sample_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        status=status,
    )
    fixture_repo.save(fixture)

    retrieved = fixture_repo.get(fix_id)
    assert retrieved.status == status
    assert retrieved.is_unstarted is expected_unstarted


def test_fixture_save_upsert_updates_record(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify save updates fixture attributes (e.g. status transition) without creating duplicates."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    fixture_repo.save(sample_fixture)

    updated_fixture = Fixture(
        fixture_id=sample_fixture.fixture_id,
        sport=sample_sport,
        league=sample_league,
        home_team=sample_fixture.home_team,
        away_team=sample_fixture.away_team,
        scheduled_start_time=sample_fixture.scheduled_start_time,
        status=FixtureStatus.IN_PLAY,
    )
    fixture_repo.save(updated_fixture)

    retrieved = fixture_repo.get(sample_fixture.fixture_id)
    assert retrieved.status == FixtureStatus.IN_PLAY
    assert len(fixture_repo.list_all()) == 1


def test_fixture_create_duplicate_raises(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify create raises DuplicateEntityError when fixture_id already exists."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    fixture_repo.create(sample_fixture)

    with pytest.raises(DuplicateEntityError, match="Fixture with identity 'FIX-TEST-001' already exists"):
        fixture_repo.create(sample_fixture)


def test_fixture_foreign_key_violations(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify foreign key enforcement when referencing unpersisted sport or league."""
    fixture_repo = FixtureRepository(test_conn)
    start_time = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)

    fixture = Fixture(
        fixture_id="FIX-FK-FAIL",
        sport=sample_sport,
        league=sample_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=start_time,
    )

    # Neither sport nor league is seeded yet
    with pytest.raises(ReferentialIntegrityError):
        fixture_repo.save(fixture)


def test_fixture_list_filters(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
) -> None:
    """Verify listing fixtures by sport, league, and status."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    dt1 = datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 10, 15, 18, 0, tzinfo=timezone.utc)

    f1 = Fixture(
        fixture_id="FIX-1",
        sport=sample_sport,
        league=sample_league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=dt1,
        status=FixtureStatus.SCHEDULED,
    )
    f2 = Fixture(
        fixture_id="FIX-2",
        sport=sample_sport,
        league=sample_league,
        home_team="Liverpool",
        away_team="Everton",
        scheduled_start_time=dt2,
        status=FixtureStatus.FINISHED,
    )

    fixture_repo.save(f1)
    fixture_repo.save(f2)

    assert len(fixture_repo.list_all()) == 2
    assert len(fixture_repo.list_by_sport("football")) == 2
    assert len(fixture_repo.list_by_league("EPL")) == 2
    assert len(fixture_repo.list_by_status(FixtureStatus.SCHEDULED)) == 1
    assert len(fixture_repo.list_by_status("FINISHED")) == 1


def test_fixture_delete_and_cascade(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify deleting a fixture succeeds."""
    _seed_sport_and_league(test_conn, sample_sport, sample_league)
    fixture_repo = FixtureRepository(test_conn)

    fixture_repo.save(sample_fixture)
    assert fixture_repo.delete(sample_fixture.fixture_id) is True
    assert fixture_repo.get_by_id(sample_fixture.fixture_id) is None
    assert fixture_repo.delete(sample_fixture.fixture_id) is False
