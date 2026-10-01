"""SQLite database schema definitions and deterministic initialization."""

import sqlite3
from telegram_bet_bot.persistence.exceptions import DatabaseInitializationError

SCHEMA_DDL = """
PRAGMA foreign_keys = ON;

-- 1. Sports Table
CREATE TABLE IF NOT EXISTS sports (
    identity TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    CHECK (length(trim(identity)) > 0),
    CHECK (length(trim(name)) > 0)
);

-- 2. Leagues Table
CREATE TABLE IF NOT EXISTS leagues (
    identity TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    sport_name TEXT NOT NULL,
    country TEXT,
    league_id TEXT,
    FOREIGN KEY (sport_name) REFERENCES sports (name) ON UPDATE CASCADE ON DELETE RESTRICT,
    UNIQUE (identity, sport_name),
    CHECK (length(trim(identity)) > 0),
    CHECK (length(trim(name)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_leagues_sport ON leagues (sport_name);

-- 3. Fixtures Table
CREATE TABLE IF NOT EXISTS fixtures (
    fixture_id TEXT PRIMARY KEY,
    sport_name TEXT NOT NULL,
    league_identity TEXT NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    scheduled_start_time TEXT NOT NULL,
    status TEXT NOT NULL,
    FOREIGN KEY (sport_name) REFERENCES sports (name) ON UPDATE CASCADE ON DELETE RESTRICT,
    FOREIGN KEY (league_identity, sport_name) REFERENCES leagues (identity, sport_name) ON UPDATE CASCADE ON DELETE RESTRICT,
    CHECK (length(trim(fixture_id)) > 0),
    CHECK (length(trim(home_team)) > 0),
    CHECK (length(trim(away_team)) > 0),
    CHECK (lower(trim(home_team)) != lower(trim(away_team))),
    CHECK (status IN ('SCHEDULED', 'IN_PLAY', 'FINISHED', 'POSTPONED', 'CANCELLED'))
);

CREATE INDEX IF NOT EXISTS idx_fixtures_sport ON fixtures (sport_name);
CREATE INDEX IF NOT EXISTS idx_fixtures_league ON fixtures (league_identity);
CREATE INDEX IF NOT EXISTS idx_fixtures_scheduled ON fixtures (scheduled_start_time);
CREATE INDEX IF NOT EXISTS idx_fixtures_status ON fixtures (status);

-- 4. Markets Table
CREATE TABLE IF NOT EXISTS markets (
    identity TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    fixture_id TEXT NOT NULL,
    market_id TEXT,
    line TEXT,
    FOREIGN KEY (fixture_id) REFERENCES fixtures (fixture_id) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (length(trim(identity)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(fixture_id)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_markets_fixture ON markets (fixture_id);

-- 5. Selections Table
CREATE TABLE IF NOT EXISTS selections (
    identity TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    market_identity TEXT NOT NULL,
    selection_id TEXT,
    odds TEXT,
    FOREIGN KEY (market_identity) REFERENCES markets (identity) ON UPDATE CASCADE ON DELETE CASCADE,
    CHECK (length(trim(identity)) > 0),
    CHECK (length(trim(name)) > 0),
    CHECK (length(trim(market_identity)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_selections_market ON selections (market_identity);

-- 6. Provider Identity Mappings Table
CREATE TABLE IF NOT EXISTS provider_identity_mappings (
    provider_name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    external_id TEXT NOT NULL,
    internal_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (provider_name, entity_type, external_id),
    CHECK (length(trim(provider_name)) > 0),
    CHECK (entity_type IN ('SPORT', 'LEAGUE', 'FIXTURE', 'MARKET', 'SELECTION')),
    CHECK (length(trim(external_id)) > 0),
    CHECK (length(trim(internal_id)) > 0)
);

CREATE INDEX IF NOT EXISTS idx_mappings_internal ON provider_identity_mappings (entity_type, internal_id);
"""


def initialize_database(connection: sqlite3.Connection) -> None:
    """Initialize the SQLite database schema in an idempotent and deterministic manner.

    Executes schema DDL to create all necessary tables and indexes if they do not exist.
    Guarantees foreign-key enforcement is enabled on the connection.

    Raises:
        DatabaseInitializationError: If executing the schema DDL fails.
    """
    try:
        connection.execute("PRAGMA foreign_keys = ON;")
        connection.executescript(SCHEMA_DDL)
    except sqlite3.Error as err:
        raise DatabaseInitializationError(
            f"Failed to initialize database schema: {err}"
        ) from err
