"""Unit tests for Selection domain entity."""

import pytest
from telegram_bet_bot.domain import (
    DomainValidationError,
    Market,
    Odds,
    Selection,
)


@pytest.fixture
def sample_market() -> Market:
    """Provide a standard market instance for tests."""
    return Market(name="Match Winner", fixture="FIX-300", market_id="MKT-300")


def test_selection_valid_construction(sample_market: Market) -> None:
    """Verify normal Selection construction with parent Market and optional Odds."""
    odds = Odds("1.85")
    sel = Selection(name="Home Win", market=sample_market, selection_id="SEL-1", odds=odds)

    assert sel.name == "Home Win"
    assert sel.market == sample_market
    assert sel.selection_id == "SEL-1"
    assert sel.odds == odds
    assert sel.fixture_id == "FIX-300"
    assert sel.identity == "SEL-1"
    assert str(sel) == "Match Winner -> Home Win"


def test_selection_default_identity_derivation(sample_market: Market) -> None:
    """Verify default identity generation when selection_id is not specified."""
    sel = Selection(name="Draw", market=sample_market)
    assert sel.identity == "MKT-300:draw"
    assert sel.fixture_id == "FIX-300"


@pytest.mark.parametrize("invalid_name", ["", "   ", None, 123])
def test_selection_invalid_name_raises(invalid_name: object, sample_market: Market) -> None:
    """Verify empty or non-string selection name raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Selection name must be a non-empty string"):
        Selection(name=invalid_name, market=sample_market)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_market", [None, "FIX-1", 123, object()])
def test_selection_invalid_market_raises(invalid_market: object) -> None:
    """Verify non-Market instance raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Associated market must be a Market instance"):
        Selection(name="Home Win", market=invalid_market)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_odds", ["1.50", 1.50, 10, object()])
def test_selection_invalid_odds_type_raises(invalid_odds: object, sample_market: Market) -> None:
    """Verify passing a non-Odds instance to odds field raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Odds must be an Odds instance"):
        Selection(name="Home Win", market=sample_market, odds=invalid_odds)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_id", ["", "   ", 123])
def test_selection_invalid_id_raises(invalid_id: object, sample_market: Market) -> None:
    """Verify invalid selection_id raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Selection ID, if provided, must be a non-empty string"):
        Selection(name="Away Win", market=sample_market, selection_id=invalid_id)  # type: ignore[arg-type]


def test_selection_value_semantics(sample_market: Market) -> None:
    """Verify equality and hash behavior for Selection."""
    s1 = Selection(name="Home Win", market=sample_market)
    s2 = Selection(name="Home Win", market=sample_market)
    s3 = Selection(name="Away Win", market=sample_market)

    assert s1 == s2
    assert s1 != s3
    assert hash(s1) == hash(s2)
    assert len({s1, s2, s3}) == 2
