"""Unit tests for Market domain entity."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest
from telegram_bet_bot.domain import (
    FOOTBALL,
    DomainValidationError,
    Fixture,
    League,
    Market,
)


@pytest.fixture
def sample_fixture() -> Fixture:
    """Provide a valid Fixture instance for market tests."""
    league = League(name="Premier League", sport=FOOTBALL)
    return Fixture(
        fixture_id="FIX-200",
        sport=FOOTBALL,
        league=league,
        home_team="Arsenal",
        away_team="Chelsea",
        scheduled_start_time=datetime(2026, 11, 1, 14, 0, tzinfo=timezone.utc),
    )


def test_market_valid_construction_with_fixture_id() -> None:
    """Verify market construction directly using a string fixture_id."""
    market = Market(name="Match Winner", fixture="FIX-200", market_id="M-1")
    assert market.name == "Match Winner"
    assert market.fixture_id == "FIX-200"
    assert market.market_id == "M-1"
    assert market.identity == "M-1"
    assert market.line is None
    assert str(market) == "Match Winner"


def test_market_valid_construction_with_fixture_object(sample_fixture: Fixture) -> None:
    """Verify market construction using a Fixture entity instance."""
    market = Market(name="Over/Under Goals", fixture=sample_fixture, line=2.5)
    assert market.name == "Over/Under Goals"
    assert market.fixture_id == "FIX-200"
    assert market.line == Decimal("2.5")
    assert market.identity == "FIX-200:over/under_goals:2.5"
    assert str(market) == "Over/Under Goals 2.5"


@pytest.mark.parametrize("invalid_name", ["", "   ", None, 123])
def test_market_invalid_name_raises(invalid_name: object) -> None:
    """Verify empty or non-string market name raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Market name must be a non-empty string"):
        Market(name=invalid_name, fixture="FIX-1")  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_fixture", ["", "   ", None, 123, object()])
def test_market_invalid_fixture_raises(invalid_fixture: object) -> None:
    """Verify empty or invalid fixture reference raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Associated fixture"):
        Market(name="Match Winner", fixture=invalid_fixture)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_line", ["not_a_number", True, False, []])
def test_market_invalid_line_raises(invalid_line: object) -> None:
    """Verify non-numeric line values raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Market line"):
        Market(name="Over/Under", fixture="FIX-1", line=invalid_line)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "non_finite_line",
    [
        Decimal("NaN"),
        Decimal("Infinity"),
        Decimal("-Infinity"),
        float("nan"),
        float("inf"),
        float("-inf"),
        "nan",
        "NaN",
        "inf",
        "-inf",
        "Infinity",
        "-Infinity",
    ],
)
def test_market_non_finite_line_raises(non_finite_line: object) -> None:
    """Verify non-finite lines (NaN, positive/negative infinity) raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Market line must be a finite number"):
        Market(name="Over/Under", fixture="FIX-1", line=non_finite_line)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "valid_line, expected_decimal",
    [
        (2.5, Decimal("2.5")),
        ("2.5", Decimal("2.5")),
        (Decimal("2.5"), Decimal("2.5")),
        (3, Decimal("3")),
        (0, Decimal("0")),
        (0.0, Decimal("0.0")),
        (-1.5, Decimal("-1.5")),
        ("-0.5", Decimal("-0.5")),
        (" 1.75 ", Decimal("1.75")),
        (Decimal("-2.5"), Decimal("-2.5")),
    ],
)
def test_market_valid_finite_numeric_lines(valid_line: object, expected_decimal: Decimal) -> None:
    """Verify valid finite lines across int, float, str, and Decimal are accepted."""
    market = Market(name="Handicap", fixture="FIX-1", line=valid_line)  # type: ignore[arg-type]
    assert market.line == expected_decimal
    assert isinstance(market.line, Decimal)
    assert market.line.is_finite() is True


def test_market_value_semantics() -> None:
    """Verify equality and hashing semantics for Market."""
    m1 = Market(name="Both Teams To Score", fixture="FIX-1", line=None)
    m2 = Market(name="Both Teams To Score", fixture="FIX-1", line=None)
    m3 = Market(name="Over/Under", fixture="FIX-1", line=2.5)

    assert m1 == m2
    assert m1 != m3
    assert hash(m1) == hash(m2)
    assert len({m1, m2, m3}) == 2
