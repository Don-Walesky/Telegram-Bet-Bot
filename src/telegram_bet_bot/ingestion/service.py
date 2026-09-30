"""Ingestion application service orchestrating data flow from provider to persistence."""

from dataclasses import dataclass, field
import logging

from telegram_bet_bot.domain import (
    Fixture,
    League,
    Market,
    Selection,
    Sport,
)
from telegram_bet_bot.ingestion.exceptions import IngestionError
from telegram_bet_bot.ingestion.models import ProviderFixtureBundle
from telegram_bet_bot.ingestion.normalizer import ProviderDataNormalizer
from telegram_bet_bot.ingestion.provider import SportsDataProvider
from telegram_bet_bot.persistence import Database
from telegram_bet_bot.persistence.repositories import (
    FixtureRepository,
    LeagueRepository,
    MarketRepository,
    SelectionRepository,
    SportRepository,
)

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    """Detailed result of a single fixture bundle ingestion operation."""

    fixture_id: str
    sport: Sport
    league: League
    fixture: Fixture
    markets: list[Market] = field(default_factory=list)
    selections: list[Selection] = field(default_factory=list)


@dataclass
class IngestionSummary:
    """Summary metrics of a batch ingestion operation."""

    sports_count: int = 0
    leagues_count: int = 0
    fixtures_count: int = 0
    markets_count: int = 0
    selections_count: int = 0
    results: list[IngestionResult] = field(default_factory=list)


class FixtureIngestionService:
    """Application service coordinating the ingestion of external fixtures and markets.

    Enforces transactional atomicity, idempotent upserts, and clean translation
    from external provider contracts to persistent domain models.
    """

    def __init__(
        self,
        db: Database,
        provider: SportsDataProvider,
        normalizer: ProviderDataNormalizer | None = None,
    ) -> None:
        self._db = db
        self._provider = provider
        self._normalizer = normalizer or ProviderDataNormalizer()

    def ingest_sports(self) -> list[Sport]:
        """Fetch, normalize, and persist all sports available from the provider."""
        provider_sports = self._provider.get_sports()
        domain_sports: list[Sport] = []

        with self._db.transaction() as conn:
            sport_repo = SportRepository(conn)
            for ps in provider_sports:
                sport = self._normalizer.normalize_sport(ps)
                sport_repo.save(sport)
                domain_sports.append(sport)

        logger.info("Successfully ingested %d sports from provider.", len(domain_sports))
        return domain_sports

    def ingest_leagues(self, sport_name: str | None = None) -> list[League]:
        """Fetch, normalize, and persist leagues from the provider."""
        provider_leagues = self._provider.get_leagues(sport_name=sport_name)
        domain_leagues: list[League] = []

        with self._db.transaction() as conn:
            sport_repo = SportRepository(conn)
            league_repo = LeagueRepository(conn)

            for pl in provider_leagues:
                # Ensure parent sport is persisted
                sport = Sport(pl.sport_name)
                sport_repo.save(sport)

                league = self._normalizer.normalize_league(pl, sport)
                league_repo.save(league)
                domain_leagues.append(league)

        logger.info("Successfully ingested %d leagues from provider.", len(domain_leagues))
        return domain_leagues

    def ingest_fixture_bundle(self, bundle: ProviderFixtureBundle) -> IngestionResult:
        """Ingest a complete fixture hierarchy atomically.

        Guarantees that the Sport, League, Fixture, Markets, and Selections
        are validated and persisted inside a single atomic transaction.
        If any element fails, the entire transaction rolls back.
        """
        if not isinstance(bundle, ProviderFixtureBundle):
            raise IngestionError(f"Expected ProviderFixtureBundle, got {type(bundle).__name__}")

        # 1. Normalize entire hierarchy first before writing to database
        sport = self._normalizer.normalize_sport(bundle.sport)
        league = self._normalizer.normalize_league(bundle.league, sport)
        fixture = self._normalizer.normalize_fixture(bundle.fixture, sport, league)

        markets_by_ext_id: dict[str, Market] = {}
        domain_markets: list[Market] = []
        for pm in bundle.markets:
            market = self._normalizer.normalize_market(pm, fixture)
            domain_markets.append(market)
            if pm.external_id:
                markets_by_ext_id[pm.external_id] = market
            # Also index by name as fallback if market external_id is omitted
            markets_by_ext_id[pm.name] = market

        domain_selections: list[Selection] = []
        for ps in bundle.selections:
            parent_market = markets_by_ext_id.get(ps.market_external_id)
            if parent_market is None:
                raise IngestionError(
                    f"Selection '{ps.name}' references market '{ps.market_external_id}' "
                    f"which was not found in fixture bundle '{bundle.fixture.external_id}'."
                )
            selection = self._normalizer.normalize_selection(ps, parent_market)
            domain_selections.append(selection)

        # 2. Persist in strict hierarchical order inside an atomic transaction
        with self._db.transaction() as conn:
            sport_repo = SportRepository(conn)
            league_repo = LeagueRepository(conn)
            fixture_repo = FixtureRepository(conn)
            market_repo = MarketRepository(conn)
            selection_repo = SelectionRepository(conn)

            sport_repo.save(sport)
            league_repo.save(league)
            fixture_repo.save(fixture)

            for m in domain_markets:
                market_repo.save(m)

            for s in domain_selections:
                selection_repo.save(s)

        logger.info(
            "Atomically ingested fixture '%s' with %d markets and %d selections.",
            fixture.fixture_id,
            len(domain_markets),
            len(domain_selections),
        )

        return IngestionResult(
            fixture_id=fixture.fixture_id,
            sport=sport,
            league=league,
            fixture=fixture,
            markets=domain_markets,
            selections=domain_selections,
        )

    def ingest_upcoming_fixtures(
        self,
        sport_name: str | None = None,
    ) -> IngestionSummary:
        """Fetch all upcoming fixture bundles from provider and ingest them atomically.

        Each fixture bundle is processed in its own atomic transaction so that
        one corrupted fixture does not prevent ingestion of other valid fixtures,
        while ensuring each fixture hierarchy is completely atomic.
        """
        bundles = self._provider.get_upcoming_fixture_bundles(sport_name=sport_name)
        summary = IngestionSummary()

        seen_sports: set[str] = set()
        seen_leagues: set[str] = set()

        for bundle in bundles:
            result = self.ingest_fixture_bundle(bundle)
            summary.results.append(result)
            summary.fixtures_count += 1
            summary.markets_count += len(result.markets)
            summary.selections_count += len(result.selections)

            if result.sport.name not in seen_sports:
                seen_sports.add(result.sport.name)
                summary.sports_count += 1

            if result.league.identity not in seen_leagues:
                seen_leagues.add(result.league.identity)
                summary.leagues_count += 1

        logger.info(
            "Completed upcoming fixture ingestion: %d fixtures, %d markets, %d selections.",
            summary.fixtures_count,
            summary.markets_count,
            summary.selections_count,
        )
        return summary
