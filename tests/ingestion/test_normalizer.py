"""Tests for ProviderDataNormalizer converting provider DTOs into pure domain entities."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import pytest

from telegram_bet_bot.domain import FixtureStatus, League, Sport
from telegram_bet_bot.ingestion.exceptions import NormalizationError
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.normalizer import (
    ProviderDataNormalizer,
    ProviderIdentityMapper,
)


def test_normalize_sport(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider sport produces a canonical domain Sport."""
    ps = ProviderSport(name="Football", external_id="s1")
    sport = normalizer.normalize_sport(ps)
    assert sport.name == "football"

    with pytest.raises(NormalizationError, match="non-empty string"):
        normalizer.normalize_sport(ProviderSport(name="   "))

    with pytest.raises(NormalizationError):
        normalizer.normalize_sport("not-a-provider-sport")  # type: ignore


def test_normalize_league(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider league preserves associated domain Sport.

    Also proves that provider external IDs are NOT adopted as canonical domain identities (Correction 1).
    """
    ps = ProviderSport(name="football", external_id="sport-ext-1")
    sport = normalizer.normalize_sport(ps)

    pl = ProviderLeague(name="Premier League", sport_name="football", country="England", external_id="epl-ext-01")
    league = normalizer.normalize_league(pl, sport)
    assert league.name == "Premier League"
    assert league.sport == sport
    assert league.country == "England"
    # Canonical domain identity is purely domain-derived: f"{sport.name}:{normalized_name}"
    assert league.identity == "football:premier_league"
    assert league.identity != "epl-ext-01"
    assert league.league_id is None
    # Provider DTO retains its external ID
    assert pl.external_id == "epl-ext-01"

    with pytest.raises(NormalizationError, match="non-empty string"):
        normalizer.normalize_league(ProviderLeague(name="", sport_name="football"), sport)


def test_normalize_fixture_success(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizing a valid provider fixture produces a pure domain Fixture.

    Proves provider external ID is separated from canonical domain identity (Correction 1).
    """
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="epl-id"), sport)

    pf = ProviderFixture(
        external_id="fix-1",
        sport_name="football",
        league_id="epl-id",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        status="SCHEDULED",
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    # External ID retained on DTO, decoupled from domain fixture_id
    assert pf.external_id == "fix-1"
    assert fixture.fixture_id != "fix-1"
    assert fixture.fixture_id == "football:epl:arsenal_vs_chelsea:20261015"
    assert fixture.sport == sport
    assert fixture.league == league
    assert fixture.home_team == "Arsenal"
    assert fixture.away_team == "Chelsea"
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    assert fixture.status == FixtureStatus.SCHEDULED


def test_normalize_fixture_converts_non_utc_offset_to_utc(normalizer: ProviderDataNormalizer) -> None:
    """Verify non-UTC timezone offsets are preserved and converted to UTC."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)

    # 17:00 at UTC+2 is 15:00 UTC
    offset_tz = timezone(timedelta(hours=2))
    start_time = datetime(2026, 10, 15, 17, 0, tzinfo=offset_tz)

    pf = ProviderFixture(
        external_id="fix-tz",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time=start_time,
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)
    assert fixture.scheduled_start_time.tzinfo == timezone.utc


def test_normalize_fixture_parses_iso_string_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify ISO-8601 strings with offsets are converted to timezone-aware UTC datetimes."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)

    pf = ProviderFixture(
        external_id="fix-iso",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time="2026-10-15T15:00:00+00:00",
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.scheduled_start_time.tzinfo is not None
    assert fixture.scheduled_start_time == datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc)


def test_normalize_fixture_rejects_naive_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify naive datetimes and naive ISO strings are rejected by normalizer."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)

    # 1. Naive Python datetime
    naive_dt = datetime(2026, 10, 15, 15, 0)
    pf1 = ProviderFixture(
        external_id="fix-naive-1",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time=naive_dt,
    )
    with pytest.raises(NormalizationError, match="naive"):
        normalizer.normalize_fixture(pf1, sport, league)

    # 2. Naive ISO-8601 string (no offset, no 'Z')
    pf2 = ProviderFixture(
        external_id="fix-naive-2",
        sport_name="football",
        league_id="l1",
        home_team="A",
        away_team="B",
        start_time="2026-10-15T15:00:00",
    )
    with pytest.raises(NormalizationError, match="naive"):
        normalizer.normalize_fixture(pf2, sport, league)


def test_normalize_fixture_rejects_malformed_timestamp(normalizer: ProviderDataNormalizer) -> None:
    """Verify corrupted timestamp strings raise NormalizationError."""
    with pytest.raises(NormalizationError, match="Malformed"):
        normalizer.normalize_start_time("invalid-datetime-string")

    with pytest.raises(NormalizationError, match="empty"):
        normalizer.normalize_start_time("   ")

    with pytest.raises(NormalizationError, match="None"):
        normalizer.normalize_start_time(None)


def test_normalize_fixture_rejects_identical_participants(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizer rejects fixtures where home and away teams are identical."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)

    pf = ProviderFixture(
        external_id="fix-same-teams",
        sport_name="football",
        league_id="l1",
        home_team="Arsenal",
        away_team="Arsenal",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="Home and away participants cannot be identical"):
        normalizer.normalize_fixture(pf, sport, league)


def test_normalize_fixture_rejects_sport_league_mismatch(normalizer: ProviderDataNormalizer) -> None:
    """Verify normalizer rejects fixture if sport does not match league's sport."""
    football = normalizer.normalize_sport(ProviderSport(name="football"))
    basketball = normalizer.normalize_sport(ProviderSport(name="basketball"))
    nba_league = normalizer.normalize_league(ProviderLeague(name="NBA", sport_name="basketball", external_id="nba"), basketball)

    pf = ProviderFixture(
        external_id="fix-mismatch",
        sport_name="football",
        league_id="nba",
        home_team="A",
        away_team="B",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="does not match fixture sport"):
        normalizer.normalize_fixture(pf, football, nba_league)


# ============================================================================
# CORRECTION 2 TESTS — VALIDATE PROVIDER FIXTURE RELATIONSHIPS
# ============================================================================


def test_normalize_fixture_matching_sport_succeeds(normalizer: ProviderDataNormalizer) -> None:
    """Verify matching sport relationship between provider fixture and domain Sport succeeds."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Premier League", sport_name="football", external_id="league-epl"),
        sport,
    )
    pf = ProviderFixture(
        external_id="fix-valid-sport",
        sport_name="football",
        league_id="league-epl",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.sport == sport


def test_normalize_fixture_mismatching_sport_fails(normalizer: ProviderDataNormalizer) -> None:
    """Verify provider fixture declaring inconsistent sport is rejected with NormalizationError."""
    football = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Premier League", sport_name="football", external_id="league-epl"),
        football,
    )
    # Declares "Basketball" but passed domain Sport is "football"
    pf = ProviderFixture(
        external_id="fix-bad-sport",
        sport_name="Basketball",
        league_id="league-epl",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="Provider fixture declares sport 'Basketball'.*does not match"):
        normalizer.normalize_fixture(pf, football, league)


def test_normalize_fixture_matching_league_succeeds(normalizer: ProviderDataNormalizer) -> None:
    """Verify matching league relationship succeeds via external ID or domain identity."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Premier League", sport_name="football", external_id="league-epl-01"),
        sport,
    )
    # 1. Matching by provider external ID
    pf1 = ProviderFixture(
        external_id="fix-m1",
        sport_name="football",
        league_id="league-epl-01",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    f1 = normalizer.normalize_fixture(pf1, sport, league)
    assert f1.league == league

    # 2. Matching by canonical league identity
    pf2 = ProviderFixture(
        external_id="fix-m2",
        sport_name="football",
        league_id="football:premier_league",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    f2 = normalizer.normalize_fixture(pf2, sport, league)
    assert f2.league == league


def test_normalize_fixture_mismatching_league_fails(normalizer: ProviderDataNormalizer) -> None:
    """Verify provider fixture declaring inconsistent league is rejected with NormalizationError."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Premier League", sport_name="football", external_id="league-epl"),
        sport,
    )
    # Declares "league-laliga-01" but passed League is Premier League
    pf = ProviderFixture(
        external_id="fix-bad-league",
        sport_name="football",
        league_id="league-laliga-01",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
    )
    with pytest.raises(NormalizationError, match="Provider fixture declares league 'league-laliga-01'.*does not match"):
        normalizer.normalize_fixture(pf, sport, league)


def test_normalize_fixture_valid_hierarchy_succeeds(normalizer: ProviderDataNormalizer) -> None:
    """Verify a complete, valid sport/league/fixture relationship hierarchy succeeds cleanly."""
    sport = normalizer.normalize_sport(ProviderSport(name="basketball"))
    league = normalizer.normalize_league(
        ProviderLeague(name="NBA", sport_name="basketball", country="USA", external_id="nba-ext-01"),
        sport,
    )
    pf = ProviderFixture(
        external_id="bb-fix-01",
        sport_name="basketball",
        league_id="nba-ext-01",
        home_team="Lakers",
        away_team="Celtics",
        start_time=datetime(2026, 11, 20, 2, 30, tzinfo=timezone.utc),
    )
    fixture = normalizer.normalize_fixture(pf, sport, league)
    assert fixture.sport == sport
    assert fixture.league == league
    assert fixture.home_team == "Lakers"
    assert fixture.away_team == "Celtics"


# ============================================================================
# CORRECTION 1 TESTS — SEPARATE PROVIDER EXTERNAL IDs FROM DOMAIN IDENTITIES
# ============================================================================


def test_identity_separation_provider_external_ids_retained_on_dtos(
    normalizer: ProviderDataNormalizer,
) -> None:
    """Verify provider external IDs are strictly preserved on provider DTOs across normalization."""
    ps = ProviderSport(name="football", external_id="prov-sport-100")
    pl = ProviderLeague(name="La Liga", sport_name="football", country="Spain", external_id="prov-lg-200")
    pf = ProviderFixture(
        external_id="prov-fix-300",
        sport_name="football",
        league_id="prov-lg-200",
        home_team="Real Madrid",
        away_team="Barcelona",
        start_time=datetime(2026, 11, 21, 20, 0, tzinfo=timezone.utc),
    )
    pm = ProviderMarket(name="Match Winner", fixture_external_id="prov-fix-300", external_id="prov-mkt-400")
    sel = ProviderSelection(name="Real Madrid", market_external_id="prov-mkt-400", external_id="prov-sel-500", odds=Decimal("2.10"))

    sport = normalizer.normalize_sport(ps)
    league = normalizer.normalize_league(pl, sport)
    fixture = normalizer.normalize_fixture(pf, sport, league)
    market = normalizer.normalize_market(pm, fixture)
    selection = normalizer.normalize_selection(sel, market)

    # Provider DTOs strictly retain their external IDs
    assert ps.external_id == "prov-sport-100"
    assert pl.external_id == "prov-lg-200"
    assert pf.external_id == "prov-fix-300"
    assert pm.external_id == "prov-mkt-400"
    assert sel.external_id == "prov-sel-500"

    # Domain entities do NOT use provider external IDs as canonical identities
    assert league.identity != "prov-lg-200"
    assert league.league_id is None
    assert fixture.fixture_id != "prov-fix-300"
    assert market.identity != "prov-mkt-400"
    assert market.market_id is None
    assert selection.identity != "prov-sel-500"
    assert selection.selection_id is None


def test_identity_separation_changing_provider_external_id_preserves_domain_identity(
    normalizer: ProviderDataNormalizer,
) -> None:
    """Verify changing a provider's external ID does NOT silently redefine domain identity."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Champions League", sport_name="football", external_id="ucl"),
        sport,
    )

    start_time = datetime(2026, 12, 1, 20, 0, tzinfo=timezone.utc)
    pf_provider_a = ProviderFixture(
        external_id="provider-a-id-999",
        sport_name="football",
        league_id="ucl",
        home_team="Bayern Munich",
        away_team="Real Madrid",
        start_time=start_time,
    )
    pf_provider_b = ProviderFixture(
        external_id="provider-b-id-777",
        sport_name="football",
        league_id="ucl",
        home_team="Bayern Munich",
        away_team="Real Madrid",
        start_time=start_time,
    )

    fix_a = normalizer.normalize_fixture(pf_provider_a, sport, league)
    # Using a fresh normalizer to simulate reading from an alternate provider
    normalizer_b = ProviderDataNormalizer()
    league_b = normalizer_b.normalize_league(
        ProviderLeague(name="Champions League", sport_name="football", external_id="ucl"),
        sport,
    )
    fix_b = normalizer_b.normalize_fixture(pf_provider_b, sport, league_b)

    # Both resolve to the exact same canonical domain identity despite different external IDs
    assert fix_a.fixture_id == fix_b.fixture_id
    assert fix_a.fixture_id == "football:champions_league:bayern_munich_vs_real_madrid:20261201"
    assert fix_a.fixture_id != "provider-a-id-999"
    assert fix_b.fixture_id != "provider-b-id-777"


def test_identity_separation_explicit_custom_mapping_respected() -> None:
    """Verify explicit custom mapping at the boundary overrides default identity derivation."""
    mapper = ProviderIdentityMapper()
    mapper.register_fixture_mapping("ext-partner-xyz", "custom-internal-ucl-final-2026")
    custom_normalizer = ProviderDataNormalizer(identity_mapper=mapper)

    sport = custom_normalizer.normalize_sport(ProviderSport(name="football"))
    league = custom_normalizer.normalize_league(
        ProviderLeague(name="Champions League", sport_name="football", external_id="ucl"),
        sport,
    )
    pf = ProviderFixture(
        external_id="ext-partner-xyz",
        sport_name="football",
        league_id="ucl",
        home_team="Bayern Munich",
        away_team="Real Madrid",
        start_time=datetime(2026, 12, 1, 20, 0, tzinfo=timezone.utc),
    )
    fixture = custom_normalizer.normalize_fixture(pf, sport, league)
    assert fixture.fixture_id == "custom-internal-ucl-final-2026"


def test_custom_mappings_isolated_between_providers_with_identical_external_id() -> None:
    """Verify identical external IDs from different providers do not share or overwrite custom mappings."""
    mapper = ProviderIdentityMapper()

    # Register custom mappings for the same external ID under two distinct providers
    shared_ext_id = "shared-match-id-100"
    mapper.register_fixture_mapping(
        external_id=shared_ext_id,
        internal_id="domain-fixture-alpha-custom",
        provider_name="provider_alpha",
    )
    mapper.register_fixture_mapping(
        external_id=shared_ext_id,
        internal_id="domain-fixture-beta-custom",
        provider_name="provider_beta",
    )

    # 1. Lookup isolation
    assert mapper.get_internal_id("provider_alpha", "FIXTURE", shared_ext_id) == "domain-fixture-alpha-custom"
    assert mapper.get_internal_id("provider_beta", "FIXTURE", shared_ext_id) == "domain-fixture-beta-custom"
    # Unmapped third provider has no custom mapping for this external ID
    assert mapper.get_internal_id("provider_gamma", "FIXTURE", shared_ext_id) is None

    # 2. Normalization isolation
    normalizer = ProviderDataNormalizer(identity_mapper=mapper)
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(
        ProviderLeague(name="Premier League", sport_name="football", external_id="epl"),
        sport,
    )
    pf_alpha = ProviderFixture(
        external_id=shared_ext_id,
        sport_name="football",
        league_id="epl",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc),
    )
    pf_beta = ProviderFixture(
        external_id=shared_ext_id,
        sport_name="football",
        league_id="epl",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc),
    )
    pf_gamma = ProviderFixture(
        external_id=shared_ext_id,
        sport_name="football",
        league_id="epl",
        home_team="Arsenal",
        away_team="Chelsea",
        start_time=datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc),
    )

    fix_alpha = normalizer.normalize_fixture(pf_alpha, sport, league, provider_name="provider_alpha")
    fix_beta = normalizer.normalize_fixture(pf_beta, sport, league, provider_name="provider_beta")
    fix_gamma = normalizer.normalize_fixture(pf_gamma, sport, league, provider_name="provider_gamma")

    assert fix_alpha.fixture_id == "domain-fixture-alpha-custom"
    assert fix_beta.fixture_id == "domain-fixture-beta-custom"
    assert fix_gamma.fixture_id == "football:premier_league:arsenal_vs_chelsea:20261201"
    assert fix_alpha.fixture_id != fix_beta.fixture_id


