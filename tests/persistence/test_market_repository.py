"""Tests for MarketRepository."""

from decimal import Decimal
import sqlite3
import pytest

from telegram_bet_bot.domain import Fixture, League, Market, Sport
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SportRepository,
)


def _seed_fixture(
    conn: sqlite3.Connection,
    sport: Sport,
    league: League,
    fixture: Fixture,
) -> None:
    SportRepository(conn).save(sport)
    LeagueRepository(conn).save(league)
    FixtureRepository(conn).save(fixture)


def test_market_save_and_retrieve_with_decimal_line(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
) -> None:
    """Verify saving a Market preserves its identity, fixture link, and Decimal line losslessly."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market_repo.save(sample_market)

    retrieved = market_repo.get_by_identity(sample_market.identity)
    assert retrieved is not None
    assert retrieved == sample_market
    assert retrieved.name == sample_market.name
    assert retrieved.fixture_id == sample_fixture.fixture_id
    assert retrieved.market_id == "MKT-OU-25"
    assert retrieved.line == Decimal("2.5")
    assert isinstance(retrieved.line, Decimal)


def test_market_null_line_handling(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify markets with no line (line=None, e.g. Match Winner) round-trip with line=None."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market = Market(
        name="Match Winner",
        fixture=sample_fixture,
        market_id="MKT-1X2",
        line=None,
    )
    market_repo.save(market)

    retrieved = market_repo.get(market.identity)
    assert retrieved.line is None
    assert retrieved.name == "Match Winner"
    assert retrieved.fixture_id == sample_fixture.fixture_id


@pytest.mark.parametrize(
    "raw_line, expected_dec",
    [
        (2.5, Decimal("2.5")),
        (-1.5, Decimal("-1.5")),
        (0, Decimal("0")),
        (" 1.75 ", Decimal("1.75")),
        (Decimal("3.5"), Decimal("3.5")),
    ],
)
def test_market_decimal_line_preservation(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    raw_line: object,
    expected_dec: Decimal,
) -> None:
    """Verify diverse line values are stored and retrieved losslessly as exact Decimals."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market = Market(
        name="Handicap",
        fixture=sample_fixture,
        line=raw_line,  # type: ignore[arg-type]
    )
    market_repo.save(market)

    retrieved = market_repo.get(market.identity)
    assert retrieved.line == expected_dec
    assert isinstance(retrieved.line, Decimal)


def test_market_save_upsert_behavior(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
) -> None:
    """Verify save updates market attributes without adding duplicate rows."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market_repo.save(sample_market)

    updated_market = Market(
        name="Total Goals O/U (Updated)",
        fixture=sample_fixture,
        market_id=sample_market.market_id,
        line=sample_market.line,
    )
    market_repo.save(updated_market)

    retrieved = market_repo.get(sample_market.identity)
    assert retrieved.name == "Total Goals O/U (Updated)"
    assert len(market_repo.list_by_fixture(sample_fixture.fixture_id)) == 1


def test_market_create_duplicate_raises(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
) -> None:
    """Verify create raises DuplicateEntityError when identity already exists."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market_repo.create(sample_market)

    with pytest.raises(DuplicateEntityError, match="Market with identity 'MKT-OU-25' already exists"):
        market_repo.create(sample_market)


def test_market_referencing_nonexistent_fixture_raises(
    test_conn: sqlite3.Connection,
) -> None:
    """Verify saving a Market referencing a nonexistent fixture raises ReferentialIntegrityError."""
    market_repo = MarketRepository(test_conn)
    orphan_market = Market(name="Match Winner", fixture="NONEXISTENT-FIX")

    with pytest.raises(ReferentialIntegrityError):
        market_repo.save(orphan_market)


def test_market_get_missing_raises_entity_not_found(test_conn: sqlite3.Connection) -> None:
    """Verify get raises EntityNotFoundError for missing market identity."""
    market_repo = MarketRepository(test_conn)
    assert market_repo.get_by_identity("MISSING") is None

    with pytest.raises(EntityNotFoundError, match="Market with identity 'MISSING' was not found"):
        market_repo.get("MISSING")


def test_market_delete(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
) -> None:
    """Verify deleting a market removes it."""
    _seed_fixture(test_conn, sample_sport, sample_league, sample_fixture)
    market_repo = MarketRepository(test_conn)

    market_repo.save(sample_market)
    assert market_repo.delete(sample_market.identity) is True
    assert market_repo.get_by_identity(sample_market.identity) is None
    assert market_repo.delete(sample_market.identity) is False
