"""Unit tests for RiskTier domain enum."""

import pytest
from telegram_bet_bot.domain import DomainValidationError, RiskTier


def test_risk_tier_enum_values() -> None:
    """Verify all defined RiskTier enum values."""
    assert RiskTier.CONSERVATIVE.value == "CONSERVATIVE"
    assert RiskTier.MODERATE.value == "MODERATE"
    assert RiskTier.AGGRESSIVE.value == "AGGRESSIVE"


@pytest.mark.parametrize(
    "raw_input, expected_tier",
    [
        ("conservative", RiskTier.CONSERVATIVE),
        ("CONSERVATIVE", RiskTier.CONSERVATIVE),
        ("  moderate  ", RiskTier.MODERATE),
        ("aggressive", RiskTier.AGGRESSIVE),
        ("AGGRESSIVE", RiskTier.AGGRESSIVE),
    ],
)
def test_risk_tier_from_string_success(raw_input: str, expected_tier: RiskTier) -> None:
    """Verify case-insensitive string parsing to RiskTier."""
    assert RiskTier.from_string(raw_input) == expected_tier


@pytest.mark.parametrize("invalid_value", ["ultra_safe", "extreme", "", "   ", "random"])
def test_risk_tier_from_string_invalid_raises_validation_error(invalid_value: str) -> None:
    """Verify invalid risk tier strings raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="Invalid RiskTier"):
        RiskTier.from_string(invalid_value)


@pytest.mark.parametrize("invalid_type", [123, None, [], {}])
def test_risk_tier_from_string_non_string_type_raises(invalid_type: object) -> None:
    """Verify non-string inputs raise DomainValidationError."""
    with pytest.raises(DomainValidationError, match="RiskTier value must be a string"):
        RiskTier.from_string(invalid_type)  # type: ignore[arg-type]


def test_risk_tier_value_semantics() -> None:
    """Verify value semantics, set uniqueness, and hashing."""
    r1 = RiskTier.CONSERVATIVE
    r2 = RiskTier.from_string("conservative")
    assert r1 == r2
    assert hash(r1) == hash(r2)
    assert len({r1, r2, RiskTier.MODERATE}) == 2
