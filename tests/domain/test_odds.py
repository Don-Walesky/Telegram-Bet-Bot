"""Unit tests for Odds value object and bookmaker implied probability."""

from decimal import Decimal
import pytest
from telegram_bet_bot.domain import InvalidOddsError, Odds


@pytest.mark.parametrize(
    "raw_input, expected_decimal",
    [
        (1.50, Decimal("1.5")),
        ("1.50", Decimal("1.50")),
        (2, Decimal("2")),
        (Decimal("3.75"), Decimal("3.75")),
        (" 1.85 ", Decimal("1.85")),
    ],
)
def test_odds_valid_construction_and_retrieval(raw_input: object, expected_decimal: Decimal) -> None:
    """Verify normal Odds construction from various valid numeric types."""
    odds = Odds(raw_input)  # type: ignore[arg-type]
    assert odds.value == expected_decimal
    assert odds.decimal_value == expected_decimal
    assert isinstance(odds.value, Decimal)
    assert odds.to_float() == float(expected_decimal)
    assert float(odds) == float(expected_decimal)


@pytest.mark.parametrize(
    "invalid_input",
    [
        1.0,
        "1.00",
        Decimal("1.0"),
        0.99,
        0,
        -1.50,
        -5,
        float("nan"),
        float("inf"),
        float("-inf"),
        "nan",
        "inf",
        "-inf",
        "invalid",
        "",
        "   ",
        True,
        False,
        None,
        [],
        {},
    ],
)
def test_odds_invalid_values_raise_invalid_odds_error(invalid_input: object) -> None:
    """Verify that non-numeric, <= 1.0, NaN, infinity, and boolean values are rejected."""
    with pytest.raises(InvalidOddsError):
        Odds(invalid_input)  # type: ignore[arg-type]


def test_odds_value_semantics_and_comparison() -> None:
    """Verify equality, ordering, and hashing behavior."""
    o1 = Odds(1.50)
    o2 = Odds("1.5")
    o3 = Odds(Decimal("1.50"))
    o4 = Odds(2.20)

    # Cross-representation equality
    assert o1 == o2
    assert o2 == o3
    assert o1 != o4

    # Direct numeric comparison with Odds instance
    assert o1 == 1.5
    assert o1 == "1.50"
    assert o1 == Decimal("1.5")
    assert o1 != "not_a_number"

    # Ordering
    assert o1 < o4
    assert o1 <= o2
    assert o4 > o1
    assert o4 >= o4
    assert not (o4 < o1)

    # Hash and set membership
    assert hash(o1) == hash(o2)
    assert hash(o2) == hash(o3)
    odds_set = {o1, o2, o3, o4}
    assert len(odds_set) == 2
    assert o1 in odds_set


def test_odds_bookmaker_implied_probability() -> None:
    """Verify mathematical calculation of bookmaker implied probability: P = 1 / DecimalOdds.

    IMPORTANT: This represents bookmaker implied probability (including bookmaker margin),
    NOT model or fair probability.
    """
    even_odds = Odds(2.00)
    assert even_odds.bookmaker_implied_probability == Decimal("0.5")
    assert even_odds.implied_probability == Decimal("0.5")

    heavy_fav = Odds(1.25)
    assert heavy_fav.bookmaker_implied_probability == Decimal("0.8")

    long_shot = Odds(4.00)
    assert long_shot.bookmaker_implied_probability == Decimal("0.25")

    # High precision check: 1 / 3.00 is approximately 0.3333333333333333...
    three_odds = Odds(3.00)
    implied = three_odds.bookmaker_implied_probability
    assert isinstance(implied, Decimal)
    assert (implied * Decimal("3.00")).quantize(Decimal("1.0")) == Decimal("1.0")
