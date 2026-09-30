"""Tests for SQLite database management, connection lifecycle, and schema initialization."""

from pathlib import Path
import sqlite3
import pytest

from telegram_bet_bot.domain import Fixture, League, Sport
from telegram_bet_bot.persistence import Database, initialize_database
from telegram_bet_bot.persistence.exceptions import DatabaseInitializationError
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    SportRepository,
)


def test_database_initialization_creates_tables(test_db: Database, test_conn: sqlite3.Connection) -> None:
    """Verify that initialize_database creates all required domain tables and indexes."""
    cursor = test_conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = {row["name"] for row in cursor.fetchall()}

    expected_tables = {"sports", "leagues", "fixtures", "markets", "selections"}
    assert expected_tables.issubset(tables)

    cursor = test_conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%';")
    indexes = {row["name"] for row in cursor.fetchall()}
    assert "idx_leagues_sport" in indexes
    assert "idx_fixtures_sport" in indexes
    assert "idx_fixtures_league" in indexes
    assert "idx_fixtures_scheduled" in indexes
    assert "idx_fixtures_status" in indexes
    assert "idx_markets_fixture" in indexes
    assert "idx_selections_market" in indexes


def test_database_initialization_is_idempotent(test_db: Database, test_conn: sqlite3.Connection) -> None:
    """Verify that running initialize multiple times is safe and preserves data."""
    test_conn.execute("INSERT INTO sports (identity, name) VALUES ('tennis', 'tennis');")
    test_conn.commit()

    # Re-initialize on existing database
    test_db.initialize()

    row = test_conn.execute("SELECT name FROM sports WHERE identity = 'tennis';").fetchone()
    assert row is not None
    assert row["name"] == "tennis"


def test_foreign_keys_strictly_enforced(test_conn: sqlite3.Connection) -> None:
    """Verify that SQLite connection enforces foreign keys by default."""
    row = test_conn.execute("PRAGMA foreign_keys;").fetchone()
    assert row[0] == 1

    # Attempting to insert a league with nonexistent sport must violate foreign keys
    with pytest.raises(sqlite3.IntegrityError, match="FOREIGN KEY constraint failed"):
        test_conn.execute(
            "INSERT INTO leagues (identity, name, sport_name) VALUES ('EPL', 'Premier League', 'nonexistent_sport');"
        )


def test_connection_context_manager_cleanup(tmp_path: Path) -> None:
    """Verify connection context manager closes the connection cleanly."""
    db_file = tmp_path / "cleanup_test.db"
    db = Database(db_path=db_file)
    db.initialize()

    with db.connection() as conn:
        assert isinstance(conn, sqlite3.Connection)
        conn.execute("SELECT 1;")
        active_conn = conn

    # After exiting context, active_conn should be closed
    with pytest.raises(sqlite3.ProgrammingError):
        active_conn.execute("SELECT 1;")


def test_transaction_commit_on_success(test_db: Database, test_conn: sqlite3.Connection) -> None:
    """Verify that successful block inside transaction context commits changes."""
    with test_db.transaction(test_conn):
        test_conn.execute("INSERT INTO sports (identity, name) VALUES ('cricket', 'cricket');")

    # Read back in new query
    row = test_conn.execute("SELECT name FROM sports WHERE identity = 'cricket';").fetchone()
    assert row is not None
    assert row["name"] == "cricket"


def test_transaction_rollback_on_failure(test_db: Database, test_conn: sqlite3.Connection) -> None:
    """Verify that an exception inside transaction context rolls back changes."""
    with pytest.raises(RuntimeError, match="Simulated failure"):
        with test_db.transaction(test_conn):
            test_conn.execute("INSERT INTO sports (identity, name) VALUES ('rugby', 'rugby');")
            raise RuntimeError("Simulated failure")

    row = test_conn.execute("SELECT name FROM sports WHERE identity = 'rugby';").fetchone()
    assert row is None


def test_parent_directory_creation_for_database(tmp_path: Path) -> None:
    """Verify that creating a database with a deeply nested directory automatically creates parents."""
    nested_path = tmp_path / "deep" / "nested" / "path" / "app.db"
    assert not nested_path.parent.exists()

    db = Database(db_path=nested_path)
    db.initialize()

    assert nested_path.exists()
    assert nested_path.is_file()


def test_multi_repository_transaction_atomic_rollback(
    test_db: Database,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify multi-repository atomic transaction rollback:

    BEGIN TRANSACTION -> save Sport -> save League -> save Fixture -> force error -> ROLLBACK.
    Confirms that Sport, League, and Fixture are all completely rolled back and do not exist.
    """
    with test_db.connection() as conn:
        sport_repo = SportRepository(conn)
        league_repo = LeagueRepository(conn)
        fixture_repo = FixtureRepository(conn)

        with pytest.raises(RuntimeError, match="Forced error inside transaction"):
            with test_db.transaction(conn):
                sport_repo.save(sample_sport)
                league_repo.save(sample_league)
                fixture_repo.save(sample_fixture)
                raise RuntimeError("Forced error inside transaction")

        # Verify on this connection that no entity exists
        assert sport_repo.get_by_identity(sample_sport.name) is None
        assert league_repo.get_by_identity(sample_league.identity) is None
        assert fixture_repo.get_by_id(sample_fixture.fixture_id) is None

    # Verify on a completely fresh connection that no entity was committed to disk
    with test_db.connection() as fresh_conn:
        assert SportRepository(fresh_conn).get_by_identity(sample_sport.name) is None
        assert LeagueRepository(fresh_conn).get_by_identity(sample_league.identity) is None
        assert FixtureRepository(fresh_conn).get_by_id(sample_fixture.fixture_id) is None


def test_multi_repository_transaction_atomic_commit(
    test_db: Database,
    sample_sport: Sport,
    sample_league: League,
    sample_fixture: Fixture,
) -> None:
    """Verify multi-repository atomic transaction commit:

    BEGIN TRANSACTION -> save Sport -> save League -> save Fixture -> COMMIT.
    Confirms all entities are persisted atomically and retrievable across connections.
    """
    with test_db.connection() as conn:
        sport_repo = SportRepository(conn)
        league_repo = LeagueRepository(conn)
        fixture_repo = FixtureRepository(conn)

        with test_db.transaction(conn):
            sport_repo.save(sample_sport)
            league_repo.save(sample_league)
            fixture_repo.save(sample_fixture)

        assert sport_repo.get_by_identity(sample_sport.name) is not None
        assert league_repo.get_by_identity(sample_league.identity) is not None
        assert fixture_repo.get_by_id(sample_fixture.fixture_id) is not None

    # Verify on a fresh connection that all entities were persisted to the database
    with test_db.connection() as fresh_conn:
        assert SportRepository(fresh_conn).get_by_identity(sample_sport.name) == sample_sport
        assert LeagueRepository(fresh_conn).get_by_identity(sample_league.identity) == sample_league
        assert FixtureRepository(fresh_conn).get_by_id(sample_fixture.fixture_id) == sample_fixture
