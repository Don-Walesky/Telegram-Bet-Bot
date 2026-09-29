# Development Bible & Technical Blueprint

**Project:** Personal Telegram Sports Betting Analysis & Bet Construction Bot  
**Status: Phase 1 — Python Project Foundation — Completed**  
**Repository Access:** Private / Personal Use  
**Target Runtime:** Python 3.11+  

---

## 1. Project Purpose & Executive Summary

The **Telegram Bet Bot** is a personal sports betting analysis, risk assessment, and betslip construction system operated through a private Telegram interface.

The primary purpose of the system is to replace emotional, ad-hoc betting decisions with a disciplined, deterministic, and auditable pipeline. It scans upcoming fixtures and monitored Telegram tip channels, extracts candidate markets, filters them against rigorous risk and correlation rules, constructs betslips conforming to explicit user constraints (target odds, leg count, risk appetite, sport selection), and explains exactly why every selection was accepted or rejected.

### What the System IS

- A personal decision-support and workflow automation tool.
- A deterministic constraint-satisfaction and risk-filtering engine.
- A multi-source candidate aggregator (fixtures, tipster channels, booking codes).
- An auditable selection system providing transparent rationale for every bet leg.
- An empirical tracking framework that records historical outcomes and measures source reliability over time.

### What the System IS NOT

- **NOT a guaranteed prediction system or "get-rich-quick" scheme.** Sports betting carries inherent financial risk; no system guarantees winning outcomes.
- **NOT an automated bet-placing bot.** It constructs analysis-backed betslips and booking codes for personal evaluation; it does not execute financial transactions on bookmaker accounts.
- **NOT a pseudo-AI black box.** It does not fabricate win probabilities, hallucinate expected values, or disguise basic heuristics as machine learning.
- **NOT a public multi-tenant SaaS.** It is engineered strictly for personal use by authorized users.

---

## 2. Product Vision & Eventual Capabilities

Over its complete lifecycle, the bot will achieve the following integrated capabilities:

+-----------------------------------------------------------------------------------+
|                                 TELEGRAM INTERFACE                                |
|  User commands (/build, /scan, /stats)  |  Interactive wizards  |  Audit reports   |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                            APPLICATION & ORCHESTRATION                            |
|       Betslip Builder Workflow      |    Tip Ingestion & Extraction Workflow      |
+-----------------------------------------------------------------------------------+
                                         |
            +----------------------------+----------------------------+
            v                                                         v
+-----------------------+                                 +-------------------------+
|   FIXTURE PROVIDER    |                                 |  CHANNEL TIP INGESTION  |
| Upcoming matches,     |                                 | Telegram scrapers,      |
| verified odds, markets|                                 | tip parser, codes       |
+-----------------------+                                 +-------------------------+
            \                                                         /
             \                                                       /
              +--------------------------+--------------------------+
                                         v
+-----------------------------------------------------------------------------------+
|                            CANDIDATE GENERATION LAYER                             |
|          Canonical Market Normalization  |  Source Signal Attribution             |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        RISK & BET CONSTRUCTION ENGINE                             |
|  *Hard Constraint Validator (Kickoff time, anti-correlation, risk ceilings)     |
|* Soft Constraint Optimizer (Target odds proximity, league diversity)           |
|  * Transparent Justification & Rejection Log Generator                           |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                       FINAL BETSLIP & AUDIT ARTIFACT                              |
|   Constructed Legs | Combined Odds | Booking Code | Explicit In/Out Justification |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                      SETTLEMENT & SOURCE LEARNING ENGINE                          |
|   Match Outcome Verification | Source Accuracy Scoring | Track Record Database    |
+-----------------------------------------------------------------------------------+

### Core Eventual Capabilities

1. **Upcoming Fixture Ingestion:** Ingests unstarted matches across multiple sports (Football/Soccer, Basketball, Tennis, etc.) with standardized market definitions.
2. **Monitored Channel Tip Scanning:** Ingests raw messages and booking codes from specified Telegram channels, parsing selections and target fixtures.
3. **Multi-Source Candidate Synthesis:** Correlates tipster recommendations against verified upcoming fixtures and market odds.
4. **User-Constrained Betslip Generation:** Dynamically generates slips matching user parameters:
   - Target sports / leagues
   - Desired leg count (e.g., 3-leg treble, 5-leg accumulator)
   - Risk appetite tier (Conservative, Moderate, Aggressive)
   - Target combined odds or odds interval (e.g., $3.00 - 4.50$)
   - Market exclusions or preferences (e.g., Over/Under goals, Match Result, Double Chance, Both Teams to Score)
