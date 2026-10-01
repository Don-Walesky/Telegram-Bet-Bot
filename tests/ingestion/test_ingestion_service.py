"""Tests for FixtureIngestionService orchestrating Provider to Persistence."""

from datetime import datetime, timezone
from decimal import Decimal
import pytest

from telegram_bet_bot.ingestion.exceptions import IngestionError, NormalizationError
from telegram_bet_bot.ingestion.mock_provider import MockSportsDataProvider
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderFixtureBundle,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.normalizer import (
    ProviderDataNormalizer,
    ProviderIdentityMapper,
)
from telegram_bet_bot.ingestion.service import FixtureIngestionService
from telegram_bet_bot.persistence import Database, PersistenceError
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    ProviderMappingRepository,
    SelectionRepository,
    SportRepository,
)


def test_ingest_sports(test_db: Database, mock_provider: MockSportsDataProvider) -> None:
    """Verify ingest_sports persists all provider sports cleanly."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    sports = service.ingest_sports()

    assert len(sports) >= 3
    with test_db.connection() as conn:
        repo = SportRepository(conn)
        persisted = repo.list_all()
        assert len(persisted) >= 3
        persisted_names = {s.name for s in persisted}
        assert "football" in persisted_names
        assert "basketball" in persisted_names
        assert "tennis" in persisted_names


def test_ingest_leagues(test_db: Database, mock_provider: MockSportsDataProvider) -> None:
    """Verify ingest_leagues persists leagues and associated sports."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    leagues = service.ingest_leagues()

    assert len(leagues) >= 4
    with test_db.connection() as conn:
        repo = LeagueRepository(conn)
        persisted = repo.list_all()
        assert len(persisted) >= 4
        league_names = {l.name for l in persisted}
        assert "Premier League" in league_names
        assert "NBA" in league_names


