# Argus Trading System

Argus is an automated multi-strategy day trading ecosystem with AI co-pilot, desktop/mobile Command Center, and multi-asset support. Built for a single operator and his family.

Full vision: @docs/PROJECT_BIBLE.md
Technical blueprint: @docs/ARCHITECTURE.md
All key decisions: @docs/DECISION_LOG.md
Assumptions and risks: @docs/RISK_REGISTER.md
Phase 1 sprint plan: @docs/07_PHASE1_SPRINT_PLAN.md

## Current State

**Structure:** Two parallel tracks (DEC-079, February 19, 2026). Expanded to AI-enhanced platform (DEC-163, February 26, 2026).
- **Build Track:** System construction at development velocity. Sprints 1–21b complete (1,597 pytest tests + 100 Vitest). Sprint 21c (The Debrief page) is NEXT.
- **Validation Track:** Paper trading ACTIVE on Alpaca IEX (system stability only — DEC-081). Signal accuracy validation pending Databento activation. All pre-Databento backtests require re-validation (DEC-132). Migrates to IBKR paper after IBKR account approved (U24619949, submitted Feb 21).

Active sprint plan: `docs/10_PHASE3_SPRINT_PLAN.md` (covers both tracks).

**Infrastructure decisions (Feb 20, DEC-081–087):**
- **Market data:** Databento US Equities Standard ($199/mo). Full universe, no symbol limits. Exchange-direct proprietary feeds. `databento` Python client (official, async). DEC-082.
- **Execution broker:** Interactive Brokers (IBKR Pro, tiered). Sole live execution broker. SmartRouting, no PFOF. `ib_async` library (asyncio-native). DEC-083.
- **Alpaca:** Demoted to strategy incubator paper testing only. No real capital through Alpaca. DEC-086.
- **Historical data:** Databento source, Parquet cache. Existing Alpaca Parquet files retained. DEC-085.
- **Cost deferral:** Databento subscription activated when adapter ready for integration testing. DEC-087.

- IBKR account application submitted Feb 21, 2026 (Account ID: U24619949). Individual, Margin, IBKR Pro (tiered), GA address. Permissions: Stocks, Options L3, Futures, Forex, Crypto. Awaiting approval.

**Expanded Vision (DEC-163, February 26, 2026):**
- ARGUS expanded to AI-enhanced trading intelligence platform (15+ patterns, Setup Quality Engine, Order Flow Model, NLP Catalyst Pipeline, Dynamic Position Sizer, Learning Loop, Pre-Market Engine).
- Seven-page Command Center (DEC-169): Dashboard, Trade Log, Performance, Orchestrator (NEW), Pattern Library (NEW), The Debrief (NEW), System.
- Contextual AI Copilot (DEC-170): Claude accessible from every page via slide-out chat panel. Context-aware. Actions through approval workflow.
- Sprint 21 split into 21a–21d (DEC-171): 21a Pattern Library page ✅, 21b Orchestrator page ✅, 21c The Debrief page (NEXT), 21d Dashboard+Performance+System+nav+Copilot shell.
- Free catalyst sources first (DEC-164): SEC EDGAR + Finnhub + FMP. Benzinga deferred.
- Full roadmap: `docs/research/ARGUS_Expanded_Roadmap.md`.

**Sprint 21b Results (Orchestrator Page — Feb 27):**
- Orchestrator page: 6th Command Center page. Hero row layout (DEC-192): SessionOverview + RegimePanel stacked left, CapitalAllocation donut right.
- RegimePanel gauge redesign (DEC-195): Visual gauge bars for Trend/Vol/Momentum with marker dots. Regime badge hero. Session phase badge in page header.
- StrategyCoverageTimeline (custom SVG, DEC-188). StrategyOperationsGrid (2-col cards, allocation bars, throttle status, pause/resume).
- DecisionTimeline (newest-first, DEC-194). GlobalControls (rebalance, flatten, pause with ConfirmModal).
- Throttle override (DEC-187): duration + mandatory reason, in-memory expiry, logged to decisions.
- Strategy config consolidation (DEC-193): shared strategyConfig.ts replaces 3 duplicated maps.
- API: session_phase, pre_market_complete, per-strategy throttle metrics, override endpoint. Client-side regime scoring (DEC-191).
- Nav updated to 6 pages (DEC-189). Keyboard shortcuts 1–6.
- 1597 tests (pytest, 39 new) + 100 (Vitest, 30 new). 13 sessions. Code review passed (DEC-192–195).

