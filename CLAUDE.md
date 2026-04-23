# ARGUS — Claude Code Context

> Dense, actionable context for Claude Code sessions. No history — see `docs/` for that.
> Last updated: April 23, 2026 (IMPROMPTU-04 — DEF-199 EOD short-flip closed, startup invariant added, pattern_strategy warm-up log downgraded to DEBUG)

## Active Sprint

**Audit Phase 3 remediation (`audit-2026-04-21`).** FIX-00/15/17/20/01/11/02/12/03/21/14/16/19/04 landed; remaining FIX-NN sessions queued. Post-31.9 component-ownership refactor scheduled (DEF-175). 22 shadow variants still collecting CounterfactualTracker data. Next production sprint: **31B (Research Console / Variant Factory)**.

Per-sprint follow-on detail (Sprint 31.5 / 31.75 / 31.8 / 31.85 / 31A / 31A.5 / 31A.75 + Apr 3–5 impromptu) has been relocated to `docs/sprint-history.md`. Build track + DEC reservations + 33.5 amendment detail: `docs/roadmap.md`.

### Known Issues (operational)
- **FMP Starter plan restriction:** FMP news endpoints return 403 on Starter plan. `fmp_news.enabled: false` in `system_live.yaml`. FMP circuit breaker (DEC-323) prevents spam if accidentally enabled.
- **Pre-existing xdist failures (DEF-048):** 4 test_main.py tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race). Pre-existing on clean HEAD. Priority: LOW.
- **Test isolation (DEF-049):** `test_orchestrator_uses_strategies_from_registry` fails when run in isolation but passes in full suite. Pre-existing.
- **Date-decay test failures (DEF-167):** Vitest hardcoded-date assertions in several files. Batched into FIX-13. Priority: LOW.
- **Flaky sprint_runner test (DEF-150):** Time-of-day arithmetic bug in `test_check_reminder_sends_after_interval`. Batched into FIX-13. Priority: LOW.
- **ibkr_broker xdist flake (DEF-171):** `test_all_ulids_mapped_bidirectionally` flakes under `-n auto`, passes in isolation. Batched into FIX-13. Priority: LOW.

## Current State

- **Active sprint:** Between sprints. 22 shadow variants deployed via `config/experiments.yaml`. Parquet consolidation script delivered (Sprint 31.85); operator activation of consolidated cache pending. Next: Sprint 31B. DEF-175 (component ownership consolidation) queued for a dedicated post-31.9 sprint.
- **Tests:** 4,980 pytest + 859 Vitest (4,967 pytest on CI non-integration). Known flakes: DEF-150 (time-of-day arithmetic, first 2 min of every hour) + DEF-167 (Vitest hardcoded-date scan) + DEF-171 (ibkr_broker xdist) + DEF-190 (pyarrow/xdist register_extension_type race) + DEF-192 (runtime warning cleanup debt, non-blocking). All batched into FIX-13. Treat as pre-existing.
- **Strategies:** 13 live + 2 shadow (15 total). Live: ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, Red-to-Green, Bull Flag, Dip-and-Rip, HOD Break, Gap-and-Go, Pre-Market High Break, Micro Pullback, VWAP Bounce, Narrow Range Breakout. Shadow: Flat-Top Breakout, ABCD.
- **Experiment Variants:** 22 shadow variants across 10 patterns in `config/experiments.yaml` (collecting CounterfactualTracker data). 2 Dip-and-Rip variants historically qualifying from the 24-symbol momentum sweep. `run_experiment.py` supports `--symbols` / `--universe-filter` / `--workers`; parallel execution via `ProcessPoolExecutor`; all 10 PatternModule patterns have `config/universe_filters/*.yaml` configs.
- **Infrastructure (by layer):**
  - *Data:* Databento EQUS.MINI (live) + FMP Starter (scanning + reference data + daily bars) + Finnhub (news + analyst recs) + yfinance VIX/SPX (daily). Universe Manager, Reference Data Cache, IntradayCandleStore, VIXDataService — all config-gated.
  - *Execution:* IBKR paper trading (Account U24619949) + SimulatedBroker for backtests. Order Manager with broker-confirmed reconciliation, overflow routing, margin circuit breaker (IBKR 201), EOD flatten synchronous verification, pre-EOD signal cutoff 3:30 PM ET, ThrottledLogger for repricing storm suppression.
  - *Intelligence:* Catalyst Pipeline (SEC EDGAR + FMP + Finnhub + Claude classifier) + Setup Quality Engine (5-dimension scoring, DEC-384 standalone overlay) + Dynamic Position Sizer + Counterfactual Engine (shadow tracking, filter accuracy) + Learning Loop V1 (advisory, config-gated).
  - *Regime:* RegimeClassifierV2 (11-field RegimeVector, 8 calculators — breadth/correlation/sector/intraday/VIX phase/momentum/term-structure/VRP).
  - *Backtest/Evaluation:* BacktestEngine (SynchronousEventBus, Parquet cache, TheoreticalFillModel) + MultiObjectiveResult + Evaluation Framework + Pareto comparison + slippage model + VectorBT (legacy grid sweeps).
  - *Experiments:* Pattern factory + parameter fingerprint + VariantSpawner + ExperimentRunner (parallel, DuckDB pre-filter) + PromotionEvaluator (Pareto + hysteresis). `experiments.enabled: true`.
  - *Historical analytics:* HistoricalQueryService (DuckDB over Parquet, 6 query methods, 4 REST endpoints, CLI). Parquet Cache Consolidation script (non-bypassable row-count validation, `--verify` DuckDB benchmark).
  - *Operations:* NYSE Holiday Calendar (`core/market_calendar.py`), OHLCV-1m observability (per-gate drop counters + first-event sentinels), Strategy Evaluation Telemetry (ring buffer + `data/evaluation.db`), Debrief Export (shutdown automation), AI Copilot (Claude API).
- **Frontend:** 10-page Command Center (Dashboard, Trade Log with Shadow Trades tab, Performance, The Arena, Orchestrator, Pattern Library, The Debrief, System, Observatory, Experiments) + AI Copilot + Universe Status Card + Intelligence Brief View. PWA mobile (Tauri desktop deferred — see DEF-174). Keyboard shortcuts 1–9 + 0 (0 = Experiments). All 15 strategies have unique colors, badges, single-letter identifiers.

## Project Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus, Regime Intelligence (breadth.py, market_correlation.py, sector_rotation.py, intraday_character.py, regime_history.py), TheoreticalFillModel (fill_model.py), Exit Math (exit_math.py), NYSE Holiday Calendar (market_calendar.py)
├── strategies/     # BaseStrategy, OrbBaseStrategy, 15 strategy implementations
│   └── patterns/   # PatternModule ABC, PatternParam, 10 patterns (BullFlag, FlatTop, DipAndRip, HODBreak, GapAndGo, ABCD, PreMarketHighBreak, MicroPullback, VwapBounce, NarrowRangeBreakout)
├── data/           # DataService (Databento/Alpaca/Replay/Backtest), Scanner, IndicatorEngine, UniverseManager, FMPReferenceClient, VIXDataService, HistoricalQueryService (DuckDB)
├── execution/      # Broker (IBKR/Alpaca/Simulated), Order Manager
├── analytics/      # Trade Logger, PerformanceCalculator, DebriefExport, Evaluation Framework
├── backtest/       # VectorBT helpers, Replay Harness, BacktestEngine (Sprint 27)
├── api/            # FastAPI REST + WebSocket, JWT auth
│   ├── routes/     # arena.py (GET /api/v1/arena/positions, GET /api/v1/arena/candles/{symbol}), market.py (GET /api/v1/market/status — no auth), historical.py (GET /api/v1/historical/symbols, /coverage, /bars/{symbol}, POST /validate-coverage)
│   └── websocket/  # ai_chat.py (WS streaming), arena_ws.py (/ws/v1/arena — 6 message types)
├── ui/             # React frontend (Vite + TypeScript + Tailwind v4)
│   └── features/
│       ├── copilot/  # CopilotPanel, ChatMessage, ActionCard
│       └── arena/    # ArenaPage, ArenaCard, ArenaControls, ArenaStatsBar, MiniChart, useArenaWebSocket, useArenaData
├── ai/             # Claude API integration (Sprint 22, active)
│   ├── client.py   # ClaudeClient (API wrapper, rate limiting, tool_use)
│   ├── config.py   # AIConfig (token budgets, TTLs, cost rates)
│   ├── prompts.py  # PromptManager (system prompt, guardrails)
│   ├── context.py  # SystemContextBuilder (per-page context)
│   ├── conversations.py  # ConversationManager (SQLite persistence)
│   ├── usage.py    # UsageTracker (per-call cost tracking)
│   ├── actions.py  # ActionManager (proposal lifecycle, TTL, re-check)
│   ├── executors.py # 5 ActionExecutors + ExecutorRegistry
│   ├── summary.py  # DailySummaryGenerator
│   ├── cache.py    # ResponseCache (TTL-based)
│   └── tools.py    # 5 tool_use definitions with JSON schemas
├── intelligence/   # CatalystPipeline, CatalystClassifier, CatalystStorage, BriefingGenerator, startup factory, polling loop (Sprints 23.5 + 23.6), SetupQualityEngine (quality_engine.py), DynamicPositionSizer (position_sizer.py) (Sprint 24)
│   └── learning/   # Learning Loop V1: OutcomeCollector, WeightAnalyzer, ThresholdAnalyzer, CorrelationAnalyzer, LearningService, ConfigProposalManager, LearningStore (Sprint 28)
├── utils/          # ThrottledLogger (Sprint 27.75)
├── config/         # system.yaml, system_live.yaml, strategies/*.yaml, regime.yaml, counterfactual.yaml, vix_regime.yaml, learning_loop.yaml, exit_management.yaml, historical_query.yaml
├── tests/          # pytest (backend) + Vitest (frontend)
├── docs/           # Decision log, sprint history, strategy specs, research reports
├── workflow/       # Metarepo submodule (protocols, templates, runner, universal rules)
└── .claude/        # rules/ (project-specific + universal→workflow), skills/→workflow, agents/→workflow
    └── rules/      # backtesting.md, trading-strategies.md, universal.md
```

## Commands

```bash
# Tests
python -m pytest --ignore=tests/test_main.py -n auto -q  # Full suite (~4,858 tests, ~114s with xdist)
python -m pytest tests/ -x               # Stop on first failure
python -m pytest tests/ -x -q            # Fail-fast, quiet
cd argus/ui && npx vitest run            # Frontend tests (~846)

# Trading engine
python -m argus.main                      # Start (paper trading default)
python -m argus.main --dry-run           # Connect and validate without trading
python -m argus.main --dev               # Dev mode (mock data, no external connections)
python -m argus.main --config system.yaml # Alpaca incubator mode (legacy)
python -m argus.main --config config/system_live.yaml  # Live mode (Databento + IBKR)

