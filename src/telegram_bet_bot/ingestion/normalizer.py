"""Adapter converting external provider DTOs into pure Phase 2 domain entities."""

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import math
from typing import Any

from telegram_bet_bot.domain import (
    Fixture,
    FixtureStatus,
    League,
    Market,
    Odds,
    Selection,
    Sport,
)
from telegram_bet_bot.domain.exceptions import DomainValidationError
from telegram_bet_bot.ingestion.exceptions import NormalizationError
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)


class ProviderDataNormalizer:
    """Normalizes external provider data structures into strict Phase 2 domain entities.

    Enforces all domain validation rules and invariants:
    - Timezone-aware UTC instant normalization
    - Lossless Decimal line and odds conversion
    - Rejection of naive or malformed timestamps
    - Rejection of invalid odds (< 1.01 or non-finite)
    - Participant distinction and status mapping
    """

    def normalize_sport(self, provider_sport: ProviderSport) -> Sport:
        """Convert a ProviderSport DTO into a domain Sport entity."""
        if not isinstance(provider_sport, ProviderSport):
            raise NormalizationError(f"Expected ProviderSport instance, got {type(provider_sport).__name__}")
        try:
            return Sport(name=provider_sport.name)
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(f"Failed to normalize sport '{provider_sport.name}': {err}") from err

    def normalize_league(self, provider_league: ProviderLeague, sport: Sport) -> League:
        """Convert a ProviderLeague DTO into a domain League entity with associated Sport."""
        if not isinstance(provider_league, ProviderLeague):
            raise NormalizationError(f"Expected ProviderLeague instance, got {type(provider_league).__name__}")
        if not isinstance(sport, Sport):
            raise NormalizationError(f"Expected domain Sport instance, got {type(sport).__name__}")

        try:
            return League(
                name=provider_league.name,
                sport=sport,
                country=provider_league.country,
                league_id=provider_league.external_id,
            )
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(f"Failed to normalize league '{provider_league.name}': {err}") from err

    def normalize_start_time(self, raw_time: Any) -> datetime:
        """Validate and convert an input timestamp into a timezone-aware UTC datetime.

        Raises:
            NormalizationError: If timestamp is naive, unparseable, or invalid.
        """
        if raw_time is None:
            raise NormalizationError("Fixture start time cannot be None.")

        if isinstance(raw_time, datetime):
            dt = raw_time
        elif isinstance(raw_time, str):
            clean_str = raw_time.strip()
            if not clean_str:
                raise NormalizationError("Fixture start time string cannot be empty.")
            try:
                dt = datetime.fromisoformat(clean_str)
            except (ValueError, TypeError) as err:
                raise NormalizationError(
                    f"Malformed fixture timestamp string '{clean_str}': cannot parse as ISO-8601."
                ) from err
        else:
            raise NormalizationError(
                f"Unsupported timestamp type {type(raw_time).__name__}: expected datetime or ISO-8601 string."
            )

        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
            raise NormalizationError(
                f"Cannot normalize naive timestamp '{raw_time}': timestamp must be timezone-aware with an explicit offset."
            )

        return dt.astimezone(timezone.utc)

    def normalize_status(self, raw_status: str | None) -> FixtureStatus:
        """Map raw provider fixture status to FixtureStatus enum."""
        if not raw_status or not isinstance(raw_status, str):
            return FixtureStatus.SCHEDULED

        clean_status = raw_status.strip().upper()
        try:
            return FixtureStatus(clean_status)
        except ValueError as err:
            raise NormalizationError(
                f"Unsupported fixture status '{raw_status}'. Expected one of: "
                f"{[s.value for s in FixtureStatus]}"
            ) from err

    def normalize_fixture(
        self,
        provider_fixture: ProviderFixture,
        sport: Sport,
        league: League,
    ) -> Fixture:
        """Convert a ProviderFixture DTO into a domain Fixture entity."""
        if not isinstance(provider_fixture, ProviderFixture):
            raise NormalizationError(f"Expected ProviderFixture instance, got {type(provider_fixture).__name__}")

        start_time = self.normalize_start_time(provider_fixture.start_time)
        status = self.normalize_status(provider_fixture.status)

        try:
            return Fixture(
                fixture_id=provider_fixture.external_id,
                sport=sport,
                league=league,
                home_team=provider_fixture.home_team,
                away_team=provider_fixture.away_team,
                scheduled_start_time=start_time,
                status=status,
            )
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(
                f"Failed to normalize fixture '{provider_fixture.external_id}': {err}"
            ) from err

    def normalize_line(self, raw_line: Any) -> Decimal | None:
        """Convert a market line to a finite Decimal or None."""
        if raw_line is None:
            return None

        if isinstance(raw_line, Decimal):
            dec_line = raw_line
        elif isinstance(raw_line, (int, float, str)):
            try:
                dec_line = Decimal(str(raw_line).strip())
            except (InvalidOperation, ValueError, TypeError) as err:
                raise NormalizationError(f"Invalid market line value '{raw_line}': cannot parse as Decimal.") from err
        else:
            raise NormalizationError(f"Unsupported market line type: {type(raw_line).__name__}")

        if not dec_line.is_finite() or math.isnan(float(dec_line)):
            raise NormalizationError(f"Market line must be a finite number, got '{raw_line}'.")

        return dec_line

    def normalize_market(self, provider_market: ProviderMarket, fixture: Fixture) -> Market:
        """Convert a ProviderMarket DTO into a domain Market entity associated with a Fixture."""
        if not isinstance(provider_market, ProviderMarket):
            raise NormalizationError(f"Expected ProviderMarket instance, got {type(provider_market).__name__}")
        if not isinstance(fixture, Fixture):
            raise NormalizationError(f"Expected domain Fixture instance, got {type(fixture).__name__}")

        line = self.normalize_line(provider_market.line)
        try:
            return Market(
                name=provider_market.name,
                fixture=fixture,
                market_id=provider_market.external_id,
                line=line,
            )
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(
                f"Failed to normalize market '{provider_market.name}': {err}"
            ) from err

    def normalize_odds(self, raw_odds: Any) -> Odds | None:
        """Convert raw odds to a domain Odds value object or None."""
        if raw_odds is None:
            return None

        if isinstance(raw_odds, Odds):
            return raw_odds

        if isinstance(raw_odds, Decimal):
            dec_odds = raw_odds
        elif isinstance(raw_odds, (int, float, str)):
            try:
                dec_odds = Decimal(str(raw_odds).strip())
            except (InvalidOperation, ValueError, TypeError) as err:
                raise NormalizationError(f"Invalid odds value '{raw_odds}': cannot parse as Decimal.") from err
        else:
            raise NormalizationError(f"Unsupported odds type: {type(raw_odds).__name__}")

        try:
            return Odds(dec_odds)
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(f"Invalid decimal odds '{raw_odds}': {err}") from err

    def normalize_selection(self, provider_selection: ProviderSelection, market: Market) -> Selection:
        """Convert a ProviderSelection DTO into a domain Selection entity associated with a Market."""
        if not isinstance(provider_selection, ProviderSelection):
            raise NormalizationError(f"Expected ProviderSelection instance, got {type(provider_selection).__name__}")
        if not isinstance(market, Market):
            raise NormalizationError(f"Expected domain Market instance, got {type(market).__name__}")

        odds = self.normalize_odds(provider_selection.odds)
        try:
            return Selection(
                name=provider_selection.name,
                market=market,
                selection_id=provider_selection.external_id,
                odds=odds,
            )
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(
                f"Failed to normalize selection '{provider_selection.name}': {err}"
            ) from err