**Sprint 20 Results (Afternoon Momentum — Feb 26):**
- AfternoonMomentumStrategy: standalone from BaseStrategy (DEC-152), 5-state machine (DEC-155), consolidation high/low channel + ATR filter (DEC-153). T1=1.0R/T2=2.0R, dynamic time stop compressed to force_close (DEC-157).
- Gap watchlist reuse from ORB family (DEC-154). 8 simultaneous entry conditions (DEC-156). Minimum risk floor. ALLOW_ALL cross-strategy (DEC-160).
- VectorBT sweep: 1,152 combos, precompute+vectorize architecture (DEC-162). Walk-forward pipeline dispatch. Provisional per DEC-132.
- System integration: main.py wiring, Orchestrator registration, per-strategy health components for all 4 strategies. CandleEvent routing via existing Orchestrator registry.
- Dev mode four-strategy mock data (positions, trades, allocations, orchestrator decisions, watchlist, strategy cards, session summary).
- 16 four-strategy integration tests (registration, sequential flows, cross-strategy risk, state machine, throttling, daily reset, allocation caps).
- Strategy spec: `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`. Databento activation deferred to Sprint 21 (DEC-161).
- 1522 tests (pytest, 112 new) + 48 (Vitest, 8 new). 10 implementation sessions + 2 code review checkpoints. Code review passed (DEC-152–162).

**Sprint 19 Results (VWAP Reclaim — Feb 25–26):**
- VwapReclaimStrategy: standalone from BaseStrategy (DEC-136), 5-state machine (DEC-138), pullback swing-low stop (DEC-139). T1=1.0R/T2=2.0R, 30-min time stop.
- Scanner reuse (DEC-137), position sizing with risk floor (DEC-140), ALLOW_ALL cross-strategy (DEC-141).
- VectorBT sweep: 59,556 trades, 768 combos, avg Sharpe 3.89, WF OOS Sharpe 1.49, P&L $15,820 (DEC-146). Provisional per DEC-132. Precompute+vectorize architecture mandated (DEC-149).
- Watchlist Sidebar: responsive layout (desktop inline/tablet slide-out/mobile overlay), compact badges, VWAP distance, sort, edge-mounted collapse pill (DEC-142, DEC-147, DEC-150).
- Keyboard shortcuts: 1–4 navigation, w watchlist toggle (DEC-151).
- Dev mode three-strategy mock data. Databento activation deferred to Sprint 20 (DEC-143).
- 1410 tests (pytest) + 40 (Vitest). 14 sessions + 2 code reviews. Code review passed.

**Sprint 18 + 18.5 Results (ORB Scalp — Feb 25):**
- OrbBaseStrategy ABC (DEC-120) — shared base for ORB family strategies. OrbScalpStrategy (DEC-123): 0.3R single target, 120s hold.
- Cross-strategy risk: ALLOW_ALL same-symbol policy (DEC-121), per-signal time stops (DEC-122), CandleEvent routing via EventBus (DEC-125).
- VectorBT Scalp sweep: directional guidance only at 1-min resolution (DEC-127). Params thesis-driven.
- UX: SessionSummaryCard, PositionTimeline (Gantt), three-way position filter (DEC-128), Zustand UI persistence (DEC-129).
- Vitest frontend testing (DEC-130). 14+3 multi-strategy integration tests.
- 1313 tests (pytest) + 7 (Vitest). Sprint 18: 12 sessions. Sprint 18.5: 7 sessions. Code review passed.

**Sprint 18.75 Results (CapitalAllocation + Dashboard Polish — Feb 25):**
- CapitalAllocation component (DEC-133): track-and-fill donut (custom SVG, color-tinted track arcs, clockwise fill arcs, sweep animation) + horizontal stacked bars with toggle. Zustand persistence.
- MarketRegimeCard (DEC-134): dashboard card showing current regime with color-coded badge. Dashboard grid restructured to 3-card equal row. Market + Market Regime paired at tablet/phone.
- Orchestrator status API enriched with deployment state (DEC-135): deployed_capital, deployed_pct, is_throttled per strategy.
- 4 new pytest + 7 new Vitest tests. 8 fix sessions.

**Sprint 17 Results (Orchestrator V1 — Feb 24–25):**
- Orchestrator: pre-market routine, 30-min regime monitoring (DEC-115), intraday throttle, EOD review, decision logging.
- RegimeClassifier (SPY realized vol as VIX proxy, DEC-113). PerformanceThrottler (consecutive losses/Sharpe/drawdown). CorrelationTracker (infrastructure for V2 allocation).
- Equal-weight allocation V1 (DEC-114). Single-strategy 40% cap accepted (DEC-119).
- DEF-016 resolved: Order Manager atomic bracket orders via `place_bracket_order()` (DEC-117).
- API: 3 orchestrator endpoints (status, decisions, rebalance) + 4 WebSocket event types.
- UI: SegmentedTab, extended Badge system, AllocationDonut, RiskGauge. 12-phase main.py startup.
- Sprint 17.5 polish: Orchestrator encapsulation properties, safe-area padding fix, donut/gauge animation-once pattern, RiskAllocationPanel stable render (no conditional skeleton swap). 1146 tests (204 new). 13+4 sessions. Code review passed.

**Sprint 16 Results (Desktop/PWA + UX Polish — Feb 24):**
- Framer Motion page transitions + stagger animations (all pages). Skeleton loading (all pages).
- AnimatedNumber (rAF interpolation), SVG Sparklines, chart draw-in animations, P&L flash enhancements.
- Trade detail slide-in panel (desktop: right 40%, mobile: bottom full-screen).
- Emergency controls: flatten all, pause all (with confirmation modals). Strategy pause/resume. Position close.
- CSV trade export with filters. PWA (manifest, SW, icons, iOS meta). Tauri v2 desktop shell.
- Platform detection utility (Tauri/PWA/Web). 942 tests (16 new), 10 sessions completed.

**Recommended ORB parameters (DEC-076):** or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0 (disabled).

**Validation Track sequence:** Build through Sprint 21d (7-page architecture) → activate Databento → IBKR paper (Gate 2, 20+ days) → Build through Sprint 26 → AI-enhanced paper with quality scoring (Gate 3, 30+ days) → Build through Sprint 32 → Full system paper (Gate 4, 50+ cumulative, Sharpe > 2.0) → CPA → live at minimum size on IBKR (Gate 5).

**Build Track queue:** Orchestrator page (21b) → The Debrief (21c) → Dashboard+Performance+System+Nav+Copilot shell (21d) → AI Layer MVP + Copilot activation (22) → NLP Catalyst + Pre-Market (23) → Order Flow V1 (24) → Quality Engine + Dynamic Sizer (25) → Red-to-Green + Patterns (26) → Pattern Expansion I (27) → Order Flow V2 + Short Selling (28) → Pattern Expansion II (29) → Learning Loop V1 (30) → Orchestrator V2 (31) → Pattern Expansion III (32) → ML/Advanced (33+).

**Command Center delivery (DEC-080):** Three surfaces from single React codebase — web app + Tauri desktop + PWA mobile. All operational after Sprint 16.

