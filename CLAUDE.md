# ARGUS — Claude Code Context

> Dense, actionable context for Claude Code sessions. No history — see `docs/` for that.
> Last updated: March 21, 2026 (Phase 5 Gate doc sync)

## Active Sprint

**No active sprint.** Sprint 25.8 (API Auth + Close-Position Fix) completed March 21, 2026.

Next planned sprint: **26 (Red-to-Green + Pattern Library Foundation)**. Red-to-Green strategy + PatternLibrary ABC + Bull Flag + Flat-Top Breakout pattern modules. Phase 5 Gate completed March 21 — build track resequenced per DEC-354: Sprint 27 is now BacktestEngine Core (not Pattern Expansion), followed by Sprint 21.6 (Re-Validation) and Sprint 28 (Learning Loop V1).

### Known Issues
- **FMP Starter plan restriction:** FMP news endpoints return 403 on Starter plan ($22/mo). `fmp_news.enabled: false` in `system_live.yaml`. FMP circuit breaker (DEC-323) prevents spam if accidentally enabled.
- **Pre-existing xdist failures (DEF-048):** 4 test_main.py tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race): `test_both_strategies_created`, `test_multi_strategy_health_status`, `test_candle_event_routing_subscribed`, `test_12_phase_startup_creates_orchestrator`. Pre-existing on clean HEAD. Priority: LOW.
- **Test isolation (DEF-049):** `test_orchestrator_uses_strategies_from_registry` fails when run in isolation but passes in full suite. Pre-existing.

## Current State

- **Active sprint:** None (between sprints)
- **Next sprint:** 26 (Red-to-Green + Pattern Library Foundation)
- **Tests:** 2,815 pytest + 611 Vitest (0 failures, 0 hangs)
- **Strategies:** 4 active (ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum)
- **Infrastructure:** Databento EQUS.MINI (live) + IBKR paper trading (Account U24619949) + FMP Starter (scanning + reference data + daily bars for regime) + Finnhub (news + analyst recs) + Claude API (Copilot + Catalyst Classification) + Universe Manager (config-gated) + Catalyst Pipeline (config-gated) + Intelligence Polling Loop (config-gated) + Reference Data Cache + Quality Engine (config-gated) + Dynamic Position Sizer + Strategy Evaluation Telemetry (ring buffer + SQLite persistence) + Debrief Export (shutdown automation)
- **Frontend:** 8-page Command Center (Observatory added Sprint 25) + AI Copilot + Universe Status Card + Intelligence Brief View (all active), Tauri desktop + PWA mobile

## Project Structure

```
argus/
├── core/           # Orchestrator, Risk Manager, Portfolio, Event Bus
├── strategies/     # BaseStrategy, OrbBaseStrategy, 4 strategy implementations
├── data/           # DataService (Databento/Alpaca/Replay/Backtest), Scanner, IndicatorEngine, UniverseManager, FMPReferenceClient
├── execution/      # Broker (IBKR/Alpaca/Simulated), Order Manager
├── analytics/      # Trade Logger, PerformanceCalculator, DebriefExport
├── backtest/       # VectorBT helpers, Replay Harness
├── api/            # FastAPI REST + WebSocket, JWT auth
│   └── websocket/  # ai_chat.py (WS streaming)
├── ui/             # React frontend (Vite + TypeScript + Tailwind v4)
│   └── features/copilot/  # CopilotPanel, ChatMessage, ActionCard
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
├── config/         # system.yaml, system_live.yaml, strategies/*.yaml
├── tests/          # pytest (backend) + Vitest (frontend)
├── docs/           # Decision log, sprint history, strategy specs, research reports
├── workflow/       # Metarepo submodule (protocols, templates, runner, universal rules)
└── .claude/        # rules/ (project-specific + universal→workflow), skills/→workflow, agents/→workflow
    └── rules/      # backtesting.md, trading-strategies.md, universal.md
```

## Commands

