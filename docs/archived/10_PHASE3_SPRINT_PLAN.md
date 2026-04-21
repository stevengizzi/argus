# ARGUS — Active Sprint Plan (Parallel Tracks) [ARCHIVED]

> **ARCHIVED — last active: Sprint 21.5 (2026-02-27).** Superseded by [docs/roadmap.md](../roadmap.md) per DEC-375. Still referenced by 43 historical sprint files (Sprints 1–21.5) as authoritative context for the era in which they were written; not cited by any sprint artifact after 21.5. Do not use as current planning source — see `docs/roadmap.md`.
>
> *Version 2.0 | February 19, 2026*
> *Supersedes Phase 3 Sprint Plan v1.0. Implements DEC-079 (parallel development tracks).*
> *Previous sprint plans (07, 09) are historical reference.*

---

## Roadmap Structure

ARGUS development follows two parallel tracks (DEC-079):

### Build Track (velocity-limited)
System construction proceeds at development speed. Sprints are numbered
sequentially (Sprint 12+) regardless of which component they target.
Each sprint remains single-threaded for focus.

### Validation Track (calendar-limited, confidence-gated)
Strategy validation runs continuously alongside development. Gates are
based on accumulated market data and user confidence, not sprint completion.

The two tracks reinforce each other: Build Track deliverables (Command Center,
Orchestrator, additional strategies) make the Validation Track more productive.
Validation Track discoveries (execution quality, slippage, parameter behavior)
inform Build Track priorities.

---

## Validation Track

### Gate 1: System Stability (ACTIVE on Alpaca IEX)
- **Parameters:** DEC-076 (or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0)
- **Account:** Alpaca paper ($100K simulated)
- **Data:** Alpaca IEX feed (~2–3% market volume — validates system stability only, not signal accuracy)
- **Status:** Running. System stability testing. Signal accuracy validation requires Databento.
- **Guide:** `docs/08_PAPER_TRADING_GUIDE.md`

### Gate 2: Quality Data Validation (PENDING — Databento + IBKR)
- **Parameters:** DEC-076 (same)
- **Data:** Databento US Equities Standard (institutional-grade, full market volume)
- **Execution:** IBKR paper trading account
- **Begins after:** Databento subscription activated + IBKR account approved (U24619949, submitted Feb 21)
- **Duration:** Minimum 20 trading days
- **Key metrics:** System stability + signal accuracy + execution quality
- **Exit criteria:** No kill criteria triggered, user satisfied, strategy behavior matches backtest expectations

### Gate 3: AI-Enhanced Paper Trading (PENDING — After Sprint 25)
- **Prerequisites:** Setup Quality Engine scoring every trade (5 dimensions — Order Flow added post-revenue per DEC-239), NLP Catalyst Pipeline enriching watchlist, Dynamic Position Sizing in paper mode
- **Strategies:** 7 active (4 Phase 1 + Red-to-Green + 2 pattern modules)
- **Duration:** Minimum 30 trading days
- **Key metric:** Quality-score-to-outcome correlation — A+ setups must outperform B setups. If not, fall back to uniform sizing.
- **Exit criteria:** Quality calibration passes, no kill criteria triggered, intelligence layer demonstrably improving trade selection

### Gate 4: Full System Paper Trading (PENDING — After Sprint 31)
- **Prerequisites:** 18 patterns active, Learning Loop V1 refining scores weekly, Orchestrator V2 managing allocation with AI advisor
- **Duration:** Minimum 20 more trading days (50+ cumulative across Gates 2–4)
- **Key metric:** System-level Sharpe > 2.0 over rolling 30-day windows
- **Exit criteria:** Pattern library stable, learning loop converging, correlation-aware allocation proven, no kill criteria triggered

### Gate 5: Live Trading (User-Gated)
- **Prerequisites:** CPA consultation complete (DEF-004). Explicit go/no-go decision.
- **Start:** Minimum size ($25K, 10-share positions) on IBKR
- **Shadow system:** Paper trading runs permanently in parallel
- **Ramp:** Minimum → Intermediate → Model-calculated → Full (see schedule below)
- **Duration:** Minimum 20 trading days per ramp stage before scaling

#### Validation Sequence (Checklist)
1. ✅ Extended backtest complete (Sprint 11, WFE 0.56, OOS Sharpe +0.34)
2. ✅ Sprint 12: DatabentoDataService adapter built (Feb 21)
3. ✅ Sprint 13: IBKRBroker adapter built (Feb 22, 811 tests)
4. ✅ Sprint 20: Four strategies covering 9:30 AM–3:30 PM
5. ✅ Sprint 21: 7-page Command Center with full analytics
6. ✅ Databento subscription activated + IBKR paper account enabled
7. ⬜ Gate 2: IBKR paper trading (20+ days, DEC-076 parameters, quality data)
8. ⬜ Sprint 25: Intelligence infrastructure operational (Quality Engine, Catalysts, Dynamic Sizing — Order Flow deferred to post-revenue per DEC-238)
9. ⬜ Gate 3: AI-enhanced paper trading (30+ days, quality scoring active)
10. ⬜ Sprint 31: Full pattern library + Learning Loop + Orchestrator V2
11. ⬜ Gate 4: Full system paper trading (20+ days, system Sharpe > 2.0)
12. ⬜ CPA consultation on capital/risk/tax implications (DEF-004)
13. ⬜ Gate 5: Explicit go/no-go → live trading on IBKR at minimum size

#### Ramp Schedule (Advisory)
| Stage | Position Size | Purpose |
|-------|--------------|---------|
| Initial | 10 shares/trade | Verify fills, slippage, system stability |
| Intermediate | 25 shares/trade | Increased size, still minimal risk |
| Model-Calculated | Quality-driven | Dynamic sizing based on quality grades |
| Full | Full model | Transition to full algorithmic sizing |

#### Kill Criteria (Hard Stops — Apply at All Gates)
1. Account drawdown exceeds 15%
2. Profit Factor below 0.7 after 50+ trades
3. Win rate below 25% over any 30-trade window
4. System errors: missed fills, orphaned orders, position tracking discrepancies
5. Zero trades for 5 consecutive trading days when gap candidates exist

#### Monitoring Checklist
- Target hit rate (backtest showed 0% — does this persist?)
- Time stop profitability (net P&L of time-stopped trades)
- Slippage vs. backtest assumption ($0.01/share)
- Trade frequency (~12–14 trades/month expected for ORB alone)
- Monthly P&L pattern (seasonal sensitivity)
- System uptime and health alerts
- Databento data quality (compare candles vs external reference)
- IBKR fill quality (compare vs Alpaca paper fills)
- Quality score calibration (predicted vs actual win rate by grade — Gate 3+)
- Learning Loop convergence (are weekly retrains improving? — Gate 4+)

### Live Trading (FUTURE — Gate 5+)
- All strategies at minimum position size with real capital on IBKR
- Shadow system (paper) runs in parallel permanently
- Minimum 20 trading days per ramp stage before scaling
- Compare live vs. paper vs. backtest expectations
- Gradual scale based on confidence: minimum → intermediate → model-calculated → full