5. **Deterministic Risk Filtering:** Applies hard rules preventing correlated legs, negative expectations, stale odds, or untrusted source picks.
6. **Transparent Selection Audit:** Provides human-readable justifications for why each leg was chosen and logs of candidate rejections.
7. **Empirical Learning & Source Calibration:** Automatically checks match outcomes, settles historical slips, and calculates source reliability metrics (Brier score, ROI, hit rate).
8. **Genuine Predictive Modeling (Deferred):** Introduces statistical and machine-learning predictive models only when clean, settled historical datasets reach sufficient sample depth.

---

## 3. Core Principles & Analytical Axioms

Every module, function, and feature in this project must adhere to seven non-negotiable architectural axioms:

### Axiom 1: Honest Semantics & Scientific Integrity

- **No Fabricated Probabilities:** Never generate or display arbitrary percentage win probabilities without an empirical or calibrated model.
- **No Pseudo-Confidence Scores:** Avoid arbitrary 1–10 confidence scores unless they represent a mathematically documented heuristic.
- **Clear Labeling:** A heuristic consensus score is labeled as a *Consensus Heuristic*, not an *AI Model Prediction*.

### Axiom 2: Strict Provenance of Probability

The system recognizes three distinct tiers of numerical metrics and must never conflate them:

1. **Bookmaker Implied Probability ($P_{\text{implied}} = \frac{1}{\text{Decimal Odds}}$):** Represents market pricing including bookmaker margin (overround).
2. **Source Consensus Index ($\text{Score} \in [0, 1]$):** Represents normalized heuristic agreement across monitored tipsters and signals.
3. **Empirical Predictive Probability ($P_{\text{model}} \in [0, 1]$):** Represents an out-of-sample calibrated statistical probability derived from settled historical data.

### Axiom 3: Hard Constraints Are Inviolable

- Hard constraints (such as game start status, maximum risk ceiling, maximum leg count, and correlation rules) cannot be relaxed or bypassed merely to satisfy target odds.
- If the candidate pool cannot satisfy all hard constraints while reaching the target odds, the system must fail gracefully with `InsufficientCandidatesError` and explain the exact deficit, rather than assembling a compromised betslip.

### Axiom 4: Strict Decoupling of Domain and Interface

- The core Domain Models, Risk Engine, Betslip Builder, and Settlement Engine are written in pure Python with zero dependencies on Telegram libraries (such as `python-telegram-bot` or `telethon`).
- The Telegram bot layer acts purely as a transport/UI adapter that translates user inputs to application commands and formats domain responses for chat display.

### Axiom 5: Deterministic & Testable Core

- Given the same input fixture pool, candidate tips, and constraint settings, the Risk and Bet Construction Engine must produce the exact same betslip and explanation logs every time.
- All filtering and scoring logic must be covered by comprehensive unit tests with deterministic synthetic datasets.

### Axiom 6: Isolation of External Dependencies

- All external data providers (Odds APIs, Telegram Scrapers, Results Resolvers) must be hidden behind abstract adapter interfaces.
- Testing must never rely on live external network connections; test suites run against deterministic mocks and fixture records.

### Axiom 7: Privacy & Security by Default

- The bot must strictly enforce single-user / authorized-user access control.
- No API keys, Telegram bot tokens, session strings, or personal credentials may ever be committed to source control.

---

## 4. Functional Requirements

### 4.1 Input Specification & User Constraints

The system must allow an authorized user to request a betslip by specifying:

- **Sports:** Single sport (e.g., Football) or multi-sport combination.
- **Leg Count:** Minimum and maximum number of selections (e.g., exact 3 legs, or 3 to 5 legs).
- **Target Odds:** Target decimal odds (e.g., $3.50$) or odds range (e.g., $[3.00, 4.00]$).
- **Risk Tier:**
  - `Conservative`: Low-variance markets, heavy favorites, high historical reliability sources, strict odds bounds ($1.20 - 1.50$ per leg).
  - `Moderate`: Balanced risk/return, standard markets, moderate odds bounds ($1.40 - 1.85$ per leg).
  - `Aggressive`: Higher variance allowed, underdog value, higher per-leg odds ($1.75 - 2.50+$ per leg).
