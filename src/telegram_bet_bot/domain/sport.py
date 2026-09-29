"""Sport entity and value object."""

from dataclasses import dataclass
from telegram_bet_bot.domain.exceptions import DomainValidationError


@dataclass(frozen=True)
class Sport:
    """Represents a sporting discipline.

    Instances are immutable, hashable, and enforce a non-empty canonical name.
    """

    name: str

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise DomainValidationError("Sport name must be a non-empty string.")
        # Canonicalize to stripped lowercase for stable equality and hashing
        object.__setattr__(self, "name", self.name.strip().lower())

    def __str__(self) -> str:
        return self.name

    def __repr__(self) -> str:
        return f"Sport('{self.name}')"


# Common sport constants for convenience
FOOTBALL = Sport("football")
BASKETBALL = Sport("basketball")
TENNIS = Sport("tennis")