def test_custom_mappings_isolated_between_different_entity_types() -> None:
    """Verify custom mappings for the same external ID remain isolated across entity types."""
    mapper = ProviderIdentityMapper()

    shared_ext_id = "shared-cross-type-id-555"
    mapper.register_custom_mapping("provider_alpha", "SPORT", shared_ext_id, "internal-sport-custom")
    mapper.register_custom_mapping("provider_alpha", "LEAGUE", shared_ext_id, "internal-league-custom")
    mapper.register_custom_mapping("provider_alpha", "FIXTURE", shared_ext_id, "internal-fixture-custom")
    mapper.register_custom_mapping("provider_alpha", "MARKET", shared_ext_id, "internal-market-custom")
    mapper.register_custom_mapping("provider_alpha", "SELECTION", shared_ext_id, "internal-selection-custom")

    # Each entity type retrieves its exact assigned internal ID
    assert mapper.get_internal_id("provider_alpha", "SPORT", shared_ext_id) == "internal-sport-custom"
    assert mapper.get_internal_id("provider_alpha", "LEAGUE", shared_ext_id) == "internal-league-custom"
    assert mapper.get_internal_id("provider_alpha", "FIXTURE", shared_ext_id) == "internal-fixture-custom"
    assert mapper.get_internal_id("provider_alpha", "MARKET", shared_ext_id) == "internal-market-custom"
    assert mapper.get_internal_id("provider_alpha", "SELECTION", shared_ext_id) == "internal-selection-custom"

    # Unmapped entity type or other provider cannot retrieve mappings
    assert mapper.get_internal_id("provider_alpha", "UNKNOWN_TYPE", shared_ext_id) is None
    assert mapper.get_internal_id("provider_beta", "FIXTURE", shared_ext_id) is None
    assert mapper.get_internal_id("provider_beta", "MARKET", shared_ext_id) is None

    # Fixture resolution only matches FIXTURE entity type mapping
    league = League(name="Premier League", sport=Sport(name="football"), country="England")
    start = datetime(2026, 12, 1, 15, 0, tzinfo=timezone.utc)
    res_id = mapper.resolve_fixture_id(shared_ext_id, league, "Arsenal", "Chelsea", start, provider_name="provider_alpha")
    assert res_id == "internal-fixture-custom"
    assert res_id != "internal-market-custom"
    assert res_id != "internal-sport-custom"


