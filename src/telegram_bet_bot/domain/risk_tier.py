"""RiskTier domain enum representing user risk appetite classification."""

from enum import Enum
from telegram_bet_bot.domain.exceptions import DomainValidationError


class RiskTier(str, Enum):
    """Classification of user risk appetite for betslip generation.

    - CONSERVATIVE: Low-variance selections, strict odds bounds, high reliability thresholds.
    - MODERATE: Balanced risk/return profile with standard market lines.
    - AGGRESSIVE: Higher-variance selections, underdog value, higher odds envelopes.
    """

    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    AGGRESSIVE = "AGGRESSIVE"

    @classmethod
    def from_string(cls, value: str) -> "RiskTier":
        """Parse a string into a RiskTier enum member in a case-insensitive manner."""
        if not isinstance(value, str):
            raise DomainValidationError(
                f"RiskTier value must be a string, got {type(value).__name__}."
            )
        normalized = value.strip().upper()
        try:
            return cls[normalized]
        except KeyError:
            valid_names = [tier.value for tier in cls]
            raise DomainValidationError(
                f"Invalid RiskTier '{value}'. Expected one of: {valid_names}."
            )