def test_ingest_fixture_bundle_success(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify ingest_fixture_bundle persists complete hierarchy atomically.

    Proves:
    1. Provider external IDs are preserved at the provider boundary on the DTO.
    2. Internal domain IDs are separate from provider external IDs.
    3. Hierarchy is written and retrievable via repositories.
    """
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    result = service.ingest_fixture_bundle(sample_bundle)

    # 1. External ID retained on DTO, decoupled from domain fixture_id
    assert sample_bundle.fixture.external_id == "ext-fix-100"
    assert result.fixture_id != sample_bundle.fixture.external_id
    assert result.fixture_id == "football:champions_league:bayern_munich_vs_real_madrid:20261201"
    assert len(result.markets) == 1
    assert len(result.selections) == 2

    # 2. Verify directly via Phase 3 repositories
    with test_db.connection() as conn:
        sport_repo = SportRepository(conn)
        league_repo = LeagueRepository(conn)
        fixture_repo = FixtureRepository(conn)
        market_repo = MarketRepository(conn)
        selection_repo = SelectionRepository(conn)

        assert sport_repo.exists("football")
        assert league_repo.get_by_identity("football:champions_league") is not None

        retrieved_fix = fixture_repo.get(result.fixture_id)
        assert retrieved_fix.home_team == "Bayern Munich"
        assert retrieved_fix.away_team == "Real Madrid"

        retrieved_markets = market_repo.list_by_fixture(result.fixture_id)
        assert len(retrieved_markets) == 1
        assert retrieved_markets[0].identity == f"{result.fixture_id}:match_winner"

        retrieved_selections = selection_repo.list_by_market(retrieved_markets[0].identity)
        assert len(retrieved_selections) == 2


def test_ingest_fixture_bundle_idempotent(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify re-ingesting identical bundle updates records and creates no duplicates."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    # Ingest once
    res1 = service.ingest_fixture_bundle(sample_bundle)

    # Ingest twice
    res2 = service.ingest_fixture_bundle(sample_bundle)

    assert res1.fixture_id == res2.fixture_id

    with test_db.connection() as conn:
        fix_repo = FixtureRepository(conn)
        fixtures = fix_repo.list_all()
        matching = [f for f in fixtures if f.fixture_id == res1.fixture_id]
        assert len(matching) == 1


def test_ingest_fixture_bundle_updates_existing_record(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify re-ingesting a bundle with updated kickoff time and odds updates the records."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    res1 = service.ingest_fixture_bundle(sample_bundle)

    # Update kickoff time and selection odds
    new_kickoff = datetime(2026, 12, 1, 21, 0, tzinfo=timezone.utc)
    updated_fixture = ProviderFixture(
        external_id=sample_bundle.fixture.external_id,
        sport_name=sample_bundle.fixture.sport_name,
        league_id=sample_bundle.fixture.league_id,
        home_team=sample_bundle.fixture.home_team,
        away_team=sample_bundle.fixture.away_team,
        start_time=new_kickoff,
        status="IN_PLAY",
    )
    updated_selection = ProviderSelection(
        name="Bayern Munich",
        market_external_id=sample_bundle.markets[0].external_id or "",
        external_id="ext-sel-100-h",
        odds=Decimal("2.65"),
    )

    updated_bundle = ProviderFixtureBundle(
        fixture=updated_fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=sample_bundle.markets,
        selections=[updated_selection, sample_bundle.selections[1]],
    )

    res2 = service.ingest_fixture_bundle(updated_bundle)
    assert res1.fixture_id == res2.fixture_id

    with test_db.connection() as conn:
        fix_repo = FixtureRepository(conn)
        sel_repo = SelectionRepository(conn)

        persisted_fix = fix_repo.get(res1.fixture_id)
        assert persisted_fix.scheduled_start_time == new_kickoff
        assert persisted_fix.status.value == "IN_PLAY"

        persisted_sel = sel_repo.get(res2.selections[0].identity)
        assert persisted_sel.odds is not None
        assert persisted_sel.odds.decimal_value == Decimal("2.65")


def test_ingest_fixture_bundle_atomic_rollback_on_normalization_failure(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that a corrupted element inside a bundle rolls back the entire hierarchy."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    # Corrupt selection odds (< 1.01)
    bad_selection = ProviderSelection(
        name="Invalid Selection",
        market_external_id="ext-mkt-100-mw",
        external_id="bad-sel",
        odds=Decimal("0.50"),
    )

    corrupted_bundle = ProviderFixtureBundle(
        fixture=sample_bundle.fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=sample_bundle.markets,
        selections=[bad_selection],
    )

    with pytest.raises(NormalizationError, match="greater than 1.0"):
        service.ingest_fixture_bundle(corrupted_bundle)

    # Confirm that NOTHING from this fixture was persisted
    with test_db.connection() as conn:
        fix_repo = FixtureRepository(conn)
        assert fix_repo.list_all() == []
        assert conn.execute("SELECT count(*) FROM markets").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM selections").fetchone()[0] == 0


def test_ingest_fixture_bundle_missing_market_reference_raises_and_rolls_back(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify selection referencing unknown market aborts ingestion with no persisted artifacts."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    orphan_selection = ProviderSelection(
        name="Orphan",
        market_external_id="nonexistent-market-id",
        odds=Decimal("2.00"),
    )

    bundle = ProviderFixtureBundle(
        fixture=sample_bundle.fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=sample_bundle.markets,
        selections=[orphan_selection],
    )

    with pytest.raises(IngestionError, match="references market.*which was not found"):
        service.ingest_fixture_bundle(bundle)

    with test_db.connection() as conn:
        assert FixtureRepository(conn).list_all() == []


# ============================================================================
# CORRECTION 3 TEST — REAL DATABASE TRANSACTION ROLLBACK
# ============================================================================


def test_ingest_fixture_bundle_real_persistence_rollback_on_database_failure(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Test real persistence-layer failure after earlier records have already been written (Correction 3).

    Required behavior:
    BEGIN TRANSACTION
      save Sport -> succeeds (written to SQLite)
      save League -> succeeds (written to SQLite)
      save Fixture -> succeeds (written to SQLite)
      save Market -> succeeds (written to SQLite)
      save Selection -> FAILS (SQLite aborts at persistence time)
    ROLLBACK
    After the failure, NONE of the earlier records remain in SQLite.
    """
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    # Attach an explicit SQLite trigger to 'selections' table that forces a failure
    # at the real SQLite engine level during selection INSERT.
    with test_db.connection() as conn:
        conn.execute(
            """
            CREATE TRIGGER trigger_fail_selection_insert
            BEFORE INSERT ON selections
            BEGIN
                SELECT RAISE(ABORT, 'Simulated SQLite failure during Selection insertion');
            END;
            """
        )

    # Ingestion successfully normalizes the bundle, executes SQL INSERT for Sport,
    # League, Fixture, and Market, but FAILS during Selection insertion inside the transaction.
    with pytest.raises(PersistenceError, match="Simulated SQLite failure during Selection insertion"):
        service.ingest_fixture_bundle(sample_bundle)

    # Verify that the transaction rolled back completely and NONE of the partially persisted
    # entities or identity mappings exist in the database.
    with test_db.connection() as conn:
        sport_repo = SportRepository(conn)
        league_repo = LeagueRepository(conn)
        fixture_repo = FixtureRepository(conn)

        assert not sport_repo.exists("football")
        assert league_repo.get_by_identity("football:champions_league") is None
        assert fixture_repo.list_all() == []
        assert conn.execute("SELECT count(*) FROM markets").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM selections").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM provider_identity_mappings").fetchone()[0] == 0