- **Allowed / Disallowed Markets:** Explicit inclusion/exclusion of markets (e.g., allow `1X2`, `Double Chance`, `Over/Under 2.5`; disallow `Exact Score`).
- **Minimum Source Score:** Minimum tipster consensus or historical reliability threshold.

### 4.2 Fixture & Odds Ingestion

- Ingest upcoming fixtures across configured sports.
- Ensure all fixtures are unstarted and kickoff is at least $T_{\text{min}}$ minutes in the future (default: 15 minutes).
- Ingest and normalize decimal odds for standard market types.
- Discard stale odds or fixtures missing verified market lines.

### 4.3 Monitored Channel & Tip Ingestion

- Connect to authorized monitored Telegram channels/chats via userbot/scraper adapter.
- Ingest incoming messages, historical posts, and tipster announcements.
- Parse structured and semi-structured betting tips (extracting fixture, teams, league, date, market type, recommended pick, stated odds, booking codes).
- Attribute tips to specific source identifiers with timestamps.

### 4.4 Candidate Generation & Normalization

- Map extracted tips and raw fixture markets to a canonical domain model.
- Disambiguate team names, competition names, and market codes (e.g., "Over 2.5 Goals" == "O2.5" == "Total Goals Over 2.5").
- Associate live bookmaker odds with parsed tip selections.
- Generate a unified pool of `CandidateBet` objects ready for evaluation.

### 4.5 Risk & Filtering Engine

Apply deterministic filtering pipelines:

- **Unstarted Verification:** Reject in-play or past fixtures.
- **Correlation Filter:** Prevent conflicting or mutually dependent selections (e.g., selecting both "Team A to Win" and "Team B or Draw" in the same game, or multiple correlated legs from the same match unless explicitly building a Same-Game Parlay).
- **Odds Bounds Filter:** Reject legs outside the permissible odds range for the selected risk tier.
- **Source Quality Filter:** Filter out tips from sources with insufficient reliability or low track records when operating under conservative/moderate risk tiers.
- **Liquidity & Market Sanity:** Reject volatile or illiquid exotic markets.

### 4.6 Betslip Construction Engine

- Formulate betslip construction as a constrained optimization problem.
- Search candidate pools to find combinations of $K$ legs that:
  1. Satisfy all hard constraints.
  2. Produce a combined decimal odds $O_{\text{total}} = \prod_{i=1}^{K} o_i$ within the target odds tolerance.
  3. Maximize overall candidate score / source reliability index.
  4. Maximize cross-league/cross-match diversification according to risk tier rules.
- If no combination exists, output a structured diagnostic report explaining what constraints failed (e.g., "Only 2 valid football candidates passed conservative risk filter; 3 requested").

### 4.7 Transparent Selection Explanation

- For every included selection in the generated betslip:
  - Match details, market, selection, decimal odds.
  - Source attribution (e.g., "Recommended by 2 monitored channels [ChannelA, ChannelB]").
  - Risk tier assessment and key statistical justification.
- For rejected candidates in the requested pool:
  - Structured rejection reason code (e.g., `REJECT_CORRELATED_FIXTURE`, `REJECT_ODDS_OUT_OF_BOUNDS`, `REJECT_KICKOFF_TOO_SOON`).

### 4.8 Historical Settlement & Source Learning

- Store all generated betslips, individual selections, and source recommendations in persistent storage.
- Automatically or manually poll fixture results post-kickoff.
- Settle betslip legs (`WON`, `LOST`, `VOID`, `CANCELLED`).
- Compute and update empirical source performance metrics:
  - Total tips tracked
  - Win rate / Hit rate ($\%$)
  - Return on Investment (ROI $\%$) assuming flat stakes
  - Average odds of recommendations
  - Calibration score / Brier score

### 4.9 Telegram Interface & User Experience

- Provide clear slash commands (`/build`, `/quickslip`, `/channels`, `/sources`, `/history`, `/help`).
- Support step-by-step interactive wizards (Inline keyboards for sport selection, risk profile, leg count).
- Render formatted betslips with emoji-enhanced summaries, leg breakdown, combined odds, and copyable booking code blocks.
- Provide detailed drill-down views on demand (`/explain <slip_id>`).

