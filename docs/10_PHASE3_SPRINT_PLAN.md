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

### Paper Trading — System Stability (ACTIVE on Alpaca IEX)
- **Parameters:** DEC-076 (or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0)
- **Account:** Alpaca paper ($100K simulated)
- **Data:** Alpaca IEX feed (~2–3% market volume — validates system stability only, not signal accuracy)
- **Status:** Running. Continues until Sprint 12 delivers Databento data. Signal accuracy validation requires Databento.
- **Guide:** `docs/08_PAPER_TRADING_GUIDE.md`

### Paper Trading — Signal Validation (PENDING Sprints 12–13)
- **Parameters:** DEC-076 (same)
- **Data:** Databento US Equities Standard (institutional-grade, full market volume)
- **Execution:** IBKR paper trading account
- **Status:** Begins after Sprint 12 (DatabentoDataService) and Sprint 13 (IBKRBroker) complete. This is the meaningful validation phase — system stability + signal accuracy + execution quality.
- **Duration:** Flexible — user decides when confidence is sufficient.

#### Validation Sequence
1. ✅ Extended backtest complete (Sprint 11, WFE 0.56, OOS Sharpe +0.34)
2. ✅ Sprint 12: DatabentoDataService adapter built (Feb 21). Databento subscription activation deferred until Sprint 13 complete + IBKR approved (DEC-087).
3. ✅ Sprint 13: IBKRBroker adapter built (Feb 22, 811 tests). Config-driven broker selection. Native bracket orders (DEC-093). T2 broker-side limit support. State reconstruction.
4. ⬜ IBKR paper trading: minimum 2 weeks with DEC-076 parameters
5. ⬜ User satisfied with system stability and strategy performance
6. ⬜ No kill criteria triggered
7. ⬜ CPA consultation on capital/risk/tax implications (DEF-004)
8. ⬜ Explicit go/no-go decision by user → live trading on IBKR at minimum size

#### Ramp Schedule (Advisory)
| Stage | Position Size | Purpose |
|-------|--------------|---------|
| Initial | 10 shares/trade | Verify fills, slippage, system stability |
| Intermediate | 25 shares/trade | Increased size, still minimal risk |
| Full | Model-calculated | Transition to algorithmic sizing |

#### Kill Criteria (Hard Stops)
1. Account drawdown exceeds 15%
2. Profit Factor below 0.7 after 50+ trades
3. Win rate below 25% over any 30-trade window
4. System errors: missed fills, orphaned orders, position tracking discrepancies
5. Zero trades for 5 consecutive trading days when gap candidates exist

#### Monitoring Checklist
- Target hit rate (backtest showed 0% — does this persist?)
- Time stop profitability (net P&L of time-stopped trades)
- Slippage vs. backtest assumption ($0.01/share)
- Trade frequency (~12–14 trades/month expected)
- Monthly P&L pattern (seasonal sensitivity)
- System uptime and health alerts
- Databento data quality (compare candles vs external reference)
- IBKR fill quality (compare vs Alpaca paper fills)

### Live Trading (FUTURE)
- ORB at minimum position size with real capital on IBKR
- Shadow system (paper) runs in parallel
- Minimum 20 trading days before scaling
- Compare live vs. paper vs. backtest expectations

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
**Next:** Sprint 14 (Command Center API).

#### Sprint 14 — Command Center: API Layer + Project Scaffolding
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

#### Sprint 15 — Command Center: Core Dashboard Views
**Target:** ~1 day
**Scope:**
- Overview dashboard: account equity, daily P&L, open positions, recent trades, system health
- Trade log with filtering (by date, strategy, outcome)
- Performance view: equity curve, daily/weekly P&L, win rate, Sharpe over time
- System health panel: heartbeat, last data received, alerts
- Real-time updates via WebSocket (positions, P&L, new trades)
- Charts: Recharts for performance metrics
- **Responsive design from day one** — mobile-first CSS via Tailwind breakpoints
  (DEC-080: same views must work on iPhone/iPad in Safari)

#### Sprint 16 — Command Center: Multi-Surface Delivery (grouped with CC sprints — DEC-096)
**Target:** ~1 day
**Scope:**
- **PWA configuration:** manifest.json, service worker, app icons, "Add to Home Screen"
  support for iOS/iPad (DEC-080). Push notification registration.
- **Tauri desktop shell:** Wrap existing React app in Tauri v2. System tray icon with
  status indicator (green/yellow/red), native OS notifications, auto-launch on startup.
  Minimal Rust — just the shell config, no custom backend logic.
- **Paper trading features:** Backtest vs. paper comparison view (overlay expected vs. actual),
  trade drill-down with entry/exit rationale, alert history, controls (emergency pause/resume,
  manual position close), walk-forward results alongside live performance.
- **Export:** CSV trade log download.

