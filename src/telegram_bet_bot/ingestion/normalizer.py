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


class ProviderIdentityMapper:
    """Manages the boundary between external provider identifiers and canonical domain identities.

    Guarantees:
    - Provider external IDs are preserved at the provider boundary on DTOs.
    - Provider external IDs are kept strictly separate from internal canonical domain identities.
    - Idempotent ingestion is preserved across repeated ingestion runs.
    - Changing a provider external ID does not silently redefine the internal domain identity
      unless explicitly mapped.
    """

    def __init__(self) -> None:
        self._fixture_mappings: dict[str, str] = {}  # external_id -> internal_id
        self._custom_mappings: dict[str, str] = {}  # explicit overrides: external_id -> internal_id
        self._league_external_ids: dict[str, set[str]] = {}  # league_identity -> set of known external_ids

    def register_fixture_mapping(self, external_id: str, internal_id: str) -> None:
        """Register an explicit custom mapping from an external fixture ID to an internal domain fixture ID."""
        if not isinstance(external_id, str) or not external_id.strip():
            raise ValueError("External ID must be a non-empty string.")
        if not isinstance(internal_id, str) or not internal_id.strip():
            raise ValueError("Internal ID must be a non-empty string.")
        self._custom_mappings[external_id.strip()] = internal_id.strip()

    def record_league_mapping(self, external_id: str | None, league: League) -> None:
        """Record the provider's external league ID associated with a domain League."""
        if external_id and isinstance(external_id, str) and external_id.strip():
            clean_ext = external_id.strip()
            self._league_external_ids.setdefault(league.identity, set()).add(clean_ext)

    def is_valid_league_reference(self, league_ref: str, league: League) -> bool:
        """Check whether a provider fixture's declared league reference matches the domain League."""
        if not league_ref or not isinstance(league_ref, str):
            return False
        clean_ref = league_ref.strip()

        # 1. Match against known external IDs for this league
        known_ext_ids = self._league_external_ids.get(league.identity, set())
        if clean_ref in known_ext_ids:
            return True

        # 2. Match against league's domain identity
        if clean_ref == league.identity:
            return True

        # 3. Match against league's domain league_id if present
        if league.league_id and clean_ref == league.league_id:
            return True

        # 4. Match against slug / normalized name variations
        normalized_name = league.name.strip().lower().replace(" ", "_")
        slug_hyphen = league.name.strip().lower().replace(" ", "-")
        canonical_slug = f"{league.sport.name}:{normalized_name}"
        canonical_hyphen = f"{league.sport.name}-{slug_hyphen}"

        clean_lower = clean_ref.lower()
        if clean_lower in {
            league.name.strip().lower(),
            normalized_name,
            slug_hyphen,
            canonical_slug,
            canonical_hyphen,
        }:
            return True

        return False

    def resolve_fixture_id(
        self,
        external_id: str,
        league: League,
        home_team: str,
        away_team: str,
        start_time: datetime,
    ) -> str:
        """Resolve a provider fixture's identity to a canonical internal domain fixture ID.

        Resolution order:
        1. Explicit custom mapping, if registered.
        2. Previously resolved internal ID for this external_id (preserves identity across kickoff changes).
        3. Deterministic canonical domain identity derived from domain attributes:
           f"{league.identity}:{home_slug}_vs_{away_slug}:{date_slug}".
        """
        clean_ext = external_id.strip() if external_id and isinstance(external_id, str) else ""

        if clean_ext and clean_ext in self._custom_mappings:
            return self._custom_mappings[clean_ext]

        if clean_ext and clean_ext in self._fixture_mappings:
            return self._fixture_mappings[clean_ext]

        # Natural canonical domain identity
        home_slug = home_team.strip().lower().replace(" ", "_")
        away_slug = away_team.strip().lower().replace(" ", "_")
        date_slug = start_time.astimezone(timezone.utc).strftime("%Y%m%d")
        internal_id = f"{league.identity}:{home_slug}_vs_{away_slug}:{date_slug}"

        if clean_ext:
            self._fixture_mappings[clean_ext] = internal_id

        return internal_id


