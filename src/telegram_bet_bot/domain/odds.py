"""Decimal odds value object and bookmaker implied probability calculation."""

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
from typing import Union
from telegram_bet_bot.domain.exceptions import InvalidOddsError

Numeric = Union[int, float, str, Decimal]


@dataclass(frozen=True)
class Odds:
    """Value object representing decimal betting odds.

    Enforces that decimal odds must be numeric, finite, non-NaN, and strictly greater than 1.0.
    Provides mathematically sound conversion to bookmaker implied probability (1 / decimal_odds).

    NOTE: The implied probability calculated here reflects bookmaker pricing (including bookmaker margin),
    NOT a true, fair, or predictive model probability.
    """

    decimal_value: Decimal

    def __init__(self, value: Numeric) -> None:
        """Initialize decimal odds from an int, float, str, or Decimal.

        Rejects boolean types, non-numeric strings, NaN, infinity, and values <= 1.0.
        """
        if isinstance(value, bool):
            raise InvalidOddsError("Odds value cannot be a boolean.")

        if isinstance(value, float):
            if math.isnan(value):
                raise InvalidOddsError("Odds value cannot be NaN.")
            if math.isinf(value):
                raise InvalidOddsError("Odds value cannot be infinite.")
            try:
                dec = Decimal(str(value))
            except (InvalidOperation, ValueError) as err:
                raise InvalidOddsError(f"Invalid odds value: {value!r}") from err
        elif isinstance(value, (int, str, Decimal)):
            try:
                dec = Decimal(str(value).strip())
            except (InvalidOperation, ValueError) as err:
                raise InvalidOddsError(f"Invalid odds value: {value!r}") from err
            if dec.is_nan():
                raise InvalidOddsError("Odds value cannot be NaN.")
            if dec.is_infinite():
                raise InvalidOddsError("Odds value cannot be infinite.")
        else:
            raise InvalidOddsError(
                f"Odds value must be numeric (int, float, str, or Decimal), got {type(value).__name__}."
            )

        if dec <= Decimal("1.0"):
            raise InvalidOddsError(
                f"Decimal odds must be strictly greater than 1.0, got {dec}."
            )

        object.__setattr__(self, "decimal_value", dec)

    @property
    def value(self) -> Decimal:
        """Return the decimal odds value as a Decimal."""
        return self.decimal_value

    def to_float(self) -> float:
        """Return the decimal odds value as a float."""
        return float(self.decimal_value)

    def __float__(self) -> float:
        return float(self.decimal_value)

    @property
    def bookmaker_implied_probability(self) -> Decimal:
        """Calculate bookmaker implied probability: P_implied = 1 / DecimalOdds.

        IMPORTANT: This represents bookmaker implied probability including bookmaker margin (overround).
        It is NOT an empirical, fair, or model predictive probability.
        """
        return Decimal(1) / self.decimal_value

    @property
    def implied_probability(self) -> Decimal:
        """Alias for bookmaker_implied_probability."""
        return self.bookmaker_implied_probability

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Odds):
            return self.decimal_value == other.decimal_value
        return False

    def __hash__(self) -> int:
        return hash(self.decimal_value.normalize())

    def __lt__(self, other: object) -> bool:
        if isinstance(other, Odds):
            return self.decimal_value < other.decimal_value
        return NotImplemented

    def __le__(self, other: object) -> bool:
        if isinstance(other, Odds):
            return self.decimal_value <= other.decimal_value
        return NotImplemented

    def __gt__(self, other: object) -> bool:
        if isinstance(other, Odds):
            return self.decimal_value > other.decimal_value
        return NotImplemented

    def __ge__(self, other: object) -> bool:
        if isinstance(other, Odds):
            return self.decimal_value >= other.decimal_value
        return NotImplemented

    def __repr__(self) -> str:
        return f"Odds({self.decimal_value})"

    def __str__(self) -> str:
        return str(self.decimal_value)
