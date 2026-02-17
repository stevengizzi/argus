# Argus Trading System

Argus is an automated multi-strategy day trading ecosystem with AI co-pilot, desktop/mobile Command Center, and multi-asset support. Built for a single operator and his family.

Full vision: @docs/PROJECT_BIBLE.md
Technical blueprint: @docs/ARCHITECTURE.md
All key decisions: @docs/DECISION_LOG.md
Assumptions and risks: @docs/RISK_REGISTER.md
Phase 1 sprint plan: @docs/07_PHASE1_SPRINT_PLAN.md

## Current State

Phase 2 COMPLETE (February 17, 2026). Phase 3 (Comprehensive Validation) IN PROGRESS. Sprint 11 ✅ COMPLETE. 542 tests, 0 flaky, ruff clean.

**Phase 2 deliverable:** Parameter Validation Report at `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`.
**Recommended ORB parameters (DEC-076):** or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0 (disabled).

**Sprint 11 Results (Extended Walk-Forward):**
- Historical data extended to 35 months (March 2023 – January 2026), 7M bars, 29 symbols
- Walk-forward: 15 windows (optimizer + fixed-params modes)
- Fixed-params (DEC-076): OOS Sharpe +0.34, P&L +$7,741, 378 trades — **positive aggregate returns**
- Optimizer mode: OOS Sharpe -11.46 — **overfits, performs worse than fixed params**
- Traditional WFE threshold (≥0.3) not met, but strategy shows aggregate profitability
- **Decision:** Proceed with paper trading using DEC-076 parameters

**Track B — Paper Trading:** Running Argus on Alpaca paper trading with DEC-076 parameters. Flexible duration. See `docs/08_PAPER_TRADING_GUIDE.md`.

**Phase 3 exit gate:** Sprint 11 ✅ COMPLETE (WFE < 0.3 but positive aggregate OOS returns — proceeding) + user satisfied with paper trading results + CPA consultation → Phase 4 (Live Trading).

Components implemented:
- Event Bus, EventStore, core events
- Clock protocol (SystemClock, FixedClock) — injectable time provider. DEF-001 resolved.
- Broker abstraction (SimulatedBroker, AlpacaBroker)
- Risk Manager with three-tier evaluation (clock-injected), state reconstruction
- BaseStrategy ABC (clock-injected), Scanner ABC, DataService ABC
- ReplayDataService with indicator computation (VWAP, ATR, SMA, RVOL)
- AlpacaDataService — live WebSocket streaming via alpaca-py (bars + trades), indicator warm-up, stale data monitoring (market hours only), reconnection with backoff, fetch_todays_bars for reconstruction
- AlpacaBroker — paper/live trading via alpaca-py REST + WebSocket, bracket orders (single T1 target), order ID mapping (ULID ↔ Alpaca UUID)
- OrbBreakoutStrategy (full implementation)
- Order Manager — position lifecycle management, T1/T2 split, stop-to-breakeven, time stops, EOD flatten, emergency flatten, reconstruct_from_broker
- AlpacaScanner — live pre-market gap scanning via Alpaca snapshots
- HealthMonitor — component status, heartbeat, webhook alerts, daily/weekly integrity checks
- Structured logging — JSON file output, colored console
- System entry point (argus/main.py) — 10-phase startup, graceful shutdown, signal handlers
- DataFetcher — historical 1m bar download from Alpaca, Parquet storage, manifest tracking, data validation
- ReplayHarness — high-fidelity backtesting using production components (EventBus, RiskManager, OrderManager, SimulatedBroker) with FixedClock injection
- BacktestDataService — step-driven DataService for harness control, shares indicator logic with ReplayDataService
- ScannerSimulator — gap-based watchlist computation for backtest mode
- BacktestMetrics — Sharpe ratio, drawdown, profit factor, R-multiples, equity curve analysis
- VectorBT ORB Sweeps — vectorized parameter exploration (pure NumPy/Pandas), 6-parameter grid (18K combos/symbol), heatmap generation (static PNG + interactive HTML)
- Walk-Forward Engine — rolling window IS/OOS optimization with WFE calculation, parameter stability analysis, cross-validation
- Report Generator — HTML reports with equity curves, monthly tables, trade distributions, walk-forward sections (Plotly interactive charts)
- Dependencies: alpaca-py>=0.30, python-dotenv>=1.0, aiohttp>=3.9, plotly>=6.5, matplotlib>=3.8, seaborn>=0.13 (NOT alpaca-trade-api — deprecated)

## Architecture

Three tiers built in sequence:
1. Trading Engine (Python, asyncio) — strategies, orchestrator, risk manager, data service, broker abstraction
2. Command Center (Tauri + React) — dashboards, controls, reports
3. AI Layer (Claude API) — advisory, approval workflow, reports

Currently building: Tier 1, Phase 3 (Comprehensive Validation — Paper Trading track active).

## Tech Stack

- Python 3.11+, asyncio throughout
- FastAPI (REST + WebSocket API server)
- SQLite (WAL mode) for trade logging and state
- alpaca-py>=0.30 (NOT alpaca-trade-api — deprecated)
- python-dotenv>=1.0
- ib_insync (secondary broker, IBKR)
- pandas, numpy, pandas-ta for data/indicators
- VectorBT for parameter exploration (Phase 2)
- plotly for backtest report visualization (Phase 2)
- APScheduler for scheduling
- YAML for all configuration

## Project Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus, Health
├── strategies/     # BaseStrategy + individual strategy modules
├── data/           # Scanner, Data Service, Indicators
├── execution/      # Broker abstraction, Order Manager
├── analytics/      # Trade Logger, Strategy Reports, Portfolio Reports
├── intelligence/   # News & catalyst intelligence (Tier 1: Phase 3, Tiers 2-3: Phase 6) [PLANNED]
├── backtest/       # Data fetcher, Replay Harness, VectorBT sweeps, walk-forward, metrics, reports
├── db/             # DatabaseManager
├── notifications/  # Push, Email, Telegram/Discord handlers
├── accounting/     # Tax tracking, P&L, Wash Sale detection
├── api/            # FastAPI server (REST + WebSocket)
config/             # YAML config files (strategies, risk, brokers, etc.)
data/
├── historical/     # Downloaded Parquet files for backtesting (gitignored)
└── backtest_runs/  # Output databases per backtest run (gitignored)
tests/              # Unit and integration tests
docs/
├── sprints/        # Sprint spec documents
├── backtesting/    # DATA_INVENTORY, BACKTEST_RUN_LOG, PARAMETER_VALIDATION_REPORT
└── *.md            # Bible, Architecture, Decision Log, Risk Register, etc.
```

## Commands

- `python -m pytest tests/` — Run all tests
- `python -m pytest tests/ -x` — Run tests, stop on first failure
- `python -m argus.main` — Start the trading engine (paper trading default)
- `python -m argus.main --dry-run` — Connect and validate without trading
- `python -m argus.backtest.data_fetcher --symbols TSLA,NVDA --start 2025-03-01 --end 2026-02-01` — Download historical data
- `python -m argus.backtest.replay_harness --data-dir data/historical/1m --start 2025-06-01 --end 2025-12-31` — Run replay backtest
- `python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31` — Run VectorBT parameter sweep
- `python -m argus.backtest.report_generator --db data/backtest_runs/run_xxx.db --output reports/orb_validation.html` — Generate backtest report
- `python -m argus.backtest.data_fetcher --start 2025-03-01 --end 2026-02-01` — Download historical data


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
- All market-hours time comparisons MUST convert UTC timestamps to ET first using `timestamp.astimezone(ZoneInfo("America/New_York"))`. NEVER compare `.timestamp.time()` directly against ET constants like `time(9, 30)`. (DEC-061)

## Testing

- pytest with pytest-asyncio for async tests
- Each module has a corresponding test file: `argus/core/risk_manager.py` → `tests/core/test_risk_manager.py`
- Test naming: `test_<what_it_does>_<expected_result>` (e.g., `test_signal_exceeding_daily_loss_is_rejected`)
- Mock external services (broker API, data feeds) in unit tests
- Integration tests use SimulatedBroker and ReplayDataService
- Aim for >90% coverage on core/ and strategies/

## Documentation Update Protocol

IMPORTANT: When making changes during a coding session, evaluate whether any of the following documents need to be updated. If they do, either update them directly or flag them for the user to update.

**Update docs/07_PHASE1_SPRINT_PLAN.md when:**
- Phase 1 is complete. This document is now historical reference. No further updates expected.

**Update docs/09_PHASE2_SPRINT_PLAN.md when:**
- A sprint is confirmed complete (change status from ⬜ PENDING to ✅ COMPLETE)
- A sprint's scope changes (components added, removed, or moved between sprints)
- A sprint's test count target is finalized or actual count is known
- The build order or sprint boundaries change for any reason
- Phase 2 is complete (mark all sprints ✅, add completion date to header)

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
- Whether 07_PHASE1_SPRINT_PLAN.md needs a status update (sprint completion, scope change)

## Deferred Items

Track items that are intentionally postponed. Each item has a trigger condition. When that condition is met during a session, surface the item proactively.

| ID | Item | Trigger | Context |
|----|------|---------|---------|
| ~~DEF-001~~ | ~~Inject clock/date provider into Risk Manager~~ | ~~Sprint 4 starts~~ | **DONE** Clock injection into Risk Manager + BaseStrategy is complete. |
| ~~DEF-002~~ | ~~Cash reserve basis: switch to start-of-day equity~~ | ~~Sprint 3~~ | **DONE** — Implemented in Sprint 3 (DEC-037). |
| ~~DEF-003~~ | ~~Replace datetime.utcnow() with datetime.now(UTC)~~ | ~~Sprint 3~~ | **DONE** — Fixed in events.py, trading.py, and tests. |
| DEF-004 | Discuss cash reserve calc with CPA before live trading | Phase 3 start | Equity vs start-of-day capital vs high water mark has tax and risk implications worth a professional opinion. |
| ~~DEF-005~~ | ~~Move webhook URLs to .env (security)~~ | ~~Post paper trading validation~~ | **DONE** — HealthConfig now reads heartbeat_url_env and alert_webhook_url_env from config, resolves actual URLs from environment variables. |
| DEF-006 | Backtrader integration if Replay Harness too slow | Phase 2 Sprint 7 (if replay takes >1hr for 6mo data) | Backtrader dropped from Phase 2 (DEC-046). Reconsidered only if Replay Harness performance is insufficient for iterative parameter work. |
| DEF-007 | Pre-market data for scanner accuracy | Backtest results promising AND scanner accuracy becomes bottleneck for live-vs-backtest correlation | IEX feed (free tier) only provides regular hours. Scanner simulation computes gap from prev close → day open, which captures overnight moves but misses pre-market volume patterns. Resolution: download 1 month SIP data to validate scanner accuracy, consider SIP for all historical data if significant. |
| ~~DEF-008~~ | ~~Synthetic data e2e trade trigger test~~ | ~~Sprint 8~~ | **RESOLVED** — Root cause: timezone bug in OrbBreakout (DEC-061). After fix, harness produces 59 trades on 7 months of real data with relaxed max_range_atr_ratio. Additional fixes: fill price ($0.01 bug), trade logging (sync fill handling), data integrity (original stop, weighted exit price). 488 tests. |
| ~~DEF-009~~ | ~~VectorBT vs Replay Harness cross-validation~~ | ~~Sprint 9 starts~~ | **DONE** — `cross_validate_single_symbol()` implemented in walk_forward.py. Compares VectorBT trade count vs Replay Harness for matching params; VectorBT >= Replay is PASS (DEC-069). |
| ~~DEF-010~~ | ~~Remove `_simulate_trades_for_day_slow()`~~ | ~~Sprint 9 completes~~ | **DONE** — Legacy function removed from vectorbt_orb.py. Tests updated to use wrapper over vectorized functions (DEC-070). |
```

This keeps it lightweight — no new document, no new sync burden. Items get removed (or moved to "Completed") as they're addressed. Both Claudes see the trigger column and know when to raise the flag.

I'd also add one line to the Project Knowledge doc's "Communication Style Notes" or similar section so this Claude knows the convention exists: