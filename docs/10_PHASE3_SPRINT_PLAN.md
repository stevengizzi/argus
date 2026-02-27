# ARGUS — Active Sprint Plan (Parallel Tracks)

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

### Gate 3: AI-Enhanced Paper Trading (PENDING — After Sprint 26)
- **Prerequisites:** Setup Quality Engine scoring every trade, NLP Catalyst Pipeline enriching watchlist, Order Flow V1 contributing to entries, Dynamic Position Sizing in paper mode
- **Strategies:** 7 active (4 Phase 1 + Red-to-Green + 2 pattern modules)
- **Duration:** Minimum 30 trading days
- **Key metric:** Quality-score-to-outcome correlation — A+ setups must outperform B setups. If not, fall back to uniform sizing.
- **Exit criteria:** Quality calibration passes, no kill criteria triggered, intelligence layer demonstrably improving trade selection

### Gate 4: Full System Paper Trading (PENDING — After Sprint 32)
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
5. ⬜ Sprint 21: 7-page Command Center with full analytics
6. ⬜ Databento subscription activated + IBKR paper account enabled
7. ⬜ Gate 2: IBKR paper trading (20+ days, DEC-076 parameters, quality data)
8. ⬜ Sprint 26: Intelligence infrastructure operational (Quality Engine, Order Flow, Catalysts)
9. ⬜ Gate 3: AI-enhanced paper trading (30+ days, quality scoring active)
10. ⬜ Sprint 32: Full pattern library + Learning Loop + Orchestrator V2
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

#### Sprint 21c — The Debrief Page (DEC-169, DEC-171)
**Target:** ~1–2 days
**Scope:**
- **The Debrief page** (NEW — 6th page): Three sections via in-page tabs. Section A — Daily Briefings: reverse-chronological list of pre-market and EOD report placeholders (structure now, AI Layer populates in Sprint 22). Manual entry support. Section B — Research Library: document browser for all project research (market data report, broker report, parameter validation, strategy specs, expanded roadmap). Documents rendered as readable panels with markdown support. Taggable, searchable, filterable by type. Section C — Learning Journal: manual observations, trade annotations (linked to trade IDs), pattern observations. Free-form entries with tags and date.
- Import existing research documents as initial Research Library content.
- API: `/api/v1/debrief/briefings` (CRUD), `/api/v1/debrief/documents` (read + metadata), `/api/v1/debrief/journal` (CRUD with tags/links).
- **Mobile:** Tab-based. Briefings default view. Document viewer optimized for phone reading.
- **Tests:** Vitest component tests, pytest for new API endpoints.

#### Sprint 21d — Dashboard Refinement + Performance Analytics + System Cleanup + Nav Restructure (DEC-169, DEC-171)
**Target:** ~2–3 days
**Scope:**
- **Dashboard refinement:** Narrow scope to pure ambient awareness. Remove controls and detailed panels migrated to Orchestrator/Pattern Library. Add: compact "Orchestrator Status" strip (strategies active, deployed capital, risk budget, regime badge — click navigates to Orchestrator). Pre-market mode: before 9:30 AM, Dashboard shows Pre-Market layout (ranked watchlist, regime forecast — placeholder until Sprint 23 populates with real data). Goal tracking indicator (21-J from UX Backlog).
- **Performance page analytics (from UX Backlog DEC-108):** Trade activity heatmap (21-C, D3 calendar heatmap), win/loss R-multiple histogram (21-D, Recharts), portfolio treemap (21-E, D3), risk waterfall chart (21-F), comparative period overlay (21-G), strategy correlation matrix (21-H). Calendar P&L view. Side-by-side strategy comparison.
- **System page cleanup:** Narrow to infrastructure health only. Strategy cards and controls already migrated. Add health cards for future intelligence components (Pre-Market Engine, Order Flow, Catalyst Service, Learning Loop — show "Not Yet Active" until respective sprints).
- **AI Copilot shell (DEC-170):** Floating chat button (bottom-right, keyboard shortcut `c`). Slide-out panel (desktop: right 35%, mobile: full-screen overlay). Shows placeholder: "AI Copilot activating in Sprint 22. Chat with Claude will be available here — contextual, page-aware, with full system knowledge." Panel structure: message history area, input field, context indicator showing current page name.
- **Nav restructure:** Desktop icon sidebar with 7 items grouped: Monitor (Dashboard 📊, Trades 📋, Performance 📈) | Operate (Orchestrator 🎯, Patterns 🧩) | Learn (Debrief 📚) | Maintain (System ⚙️). Keyboard shortcuts 1–7, `c` for copilot, `w` for watchlist. Mobile: 5 bottom tabs (Dashboard, Trades, Orchestrator, Patterns, More → Performance, Debrief, System). Copilot button floats above tab bar.
- **Trade Replay Mode (21-I from UX Backlog):** Animated trade walkthrough from Trade Log or Pattern Library Trades tab.
- **Tests:** Vitest for new dashboard components, heatmap, histogram, treemap, nav, copilot shell.
- **Milestone:** 7-page Command Center architecture established. All intelligence sprints (23+) add features to the correct pages.

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