class ProviderDataNormalizer:
    """Normalizes external provider data structures into strict Phase 2 domain entities.

    Enforces all domain validation rules and invariants:
    - Decoupling of provider external IDs from internal domain identities
    - Strict validation of provider fixture sport and league relationships
    - Timezone-aware UTC instant normalization
    - Lossless Decimal line and odds conversion
    - Rejection of naive or malformed timestamps
    - Rejection of invalid odds (< 1.01 or non-finite)
    - Participant distinction and status mapping
    """

    def __init__(self, identity_mapper: ProviderIdentityMapper | None = None) -> None:
        self._identity_mapper = identity_mapper or ProviderIdentityMapper()

    @property
    def identity_mapper(self) -> ProviderIdentityMapper:
        """Return the active provider identity mapper."""
        return self._identity_mapper

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
            # We do NOT pass league_id=provider_league.external_id to prevent leaking
            # provider external ID into canonical domain identity.
            # League.identity naturally evaluates to f"{sport.name}:{normalized_name}".
            league = League(
                name=provider_league.name,
                sport=sport,
                country=provider_league.country,
                league_id=None,
            )
            self._identity_mapper.record_league_mapping(provider_league.external_id, league)
            return league
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
        if not isinstance(sport, Sport):
            raise NormalizationError(f"Expected domain Sport instance, got {type(sport).__name__}")
        if not isinstance(league, League):
            raise NormalizationError(f"Expected domain League instance, got {type(league).__name__}")

        # Validate provider fixture's declared relationships against domain objects (Correction 2)
        if not provider_fixture.sport_name or not isinstance(provider_fixture.sport_name, str):
            raise NormalizationError("Provider fixture must declare a non-empty sport_name.")
        if provider_fixture.sport_name.strip().lower() != sport.name:
            raise NormalizationError(
                f"Provider fixture declares sport '{provider_fixture.sport_name}', which does not match "
                f"passed domain Sport '{sport.name}'."
            )

        if not provider_fixture.league_id or not isinstance(provider_fixture.league_id, str):
            raise NormalizationError("Provider fixture must declare a non-empty league_id.")
        if not self._identity_mapper.is_valid_league_reference(provider_fixture.league_id, league):
            raise NormalizationError(
                f"Provider fixture declares league '{provider_fixture.league_id}', which does not match "
                f"passed domain League '{league.identity}'."
            )

        start_time = self.normalize_start_time(provider_fixture.start_time)
        status = self.normalize_status(provider_fixture.status)

        # Resolve canonical internal domain identity decoupled from provider external_id (Correction 1)
        fixture_id = self._identity_mapper.resolve_fixture_id(
            external_id=provider_fixture.external_id,
            league=league,
            home_team=provider_fixture.home_team,
            away_team=provider_fixture.away_team,
            start_time=start_time,
        )

        try:
            return Fixture(
                fixture_id=fixture_id,
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
            # We do NOT pass market_id=provider_market.external_id to prevent leaking
            # provider external ID into canonical domain identity.
            # Market.identity naturally evaluates to f"{fixture.fixture_id}:{name}:{line}".
            return Market(
                name=provider_market.name,
                fixture=fixture,
                market_id=None,
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
            # We do NOT pass selection_id=provider_selection.external_id to prevent leaking
            # provider external ID into canonical domain identity.
            # Selection.identity naturally evaluates to f"{market.identity}:{name}".
            return Selection(
                name=provider_selection.name,
                market=market,
                selection_id=None,
                odds=odds,
            )
        except (DomainValidationError, TypeError, ValueError) as err:
            raise NormalizationError(
                f"Failed to normalize selection '{provider_selection.name}': {err}"
            ) from err