#### Sprint 17 — Orchestrator V1 (DEC-096)
**Target:** ~1-2 days
**Scope:**
- Orchestrator core: pre-market routine, regime classification, capital allocation
- Market Regime Classification V1 (SPY MAs, VIX, breadth, momentum)
- Capital allocation engine (rules-based V1)
- Performance-based throttling (consecutive losses, Sharpe decay, drawdown)
- Strategy activation/deactivation based on regime
- AllocationUpdateEvent, StrategyActivatedEvent, StrategySuspendedEvent on Event Bus
- Command Center integration: strategy deploy/pause/stop controls, allocation display
- DEF-016 re-evaluation: atomic bracket submission via `broker.place_bracket_order()` in Order Manager. Natural fit — Orchestrator restructures signal→Order Manager flow.
- Comprehensive test suite

#### Sprint 18 — ORB Scalp Strategy
**Target:** ~1-2 days
**Scope:**
- ORB Scalp strategy implementation (faster variant: 0.3-0.5R quick targets)
- Strategy spec sheet (04_STRATEGY_TEMPLATE.md filled in)
- VectorBT parameter sweep for ORB Scalp
- Walk-forward validation
- Cross-strategy risk integration (ORB + ORB Scalp same-stock prevention)
- Paper trading deployment alongside ORB

**Deliverable:** After Sprint 18, the Command Center is accessible as:
1. Web app (any browser, any device)
2. Desktop app (Tauri, macOS/Windows/Linux — system tray, native notifications)
3. Mobile app (PWA on iPhone/iPad — home screen icon, no Safari chrome)

**Note:** Databento subscription activation recommended around Sprint 19 (DEC-097).

#### Sprint 19 — VWAP Reclaim Strategy (NEW — DEC-096)
**Target:** ~1-2 days
**Scope:**
- VWAP Reclaim strategy implementation (mean-reversion, 10:00 AM–12:00 PM, 5–30 min holds)
- Strategy spec sheet (04_STRATEGY_TEMPLATE.md filled in)
- VectorBT parameter sweep (requires Databento historical data for quality validation)
- Walk-forward validation
- Cross-strategy risk integration (ORB + ORB Scalp + VWAP Reclaim same-stock prevention)
- Orchestrator capital allocation for three strategies
- Paper trading deployment

#### Sprint 20 — Afternoon Momentum Strategy (NEW — DEC-096)
**Target:** ~1-2 days
**Scope:**
- Afternoon Momentum strategy implementation (consolidation breakout, 2:00–3:30 PM, 15–60 min holds)
- Strategy spec sheet (04_STRATEGY_TEMPLATE.md filled in)
- VectorBT parameter sweep
- Walk-forward validation
- Cross-strategy risk integration (four strategies, full-day coverage)
- Orchestrator capital allocation for four strategies
- Paper trading deployment
- **Milestone:** ARGUS now covers 9:30 AM–3:30 PM with four uncorrelated signal types.

#### Sprint 21 — Command Center: Analytics & Strategy Lab (NEW — DEC-096)
**Target:** ~1-2 days
**Scope:**
- Strategy Lab: incubator pipeline visualization, per-strategy detail views
- Strategy correlation matrix (how do strategies move relative to each other?)
- Regime performance heatmaps (which strategies excel in which market conditions?)
- Trade journal with annotation support (user notes per trade)
- Side-by-side strategy comparison views
- Drawdown analysis and recovery time tracking
- Calendar P&L view (daily/weekly/monthly grid with color coding)
- Risk Dashboard: utilization at all three levels, sector exposure heat map
- Approval Queue: pending approvals from Orchestrator
- **Milestone:** Operator has full analytical toolkit for building conviction before live capital.

#### Sprint 22 — AI Layer MVP (DEC-096, DEC-098)
**Target:** ~1-2 days
**Scope:**
- Anthropic API integration (`argus/ai/claude_service.py`)
- Model: Claude Opus for all calls (DEC-098). Prompt caching for system context.
- System Context Builder: assembles current state (positions, regime, strategy metrics) for Claude
- Pre-market briefing: overnight analysis, regime assessment, allocation recommendations
- Post-trade analysis: real-time trade evaluation with context (ATR, volume, regime, historical comparison)
- Anomaly detection: periodic system/market checks during trading hours
- Weekly/monthly strategy performance reviews with narrative reports
- Approval workflow: Claude proposes parameter/allocation changes → user approves in Command Center
- Natural language chat endpoint in API + chat view in Command Center
- API key stored in encrypted secrets manager (existing architectural rule)

#### Sprint 23+ — Additional Features (Backlog)
**Scope (prioritized):**
- Tier 1 News Integration (economic/earnings calendar, event-day risk filters)
- Red-to-Green strategy (through full incubator pipeline)
- Tier 2 News (news feed + classification via IQFeed/Benzinga)
- Accounting module (tax tracking, wash sales, P&L reports)
- Learning Journal
- Tier 3 News (Claude sentiment analysis)
- Multi-asset: crypto via IBKR
- IQFeedDataService adapter (when forex or Tier 2 news needed)

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