#### Sprint 23 — NLP Catalyst Pipeline + Pre-Market Engine (DEC-163, DEC-164)
**Target:** ~2–3 days
**Scope:**
- **CatalystService** (`argus/intelligence/catalyst_service.py`): Symbol-matched news from Finnhub (company news API, free tier) + SEC EDGAR (8-K, Form 4) + FMP (earnings calendar, press releases).
- **CatalystClassifier** (`argus/intelligence/catalyst_classifier.py`): Claude API for catalyst quality scoring (1–10) and category assignment (FDA, Earnings, Analyst, M&A, Offering, Insider, Macro, Legal, Product, Guidance).
- **PreMarketEngine** (`argus/intelligence/premarket_engine.py`): Automated 4:00 AM → 9:25 AM pipeline. Populates Dashboard pre-market mode with real ranked watchlist + catalyst data. Generates pre-market briefing via AI Layer (saved to Debrief).
- **CatalystEvent** on Event Bus. Scanner enrichment with catalyst metadata.
- **UI:** Dashboard pre-market mode now populated with live data. Watchlist sidebar gains catalyst type badges. Trade Detail Panel gains catalyst context section. The Debrief gains real pre-market briefings.
- **Tests:** ~80 new.

#### Sprint 24 — Order Flow Model V1 (DEC-163, DEC-165)
**Target:** ~2–3 days
**Scope:**
- Databento L2 (MBP-10) subscription for all watchlist symbols. DatabentoDataService extension.
- **OrderFlowAnalyzer** (`argus/intelligence/order_flow.py`): bid/ask imbalance, ask thinning, tape speed, bid stacking. Throttled 100ms updates.
- **OrderFlowEvent** on Event Bus. OrderFlowSnapshot for strategy queries.
- **UI:** Watchlist gains flow quality dot (green/yellow/red). Trade Detail Panel gains L2 depth heatmap + entry flow snapshot.
- **Deferred:** L3, iceberg/spoofing detection → Sprint 28.
- **Tests:** ~60 new.

#### Sprint 25 — Setup Quality Engine + Dynamic Position Sizer (DEC-163)
**Target:** ~3–4 days
**Scope:**
- **SetupQualityEngine** (`argus/intelligence/quality_engine.py`): Composite 0–100 scoring from 6 weighted inputs. Configurable weights via YAML.
- **DynamicPositionSizer** (`argus/intelligence/position_sizer.py`): Grade → risk tier → share count. A+=2–3%, B=0.5–0.75%, C-=SKIP. Replaces fixed risk_per_trade_pct. Risk Manager limits still enforced.
- SignalEvent enrichment: quality_score, quality_grade, risk_tier fields.
- Quality History DB table for Learning Loop.
- **UI:** Dashboard gains quality distribution mini-card. Watchlist/positions/trade log gain quality grade badges. Trade Detail gains radar chart + "Why this size?" breakdown. Performance gains "by quality grade" chart.
- **Tests:** ~100 new.

#### Sprint 26 — Red-to-Green + Pattern Library Foundation (DEC-163, DEC-167)
**Target:** ~2 days
- RedToGreenStrategy through Incubator stages 1–3.
- PatternLibrary ABC interface. Bull Flag + Flat-Top Breakout modules.
- Pattern modules feed "pattern strength" to Quality Engine.
- **7 strategies/patterns active.** Tests: ~80 new.

#### Sprint 27 — Pattern Expansion I (DEC-167)
**Target:** ~2–3 days
- Dip-and-Rip, HOD Break, Pre-Market High Break, Gap-and-Go modules. Each stages 1–3.
- **11 strategies/patterns active.** Tests: ~60 new.

#### Sprint 28 — Order Flow V2 + Short Selling (DEC-166)
**Target:** ~2–3 days
- Databento L3 integration. Iceberg/spoofing/absorption detection.
- Short selling infrastructure. Parabolic Short module.
- **12 strategies/patterns active.** Tests: ~80 new.

#### Sprint 29 — Pattern Expansion II (DEC-167)
**Target:** ~2–3 days
- ABCD Reversal, Sympathy Play, Power Hour Reversal, Earnings Gap Continuation modules.
- **16 strategies/patterns active.** Tests: ~60 new.

#### Sprint 30 — Learning Loop V1 (DEC-163)
**Target:** ~2–3 days
- LearningDatabase, PostTradeAnalyzer, weekly batch retraining, quality calibration.
- **UI:** Performance gains calibration chart. Dashboard gains weekly insight card. System gains Learning Loop health.
- Tests: ~60 new.

#### Sprint 31 — Orchestrator V2 AI-Enhanced (DEC-163)
**Target:** ~2–3 days
- Intraday dynamic allocation. AI allocation advisor. Correlation-aware allocation. Quality-weighted replaces equal-weight. Opportunity cost tracking.
- Tests: ~60 new.

#### Sprint 32 — Pattern Expansion III + Volume Profile (DEC-163)
**Target:** ~2–3 days
- Volume Shelf Bounce, Micro Float Runner modules. Volume Profile (VPOC/value area).
- **18 strategies/patterns — full V1 library.** Tests: ~60 new.

#### Sprint 33+ — Optimization & Expansion (Backlog)
- Learning Loop V2 (ML — LightGBM). Advanced Regime Engine. Crypto expansion via IBKR. Monte Carlo simulation. Tax optimization. Strategy breeding.

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