Components implemented:
- Event Bus, EventStore, core events
- Clock protocol (SystemClock, FixedClock) — injectable time provider. DEF-001 resolved.
- Broker abstraction (SimulatedBroker, AlpacaBroker, IBKRBroker)
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
- System entry point (argus/main.py) — 12-phase startup (Orchestrator as Phase 9, API as Phase 12), graceful shutdown, signal handlers
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
- DatabentoConfig, DatabentoSymbolMap, DatabentoDataService (Sprint 12, partial — core streaming, indicators, stale monitor, historical cache)
- DataStaleEvent, DataResumedEvent events
- DatabentoDataService reconnection with exponential backoff, DataFetcher Databento backend (historical + manifest), DatabentoScanner (V1 watchlist), DataSource enum + system integration, shared databento_utils.py (DEC-090, DEC-091)
- IndicatorEngine (Sprint 12.5, DEC-092) — shared indicator computation (VWAP, ATR-14, SMA-9/20/50, RVOL) used by all four DataService implementations. DEF-013 resolved.
- IBKRBroker (Sprint 13, DEC-083/093/094) — full Broker abstraction via `ib_async`. Native bracket orders (parent + stop + T1 + T2 via `parentId`). Fill streaming via async event bridge. Reconnection with exponential backoff + position verification. State reconstruction from `orderRef` ULID recovery. Config-driven broker selection (`BrokerSource` enum).
- IBKRContractResolver — stock contract creation with caching. IBKRErrorSeverity — error code classification and severity routing.
- Order Manager T2 support (DEC-093) — `t2_order_id` on ManagedPosition, broker-side T2 limit orders, `_handle_t2_fill()`, tick-skip logic for IBKR path, T2 cancellation in all exit paths. Backward compatible with Alpaca tick-monitored T2.
- Dependencies added: ib_async>=1.0.0
- FastAPI REST API (Sprint 14) — JWT auth, health/account/positions/trades/strategies/performance endpoints
- WebSocket bridge — real-time Event Bus streaming to clients, tick throttling, position filtering, heartbeat
- PerformanceCalculator — 17-metric analytics (win rate, profit factor, Sharpe, drawdown, R-multiples)
- TradeLogger query methods — `query_trades()`, `count_trades()`, `get_daily_pnl()`, `get_todays_pnl()`
- Dev mode factory — `create_dev_state()` with mock data for frontend development
- React frontend scaffold (argus/ui/) — Vite, TypeScript, Tailwind CSS v4, Zustand, React Router
- Dependencies added: fastapi>=0.115, uvicorn>=0.34, python-jose[cryptography]>=3.3, passlib[bcrypt]>=1.7
- Orchestrator (Sprint 17) — pre-market routine, 30-min regime polling, intraday throttle checks, EOD review, decision logging. Equal-weight allocation V1 (DEC-114).
- RegimeClassifier — SPY realized vol as VIX proxy (DEC-113), trend scoring (SMA-20/50), momentum (5d ROC). 5 regime types. Crisis override.
- PerformanceThrottler — consecutive losses, rolling Sharpe, drawdown rules. Returns NONE/REDUCE/SUSPEND.
- CorrelationTracker — daily P&L recording, correlation matrix computation. Infrastructure for V2 allocation (DEC-116).
- Order Manager DEF-016 resolved — atomic bracket submission via `place_bracket_order()`. ManagedPosition tracks bracket component IDs (DEC-117).
- API: /orchestrator/status, /orchestrator/decisions, /orchestrator/rebalance endpoints. 4 WebSocket event types (RegimeChange, AllocationUpdate, StrategyActivated, StrategySuspended).
- UI: SegmentedTab (reusable pill tabs), Badge system (StrategyBadge, RegimeBadge, RiskBadge, ThrottleBadge), AllocationDonut (Recharts), RiskGauge (SVG radial arc).
- OrbBaseStrategy ABC — shared base for ORB-family strategies (DEC-120)
- OrbScalpStrategy — fast ORB variant, 0.3R single target, 120s hold (DEC-123)
- Per-signal time stops on SignalEvent → ManagedPosition (DEC-122)
- CandleEvent multi-strategy routing via Orchestrator registry (DEC-125)
- SessionSummaryCard — after-hours session recap (API + React component)
- PositionTimeline — horizontal Gantt chart of positions (React + Vitest tests)
- Zustand positionsUI store — view mode + filter persistence across re-mounts (DEC-129)
- VwapReclaimStrategy (Sprint 19, DEC-136) — 5-state machine (WATCHING → ABOVE_VWAP → BELOW_VWAP → ENTERED/REJECTED), pullback swing-low stop, VWAP distance metric
- AfternoonMomentumStrategy (Sprint 20, DEC-152) — 5-state machine (WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED/REJECTED), consolidation channel, dynamic time stop
- VectorBT VWAP Reclaim sweeps (`backtest/vectorbt_vwap_reclaim.py`) — precompute+vectorize architecture (DEC-144)
- VectorBT Afternoon Momentum sweeps (`backtest/vectorbt_afternoon_momentum.py`) — consolidation detection + breakout simulation (DEC-162)
- Watchlist Sidebar (DEC-142) — responsive layout (desktop inline/tablet slide-out/mobile overlay), VWAP distance, compact badges, sort controls
- Keyboard shortcuts (DEC-151, DEC-180) — 1–5 navigation, w watchlist toggle
- Pattern Library page (Sprint 21a, DEC-172–179) — IncubatorPipeline, PatternCardGrid, PatternCard, PatternFilters, PatternDetail with 5 tabs (Overview, Backtest, Performance, Trades, Intelligence), MarkdownRenderer
- SlideInPanel (shared) — extracted from TradeDetailPanel (DEC-177), used by SymbolDetailPanel
- SymbolDetailPanel (global, DEC-177) — SymbolChart (candlestick), SymbolTradingHistory, SymbolPositionDetail. Triggered from any symbol click via symbolDetailUI Zustand store.
- Strategy spec auto-discovery (DEC-181) — convention-based (`strat_X` → `STRATEGY_X.md`)
- Dependencies added: react-markdown, remark-gfm

