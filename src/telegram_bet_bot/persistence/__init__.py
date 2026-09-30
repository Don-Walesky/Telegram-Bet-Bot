"""Persistence layer package for Telegram Bet Bot."""

from telegram_bet_bot.persistence.database import Database
from telegram_bet_bot.persistence.exceptions import (
    DatabaseInitializationError,
    DuplicateEntityError,
    EntityNotFoundError,
    PersistenceError,
    ReferentialIntegrityError,
)
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SelectionRepository,
    SportRepository,
)
from telegram_bet_bot.persistence.schema import SCHEMA_DDL, initialize_database

__all__ = [
    "Database",
    "initialize_database",
    "SCHEMA_DDL",
    "PersistenceError",
    "DatabaseInitializationError",
    "EntityNotFoundError",
    "DuplicateEntityError",
    "ReferentialIntegrityError",
    "SportRepository",
    "LeagueRepository",
    "FixtureRepository",
    "MarketRepository",
    "SelectionRepository",
]
