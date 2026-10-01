"""Persistence repositories for core domain entities."""

from telegram_bet_bot.persistence.repositories.fixture_repository import FixtureRepository
from telegram_bet_bot.persistence.repositories.league_repository import LeagueRepository
from telegram_bet_bot.persistence.repositories.market_repository import MarketRepository
from telegram_bet_bot.persistence.repositories.provider_mapping_repository import (
    ProviderMappingRepository,
)
from telegram_bet_bot.persistence.repositories.selection_repository import (
    SelectionRepository,
)
from telegram_bet_bot.persistence.repositories.sport_repository import SportRepository

__all__ = [
    "SportRepository",
    "LeagueRepository",
    "FixtureRepository",
    "MarketRepository",
    "SelectionRepository",
    "ProviderMappingRepository",
]