---

## Build Track

### Completed Sprints

| Sprint | Phase | Scope | Tests | Date |
|--------|-------|-------|-------|------|
| 1 | Engine | Config, Event Bus, data models, DB, Trade Logger | 52 | Feb 14 |
| 2 | Engine | Broker Abstraction, SimulatedBroker, Risk Manager | 112 | Feb 14 |
| 3 | Engine | BaseStrategy, ORB Breakout, ReplayDataService, Scanner | 222 | Feb 15 |
| 4a | Engine | AlpacaDataService, AlpacaBroker, Clock injection | 282 | Feb 15 |
| 4b | Engine | Order Manager, AlpacaScanner | 320 | Feb 15 |
| 5 | Engine | HealthMonitor, entry point, state reconstruction, logging | 362 | Feb 16 |
| 6 | Backtest | DataFetcher, Manifest, DataValidator (2.2M+ bars) | 417 | Feb 16 |
| 7 | Backtest | Replay Harness, BacktestDataService, synthetic ticks | 473 | Feb 16 |
| 8 | Backtest | VectorBT parameter sweeps (522K combos) | 506 | Feb 17 |
| 9 | Backtest | Walk-forward validation, HTML reports | 542 | Feb 17 |
| 10 | Backtest | Analysis, Parameter Validation Report | 542 | Feb 17 |
| 11 | Validation | Extended backtest (35mo, 15 windows, WFE=0.56) | 542 | Feb 17 |
| 12 | Infrastructure | DatabentoDataService adapter (streaming, reconnection, historical, scanner, system integration) | 658 | Feb 21 |
| 12.5 | Refactor | IndicatorEngine extraction (DEF-013, DEC-092) | 685 | Feb 21 |
| 13 | Infrastructure | IBKRBroker adapter (connection, orders, brackets, fills, reconnection, reconstruction, Order Manager T2, system integration) | 811 | Feb 22 |
| 13.5 | Evaluation | DEF-016 bracket refactor evaluation → DEFERRED (DEC-095) | 811 | Feb 22 |
| 14 | Command Center API | FastAPI REST (7 endpoint groups) + WebSocket bridge + React scaffold. DEC-099–103. | 926 | Feb 23 |
| 15 | Command Center Frontend | 4 pages (Dashboard, Trade Log, Performance, System). Responsive at 4 breakpoints. Lightweight Charts. WebSocket real-time. 8 sessions. Code review passed. Design research → UX Feature Backlog (DEC-106–110). | 926 | Feb 23 |
| 16 | UX Polish | Desktop/PWA, Framer Motion, skeleton loading, sparklines, trade detail panel, emergency controls, CSV export, PWA, Tauri v2 (DEC-107, DEC-111–112) | 942 | Feb 24 |
| 17 | Orchestrator V1 | Orchestrator, RegimeClassifier, PerformanceThrottler, CorrelationTracker, DEF-016 resolved, 3 API endpoints, 4 WS events, UI components (DEC-113–119) | 1,146 | Feb 24 |
| 21a | Command Center | Pattern Library page (5th page), SymbolDetailPanel, SlideInPanel, strategy metadata enrichment, spec auto-discovery (DEC-172–183) | 1,558 + 70 | Feb 27 |
| 21b | Command Center | Orchestrator page (6th page), hero row layout, regime gauges, strategy operations, decision timeline, throttle override, session phase (DEC-186–195) | 1,597 + 100 | Feb 27 |

### Build Track Queue

Sprints below are ordered by priority but can be resequenced based on what
the Validation Track needs most. Estimates assume the demonstrated ~1 day
per sprint velocity.

#### Sprint 12 — DatabentoDataService Adapter ✅ COMPLETE (Feb 21)
**Delivered:**
- DatabentoConfig, DatabentoSymbolMap, DatabentoDataService (live streaming + reconnection + stale monitor)
- DataFetcher Databento backend (historical data + Parquet cache + manifest tracking)
- DatabentoScanner (V1 watchlist-based gap scanning)
- System integration: DataSource enum, provider selection in main.py
- Shared `databento_utils.py` (normalize_databento_df) — DEC-091
- 658 tests (96 new), ruff fully clean
**Deferred:** SystemAlertEvent for dead data feed (DEF-014), full-universe scanning (DEF-015)
**Note:** Databento subscription not yet activated — deferred until Sprint 13 complete + IBKR approved (DEC-087)

#### Sprint 12.5 — IndicatorEngine Extraction (DEF-013) ✅ COMPLETE (Feb 21)
**Delivered:**
- `IndicatorEngine` class in `argus/data/indicator_engine.py`
- `IndicatorValues` dataclass for returning computed indicator values
- Refactored all four DataServices to delegate to IndicatorEngine:
  - AlpacaDataService, DatabentoDataService, ReplayDataService, BacktestDataService
- Comprehensive unit tests (27 new tests for IndicatorEngine)
- 685 tests total (27 new), ruff fully clean
- Pure refactor — zero behavioral changes, all existing tests pass unchanged
- DEC-092 recorded

**Unblocks:** Clean foundation before adding more DataService implementations (IQFeed, etc.)

#### Sprint 13 — IBKRBroker Adapter ✅ COMPLETE (Feb 22)
**Delivered:**
- `IBKRBroker` implementing full Broker abstraction via `ib_async` library (DEC-083, DEC-093)
- `IBKRConfig` + `BrokerSource` enum for config-driven broker selection (DEC-094)
- `IBKRContractResolver` — stock contract creation with caching
- `IBKRErrorSeverity` classification — IBKR error code mapping with severity routing
- Order submission: market, limit, stop, stop-limit with ULID↔IBKR ID mapping via `orderRef`
- Native bracket orders: parent + stop + T1 + T2 via `parentId` linkage + `transmit` flag pattern
- Fill streaming: `_on_order_status` → `asyncio.ensure_future` → `_handle_order_status` event bridge
- Cancel, modify, account queries (`get_positions`, `get_account`, `flatten_all`)
- Reconnection with exponential backoff, position snapshot comparison, `_reconnecting` guard
- State reconstruction: `reconstruct_state()` recovers positions + ULID mappings from `orderRef`
- Order Manager T2 support: `t2_order_id` field, `_submit_t2_order()`, `_handle_t2_fill()`, tick-skip logic, T2 cancellation in all exit paths
- System integration: `main.py` broker branching, `__init__.py` exports, import cycle verification
- 811 tests (126 new), ruff fully clean
**Deferred:** DEF-016 (Order Manager `place_bracket_order()` integration — atomic bracket submission). SystemAlertEvent on max reconnect retries (DEF-014 amended).

#### Sprint 13.5 — DEF-016 Evaluation ✅ COMPLETE (Feb 22)
**Outcome:** DEFER. Atomic bracket refactor deferred to Sprint 17+ (DEC-095).
**Rationale:** Scope exceeds threshold — SimulatedBroker sync fill conflict, AlpacaBroker single-target limitation, full Order Manager test rewrite required (~1.5–2 days). Near-zero practical benefit for market-order ORB on IBKR. No trigger conditions met.
**Next:** Sprint 15 (Command Center Frontend).

