"""Fixture and market ingestion layer."""

from telegram_bet_bot.ingestion.exceptions import (
    IngestionError,
    MalformedProviderDataError,
    NormalizationError,
    ProviderError,
    ProviderUnavailableError,
)
from telegram_bet_bot.ingestion.mock_provider import MockSportsDataProvider
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderFixtureBundle,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.normalizer import ProviderDataNormalizer
from telegram_bet_bot.ingestion.provider import SportsDataProvider
from telegram_bet_bot.ingestion.service import (
    FixtureIngestionService,
    IngestionResult,
    IngestionSummary,
)

__all__ = [
    "FixtureIngestionService",
    "IngestionError",
    "IngestionResult",
    "IngestionSummary",
    "MalformedProviderDataError",
    "MockSportsDataProvider",
    "NormalizationError",
    "ProviderDataNormalizer",
    "ProviderError",
    "ProviderFixture",
    "ProviderFixtureBundle",
    "ProviderLeague",
    "ProviderMarket",
    "ProviderSelection",
    "ProviderSport",
    "ProviderUnavailableError",
    "SportsDataProvider",
]