# ============================================================================
# MARKET AND SELECTION NORMALIZATION TESTS
# ============================================================================


def test_normalize_market_and_line(normalizer: ProviderDataNormalizer) -> None:
    """Verify market line normalization preserves Decimal precision and rejects invalid lines."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="f1",
            sport_name="football",
            league_id="l1",
            home_team="A",
            away_team="B",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )

    # Valid market with line
    pm1 = ProviderMarket(name="Total Goals", fixture_external_id="f1", external_id="m1", line=Decimal("2.5"))
    m1 = normalizer.normalize_market(pm1, fixture)
    assert m1.line == Decimal("2.5")
    assert m1.identity != "m1"
    assert m1.identity == f"{fixture.fixture_id}:total_goals:2.5"
    assert m1.market_id is None

    # Valid market with None line
    pm2 = ProviderMarket(name="Match Winner", fixture_external_id="f1", external_id="m2", line=None)
    m2 = normalizer.normalize_market(pm2, fixture)
    assert m2.line is None
    assert m2.identity == f"{fixture.fixture_id}:match_winner"
    assert m2.market_id is None

    # Invalid non-finite line
    pm_nan = ProviderMarket(name="Bad Market", fixture_external_id="f1", line="NaN")
    with pytest.raises(NormalizationError, match="finite"):
        normalizer.normalize_market(pm_nan, fixture)


def test_normalize_selection_and_odds(normalizer: ProviderDataNormalizer) -> None:
    """Verify selection odds normalization creates valid Odds and rejects invalid values."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="l1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="f1",
            sport_name="football",
            league_id="l1",
            home_team="A",
            away_team="B",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )
    market = normalizer.normalize_market(
        ProviderMarket(name="MW", fixture_external_id="f1", external_id="m1"),
        fixture,
    )

    # Valid selection with odds
    ps1 = ProviderSelection(name="Arsenal", market_external_id="m1", external_id="s1", odds=Decimal("2.10"))
    sel1 = normalizer.normalize_selection(ps1, market)
    assert sel1.odds is not None
    assert sel1.odds.decimal_value == Decimal("2.10")
    assert sel1.odds.implied_probability == Decimal("1") / Decimal("2.10")
    assert sel1.identity != "s1"
    assert sel1.identity == f"{market.identity}:arsenal"
    assert sel1.selection_id is None

    # Valid selection with None odds
    ps2 = ProviderSelection(name="Arsenal", market_external_id="m1", external_id="s2", odds=None)
    sel2 = normalizer.normalize_selection(ps2, market)
    assert sel2.odds is None

    # Invalid odds < 1.01
    ps_low = ProviderSelection(name="Bad", market_external_id="m1", odds=Decimal("0.95"))
    with pytest.raises(NormalizationError, match="greater than 1.0"):
        normalizer.normalize_selection(ps_low, market)

    # Invalid non-finite odds
    ps_inf = ProviderSelection(name="Bad", market_external_id="m1", odds="Infinity")
    with pytest.raises(NormalizationError, match="finite"):
        normalizer.normalize_selection(ps_inf, market)