#### Sprint 14 — Command Center: API Layer + Project Scaffolding ✅ COMPLETE (Feb 23)
**Target:** ~1 day
**Scope:**
- FastAPI server exposing trading engine data as REST endpoints
- WebSocket endpoint forwarding Event Bus events to frontend clients
- Monorepo structure: `argus/api/` (FastAPI) + `argus/ui/` (React)
- React project scaffolding (Vite + TypeScript + Tailwind)
- Authentication (JWT, simple for single-user V1)
- API endpoints (read-only MVP):
  - `GET /api/v1/account` — equity, cash, buying power
  - `GET /api/v1/positions` — open positions
  - `GET /api/v1/trades` — trade history (filterable)
  - `GET /api/v1/performance/{period}` — metrics
  - `GET /api/v1/health` — system health
  - `GET /api/v1/strategies` — strategy list + status
  - `WS /ws/v1/live` — real-time event stream

#### Sprint 15 — Command Center: Core Dashboard Views ✅ COMPLETE (Feb 23)
**Delivered:**
- Four pages: Dashboard (account summary cards, open positions with WS real-time prices, recent trades, system health mini), Trade Log (filter bar, stats summary, paginated table with exit reason badges), Performance (period selector, 12-metric grid, equity curve + daily P&L histogram via Lightweight Charts, strategy breakdown), System (overview, component health, strategy cards, collapsible events log)
- Responsive design at 4 breakpoints: 393px (iPhone SE/mini), 834px (iPad portrait), 1194px (iPad landscape), 1512px (MacBook Pro). Icon sidebar nav (desktop/tablet) + bottom tab bar (mobile).
- Dark theme throughout. Loading/error/empty states on all pages. WebSocket reconnection with status indicator. Touch targets ≥44px. iPhone safe area padding.
- 8 implementation sessions, zero build errors, clean lint. 926 tests (unchanged — no new backend tests).
- Code review: all 4 pages across 3 device classes (20 screenshots). Visual consistency confirmed.
- Design research session → UX Feature Backlog created (`docs/ui/UX_FEATURE_BACKLOG.md`, 35 features, DEC-106–110).

#### Sprint 16 — Desktop/PWA + UX Polish ✅ COMPLETE (Feb 24)
**Delivered:**
- **UX Polish (DEC-107):** Framer Motion page transitions + stagger entry animations (all pages), skeleton loading states (all pages), AnimatedNumber (hero equity countup), enhanced P&L flash with scale pulse, card hover lift + table row transitions (desktop-only), SVG sparklines on dashboard cards, chart draw-in animations (equity curve, P&L histogram), contextual empty states (time-aware).
- **Trade detail panel:** Slide-in (desktop: right 40%, mobile: full-screen bottom 90vh). P&L summary, entry/exit, exit reason explanations, hold duration, commission. Close via Escape/backdrop/X.
- **Controls:** Emergency flatten all positions, emergency pause all strategies (with confirmation modals). Per-strategy pause/resume toggle. Individual position close.
- **CSV export:** Trade log download with strategy/date filters. Date-stamped filename.
- **PWA:** manifest.json, service worker (cache-first shell, network-only API/WS), app icons (192/512/maskable/apple-touch), iOS meta tags, production-only SW registration.
- **Tauri v2:** Desktop shell config, system tray icon with toggle visibility, close-to-tray behavior, platform detection utility, all required icons.
- 10 implementation sessions. 942 tests (16 new). Code review passed (DEC-111–112).

#### Sprint 17 — Orchestrator V1 ✅ COMPLETE (Feb 24–25)
**Delivered:**
- Orchestrator core: pre-market routine, 30-min regime monitoring (DEC-115), intraday throttle checks, EOD review, decision logging to `orchestrator_decisions` table.
- RegimeClassifier: SPY 20-day realized vol as VIX proxy (DEC-113), regime categorization (bullish/bearish/range-bound/volatile/crisis).
- PerformanceThrottler: consecutive loss tracking, rolling Sharpe decay, drawdown monitoring. Per-strategy throttle actions (reduce allocation, suspend).
- CorrelationTracker: infrastructure for V2 allocation (DEC-116). Rolling correlation computation, no allocation impact in V1.
- Equal-weight allocation V1 (DEC-114). Single-strategy 40% cap accepted (DEC-119).
- DEF-016 resolved: Order Manager atomic bracket orders via `place_bracket_order()` (DEC-117). Self-contained pre-market poll loop (DEC-118).
- API: GET /orchestrator/status, GET /orchestrator/decisions, POST /orchestrator/rebalance. 4 WebSocket event types.
- UI: SegmentedTab, extended Badge system (strategy state + regime), AllocationDonut (Recharts), RiskGauge (SVG arc).
- 12-phase main.py startup. 1146 tests (204 new). 13 implementation sessions. Code review passed.

#### Sprint 17.5 — Orchestrator Polish ✅ COMPLETE (Feb 25)
**Delivered:**
- Orchestrator encapsulation: 3 read-only properties replacing direct `_private` attribute access in API routes.
- Safe-area padding: additive inner spacer div instead of CSS override that zeroed top padding on non-iOS.
- Animation stability: `hasAnimated` ref pattern on AllocationDonut + RiskGauge (play once, then disabled).
- **RiskAllocationPanel stable render:** Removed conditional skeleton swap (`if (loading) return <Skeleton />`) that caused React to tear down and remount child components every poll cycle. Panel now always renders same DOM structure; children handle empty states internally. Root cause: conditional early returns create different React element trees — switching between them destroys all component state (refs, animation flags).
- Indentation fix in orchestrator.py. Removed `React.memo()` wrappers (broke Vite Fast Refresh in dev mode).
- 1146 tests (unchanged — frontend-only fixes). 4 sessions.

#### Sprint 18 — ORB Scalp Strategy ✅ COMPLETE (Feb 25)
**Delivered:**
- OrbBaseStrategy ABC extraction (DEC-120) — shared OR formation, breakout detection, scanner criteria
- OrbScalpStrategy (DEC-123) — single-target 0.3R exit, 120s hold, per-signal time stop (DEC-122)
- Cross-strategy risk: ALLOW_ALL duplicate stock policy (DEC-121), Risk Manager ↔ Order Manager reference (DEC-124), CandleEvent routing (DEC-125). Sector exposure deferred (DEC-126, DEF-020).
- VectorBT Scalp sweep: 20,880 trades across 29 symbols × 16 param combos. All aggregate Sharpes negative — 1-min bar resolution insufficient for scalp validation (DEC-127, RSK-026). Directional guidance only.
- Walk-forward infrastructure generalized for multi-strategy (`--strategy orb_scalp`).
- Strategy spec sheet: `docs/strategies/STRATEGY_ORB_SCALP.md`
- 14 multi-strategy integration tests (Orchestrator, allocation, risk, throttle, reconstruction).
- UX: SessionSummaryCard (after-hours recap, dismissable), PositionTimeline (horizontal Gantt, strategy badges, time stops, click-to-detail).
- Vitest frontend testing setup (DEC-130): 7 component tests.
- Session summary API endpoint. Dev mode mock data for both strategies.
- 1299 tests (153 new). 12 implementation sessions. Code review passed. DEC-120–127.

