"""Deterministic mock sports-data provider for testing and offline development."""

from datetime import datetime, timezone
from decimal import Decimal

from telegram_bet_bot.ingestion.exceptions import (
    MalformedProviderDataError,
    ProviderUnavailableError,
)
from telegram_bet_bot.ingestion.models import (
    ProviderFixture,
    ProviderFixtureBundle,
    ProviderLeague,
    ProviderMarket,
    ProviderSelection,
    ProviderSport,
)
from telegram_bet_bot.ingestion.provider import SportsDataProvider


class MockSportsDataProvider(SportsDataProvider):
    """In-memory deterministic mock sports data provider.

    Supplies synthetic sports, leagues, fixtures, markets, and selections.
    Strictly free from predictive probabilities, tips, EV ranking, or betting logic.
    Supports optional failure injection for testing error boundaries.
    """

    def __init__(
        self,
        simulate_unavailable: bool = False,
        simulate_malformed: bool = False,
        provider_name: str = "mock_provider",
    ) -> None:
        self.provider_name = provider_name
        self.name = provider_name
        self.simulate_unavailable = simulate_unavailable
        self.simulate_malformed = simulate_malformed
        self._bundles: dict[str, ProviderFixtureBundle] = {}
        self._load_synthetic_data()

    def _check_health(self) -> None:
        if self.simulate_unavailable:
            raise ProviderUnavailableError("Simulated provider outage: service unreachable.")
        if self.simulate_malformed:
            raise MalformedProviderDataError("Simulated malformed payload returned by provider.")

    def _load_synthetic_data(self) -> None:
        """Seed deterministic synthetic fixture hierarchies across multiple sports."""
        # 1. Football - Premier League: Arsenal vs Chelsea
        sport_football = ProviderSport(name="football", external_id="sport-fb-01")
        league_epl = ProviderLeague(
            name="Premier League",
            sport_name="football",
            country="England",
            external_id="league-epl-01",
        )
        fixture_epl = ProviderFixture(
            external_id="fix-fb-epl-001",
            sport_name="football",
            league_id="league-epl-01",
            home_team="Arsenal",
            away_team="Chelsea",
            start_time=datetime(2026, 11, 20, 15, 0, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        mkt_1x2 = ProviderMarket(
            name="Match Winner",
            fixture_external_id="fix-fb-epl-001",
            external_id="mkt-fb-epl-001-1x2",
            line=Decimal("0"),
        )
        sel_home = ProviderSelection(
            name="Arsenal",
            market_external_id="mkt-fb-epl-001-1x2",
            external_id="sel-fb-epl-001-1",
            odds=Decimal("1.95"),
        )
        sel_draw = ProviderSelection(
            name="Draw",
            market_external_id="mkt-fb-epl-001-1x2",
            external_id="sel-fb-epl-001-x",
            odds=Decimal("3.50"),
        )
        sel_away = ProviderSelection(
            name="Chelsea",
            market_external_id="mkt-fb-epl-001-1x2",
            external_id="sel-fb-epl-001-2",
            odds=Decimal("3.90"),
        )

        mkt_ou = ProviderMarket(
            name="Total Goals",
            fixture_external_id="fix-fb-epl-001",
            external_id="mkt-fb-epl-001-ou25",
            line=Decimal("2.5"),
        )
        sel_over = ProviderSelection(
            name="Over 2.5",
            market_external_id="mkt-fb-epl-001-ou25",
            external_id="sel-fb-epl-001-o25",
            odds=Decimal("1.80"),
        )
        sel_under = ProviderSelection(
            name="Under 2.5",
            market_external_id="mkt-fb-epl-001-ou25",
            external_id="sel-fb-epl-001-u25",
            odds=Decimal("2.05"),
        )

        bundle_epl = ProviderFixtureBundle(
            fixture=fixture_epl,
            sport=sport_football,
            league=league_epl,
            markets=[mkt_1x2, mkt_ou],
            selections=[sel_home, sel_draw, sel_away, sel_over, sel_under],
        )
        self._bundles[fixture_epl.external_id] = bundle_epl

        # 2. Football - La Liga: Real Madrid vs Barcelona
        league_laliga = ProviderLeague(
            name="La Liga",
            sport_name="football",
            country="Spain",
            external_id="league-laliga-01",
        )
        fixture_laliga = ProviderFixture(
            external_id="fix-fb-ll-002",
            sport_name="football",
            league_id="league-laliga-01",
            home_team="Real Madrid",
            away_team="Barcelona",
            start_time="2026-11-21T20:00:00+00:00",
            status="SCHEDULED",
        )
        mkt_ll_1x2 = ProviderMarket(
            name="Match Winner",
            fixture_external_id="fix-fb-ll-002",
            external_id="mkt-fb-ll-002-1x2",
            line=None,
        )
        sel_rm = ProviderSelection(
            name="Real Madrid",
            market_external_id="mkt-fb-ll-002-1x2",
            external_id="sel-fb-ll-002-rm",
            odds=Decimal("2.20"),
        )
        sel_barca = ProviderSelection(
            name="Barcelona",
            market_external_id="mkt-fb-ll-002-1x2",
            external_id="sel-fb-ll-002-fcb",
            odds=Decimal("3.10"),
        )
        bundle_laliga = ProviderFixtureBundle(
            fixture=fixture_laliga,
            sport=sport_football,
            league=league_laliga,
            markets=[mkt_ll_1x2],
            selections=[sel_rm, sel_barca],
        )
        self._bundles[fixture_laliga.external_id] = bundle_laliga

        # 3. Basketball - NBA: LA Lakers vs Boston Celtics
        sport_basketball = ProviderSport(name="basketball", external_id="sport-bb-01")
        league_nba = ProviderLeague(
            name="NBA",
            sport_name="basketball",
            country="USA",
            external_id="league-nba-01",
        )
        fixture_nba = ProviderFixture(
            external_id="fix-bb-nba-003",
            sport_name="basketball",
            league_id="league-nba-01",
            home_team="Los Angeles Lakers",
            away_team="Boston Celtics",
            start_time=datetime(2026, 11, 22, 2, 30, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        mkt_ml = ProviderMarket(
            name="Moneyline",
            fixture_external_id="fix-bb-nba-003",
            external_id="mkt-bb-nba-003-ml",
            line=None,
        )
        sel_lakers = ProviderSelection(
            name="Los Angeles Lakers",
            market_external_id="mkt-bb-nba-003-ml",
            external_id="sel-bb-nba-003-lal",
            odds=Decimal("2.15"),
        )
        sel_celtics = ProviderSelection(
            name="Boston Celtics",
            market_external_id="mkt-bb-nba-003-ml",
            external_id="sel-bb-nba-003-bos",
            odds=Decimal("1.72"),
        )
        bundle_nba = ProviderFixtureBundle(
            fixture=fixture_nba,
            sport=sport_basketball,
            league=league_nba,
            markets=[mkt_ml],
            selections=[sel_lakers, sel_celtics],
        )
        self._bundles[fixture_nba.external_id] = bundle_nba

        # 4. Tennis - ATP: Alcaraz vs Sinner
        sport_tennis = ProviderSport(name="tennis", external_id="sport-tn-01")
        league_atp = ProviderLeague(
            name="ATP Tour",
            sport_name="tennis",
            country=None,
            external_id="league-atp-01",
        )
        fixture_tennis = ProviderFixture(
            external_id="fix-tn-atp-004",
            sport_name="tennis",
            league_id="league-atp-01",
            home_team="Carlos Alcaraz",
            away_team="Jannik Sinner",
            start_time=datetime(2026, 11, 23, 14, 0, tzinfo=timezone.utc),
            status="SCHEDULED",
        )
        mkt_tn_winner = ProviderMarket(
            name="Match Winner",
            fixture_external_id="fix-tn-atp-004",
            external_id="mkt-tn-atp-004-mw",
            line=None,
        )
        sel_alcaraz = ProviderSelection(
            name="Carlos Alcaraz",
            market_external_id="mkt-tn-atp-004-mw",
            external_id="sel-tn-atp-004-ca",
            odds=Decimal("1.90"),
        )
        sel_sinner = ProviderSelection(
            name="Jannik Sinner",
            market_external_id="mkt-tn-atp-004-mw",
            external_id="sel-tn-atp-004-js",
            odds=Decimal("1.90"),
        )
        bundle_tennis = ProviderFixtureBundle(
            fixture=fixture_tennis,
            sport=sport_tennis,
            league=league_atp,
            markets=[mkt_tn_winner],
            selections=[sel_alcaraz, sel_sinner],
        )
        self._bundles[fixture_tennis.external_id] = bundle_tennis

    def get_sports(self) -> list[ProviderSport]:
        self._check_health()
        seen = set()
        sports = []
        for bundle in self._bundles.values():
            if bundle.sport.name not in seen:
                seen.add(bundle.sport.name)
                sports.append(bundle.sport)
        return sports

    def get_leagues(self, sport_name: str | None = None) -> list[ProviderLeague]:
        self._check_health()
        seen = set()
        leagues = []
        for bundle in self._bundles.values():
            if sport_name is None or bundle.league.sport_name.lower() == sport_name.lower():
                league_key = (bundle.league.name, bundle.league.sport_name)
                if league_key not in seen:
                    seen.add(league_key)
                    leagues.append(bundle.league)
        return leagues

    def get_fixtures(
        self,
        sport_name: str | None = None,
        league_id: str | None = None,
    ) -> list[ProviderFixture]:
        self._check_health()
        fixtures = []
        for bundle in self._bundles.values():
            if sport_name is not None and bundle.fixture.sport_name.lower() != sport_name.lower():
                continue
            if league_id is not None and bundle.fixture.league_id != league_id:
                continue
            fixtures.append(bundle.fixture)
        return fixtures

    def get_markets(self, fixture_external_id: str) -> list[ProviderMarket]:
        self._check_health()
        bundle = self._bundles.get(fixture_external_id)
        if bundle is None:
            return []
        return list(bundle.markets)

    def get_selections(self, market_external_id: str) -> list[ProviderSelection]:
        self._check_health()
        selections = []
        for bundle in self._bundles.values():
            for sel in bundle.selections:
                if sel.market_external_id == market_external_id:
                    selections.append(sel)
        return selections

    def get_fixture_bundle(self, fixture_external_id: str) -> ProviderFixtureBundle | None:
        self._check_health()
        return self._bundles.get(fixture_external_id)

    def get_upcoming_fixture_bundles(
        self,
        sport_name: str | None = None,
    ) -> list[ProviderFixtureBundle]:
        self._check_health()
        bundles = []
        for bundle in self._bundles.values():
            if sport_name is not None and bundle.sport.name.lower() != sport_name.lower():
                continue
            bundles.append(bundle)
        return bundles
