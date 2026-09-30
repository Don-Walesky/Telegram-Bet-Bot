# Telegram Bet Bot

A personal Telegram sports betting analysis and betslip construction bot built in Python.

> **Important:** This is a **public repository intended for personal and authorized use** (not a public multi-tenant SaaS). It is an analytical decision-support and workflow automation tool, **not** an automated real-money gambling agent or guaranteed prediction system.

---

## Project Purpose

The primary purpose of **Telegram Bet Bot** is to provide a disciplined, deterministic, and auditable pipeline for sports betting analysis and betslip construction. The bot assists authorized users by standardizing constraints (target odds ranges, leg counts, risk tiers) and providing transparent rationale for bet selections.

---

## Current Development Status

- **Phase 4: Fixture & Market Ingestion Layer (Completed)**
  - Abstract `SportsDataProvider` protocol defining standard data ingestion contracts
  - Provider DTO boundary (`ProviderSport`, `ProviderLeague`, `ProviderFixture`, `ProviderMarket`, `ProviderSelection`, `ProviderFixtureBundle`)
  - Deterministic `MockSportsDataProvider` supplying multi-sport synthetic fixture and market data without predictive bias
  - Strict `ProviderDataNormalizer` adapting external provider DTOs into pure Phase 2 domain entities
  - `FixtureIngestionService` coordinating transactional batch and single-bundle ingestion
  - Idempotent upsert persistence preventing duplicate records across ingestion runs
  - Atomic transaction rollback preventing partial writes upon normalization or provider failure
  - Comprehensive unit and integration test suite with temporary SQLite database isolation

- **Phase 3: Persistence Layer & Storage Models (Completed)**
  - Clean, SQLite-backed persistence foundation using Python standard library `sqlite3` (no ORM or external database dependencies)
  - Explicit database schema with primary keys, composite foreign keys, unique constraints, and check constraints
  - Enforced referential integrity via runtime `PRAGMA foreign_keys = ON;`
  - Lossless Decimal storage using canonical string representations (`Market.line`, `Odds.decimal_value`)
  - Strict timezone-aware UTC ISO-8601 datetime storage and reconstruction rejecting naive datetimes
  - Clean repository abstractions (`SportRepository`, `LeagueRepository`, `FixtureRepository`, `MarketRepository`, `SelectionRepository`)
  - Explicit Domain ↕ Persistence translation preventing database implementation details from leaking into domain entities
  - Transaction safety using context-managed connection boundaries
  - Isolated test fixtures utilizing temporary SQLite databases with zero persistent artifacts

- **Phase 2: Core Domain Entities & Invariants (Completed)**
  - Pure domain entities and value objects (`Sport`, `League`, `Fixture`, `Market`, `Selection`, `Odds`, `RiskTier`)
  - Strict domain invariant validation and immutability enforcement
  - Value semantics, explicit equality, and consistent hashing for domain models
  - Standardized decimal odds with mathematical bookmaker implied probability calculation ($P_{\text{implied}} = \frac{1}{\text{Decimal Odds}}$)
  - Hardened market line validation rejecting non-finite values (NaN, positive/negative infinity)
  - Domain isolation with zero external library or database dependencies
  - Comprehensive unit test suite covering validation, boundaries, and value semantics

- **Phase 1: Python Project Foundation (Completed)**
  - Clean `src/` layout (`telegram_bet_bot`)
  - Modern project packaging (`pyproject.toml`)
  - Typed environment configuration loader and validation (`config.py`)
  - Executable application entry point (`main.py`)
  - Minimal smoke test suite (`tests/test_smoke.py`)
  - Strict Git hygiene (protecting secrets and local artifacts)

Subsequent phases (telegram tip ingestion, risk engine, settlement, and Telegram bot application) are planned and documented in [`docs/DEVELOPMENT_BIBLE.md`](docs/DEVELOPMENT_BIBLE.md).

---

## Environment Setup

### 1. Prerequisites
- Python 3.11 or higher (Python 3.14 supported)
- Git

### 2. Create Virtual Environment

```bash
# Create the virtual environment
python -m venv .venv

# Activate the virtual environment
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Linux / macOS:
source .venv/bin/activate
```

---

## Installing Dependencies

Install the package in editable mode along with testing tools:

```bash
pip install -e .
pip install pytest
```

---

## Running the Application

### 1. Configuration (Optional)
Copy the example environment template to create a local `.env` file:

```bash
cp .env.example .env
```

Default settings:
- `APP_ENV=development`
- `LOG_LEVEL=INFO`

### 2. Run Entry Point

Run using the Python module:
```bash
python -m telegram_bet_bot.main
```

Or via the installed console script:
```bash
telegram-bet-bot
```

---

## Running Tests

Execute the test suite with `pytest`:

```bash
pytest
```

---

## Security Warning & Secret Management

- **Never Commit Secrets:** Real Telegram Bot tokens (`BOT_TOKEN`), API keys, session strings, or `.env` files must **never** be committed to Git.
- **Git Protection:** The `.gitignore` file is configured to exclude `.env`, `.envrc`, virtual environments (`.venv/`), cache directories, and local SQLite databases.
- **Access Control:** When the Telegram interface is introduced in later phases, access will be restricted strictly to authorized user IDs via an explicit whitelist.

---

## Technical Specifications & Roadmap

For full architectural blueprints, engineering principles, mathematical definitions, and the complete phased roadmap, refer to:

👉 [`docs/DEVELOPMENT_BIBLE.md`](docs/DEVELOPMENT_BIBLE.md)