def test_durable_identity_mapping_survives_new_mapper_instance(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that identity mappings survive the creation of a new mapper instance."""
    service1 = FixtureIngestionService(db=test_db, provider=mock_provider)
    res1 = service1.ingest_fixture_bundle(sample_bundle)

    # Verify mappings exist in SQLite
    with test_db.connection() as conn:
        mapping_repo = ProviderMappingRepository(conn)
        assert mapping_repo.exists("mock_provider", "FIXTURE", sample_bundle.fixture.external_id)
        assert mapping_repo.get_internal_id("mock_provider", "FIXTURE", sample_bundle.fixture.external_id) == res1.fixture_id
        assert mapping_repo.exists("mock_provider", "SPORT", sample_bundle.sport.external_id)
        assert mapping_repo.exists("mock_provider", "LEAGUE", sample_bundle.league.external_id)
        assert mapping_repo.exists("mock_provider", "MARKET", sample_bundle.markets[0].external_id)
        assert mapping_repo.exists("mock_provider", "SELECTION", sample_bundle.selections[0].external_id)

    # Instantiate a completely fresh mapper instance with no in-memory state
    mapper2 = ProviderIdentityMapper(db=test_db)
    resolved_id = mapper2.get_internal_id("mock_provider", "FIXTURE", sample_bundle.fixture.external_id)
    assert resolved_id == res1.fixture_id

    # Ingest using a new service instance backed by mapper2
    service2 = FixtureIngestionService(
        db=test_db,
        provider=mock_provider,
        normalizer=ProviderDataNormalizer(identity_mapper=mapper2),
    )
    res2 = service2.ingest_fixture_bundle(sample_bundle)
    assert res2.fixture_id == res1.fixture_id


def test_durable_identity_mapping_survives_closing_and_reopening_database(
    tmp_path,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that identity mappings survive closing and reopening the SQLite database on disk."""
    from datetime import timedelta
    from pathlib import Path

    db_file = tmp_path / "restart_test.db"
    db1 = Database(db_file)
    db1.initialize()
    provider = MockSportsDataProvider()
    service1 = FixtureIngestionService(db=db1, provider=provider)
    res1 = service1.ingest_fixture_bundle(sample_bundle)

    # Close/dereference db1 and open a new Database instance pointing to the same file
    del service1
    del db1

    db2 = Database(db_file)
    service2 = FixtureIngestionService(db=db2, provider=provider)

    # Ingest updated fixture with kickoff moved forward by 2 days
    new_kickoff = sample_bundle.fixture.start_time + timedelta(days=2)
    updated_fixture = ProviderFixture(
        external_id=sample_bundle.fixture.external_id,
        sport_name=sample_bundle.fixture.sport_name,
        league_id=sample_bundle.fixture.league_id,
        home_team=sample_bundle.fixture.home_team,
        away_team=sample_bundle.fixture.away_team,
        start_time=new_kickoff,
        status="SCHEDULED",
    )
    updated_bundle = ProviderFixtureBundle(
        fixture=updated_fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=sample_bundle.markets,
        selections=sample_bundle.selections,
    )

    res2 = service2.ingest_fixture_bundle(updated_bundle)

    # Crucial assertion: the fixture ID remains identical to the first ingestion
    # because the durable mapping survived database restart!
    assert res2.fixture_id == res1.fixture_id

    with db2.connection() as conn:
        fix_repo = FixtureRepository(conn)
        persisted = fix_repo.get(res1.fixture_id)
        assert persisted.scheduled_start_time == new_kickoff


def test_repeated_ingestion_remains_idempotent(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that repeated ingestion of the same bundle is idempotent and creates no duplicate rows."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    res1 = service.ingest_fixture_bundle(sample_bundle)
    res2 = service.ingest_fixture_bundle(sample_bundle)

    assert res1.fixture_id == res2.fixture_id

    with test_db.connection() as conn:
        assert conn.execute("SELECT count(*) FROM fixtures").fetchone()[0] == 1
        assert conn.execute("SELECT count(*) FROM markets").fetchone()[0] == len(sample_bundle.markets)
        assert conn.execute("SELECT count(*) FROM selections").fetchone()[0] == len(sample_bundle.selections)
        assert (
            conn.execute("SELECT count(*) FROM provider_identity_mappings WHERE entity_type='FIXTURE'").fetchone()[0]
            == 1
        )


def test_identical_external_ids_from_different_providers_remain_distinct(
    test_db: Database,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that the same external ID from two different providers maps to distinct internal entities."""
    prov_a = MockSportsDataProvider(provider_name="provider_alpha")
    prov_b = MockSportsDataProvider(provider_name="provider_beta")

    service_a = FixtureIngestionService(db=test_db, provider=prov_a)
    service_b = FixtureIngestionService(db=test_db, provider=prov_b)

    # Ingest bundle with external_id="ext-fix-100" from provider_alpha
    res_a = service_a.ingest_fixture_bundle(sample_bundle)

    # Create bundle from provider_beta with the SAME external_id="ext-fix-100", but for a different match
    fixture_b = ProviderFixture(
        external_id=sample_bundle.fixture.external_id,  # Same external ID!
        sport_name="football",
        league_id="ext-league-1",
        home_team="Liverpool",
        away_team="Manchester City",
        start_time=sample_bundle.fixture.start_time,
        status="SCHEDULED",
    )
    market_b = ProviderMarket(
        name="Match Winner",
        fixture_external_id=sample_bundle.fixture.external_id,
        external_id="ext-mkt-100-mw",
    )
    sel_b = ProviderSelection(
        name="Liverpool",
        market_external_id="ext-mkt-100-mw",
        external_id="ext-sel-100-h",
        odds=Decimal("2.10"),
    )
    bundle_b = ProviderFixtureBundle(
        fixture=fixture_b,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=[market_b],
        selections=[sel_b],
    )

    res_b = service_b.ingest_fixture_bundle(bundle_b)

    # Internal IDs must be distinct
    assert res_a.fixture_id != res_b.fixture_id

    with test_db.connection() as conn:
        mapping_repo = ProviderMappingRepository(conn)
        assert (
            mapping_repo.get_internal_id("provider_alpha", "FIXTURE", sample_bundle.fixture.external_id)
            == res_a.fixture_id
        )
        assert (
            mapping_repo.get_internal_id("provider_beta", "FIXTURE", sample_bundle.fixture.external_id)
            == res_b.fixture_id
        )
        assert conn.execute("SELECT count(*) FROM fixtures").fetchone()[0] == 2


def test_provider_external_id_change_preserves_domain_identity_when_reliably_matched(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that when a provider changes an external ID, the existing domain entity is reused if matched."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    res1 = service.ingest_fixture_bundle(sample_bundle)

    # Provider changes external ID from "ext-fix-100" to "ext-fix-100-v2", but for the exact same match
    new_fixture = ProviderFixture(
        external_id="ext-fix-100-v2",
        sport_name=sample_bundle.fixture.sport_name,
        league_id=sample_bundle.fixture.league_id,
        home_team=sample_bundle.fixture.home_team,
        away_team=sample_bundle.fixture.away_team,
        start_time=sample_bundle.fixture.start_time,
        status="SCHEDULED",
    )
    new_market = ProviderMarket(
        name=sample_bundle.markets[0].name,
        fixture_external_id="ext-fix-100-v2",
        external_id="ext-mkt-100-mw-v2",
    )
    new_sel_h = ProviderSelection(
        name=sample_bundle.selections[0].name,
        market_external_id="ext-mkt-100-mw-v2",
        external_id="ext-sel-100-h-v2",
        odds=Decimal("2.50"),
    )
    new_bundle = ProviderFixtureBundle(
        fixture=new_fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=[new_market],
        selections=[new_sel_h],
    )

    res2 = service.ingest_fixture_bundle(new_bundle)

    # The domain fixture ID is preserved without creating a duplicate domain fixture
    assert res2.fixture_id == res1.fixture_id

    with test_db.connection() as conn:
        assert conn.execute("SELECT count(*) FROM fixtures").fetchone()[0] == 1
        mapping_repo = ProviderMappingRepository(conn)
        assert (
            mapping_repo.get_internal_id("mock_provider", "FIXTURE", "ext-fix-100")
            == res1.fixture_id
        )
        assert (
            mapping_repo.get_internal_id("mock_provider", "FIXTURE", "ext-fix-100-v2")
            == res1.fixture_id
        )


def test_market_to_fixture_mismatch_in_bundle_rejected_and_leaves_no_records(
    test_db: Database,
    mock_provider: MockSportsDataProvider,
    sample_bundle: ProviderFixtureBundle,
) -> None:
    """Verify that a market referencing a differing fixture is rejected before persisting and leaves 0 records."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)

    mismatched_market = ProviderMarket(
        name="Match Winner",
        fixture_external_id="unrelated-ext-fix-999",
        external_id="mkt-unrelated",
    )
    mismatched_bundle = ProviderFixtureBundle(
        fixture=sample_bundle.fixture,
        sport=sample_bundle.sport,
        league=sample_bundle.league,
        markets=[mismatched_market],
        selections=[],
    )

    with pytest.raises(NormalizationError, match="references fixture 'unrelated-ext-fix-999'"):
        service.ingest_fixture_bundle(mismatched_bundle)

    # Ensure zero partial database records exist
    with test_db.connection() as conn:
        assert conn.execute("SELECT count(*) FROM fixtures").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM markets").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM selections").fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM provider_identity_mappings").fetchone()[0] == 0


def test_ingest_upcoming_fixtures(test_db: Database, mock_provider: MockSportsDataProvider) -> None:
    """Verify batch ingestion of all upcoming fixtures from provider."""
    service = FixtureIngestionService(db=test_db, provider=mock_provider)
    summary = service.ingest_upcoming_fixtures()

    assert summary.fixtures_count >= 4
    assert summary.sports_count >= 3
    assert summary.leagues_count >= 4
    assert summary.markets_count >= 5
    assert summary.selections_count >= 10

    # Verify queryable from SQLite
    with test_db.connection() as conn:
        fixtures = FixtureRepository(conn).list_all()
        assert len(fixtures) == summary.fixtures_count
        mapping_count = conn.execute("SELECT count(*) FROM provider_identity_mappings").fetchone()[0]
        assert mapping_count > 0