#### Sprint 18.5 — Post-Review Polish ✅ COMPLETE (Feb 25)
**Delivered:**
- ORB Scalp mock data in dev mode (open positions, closed trades, system status, strategy cards, performance breakdown, allocation donut)
- SessionSummaryCard dev-mode override — bypasses market status gate for testability (DEC-131)
- Mobile timeline label density: hourly labels at <640px to prevent cramping
- Three-way position filter: All / Open / Closed in both Table and Timeline views (DEC-128). Default: Open during hours, All after hours.
- View toggle persistence: Zustand store (`stores/positionsUI.ts`) survives responsive re-mounts (DEC-129)
- 3 integration test gap fills: same-symbol collision blocked by exposure cap, partial allocation exhaustion per-strategy, throttle isolation between strategies
- AllocationDonut legend: expanded width for full strategy names + display name mapping
- Badge contrast: dark slate badges on amber/yellow timeline bars
- 1313 tests (pytest, 14 new) + 7 (Vitest). 7 sessions.

#### Sprint 18.75 — CapitalAllocation + Dashboard Polish ✅ COMPLETE (Feb 25)
**Delivered:**
- **CapitalAllocation component (DEC-133):** AllocationDonut renamed to CapitalAllocation. Two views via SegmentedTab toggle: (1) Track-and-fill donut — custom SVG with color-tinted track arcs at low opacity, bright clockwise fill arcs proportional to deployment %, sweep animation on mount/toggle, center stat showing total deployed %. (2) Horizontal stacked bars — one per strategy + reserve, deployed/available/throttled segments, labels above/below bars at all breakpoints. Zustand view persistence.
- **MarketRegimeCard (DEC-134):** New dashboard card showing current regime (RegimeClassifier data) with color-coded badge and description. Uses orchestrator status API.
- **Dashboard grid restructure (DEC-134):** Second row from 2 cards to 3 equal-width cards (CapitalAllocation, Risk Budget, Market Regime). Responsive: Market + Market Regime pair at tablet/phone breakpoints (always 2-col).
- **API enrichment (DEC-135):** Orchestrator status endpoint enriched with per-strategy deployed_capital, deployed_pct, is_throttled, plus total_deployed_capital and total_equity.
- **Dev mode mock data:** Strategy allocations corrected to 40%/40%/20% = 100%. Position sizes scaled to realistic values relative to allocations.
- 4 new orchestrator pytest tests (deployment state), 7 new Vitest component tests (CapitalAllocation). 1317 pytest + 14 Vitest total. 8 fix sessions. Code review passed.

#### Sprint 19 — VWAP Reclaim Strategy ✅ COMPLETE (Feb 25–26)
**Delivered:**
- VwapReclaimStrategy: standalone from BaseStrategy (DEC-136), 5-state machine (DEC-138), pullback swing-low stop (DEC-139), T1=1.0R/T2=2.0R, 30-min time stop
- VwapReclaimConfig + YAML, StrategyType.VWAP_RECLAIM enum
- Scanner reuse: shared gap watchlist (DEC-137). Position sizing with minimum risk floor (DEC-140). Cross-strategy ALLOW_ALL extended (DEC-141).
- System integration: main.py wiring, Orchestrator registration, health monitoring
- VectorBT parameter sweep: 59,556 trades, 768 combos, avg Sharpe 3.89, WF OOS Sharpe 1.49 / P&L $15,820 (DEC-146, provisional per DEC-132). Precompute+vectorize architecture (~500x speedup, DEC-144). Performance rule codified in `.claude/rules/backtesting.md` (DEC-149).
- Walk-forward validation: 15 windows, 35 months, VWAP Reclaim dispatch (DEC-145). VectorBT ↔ live state machine divergences harmonized (DEC-148).
- Replay Harness integration (strategy factory)
- Watchlist Sidebar (DEC-142, DEC-147, DEC-150): responsive (desktop 280px inline / tablet slide-out / mobile overlay), compact single-letter badges (O/S/V), VWAP distance metric, sort controls, green left border for entered positions, edge-mounted collapse pill. 26 Vitest component tests.
- Keyboard shortcuts (DEC-151): `1`–`4` page navigation, `w` watchlist toggle
- Dev mode three-strategy mock data (positions, trades, strategy cards, allocation, watchlist)
- Strategy spec: `docs/strategies/STRATEGY_VWAP_RECLAIM.md`
- Integration tests: three-strategy scenarios (allocation, risk, throttle, reconstruction)
- Databento activation deferred to Sprint 20 (DEC-143)
- 1410 tests (pytest, 93 new) + 40 (Vitest, 26 new). 14 implementation sessions + 2 code review checkpoints. Code review passed. DEC-136–151.

#### Sprint 20 — Afternoon Momentum Strategy ✅ COMPLETE (Feb 26)
**Delivered:**
- AfternoonMomentumStrategy: standalone from BaseStrategy (DEC-152), 5-state machine (DEC-155), consolidation high/low channel + ATR filter (DEC-153), 8 simultaneous entry conditions (DEC-156)
- AfternoonMomentumConfig + YAML, gap watchlist reuse from ORB family (DEC-154)
- T1=1.0R/T2=2.0R, dynamic time stop compressed to force_close (DEC-157). Trailing stop deferred (DEC-158, DEF-024). EOD force close at 3:45 PM (DEC-159).
- Cross-strategy: ALLOW_ALL time-separated coverage (DEC-160). Minimum risk floor. Position sizing with consolidation-low stop.
- VectorBT parameter sweep: 1,152 combos, precompute+vectorize architecture (DEC-162). Walk-forward pipeline dispatch. Results provisional per DEC-132.
- Replay Harness integration (strategy factory for afternoon_momentum)
- System integration: main.py Phase 8 creation + Phase 9 Orchestrator registration + Phase 10 per-strategy health (all 4 strategies now have health components)
- Dev mode four-strategy mock data (positions, trades, allocations, orchestrator decisions, watchlist, strategy cards, session summary). 20/20/20/20 allocation split.
- 16 four-strategy integration tests (registration, sequential flows, cross-strategy risk, state machine, volume filter, time stops, EOD flatten, throttling, daily reset, allocation caps)
- Strategy spec: `docs/strategies/STRATEGY_AFTERNOON_MOMENTUM.md`
- Vitest: StrategyCards tests (6 new) + CapitalAllocation 4-strategy tests (2 new)
- Databento activation deferred to Sprint 21 (DEC-161)
- 1522 tests (pytest, 112 new) + 48 (Vitest, 8 new). 10 implementation sessions + 2 code review checkpoints. Code review passed. DEC-152–162.
- **Milestone:** ARGUS now covers 9:30 AM–3:30 PM with four strategies (ORB, Scalp, VWAP Reclaim, Afternoon Momentum).

#### Sprint 21a — Pattern Library Page ✅ COMPLETE (Feb 27)
**Delivered:**
- **Pattern Library page (DEC-169, DEC-171):** NEW 5th page. Master-detail layout. Left panel: strategy cards grid with pipeline stage badges, operating windows, key metrics, filters (stage, time window, pattern family), sort controls. Right panel: tabbed strategy detail (Overview, Performance, Backtest, Trades, Intelligence).
- **IncubatorPipeline (DEC-179):** Horizontal pipeline with 10 stages, dot indicators, click-to-filter, responsive (pipeline on desktop, compact pills on mobile).
- **PatternCard, PatternCardGrid, PatternFilters:** Strategy cards with metrics, family badges, pipeline stage, responsive grid.
- **PatternDetail with 5 tabs:** Overview (MarkdownRenderer for spec sheets + config summary), Backtest (structured summary from YAML), Performance (EquityCurve + DailyPnlChart in compact mode), Trades (symbol-filtered trade history), Intelligence (placeholder).
- **SymbolDetailPanel (DEC-177):** Global slide-in panel triggered from any symbol click via `symbolDetailUI` Zustand store. SymbolChart (candlestick via Lightweight Charts), SymbolTradingHistory, SymbolPositionDetail.
- **SlideInPanel extraction (DEC-177):** Shared component from TradeDetailPanel. Desktop: right 40%, mobile: bottom 90vh.
- **Strategy metadata enrichment (DEC-172):** API returns time_window, family, description_short, performance_summary, backtest_summary.
- **Strategy spec auto-discovery (DEC-181):** Convention-based (`strat_X` → `STRATEGY_X.md`), no hardcoded map.
- **Z-index hierarchy (DEC-182):** SlideInPanel z-50, WatchlistSidebar mobile z-40.
- **Compact chart prop (DEC-183):** EquityCurve and DailyPnlChart `compact` prop replaces CSS override.
- **Keyboard shortcuts (DEC-180):** 1–5 navigation (Pattern Library = 4), w watchlist.
- **Dependencies added:** react-markdown, remark-gfm
- 1558 tests (pytest, 36 new) + 70 (Vitest, 22 new). 9 implementation sessions. Code review passed. DEC-172–183.

#### Sprint 21b — Orchestrator Page ✅ COMPLETE (Feb 27)
**Delivered:**
- **Orchestrator page (DEC-169, DEC-171):** NEW 6th page. Hero row layout (DEC-192): SessionOverview + RegimePanel stacked left, CapitalAllocation donut right. StrategyCoverageTimeline (custom SVG, DEC-188). StrategyOperationsGrid (2-col cards with allocation bars, throttle status, pause/resume). DecisionTimeline (newest-first, DEC-194). GlobalControls (force rebalance, emergency flatten/pause with ConfirmModal).
- **RegimePanel gauge redesign (DEC-195):** Visual gauge bars for Trend/Vol/Momentum with positioned marker dots on red→yellow→green gradient. Regime badge as hero element. Session phase badge extracted to page header (`SessionPhaseBadge`).
- **Throttle override (DEC-187):** Duration dropdown (30m/1h/rest-of-day) + mandatory reason textarea. In-memory `_override_until` with time-based expiry. Logged to decision log.
- **Strategy config consolidation (DEC-193):** Shared `strategyConfig.ts` with `STRATEGY_DISPLAY` record. All components import from single source.
- **ConfirmModal extraction:** Reusable confirmation dialog extracted from GlobalControls.
- **API extensions:** Session phase, pre_market_complete, per-strategy operating_window/throttle metrics/override status. Date filter on decisions endpoint. POST override endpoint. Client-side regime input scoring (DEC-191).
- **Dev mode:** ORB Scalp throttled (REDUCE), ~15 decision entries, operating windows, session phase. Four-strategy mock data.
- **Nav:** 6 pages, abbreviated mobile labels (DEC-189). Keyboard shortcuts 1–6.
- 1597 tests (pytest, 39 new) + 100 (Vitest, 30 new). 13 sessions (8 implementation + 1 review + 4 polish). Code review passed. DEC-186–195.
- **Deferred to 21d:** PreMarketCard/EodSummaryCard as dedicated components, multi-day regime history, decision filtering, "More" menu for mobile nav.

#### Sprint 21c — The Debrief Page ✅ COMPLETE (Feb 27)
**Delivered:**
- **The Debrief page (DEC-169, DEC-171):** 7th and final Command Center page. Three-section SegmentedTab: Briefings, Research Library, Journal.
- **Briefings tab:** BriefingList (Pre-Market/EOD creation dropdown, reverse-chronological cards), BriefingCard (type+status badges, content preview, DocumentModal reading), BriefingEditor (side-by-side markdown edit/preview on desktop, toggle on mobile, Ctrl+S save, unsaved indicator, key-based remount pattern). UNIQUE(date, briefing_type) constraint — 409 Conflict handled via ApiError class (DEC-202).
- **Research Library:** Hybrid filesystem (read-only repo docs from docs/research/, docs/strategies/, docs/backtesting/) + database (CRUD custom docs) via DEC-198. ResearchDocCard (category+source badges), DocumentEditor (markdown, category selector, TagInput). Custom docs sort first.
- **Journal:** JournalList (4-filter dimensions: type, strategy, tag, search with 300ms debounce). JournalEntryCard (4 typed badges — Observation/Eye, Trade Annotation/Target, Pattern Note/Lightbulb, System Note/Settings — expand/collapse, inline edit via AnimatePresence). JournalEntryForm (collapsed→expanded inline creation, success flash). TradeSearchInput (debounced symbol search, linked trade chips → SymbolDetailPanel). TagInput shared component (autocomplete, keyboard nav, duplicate prevention).
- **Backend:** DebriefService (992 lines), 3 DB tables (briefings, journal_entries updated DEC-196, documents), 4 API route files (briefings.py, documents.py, journal.py, debrief_search.py), LIKE search over FTS5 (DEC-200). Batch trade fetch endpoint (DEC-203).
- **Nav:** 7 pages complete (DEC-199). Keyboard shortcuts 1–7, b/r/j tab switching, n new entry, Escape close (else-if priority chain).
- **Dev mode:** 5 briefings, 3+ DB docs, 10 journal entries.
- **Post-review fixes:** ApiError class (DEC-202), Escape handler cascade, success flash timer cleanup, batch trade endpoint (DEC-203).
- 1664 tests (pytest, 105 new) + 138 (Vitest, 38 new). 10 implementation sessions + 2 code reviews + 1 fix session. Code review passed. DEC-196–203.
- **Resolved deferrals:** DEF-026 (FTS5 → LIKE search, DEC-200), DEF-027 (trade linking UI, DEC-201).

**Decisions:** DEC-196 through DEC-201
**Resolved deferrals:** DEF-026 (FTS5 → LIKE search), DEF-027 (trade linking UI included)

#### Sprint 21d — Dashboard Refinement + Performance Analytics + System Cleanup + Nav Restructure + AI Copilot Shell ✅ COMPLETE (Feb 27–28)
**Delivered:**
- **Dashboard redesign (DEC-204):** Narrowed to ambient awareness. OrchestratorStatusStrip (clickable → Orchestrator). StrategyDeploymentBar (per-strategy capital deployment with accent colors, DEC-219). GoalTracker (2-column pace dashboard, DEC-220). Three-card row: MarketStatus (merged Market+Regime), TodayStats (2×2 metrics), SessionTimeline (SVG strategy windows + "now" marker, DEC-221). PreMarketLayout with placeholder cards (DEC-213). Dashboard aggregate endpoint (DEC-222). useSummaryData hook disabling pattern (DEC-223). Removed: CapitalAllocation, RiskGauge, MarketRegimeCard (migrated to Orchestrator in Sprint 17/21b).
- **Performance analytics (DEC-205):** 5-tab layout with 8 visualizations. Overview (MetricsGrid, EquityCurve, DailyPnlChart, StrategyBreakdown, comparison toggle). Heatmaps (TradeActivityHeatmap via D3, CalendarPnlView). Distribution (RMultipleHistogram via Recharts, RiskWaterfall — side-by-side desktop DEC-227). Portfolio (PortfolioTreemap via D3, CorrelationMatrix — side-by-side 60/40 desktop). Replay (TradeReplay with trade selector + Lightweight Charts playback). Unified diverging color scale (DEC-224). WCAG dynamic text contrast (DEC-225). Single-letter strategy labels (DEC-226). Tab keyboard shortcuts o/h/d/p/r (DEC-228). Performance Workbench deferred (DEC-229).
- **System cleanup (DEC-210):** Removed StrategyCards and EmergencyControls. Added IntelligencePlaceholders (6 AI component cards with sprint target badges).
- **Navigation restructure (DEC-211, DEC-216):** Sidebar group dividers. Mobile 5-tab (Dash, Trades, Orch, Patterns, More) + MoreSheet bottom sheet (Performance, Debrief, System).
- **AI Copilot shell (DEC-212, DEC-217):** CopilotPanel (new component, persists across pages), CopilotButton (adaptive positioning), copilotUI Zustand store, `c` keyboard shortcut. Placeholder content for Sprint 22 activation.
- **Backend:** 5 new endpoints (heatmap, distribution, correlation, replay, goals) + dashboard summary aggregate. GoalsConfig. New TradeLogger method. Dev mock data expansion.
- **Dependencies:** d3-scale, d3-color, d3-hierarchy, d3-interpolate (individual modules).
- 1712 tests (pytest, 48 new) + 257 (Vitest, 119 new). 13 implementation sessions + 3 code reviews. Code review passed (DEC-204–229).
- **Deferred:** DEF-028 (CalendarPnlView strategy filter), DEC-229 (Performance Workbench).

**Decisions:** DEC-204 through DEC-229
**Deferred:** DEF-028, DEC-229

### Sprint 21.5 — Live Integration (Databento + IBKR)
Status: ✅ COMPLETE (Feb 28 – Mar 5, 2026)
**Start:** Feb 28, 2026
**Estimated sessions:** 13–16 (Claude Code) + 3 code reviews (Claude.ai)
**Test count:** 1,737 (pytest) + 291 (Vitest) — final

**Completed sessions:**
- Sessions 1–3: Databento connection. API format discoveries: instrument_id direct attribute (DEC-241), built-in symbology_map (DEC-242), fixed-point prices ×1e9 (DEC-243). Dataset switch from XNAS.ITCH to EQUS.MINI (DEC-237/248).
- Sessions 4–6: First live market data streaming. 30+ min with CandleEvents across 10 symbols. VWAP Reclaim signal on NFLX (~$97, 3573 shares requested — correctly rejected by Risk Manager for 5% concentration limit).
- Session 7: IBKR paper connection. Bracket orders validated. flatten_all() SMART routing fix (DEC-245).
- Sessions 8–9: Position management lifecycle. State reconstruction from broker. Reconnection. get_open_orders() added to Broker ABC (DEC-246).
- Session A1: Validation scripts — 13/13 integration PASS, 4/4 resilience PASS. Discovered EQUS.MINI historical data lag blocking scanner (422 error).
- Session B0: Scanner resilience fix (DEC-247, 13 new tests). EQUS.MINI diagnostic — live streaming confirmed, all schemas verified (ohlcv-1m, ohlcv-1d, trades, tbbo), multi-symbol queries functional (DEC-248). DatabentoSymbolMap deleted.
- Sessions B1–B5: Position sizing verified (Risk Manager concentration limit working correctly). Time stop/EOD flatten validated via code review. Operational scripts created (`scripts/start_live.sh`, `scripts/stop_live.sh`). `docs/LIVE_OPERATIONS.md` created (418 lines). Documentation sync complete.
- Session C1 (Mar 3): First live market day. AAPL VWAP Reclaim +$70.30 (1.22R). Bugs found & fixed: absolute risk floor replaces 0.25R ratio (DEC-251), tick rounding (DEC-252). Post-session: heartbeat logging (DEC-253), auto-shutdown (DEC-254), IBKR error severity (DEC-255), PositionClosedEvent symbol field (DEC-256).
- Session C2 (Mar 4): Second paper trading session. 11 trades, 7 symbols, 3 strategies active. +$335.79 net P&L, 40% win rate. Discovered 4 ORB dual-fire incidents, flatten fill mismatch, concentration race condition, win rate 0% bug, dashboard P&L excluding unrealized, strategy colors all grey, candlestick chart showing synthetic data. Full post-market diagnostic captured.
- Session C3 (Mar 5): Third paper trading session with 21.5.1 fixes deployed. Ran successfully.
- Sprint 21.5.1 (Mar 5, unplanned): 5 sessions + 1 hotfix. Session 1: flatten fill routing, concentration race fix, ORB exclusion (DEC-261). Session 2: daily P&L includes unrealized, 0.0 handling fix, bars endpoint real data, TradeResponse fields. Session 3: strategy colors, price levels, position timeline zoom, PositionDetailPanel. Session 4+4b: TradeChart (Lightweight Charts v5), trade filters, is_dev_mode gate removal.
- Block D (Mar 5): Sprint closeout, documentation sync, code audit. READ-ONLY session.

**Remaining sessions:**
- Block C (C2–C3): Full trading day validation (all 4 strategies, Databento + IBKR, Command Center with live data)
- Block D (D1): Sprint closeout + documentation

**Key deliverables:**
- `config/system_live.yaml` (Databento + IBKR config) ✅
- `.env.example` (documented environment variables) ✅
- EQUS.MINI consolidated dataset (replaces XNAS.ITCH + XNYS.PILLAR plan) ✅
- Live Databento data flowing through all 4 strategies — pending full-day validation
- Paper trades executing on IBKR via IB Gateway ✅
- Command Center showing real-time live data — pending full-day validation
- `docs/LIVE_OPERATIONS.md` ✅ (418 lines)
- Startup/shutdown automation scripts (`scripts/start_live.sh`, `scripts/stop_live.sh`) ✅
- `scripts/diagnose_databento.py` diagnostic tool ✅
- Concentration limit approve-with-modification (DEC-249) ✅
- Time stop + EOD validation script (`scripts/test_time_stop_eod.py`) ✅

**Decisions:** DEC-230–261 (32 decisions)
**Prerequisites:** Databento subscription activated ✅, IBKR account approved ✅
**Exit criteria:** Full market session (9:30-4:00 ET) completed without crashes, all 4 strategies processing data, paper trades executing, Command Center operational with live data, clean overnight workflow verified

### Sprint 21.5.1 — C2 Bug Fixes + UI Polish ✅ COMPLETE (Mar 5, 2026)
**Unplanned sub-sprint** triggered by C2 paper trading findings.
**Sessions:** 5 implementation + 1 hotfix (all in one day)
**Tests added:** +25 pytest (1,712→1,737), +34 Vitest (257→291)
**Decisions:** DEC-261
**Key deliverables:**
- Trading engine: flatten fill strategy_id matching, pending entry exposure in concentration check, ORB family same-symbol mutual exclusion (DEC-261)
- Backend: daily P&L includes unrealized, 0.0 handling fix, bars endpoint real data, TradeResponse stop/target fields
- Frontend: strategy colors, price levels display, position timeline zoom, PositionDetailPanel, TradeChart (Lightweight Charts v5), trade filters
- Hotfix: removed is_dev_mode gate blocking real bars data in paper trading

### Sprint 21.7 — FMP Scanner Integration (DEC-257, DEC-258, DEC-259)
**Status:** QUEUED (follows Sprint 21.5 completion)
**Estimated sessions:** 2–3
**Full spec:** To be drafted in dedicated sprint planning conversation

**Scope:**
- Add FMP Starter ($22/mo) as scanning data source
- Implement `FMPScannerSource` class: 1–2 REST calls pre-market (daily bars for gap/volume screening, gainers/losers endpoint)
- Config entry for FMP API key (secrets manager)
- Scanner adapter: parse FMP JSON → ranked symbol list via existing Scanner interface
- Tests for FMP adapter (mock HTTP responses)
- Validate end-to-end: FMP scan → symbol list → Databento live subscription → strategy execution

**Rationale:** Databento historical daily bar lag (DEC-247) makes the scanner non-functional for pre-market gap/volume screening. Static 10-symbol fallback is adequate for execution validation but not for alpha validation. FMP Starter provides reliable pre-market daily bars at $22/mo. Every paper trading session after this sprint produces more meaningful validation data for Gate 2 metrics.

**Prerequisites:** Sprint 21.5 complete (live pipeline confirmed working)
**Exit criteria:** Scanner produces dynamic watchlist from FMP data pre-market. Full pipeline validated: FMP scan → Databento subscription → strategies receive data → paper trades execute.

**Decisions:** DEC-257 (hybrid architecture), DEC-258 (FMP Starter), DEC-259 (this sprint), DEC-260 (rejected providers)

### Sprint 21.6 — Backtest Re-Validation (DEC-132 / DEC-235)
**Status:** QUEUED (runs parallel with Sprint 22)
**Estimated sessions:** 6-8
**Full spec:** To be drafted after Sprint 21.5 completion

**Scope:**
- Pull Databento historical data for all 28+ backtest symbols (35 months)
- Re-run VectorBT parameter sweeps with exchange-direct data
- Re-run walk-forward analysis for all 4 strategies
- Compare results against Alpaca-data baselines
- Adjust parameters if material differences found
- Update strategy specs and decision log entries marked "provisional per DEC-132"

**Prerequisites:** Sprint 21.5 complete (Databento data pipeline confirmed working)
**Exit criteria:** All 4 strategy parameters either confirmed or updated with Databento data. DEC-132 resolved.

#### Sprint 22 — AI Layer MVP + Copilot Activation (DEC-096, DEC-098, DEC-170)
**Target:** ~2–3 days
**Scope:**
- Anthropic API integration (`argus/ai/claude_service.py`). Model: Claude Opus for all calls (DEC-098). Prompt caching for system context.
- **System Context Builder** (`argus/ai/context_builder.py`): Assembles current state for Claude — positions, regime, strategy metrics, quality scores, recent decisions, recent trades. Page-specific context payloads for Copilot (DEC-170).
- **AI Copilot activation (DEC-170):** Full chat functionality in the slide-out panel. Context injection per page. Message history persistence (stored in Debrief Learning Journal DB). Claude can: answer questions about any system data, generate reports (saved to Debrief), propose parameter changes (approval workflow), propose allocation overrides (approval workflow), annotate trades (saved to Learning Journal), explain any Orchestrator decision.
- **Pre-market briefing generation:** Claude produces daily briefing from regime data + scanner results + any available catalyst info. Saved to The Debrief automatically.
- **EOD report generation:** Claude analyzes day's trades, regime, notable events. Saved to The Debrief.
- **Post-trade analysis:** Real-time trade evaluation with context.
- **Anomaly detection:** Periodic system/market checks during trading hours.
- **Weekly/monthly reviews:** Claude generates narrative performance reports.
- **Approval workflow:** Claude proposes changes → approval card appears in Orchestrator decision stream AND as Copilot message → user approves/rejects/modifies.
- API: `/api/v1/ai/chat` (WebSocket), `/api/v1/ai/briefing/generate`, `/api/v1/ai/report/generate`, `/api/v1/ai/analyze/trade/{trade_id}`.
- **UX (from Backlog):** AI insight cards on Dashboard (22-A). Strategy optimization landscape in Orchestrator (22-C, Three.js/Plotly 3D). Multi-line outcome projections on Performance (22-D, Monte Carlo fan chart).
**Updated prerequisite (DEC-230):** Sprint 22 now follows Sprint 21.5 (live integration). AI Layer will be built on top of a live system with real Databento data and IBKR paper execution, rather than mock data. Copilot tested with real market context from session one. Sprint 21.6 (backtest re-validation) runs in parallel.

#### Sprint 23 — NLP Catalyst Pipeline + Pre-Market Engine (DEC-163, DEC-164)
**Target:** ~2–3 days
**Scope:**
- **CatalystService** (`argus/intelligence/catalyst_service.py`): Symbol-matched news from Finnhub (company news API, free tier) + SEC EDGAR (8-K, Form 4) + FMP (earnings calendar, press releases).
- **CatalystClassifier** (`argus/intelligence/catalyst_classifier.py`): Claude API for catalyst quality scoring (1–10) and category assignment (FDA, Earnings, Analyst, M&A, Offering, Insider, Macro, Legal, Product, Guidance).
- **PreMarketEngine** (`argus/intelligence/premarket_engine.py`): Automated 4:00 AM → 9:25 AM pipeline. Populates Dashboard pre-market mode with real ranked watchlist + catalyst data. Generates pre-market briefing via AI Layer (saved to Debrief).
- **CatalystEvent** on Event Bus. Scanner enrichment with catalyst metadata.
- **UI:** Dashboard pre-market mode now populated with live data. Watchlist sidebar gains catalyst type badges. Trade Detail Panel gains catalyst context section. The Debrief gains real pre-market briefings.
- **Tests:** ~80 new.

