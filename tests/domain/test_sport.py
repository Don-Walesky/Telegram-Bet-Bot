"""Unit tests for Sport domain entity."""

import pytest
from telegram_bet_bot.domain import BASKETBALL, FOOTBALL, TENNIS, DomainValidationError, Sport


def test_sport_valid_construction() -> None:
    """Verify normal Sport construction with case normalization."""
    sport = Sport("Football")
    assert sport.name == "football"
    assert str(sport) == "football"
    assert repr(sport) == "Sport('football')"


@pytest.mark.parametrize("invalid_name", ["", "   ", None, 123, []])
def test_sport_invalid_names_raise_validation_error(invalid_name: object) -> None:
    """Verify that empty, whitespace, or non-string names raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Sport name must be a non-empty string"):
        Sport(invalid_name)  # type: ignore[arg-type]


def test_sport_value_semantics_equality_and_hashing() -> None:
    """Verify equality and set/dict membership behavior for Sport."""
    s1 = Sport("football")
    s2 = Sport("FOOTBALL")
    s3 = Sport("Basketball")

    assert s1 == s2
    assert s1 != s3
    assert hash(s1) == hash(s2)

    sports_set = {s1, s2, s3}
    assert len(sports_set) == 2
    assert s1 in sports_set


def test_predefined_sports_constants() -> None:
    """Verify predefined sport constants are valid and immutable."""
    assert FOOTBALL.name == "football"
    assert BASKETBALL.name == "basketball"
    assert TENNIS.name == "tennis"