# Backtesting — operational wrappers (primary entrypoints)
python scripts/revalidate_strategy.py --strategy orb --start 2025-06-01 --end 2025-12-31
python scripts/validate_all_strategies.py --cache-dir data/databento_cache
python scripts/run_experiment.py --pattern bull_flag

# Backtesting — direct module CLIs (invoked internally by wrappers above)
python -m argus.backtest.data_fetcher --symbols TSLA,NVDA --start 2025-03-01 --end 2026-02-01
python -m argus.backtest.replay_harness --data-dir data/historical/1m --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.engine --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31 --strategy orb_breakout

# API & Frontend
python -m argus.api --dev                 # API server with mock data (password: "argus")
python -m argus.api.setup_password        # Generate password hash for production
cd argus/ui && npm install               # Install frontend dependencies
cd argus/ui && npm run dev               # Vite dev server
cd argus/ui && npm run build             # Production build

# Live operations
./scripts/start_live.sh [--with-ui]      # Start ARGUS (4 pre-flight checks, PID management)
./scripts/stop_live.sh                   # Graceful shutdown (SIGINT, 60s timeout, force kill)

# Validation & diagnostics
python scripts/diagnose_databento.py     # Databento EQUS.MINI capabilities
python scripts/test_session8_integration.py  # 13 integration checks
python scripts/test_session9_resilience.py   # 4 resilience checks
python scripts/diagnose_time_stop_eod.py # Time stop + EOD flatten (IBKR or mock)

# AI Layer
ANTHROPIC_API_KEY="sk-..." python -m argus.api --dev  # Run with AI enabled
python -m pytest tests/ai/ -x -q                       # AI module tests only

# Autonomous Sprint Runner (Sprint 23.2)
python scripts/sprint-runner.py --help                # Show all CLI options
python scripts/sprint-runner.py run path/to/sprint-package.yaml  # Execute sprint
python scripts/sprint-runner.py resume --run-dir path/to/run  # Resume from checkpoint

