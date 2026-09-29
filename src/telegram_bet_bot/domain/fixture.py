"""Fixture entity and lifecycle status enum."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from telegram_bet_bot.domain.exceptions import DomainValidationError
from telegram_bet_bot.domain.league import League
from telegram_bet_bot.domain.sport import Sport


class FixtureStatus(str, Enum):
    """Lifecycle state of a sporting event.

    - SCHEDULED: Not yet started; eligible for betslip candidate evaluation.
    - IN_PLAY: Match currently underway; excluded from pre-match betslip generation.
    - FINISHED: Event concluded; ready for outcome settlement.
    - POSTPONED: Delayed past original schedule window.
    - CANCELLED: Abandoned or voided.
    """

    SCHEDULED = "SCHEDULED"
    IN_PLAY = "IN_PLAY"
    FINISHED = "FINISHED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"

    @property
    def is_unstarted(self) -> bool:
        """Return True only if the fixture is scheduled and has not commenced."""
        return self == FixtureStatus.SCHEDULED


@dataclass(frozen=True)
class Fixture:
    """Represents a scheduled sporting event between two distinct participants.

    Invariants enforced:
    - Valid, non-empty fixture identity.
    - Valid Sport and League instances.
    - League's associated sport must match the fixture's sport.
    - Non-empty home and away participant names.
    - Home and away participants cannot be identical.
    - Scheduled start time must be a timezone-aware datetime.
    - Valid FixtureStatus.
    """

    fixture_id: str
    sport: Sport
    league: League
    home_team: str
    away_team: str
    scheduled_start_time: datetime
    status: FixtureStatus = FixtureStatus.SCHEDULED

    def __post_init__(self) -> None:
        if not isinstance(self.fixture_id, str) or not self.fixture_id.strip():
            raise DomainValidationError("Fixture identity must be a non-empty string.")
        object.__setattr__(self, "fixture_id", self.fixture_id.strip())

        if not isinstance(self.sport, Sport):
            raise DomainValidationError(
                f"Fixture sport must be a Sport instance, got {type(self.sport).__name__}."
            )

        if not isinstance(self.league, League):
            raise DomainValidationError(
                f"Fixture league must be a League instance, got {type(self.league).__name__}."
            )

        if self.league.sport != self.sport:
            raise DomainValidationError(
                f"League sport '{self.league.sport.name}' does not match fixture sport '{self.sport.name}'."
            )

        if not isinstance(self.home_team, str) or not self.home_team.strip():
            raise DomainValidationError("Home participant must be a non-empty string.")
        object.__setattr__(self, "home_team", self.home_team.strip())

        if not isinstance(self.away_team, str) or not self.away_team.strip():
            raise DomainValidationError("Away participant must be a non-empty string.")
        object.__setattr__(self, "away_team", self.away_team.strip())

        if self.home_team.casefold() == self.away_team.casefold():
            raise DomainValidationError(
                f"Home and away participants cannot be identical: '{self.home_team}'."
            )

        if not isinstance(self.scheduled_start_time, datetime):
            raise DomainValidationError(
                f"Scheduled start time must be a datetime, got {type(self.scheduled_start_time).__name__}."
            )

        if (
            self.scheduled_start_time.tzinfo is None
            or self.scheduled_start_time.tzinfo.utcoffset(self.scheduled_start_time) is None
        ):
            raise DomainValidationError(
                "Scheduled start time must be a timezone-aware datetime. Naive datetimes are rejected."
            )

        if not isinstance(self.status, FixtureStatus):
            raise DomainValidationError(
                f"Fixture status must be a FixtureStatus enum member, got {type(self.status).__name__}."
            )

    @property
    def is_unstarted(self) -> bool:
        """Return True if fixture is scheduled and has not commenced."""
        return self.status.is_unstarted

    def __str__(self) -> str:
        return f"{self.home_team} vs {self.away_team} ({self.league.name})"

    def __repr__(self) -> str:
        return (
            f"Fixture(fixture_id='{self.fixture_id}', "
            f"match='{self.home_team} vs {self.away_team}', "
            f"league='{self.league.name}', "
            f"status={self.status.value})"
        )