## Architecture

Three tiers, built in parallel (DEC-079):
1. Trading Engine (Python, asyncio) — strategies, orchestrator, risk manager, data service, broker abstraction ✅ Core complete
2. Command Center (FastAPI + React → web + Tauri desktop + PWA mobile) — dashboards, controls, reports → Build Track Sprint 14+
3. AI Layer (Claude API) — advisory, approval workflow, reports → Build Track Sprint 22+

Currently: Validation Track (paper trading on Alpaca) running in parallel with Build Track (Sprint 21b next).

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
├── intelligence/   # News & catalyst intelligence (Tier 1: Sprint 23+, Tiers 2-3: later) [PLANNED]
├── backtest/       # Data fetcher, Replay Harness, VectorBT sweeps, walk-forward, metrics, reports
├── db/             # DatabaseManager
├── notifications/  # Push, Email, Telegram/Discord handlers
├── accounting/     # Tax tracking, P&L, Wash Sale detection
├── api/            # FastAPI server (REST + WebSocket)
├── ui/             # React frontend (Vite + TypeScript + Tailwind CSS v4)
├── models/         # Data models (Trade, Strategy, etc.)
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
- `python -m argus.api --dev` — Start API server in dev mode with mock data (password: "argus")
- `python -m argus.api.setup_password` — Generate password hash for production config
- `cd argus/ui && npm install` — Install frontend dependencies
- `cd argus/ui && npm run dev` — Start frontend dev server (Vite)
- `cd argus/ui && npm run build` — Build frontend for production


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

## UI/UX Rules

