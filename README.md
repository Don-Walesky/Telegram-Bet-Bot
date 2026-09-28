# Telegram Bet Bot

A personal Telegram sports betting analysis and betslip construction bot built in Python.

> **Important:** This is a **private repository for personal use**. It is an analytical decision-support and workflow automation tool, **not** an automated real-money gambling agent or guaranteed prediction system.

---

## Project Purpose

The primary purpose of **Telegram Bet Bot** is to provide a disciplined, deterministic, and auditable pipeline for sports betting analysis and betslip construction. The bot assists authorized users by standardizing constraints (target odds ranges, leg counts, risk tiers) and providing transparent rationale for bet selections.

---

## Current Development Status

- **Phase 1: Python Project Foundation (Completed)**
  - Clean `src/` layout (`telegram_bet_bot`)
  - Modern project packaging (`pyproject.toml`)
  - Typed environment configuration loader and validation (`config.py`)
  - Executable application entry point (`main.py`)
  - Minimal smoke test suite (`tests/test_smoke.py`)
  - Strict Git hygiene (protecting secrets and local artifacts)

Subsequent phases (domain modeling, persistence, fixture ingestion, risk engine, and Telegram integration) are planned and documented in [`docs/DEVELOPMENT_BIBLE.md`](docs/DEVELOPMENT_BIBLE.md).

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
