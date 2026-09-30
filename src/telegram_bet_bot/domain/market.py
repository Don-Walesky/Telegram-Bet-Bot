"""Market domain entity representing a betting market associated with a fixture."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Union
from telegram_bet_bot.domain.exceptions import DomainValidationError
from telegram_bet_bot.domain.fixture import Fixture


@dataclass(frozen=True)
class Market:
    """Represents a betting market associated with a specific sporting fixture.

    Examples:
    - Match Winner (1X2 / Moneyline)
    - Total Goals (Over/Under with line=2.5)
    - Both Teams To Score (BTTS)

    Invariants:
    - Non-empty market name.
    - Valid associated fixture identifier.
    - Finite numeric line value when specified (rejects NaN, +/- Infinity).
    """

    name: str
    fixture_id: str
    market_id: str | None = None
    line: Decimal | None = None

    def __init__(
        self,
        name: str,
        fixture: Union[Fixture, str],
        market_id: str | None = None,
        line: Union[int, float, str, Decimal, None] = None,
    ) -> None:
        if not isinstance(name, str) or not name.strip():
            raise DomainValidationError("Market name must be a non-empty string.")
        object.__setattr__(self, "name", name.strip())

        if isinstance(fixture, Fixture):
            resolved_fixture_id = fixture.fixture_id
        elif isinstance(fixture, str):
            if not fixture.strip():
                raise DomainValidationError("Associated fixture identity must be a non-empty string.")
            resolved_fixture_id = fixture.strip()
        else:
            raise DomainValidationError(
                f"Associated fixture must be a Fixture instance or non-empty string ID, got {type(fixture).__name__}."
            )
        object.__setattr__(self, "fixture_id", resolved_fixture_id)

        if market_id is not None:
            if not isinstance(market_id, str) or not market_id.strip():
                raise DomainValidationError("Market ID, if provided, must be a non-empty string.")
            object.__setattr__(self, "market_id", market_id.strip())
        else:
            object.__setattr__(self, "market_id", None)

        if line is not None:
            if isinstance(line, bool):
                raise DomainValidationError("Market line cannot be a boolean.")
            try:
                dec_line = Decimal(str(line).strip())
            except Exception as err:
                raise DomainValidationError(f"Market line must be numeric, got {line!r}.") from err
            if not dec_line.is_finite():
                raise DomainValidationError(f"Market line must be a finite number, got {line!r}.")
            object.__setattr__(self, "line", dec_line)
        else:
            object.__setattr__(self, "line", None)

    @property
    def identity(self) -> str:
        """Stable market identifier."""
        if self.market_id:
            return self.market_id
        line_suffix = f":{self.line}" if self.line is not None else ""
        normalized_name = self.name.lower().replace(" ", "_")
        return f"{self.fixture_id}:{normalized_name}{line_suffix}"

    def __str__(self) -> str:
        if self.line is not None:
            return f"{self.name} {self.line}"
        return self.name

    def __repr__(self) -> str:
        return f"Market(name='{self.name}', fixture_id='{self.fixture_id}', line={self.line})"