def test_market_relationship_validation_matching_accepted(normalizer: ProviderDataNormalizer) -> None:
    """Verify that a market with matching fixture_external_id is accepted."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="lg-1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="fix-100",
            sport_name="football",
            league_id="lg-1",
            home_team="Arsenal",
            away_team="Chelsea",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )

    pm = ProviderMarket(name="Match Winner", fixture_external_id="fix-100", external_id="mkt-1")
    market = normalizer.normalize_market(pm, fixture, expected_fixture_external_id="fix-100")
    assert market.name == "Match Winner"
    assert market.fixture_id == fixture.fixture_id


def test_market_relationship_validation_mismatch_rejected(normalizer: ProviderDataNormalizer) -> None:
    """Verify that a market referencing a different fixture is rejected."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="lg-1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="fix-100",
            sport_name="football",
            league_id="lg-1",
            home_team="Arsenal",
            away_team="Chelsea",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )

    # Market declares unrelated fixture ID
    pm_wrong = ProviderMarket(name="Match Winner", fixture_external_id="fix-999-unrelated", external_id="mkt-1")

    with pytest.raises(NormalizationError, match="references fixture 'fix-999-unrelated'"):
        normalizer.normalize_market(pm_wrong, fixture, expected_fixture_external_id="fix-100")

    # Also fails without explicit expected_fixture_external_id via identity mapper check
    with pytest.raises(NormalizationError, match="references fixture 'fix-999-unrelated'"):
        normalizer.normalize_market(pm_wrong, fixture)