---

## 5. Non-Functional Requirements

### 5.1 Modularity & Architectural Cleanliness

- Enforce strict separation of concerns using Clean Architecture / Hexagonal Architecture principles.
- Core business logic must remain independent of external frameworks, libraries, databases, and network protocols.

### 5.2 Determinism & Auditability

- Core calculation functions must be pure and free of hidden side-effects.
- Randomness (if used in candidate shuffling) must accept a configurable random seed for reproducible unit testing.

### 5.3 Performance & Response Times

- Betslip generation from a pool of up to 500 candidate bets must complete in under 2.0 seconds on standard consumer hardware.
- Telegram bot interactions must provide immediate visual feedback (e.g., "Typing..." or progress indicators) during complex queries.

### 5.4 Robustness & Fault Tolerance

- Ingestion errors (malformed Telegram messages, unexpected API payloads, network timeouts) must be caught, logged, and isolated without crashing the bot daemon.
- Unparseable messages must be quarantined for inspection rather than causing pipeline failure.

### 5.5 Persistence & Data Integrity

- Local relational database (SQLite via structured repository layer) for personal operational simplicity and zero-configuration hosting.
- Relational schema with strict foreign keys, timestamps, unique constraints, and transaction boundaries.

---

## 6. Initial User Journeys

### Journey 1: Quick Betslip Generation via Command

1. User sends Telegram command: `/build sport=football legs=3 odds=3.50 risk=moderate`
2. Bot validates user authorization (whitelist check).
3. Bot checks for active fixture and tip candidate pool.
4. Bot runs the Risk & Bet Construction Engine.
5. Bot responds with:
   - Formatted Betslip Summary (Combined Odds: 3.48, 3 legs)
   - Leg 1: Premier League - Arsenal vs Chelsea -> Arsenal Win (Odds: 1.65) [Source: Channel Alpha]
   - Leg 2: La Liga - Real Madrid vs Sevilla -> Over 2.5 Goals (Odds: 1.45) [Source: Channel Beta]
   - Leg 3: Serie A - Inter vs Milan -> Both Teams to Score (Odds: 1.45) [Consensus: 2 Channels]
   - Booking code (if available) and summary rationale.
   - Inline buttons: `[View Explanations]` `[Save Slip]` `[Regenerate]`

### Journey 2: Guided Interactive Betslip Builder

1. User sends: `/build`
2. Bot prompts: "Select sport(s)" -> User clicks `[Football]` `[Basketball]` -> `[Next]`
3. Bot prompts: "Select risk profile" -> User clicks `[Conservative]`
4. Bot prompts: "Select number of legs" -> User clicks `[3 Legs]`
5. Bot prompts: "Select target odds" -> User clicks `[2.50 - 3.50]`
6. Bot constructs slip and renders final response with detailed breakdown.

### Journey 3: Monitoring & Channel Parsing Verification

1. User sends: `/sources`
2. Bot renders a list of monitored Telegram channels, active tip counts for today's fixtures, and 30-day empirical accuracy ratings.
3. User sends: `/tips channel=Alpha`
4. Bot lists parsed candidate tips currently in the active pool from that channel.

### Journey 4: Audit & Rejection Query

1. User clicks `[View Explanations]` on a generated slip or runs `/explain <slip_id>`.
2. Bot displays:
   - For each included leg: reason for inclusion, source backing, odds sanity check.
   - Summary of rejected candidate bets (e.g., "14 candidates evaluated: 8 rejected due to odds outside tier, 2 rejected due to match already started, 1 rejected due to fixture correlation").

### Journey 5: Outcome Settlement & Track Record Review

1. Background task or manual command `/settle` runs post-match.
2. Bot matches completed match scores to open betslips.
3. Bot notifies user: "Betslip #104 Settled: WON (Combined Odds: 3.48). ROI: +248%."
4. User queries `/history` -> Bot renders monthly ROI, strike rate, and individual channel performance rankings.

---

## 7. Proposed System Architecture

The system follows a strict layered architecture with dependency inversion:

+-------------------------------------------------------------------------------+
|                           1. PRESENTATION LAYER                               |
|   - Telegram Bot Handlers (Commands, CallbackQueries, Message Receivers)      |
|   - View Formatters (Telegram HTML/Markdown message renderers)                |
|   - Interactive Wizard FSM (State machine for guided flows)                   |
+-------------------------------------------------------------------------------+
                                    |
                                    v
