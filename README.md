# Telegram Bet Bot

A personal Telegram sports betting analysis and deterministic betslip construction bot built in Python.

> **Important:** This is a **private repository for personal use**. It is an analytical decision-support and workflow automation tool, **not** a guaranteed prediction system or automated real-money gambling agent.

---

## Overview

**Telegram Bet Bot** is designed to replace ad-hoc, emotional betting choices with a disciplined, auditable pipeline. It scans upcoming unstarted sports fixtures and monitored Telegram tip channels, extracts candidate betting markets, filters them through a deterministic Risk & Bet Construction Engine, and synthesizes betslips that strictly conform to user-specified constraints (sports, leg counts, target odds ranges, and risk appetite).

For every generated betslip, the bot provides transparent explanations for why each selection was included and logs why other candidates were rejected. Over time, it tracks settled match outcomes to empirically measure tipster channel reliability.

---

## Eventual Capabilities

- **Upcoming Fixture Ingestion:** Scans unstarted fixtures across multiple sports (Football, Basketball, Tennis, etc.) with standardized odds.
- **Tip & Channel Scanning:** Monitors authorized Telegram channels to extract tips, selections, and booking codes.
- **User-Constrained Betslip Generation:** Dynamically constructs betslips based on sport, leg count, target odds range, and risk tier (Conservative, Moderate, Aggressive).
- **Deterministic Risk Engine:** Strictly enforces hard constraints (unstarted games, anti-correlation, risk ceilings) and optimizes soft constraints (odds proximity, league diversification).
- **Auditable Selection Explanations:** Explains why selections were chosen and why alternatives were rejected.
- **Empirical Settlement & Learning:** Automatically settles finished fixtures, tracking source accuracy, hit rate, and historical performance metrics.
- **Genuine Predictive Models (Deferred):** Integrates statistical and machine-learning models only after accumulating sufficient verified historical datasets.

---

## High-Level Architecture

The system follows a clean, decoupled architecture where business logic is strictly separated from the Telegram user interface:

Telegram Interface (Handlers, Interactive Wizards, Formatters)
                ↓
Application / Orchestration Layer (Use Cases & Workflows)
                ↓
Domain Core (Entities: Fixtures, Markets, Odds, Risk Tiers, Betslips)
                ↓
Data & Ingestion Sources (Fixture Providers & Telegram Channel Scrapers)
                ↓
Candidate Generation & Normalization
                ↓
Deterministic Risk & Bet Construction Engine
                ↓
Betslip Artifact & Transparent Audit Logs
                ↓
Telegram Presentation

---

## Development Status & Phasing

The project is being developed in strictly controlled, test-driven phases.

| Phase | Description | Status |
| :--- | :--- | :--- |
| **Phase 0** | **Architecture & Documentation (Development Bible, Blueprint, README)** | **In Progress** |
| **Phase 1** | Project Scaffolding, Typed Configuration & Core Domain Models | Planned |
| **Phase 2** | Persistence Layer (SQLite schema, Repositories, Migrations) | Planned |
| **Phase 3** | Fixture & Market Ingestion Layer (Providers, Normalization) | Planned |
| **Phase 4** | Telegram Tip Ingestion & Parser Subsystem (Channels, Booking Codes) | Planned |
| **Phase 5** | Deterministic Risk & Bet Construction Engine (Constraints, Optimizer, Explanations) | Planned |
| **Phase 6** | Settlement, Historical Outcome Tracking & Source Reliability Engine | Planned |
| **Phase 7** | Telegram Bot Application & Interactive Wizard Layer | Planned |
| **Phase 8** | End-to-End Integration, Resilience & System Hardening | Planned |
| **Phase 9** | Genuine Machine Learning & Predictive Modeling (Deferred) | Deferred |

---

## Core Product Principles

1. **Honest Semantics:** No fabricated probabilities or false AI claims. Heuristic consensus scores are never labeled as machine learning.
2. **Clear Provenance:** Bookmaker implied probabilities, tipster consensus scores, and empirical predictive probabilities are strictly segregated.
3. **Hard Constraints Are Inviolable:** Hard rules (unstarted matches, anti-correlation, risk limits) are never bypassed to force a target odds value.
4. **Decoupled Architecture:** Core domain and risk logic are pure Python with zero dependencies on Telegram or external UI frameworks.
5. **Deterministic Core:** Given identical candidate pools and constraints, the engine produces identical, reproducible betslips and audit logs.

---

## Security Warning & Privacy Notice

- **Never Commit Secrets:** API keys, Telegram Bot tokens (`BOT_TOKEN`), Telegram userbot credentials (`API_ID`, `API_HASH`, session strings), database files, or `.env` files must **never** be committed to version control.
- **Single-User Access Control:** The bot enforces an explicit user ID whitelist (`ALLOWED_TELEGRAM_USER_IDS`). All requests from unlisted users are immediately rejected.
- **Local Storage:** All application data and historical slips are stored locally in a private SQLite database.

---

## Development Bible

For complete technical specifications, architectural diagrams, mathematical formulations, and engineering standards, refer to:

👉 **[`docs/DEVELOPMENT_BIBLE.md`](docs/DEVELOPMENT_BIBLE.md)**
