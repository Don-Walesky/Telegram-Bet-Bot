"""Tests for ProviderMappingRepository."""

from datetime import datetime, timezone
import sqlite3
import pytest

from telegram_bet_bot.persistence.exceptions import PersistenceError
from telegram_bet_bot.persistence.repositories import ProviderMappingRepository


def test_mapping_save_and_retrieve_all_entity_types(test_conn: sqlite3.Connection) -> None:
    """Verify saving and retrieving mappings across all supported provider entity types."""
    repo = ProviderMappingRepository(test_conn)

    entity_types = ["SPORT", "LEAGUE", "FIXTURE", "MARKET", "SELECTION"]
    for entity_type in entity_types:
        ext_id = f"ext-{entity_type.lower()}-100"
        int_id = f"internal-{entity_type.lower()}-canonical"

        repo.save_mapping(
            provider_name="test_provider",
            entity_type=entity_type,
            external_id=ext_id,
            internal_id=int_id,
        )

        assert repo.get_internal_id("test_provider", entity_type, ext_id) == int_id
        assert repo.get_external_id("test_provider", entity_type, int_id) == ext_id
        assert repo.exists("test_provider", entity_type, ext_id) is True


def test_mapping_upsert_behavior(test_conn: sqlite3.Connection) -> None:
    """Verify saving an existing mapping key updates the internal ID without duplicating rows."""
    repo = ProviderMappingRepository(test_conn)

    repo.save_mapping("provider_a", "FIXTURE", "ext-fix-1", "fixture:first")
    assert repo.get_internal_id("provider_a", "FIXTURE", "ext-fix-1") == "fixture:first"

    # Re-save with updated internal ID
    repo.save_mapping("provider_a", "FIXTURE", "ext-fix-1", "fixture:updated")
    assert repo.get_internal_id("provider_a", "FIXTURE", "ext-fix-1") == "fixture:updated"
    assert repo.count(provider_name="provider_a", entity_type="FIXTURE") == 1


def test_identical_external_ids_from_different_providers_remain_distinct(
    test_conn: sqlite3.Connection,
) -> None:
    """Verify that identical external IDs from different providers do not collide."""
    repo = ProviderMappingRepository(test_conn)

    repo.save_mapping("provider_alpha", "FIXTURE", "same-ext-id", "domain:fixture:alpha")
    repo.save_mapping("provider_beta", "FIXTURE", "same-ext-id", "domain:fixture:beta")

    assert repo.get_internal_id("provider_alpha", "FIXTURE", "same-ext-id") == "domain:fixture:alpha"
    assert repo.get_internal_id("provider_beta", "FIXTURE", "same-ext-id") == "domain:fixture:beta"

    assert repo.count(entity_type="FIXTURE") == 2
    assert repo.count(provider_name="provider_alpha") == 1
    assert repo.count(provider_name="provider_beta") == 1


def test_list_external_ids_for_single_internal_entity(test_conn: sqlite3.Connection) -> None:
    """Verify that multiple external IDs mapped to the same domain entity can be queried."""
    repo = ProviderMappingRepository(test_conn)

    # Provider changes external ID over time, both mapped to the same internal fixture
    repo.save_mapping("prov", "FIXTURE", "old-ext-id", "domain:fixture:100")
    repo.save_mapping("prov", "FIXTURE", "new-ext-id", "domain:fixture:100")

    ext_ids = repo.list_external_ids("prov", "FIXTURE", "domain:fixture:100")
    assert "old-ext-id" in ext_ids
    assert "new-ext-id" in ext_ids
    assert len(ext_ids) == 2


def test_invalid_entity_type_rejected(test_conn: sqlite3.Connection) -> None:
    """Verify that unapproved entity types are rejected by the repository and schema."""
    repo = ProviderMappingRepository(test_conn)

    with pytest.raises(PersistenceError, match="Invalid entity type 'UNSUPPORTED'"):
        repo.save_mapping("prov", "UNSUPPORTED", "ext-1", "int-1")


def test_empty_fields_rejected(test_conn: sqlite3.Connection) -> None:
    """Verify empty string identifiers are rejected."""
    repo = ProviderMappingRepository(test_conn)

    with pytest.raises(PersistenceError, match="Provider name must be a non-empty string"):
        repo.save_mapping("", "FIXTURE", "ext-1", "int-1")

    with pytest.raises(PersistenceError, match="External ID must be a non-empty string"):
        repo.save_mapping("prov", "FIXTURE", "  ", "int-1")

    with pytest.raises(PersistenceError, match="Internal ID must be a non-empty string"):
        repo.save_mapping("prov", "FIXTURE", "ext-1", "  ")


def test_delete_mapping(test_conn: sqlite3.Connection) -> None:
    """Verify mapping deletion."""
    repo = ProviderMappingRepository(test_conn)
    repo.save_mapping("prov", "SPORT", "ext-sp", "football")

    assert repo.exists("prov", "SPORT", "ext-sp") is True
    assert repo.delete_mapping("prov", "SPORT", "ext-sp") is True
    assert repo.exists("prov", "SPORT", "ext-sp") is False
    assert repo.delete_mapping("prov", "SPORT", "ext-sp") is False