```bash
# Tests
python -m pytest --ignore=tests/test_main.py -n auto -q  # Full suite (~39s with xdist)
python -m pytest tests/ -x               # Stop on first failure
python -m pytest tests/ -x -q            # Fail-fast, quiet
cd argus/ui && npx vitest run            # Frontend tests (~611)

# Trading engine
python -m argus.main                      # Start (paper trading default)
python -m argus.main --dry-run           # Connect and validate without trading
python -m argus.main --dev               # Dev mode (mock data, no external connections)
python -m argus.main --config system.yaml # Alpaca incubator mode (legacy)
python -m argus.main --config config/system_live.yaml  # Live mode (Databento + IBKR)

# Backtesting
python -m argus.backtest.data_fetcher --symbols TSLA,NVDA --start 2025-03-01 --end 2026-02-01
python -m argus.backtest.replay_harness --data-dir data/historical/1m --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA,NVDA --start 2025-06-01 --end 2025-12-31
python -m argus.backtest.report_generator --db data/backtest_runs/run_xxx.db --output reports/orb_validation.html

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
python scripts/test_time_stop_eod.py     # Time stop + EOD flatten (IBKR or mock)

# AI Layer
ANTHROPIC_API_KEY="sk-..." python -m argus.api --dev  # Run with AI enabled
python -m pytest tests/ai/ -x -q                       # AI module tests only

# Autonomous Sprint Runner (Sprint 23.2)
python scripts/sprint-runner.py --help                # Show all CLI options
python scripts/sprint-runner.py run path/to/sprint-package.yaml  # Execute sprint
python scripts/sprint-runner.py resume --run-dir path/to/run  # Resume from checkpoint
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
- Walk-forward validation: WFE > 0.3 required (DEC-047)
- Pre-Databento backtests are PROVISIONAL (DEC-132)
- See `.claude/rules/backtesting.md` for detailed sweep rules

### API
- FastAPI in-process (Phase 12 startup) (DEC-099)
- Single-user JWT with bcrypt (DEC-102)
- WebSocket: curated event list, tick throttling (DEC-101)
- AppState dataclass → FastAPI Depends() injection (DEC-100)

## UI/UX Rules

- **Design principles (DEC-109):** Information over decoration. Ambient awareness. Progressive disclosure. Motion with purpose. Mobile as primary trading surface. Research lab aesthetics.
- **Animation library (DEC-110):** Framer Motion for page transitions + stagger. CSS transitions for hover/micro-interactions. Lightweight Charts native for chart animations. Budget: <500ms, 60fps, never blocks interaction.
- **Chart library stack (DEC-104, DEC-108):** Lightweight Charts (time-series) + Recharts (standard charts) + D3 (custom viz, sparingly) + Three.js r128 (Observatory Funnel/Radar 3D views, code-split via React.lazy).
- **UX Feature Backlog:** `docs/ui/ux-feature-backlog.md` — canonical inventory of all planned UI/UX enhancements. Reference when planning sprint UX scope. (DEC-106)
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

## Documentation Sync

Doc updates are handled by the doc-sync skill. See `.claude/skills/doc-sync.md` for the protocol.

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
| DEF-011 | IQFeedDataService adapter | Forex strategy development starts OR breadth indicator integration starts | IQFeed provides forex and breadth indicators (advance/decline, TICK, TRIN) that neither Databento nor FMP provide. Benzinga news originally a draw but FMP covers news needs more cost-effectively (DEC-258/260). Build when a specific feature requires forex or breadth data. ~$160–250/month. |
| DEF-012 | Databento L2 depth activation | A strategy requires order book depth data for entry/exit decisions | MBP-10 schema available on Standard plan. DatabentoDataService designed for L2 from Sprint 12, but not activated until a strategy needs it. |
| ~~DEF-013~~ | ~~Extract shared IndicatorEngine from DataService implementations~~ | ~~Sprint 12.5~~ | **DONE** — `IndicatorEngine` class created in `argus/data/indicator_engine.py`. All four DataService implementations (AlpacaDataService, DatabentoDataService, ReplayDataService, BacktestDataService) now delegate to IndicatorEngine. 27 new tests, 685 total tests passing. DEC-092. |
| DEF-014 | SystemAlertEvent for dead data feed | Command Center MVP (Sprint 14–16) OR Health Monitor alerting built | `DatabentoDataService._run_with_reconnection()` logs `critical` when max retries exceeded but emits no Event Bus event. Add `SystemAlertEvent` (or similar) so Health Monitor and Command Center can react (red banner, push notification). Location: `argus/data/databento_data_service.py`. |
| ~~DEF-015~~ | ~~DatabentoScanner full-universe scanning~~ | — | **SUPERSEDED by DEC-263:** Full-universe strategy-specific monitoring architecture adopted. Sprint 23 implements Universe Manager with broad Databento subscription (3,000–5,000 symbols), full IndicatorEngine on all symbols, strategy-declared universe filters. |
| ~~DEF-016~~ | ~~Order Manager `place_bracket_order()` integration~~ | ~~Sprint 17~~ | **DONE** (Sprint 17, DEC-117). Order Manager uses `place_bracket_order()` for atomic entry+stop+T1+T2. ManagedPosition tracks bracket component IDs. SimulatedBroker + IBKRBroker validated. Known limitation: AlpacaBroker bracket child order fills don't route correctly — acceptable, Alpaca is incubator-only (DEC-086). |
| DEF-017 | Performance-weighted + correlation-adjusted allocation | 20+ days of multi-strategy live data available | V1 uses equal-weight. V2 shifts ±10% based on trailing Sharpe/drawdown. V3 adds CorrelationTracker cross-correlation penalty. CorrelationTracker infrastructure built in Sprint 17 (DEC-116). |
| DEF-018 | Real VIX data integration | IQFeed subscription activated OR CBOE Databento dataset added | RegimeClassifier V1 uses SPY 20-day realized vol as VIX proxy (DEC-113). Replace with real-time VIX index when data source available. |
| DEF-019 | Breadth indicator integration (advance/decline, TICK, TRIN) | IQFeed subscription activated | RegimeClassifier designed for breadth inputs but V1 uses SPY-only signals. IQFeed provides NYSE breadth data. ~$160–250/month. |
| DEF-020 | Cross-strategy sector exposure check (max_single_sector_pct) | IQFeed subscription activated OR fundamentals data source integrated | Risk Manager cross-strategy checks skip sector exposure in V1 — no sector classification data available (DEC-126). Requires SIC/GICS mapping per symbol. Single-stock cap (5%) provides concentration protection meanwhile. |
| DEF-021 | Sub-bar backtesting precision for ORB Scalp | Databento tick-level data available for backtesting OR Scalp paper trading results diverge significantly from backtests | Synthetic ticks give ~15s granularity per 1m bar (DEC-053). Scalp targets 30–120s holds — time stops shorter than 60s resolve at nearest bar boundary. Backtesting results are directional guidance, not exact P&L. |
| DEF-022 | VwapBaseStrategy ABC extraction | Second VWAP-based strategy designed (e.g., VWAP Fade) | No shared logic exists yet — VwapReclaimStrategy inherits directly from BaseStrategy (DEC-136). If a second VWAP variant is built, extract shared VWAP crossover tracking into a VwapBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-023~~ | ~~Watchlist Endpoint Production Implementation~~ | — | **PARTIALLY RESOLVED** (Sprint 21.7): Watchlist endpoint now reads from `cached_watchlist` (scan_source, selection_reason populated). Remaining: current_price, sparkline, strategy state aggregation. |
| DEF-024 | Trailing Stop Mechanism | Walk-forward shows afternoon moves routinely exceed T2 targets | Order Manager trailing stop logic, Risk Manager awareness, VectorBT sweep support, backtesting infrastructure. Touches cross-cutting concerns across execution, risk, and backtesting layers. T1/T2 fixed targets proven across four strategies — trailing stop adds complexity only if data shows clear benefit. DEC-158. |
| DEF-025 | Shared Consolidation Base Class | Second consolidation-based strategy designed (e.g., Midday Range Breakout) | AfternoonMomentumStrategy inherits directly from BaseStrategy (DEC-152). If a second consolidation variant is built, extract shared midday range tracking into a ConsolidationBaseStrategy ABC. Follows the OrbBaseStrategy extraction pattern (DEC-120). |
| ~~DEF-026~~ | ~~FTS5 full-text search~~ | — | **RESOLVED** (DEC-200): LIKE queries shipped as V1 solution. FTS5 deferred to >10K entries. |
| ~~DEF-027~~ | ~~Journal trade linking UI~~ | — | **RESOLVED** (DEC-201): Full search UI with TradeSearchInput shipped in Sprint 21c. |
| DEF-028 | CalendarPnlView strategy filter | Performance Workbench implementation (DEC-229) OR user requests during paper trading | CalendarPnlView renders all-strategy aggregated P&L. Strategy-specific calendar filtering deferred because calendar needs a different data query path than other charts (daily aggregation by strategy). Low priority — user can already filter by strategy in Overview and Heatmaps tabs. |
| DEF-029 | Persist Live Candle Data to Database for Post-Session Replay | Live candle data flows through the Event Bus but isn't persisted to the database. The Performance page Replay tab shows "Bar data not available for this trade" because there are no stored bars around the trade's timestamps. Need a new `candle_bars` table (symbol, timestamp, open, high, low, close, volume) with writes from the DataService callback. ~3,900 rows/day (10 symbols × 390 bars). Required for post-session review, The Debrief page EOD analysis, and replay visualizations. |
| DEF-030 | Live candlestick chart real-time updates | Sprint 22+ or UX backlog prioritization | TradeChart loads historical only, no WebSocket subscription. |
| DEF-031 | Orders table persistence | When post-hoc order forensics needed beyond log analysis | Orders not persisted to DB, only completed trades. |
| DEF-032 | FMPScannerSource criteria_list filtering | Sprint 23.5 (NLP Catalyst) or Sprint 24 (Quality Engine) | `scan()` accepts `criteria_list` parameter but ignores it (documented in docstring). FMP endpoints are pre-filtered server-side; post-fetch filtering by strategy-specific criteria becomes meaningful when Quality Engine provides scoring criteria. |
| DEF-033 | Approve→Executed status transition is simulated with setTimeout(1500ms) in ChatMessage.tsx. Real execution status should be pushed via WebSocket (`{"type": "proposal_update", ...}`) after ActionExecutor completes. Requires: WS protocol extension (new message type), executor pipeline event emission, frontend WS handler update. Cosmetic-only impact — proposal is correctly marked `approved` in DB; only the UI status badge is faked. | Next UI polish pass or Sprint 23 if room. |
| DEF-034 | Pydantic serialization warnings on `review_verdict` field | Next sprint runner polish pass | `SessionResult.review_verdict` accepts string where enum is expected, producing `PydanticSerializationUnexpectedValue` warnings during test runs. Cosmetic — does not affect functionality. Recurring across Sprint 23.2 S3–S6 tests. Fix: either use `ReviewVerdict` enum values directly or add `use_enum_values=True` to model config. |
| DEF-035 | FMP Premium Upgrade ($59/mo) | When batch-quote speed becomes a bottleneck | FMP Premium enables batch-quote endpoints (27 min → ~2 min load). Sprint 23.5 completed without upgrade — Finnhub free tier covers news needs. Priority: LOW. |
| ~~DEF-036~~ | ~~Stock-List Response Caching~~ | — | **RESOLVED** (Sprint 23.6): Reference data file cache with JSON persistence, per-symbol staleness, and incremental warm-up implemented (DEC-314). Reduces ~27 min to ~2–5 min. |
| DEF-037 | FMP API Key Redaction in Error Logs | Next cleanup sprint | FMP API URLs with API key appear in error logs. Should redact `apikey=XXX` before logging. Priority: MEDIUM. |
| DEF-038 | Fuzzy/Embedding-Based Catalyst Dedup | Sprint 28+ or when duplicate catalyst volume is high | Current semantic dedup uses (symbol, category, time_window) grouping (DEC-311). Embedding-based similarity matching would catch semantic duplicates with different headlines. Requires embedding model integration. Priority: LOW — rule-based dedup handles the common case. |
| DEF-039 | Runner Conformance Check Reliability Audit | When conformance_fallback_count consistently >2 per sprint run | Sprint 23.6 added conformance fallback tracking. If fallback counter shows frequent failures, investigate structured output parsing reliability and tighten the conformance check. Priority: LOW — monitoring only. |
| DEF-040 | Runner main.py Further Decomposition | Runner exceeds ~2,500 lines | Sprint 23.6 S5 extracted CLI helpers (~120 lines). main.py still 2,067 lines. Further extraction candidates: session execution loop, parallel session handling, notification logic. Priority: LOW. |
| ~~DEF-041~~ | ~~Frontend catalyst endpoint short-circuit~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9, DEC-329). `usePipelineStatus` hook gates catalyst/briefing TanStack queries on health endpoint pipeline component. Zero requests when pipeline inactive. |
| ~~DEF-043~~ | ~~/debrief/briefings endpoint 503 fix~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Root cause: `DebriefService` only initialized in `dev_state.py`, never in `server.py` lifespan. Fix: ~10 lines wiring `DebriefService(db)` in lifespan. Frontend empty state already existed. |
| ~~DEF-044~~ | ~~SPY intra-day regime re-evaluation~~ | — | **PARTIALLY RESOLVED** (Sprint 25.6, DEC-346): Periodic 300s regime reclassification task added. Regime now reclassified during market hours. Remaining: regime-aware strategy behavior (how should mid-session regime changes affect running strategies). |
| ~~DEF-045~~ | ~~SEC Edgar timeout test rewrite~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Rewrote to call `client.start()` with mocked CIK refresh, inspects `client._session.timeout`. Matches Finnhub/FMP pattern. |
| ~~DEF-046~~ | ~~test_main.py xdist failures (2 named tests)~~ | ~~Sprint 23.9~~ | **CLOSED** (Sprint 23.9). Root cause: `load_dotenv()` in `ArgusSystem.__init__()` re-loaded `.env` after monkeypatch, `AIConfig.auto_detect_enabled` overrode `enabled=False`. Fix: empty `ANTHROPIC_API_KEY` env var + explicit `ai: enabled: false`. 4 additional failures tracked as DEF-048. |
| DEF-047 | Bulk catalyst endpoint | Unscheduled | Consolidate per-symbol catalyst GET requests into single batch request. Currently one request per watchlist symbol when pipeline is active. Priority: LOW. |
| DEF-048 | Additional test_main.py xdist failures | Unscheduled | 4 more tests fail under `-n auto` (same `load_dotenv`/`AIConfig` race as DEF-046): `test_both_strategies_created`, `test_multi_strategy_health_status`, `test_candle_event_routing_subscribed`, `test_12_phase_startup_creates_orchestrator`. Pre-existing on clean HEAD. Same fix approach as DEF-046. Priority: LOW. |
| DEF-049 | test_orchestrator_uses_strategies_from_registry isolation failure | Unscheduled | `test_orchestrator_uses_strategies_from_registry` in tests/test_main.py fails when run in isolation but passes in full suite. Pre-existing test isolation issue. Discovered Sprint 24 S1. Priority: LOW. |
| DEF-074 | Dual regime recheck path consolidation | Natural lull / future cleanup | Orchestrator's `_poll_loop` and main.py's `_run_regime_reclassification` both call `reclassify_regime()`. Benign (idempotent) but redundant. Consolidate to single periodic mechanism. Priority: LOW. |
| ~~DEF-050~~ | ~~Full ArgusSystem e2e integration test~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S2): Full strategy → quality engine → sizer → RM integration test implemented. |
| ~~DEF-052~~ | ~~Dashboard quality cards interactivity~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b + S4f): Tooltips, legend, and chart redesign completed. QualityDistributionCard donut removed (redundant with SignalQualityPanel histogram). |
| ~~DEF-053~~ | ~~Quality column in Dashboard tables~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b): Quality column added to Dashboard Positions/Recent Trades tables. |
| ~~DEF-054~~ | ~~Orchestrator clickable signal rows~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4b): Clickable signal rows with SignalDetailPanel implemented. |
| ~~DEF-055~~ | ~~Orchestrator 3-column layout~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4a): Decision Log + Catalyst Alerts + Recent Signals combined into 3-column row. |
| ~~DEF-056~~ | ~~QualityOutcomeScatter page placement~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S4a): Relocated from Debrief Quality tab to Performance Distribution tab. |
| ~~DEF-057~~ | ~~SEC EDGAR EFTS URL live validation~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S2): URL works with User-Agent header. No code change needed. |
| ~~DEF-058~~ | ~~Trades DB quality columns~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1a): Quality grade/score wired through Order Manager → TradeLogger → DB schema. |
| ~~DEF-059~~ | ~~Pre-existing TypeScript build errors (22)~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S3): All 22 TS build errors fixed. TS errors: 22 → 0. |
| ~~DEF-060~~ | ~~PROVISIONAL comment gap in system YAML quality sections~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): PROVISIONAL comments added to system.yaml/system_live.yaml quality sections. |
| ~~DEF-061~~ | ~~Quality API private attribute access~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): `@property` accessors added for `_db`/`_config` on SetupQualityEngine. |
| ~~DEF-062~~ | ~~QA seed script cleanup~~ | ~~Unscheduled~~ | **RESOLVED** (Sprint 24.1 S1b): Production guard added to `scripts/seed_quality_data.py`. |
| ~~DEF-075~~ | ~~`fetch_daily_bars()` via FMP for regime classification~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Implemented via FMP stable historical-price-eod endpoint. |
| ~~DEF-076~~ | ~~Health endpoint `last_data_received` always null~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): `last_update` attribute added to DatabentoDataService, set in `_dispatch_record()`. |
| ~~DEF-077~~ | ~~Diagnostic logging when position sizer returns 0 shares~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Log now includes grade, score, allocated_capital, buying_power, entry, stop, risk_per_share. |
| ~~DEF-078~~ | ~~Rate-limit regime reclassification warnings~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Counter-based rate limiting — logs on 1st occurrence and every 6th. Resets on success. |
| ~~DEF-079~~ | ~~Automated debrief data export at shutdown~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): `debrief_export.py` produces `logs/debrief_YYYYMMDD.json` during shutdown. |
| ~~DEF-080~~ | ~~VWAP Reclaim false suspension on zero trade history~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Early return `ThrottleAction.NONE` when both trades and daily_pnl are empty. |
| ~~DEF-081~~ | ~~Entry evaluation conditions_passed/conditions_total metadata~~ | ~~Sprint 25.7~~ | **RESOLVED** (Sprint 25.7 S1): Added to all ENTRY_EVALUATION calls in `_check_breakout_conditions()`. |
| DEF-082 | Quality engine catalyst_quality and volume_profile always 50.0 (neutral default) | Unscheduled | Expected when no real-time RVOL or symbol-specific catalysts. Will become useful as data sources are enriched. Priority: LOW. |
| ~~DEF-083~~ | ~~API auth 403→401~~ | ~~Sprint 25.8~~ | **RESOLVED** (Sprint 25.8, DEC-351): `HTTPBearer(auto_error=False)` + explicit 401. 35 tests fixed. |
| DEF-084 | Full test suite runtime optimization | Partially resolved | FMP rate limit configurable (454s→39s with xdist). Remaining slow tests: `test_stale_data_detection/recovery` (10s each). `slow` marker registered in pyproject.toml. Priority: LOW. |
| ~~DEF-085~~ | ~~Close-position endpoint regression~~ | ~~Sprint 25.8~~ | **RESOLVED** (Sprint 25.8, DEC-352): Routes through `OrderManager.close_position()`. 5 new tests. |
| ~~DEF-086~~ | ~~WebSocket test hangs~~ | ~~Post-sprint~~ | **RESOLVED**: 8 tests rewrote to test bridge pipeline directly via send_queue, eliminating sync/async cross-thread hang. |
| ~~DEF-087~~ | ~~11 pre-existing test failures~~ | ~~Post-sprint~~ | **RESOLVED**: 4 vectorbt (NumPy 2.x dep upgrade), 1 data_fetcher (Pandas 2.x datetime precision), 4 e2e telemetry (hardcoded date + async flush), 2 integration sprint20 (regime-based allocation assertions). Zero production code changes. |

## Reference

| Document | What It Covers |
|----------|---------------|
| `docs/decision-log.md` | All 352 DEC entries with full rationale |
| `docs/dec-index.md` | Quick-reference index with status markers |
| `docs/sprint-history.md` | Complete sprint history (1–25.8) |
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