+-------------------------------------------------------------------------------+
|                           2. APPLICATION LAYER                                |
|   - Betslip Construction Orchestrator Use Case                                |
|   - Tip Ingestion & Extraction Orchestrator Use Case                          |
|   - Settlement & Result Reconciliation Orchestrator Use Case                  |
|   - Source Performance Evaluation Use Case                                    |
+-------------------------------------------------------------------------------+
                                    |
            +-----------------------+-----------------------+
            v                                               v
+---------------------------------------+   +-----------------------------------+
|       3. DOMAIN CORE (Pure Python)    |   |     4. RISK & BET CONSTRUCTION    |
| - Entities: Fixture, Market, Selection|   | - Hard Constraint Evaluator       |
| - Value Objects: Odds, RiskTier, Score|   | - Soft Constraint Scorer          |
| - Aggregate: Betslip, CandidateBet    |   | - Combinatorial Slip Builder      |
| - Domain Events & Custom Exceptions   |   | - Explanation & Audit Generator   |
+---------------------------------------+   +-----------------------------------+
                                    ^                       ^
                                    |                       |
+-------------------------------------------------------------------------------+
|                         5. INFRASTRUCTURE & ADAPTERS                          |
|   - Database Repositories (SQLite via SQLAlchemy / Core persistence)          |
|   - Telegram Channel Scraper Adapter (Telethon / Client)                      |
|   - External Fixture & Odds API Adapters                                      |
|   - External Results & Settlement Providers                                   |
|   - Configuration & Security Subsystem (Env loader, Whitelist enforcer)        |
+-------------------------------------------------------------------------------+

### Architectural Boundaries & Coupling Rules

1. **Domain Core** has **ZERO** external dependencies. It contains standard Python classes, dataclasses, enums, and domain logic.
2. **Risk & Bet Construction Engine** depends only on Domain Core entities and pure mathematical algorithms.
3. **Application Layer** orchestrates domain models and interfaces. It knows nothing about Telegram presentation or specific database drivers.
4. **Infrastructure Layer** implements interfaces defined by Application/Domain layers (Dependency Inversion Principle).
5. **Presentation Layer (Telegram)** translates Telegram chat messages to Application commands and formats domain responses for the user.

---

## 8. Domain Boundaries & Core Entities

+-------------------------------------------------------------------------+
|                               DOMAINS                                   |
+-------------------------------------------------------------------------+
| [Sports & Fixtures Domain]                                              |
|   Sport (Enum) -> League (Entity) -> Fixture (Entity)                   |
|   KickoffTime (VO), FixtureStatus (Enum)                                |
+-------------------------------------------------------------------------+
| [Markets & Odds Domain]                                                 |
|   MarketType (Enum: 1X2, OVER_UNDER, BTTS, DOUBLE_CHANCE, HANDICAP, etc)|
|   Selection (VO: target, line, outcome)                                 |
|   DecimalOdds (VO: value >= 1.01, implied_probability)                  |
+-------------------------------------------------------------------------+
| [Tips & Ingestion Domain]                                               |
|   TipsterSource (Entity: name, channel_id, trust_tier)                  |
|   RawTipMessage (Entity: raw_text, source_id, timestamp)                |
|   ParsedTip (Entity: fixture_ref, market_ref, stated_odds, code)        |
+-------------------------------------------------------------------------+
| [Candidate & Risk Domain]                                               |
|   CandidateBet (Aggregate: Fixture, Selection, Odds, Signals, RiskTier)|
|   RiskTier (Enum: CONSERVATIVE, MODERATE, AGGRESSIVE)                   |
|   ConstraintSet (VO: min_odds, max_odds, target_odds, leg_count, etc)   |
|   EvaluationResult (VO: is_valid, rejection_reasons, score)             |
+-------------------------------------------------------------------------+
| [Betslip & Settlement Domain]                                           |
|   BetslipLeg (Entity: candidate_ref, odds_at_construction)              |
|   Betslip (Aggregate: legs, total_odds, status, explanation)            |
|   SettlementOutcome (Enum: PENDING, WON, LOST, VOID, CANCELLED)          |
|   SourceMetricRecord (Entity: source_id, sample_size, roi, win_rate)    |
+-------------------------------------------------------------------------+

---

## 9. Data-Flow Principles & Pipelines

### Pipeline A: Tip & Fixture Ingestion Data-Flow

[Telegram Channel Stream] / [Fixture API]
                  │
                  ▼
         [Raw Message / Payload]
                  │
                  ▼
         [Regex / NLP Parser]
                  │
                  ▼
   [Canonical Entity Normalizer] (Disambiguates teams, leagues, markets)
                  │
                  ▼
      [Active Candidate Repository]

### Pipeline B: Betslip Construction Data-Flow

[User Request (/build)]
         │
         ▼
[ConstraintSet Validator]
         │
         ▼
[Fetch Active Candidates] ──► (Filter: Kickoff >= now + 15m)
         │
         ▼
[Risk Engine: Hard Filtering] ──► (Filter: Odds bounds, disallowed markets, invalid lines)
         │
         ▼
[Risk Engine: Anti-Correlation Check] ──► (Prune duplicate/conflicting fixtures)
         │
         ▼
[Combinatorial Optimizer] ──► (Find subset of K legs satisfying target odds & risk tier)
         │
         ├─────────────────────────────────────────┐
         ▼ (Success)                               ▼ (Failure)
[Generate Audit & Justification]          [Generate InsufficientCandidatesReport]
         │                                         │
         ▼                                         ▼
[Construct Betslip Entity & Persist]      [Format Diagnostic Explanation]
         │                                         │
         ▼                                         ▼
[Render Formatted Slip to Telegram]       [Render Actionable Advice to Telegram]

### Pipeline C: Settlement & Calibration Data-Flow

[Fixture Outcome Provider]
         │
         ▼
[Fetch Settled Match Scores]
         │
         ▼
[Evaluate Each Betslip Leg: WON/LOST/VOID]
         │
         ▼
[Update Betslip Overall Status & PnL]
         │
         ▼
[Update Source Track Record & Calibration Metrics]
         │
         ▼
[Emit Telegram Notification to User]

---

## 10. Probability, Provenance & Semantics Framework

To prevent misleading claims, the system enforces unambiguous terminology across code, logs, and UI:

| Concept | Mathematical Definition | Allowed Variable / UI Names | Prohibited Variable / UI Names |
| :--- | :--- | :--- | :--- |
| **Bookmaker Implied Probability** | $P_{\text{imp}} = \frac{1}{\text{Decimal Odds}}$ | `implied_prob`, `bookmaker_implied_probability` | `win_probability`, `ai_confidence`, `true_probability` |
| **Margin-Adjusted Implied Probability** | $P_{\text{fair}} = \frac{P_{\text{imp}}}{\sum P_{\text{imp}}}$ | `fair_implied_prob`, `margin_adjusted_probability` | `model_prediction`, `true_odds` |
| **Source Consensus Index** | $S = \frac{\sum w_i \cdot \mathbb{I}(\text{tip}_i)}{\sum w_i}$ | `consensus_score`, `tipster_agreement_score` | `model_confidence`, `ml_score`, `ai_prediction` |
| **Historical Source Accuracy** | $\text{HitRate} = \frac{N_{\text{won}}}{N_{\text{total}}}$ | `historical_win_rate`, `empirical_accuracy` | `predictive_power`, `guarantee_score` |
| **True Model Predictive Probability** | $P_{\text{model}} = f(\mathbf{x}; \theta)$ calibrated on settled out-of-sample data | `model_probability`, `calibrated_predictive_probability` | *Must only be used when a validated ML/statistical model is running* |

---

## 11. Risk-Engine & Bet Construction Principles

### 11.1 Hard Constraints (Non-Negotiable)

1. **Temporal Sanctity:** No fixture whose official kickoff is in the past or less than $T_{\text{buffer}}$ (default: 15 minutes) from generation time can be included.
2. **Correlation Guard:** No two selections from the same fixture may be included in the same betslip unless explicitly designated as an authorized Same-Game Parlay (SGP) with adjusted joint pricing.
3. **Odds Envelope:** Every individual leg must strictly satisfy $\text{min\_odds} \le o_i \le \text{max\_odds}$ for the requested risk tier.
4. **Market Integrity:** The selected market line must be currently active and verified against bookmaker reference data.
5. **No Blind Forcing:** Under no circumstance may the engine pick an invalid or high-risk candidate simply to push combined odds into the target range.