def test_market_relationship_validation_empty_reference_rejected(normalizer: ProviderDataNormalizer) -> None:
    """Verify that a market with empty or missing fixture reference is rejected."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="lg-1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="fix-100",
            sport_name="football",
            league_id="lg-1",
            home_team="Arsenal",
            away_team="Chelsea",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )

    pm_empty = ProviderMarket(name="Match Winner", fixture_external_id="", external_id="mkt-1")
    with pytest.raises(NormalizationError, match="must declare a non-empty fixture_external_id"):
        normalizer.normalize_market(pm_empty, fixture)


def test_league_sport_relationship_mismatch_rejected(normalizer: ProviderDataNormalizer) -> None:
    """Verify that a league declaring a sport differing from the passed domain Sport is rejected."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    pl_bad = ProviderLeague(name="NBA", sport_name="basketball", external_id="lg-nba")

    with pytest.raises(NormalizationError, match="declares sport 'basketball', which does not match passed domain Sport 'football'"):
        normalizer.normalize_league(pl_bad, sport)


def test_selection_market_relationship_mismatch_rejected(normalizer: ProviderDataNormalizer) -> None:
    """Verify that a selection referencing a differing market is rejected."""
    sport = normalizer.normalize_sport(ProviderSport(name="football"))
    league = normalizer.normalize_league(ProviderLeague(name="EPL", sport_name="football", external_id="lg-1"), sport)
    fixture = normalizer.normalize_fixture(
        ProviderFixture(
            external_id="fix-1",
            sport_name="football",
            league_id="lg-1",
            home_team="A",
            away_team="B",
            start_time=datetime(2026, 10, 15, 15, 0, tzinfo=timezone.utc),
        ),
        sport,
        league,
    )
    market = normalizer.normalize_market(
        ProviderMarket(name="MW", fixture_external_id="fix-1", external_id="mkt-target"),
        fixture,
    )

    ps_wrong = ProviderSelection(name="Home", market_external_id="mkt-other", external_id="s1", odds=Decimal("2.00"))
    with pytest.raises(NormalizationError, match="references market 'mkt-other', which does not match expected market 'mkt-target'"):
        normalizer.normalize_selection(ps_wrong, market, expected_market_external_id="mkt-target")
