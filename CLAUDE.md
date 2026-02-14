# Argus Trading System

Argus is an automated multi-strategy day trading ecosystem with AI co-pilot, desktop/mobile Command Center, and multi-asset support. Built for a single operator and his family.

Full vision: @docs/PROJECT_BIBLE.md
Technical blueprint: @docs/ARCHITECTURE.md
All key decisions: @docs/DECISION_LOG.md
Assumptions and risks: @docs/RISK_REGISTER.md

## Current State

Phase 1 — Sprint 1 complete. Config system, Event Bus, database layer, and Trade Logger are built and tested (52 tests). Currently preparing for Sprint 2 (Broker Abstraction + Risk Manager).

Update this section as development progresses.

## Architecture

Three tiers built in sequence:
1. Trading Engine (Python, asyncio) — strategies, orchestrator, risk manager, data service, broker abstraction
2. Command Center (Tauri + React) — dashboards, controls, reports
3. AI Layer (Claude API) — advisory, approval workflow, reports

Currently building: Tier 1, Phase 1.

## Tech Stack

- Python 3.11+, asyncio throughout
- FastAPI (REST + WebSocket API server)
- SQLite (WAL mode) for trade logging and state
- alpaca-trade-api SDK (primary broker)
- ib_insync (secondary broker, IBKR)
- pandas, numpy, pandas-ta for data/indicators
- VectorBT for parameter exploration
- Backtrader for strategy validation
- APScheduler for scheduling
- YAML for all configuration

## Project Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus
├── strategies/     # BaseStrategy + individual strategy modules
├── data/           # Scanner, Data Service, Indicators
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Strategy Reports, Portfolio Reports
├── backtest/       # VectorBT helpers, Backtrader configs, Replay Harness
├── notifications/  # Push, Email, Telegram/Discord handlers
├── accounting/     # Tax tracking, P&L, Wash Sale detection
├── api/            # FastAPI server (REST + WebSocket)
config/             # YAML config files (strategies, risk, brokers, etc.)
tests/              # Unit and integration tests
docs/               # Project documentation (Bible, Architecture, etc.)
```

## Commands

- `python -m pytest tests/` — Run all tests
- `python -m pytest tests/ -x` — Run tests, stop on first failure
- `python -m argus.main` — Start the trading engine
- `python -m argus.backtest.replay` — Run the replay harness

## Code Style

- Type hints on ALL function signatures (parameters and return types)
- Docstrings on all public methods and classes (Google style)
- Abstract base classes (ABC) for all pluggable interfaces
- snake_case for files, functions, variables
- PascalCase for classes
- UPPER_SNAKE_CASE for constants
- All imports at top of file, grouped: stdlib → third-party → local
- No wildcard imports
- Max line length: 100 characters
- Use pathlib for file paths, not os.path
- Use dataclasses or Pydantic models for structured data, not raw dicts
- Prefer explicit over implicit — no magic

## Architectural Rules (MUST FOLLOW)

- NEVER hardcode configuration values — always read from YAML config files
- NEVER place broker orders without passing through the Risk Manager
- ALL trades MUST be logged to the database with full metadata
- Strategies MUST implement the complete BaseStrategy interface
- Strategies MUST be stateless between trading days (reset_daily_state)
- Strategies NEVER import or reference other strategies
- Strategies NEVER import or reference the Orchestrator or Risk Manager directly
- ALL inter-component communication goes through the Event Bus
- Broker API keys and secrets NEVER in code or committed files — environment variables only
- Every public interface MUST have corresponding tests
- async/await everywhere — no blocking calls in the main event loop

## Testing

- pytest with pytest-asyncio for async tests
- Each module has a corresponding test file: `argus/core/risk_manager.py` → `tests/core/test_risk_manager.py`
- Test naming: `test_<what_it_does>_<expected_result>` (e.g., `test_signal_exceeding_daily_loss_is_rejected`)
- Mock external services (broker API, data feeds) in unit tests
- Integration tests use SimulatedBroker and ReplayDataService
- Aim for >90% coverage on core/ and strategies/

## Documentation Update Protocol

IMPORTANT: When making changes during a coding session, evaluate whether any of the following documents need to be updated. If they do, either update them directly or flag them for the user to update.

**Update docs/DECISION_LOG.md when:**
- A new technical decision is made (library choice, pattern choice, design tradeoff)
- An existing decision is changed or superseded
- Format: follow the existing DEC-XXX template exactly

**Update docs/RISK_REGISTER.md when:**
- A new assumption is discovered during implementation
- An existing assumption is validated or invalidated
- A new risk is identified
- Format: follow the existing A-XXX / R-XXX templates exactly

**Update docs/ARCHITECTURE.md when:**
- A new module or interface is created that differs from the spec
- Database schema changes
- API endpoints change
- New dependencies are added

**Update docs/PROJECT_BIBLE.md when:**
- Strategy rules change
- Risk management parameters change
- System behavior rules change

**Update this file (CLAUDE.md) when:**
- Current State changes (phase completion, new phase started)
- Project Structure changes (new directories, renamed modules)
- Commands change (new scripts, changed invocations)
- New architectural rules are established

At the END of every significant coding session, output a brief "Docs Status" summary:
- Which docs were updated and why
- Which docs SHOULD be updated but weren't (flag for user)
- Any decisions made during the session that should be recorded