### 11.2 Soft Constraints & Optimization Objectives

When multiple valid sets of $K$ legs satisfy all hard constraints, the builder ranks candidate combinations by an objective function:

$$\text{Score}(\text{Slip}) = w_1 \cdot \text{Proximity}(\text{Odds}_{\text{total}}, \text{Odds}_{\text{target}}) + w_2 \cdot \overline{\text{SourceConsensus}} + w_3 \cdot \text{DiversityScore}$$

Where:

- $\text{Proximity}(O, T) = 1.0 - \frac{|O - T|}{T}$
- $\text{DiversityScore}$ rewards slips spanning distinct leagues and tournaments to minimize systemic weather/schedule shocks.

---

## 12. Learning-Engine Principles & Data Lifecycle

### Phase Evolution of Learning

- **Phase 1 to Phase 7 (Deterministic / Empirical):**
  - Track empirical hit rate, ROI, average odds, and profit/loss per tipster channel and market type.
  - Weight tipster consensus scores by historical reliability ($w_i = \text{ROI}_{\text{historical}} \times \text{VolumeDiscount}$).
  - No speculative ML algorithms.
- **Phase 10+ (Future Genuine Predictive Modeling):**
  - Initiated only after accumulating $\ge 1,000$ settled standardized fixture records.
  - Feature engineering on historical performance, expected goals (xG), home/away splits, rest days.
  - Strict out-of-time walk-forward validation and Brier score calibration before model inference goes live.

---

## 13. Security & Access Control Requirements

1. **Telegram Single-User Whitelist:**
   - The bot checks incoming `message.from_user.id` against a configured `ALLOWED_TELEGRAM_USER_IDS` set.
   - Any message from an unlisted user ID is silently dropped or rejected with a generic unauthorized notice and security log entry.
2. **Credential Management:**
   - Zero credentials in code. All configuration loaded via environment variables (`.env`) validated by strict configuration models.
   - Separate tokens for Telegram Bot API (`BOT_TOKEN`) and Telegram Scraper API (`API_ID`, `API_HASH`, `SESSION_STRING`).
3. **Sanitization & Input Validation:**
   - All text inputs from Telegram and parsed channels are sanitized before database storage or command evaluation to prevent injection or formatting exploits.
4. **Local Data Isolation:**
   - SQLite database stored locally in private application directory with strict file-system permissions.

---

## 14. Testing Strategy & Verification Standards

A test-driven and quality-enforced regime is mandatory across all phases:

### Testing Pyramid

1. **Unit Tests (`tests/unit/`):**
   - Pure domain models, entities, value objects, and invariant enforcement.
   - Risk engine constraint evaluation with synthetic candidate pools.
   - Combinatorial betslip builder algorithms (edge cases: empty pool, exact match, impossible odds targets).
   - Regex/text parsing utilities for tip ingestion.
2. **Integration Tests (`tests/integration/`):**
   - SQLite database repositories, migrations, and transactional integrity.
   - Fixture and tip ingestion persistence pipelines with mock payloads.
   - Settlement reconciliation against historical score fixtures.
3. **Contract / Mock Tests (`tests/mocks/`):**
   - Mock Telegram Scraper and Mock Fixture API responses verifying parser resilience against schema changes.
4. **End-to-End Tests (`tests/e2e/`):**
   - Complete workflow: Synthetic raw tip ingestion -> Candidate creation -> Betslip construction -> Settlement -> Track record update.

### Quality & Static Analysis Gates

- Static Type Checking: `mypy` or `pyright` in strict mode.
- Code Formatting & Linting: `ruff` or `flake8` + `black`.
- Coverage Target: $\ge 90\%$ test coverage on Domain Core and Risk Engine.

---

## 15. Development Methodology & Phased Roadmap

Development strictly proceeds one phase at a time. Each phase requires:

1. Inspection of existing codebase.
2. Explanation of proposed changes.
3. Implementation restricted strictly to the designated phase scope.
4. Writing comprehensive tests.
5. Executing test suite and static checks.
6. Reporting exact results and stopping for user review before the next phase.

### Implementation Phases

