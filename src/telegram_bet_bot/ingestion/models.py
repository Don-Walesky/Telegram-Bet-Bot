"""Provider Data Transfer Objects (DTOs) representing external sports data boundaries.

These data structures represent the external provider's schema before normalization
and conversion into pure Phase 2 domain entities.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Union

NumericLike = Union[Decimal, float, str, int]
DateTimeLike = Union[datetime, str]


@dataclass(frozen=True)
class ProviderSport:
    """External provider representation of a sporting discipline."""

    name: str
    external_id: str | None = None


@dataclass(frozen=True)
class ProviderLeague:
    """External provider representation of a tournament or competition."""

    name: str
    sport_name: str
    country: str | None = None
    external_id: str | None = None


@dataclass(frozen=True)
class ProviderFixture:
    """External provider representation of a sporting contest."""

    external_id: str
    sport_name: str
    league_id: str
    home_team: str
    away_team: str
    start_time: DateTimeLike
    status: str = "SCHEDULED"


@dataclass(frozen=True)
class ProviderMarket:
    """External provider representation of a wagering market."""

    name: str
    fixture_external_id: str
    external_id: str | None = None
    line: NumericLike | None = None


@dataclass(frozen=True)
class ProviderSelection:
    """External provider representation of a discrete market outcome / selection."""

    name: str
    market_external_id: str
    external_id: str | None = None
    odds: NumericLike | None = None


@dataclass(frozen=True)
class ProviderFixtureBundle:
    """Composite bundle holding a fixture and its related hierarchical provider data."""

    fixture: ProviderFixture
    sport: ProviderSport
    league: ProviderLeague
    markets: list[ProviderMarket] = field(default_factory=list)
    selections: list[ProviderSelection] = field(default_factory=list)
