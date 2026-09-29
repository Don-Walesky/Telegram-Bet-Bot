"""Selection domain entity representing a selectable betting outcome."""

from dataclasses import dataclass
from telegram_bet_bot.domain.exceptions import DomainValidationError
from telegram_bet_bot.domain.market import Market
from telegram_bet_bot.domain.odds import Odds


@dataclass(frozen=True)
class Selection:
    """Represents a specific selectable outcome belonging to a Market.

    Examples:
    - Home Win (1), Draw (X), Away Win (2)
    - Over 2.5, Under 2.5
    - BTTS Yes, BTTS No

    Invariants:
    - Non-empty selection name.
    - Associated Market must be a valid Market instance.
    - If provided, odds must be a valid Odds instance.
    """

    name: str
    market: Market
    selection_id: str | None = None
    odds: Odds | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise DomainValidationError("Selection name must be a non-empty string.")
        object.__setattr__(self, "name", self.name.strip())

        if not isinstance(self.market, Market):
            raise DomainValidationError(
                f"Associated market must be a Market instance, got {type(self.market).__name__}."
            )

        if self.selection_id is not None:
            if not isinstance(self.selection_id, str) or not self.selection_id.strip():
                raise DomainValidationError("Selection ID, if provided, must be a non-empty string.")
            object.__setattr__(self, "selection_id", self.selection_id.strip())

        if self.odds is not None and not isinstance(self.odds, Odds):
            raise DomainValidationError(
                f"Odds must be an Odds instance, got {type(self.odds).__name__}."
            )

    @property
    def fixture_id(self) -> str:
        """Retrieve fixture identity via the parent market."""
        return self.market.fixture_id

    @property
    def identity(self) -> str:
        """Stable selection identifier."""
        if self.selection_id:
            return self.selection_id
        normalized_name = self.name.lower().replace(" ", "_")
        return f"{self.market.identity}:{normalized_name}"

    def __str__(self) -> str:
        return f"{self.market.name} -> {self.name}"

    def __repr__(self) -> str:
        return (
            f"Selection(name='{self.name}', "
            f"market='{self.market.name}', "
            f"fixture_id='{self.fixture_id}')"
        )