- **Design principles (DEC-109):** Information over decoration. Ambient awareness. Progressive disclosure. Motion with purpose. Mobile as primary trading surface. Research lab aesthetics.
- **Animation library (DEC-110):** Framer Motion for page transitions + stagger. CSS transitions for hover/micro-interactions. Lightweight Charts native for chart animations. Budget: <500ms, 60fps, never blocks interaction.
- **Chart library stack (DEC-104, DEC-108):** Lightweight Charts (time-series) + Recharts (standard charts) + D3 (custom viz, sparingly) + Three.js/Plotly 3D (Sprint 22 optimization landscape).
- **UX Feature Backlog:** `docs/ui/UX_FEATURE_BACKLOG.md` — canonical inventory of all planned UI/UX enhancements. Reference when planning sprint UX scope. (DEC-106)
- **Responsive breakpoints:** 393px (iPhone SE/mini), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook Pro).
- **Mobile nav:** Bottom tab bar. Desktop/tablet: icon sidebar.
- **Frontend testing (DEC-130):** Vitest for React component tests. Config: `vitest.config.ts`. Pattern: `ComponentName.test.tsx` alongside component. Setup: `src/test/setup.ts`.
- **Positions UI state (DEC-129):** Display mode (table/timeline) and filter (all/open/closed) managed in Zustand store (`stores/positionsUI.ts`). Session-level — no localStorage.

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
| ~~DEF-013~~ | ~~Extract shared IndicatorEngine from DataService implementations~~ | ~~Sprint 12.5~~ | **DONE** — `IndicatorEngine` class created in `argus/data/indicator_engine.py`. All four DataService implementations (AlpacaDataService, DatabentoDataService, ReplayDataService, BacktestDataService) now delegate to IndicatorEngine. 27 new tests, 685 total tests passing. DEC-092. |
| DEF-014 | SystemAlertEvent for dead data feed | Command Center MVP (Sprint 14–16) OR Health Monitor alerting built | `DatabentoDataService._run_with_reconnection()` logs `critical` when max retries exceeded but emits no Event Bus event. Add `SystemAlertEvent` (or similar) so Health Monitor and Command Center can react (red banner, push notification). Location: `argus/data/databento_data_service.py`. |
| DEF-015 | DatabentoScanner full-universe scanning | Databento subscription active (DEC-087) AND paper trading validates need for broader symbol coverage | V1 DatabentoScanner uses configured watchlist. Full-universe scanning (~8K US equities) requires cost/latency analysis with live Databento subscription. Location: `argus/data/databento_scanner.py`, `scan()` and `scan_with_gap_data()`. |
| ~~DEF-016~~ | ~~Order Manager `place_bracket_order()` integration~~ | ~~Sprint 17~~ | **DONE** (Sprint 17, DEC-117). Order Manager uses `place_bracket_order()` for atomic entry+stop+T1+T2. ManagedPosition tracks bracket component IDs. SimulatedBroker + IBKRBroker validated. Known limitation: AlpacaBroker bracket child order fills don't route correctly — acceptable, Alpaca is incubator-only (DEC-086). |
| DEF-017 | Performance-weighted + correlation-adjusted allocation | 20+ days of multi-strategy live data available | V1 uses equal-weight. V2 shifts ±10% based on trailing Sharpe/drawdown. V3 adds CorrelationTracker cross-correlation penalty. CorrelationTracker infrastructure built in Sprint 17 (DEC-116). |
| DEF-018 | Real VIX data integration | IQFeed subscription activated OR CBOE Databento dataset added | RegimeClassifier V1 uses SPY 20-day realized vol as VIX proxy (DEC-113). Replace with real-time VIX index when data source available. |
| DEF-019 | Breadth indicator integration (advance/decline, TICK, TRIN) | IQFeed subscription activated | RegimeClassifier designed for breadth inputs but V1 uses SPY-only signals. IQFeed provides NYSE breadth data. ~$160–250/month. |
| DEF-020 | Cross-strategy sector exposure check (max_single_sector_pct) | IQFeed subscription activated OR fundamentals data source integrated | Risk Manager cross-strategy checks skip sector exposure in V1 — no sector classification data available (DEC-126). Requires SIC/GICS mapping per symbol. Single-stock cap (5%) provides concentration protection meanwhile. |
| DEF-021 | Sub-bar backtesting precision for ORB Scalp | Databento tick-level data available for backtesting OR Scalp paper trading results diverge significantly from backtests | Synthetic ticks give ~15s granularity per 1m bar (DEC-053). Scalp targets 30–120s holds — time stops shorter than 60s resolve at nearest bar boundary. Backtesting results are directional guidance, not exact P&L. |
| DEF-022 | VwapBaseStrategy ABC extraction | Second VWAP-based strategy designed (e.g., VWAP Fade) | No shared logic exists yet — VwapReclaimStrategy inherits directly from BaseStrategy (DEC-136). If a second VWAP variant is built, extract shared VWAP crossover tracking into a VwapBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |
| DEF-023 | Watchlist Endpoint Production Implementation | Sprint 20+ when live scanner generates watchlist candidates | GET /api/v1/watchlist returns mock data only via `_mock_watchlist` attribute injection. Production implementation needs to aggregate from: Scanner watchlist, Strategy state (which symbols each strategy tracks), DataService (prices, sparkline), and VWAP Reclaim strategy state. Location: `argus/api/routes/watchlist.py`. |
| DEF-024 | Trailing Stop Mechanism | Walk-forward shows afternoon moves routinely exceed T2 targets | Order Manager trailing stop logic, Risk Manager awareness, VectorBT sweep support, backtesting infrastructure. Touches cross-cutting concerns across execution, risk, and backtesting layers. T1/T2 fixed targets proven across four strategies — trailing stop adds complexity only if data shows clear benefit. DEC-158. |
| DEF-025 | Shared Consolidation Base Class | Second consolidation-based strategy designed (e.g., Midday Range Breakout) | AfternoonMomentumStrategy inherits directly from BaseStrategy (DEC-152). If a second consolidation variant is built, extract shared midday range tracking into a ConsolidationBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |

This keeps it lightweight — no new document, no new sync burden. Items get removed (or moved to "Completed") as they're addressed. Both Claudes see the trigger column and know when to raise the flag.

I'd also add one line to the Project Knowledge doc's "Communication Style Notes" or similar section so this Claude knows the convention exists: