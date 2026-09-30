"""Abstract sports data provider interface and protocol."""

from typing import Protocol, runtime_checkable

from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderFixtureBundle,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)


@runtime_checkable
class SportsDataProvider(Protocol):
    """Protocol defining the contract for an external sports-data provider client."""

    def get_sports(self) -> list[ProviderSport]:
        """Fetch all sports supported by the provider."""
        ...

    def get_leagues(self, sport_name: str | None = None) -> list[ProviderLeague]:
        """Fetch leagues, optionally filtered by sport name."""
        ...

    def get_fixtures(
        self,
        sport_name: str | None = None,
        league_id: str | None = None,
    ) -> list[ProviderFixture]:
        """Fetch fixtures, optionally filtered by sport or league."""
        ...

    def get_markets(self, fixture_external_id: str) -> list[ProviderMarket]:
        """Fetch all markets available for a given fixture."""
        ...

    def get_selections(self, market_external_id: str) -> list[ProviderSelection]:
        """Fetch all outcome selections available for a given market."""
        ...

    def get_fixture_bundle(self, fixture_external_id: str) -> ProviderFixtureBundle | None:
        """Fetch a complete hierarchy bundle for a single fixture."""
        ...

    def get_upcoming_fixture_bundles(
        self,
        sport_name: str | None = None,
    ) -> list[ProviderFixtureBundle]:
        """Fetch all upcoming fixture hierarchy bundles ready for ingestion."""
        ...
