# Argus Trading System

Argus is an automated multi-strategy day trading ecosystem with AI co-pilot, desktop/mobile Command Center, and multi-asset support. Built for a single operator and his family.

Full vision: @docs/PROJECT_BIBLE.md
Technical blueprint: @docs/ARCHITECTURE.md
All key decisions: @docs/DECISION_LOG.md
Assumptions and risks: @docs/RISK_REGISTER.md
Phase 1 sprint plan: @docs/07_PHASE1_SPRINT_PLAN.md

## Current State

**Structure:** Two parallel tracks (DEC-079, February 19, 2026).
- **Build Track:** System construction at development velocity. Sprints 1–11 complete (542 tests). Next: Sprint 12 (DatabentoDataService adapter).
- **Validation Track:** Paper trading ACTIVE on Alpaca IEX (system stability only — DEC-081). Signal accuracy validation pending DatabentoDataService (Sprint 12). Migrates to IBKR paper after Sprint 13.

Active sprint plan: `docs/10_PHASE3_SPRINT_PLAN.md` (covers both tracks).

**Infrastructure decisions (Feb 20, DEC-081–087):**
- **Market data:** Databento US Equities Standard ($199/mo). Full universe, no symbol limits. Exchange-direct proprietary feeds. `databento` Python client (official, async). DEC-082.
- **Execution broker:** Interactive Brokers (IBKR Pro, tiered). Sole live execution broker. SmartRouting, no PFOF. `ib_async` library (asyncio-native). DEC-083.
- **Alpaca:** Demoted to strategy incubator paper testing only. No real capital through Alpaca. DEC-086.
- **Historical data:** Databento source, Parquet cache. Existing Alpaca Parquet files retained. DEC-085.
- **Cost deferral:** Databento subscription activated when adapter ready for integration testing. DEC-087.

- IBKR account application submitted Feb 21, 2026 (Account ID: U24619949). Individual, Margin, IBKR Pro (tiered), GA address. Permissions: Stocks, Options L3, Futures, Forex, Crypto. Awaiting approval.

**Recommended ORB parameters (DEC-076):** or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0 (disabled).

**Sprint 11 Results (Extended Walk-Forward):**
- Historical data extended to 35 months (March 2023 – January 2026), 7M bars, 29 symbols
- Walk-forward: 15 windows (optimizer + fixed-params modes)
- Fixed-params (DEC-076): OOS Sharpe +0.34, P&L +$7,741, 378 trades — **positive aggregate returns**
- Optimizer mode: OOS Sharpe -11.46 — **overfits, performs worse than fixed params**
- **Decision:** Proceed with paper trading using DEC-076 parameters

**Config fix (DEC-078):** `earliest_entry` changed from 09:45 to 09:35 to match or=5 window.

**Validation Track sequence:** DatabentoDataService (Sprint 12) → IBKRBroker (Sprint 13) → IBKR paper trading (2+ weeks) → CPA consultation → live trading at minimum size on IBKR.

**Build Track queue:** DatabentoDataService (Sprint 12) → IBKRBroker (Sprint 13) → Command Center MVP (Sprints 14–16) → Orchestrator (17) → ORB Scalp (18) → Tier 1 News (19) → AI Layer MVP (20) → Expansion (21+)

**Command Center delivery (DEC-080):** Three surfaces from single React codebase — web app + Tauri desktop + PWA mobile. All operational after Sprint 16.

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
- Research reports completed: Market Data Infrastructure (`argus_market_data_research_report.md`) and Execution Broker (`argus_execution_broker_research_report.md`)
- Decisions DEC-081–087: Databento data backbone, IBKR live execution, Alpaca incubator-only, sprint resequencing, Parquet cache strategy, cost deferral

## Architecture

Three tiers, built in parallel (DEC-079):
1. Trading Engine (Python, asyncio) — strategies, orchestrator, risk manager, data service, broker abstraction ✅ Core complete
2. Command Center (FastAPI + React → web + Tauri desktop + PWA mobile) — dashboards, controls, reports → Build Track Sprint 12+
3. AI Layer (Claude API) — advisory, approval workflow, reports → Build Track Sprint 18+

Currently: Validation Track (paper trading) running in parallel with Build Track (Sprint 12 next).