#### Sprint 24 — Setup Quality Engine + Dynamic Position Sizer (DEC-163, DEC-239)
**Target:** ~3–4 days
**Scope:**
- **SetupQualityEngine** (`argus/intelligence/quality_engine.py`): Composite 0–100 scoring from 5 weighted inputs (DEC-239). Order Flow dimension added post-revenue when Databento Plus activated. Configurable weights via YAML.
- **DynamicPositionSizer** (`argus/intelligence/position_sizer.py`): Grade → risk tier → share count. A+=2–3%, B=0.5–0.75%, C-=SKIP. Replaces fixed risk_per_trade_pct. Risk Manager limits still enforced.
- SignalEvent enrichment: quality_score, quality_grade, risk_tier fields.
- Quality History DB table for Learning Loop.
- **UI:** Dashboard gains quality distribution mini-card. Watchlist/positions/trade log gain quality grade badges. Trade Detail gains radar chart + "Why this size?" breakdown. Performance gains "by quality grade" chart.
- **Tests:** ~100 new.

#### Sprint 25 — Red-to-Green + Pattern Library Foundation (DEC-163, DEC-167)
**Target:** ~2 days
- RedToGreenStrategy through Incubator stages 1–3.
- PatternLibrary ABC interface. Bull Flag + Flat-Top Breakout modules.
- Pattern modules feed "pattern strength" to Quality Engine.
- **7 strategies/patterns active.** Tests: ~80 new.

#### Sprint 26 — Pattern Expansion I (DEC-167)
**Target:** ~2–3 days
- Dip-and-Rip, HOD Break, Pre-Market High Break, Gap-and-Go modules. Each stages 1–3.
- **11 strategies/patterns active.** Tests: ~60 new.

#### Sprint 27 — Short Selling Infrastructure + Parabolic Short (DEC-166, DEC-238)
**Target:** ~2–3 days
- Short selling infrastructure: locate/borrow tracking, inverted risk logic, short-specific Risk Manager rules.
- Parabolic Short module (first short strategy).
- **Note:** Decoupled from Order Flow V2 (DEC-238). Short entries use L1 signals (parabolic extension detection, volume exhaustion, reversal candle patterns). Order Flow enhancement added post-revenue.
- **12 strategies/patterns active.** Tests: ~80 new.

#### Sprint 28 — Pattern Expansion II (DEC-167)
**Target:** ~2–3 days
- ABCD Reversal, Sympathy Play, Power Hour Reversal, Earnings Gap Continuation modules.
- **16 strategies/patterns active.** Tests: ~60 new.

#### Sprint 29 — Learning Loop V1 (DEC-163)
**Target:** ~2–3 days
- LearningDatabase, PostTradeAnalyzer, weekly batch retraining, quality calibration.
- **UI:** Performance gains calibration chart. Dashboard gains weekly insight card. System gains Learning Loop health.
- Tests: ~60 new.

#### Sprint 30 — Orchestrator V2 AI-Enhanced (DEC-163)
**Target:** ~2–3 days
- Intraday dynamic allocation. AI allocation advisor. Correlation-aware allocation. Quality-weighted replaces equal-weight. Opportunity cost tracking.
- Tests: ~60 new.

#### Sprint 31 — Pattern Expansion III + Volume Profile (DEC-163)
**Target:** ~2–3 days
- Volume Shelf Bounce, Micro Float Runner modules. Volume Profile (VPOC/value area).
- **18 strategies/patterns — full V1 library.** Tests: ~60 new.

#### Sprint 32+ — Optimization & Expansion (Backlog)
- Learning Loop V2 (ML — LightGBM). Advanced Regime Engine. Crypto expansion via IBKR. Monte Carlo simulation. Tax optimization. Strategy breeding.

#### Post-Revenue Backlog (DEC-238)
Scheduled when monthly trading income justifies Databento Plus tier ($1,399/mo). Historical L2/L3 data available on current Standard plan for backtesting these features before activation.

- **Order Flow Model V1** (was Sprint 24): Databento L2 (MBP-10) subscription for watchlist symbols. OrderFlowAnalyzer (bid/ask imbalance, ask thinning, tape speed, bid stacking). OrderFlowEvent on Event Bus. UI: flow quality indicators, L2 depth heatmap. ~2–3 days.
- **Order Flow V2 + L3** (was part of Sprint 28): Databento L3 integration. Iceberg/spoofing/absorption detection. ~1–2 days.
- **Setup Quality Engine 6th Dimension:** Add Order Flow (20%) to scoring. Rebalance all weights to original 6-dimension design. ~0.5 day.

---

## Sprint Execution Protocol

Each sprint follows the established pattern:
1. **Spec:** Claude.ai designs the sprint spec with test targets
2. **Implement:** Claude Code executes the spec from the git repo
3. **Review:** User reviews transcript, runs tests, validates
4. **Document:** Update this sprint plan, CLAUDE.md, and any affected docs
5. **Sync:** Push to git, sync to Claude project

Sprints remain single-threaded for focus. Context switches happen between
sprints, not within them.

---

## What Changed From Previous Structure (DEC-079, DEC-080, DEC-082–087)

| Before | After |
|--------|-------|
| Alpaca for both data and execution | Databento for data, IBKR for execution, Alpaca for incubator only |
| Free data (Alpaca IEX, 2–3% volume) | Databento $199/month (full universe, exchange-direct feeds) |
| Alpaca → IBKR phased migration planned | Direct IBKR adoption (no phased migration) |
| Command Center as Sprint 12–14 | Infrastructure first (Sprint 12–13), then Command Center (Sprint 14–16) |
| Linear phases → Two parallel tracks (DEC-079) | Two parallel tracks (unchanged) |
| Single-strategy validation before second strategy | Multiple strategies can validate in parallel once Orchestrator exists |
| Command Center = Tauri desktop only | Three surfaces from single React codebase: web + Tauri desktop + PWA mobile (DEC-080) |
| Historical data from Alpaca only | Databento source, Parquet cache. Existing Alpaca data retained (DEC-085) |
| $0/month data cost | $199/month Databento (deferred until adapter ready — DEC-087) |

---

## Completed Phase Summary (Historical Reference)

| Phase | Scope | Sprints | Tests | Dates |
|-------|-------|---------|-------|-------|
| 1 — Core Engine | Trading Engine + ORB Strategy | 1–5 | 362 | Feb 14–16, 2026 |
| 2 — Backtesting | Parameter sweeps, walk-forward, reports | 6–10 | 542 | Feb 16–17, 2026 |
| 3a — Extended Backtest | 35mo data, 15 WF windows | 11 | 542 | Feb 17, 2026 |

*Phase 1 Sprint Plan: `07_PHASE1_SPRINT_PLAN.md` (historical)*
*Phase 2 Sprint Plan: `09_PHASE2_SPRINT_PLAN.md` (historical)*