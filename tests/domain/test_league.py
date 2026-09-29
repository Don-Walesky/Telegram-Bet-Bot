"""Unit tests for League domain entity."""

import pytest
from telegram_bet_bot.domain import FOOTBALL, League, Sport, DomainValidationError


def test_league_valid_construction() -> None:
    """Verify normal League construction with optional attributes."""
    league = League(name="Premier League", sport=FOOTBALL, country="England", league_id="EPL")
    assert league.name == "Premier League"
    assert league.sport == FOOTBALL
    assert league.country == "England"
    assert league.league_id == "EPL"
    assert league.identity == "EPL"
    assert str(league) == "Premier League (England)"


def test_league_default_identity_derivation() -> None:
    """Verify league identity generation when league_id is not explicitly provided."""
    league = League(name="La Liga", sport=FOOTBALL)
    assert league.identity == "football:la_liga"
    assert str(league) == "La Liga"


@pytest.mark.parametrize("invalid_name", ["", "   ", None, 99])
def test_league_invalid_name_fails(invalid_name: object) -> None:
    """Verify empty or non-string league names raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="League name must be a non-empty string"):
        League(name=invalid_name, sport=FOOTBALL)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_sport", [None, "football", 123, object()])
def test_league_invalid_sport_fails(invalid_sport: object) -> None:
    """Verify non-Sport instances raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="League sport must be a Sport instance"):
        League(name="NBA", sport=invalid_sport)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_country", ["", "   ", 123])
def test_league_invalid_country_fails(invalid_country: object) -> None:
    """Verify that an invalid country string raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="League country, if provided, must be a non-empty string"):
        League(name="Serie A", sport=FOOTBALL, country=invalid_country)  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_id", ["", "   ", 123])
def test_league_invalid_id_fails(invalid_id: object) -> None:
    """Verify that an invalid league_id raises DomainValidationError."""
    with pytest.raises(DomainValidationError, match="League ID, if provided, must be a non-empty string"):
        League(name="Serie A", sport=FOOTBALL, league_id=invalid_id)  # type: ignore[arg-type]


def test_league_value_semantics() -> None:
    """Verify equality and hashing semantics for League."""
    l1 = League(name="Premier League", sport=FOOTBALL, country="England")
    l2 = League(name="Premier League", sport=FOOTBALL, country="England")
    l3 = League(name="Serie A", sport=FOOTBALL, country="Italy")

    assert l1 == l2
    assert l1 != l3
    assert hash(l1) == hash(l2)
    assert len({l1, l2, l3}) == 2
