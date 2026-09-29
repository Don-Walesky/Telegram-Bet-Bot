"""League entity representing a sports competition or tournament."""

from dataclasses import dataclass
from telegram_bet_bot.domain.exceptions import DomainValidationError
from telegram_bet_bot.domain.sport import Sport


@dataclass(frozen=True)
class League:
    """Represents a sports league or tournament associated with a sport.

    Enforces non-empty name and valid associated Sport instance.
    """

    name: str
    sport: Sport
    country: str | None = None
    league_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise DomainValidationError("League name must be a non-empty string.")
        object.__setattr__(self, "name", self.name.strip())

        if not isinstance(self.sport, Sport):
            raise DomainValidationError(
                f"League sport must be a Sport instance, got {type(self.sport).__name__}."
            )

        if self.country is not None:
            if not isinstance(self.country, str) or not self.country.strip():
                raise DomainValidationError("League country, if provided, must be a non-empty string.")
            object.__setattr__(self, "country", self.country.strip())

        if self.league_id is not None:
            if not isinstance(self.league_id, str) or not self.league_id.strip():
                raise DomainValidationError("League ID, if provided, must be a non-empty string.")
            object.__setattr__(self, "league_id", self.league_id.strip())

    @property
    def identity(self) -> str:
        """Stable league identifier, using league_id if present or sport:name."""
        if self.league_id:
            return self.league_id
        normalized_name = self.name.lower().replace(" ", "_")
        return f"{self.sport.name}:{normalized_name}"

    def __str__(self) -> str:
        if self.country:
            return f"{self.name} ({self.country})"
        return self.name

    def __repr__(self) -> str:
        return f"League(name='{self.name}', sport={self.sport!r}, league_id={self.league_id!r})"