# Learning Loop (Sprint 28)
python scripts/run_learning_analysis.py               # Manual learning analysis
python scripts/run_learning_analysis.py --window-days 30  # Custom window
python scripts/run_learning_analysis.py --strategy-id orb_breakout  # Single strategy
python scripts/run_learning_analysis.py --dry-run     # Analyze without persisting
```

**Environment Variables:**
- `ANTHROPIC_API_KEY` — Required for AI Copilot. Gracefully disabled if unset.
- `ARGUS_JWT_SECRET` — Required for API authentication.
- `FMP_API_KEY` — Required for pre-market scanning.

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

## Architectural Rules

### Event Bus
- FIFO per subscriber, monotonic sequence numbers (DEC-025)
- Sole streaming mechanism — no callbacks on DataService (DEC-029)
- Type-only subscription; filtering in handlers, not at bus level (DEC-033)

### Strategies
- Daily-stateful, session-stateless (DEC-028)
- Inherit from BaseStrategy (or proven family base like OrbBaseStrategy)
- ALLOW_ALL cross-strategy policy (DEC-121/160)
- Per-signal time stops via SignalEvent.time_stop_seconds (DEC-122)

### Risk & Execution
- Risk Manager: approve-with-modification for share reduction/target tightening only. NEVER modify stops or entry (DEC-027)
- Concentration limit: approve-with-modification, 0.25R floor (DEC-249)
- Atomic bracket orders: entry + stop + T1 + T2 submitted together (DEC-117)
- All stock positions close intraday. Long only for V1.
- NEVER place broker orders without passing through the Risk Manager
- ALL trades MUST be logged to the database with full metadata
- All market-hours time comparisons MUST convert UTC timestamps to ET first using `timestamp.astimezone(ZoneInfo("America/New_York"))`. NEVER compare `.timestamp.time()` directly against ET constants like `time(9, 30)`. (DEC-061)

### Data
- Databento EQUS.MINI primary (DEC-248). Prices fixed-point × 1e9 (DEC-243)
- Databento threading: callbacks on reader thread → `call_soon_threadsafe()` (DEC-088)
- Historical data has ~15min intraday lag (DEC-244), multi-day daily bar lag (DEC-247)
- IndicatorEngine shared by all DataService implementations (DEC-092)
- Universe Manager: config-gated (`universe_manager.enabled`), fail-closed on missing reference data (DEC-277)
- Fast-path discard in DatabentoDataService drops non-viable symbols before IndicatorEngine (Sprint 23)
- Strategy universe filters are declarative YAML only — never modify strategy Python code for filter changes

### Frontend
- React + TypeScript, TanStack Query, Zustand, Framer Motion
- Chart libraries: Lightweight Charts (financial), Recharts (analytics), D3 (custom viz) (DEC-104/215)
- Design north star: "Bloomberg Terminal meets modern fintech" (DEC-109)
- Responsive: <640px phone, 640–1023px tablet, ≥1024px desktop (DEC-105)
- Animation budget: <500ms, 60fps, never blocks interaction (DEC-110)
- No conditional skeleton/content swaps — always render same DOM structure (Sprint 17.5 lesson)

### Config & DB
- YAML → Pydantic BaseModel (not BaseSettings) (DEC-032)
- aiosqlite for async DB; TradeLogger is sole persistence interface (DEC-034)
- Trade IDs: ULIDs via python-ulid (DEC-026)
- Separate configs: system.yaml (Alpaca incubator), system_live.yaml (Databento + IBKR) (DEC-231)
- NEVER hardcode configuration values — always read from YAML config files
- Broker API keys and secrets NEVER in code or committed files — environment variables only
- FMP_API_KEY required for pre-market scanning (Sprint 21.7, DEC-258)

### Backtesting
- VectorBT: precompute+vectorize architecture MANDATORY (DEC-149)
- BacktestEngine (Sprint 27): production-code backtesting via SynchronousEventBus, bar-level fill model, Databento OHLCV-1m + Parquet cache; `to_multi_objective_result()` produces regime-tagged `MultiObjectiveResult` (Sprint 27.5); optional `slippage_model_path` on `BacktestEngineConfig` loads calibrated slippage model
- Walk-forward validation: WFE > 0.3 required (DEC-047); `oos_engine` parameter selects BacktestEngine vs Replay Harness
- Pre-Databento backtests are PROVISIONAL (DEC-132). PARTIALLY RESOLVED (Sprint 21.6) — pipeline proven end-to-end, Bull Flag validated, 6 strategies pending full-universe re-validation
- See `.claude/rules/backtesting.md` for detailed sweep rules

### API
- FastAPI in-process (Phase 12 startup) (DEC-099)
- Single-user JWT with bcrypt (DEC-102)
- WebSocket: curated event list, tick throttling (DEC-101)
- AppState dataclass → FastAPI Depends() injection (DEC-100)

## UI/UX Rules

- **Design principles (DEC-109):** Information over decoration. Ambient awareness. Progressive disclosure. Motion with purpose. Mobile as primary trading surface. Research lab aesthetics.
- **Animation library (DEC-110):** Framer Motion for page transitions + stagger. CSS transitions for hover/micro-interactions. Lightweight Charts native for chart animations. Budget: <500ms, 60fps, never blocks interaction.
- **Chart library stack (DEC-104, DEC-108):** Lightweight Charts (time-series) + Recharts (standard charts) + D3 (custom viz, sparingly) + Three.js (current npm semver per `argus/ui/package.json`, Observatory Funnel/Radar 3D views, code-split via React.lazy).
- **UX Feature Backlog:** `docs/ui/ux-feature-backlog.md` — canonical inventory of all planned UI/UX enhancements. Reference when planning sprint UX scope. (DEC-106)
- **Responsive breakpoints:** 393px (iPhone SE/mini), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook Pro).
- **Mobile nav:** Bottom tab bar. Desktop/tablet: icon sidebar.
- **Frontend testing (DEC-130):** Vitest for React component tests. Config: `vitest.config.ts`. Pattern: `ComponentName.test.tsx` alongside component. Setup: `src/test/setup.ts`.
- **Positions UI state (DEC-129):** Display mode (table/timeline) and filter (all/open/closed) managed in Zustand store (`stores/positionsUI.ts`). Session-level — no localStorage.

## Testing

See `.claude/rules/testing.md` for all testing guidance (structure, naming, commands, xdist tiering, fixtures, known flakes).

## Documentation Sync

Doc updates are handled by the doc-sync skill. See `.claude/skills/doc-sync.md` for the protocol.

## Deferred Items

Track items that are intentionally postponed. Each item has a trigger condition. When that condition is met during a session, surface the item proactively.

| ID | Item | Trigger | Context |
|----|------|---------|---------|
| ~~DEF-003~~ | ~~datetime.utcnow() → datetime.now(UTC)~~ | — | **DONE** (Sprint 3). |
| ~~DEF-004~~ | ~~CPA cash-reserve consultation~~ | — | **SUPERSEDED** (DEC-380): CPA consultation removed from gates; Tax Intelligence Automation is a post-revenue deliverable. |
| DEF-006 | Backtrader integration if Replay Harness too slow | If replay >1hr for 6mo data | Backtrader dropped (DEC-046). Reconsidered only if Replay performance becomes insufficient. |
| DEF-007 | Pre-market data for scanner accuracy | Scanner accuracy becomes bottleneck | IEX free tier lacks pre-market. Resolution: validate against 1 month SIP data. |
| ~~DEF-008~~ | ~~Synthetic e2e trade trigger test~~ | — | **RESOLVED** (Sprint 8, DEC-061). |
| ~~DEF-009~~ | ~~VectorBT vs Replay cross-validation~~ | — | **DONE** (Sprint 9, DEC-069). |
| ~~DEF-010~~ | ~~Remove `_simulate_trades_for_day_slow()`~~ | — | **DONE** (Sprint 9, DEC-070). |
| DEF-011 | IQFeedDataService adapter | Forex or breadth indicators needed | ~$160–250/mo. Build when a specific feature needs forex or breadth. |
| DEF-012 | Databento L2 depth activation | A strategy requires order-book depth | MBP-10 available on Standard plan. |
| ~~DEF-013~~ | ~~Extract shared IndicatorEngine~~ | — | **DONE** (Sprint 12.5, DEC-092). |
| ~~DEF-014~~ | ~~SystemAlertEvent for dead data feed~~ | — | **PARTIALLY RESOLVED** (FIX-06, audit 2026-04-21): emitter side wired — `SystemAlertEvent` added to `argus/core/events.py`; `DatabentoDataService._run_with_reconnection()` publishes `source="databento_feed", alert_type="max_retries_exceeded", severity="critical"` when reconnect retries are exhausted. HealthMonitor subscription + Command Center surface deferred until the next main.py expansion session touches `HealthMonitor` (no active subscribers today; the event is in-place for when they land). IBKR/Alpaca emitter sites (`argus/execution/ibkr_broker.py:453,531`, `argus/data/alpaca_data_service.py:593`) still carry TODOs — out of FIX-06 scope. |
| ~~DEF-015~~ | ~~DatabentoScanner full-universe~~ | — | **SUPERSEDED by DEC-263** (Universe Manager, Sprint 23). |
| ~~DEF-016~~ | ~~Order Manager `place_bracket_order()`~~ | — | **DONE** (Sprint 17, DEC-117). |
| DEF-017 | Performance-weighted + correlation-adjusted allocation | 20+ days multi-strategy live data | V1 equal-weight; V2 ±10% based on trailing Sharpe/DD; V3 adds correlation penalty. |
| ~~DEF-018~~ | ~~Real VIX data integration~~ | — | **PARTIALLY RESOLVED** (Sprint 27.9): daily VIX via yfinance. Real-time VIX deferred. |
| DEF-019 | Breadth indicators (advance/decline, TICK, TRIN) | IQFeed activated | ~$160–250/mo. |
| DEF-020 | Cross-strategy sector exposure check | IQFeed activated OR fundamentals integrated | V1 skips sector exposure (DEC-126). 5% single-stock cap provides concentration cover. |
| DEF-021 | Sub-bar backtest precision for ORB Scalp | Tick-level data OR Scalp paper diverges | Synthetic ticks ~15s/bar (DEC-053); Scalp 30–120s holds sometimes resolve at bar boundary. |
| DEF-022 | VwapBaseStrategy ABC extraction | Second VWAP strategy designed | Follow the OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-023~~ | ~~Watchlist endpoint production implementation~~ | — | **PARTIALLY RESOLVED** (Sprint 21.7): scan_source/selection_reason populated. Remaining: current_price, sparkline, strategy state. |
| ~~DEF-024~~ | ~~Trailing Stop Mechanism~~ | — | **RESOLVED** (Sprint 28.5): configurable trail + exit escalation. |
| DEF-025 | Shared Consolidation Base Class | Second consolidation strategy designed | Follow OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-026~~ | ~~FTS5 full-text search~~ | — | **RESOLVED** (DEC-200): LIKE queries shipped as V1. |
| ~~DEF-027~~ | ~~Journal trade linking UI~~ | — | **RESOLVED** (DEC-201, Sprint 21c). |
| DEF-028 | CalendarPnlView strategy filter | Performance Workbench OR user request | Cross-strategy filter already available via Overview + Heatmaps tabs. Priority: LOW. |
| ~~DEF-029~~ | ~~Persist live candle data for post-session replay~~ | — | **OBSOLETE** (audit P1-H4): superseded by IntradayCandleStore + Arena endpoint. |
| ~~DEF-030~~ | ~~Live candlestick chart real-time updates~~ | — | **OBSOLETE** (audit P1-H4): Arena WS `arena_candle` (Sprint 32.75). |
| DEF-031 | Orders table persistence | Post-hoc order forensics needed | Orders not persisted to DB, only completed trades. |
| DEF-032 | FMPScannerSource criteria_list filtering | Quality Engine provides scoring criteria | `scan()` accepts `criteria_list` but ignores it. Pointer comment re-verified at `argus/data/fmp_scanner.py::scan` by FIX-06 audit 2026-04-21 (P1-C2-14). |
| DEF-033 | Approve→Executed status via WebSocket instead of setTimeout | Next UI polish pass | Cosmetic — proposal correctly marked `approved` in DB; UI status badge faked via 1500ms setTimeout. |
| ~~DEF-034~~ | ~~Pydantic serialization warnings on `review_verdict`~~ | — | **RESOLVED** (FIX-20, audit 2026-04-21). |
| DEF-035 | FMP Premium Upgrade ($59/mo) | Batch-quote speed becomes bottleneck | 27 min → ~2 min load. Sprint 23.5 completed without upgrade. Priority: LOW. |
| ~~DEF-036~~ | ~~Stock-list response caching~~ | — | **RESOLVED** (Sprint 23.6, DEC-314): ~27 min → ~2–5 min. |
| ~~DEF-037~~ | ~~FMP API key redaction in error logs~~ | — | **RESOLVED** (FIX-06, audit 2026-04-21, P1-C2-11): `FMPReferenceClient._redact()` helper replaces the active API key with `[REDACTED]` before any error log emission; routed through `fetch_stock_list` network/exception paths and the canary test. `DatabentoDataService.fetch_daily_bars()` gets a WARNING comment against future log additions. Regression guards in `tests/data/test_fmp_reference.py::test_redact_masks_api_key_in_error_strings`. |
| DEF-038 | Fuzzy/embedding-based catalyst dedup | Sprint 28+ or high duplicate volume | Current rule-based dedup (DEC-311) handles the common case. Priority: LOW. |
| DEF-039 | Runner conformance check reliability audit | conformance_fallback_count consistently >2/sprint | Monitoring only. Priority: LOW. |
| DEF-040 | Runner main.py further decomposition | Runner exceeds ~2,500 lines | main.py 2,067 lines. Extraction candidates: session loop, parallel sessions, notifications. Priority: LOW. |
| ~~DEF-041~~ | ~~Frontend catalyst endpoint short-circuit~~ | — | **CLOSED** (Sprint 23.9, DEC-329). |
| ~~DEF-043~~ | ~~/debrief/briefings 503 fix~~ | — | **CLOSED** (Sprint 23.9). |
| ~~DEF-044~~ | ~~SPY intraday regime re-evaluation~~ | — | **PARTIALLY RESOLVED** (Sprint 25.6, DEC-346): 300s periodic reclassify. Regime-aware strategy behavior still open. |
| ~~DEF-045~~ | ~~SEC Edgar timeout test rewrite~~ | — | **CLOSED** (Sprint 23.9). |
| ~~DEF-046~~ | ~~test_main.py xdist failures (2 tests)~~ | — | **CLOSED** (Sprint 23.9). 4 more tracked as DEF-048. |
| DEF-047 | Bulk catalyst endpoint | Unscheduled | Consolidate per-symbol catalyst GETs into single batch request. Priority: LOW. |
| DEF-048 | Additional test_main.py xdist failures | Unscheduled | 4 more tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race as DEF-046). Priority: LOW. |
| DEF-049 | test_orchestrator_uses_strategies_from_registry isolation failure | Unscheduled | Fails isolated, passes in full suite. Pre-existing. Priority: LOW. |
| ~~DEF-050~~ | ~~Full ArgusSystem e2e integration test~~ | — | **RESOLVED** (Sprint 24.1 S2). |
| ~~DEF-052~~ | ~~Dashboard quality cards interactivity~~ | — | **RESOLVED** (Sprint 24.1 S4b+S4f). |
| ~~DEF-053~~ | ~~Quality column in Dashboard tables~~ | — | **RESOLVED** (Sprint 24.1 S4b). |
| ~~DEF-054~~ | ~~Orchestrator clickable signal rows~~ | — | **RESOLVED** (Sprint 24.1 S4b). |
| ~~DEF-055~~ | ~~Orchestrator 3-column layout~~ | — | **RESOLVED** (Sprint 24.1 S4a). |
| ~~DEF-056~~ | ~~QualityOutcomeScatter page placement~~ | — | **RESOLVED** (Sprint 24.1 S4a). |
| ~~DEF-057~~ | ~~SEC EDGAR EFTS URL validation~~ | — | **RESOLVED** (Sprint 24.1 S2). |
| ~~DEF-058~~ | ~~Trades DB quality columns~~ | — | **RESOLVED** (Sprint 24.1 S1a). |
| ~~DEF-059~~ | ~~Pre-existing TypeScript build errors (22)~~ | — | **RESOLVED** (Sprint 24.1 S3). |
| ~~DEF-060~~ | ~~PROVISIONAL comment gap in system YAML~~ | — | **RESOLVED** (Sprint 24.1 S1b). |
| ~~DEF-061~~ | ~~Quality API private attribute access~~ | — | **RESOLVED** (Sprint 24.1 S1b). |
| ~~DEF-062~~ | ~~QA seed script cleanup~~ | — | **RESOLVED** (Sprint 24.1 S1b). |
| ~~DEF-063~~ | ~~Trust cache on startup (reference data)~~ | — | **RESOLVED** (Sprint 25.9 S2, DEC-362). |
| DEF-064 | Warm-up 78% failure rate on mid-session boot | Unscheduled | Databento historical 422 during lazy warm-up. Pre-market boot (normal path) skips warm-up per DEC-316. Priority: LOW. |
| ~~DEF-074~~ | ~~Dual regime recheck path consolidation~~ | — | **RESOLVED** (FIX-03, audit 2026-04-21). |
| ~~DEF-075~~ | ~~`fetch_daily_bars()` via FMP for regime~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-076~~ | ~~Health endpoint `last_data_received` null~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-077~~ | ~~Diagnostic logging for sizer 0 shares~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-078~~ | ~~Rate-limit regime reclassification warnings~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-079~~ | ~~Automated debrief export at shutdown~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-080~~ | ~~VWAP Reclaim zero-trade suspension false~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-081~~ | ~~ENTRY_EVALUATION conditions_passed metadata~~ | — | **RESOLVED** (Sprint 25.7 S1). |
| ~~DEF-082~~ | ~~CatalystStorage → catalyst.db (catalyst_quality always 50)~~ | — | **RESOLVED** (FIX-01, audit 2026-04-21, `tests/test_fix01_catalyst_db_path.py`). |
| ~~DEF-083~~ | ~~API auth 403→401~~ | — | **RESOLVED** (Sprint 25.8, DEC-351). |
| DEF-084 | Full test suite runtime optimization | Partially resolved | Remaining slow: `test_stale_data_detection/recovery`. Priority: LOW. |
| ~~DEF-085~~ | ~~Close-position endpoint regression~~ | — | **RESOLVED** (Sprint 25.8, DEC-352). |
| ~~DEF-086~~ | ~~WebSocket test hangs~~ | — | **RESOLVED** (post-sprint). |
| ~~DEF-087~~ | ~~11 pre-existing test failures~~ | — | **RESOLVED** (post-sprint). |
| ~~DEF-088~~ | ~~PatternParam structured type~~ | — | **RESOLVED** (Sprint 29 S1–S2, DEC-378). |
| ~~DEF-089~~ | ~~In-memory ResultsCollector for parallel sweeps~~ | — | **OBSOLETE** (audit P1-H4): Sprint 31.5 ProcessPoolExecutor removed contention. |
| ~~DEF-090~~ | ~~execution_record time_of_day ET~~ | — | **RESOLVED** (Sprint 27.5 cleanup). |
| ~~DEF-091~~ | ~~Public accessors on V1 RegimeClassifier + VIXDataService private attrs~~ | — | **RESOLVED** (FIX-05, audit 2026-04-21). `RegimeClassifier.compute_trend_score()` + `.vol_low_threshold` / `.vol_high_threshold` properties and `VIXDataService.config` property are the supported read surfaces. `RegimeClassifierV2` no longer reads `self._v1_classifier._compute_trend_score` / `._config.*` or `vix_data_service._config`. |
| ~~DEF-092~~ | ~~Unused Protocol types in regime.py~~ | — | **RESOLVED** (FIX-05, audit 2026-04-21). Four orphaned Protocol classes (`BreadthCalculator`, `CorrelationCalculator`, `SectorRotationCalculator`, `IntradayCalculator`) deleted from `argus/core/regime.py`. `typing.Protocol` import also dropped. |
| ~~DEF-093~~ | ~~main.py duplicate orchestrator YAML load~~ | — | **RESOLVED** (FIX-03, audit 2026-04-21). |
| DEF-094 | ORB Scalp time-stop dominance | 5+ sessions of data | ~80% of scalp exits via 120s time-stop (vs target/stop). Tune after data. Priority: LOW. |
| DEF-095 | Submit-before-cancel bracket amendment pattern | Live trading hardening | Currently cancel-then-resubmit leaves sub-second unprotected window. Priority: MEDIUM. |
| ~~DEF-096~~ | ~~Protocol type for duck-typed candle store reference~~ | — | **RESOLVED** (FIX-07, audit 2026-04-21). New `argus/core/protocols.py` exposes `CandleStoreProtocol` + `CounterfactualStoreProtocol` (both `@runtime_checkable`). Consumers replaced: `CounterfactualTracker._store` / `._candle_store` and `PatternBasedStrategy._candle_store` are now Protocol-typed; the pre-FIX-07 `hasattr(store, "get_bars")` / `hasattr(store, "write_open")` probes were removed. Covers the P1-D1 L5 recurrence (same pattern on `_store`). Regression: `tests/intelligence/test_fix07_audit.py::TestProtocolStores`. |
| ~~DEF-097~~ | ~~Schedule monthly cache update cron~~ | — | **RESOLVED** (FIX-21, audit 2026-04-21): paired with DEF-162 in `docs/live-operations.md` §12. |
| DEF-098 | Trade count inconsistency between Dashboard cards | Unscheduled | Paper-trading ghost positions; fix depends on DEF-099. Priority: MEDIUM. |
| DEF-099 | Position reconciliation ghost positions | Monitor 5+ sessions | **PARTIALLY RESOLVED** (Sprint 27.8 S1): auto-cleanup + bracket exhaustion + ExitReason.RECONCILIATION. |
| DEF-100 | IBKR paper trading repricing storm (err 399) | Unscheduled | IBKR-paper-specific; live unaffected. Sprint 27.75 throttling mitigates noise. Priority: LOW-MEDIUM. |
| ~~DEF-101~~ | ~~Tests coupled to paper-trading config values~~ | — | **RESOLVED** (Sprint 27.8 S1). |
| ~~DEF-102~~ | ~~Trades page server-side stats~~ | — | **RESOLVED** (Sprint 28.75 S2, subsumed by DEF-117). |
| DEF-103 | yfinance reliability as unofficial scraper | Monitor 5+ sessions | Cache + staleness self-disable + optional FMP fallback mitigate. Priority: LOW. |
| ~~DEF-104~~ | ~~Dual ExitReason enums (events.py + trading.py) sync~~ | — | **RESOLVED** (FIX-05, audit 2026-04-21). `argus.core.events` now re-exports `ExitReason` from `argus.models.trading` — single source of truth. Eliminates the Sprint-27.8-style drift risk. |
| DEF-105 | Reconciliation trades inflate total_trades | Unscheduled | Related to DEF-098. Priority: LOW. |
| ~~DEF-106~~ | ~~`models.py from_dict()` has ~8 assert statements~~ | — | **RESOLVED** (FIX-07, audit 2026-04-21). All 8 `assert isinstance(...)` sites in `argus/intelligence/learning/models.py::LearningReport.from_dict()` + `_parse_weight_rec()` converted to explicit `if not isinstance: raise TypeError(...)` guards that survive `python -O`. Batched with the new P1-F1 #7 site at `argus/api/routes/counterfactual.py:204` (`_breakdown_to_response`). Regression: `tests/intelligence/test_fix07_audit.py::TestLearningReportFromDictRaisesTypeError` + `tests/api/test_fix07_audit.py::TestBreakdownTypeGuardRaises`. Follow-on analytics-layer sites (`argus/analytics/ensemble_evaluation.py` × 3, `argus/intelligence/learning/outcome_collector.py` × 2) carry the same anti-pattern and are out-of-scope for FIX-07 — see DEF-106's original row for context; a future sweep can close them out via the same pattern. |
| ~~DEF-107~~ | ~~Unused `raiseRec` destructured variable in LearningInsightsPanel.tsx L388~~ | — | **RESOLVED** (FIX-08, audit 2026-04-21, Finding 18). Removed `raise: raiseRec` from the `conflictingThresholds.map` destructure. **Spec path drift note (P12 verification):** the FIX-08 spec scope header listed `argus/ui/src/features/learning/LearningInsightsPanel.ts` and the Finding 18 body said `features/learning/LearningInsightsPanel.tsx`; actual path is `argus/ui/src/components/learning/LearningInsightsPanel.tsx:388`. `lower`, `lowerProposal`, `raiseProposal` remain in the destructure — they are referenced in the JSX body. Vitest delta 0; no test referenced the unused variable. |
| DEF-108 | R2G `_build_signal` sync limitation (atr_value=None) | Unscheduled | R2G currently uses percent fallback. Priority: LOW. |
| ~~DEF-109~~ | ~~V1 trailing-stop config dead code on OrderManagerConfig~~ | — | **RESOLVED** (audit 2026-04-21 FIX-16-config-consistency): `enable_trailing_stop` and `trailing_stop_atr_multiplier` removed from `OrderManagerConfig`; AMD-10 deprecation warning removed from `main.py`; legacy fields removed from `config/order_manager.yaml`; `TestDeprecatedConfigWarning` test class removed. Trailing stops live entirely in `config/exit_management.yaml` via `ExitManagementConfig` (Sprint 28.5). |
| DEF-110 | Exit reason misattribution on escalation-failure + trail-active | Unscheduled | Cosmetic — position closes correctly. Priority: LOW. |
| ~~DEF-111~~ | ~~Trail stops not firing in live session~~ | — | **RESOLVED** (Sprint 28.75 S1): config timing, not code. |
| ~~DEF-112~~ | ~~Flatten-pending orders hang indefinitely~~ | — | **RESOLVED** (Sprint 28.75 S1): flatten_pending_timeout + max_flatten_retries. |
| ~~DEF-113~~ | ~~"flatten already pending" log spam~~ | — | **RESOLVED** (Sprint 28.75 S1): ThrottledLogger 60s/symbol. |
| ~~DEF-114~~ | ~~"IBKR portfolio snapshot missing" log spam~~ | — | **RESOLVED** (Sprint 28.75 S1): ThrottledLogger 600s/symbol. |
| ~~DEF-115~~ | ~~Closed positions tab capped at 50~~ | — | **RESOLVED** (Sprint 28.75 S2): limit 250. |
| ~~DEF-116~~ | ~~TodayStats win rate 0%~~ | — | **RESOLVED** (Sprint 28.75 S2): frontend display logic. |
| ~~DEF-117~~ | ~~Trades page stats freeze + filter bug~~ | — | **RESOLVED** (Sprint 28.75 S2): server-side `/api/v1/trades/stats`. |
| ~~DEF-118~~ | ~~Avg R missing from Trades page summary~~ | — | **RESOLVED** (Sprint 28.75 S2). |
| ~~DEF-119~~ | ~~Open positions colored P&L + exit price~~ | — | **RESOLVED** (Sprint 28.75 S2). |
| ~~DEF-120~~ | ~~VixRegimeCard fills entire viewport~~ | — | **RESOLVED** (Sprint 28.75 S2). |
| ~~DEF-121~~ | ~~PatternBacktester `_create_pattern_by_name()`~~ | — | **RESOLVED** (Sprint 32 S3): all 7 patterns via factory delegation. |
| DEF-122 | ABCD swing detection O(n³) optimization | Parameter sweeps at scale | PatternBacktester full sweep times out. Precomputed swing cache needed. Priority: MEDIUM. |
| ~~DEF-123~~ | ~~`build_parameter_grid()` float accumulation~~ | — | **RESOLVED-VERIFIED** (FIX-08, audit 2026-04-21, Finding 6). Confirmed both float-grid generators (`_generate_param_values` for PatternParam and `_generate_exit_values` for ExitSweepParam) use the integer-multiplied form `round(min + i * step, 6)` rather than cumulative addition — this is what `numpy.arange` would produce internally. The spec's `numpy.arange` migration would add a numpy import to a hot grid path for zero behavioural gain; existing mitigation kept. Inline docstrings now point at the chosen pattern with rationale, so a future reviewer doesn't reflexively re-flag the same trade-off. |
| ~~DEF-124~~ | ~~Pattern constructor params not wired from YAML~~ | — | **RESOLVED** (Sprint 32): `build_pattern_from_config()`. |
| DEF-125 | Time-of-day signal conditioning | Sprint 32+ | 10:00 AM hour worst-performing; no strategy adjusts by time-of-day beyond operating window. |
| DEF-126 | Regime-strategy interaction profiles | Sprint 32.5+ | Per-strategy regime sensitivity tuning needed. |
| DEF-127 | Virtual scrolling for trades table | Unscheduled | Limit raised 250→1000 (Sprint 29.5 S3). Virtual scrolling deferred until 1000 insufficient. |
| DEF-128 | IBKR error 404 multi-position qty divergence prevention | Sprint 30 | Sprint 29.5 S1 added re-query-qty; deeper fix prevents divergence. |
| ~~DEF-131~~ | ~~Experiments + Counterfactual visibility (API + UI)~~ | — | **RESOLVED** (Sprint 32.5 S5–S7). |
| ~~DEF-132~~ | ~~Exit parameters as variant dimensions~~ | — | **RESOLVED** (Sprint 32.5 S1+S2). |
| ~~DEF-133~~ | ~~Adaptive Capital Intelligence vision doc~~ | — | **RESOLVED** (Sprint 32.5 S8). |
| ~~DEF-134~~ | ~~BacktestEngine all 7 PatternModule patterns~~ | — | **RESOLVED** (Sprint 32.5 S3+S4). |
| DEF-135 | Full visual verification of Shadow Trades + Experiments pages | Post first paper-trading week with `experiments.enabled=true` | Visual items untestable until data accumulates. |
| ~~DEF-136~~ | ~~GoalTracker.test.tsx Vitest failures~~ | — | **RESOLVED** (Sprint 32.75). |
| ~~DEF-137~~ | ~~`test_history_store_migration` hardcoded date~~ | — | **RESOLVED** (Sprint 32.8). |
| ~~DEF-138~~ | ~~ArenaPage.test.tsx WebSocket mock~~ | — | **RESOLVED** (Sprint 32.8). |
| ~~DEF-139~~ | ~~Startup zombie flatten queue~~ | — | **RESOLVED** (Sprint 32.9 S1): `getattr(pos, "qty", 0)` → `shares`. |
| ~~DEF-140~~ | ~~EOD flatten reports closed but broker retains~~ | — | **RESOLVED** (Sprint 32.9 S1): same shares/qty fix + asyncio.Event fill verification. |
| ~~DEF-141~~ | ~~Intelligence polling unbound symbols~~ | — | **RESOLVED** (Sprint 32.9 S2). |
| ~~DEF-142~~ | ~~Quality engine grade compression (system_live pre-recal)~~ | — | **RESOLVED** (FIX-01, DEC-384): standalone overlay registry. |
| ~~DEF-143~~ | ~~BacktestEngine ignores config_overrides on patterns~~ | — | **RESOLVED** (Sprint 31A S1). |
| ~~DEF-144~~ | ~~Debrief export safety_summary incomplete~~ | — | **RESOLVED** (Sprint 31A S1+S3). |
| ~~DEF-145~~ | ~~Sweep tooling --symbols/--universe-filter~~ | — | **RESOLVED** (Sprint 31A.75 S1). |
| ~~DEF-146~~ | ~~DuckDB BacktestEngine pre-filter wiring~~ | — | **RESOLVED** (Sprint 31.5 S2). |
| DEF-147 | DuckDB Research Console backend | Sprint 31B | `HistoricalQueryService` as backend for SQL-based sweep viz. Priority: LOW. |
| DEF-148 | FRED macro regime service | Sprint 34 | New `argus/data/fred_macro_service.py`; `MacroSnapshot` + 3 derived regimes. Priority: MEDIUM. |
| DEF-149 | FRED VIX backup source (VIXCLS fallback) | Opportunistic | Priority: LOW. |
| ~~DEF-150~~ | ~~Time-of-day arithmetic bug in `test_check_reminder_sends_after_interval`~~ | — | **RESOLVED** (FIX-13a, 2026-04-23): one-line fix at `tests/sprint_runner/test_notifications.py:313` replaces `(minute - 2) % 60` with `datetime.now(UTC) - timedelta(minutes=2)`. No longer fails during the first 2 minutes of every hour. |
| ~~DEF-151~~ | ~~date objects not JSON-serializable in ExperimentStore~~ | — | **RESOLVED** (Apr 4, commit 3a48bcf): `default=str` in `store.py:193`. |
| ~~DEF-152~~ | ~~gap_and_go stop-price bug~~ | — | **RESOLVED** (Sprint 31.75 S1): `min_risk_per_share` + ATR floor. |
| ~~DEF-153~~ | ~~config_fingerprint NULL in BacktestEngine trades~~ | — | **RESOLVED** (Sprint 31.75 S1). |
| ~~DEF-154~~ | ~~VWAP Bounce sweep axes inadequate~~ | — | **RESOLVED** (Sprint 31.75 S2): 4 signal-density controls. |
| ~~DEF-155~~ | ~~Premature `api_server → healthy` signal~~ | — | **RESOLVED** (Apr 20 impromptu): `_wait_for_port()` gates health. |
| ~~DEF-156~~ | ~~start_live.sh post-startup health probe~~ | — | **RESOLVED** (Apr 20 impromptu). |
| ~~DEF-157~~ | ~~evaluation.db VACUUM~~ | — | **RESOLVED** (Apr 20 impromptu): 3.7 GB → 209 MB. |
| ~~DEF-158~~ | ~~Duplicate SELL orders flipping positions short~~ | — | **RESOLVED** (Apr 20 impromptu): 3 root causes fixed. |
| ~~DEF-159~~ | ~~Reconstructed flatten trades with entry_price=0.00~~ | — | **RESOLVED** (Apr 20 impromptu): `entry_price_known` column + analytics exclusion. |
| DEF-160 | Shutdown race between bracket-cancel flatten and stop-retry | Unscheduled | May be subsumed by DEF-158 fix. Cosmetic — positions close correctly. Priority: LOW. |
| ~~DEF-161~~ | ~~DuckDB Parquet consolidation (983K files unusable)~~ | — | **RESOLVED** (Sprint 31.85): `scripts/consolidate_parquet_cache.py` + 24K per-symbol consolidated cache. |
| ~~DEF-162~~ | ~~Monthly re-consolidation cron scheduling~~ | — | **RESOLVED** (FIX-21, audit 2026-04-21): paired with DEF-097 in `docs/live-operations.md` §12. |
| ~~DEF-163~~ | ~~Timezone-boundary bug in `test_get_todays_pnl_excludes_unrecoverable` — SQLite's `date()` UTC-normalizes stored ISO timestamps before extracting the date, so a synthetic `exit_time=now` during the 20:00–24:00 ET window drifts to next-day-UTC and mismatches `today_et`.~~ | — | **RESOLVED** (IMPROMPTU-03, 2026-04-22). Test rewritten to use fixed 15:00 ET `exit_time` — deterministic across all wall-clock windows. Latent production concern (SQL-side UTC normalization) tracked as DEF-191; does not affect current operations because real trades can only exit during market hours. |
| DEF-164 | Late-night ARGUS boot collides with after-hours auto-shutdown | Unscheduled | Sprint 31.85 operator activation. Fix candidates: shutdown waits for init, or suppress auto-shutdown N min post-boot. Priority: LOW. |
| ~~DEF-165~~ | ~~DuckDB conn close hangs when CREATE VIEW interrupted~~ | — | **RESOLVED** (FIX-06, audit 2026-04-21, P1-C2-7): `HistoricalQueryService.close()` now calls `self._conn.interrupt()` (best-effort, swallow AttributeError + engine errors) before `self._conn.close()`. DEF-164 late-night activation scenario no longer hangs the teardown path. |
| DEF-166 | `test_speed_benchmark` flaky under pytest-cov | Unscheduled | Audit P1-H4. Not blocking. Priority: LOW. |
| ~~DEF-167~~ | ~~Vitest hardcoded-date decay in 4 files~~ | — | **RESOLVED** (FIX-13a, 2026-04-23): the 3 remaining pending sites flagged in the FIX-13a kickoff (`TradesPage.test.tsx:64,66`, `PerformancePage.test.tsx:68,69,87-89,99`, `ResearchDocCard.test.tsx:26,41,42`) converted to dynamic `new Date().toISOString()` / `Date.now() - N * 86400_000` patterns. Remaining hardcoded dates across the Vitest suite are mock-fixture data with no decay surface (no assertion reads the specific date value). |
| DEF-168 | `docs/architecture.md` API catalog substantially drifted | P1-H1a follow-up | ≥10 mismatches audited 2026-04-21. Warning banner added in place; correct fix is to regenerate catalog by introspecting the FastAPI app. Priority: MEDIUM. |
| DEF-169 | `--dev` mode retired (FIX-11) | Monitor | `dev_state.py` + `argus/api/__main__.py` deleted. `_mock_watchlist` now test-only. `GET /trades/{id}/replay` → 501 until DEF-029 lands. Priority: INFORMATIONAL. |
| ~~DEF-170~~ | ~~VIX regime calculators stay None in production~~ | — | **RESOLVED** (FIX-05, audit 2026-04-21). `RegimeClassifierV2.attach_vix_service()` now re-instantiates the four VIX calculators (`VolRegimePhaseCalculator`, `VolRegimeMomentumCalculator`, `TermStructureRegimeCalculator`, `VarianceRiskPremiumCalculator`) from the injected service when `regime_config.vix_calculators_enabled` is `True`. The lifespan path `api/server.py:_init_vix_data_service → orchestrator.attach_vix_service → v2.attach_vix_service` now produces a fully-wired classifier instead of reference-only. Paired DEF-091 cleanup: V1's public `compute_trend_score()` / `vol_low_threshold` / `vol_high_threshold` + VIX service's `config` property replace private-attr reach-ins. Regression: `tests/core/test_regime_vector_expansion.py::TestAttachVixServiceRewiresCalculators` (4 tests). |
| ~~DEF-171~~ | ~~`test_all_ulids_mapped_bidirectionally` xdist flake~~ | — | **RESOLVED** (FIX-13a, 2026-04-23): root cause was `order._mock_order_id = id(order) % 10000` in the `mock_ib` fixture (`tests/execution/test_ibkr_broker.py:91`). Collisions on the low 13 bits of `id(order)` could assign the same `orderId` to two distinct orders inside a single test, overwriting the bidirectional mapping. Replaced with an `itertools.count(1)` monotonic counter scoped to the fixture. Verified 82 tests pass under `-n auto`. |
| ~~DEF-172~~ | ~~Duplicate `CatalystStorage` instances active concurrently in live mode~~ | — | **RESOLVED-VERIFIED** (IMPROMPTU 2026-04-22). Behavioral verification: (1) `main.py` shutdown step 5a closes `self._catalyst_storage` cleanly (FIX-03); (2) `argus/api/server.py` `_teardown` calls `shutdown_intelligence(components)` → `components.storage.close()` in `argus/intelligence/startup.py`; (3) `CatalystStorage.initialize()` in `argus/intelligence/storage.py:143` sets `PRAGMA journal_mode = WAL`, enabling safe two-reader/single-writer concurrency against `catalyst.db`. "Duplicate" reduces to two independent read handles over the same SQLite file in WAL mode; write path is solely owned by the intelligence pipeline instance; both close paths fire independently. Structural consolidation deferred to DEF-175 (dedicated post-31.9 refactor). |
| ~~DEF-173~~ | ~~`LearningStore.enforce_retention()` never called at boot~~ | — | **RESOLVED** (IMPROMPTU 2026-04-22). `argus/api/server.py::_init_learning_loop` now calls `await learning_store.enforce_retention(ll_config.report_retention_days)` immediately after `learning_store.initialize()`, mirroring the FIX-03 `ExperimentStore` retention pattern in `main.py`. Protected `APPLIED`/`REVERTED` proposal reports are preserved by enforce_retention's SQL (Amendment 11). +1 regression guard: `tests/api/test_init_learning_loop.py::test_init_learning_loop_enforces_retention`. Note: the wiring location is part of DEF-175's migration scope — the call will move from api/server.py to main.py when component construction is consolidated. |
| DEF-175 | Component ownership consolidation — multiple components (`CatalystStorage`, `SetupQualityEngine`, `DynamicPositionSizer`, `ExperimentStore`) have parallel construction sites in both `argus/main.py` and `argus/api/server.py` `_init_*` lifespan phases, producing duplicate instances at runtime. Root cause: `api/server.py` lifespan is being used as a component construction site when those components are conceptually owned by ArgusSystem. DEF-172 and DEF-173 were individual symptoms. Full fix requires migrating component construction out of `api/server.py` lifespan into `main.py` Phase 9.x so ArgusSystem is sole owner and `api/server.py` becomes pure REST/WS adapter. | Dedicated post-Sprint-31.9 sprint (~2-3 sessions) | Discovery doc: `docs/sprints/post-31.9-component-ownership/DISCOVERY.md`. Blocked on Sprint 31.9 closure. MEDIUM priority — no active runtime harm today (SetupQualityEngine is stateless; CatalystStorage duplicates handled by SQLite WAL) but each passing week adds risk surface as new components follow the same pattern. |
| DEF-174 | Tauri desktop wrapper never integrated. Platform-detection helpers (`isTauri`, `isPWA`, `isMacOS`, etc.) shipped in `argus/ui/src/utils/platform.ts` during Sprint 16, but nothing in `argus/ui/src/` ever imported them and no `@tauri-apps/*` dependency was added. The file was deleted by FIX-12 (audit 2026-04-21, P1-F2-M08) since the dead code was actively misleading — `CLAUDE.md` previously advertised "Tauri desktop + PWA mobile" as shipped. Current state: PWA only. | Opportunistic (only if desktop-app packaging becomes a product requirement) | If Tauri integration is revisited, reinstate platform-detection helpers at that point against the then-current `@tauri-apps/api` surface; a Sprint-16-era copy is not a safe starting point. Priority: LOW — no active failure; removing the drift between claimed and actual architecture was the goal. |
| DEF-176 | Full removal of deprecated `OrderManager(auto_cleanup_orphans=...)` kwarg. FIX-04 (audit 2026-04-21, P1-C1-L10) added a `DeprecationWarning` when the legacy kwarg is used and verified production (`argus/main.py`) passes `reconciliation_config=` instead. Three reconciliation test modules — `tests/execution/test_order_manager_reconciliation.py`, `test_order_manager_reconciliation_redesign.py`, and `test_order_manager_sprint2875.py` — still pass the deprecated kwarg and were outside FIX-04's declared scope. | Opportunistic / next execution-layer cleanup sprint | Migrate the three test files to the typed `ReconciliationConfig(auto_cleanup_orphans=...)` constructor, then delete the `auto_cleanup_orphans: bool = False` parameter from `OrderManager.__init__`, the docstring entry, the `if auto_cleanup_orphans and reconciliation_config is None: warnings.warn(...)` guard, and the `ReconciliationConfig(auto_cleanup_orphans=auto_cleanup_orphans)` fallback. Priority: LOW. |
| DEF-177 | `RejectionStage` enum missing `MARGIN_CIRCUIT`. Margin-circuit-breaker rejections currently emit `SignalRejectedEvent(rejection_stage="risk_manager")`, conflating them with ordinary risk-manager rejections in the `FilterAccuracy.by_stage` cut (the principal cut used by Experiments and Learning surfaces). FIX-04 (audit 2026-04-21, P1-D1-M03) identified the fix but deferred it: adding `MARGIN_CIRCUIT = "margin_circuit"` requires editing `argus/intelligence/counterfactual.py` (the enum), updating `counterfactual_positions.rejection_stage` schema/values, and bumping the emitted stage at `argus/execution/order_manager.py:485`. Scope spans execution + intelligence domains and was outside FIX-04's execution-only declared scope (halt-rule-4). *Cross-references DEF-184 — both modify `RejectionStage` in orthogonal directions; coordinate in one session.* | Dedicated cross-domain session, must coordinate with DEF-184 | Cross-domain fix: (1) extend `RejectionStage` enum in `argus/intelligence/counterfactual.py` with `MARGIN_CIRCUIT`; (2) confirm `RejectionStage(event.rejection_stage)` call at `argus/main.py:1833` parses "margin_circuit" via StrEnum — additive, no existing consumer breaks; (3) change `order_manager.py:485` `rejection_stage="risk_manager"` → `rejection_stage="margin_circuit"` inside the margin-circuit block; (4) add regression test asserting the emitted stage differs under margin open vs ordinary risk rejection. Priority: MEDIUM — masks operational signal during margin incidents. |
| DEF-178 | `alpaca-py` still listed in core `[project.dependencies]` despite DEC-086 demoting Alpaca to incubator-only. Four runtime files still import it (`argus/execution/alpaca_broker.py`, `argus/data/alpaca_data_service.py`, `argus/data/alpaca_scanner.py`, `argus/backtest/data_fetcher.py`). FIX-18 (audit 2026-04-21, P1-I-L04) left the constraint in place and added an inline pointer comment; the full fix requires moving `alpaca-py` to `[project.optional-dependencies].incubator`, feature-detecting the import at each of the four call sites (`try: import alpaca ... except ImportError: ...`), and gating activation via `BrokerSource.ALPACA` / `DataSource.ALPACA`. Cross-ref PF-07 under P1-C1 / P1-C2. | Opportunistic / execution-layer cleanup sprint | Sequence: (1) create `[project.optional-dependencies].incubator = ["alpaca-py>=0.30,<1"]`; (2) wrap each of the 4 `import alpaca*` sites in a local try/except that raises a clear `RuntimeError` with `pip install -e ".[incubator]"` guidance when the config selects an Alpaca source and the extra is absent; (3) verify `system_live.yaml` / production deployment paths never reach those sites (Databento + IBKR only). Priority: LOW. |
| DEF-179 | Migrate `python-jose` → `PyJWT` for JWT signing/verification across the Command Center API. FIX-18 (audit 2026-04-21, P1-I-M02) mitigated CVE-2024-33663 by bumping the lower bound to `>=3.4.0,<4` — the CVE is fixed and `python-jose` has in fact shipped 3.4.0 and 3.5.0 (the audit finding's "no release since 2022" claim is superseded). `python-jose` remains imported at `argus/api/auth.py:26`, `argus/api/websocket/live.py:18`, `argus/api/websocket/observatory_ws.py:19`, `argus/api/websocket/ai_chat.py:17`, `argus/api/websocket/arena_ws.py:20`, plus two test modules (`tests/api/test_auth.py`, `tests/api/test_fix11_backend_api.py`). | Opportunistic / next API-layer cleanup sprint | Near-drop-in swap: `PyJWT>=2.8,<3` replaces `python-jose[cryptography]`. API differences: `jwt.encode(payload, secret, algorithm="HS256")` returns `str` directly (no `.decode()`); `jwt.decode(...)` raises `jwt.PyJWTError` subclasses instead of `jose.JWTError`. Rename exception import at all 5 sites; update 2 test fixtures. Single-session weekend work. Priority: LOW — CVE already mitigated. |
| DEF-180 | No Python lockfile (`poetry.lock` / `uv.lock` / `pdm.lock` / `requirements-lock.txt`). Reproducibility depends entirely on the version-range solver producing the same tree across installs; combined with the now-bounded runtime deps (FIX-18 P1-I-M01) and the new CI workflow (FIX-18 P1-I-M06 — `.github/workflows/ci.yml`), a lockfile would give CI and operator installs identical resolved trees. Frontend already has `package-lock.json`; Python does not. FIX-18 left this out of scope because the choice of tool (uv vs pip-tools vs poetry) and the CI integration change are a distinct operator workflow decision. | Dedicated single-session sprint (~30-60 min) | Recommended recipe: (1) `pip install uv` then `uv pip compile pyproject.toml -o requirements.lock` and `uv pip compile --extra dev --extra backtest pyproject.toml -o requirements-dev.lock`; (2) commit both alongside `pyproject.toml`; (3) add a regen command to `README.md` or a new `docs/deps.md`; (4) update `.github/workflows/ci.yml` to `pip install -r requirements-dev.lock` before the editable install. Priority: LOW-MEDIUM. |
| DEF-181 | Node 20 deprecation in GitHub Actions. `actions/checkout@v4`, `actions/setup-python@v5`, `actions/setup-node@v4` all run on Node.js 20 which will be forced to Node.js 24 on June 2, 2026 and removed September 16, 2026. First CI runs on 2026-04-22 surfaced the warning. | Before 2026-06-02 | Bump action pins in `.github/workflows/ci.yml` to whatever Node-24-compatible successors each action publishes. LOW priority. |
| DEF-182 | Weekly reconciliation full implementation. `HealthMonitor._run_weekly_reconciliation()` has been a stub since Sprint 5 — it fires a weekly WARNING without comparing `trade_logger` records against broker order history. FIX-05 (audit 2026-04-21, P1-A2-L11) upgraded the placeholder's log level and pointed at this DEF; full implementation requires fetching `broker.get_order_history(days=7)`, pairing with `TradeLogger.get_trades_by_date_range(...)` for the same window, and emitting discrepancy alerts. | Opportunistic / operations sprint | Required: (1) verify `IBKRBroker.get_order_history()` exists (or extend the broker protocol); (2) build a comparison pass that flags broker-side trades missing from the local ledger and vice-versa; (3) alert via `_send_alert(severity="critical")` only on confirmed drift, not transient discrepancies. Priority: LOW — observationally harmless until live trading, but the feature is documented in `architecture.md`. |
| DEF-183 | Full Alpaca incubator retirement — delete `argus/data/alpaca_data_service.py`, `argus/data/alpaca_scanner.py`, `argus/execution/alpaca_broker.py`, their test modules (`tests/data/test_alpaca_data_service.py`, `tests/data/test_alpaca_scanner.py`, `tests/execution/test_alpaca_broker.py` — if present), and simplify `argus/main.py:301-317` / `:339-346` to a single Databento+IBKR live path (no `DataSource.ALPACA` / `BrokerSource.ALPACA` branches). `system.yaml` (`data_source: "alpaca"`, `scanner_type: "alpaca"`) also needs updating to the live defaults or removal. Pairs with DEF-178 (dependency-level `alpaca-py` removal) — both should land in the same session. | Opportunistic / dedicated cleanup sprint | DEC-086 demoted Alpaca to incubator during Sprint 21.6 pivot; no live use case remains. FIX-06 audit 2026-04-21 (P1-C2-10) flagged the reachability via config; retiring safely is outside the data-layer session's scope because it touches `main.py`. LOW priority — no active runtime harm (paths are never selected in production config) but the dead branch is ongoing maintenance drag. |
| DEF-184 | Full `RejectionStage` → `RejectionStage` + `TrackingReason` split. `RejectionStage` in `argus/intelligence/counterfactual.py:41-48` currently mixes true pipeline rejections (`QUALITY_FILTER`, `POSITION_SIZER`, `RISK_MANAGER`) with routing decisions that are not really rejections (`SHADOW`, `BROKER_OVERFLOW`). `FilterAccuracy.by_stage` then reports shadow-mode variants as a "filter accuracy" category, which is conceptually wrong — shadow mode is operator-chosen routing, not a filter. FIX-07 P1-D1-L14 identified the fix but deferred: the split touches the enum, `FilterAccuracy` cut logic, REST serialization at `api/routes/counterfactual.py`, the `counterfactual_positions.rejection_stage` SQLite column, and every `_process_signal` call site that emits `SignalRejectedEvent(stage=SHADOW)`. Cross-references DEF-177 (which wants to *extend* `RejectionStage` with `MARGIN_CIRCUIT` — opposite direction). | Dedicated cross-domain session — coordinate with DEF-177 | Recommended sequence: (1) introduce `TrackingReason` StrEnum (`SHADOW`, `BROKER_OVERFLOW`) in `counterfactual.py`; (2) shrink `RejectionStage` to true rejections (and add `MARGIN_CIRCUIT` per DEF-177 in the same session); (3) add a `tracking_reason: TrackingReason \| None` field to `CounterfactualPosition`; (4) migrate `counterfactual_positions` schema via idempotent `ALTER TABLE ADD COLUMN`; (5) split `FilterAccuracy.by_stage` so shadow counts appear under a separate `by_tracking_reason` cut; (6) update frontend `/counterfactual/accuracy` consumer. Priority: LOW (cosmetic reporting issue, not a correctness bug). |
| DEF-185 | Analytics-layer `assert isinstance` anti-pattern (DEF-106 follow-on). FIX-07 closed DEF-106 by converting 8 assert sites in `argus/intelligence/learning/models.py` + 1 in `argus/api/routes/counterfactual.py` to `if not isinstance: raise TypeError`. Five additional sites sharing the same anti-pattern remain: `argus/analytics/ensemble_evaluation.py` (3 sites) + `argus/intelligence/learning/outcome_collector.py` (2 sites). Python `-O` optimization strips asserts — guards disappear in production. | Opportunistic / next analytics-layer cleanup sprint | Same fix pattern as DEF-106: replace each `assert isinstance(x, T)` with `if not isinstance(x, T): raise TypeError(...)`. Add paired regression test per site. Priority: LOW. |
| DEF-186 | BacktestEngine private-attribute reach-in consolidation. FIX-09 (audit 2026-04-21) partially addressed by adding `EventBusProtocol` in `argus/core/protocols.py` and retyping `BacktestDataService.__init__` against it (the single in-scope call site). Three sibling reach-ins remain and share the same underlying pattern — backtest-side code reaches into private attributes because public accessors don't exist on the consumed modules: (a) **F3 / P1-E1-M03** — `BacktestEngine` accesses `SimulatedBroker._pending_brackets` at 5 call-sites in `argus/backtest/engine.py` (filters by symbol + order_type to implement the bar-level fill model); fix is a public `get_pending_brackets(symbol, order_type=None)` accessor on `SimulatedBroker`. (b) **F4 / P1-E1-M04** — `BacktestEngine._supply_daily_reference_data` accesses `self._strategy._pattern` to call `set_reference_data({"prior_closes": ...})` (mirrors main.py Phase 9.5); fix is a public `PatternBasedStrategy.set_pattern_reference_data(data)` forwarder, updating both live + backtest wiring. (c) **F20 / P1-E1-L05 remainder** — three `# type: ignore[arg-type]` comments remain in `argus/backtest/engine.py` at the `RiskManager` and `OrderManager` constructor sites (both accept `SyncEventBus` where `EventBus` is typed); fix is to retype `RiskManager.__init__` and `OrderManager.__init__` against the new `EventBusProtocol`. | Opportunistic / next execution-layer or backtest cleanup session | Single-session work bundle. Order: (1) add `SimulatedBroker.get_pending_brackets(symbol, order_type=None)` — verify no behavior change via existing bracket tests; (2) add `PatternBasedStrategy.set_pattern_reference_data(data)` forwarder + migrate main.py + engine.py to use it; (3) retype `RiskManager.__init__` / `OrderManager.__init__` against `EventBusProtocol` and drop the remaining 3 `# type: ignore[arg-type]` in engine.py. Priority: LOW — all three items are type-system / code-hygiene improvements with no runtime bug today. |
| DEF-187 | Migrate walk-forward IS path from VectorBT to BacktestEngine — retire `argus/backtest/walk_forward.py` + the 3 remaining `vectorbt_*.py` sweep files (`vectorbt_orb.py`, `vectorbt_orb_scalp.py`, `vectorbt_vwap_reclaim.py`, `vectorbt_afternoon_momentum.py`). FIX-09 P1-E2-M05 identified this as a ~6,713 production LOC + ~4,108 test LOC retirement opportunity gated by DEC-149 supersede. The OOS path already routes through BacktestEngine via `oos_engine="backtest_engine"`; the IS sweep is the remaining VectorBT dependency. Replacement requires: (a) walk-forward windowing on top of `ExperimentRunner.run_sweep(workers=N)` (Sprint 31.5 parallel infra); (b) WFE computation harness reading from `ExperimentStore` / `experiments.db`; (c) migrating the 4 `_optimize_in_sample_*` helpers to `ExperimentRunner` + DuckDB pre-filtering. After retirement, `scripts/revalidate_strategy.py` would run BacktestEngine for both IS and OOS paths. Retirement is gated on Sprint 33+ validation-tooling sprint planning. Cross-references: DEF-178 (`alpaca-py` dependency retirement, paired with `data_fetcher.py`), DEF-183 (Alpaca incubator retirement), DEC-149 VectorBT supersede. | Sprint 33+ validation-tooling sprint | Priority: MEDIUM. Blocked on: (a) walk-forward windowing design for ExperimentRunner; (b) confirmation that ExperimentStore retention covers the historical-IS-sweep use case; (c) migrating `revalidate_strategy.py` fixed-params path. Also cross-references DEF-178 / DEF-183 (Alpaca retirement cluster — all three are "next cleanup-sprint" items). |
| ~~DEF-188~~ | ~~`test_market_calendar::TestGetNextTradingDay::test_defaults_to_today` ET-vs-local-tz mismatch. Implementation uses `datetime.now(tz=_ET).date()`; test compared result against `datetime.date.today()` (local tz). On UTC CI runners during the 20:00–24:00 ET window, the test assertion `result > today` fired with both sides equal.~~ | — | **RESOLVED** (IMPROMPTU-03, 2026-04-22). Test rewritten to compare against ET-derived today. Same root-cause family as DEF-163. |
| DEF-189 | `scripts/revalidate_strategy.py:383` uses VectorBT param names (e.g., `or_minutes`) as dot-path leaves in `config_overrides`, but `OrbBreakoutConfig` has `orb_window_minutes` etc. Under the pre-FIX-09 flat-key fallback, these typos silently mapped to the outer dict; under FIX-09's option (b) strict-dot-path behavior, they silently no-op. Either way, the `revalidate_strategy.py` fixed-params flow has been running with default strategy params rather than intended overrides for an unknown period. Affects BacktestEngine path only (walk-forward path via `_WALK_FORWARD_SUPPORTED` uses a different override mechanism). | post-31.9 | MEDIUM priority. Dedicated standalone micro-fix: grep every `config_overrides` call site in `revalidate_strategy.py`, verify each param name matches its target config field, either correct the param names or switch to flat keys. Add a regression test: config_override dict with known bad key should raise or log WARNING. Cross-reference F1 finding in FIX-09 audit doc. |
| ~~DEF-190~~ | ~~pyarrow/xdist concurrent `register_extension_type` race~~ | — | **RESOLVED** (FIX-13a, 2026-04-23): top-level `tests/conftest.py` now calls `_prewarm_pyarrow_pandas_extensions()` at module-import time. The helper constructs a 1-row pandas.DataFrame with a `Period` dtype and converts to `pyarrow.Table.from_pandas()` — forcing `register_extension_type('pandas.period')` to run once per xdist worker before any test module executes. Eliminates the first-run race. Regression guard at `tests/test_def190_pyarrow_eager_import.py`. |
| DEF-191 | Latent `TradeLogger.get_todays_pnl()` SQL-side UTC normalization — SQLite's `date()` function on stored ISO timestamps with tz offset normalizes to UTC before extracting the date. For real production trades (market-hours exits, 9:30–16:00 ET), the UTC date equals the ET date, so the query works correctly. If ARGUS ever supports after-hours trading (pre-market ≥ 4:00 ET or after-hours ≤ 20:00 ET), trades exiting in the 20:00–24:00 ET window would be miscounted. | post-31.9 | Fix options: (a) change stored `exit_time` to naive-ET ISO; (b) add a denormalized `trading_date` column populated at insert time; (c) accept the limitation and document the window. Priority: LOW (pre-empts a future-feature bug, not a current one). |
| DEF-192 | Consolidated test runtime warning cleanup debt. Baseline was 39 warnings across ~6 categories. | FIX-13a (partial); remainder opportunistic | **PARTIAL** (FIX-13a, 2026-04-23): closed numpy invalid-cast at `argus/backtest/vectorbt_afternoon_momentum.py:1065/1103/1141` — wrapped `pivot*_trades.values` in `np.nan_to_num(..., nan=0)` before `.astype(int)`. Post-FIX-13a full-suite count fluctuates 26–40 across runs because several categories are async-mock coroutine-never-awaited warnings whose emission is order-dependent under xdist (first-run vs second-run differences). The ≤5 target is NOT met — kickoff Hazard 4 acknowledged this as acceptable partial. Remaining categories: (i) aiosqlite "Event loop is closed" (~3 sites); (ii) AsyncMock coroutine-never-awaited (~8 sites, intermittent); (iii) `websockets.legacy` deprecation (transitive dep); (iv) `OrderManager(auto_cleanup_orphans=...)` deprecation (3 test sites — intentionally preserved until DEF-176 migrates them to `reconciliation_config=`); (v) pytest collection warning on `scripts/sprint_runner/state.py::TestBaseline` — file lives in the `workflow/` submodule (Universal RULE-018 prohibits in-project edits); defer to upstream metarepo change. Priority: LOW. |
| DEF-193 | Observatory WebSocket push-only loop doesn't detect client disconnect on Linux. `argus/api/websocket/observatory_ws.py` pushes via `send_json()` in a `while True: await asyncio.sleep(interval)` loop, never calling `receive()`. On macOS the next `send_json()` after disconnect raises `WebSocketDisconnect`; on Linux `send_json()` does not reliably raise and the server task loops forever on a dead socket. Surfaced by FIX-13c CI diagnostic session as a latent xdist-timing-sensitive hang in `test_observatory_ws.py`; tests worked around via `pytest.mark.timeout(30)` + `ws_update_interval_ms=200`, but the production bug remains. | Opportunistic / next API-layer session | Proposed fix: wrap push loop in `asyncio.wait_for(websocket.receive(), timeout=interval)` alongside `send_json()` so a closed connection surfaces promptly, OR periodically poll `websocket.client_state` to detect `DISCONNECTED` state. Single-file fix, ~20 lines. Pattern extends to `arena_ws.py` if same idiom is used there. Priority: MEDIUM — doesn't affect correctness of live data delivery (clients reconnect via UI), but causes zombie server tasks that accumulate over a long-running session. |
| DEF-194 | IBKR `ib_async` stale position cache after reconnect. On April 22 the 9:29 AM ET Databento + IBKR disconnect/reconnect cycle (IBKR Error 1100 → Error 1102) left `ib_async`'s auto-synced `positions()` cache inconsistent with actual IBKR state. Specifically, PURR showed a 1.00× flatten ratio (vs 2.00× for 50 other symbols) consistent with the cache returning +323 shares for a position that was actually 0, so ARGUS's SELL 323 flipped 0 → −323 rather than doubling an existing short. This is distinct from DEF-194's doubling mechanism (DEF-194 → DEF-199 cluster) but compounds it. Surfaced in April 22 market session debrief (`docs/sprints/sprint-31.9/debrief-2026-04-22-triage.md` §C2). | Opportunistic / paired with DEF-195 reconnect-recovery session | Proposed fix options: (1) call `await self._ib.reqPositionsAsync()` explicitly before each EOD Pass 2 query to force fresh sync; (2) add a `positions_last_updated` timestamp check and force refresh if older than N seconds; (3) pair with DEF-195 fix — combined, the two provide defense-in-depth. Priority: MEDIUM. Paper trading only affects data integrity; live trading this path would compound DEF-199's short-doubling if both fire together. |
| DEF-195 | `max_concurrent_positions` count diverges from broker state after disconnect-recovery missed fill callbacks. On April 22 ARGUS's internal `_managed_positions` dict capped at 50 (correctly rejecting 8,996 signals with "max concurrent positions reached"), but IBKR position count climbed to 134 at 10:34 AM ET and 51 positions remained open at EOD flatten — positions that ARGUS never added to `_managed_positions` because their entry-fill callbacks were lost in the 9:29 AM disconnect. The `max_concurrent_positions` check uses only the internal dict count; it has no awareness of broker-side positions that escaped reconciliation. Also linked to BITO single-stock concentration reaching ~8% (5,823 shares × ~$10.85 ≈ $63K on $794K account, exceeding the documented 5% single-stock limit) because the concentration check was bypassed for untracked positions. Surfaced in April 22 market session debrief §C3. | Post-31.9 dedicated cross-domain session, coordinate with DEF-194/DEF-196 | HIGH priority for live trading (phantom long positions accumulate silently, concentration limits silently bypassed); MEDIUM for paper. Proposed fix: periodic reconciliation comparing `_managed_positions.count` vs `broker.get_positions().count` — if diverges by >10% (or any threshold), trigger WARNING and block new entries until resynced. Concentration check should also be updated to count broker-visible positions, not just internally-tracked ones. Natural fit with DEF-199 fix session (both touch the reconciliation flow around `_flatten_unknown_position`). |
| DEF-196 | 32 DEC-372 stop-retry-exhaustion cascade events between 9:40–9:59 AM ET on April 22, immediately after the 9:29 AM IBKR reconnect. All 32 events fired the pattern "Stop retry failed for X. Emergency flattening" (RCUS, AIQ, AMDL, CRCG, CRSR, EDV, ETHE, EWT, EYPT, FBTC, FCEL, FETH, FLYW, FRMI, GBCI, ICLN, LAR, MSTZ, NKLR, OBE, POET, RDW, RKLZ, SBSW ×2, SONY, SOXS ×2, TGTX, VALE, VCLT, JMIA). Root cause: after IBKR reconnect, in-flight order IDs on IBKR's side are invalidated; ARGUS's `stop_cancel_retry_max` (default 3) retries cancels against stale IDs until exhausted, then fires an emergency MARKET SELL. However, the original bracket stop may still be live on IBKR's side — it just can't be canceled because the ID is stale. When price later hits the stop level, IBKR fills it, flipping the position short. 5 of the 32 symbols (EDV, FCEL, RCUS, RKLZ, SOXS) also appear in the 51 EOD-remaining list from DEF-199, linking the stop-retry-exhaustion path to the EOD short-flip cascade. Surfaced in April 22 market session debrief §C4. *Cross-references DEF-177 (RejectionStage.MARGIN_CIRCUIT) and DEF-184 (RejectionStage/TrackingReason split) — all three are execution/intelligence-layer reconnect-recovery work that should coordinate in one session.* | Post-31.9 dedicated cross-domain session ("Reconnect-Recovery + RejectionStage" sprint) | MEDIUM priority. Proposed fix options: (1) on IBKR reconnect, call `reqOpenOrders()` and rebuild `_stop_retry_count` + `_amended_prices` with the fresh order IDs; (2) reset `stop_cancel_retry_max` counter and add a longer delay before first retry post-reconnect; (3) before firing emergency MARKET flatten, query current broker position qty and skip if 0. The three approaches compose — (1) recovers cleanly; (2) buys time for (1) to execute; (3) is a final safety net. Cluster with DEF-177 + DEF-184 + DEF-194 + DEF-195 in one reconnect-recovery session (estimated 2-3 sessions). |
| DEF-197 | `data/evaluation.db` is 4.78 GB at boot (April 22 startup log: `EvaluationEventStore initialized: data/evaluation.db (size=4776.3 MB, freelist=0.0%)`). Sprint 31.8 S2 landed a VACUUM-on-retention fix (`close→asyncio.to_thread(VACUUM)→reopen` pattern) but retention DELETE may not be executing. Freelist=0.0% rules out the "VACUUM failing to reclaim" theory — the data is live, not deleted-but-not-reclaimed. Most likely retention is not deleting at all. Diagnostic SQL: `SELECT MIN(trading_date), MAX(trading_date), COUNT(*) FROM evaluation_events;` — if rows span >7 days, retention is broken. Surfaced in April 22 market session debrief §C5. | Opportunistic / next data-layer touch | Proposed investigation: run the diagnostic SQL first to confirm the hypothesis (retention not deleting vs. VACUUM not reclaiming vs. pre-fix accumulated data never retroactively vacuumed); if retention is broken, look at `EvaluationEventStore._enforce_retention()` and check whether it's scheduled/triggered at all, and whether the date-column comparison uses the right timezone. If pre-fix data accumulated and was never retroactively vacuumed, a one-shot `VACUUM INTO 'evaluation.db.new' WHERE trading_date >= date('now', '-7 days')` + swap would reclaim it. Priority: MEDIUM. Performance impact is startup-time-only (SQLite open on a 4.78GB file is slower than a small file); trading operation unaffected. |
| DEF-198 | Boot phase labels in `argus/main.py` show `[N/12]` (e.g., `[9/12] Initializing orchestrator...`, `[10.3/12] Initializing telemetry store...`) but FIX-03 close-out / handoff documentation describe a "17-phase boot sequence delivered by FIX-03." Additionally, FIX-03 handoff claimed `EvaluationEventStore` init moved to Phase 9 (before orchestrator), but April 22 boot log shows `[9/12] Initializing orchestrator...` THEN `[10.3/12] Initializing telemetry store... EvaluationEventStore initialized` — the phase ordering contradicts the handoff. Surfaced in April 22 market session debrief §B4 + §C6. | Opportunistic / next main.py touch | Proposed resolution: reconcile `argus/main.py` phase logging with the FIX-03 close-out claim. Two paths: (a) if the 17-phase count was an aspirational/renumbering target FIX-03 intended but didn't complete, update all phase-label strings to reflect actual N and re-verify ordering against the handoff; (b) if the 17-phase claim was handoff inaccuracy, correct the handoff + project-knowledge docs + any dependent debrief templates. Priority: LOW (documentation accuracy, not runtime correctness). Defer until main.py is touched for another reason. |
| ~~DEF-199~~ | ~~`_flatten_unknown_position()` systematically doubles short positions at EOD~~ | — | **RESOLVED** (IMPROMPTU-04, 2026-04-23, commit `0623801`): three-part fix — (1) EOD Pass 2 at `order_manager.py:1707` now branches on `pos.side`: `OrderSide.BUY` → SELL-flatten as before, `OrderSide.SELL` → ERROR log + skip (ARGUS is long-only; cover manually via `scripts/ibkr_close_all_positions.py`), unknown side → ERROR + skip; (2) EOD Pass 1 retry at `:1684` applies the same three-branch logic using a new `broker_side_map` built alongside `broker_qty_map`; (3) new `check_startup_position_invariant()` helper in `argus/main.py` + `ArgusSystem._startup_flatten_disabled` flag — audits `broker.get_positions()` immediately after `broker.connect()`, sets the flag on any non-BUY side (fails closed on exception), gates the `order_manager.reconstruct_from_broker()` call. Regression guards: `tests/execution/order_manager/test_def199_eod_short_flip.py` (6 revert-proof tests covering both filter sites) + `tests/test_startup_position_invariant.py` (5 pure-function tests) + 2 C1 log-level tests in `tests/strategies/patterns/test_pattern_strategy.py`. `ibkr_broker.py:925-950` (`abs(int(pos.position))`), `models/trading.py:164` (`Field(ge=1)`), and `_flatten_unknown_position` implementation all unchanged — the side-check is in the filter, not the flatten implementation. Pre-existing Sprint 32.9 / 29.5 EOD tests updated to set `side=OrderSide.BUY` on their MagicMock broker positions (the `side` attribute was previously absent). Cross-references DEF-194 (stale cache) + DEF-195 (broker-state divergence) + DEF-196 (stop-retry cascade) — those remain open as DEF-199's causal upstream and are scoped to a separate reconnect-recovery session. |

## Reference

| Document | What It Covers |
|----------|---------------|
| `docs/decision-log.md` | All DEC entries with full rationale. Latest: DEC-384 (FIX-01, standalone system overlay registry). |
| `docs/dec-index.md` | Quick-reference index with status markers |
| `docs/sprint-history.md` | Complete sprint history + per-sprint follow-on detail |
| `docs/pre-live-transition-checklist.md` | Config + test values to restore before live trading |
| `docs/process-evolution.md` | Workflow evolution narrative |
| `docs/live-operations.md` | Live trading procedures |
| `docs/strategies/STRATEGY_*.md` | Per-strategy spec sheets |
| `docs/risk-register.md` | Active risks and assumptions |
| `docs/project-bible.md` | System vision and invariants |
| `docs/architecture.md` | Technical blueprint |
| `docs/roadmap.md` | Strategic vision + sprint queue (DEC-262) |
| `docs/sprint-campaign.md` | Operational sprint choreography |
| `docs/ui/ux-feature-backlog.md` | Planned UI/UX enhancements |
| `.claude/rules/` | Backtesting, trading-strategies, universal rules |
| `.claude/skills/doc-sync.md` | Documentation sync protocol |