## Tech Stack

- Python 3.11+, asyncio throughout
- FastAPI (REST + WebSocket API server)
- SQLite (WAL mode) for trade logging and state
- databento (official Python client — primary market data, DEC-082)
- ib_async (asyncio-native IBKR integration — primary execution, DEC-083)
- alpaca-py>=0.30 (strategy incubator paper testing only — DEC-086)
- python-dotenv>=1.0
- pandas, numpy, pandas-ta for data/indicators
- VectorBT for parameter exploration
- plotly for backtest report visualization
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
├── intelligence/   # News & catalyst intelligence (Tier 1: Sprint 17, Tiers 2-3: later) [PLANNED]
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

## Docs Update Procedure

When Steven says **"update all docs"** (or "sync docs", "docs update"), run through this checklist and directly edit every doc that needs changes:

| Doc | Update If... | What to Update |
|-----|-------------|----------------|
| `docs/05_DECISION_LOG.md` | Any design/implementation decision was made | Add new DEC-NNN entry. **Check current highest number first** — never reuse or skip. Use the standard table format. |
| `docs/02_PROJECT_KNOWLEDGE.md` | Decision made, sprint completed, constraint discovered, architecture changed | Add to "Key Decisions Made (Do Not Relitigate)" with DEC reference. Update "Current Project State". Update Build Track queue or Validation Track status. |
| `docs/03_ARCHITECTURE.md` | New component, schema change, API endpoint added/changed, dependency added | Update relevant section. Add new interfaces with implementation status. |
| `docs/01_PROJECT_BIBLE.md` | Strategy rules changed, risk parameters changed, system invariants changed | Rare — only update if a fundamental rule changed. |
| `docs/06_RISK_REGISTER.md` | New risk identified, existing risk resolved, assumption validated/invalidated | Add new RSK-NNN or ASM-NNN, or update existing entry status. Check current highest number first. |
| `docs/10_PHASE3_SPRINT_PLAN.md` | Sprint completed, sprint scope changed, Build Track queue reordered, Validation Track status changed | Move sprint from queue to completed table. Update test counts. Record outcomes. |
| `CLAUDE.md` | Current state changed, new architectural rule, new command, new deferred item, project structure changed | Update "Current State" (Build Track position, Validation Track status). Add rules to "Architectural Rules". Update "Commands" with new scripts. |

### Rules

1. **Check the current highest DEC/RSK/ASM number before adding new entries.** The #1 source of doc bugs is duplicate numbers.
2. **Draft actual content, not just "update X".** Every doc change should be directly written to the file.
3. **Sprint numbers are the canonical identifier.** Use sprint numbers (Sprint 12, Sprint 13) in all docs. Historical phases (Phase 1, Phase 2) are referenced by name only.
4. **Don't update docs that didn't change.** The checklist is a filter, not a mandate. Most sessions touch 2–3 docs at most.
5. **Project Knowledge (02) is also the Claude.ai project instructions.** After updating `02_PROJECT_KNOWLEDGE.md`, remind Steven to sync the Claude.ai project instructions if changes are significant.
6. **Commit doc updates separately:** `docs: update [list of changed docs]`

### Output Format

At the END of every significant coding session, output a brief **"Docs Status"** summary:
- Which docs were updated and why
- Which docs SHOULD be updated but weren't (flag for user)
- Any decisions made during the session that should be recorded
- Whether `10_PHASE3_SPRINT_PLAN.md` needs a sprint status update

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
| DEF-011 | IQFeedDataService adapter | Forex strategy development starts OR Tier 2 news integration starts | IQFeed provides forex, Benzinga news, and breadth indicators that Databento lacks. Build when a specific feature requires it. ~$160–250/month. |
| DEF-012 | Databento L2 depth activation | A strategy requires order book depth data for entry/exit decisions | MBP-10 schema available on Standard plan. DatabentoDataService designed for L2 from Sprint 12, but not activated until a strategy needs it. |

This keeps it lightweight — no new document, no new sync burden. Items get removed (or moved to "Completed") as they're addressed. Both Claudes see the trigger column and know when to raise the flag.

I'd also add one line to the Project Knowledge doc's "Communication Style Notes" or similar section so this Claude knows the convention exists: