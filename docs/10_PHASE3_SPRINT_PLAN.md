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
2. ⬜ Sprint 12: DatabentoDataService adapter built → resume paper trading with quality data
3. ⬜ Sprint 13: IBKRBroker adapter built → migrate paper trading to IBKR
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

### Build Track Queue

Sprints below are ordered by priority but can be resequenced based on what
the Validation Track needs most. Estimates assume the demonstrated ~1 day
per sprint velocity.

#### Sprint 12 — DatabentoDataService Adapter
**Target:** ~2–3 days
**Scope:**
- `DatabentoDataService` implementing the DataService abstraction
- Uses `databento` Python client library (official, async)
- Subscribes to OHLCV-1m bars and trades streams → publishes CandleEvents and TickEvents
- Full-universe subscription (no symbol limits) with strategy-specific filtering
- L2 depth integration designed from day one (MBP-10 schema), activated when a strategy requires it
- Single live session, Event Bus fan-out to all consumers
- Session management with reconnection logic and exponential backoff
- Circuit-breaker: halt new trades if data stream fails (RSK-021 mitigation)
- Historical data interface: on-demand queries to Databento historical API → Parquet cache (DEC-085)
- DataFetcher gains Databento backend alongside existing Alpaca backend
- Comprehensive test suite matching existing DataService test patterns
- **Databento subscription activated at end of sprint for integration testing (DEC-087)**

**Unblocks:** Paper trading resumes with institutional-grade data quality.

#### Sprint 13 — IBKRBroker Adapter + IB Gateway Integration
**Target:** ~3–5 days
**Scope:**
- `IBKRBroker` implementing the Broker abstraction via `ib_async` library
- IB Gateway connection/reconnection with keep-alive logic (Docker containerized)
- Order submission: map ARGUS order types to IBKR order types (market, limit, full bracket)
- Fill streaming: subscribe to order status events via `ib_async` event system
- Account queries: position, buying power, open order retrieval
- Error handling: map IBKR error codes to ARGUS error events
- State reconstruction: query IBKR for open positions/orders at startup
- Comprehensive test suite comparable to AlpacaBroker (~80 tests)
- **Requires IBKR account (paper trading sufficient) — begin application immediately**

**Unblocks:** Paper trading migrates to IBKR. Path to live trading on production platform.

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

#### Sprint 16 — Command Center: Multi-Surface Delivery + Paper Trading Features
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

**Deliverable:** After Sprint 16, the Command Center is accessible as:
1. Web app (any browser, any device)
2. Desktop app (Tauri, macOS/Windows/Linux — system tray, native notifications)
3. Mobile app (PWA on iPhone/iPad — home screen icon, no Safari chrome)

#### Sprint 17 — Orchestrator Framework
**Target:** ~1-2 days
**Scope:**
- Orchestrator core: pre-market routine, regime classification, capital allocation
- Market Regime Classification V1 (SPY MAs, VIX, breadth, momentum)
- Capital allocation engine (rules-based V1)
- Performance-based throttling (consecutive losses, Sharpe decay, drawdown)
- Strategy activation/deactivation based on regime
- AllocationUpdateEvent, StrategyActivatedEvent, StrategySuspendedEvent on Event Bus
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

#### Sprint 19 — Tier 1 News Integration
**Target:** ~1 day
**Scope:**
- Economic calendar ingestion (FOMC, NFP, CPI, GDP, Fed speeches)
- Earnings calendar (flag scanner candidates with pending earnings)
- Risk Manager event-day filters (reduce positions on FOMC days, etc.)
- Scanner metadata enrichment ("AAPL reports earnings after close")
- CatalystEvent on Event Bus

#### Sprint 20 — AI Layer MVP
**Target:** ~1-2 days
**Scope:**
- Claude API integration (claude_service.py)
- System Context Builder (assembles current state for Claude)
- Automated end-of-day report generation
- Paper trading analysis: Claude reviews daily/weekly performance
- Basic approval workflow (Claude proposes → user approves in Command Center)
- Claude chat endpoint in API + chat view in Command Center

#### Sprint 21 — Command Center: Strategy Lab + Controls
**Target:** ~1 day
**Scope:**
- Strategy Lab: incubator pipeline visualization, per-strategy detail
- Live Monitor: real-time position view with streaming P&L, price charts
- Risk Dashboard: utilization at all three levels, sector exposure heat map
- Approval Queue: pending approvals from Claude/Orchestrator
- Autonomy settings configuration

#### Sprint 22+ — Additional Strategies, Expansion
**Scope (prioritized backlog):**
- VWAP Reclaim strategy (through full incubator pipeline)
- Red-to-Green strategy
- Afternoon Momentum strategy
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