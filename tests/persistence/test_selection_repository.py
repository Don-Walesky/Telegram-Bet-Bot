"""Tests for SelectionRepository."""

from decimal import Decimal
import sqlite3
import pytest

from telegram_bet_bot.domain import Fixture, League, Market, Odds, Selection, Sport
from telegram_bet_bot.persistence.exceptions import (
    DuplicateEntityError,
    EntityNotFoundError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SelectionRepository,
    SportRepository,
)


def _seed_market(
    conn: sqlite3.Connection,
    sport: Sport,
    league: League,
    fixture: Fixture,
    market: Market,
) -> None:
    SportRepository(conn).save(sport)
    LeagueRepository(conn).save(league)
    FixtureRepository(conn).save(fixture)
    MarketRepository(conn).save(market)


def test_selection_save_and_retrieve_with_odds(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
    sample_selection: Selection,
) -> None:
    """Verify persisting a Selection preserves its identity, parent Market, and Decimal Odds."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    selection_repo.save(sample_selection)

    retrieved = selection_repo.get_by_identity(sample_selection.identity)
    assert retrieved is not None
    assert retrieved == sample_selection
    assert retrieved.name == "Over 2.5 Goals"
    assert retrieved.selection_id == "SEL-OU-OVER"
    assert retrieved.market.identity == sample_market.identity
    assert retrieved.odds is not None
    assert retrieved.odds == Odds("1.95")
    assert retrieved.odds.value == Decimal("1.95")
    assert isinstance(retrieved.odds.value, Decimal)


def test_selection_null_odds_handling(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
) -> None:
    """Verify selections without odds (odds=None) round-trip properly."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    selection = Selection(
        name="Under 2.5 Goals",
        market=sample_market,
        selection_id="SEL-OU-UNDER",
        odds=None,
    )
    selection_repo.save(selection)

    retrieved = selection_repo.get(selection.identity)
    assert retrieved.odds is None
    assert retrieved.name == "Under 2.5 Goals"
    assert retrieved.market.identity == sample_market.identity


@pytest.mark.parametrize(
    "raw_odds, expected_dec, expected_prob",
    [
        (2.00, Decimal("2"), Decimal("0.5")),
        ("1.25", Decimal("1.25"), Decimal("0.8")),
        ("4.00", Decimal("4.00"), Decimal("0.25")),
        (Decimal("1.50"), Decimal("1.50"), Decimal("1") / Decimal("1.50")),
    ],
)
def test_selection_decimal_odds_preservation(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
    raw_odds: object,
    expected_dec: Decimal,
    expected_prob: Decimal,
) -> None:
    """Verify odds values across representations round-trip and retain implied probability calculation."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    odds_obj = Odds(raw_odds)  # type: ignore[arg-type]
    selection = Selection(
        name=f"Outcome {raw_odds}",
        market=sample_market,
        odds=odds_obj,
    )
    selection_repo.save(selection)

    retrieved = selection_repo.get(selection.identity)
    assert retrieved.odds is not None
    assert retrieved.odds == odds_obj
    assert retrieved.odds.value == expected_dec
    assert retrieved.odds.bookmaker_implied_probability == expected_prob


def test_selection_save_upsert_behavior(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
    sample_selection: Selection,
) -> None:
    """Verify save updates selection attributes (such as changing odds) without duplicate rows."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    selection_repo.save(sample_selection)

    # Odds drift: 1.95 -> 2.10
    updated_selection = Selection(
        name=sample_selection.name,
        market=sample_market,
        selection_id=sample_selection.selection_id,
        odds=Odds("2.10"),
    )
    selection_repo.save(updated_selection)

    retrieved = selection_repo.get(sample_selection.identity)
    assert retrieved.odds == Odds("2.10")
    assert len(selection_repo.list_by_market(sample_market.identity)) == 1


def test_selection_create_duplicate_raises(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
    sample_selection: Selection,
) -> None:
    """Verify create raises DuplicateEntityError when identity already exists."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    selection_repo.create(sample_selection)

    with pytest.raises(DuplicateEntityError, match="Selection with identity 'SEL-OU-OVER' already exists"):
        selection_repo.create(sample_selection)


def test_selection_referencing_nonexistent_market_raises(
    test_conn: sqlite3.Connection,
) -> None:
    """Verify saving a Selection referencing a nonexistent market raises ReferentialIntegrityError."""
    selection_repo = SelectionRepository(test_conn)
    orphan_market = Market(name="Phantom Market", fixture="FIX-PHANTOM")
    selection = Selection(name="Phantom Selection", market=orphan_market)

    with pytest.raises(ReferentialIntegrityError):
        selection_repo.save(selection)


def test_selection_get_missing_raises_entity_not_found(test_conn: sqlite3.Connection) -> None:
    """Verify get raises EntityNotFoundError for missing selection identity."""
    selection_repo = SelectionRepository(test_conn)
    assert selection_repo.get_by_identity("MISSING") is None

    with pytest.raises(EntityNotFoundError, match="Selection with identity 'MISSING' was not found"):
        selection_repo.get("MISSING")


def test_selection_delete(
    test_conn: sqlite3.Connection,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
    sample_market: Market,
    sample_selection: Selection,
) -> None:
    """Verify deleting a selection removes it."""
    _seed_market(test_conn, sample_sport, sample_league, sample_fixture, sample_market)
    selection_repo = SelectionRepository(test_conn)

    selection_repo.save(sample_selection)
    assert selection_repo.delete(sample_selection.identity) is True
    assert selection_repo.get_by_identity(sample_selection.identity) is None
    assert selection_repo.delete(sample_selection.identity) is False