[Phase 0: Architecture & Documentation]  <-- CURRENT PHASE
   ├── docs/DEVELOPMENT_BIBLE.md
   └── README.md
        │
        ▼
[Phase 1: Python Project Foundation]
   ├── Clean package structure (src/ layout)
   ├── Modern pyproject.toml packaging & dependency specifications
   ├── Basic environment configuration subsystem (typed settings & validation)
   ├── .env.example configuration template
   ├── .gitignore & security hygiene
   ├── Minimal application entry point (main.py)
   ├── Minimal smoke & configuration test suite (tests/test_smoke.py)
   └── Basic README setup and operational documentation
        │
        ▼
[Phase 2: Core Domain Entities & Invariants]
   ├── Pure Domain Entities & Value Objects (Sport, League, Fixture, Market, Selection, Odds, RiskTier)
   ├── Strict validation rules & domain invariant enforcement
   └── Comprehensive unit tests for domain models & invariants
        │
        ▼
[Phase 3: Persistence Layer & Storage Models]
   ├── SQLite database schema, connection manager, migrations
   ├── Repositories (FixtureRepo, TipRepo, BetslipRepo, SourceMetricRepo)
   └── Integration tests for database operations
        │
        ▼
[Phase 4: Fixture & Market Ingestion Layer]
   ├── Abstract Fixture Provider Interface
   ├── Mock Fixture Provider & Real Provider Adapter (API-Football / Odds API)
   ├── Canonical entity normalizer & disambiguation dictionary
   └── Ingestion pipeline tests
        │
        ▼
[Phase 5: Telegram Tip Ingestion & Parser Subsystem]
   ├── Monitored channel listener adapter (Telethon / MTProto client interface)
   ├── Tip text & booking code parser (Regex & structured pattern matchers)
   ├── Candidate bet aggregator & signal binder
   └── Parser unit tests with real-world sample corpus
        │
        ▼
[Phase 6: Deterministic Risk & Bet Construction Engine]
   ├── Hard constraint validator (kickoff time, anti-correlation, risk ceilings)
   ├── Soft constraint scorer (target odds proximity, league diversity)
   ├── Combinatorial / Knapsack betslip builder
   ├── Audit trail & explanation generator (in/out justification logs)
   └── Comprehensive test suite for all builder permutations
        │
        ▼
[Phase 7: Settlement, Outcome Tracking & Source Learning Engine]
   ├── Result reconciliation service (checking match scores)
   ├── Betslip and leg settlement state machine
   ├── Source reliability & empirical accuracy tracker (hit rate, ROI, Brier score)
   └── Settlement workflow tests
        │
        ▼
[Phase 8: Telegram Bot Application & Interaction Layer]
   ├── Telegram Bot application wrapper (python-telegram-bot / aiogram)
   ├── Security middleware (whitelist authorization)
   ├── Command handlers (/build, /quickslip, /sources, /history, /explain)
   ├── Interactive guided builder wizard (inline keyboards & state machine)
   └── Presentation formatters (HTML/Markdown betslips, booking codes)
        │
        ▼
[Phase 9: End-to-End Integration, Resilience & System Hardening]
   ├── End-to-end workflow verification across all modules
   ├── Graceful error handling, quarantine logging for unparseable tips
   ├── Operational runbooks and monitoring diagnostics
   └── Full test suite verification
        │
        ▼
[Phase 10: Genuine Machine Learning & Predictive Modeling (Deferred)]
   ├── Historical dataset compilation & feature engineering
   ├── Statistical modeling & out-of-time walk-forward validation
   └── Predictive model integration

---

## 16. Explicitly Deferred Features

The following features are **explicitly out of scope** during early phases and must not be speculatively built:

1. **Machine Learning / Deep Learning Models:** Deferred until Phase 10 when sufficient historical settled data exists.
2. **Automated Real-Money Bet Placement:** Out of scope. System is strictly for decision analysis and betslip generation.
3. **In-Play / Live Betting Construction:** Out of scope. System strictly handles pre-match, unstarted fixtures.
4. **Public Multi-User / Web Dashboard:** Out of scope. The interface is exclusively a single-user private Telegram bot.
5. **Complex Microservices Infrastructure:** Out of scope. A clean, modular monolith with SQLite is optimal for personal use.

---

*This document serves as the single source of truth for the architecture, principles, and implementation discipline of Telegram-Bet-Bot.*
