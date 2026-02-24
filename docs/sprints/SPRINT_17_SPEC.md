# Sprint 17 — Orchestrator V1 + DEF-016 Bracket Refactor

## Implementation Specification for Claude Code

> **Sprint:** 17 | **Target:** ~13 sessions | **Starting tests:** 942 | **Target tests:** ~1,100+
> **Date:** February 24, 2026
> **Prerequisite:** Sprint 16 complete (942 tests), all passing, ruff clean

---

## Design Decisions Made (to be logged as DEC entries)

### DEC-113: Regime Classification V1 Data Source
- **Decision:** Fetch SPY daily bars via REST at pre-market time through DataService. Use SPY 20-day realized volatility as VIX proxy. Skip breadth (advance/decline) in V1.
- **Rationale:** SPY is a market barometer, not a traded symbol — shouldn't pollute the real-time data stream. Daily bars are sufficient for MA, momentum, and volatility computation. Alpaca REST provides reliable daily bars (IEX accuracy issues only affect intraday data). VIX requires a separate CBOE dataset subscription even on Databento. Breadth requires IQFeed ($160–250/mo) — not justified for V1 with one strategy. Architecture supports adding real VIX and breadth later with zero Orchestrator code changes.

### DEC-114: Orchestrator Allocation Method — Equal Weight V1
- **Decision:** Equal-weight allocation for V1. `allocation_method: "equal_weight"` in config. Performance-weighted allocation deferred to post-Sprint 21 when sufficient multi-strategy trade data exists.
- **Rationale:** Performance-weighted allocation requires statistically meaningful trade history across multiple strategies. With one strategy and limited paper trading, the data doesn't exist yet. The allocation engine interface supports future methods via config-driven dispatch.
- **Future:** `performance_weighted` method (±10% shift based on trailing 20-day Sharpe/profit factor, per Bible Section 5.2), Kelly criterion, ML-based allocation. Tracked as DEF-017.

### DEC-115: Continuous Regime Monitoring
- **Decision:** Orchestrator re-evaluates market regime every 30 minutes during market hours (configurable). If regime shifts, Orchestrator adjusts strategy activation immediately (prevents new signals, does not flatten existing positions).
- **Rationale:** Surprise market events (Fed announcements, tariff news, flash crashes) can invalidate the morning's regime classification. Without intraday re-evaluation, strategies continue trading in conditions they're not designed for. The RegimeClassifier is already callable on-demand; adding periodic re-evaluation is minimal scope.

### DEC-116: Strategy Correlation Tracker — Infrastructure Now, Allocation Later
- **Decision:** Build `CorrelationTracker` class that records daily P&L per strategy and computes pairwise correlation matrix. Wire it into the allocation engine as an optional modifier. Correlation-adjusted allocation is not active in V1 — tracker collects data silently. Can be seeded from backtested returns when Sprints 18–20 produce strategy backtests.
- **Rationale:** 4 strategies coming online within the week (Sprints 18–20). Correlation computation requires 20–30 days of parallel daily returns — infrastructure must exist before data accumulates. Backtested returns can bootstrap initial estimates. Correlation-adjusted allocation activates when sufficient data exists (configurable minimum days threshold).
- **Future:** Active correlation-adjusted allocation when `min_correlation_days` threshold is met. Tracked as part of DEF-017.

### DEC-117: DEF-016 Resolution — Atomic Bracket Orders in Order Manager
- **Decision:** Refactor Order Manager to use `place_bracket_order()` for entry+stop+T1+T2 submission. All three broker implementations already support `place_bracket_order()`. The refactor is scoped to Order Manager's `on_approved()` and `_handle_entry_fill()` methods plus test updates.
- **Rationale:** Eliminates the unprotected window between entry fill and stop/target placement. For a system managing family income, "near-zero risk" is not the right standard — zero risk is. SimulatedBroker already has working `place_bracket_order()`. IBKRBroker uses native IBKR bracket linkage. AlpacaBroker supports single-target brackets (acceptable for incubator use).

### DEC-118: Pre-Market Scheduling — Self-Contained Poll Loop
- **Decision:** Orchestrator runs its own background polling loop (like Order Manager's fallback poll). Checks clock every 30 seconds. Fires pre-market routine at configured time (default 9:25 AM ET), regime re-evaluation every N minutes during market hours, and EOD review at configured time (default 4:05 PM ET). No APScheduler dependency.
- **Rationale:** Consistent with Order Manager's time-based trigger pattern. Self-contained, no new dependencies. Handles mid-day restarts gracefully (detects market hours, runs abbreviated pre-market).

---

## Architecture Overview

### New Files

```
argus/core/orchestrator.py          — Main Orchestrator class
argus/core/regime.py                — RegimeClassifier + MarketRegime enum + RegimeIndicators
argus/core/throttle.py              — PerformanceThrottler
argus/core/correlation.py           — CorrelationTracker
tests/core/test_orchestrator.py     — Orchestrator tests
tests/core/test_regime.py           — RegimeClassifier tests
tests/core/test_throttle.py         — PerformanceThrottler tests
tests/core/test_correlation.py      — CorrelationTracker tests
argus/api/routes/orchestrator.py    — API routes for Orchestrator status/decisions/rebalance
tests/api/test_orchestrator.py      — API route tests
```

### Modified Files

```
config/orchestrator.yaml            — Extended config (regime thresholds, schedule, correlation)
argus/core/config.py                — OrchestratorConfig Pydantic model
argus/core/events.py                — Minor: no new events needed (all 4 already defined)
argus/data/service.py               — Add fetch_daily_bars() to DataService ABC
argus/data/alpaca_data_service.py   — Implement fetch_daily_bars() via Alpaca REST
argus/data/databento_data_service.py— Implement fetch_daily_bars() stub (returns None)
argus/data/replay_data_service.py   — Implement fetch_daily_bars() stub (returns None)
argus/backtest/backtest_data_service.py — Implement fetch_daily_bars() stub (returns None)
argus/main.py                       — 12-phase startup, Orchestrator owns strategy lifecycle
argus/api/dependencies.py           — Add orchestrator to AppState
argus/api/server.py                 — Register orchestrator routes
argus/api/websocket/live.py         — Add 4 Orchestrator events to standard_events
argus/api/dev_state.py              — Mock orchestrator data for dev mode
argus/db/manager.py                 — Add orchestrator_decisions table to schema
argus/execution/order_manager.py    — DEF-016: use place_bracket_order()
argus/execution/simulated_broker.py — Minor adjustments if needed for bracket flow
tests/execution/test_order_manager.py — Rewrite entry flow tests for bracket submission
argus/ui/src/                       — UX add-ons (4 features)
```

### Class Hierarchy

```
MarketRegime (Enum)
    BULLISH_TRENDING
    BEARISH_TRENDING
    RANGE_BOUND
    HIGH_VOLATILITY
    CRISIS

RegimeIndicators (dataclass)
    spy_price: float
    spy_sma_20: float | None
    spy_sma_50: float | None
    spy_roc_5d: float | None          # 5-day rate of change
    spy_realized_vol_20d: float | None # VIX proxy
    spy_vs_vwap: float | None          # positive = above VWAP
    timestamp: datetime

ThrottleAction (Enum)
    NONE          — no action needed
    REDUCE        — reduce allocation to minimum
    SUSPEND       — suspend strategy entirely

StrategyAllocation (dataclass)
    strategy_id: str
    allocation_pct: float      # 0.0–1.0
    allocation_dollars: float
    throttle_action: ThrottleAction
    eligible: bool             # passed regime filter
    reason: str                # human-readable explanation

OrchestratorConfig (Pydantic BaseModel)
    # Allocation
    allocation_method: str = "equal_weight"
    max_allocation_pct: float = 0.40
    min_allocation_pct: float = 0.10
    cash_reserve_pct: float = 0.20
    # Throttling
    performance_lookback_days: int = 20
    consecutive_loss_throttle: int = 5
    suspension_sharpe_threshold: float = 0.0
    suspension_drawdown_pct: float = 0.15
    recovery_days_required: int = 10
    # Regime
    regime_check_interval_minutes: int | None = 30  # None = pre-market only
    spy_symbol: str = "SPY"
    vol_low_threshold: float = 0.08    # annualized realized vol
    vol_normal_threshold: float = 0.16
    vol_high_threshold: float = 0.25
    vol_crisis_threshold: float = 0.35
    # Schedule
    pre_market_time: str = "09:25"     # ET
    eod_review_time: str = "16:05"     # ET
    poll_interval_seconds: int = 30
    # Correlation
    correlation_enabled: bool = True
    min_correlation_days: int = 20
    max_combined_correlated_allocation: float = 0.60  # max for highly correlated pair

RegimeClassifier
    classify(indicators: RegimeIndicators) -> MarketRegime
    compute_indicators(daily_bars: pd.DataFrame) -> RegimeIndicators

PerformanceThrottler
    check(strategy_id, trades, daily_pnl_series) -> ThrottleAction
    get_consecutive_losses(trades) -> int
    get_rolling_sharpe(daily_pnl, lookback_days) -> float
    get_drawdown_from_peak(daily_pnl) -> float

CorrelationTracker
    record_daily_pnl(strategy_id, date, pnl) -> None
    get_correlation_matrix() -> pd.DataFrame | None  # None if insufficient data
    get_pairwise_correlation(strategy_a, strategy_b) -> float | None
    has_sufficient_data() -> bool
    seed_from_backtest(strategy_id, daily_pnl_series) -> None

Orchestrator
    __init__(config, event_bus, clock, trade_logger, broker, data_service)
    start() / stop()
    register_strategy(strategy) / get_strategies() / get_strategy(id)
    run_pre_market() — full daily routine
    classify_regime() -> MarketRegime
    calculate_allocations() -> dict[str, StrategyAllocation]
    check_throttling(strategy_id) -> ThrottleAction
    run_end_of_day()
    manual_rebalance() — API-triggered
    current_regime -> MarketRegime (property)
    current_allocations -> dict[str, StrategyAllocation] (property)
    _on_position_closed(event) — intraday throttle check
    _poll_loop() — background task for scheduling
    _run_regime_recheck() — intraday regime re-evaluation
```

### Data Flow

```
Pre-Market (9:25 AM ET):
  Orchestrator.run_pre_market()
  ├── DataService.fetch_daily_bars("SPY", 60) → pd.DataFrame
  ├── RegimeClassifier.compute_indicators(bars) → RegimeIndicators
  ├── RegimeClassifier.classify(indicators) → MarketRegime
  ├── For each registered strategy:
  │   ├── strategy.get_market_conditions_filter() → check allowed_regimes
  │   ├── PerformanceThrottler.check(strategy_id, ...) → ThrottleAction
  │   └── Calculate allocation percentage
  ├── CorrelationTracker.get_correlation_matrix() → adjust if available
  ├── Apply allocations: strategy.allocated_capital = X, strategy.is_active = Y
  ├── Publish events: RegimeChangeEvent, AllocationUpdateEvent, Activated/Suspended
  └── Log decisions to orchestrator_decisions table

During Market Hours (every 30 min):
  Orchestrator._run_regime_recheck()
  ├── DataService.fetch_daily_bars("SPY", 60) → fresh daily bars
  ├── RegimeClassifier.classify() → new regime
  ├── If regime changed:
  │   ├── Re-evaluate strategy eligibility
  │   ├── Deactivate newly ineligible strategies (is_active = False)
  │   ├── Publish RegimeChangeEvent + StrategySuspendedEvent
  │   └── Log decision
  └── If regime unchanged: no-op

On PositionClosedEvent (intraday):
  Orchestrator._on_position_closed()
  ├── Update intraday loss tracking for the strategy
  ├── Check consecutive loss threshold
  ├── If throttle triggered:
  │   ├── strategy.is_active = False (no new signals)
  │   ├── Existing positions play out (stops still active)
  │   ├── Publish StrategySuspendedEvent
  │   └── Log decision

End of Day (4:05 PM ET):
  Orchestrator.run_end_of_day()
  ├── Compute final daily metrics per strategy
  ├── CorrelationTracker.record_daily_pnl() for each strategy
  ├── Log summary to orchestrator_decisions table
  └── Publish summary event (consumed by future AI Layer)
```

### main.py Startup Sequence (12 Phases)

```
Phase  1: Foundation      (Config, Clock, EventBus)              — unchanged
Phase  2: Database        (DatabaseManager, TradeLogger)         — add orchestrator_decisions table
Phase  3: Broker          (IBKR/Alpaca/Simulated)               — unchanged
Phase  4: Health Monitor                                         — unchanged
Phase  5: Risk Manager                                           — unchanged
Phase  6: Data Service    (Databento/Alpaca)                     — unchanged
Phase  7: Scanner                                                — unchanged
Phase  8: Strategies      (create instances, register with Orchestrator, do NOT activate)  — CHANGED
Phase  9: Orchestrator    (create, register strategies, run pre-market) — NEW
Phase 10: Order Manager                                          — unchanged (but uses bracket orders)
Phase 11: Start Streaming                                        — unchanged
Phase 12: API Server      (was Phase 11)                         — add orchestrator to AppState
```

### API Endpoints

```
GET  /api/v1/orchestrator/status
  Response: {
    regime: "bullish_trending",
    regime_indicators: { spy_price, spy_sma_20, spy_sma_50, ... },
    regime_updated_at: "2026-02-24T14:25:00Z",
    allocations: [
      { strategy_id, allocation_pct, allocation_dollars, throttle_action, eligible, reason }
    ],
    cash_reserve_pct: 0.20,
    total_deployed_pct: 0.40,
    next_regime_check: "2026-02-24T15:00:00Z"
  }

GET  /api/v1/orchestrator/decisions?limit=50&offset=0
  Response: {
    decisions: [
      { id, date, decision_type, strategy_id, details, rationale, created_at }
    ],
    total: 127
  }

POST /api/v1/controls/orchestrator/rebalance
  Response: {
    success: true,
    message: "Rebalance completed",
    new_regime: "bullish_trending",
    allocations: [...]
  }
```

### Database Schema Addition

```sql
-- Already defined in Architecture doc, just needs implementation in DatabaseManager
CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    strategy_id TEXT,
    details TEXT,
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### DEF-016: Order Manager Bracket Refactor

**Current flow (sequential):**
```
on_approved() → place_order(entry) → wait for fill →
_handle_entry_fill() → place_order(stop) + place_order(t1) + place_order(t2)
```

**New flow (atomic bracket):**
```
on_approved() → construct entry+stop+t1+t2 → place_bracket_order(entry, stop, [t1, t2]) →
_handle_entry_fill() → ManagedPosition created with stop/t1/t2 order IDs already set
```

**Key changes:**
1. `on_approved()`: Build all orders (entry, stop, T1, T2) from signal data. Call `place_bracket_order()`.
2. Track bracket order IDs from `BracketOrderResult` in pending orders.
3. `_handle_entry_fill()`: Create ManagedPosition with pre-set stop/T1/T2 order IDs. Do NOT submit separate stop/T1/T2 orders.
4. `_submit_stop_order()`, `_submit_t1_order()`, `_submit_t2_order()` still used for mid-position modifications (e.g., stop-to-breakeven after T1 fill) — only the initial submission changes.
5. SimulatedBroker sync fill handling: `place_bracket_order()` returns entry as FILLED + stop/targets as PENDING. The `on_approved()` method detects the sync fill and calls `on_fill()` same as current code.

**Test changes:** ~15–20 tests in `test_order_manager.py` that mock `place_order()` for entry submission need to mock `place_bracket_order()` instead. Fill handling tests (T1, stop, flatten) should be largely unchanged since those still go through the same handlers.

---

## Session Breakdown

### Session 1: Config + Models + DB Schema (~15 tests)

**New files:**
- `argus/core/regime.py` — `MarketRegime` enum, `RegimeIndicators` dataclass
- `argus/core/throttle.py` — `ThrottleAction` enum, `StrategyAllocation` dataclass
- `argus/core/correlation.py` — `CorrelationTracker` class (data recording + matrix computation)
- `tests/core/test_correlation.py`

**Modified files:**
- `argus/core/config.py` — Add `OrchestratorConfig` Pydantic model
- `config/orchestrator.yaml` — Extend with regime, schedule, correlation config
- `argus/db/manager.py` — Add `orchestrator_decisions` table creation to `initialize()`

**Tests:** OrchestratorConfig validation (required fields, defaults, edge cases), MarketRegime enum values, CorrelationTracker (record, compute, seed, insufficient data), DB table creation.

### Session 2: RegimeClassifier (~20 tests)

**New files:**
- Complete `argus/core/regime.py` — Add `RegimeClassifier` class
- `tests/core/test_regime.py`

**Logic:**
- `compute_indicators(daily_bars: pd.DataFrame) -> RegimeIndicators`: Compute SMAs, ROC, realized vol, VWAP from raw bars
- `classify(indicators: RegimeIndicators) -> MarketRegime`: Rules-based scoring
  - Trend score: SPY vs SMA-20/50 → +1 bullish, -1 bearish, 0 neutral
  - Volatility bucket: realized vol → Low/Normal/High/Crisis
  - Momentum: 5-day ROC → confirms or contradicts trend
  - Combined: majority voting with tie-break toward caution

**Tests:** Each indicator computation, each regime category, missing indicators (graceful degradation), edge cases (SPY exactly at SMA), volatility threshold boundaries.

### Session 3: PerformanceThrottler (~20 tests)

**New files:**
- Complete `argus/core/throttle.py` — Add `PerformanceThrottler` class
- `tests/core/test_throttle.py`

**Logic:**
- `check(strategy_id, trades, config) -> ThrottleAction`:
  - Count consecutive losses from trade sequence (most recent first)
  - Compute 20-day rolling Sharpe from daily P&L
  - Compute drawdown from equity peak
  - Return worst action: SUSPEND > REDUCE > NONE
- `get_consecutive_losses()`: Walk trades newest-first, count losses until a win
- `get_rolling_sharpe()`: Use existing `compute_sharpe_ratio()` from `analytics/performance.py`
- `get_drawdown_from_peak()`: Running max equity minus current equity, as percentage

**Tests:** 0/1/4/5/6 consecutive losses, Sharpe exactly at 0, Sharpe positive/negative, drawdown at threshold, multiple triggers (return worst), empty trade list, single trade.

### Session 4: Orchestrator Core (~25 tests)

**New files:**
- `argus/core/orchestrator.py` — Full Orchestrator class
- `tests/core/test_orchestrator.py`

**Logic:**
- Constructor takes config, event_bus, clock, trade_logger, broker, data_service
- `register_strategy()` / `get_strategies()` — strategy registry dict
- `run_pre_market()`:
  1. Fetch SPY bars via `data_service.fetch_daily_bars()`
  2. Classify regime via `RegimeClassifier`
  3. Filter strategies by `strategy.get_market_conditions_filter().allowed_regimes`
  4. Check throttling per strategy via `PerformanceThrottler`
  5. Calculate allocations (equal weight among eligible, non-throttled)
  6. Apply: set `strategy.allocated_capital` and `strategy.is_active`
  7. Publish events: `RegimeChangeEvent`, `AllocationUpdateEvent`, `StrategyActivated/SuspendedEvent`
  8. Log decisions to DB via TradeLogger/DatabaseManager
- `calculate_allocations()`:
  - Deployable = total_equity * (1 - cash_reserve_pct)
  - Per-strategy = deployable / N_eligible (equal weight)
  - Cap at max_allocation_pct * total_equity
  - Throttled strategies get min_allocation_pct * total_equity
  - Check CorrelationTracker if available (adjust combined allocation for correlated pairs)
- `manual_rebalance()` — calls `calculate_allocations()` + applies + publishes

**Tests:** Registration, pre-market with single strategy, pre-market with multiple strategies, regime filtering (strategy excluded), throttling (reduce, suspend), allocation math (verify percentages), allocation caps, cash reserve enforcement, event publishing verification, decision logging, SPY data unavailable (fallback to previous regime).

### Session 5: DataService.fetch_daily_bars() (~10 tests)

**Modified files:**
- `argus/data/service.py` — Add abstract `fetch_daily_bars()` method
- `argus/data/alpaca_data_service.py` — Implement via Alpaca REST bars API
- `argus/data/databento_data_service.py` — Return None (subscription not active)
- `argus/data/replay_data_service.py` — Return None
- `argus/backtest/backtest_data_service.py` — Return None

**AlpacaDataService implementation:**
```python
async def fetch_daily_bars(self, symbol: str, lookback_days: int = 60) -> pd.DataFrame | None:
    """Fetch daily OHLCV bars via Alpaca REST API."""
    # Use self._rest_client (alpaca-py) to fetch bars
    # Convert to DataFrame with columns: timestamp, open, high, low, close, volume
    # Handle errors gracefully — return None on failure
```

**Tests:** AlpacaDataService fetch_daily_bars with mocked REST response, empty response, API error, other DataService stubs return None.

### Session 6: Intraday Monitoring + Regime Re-eval + EOD + Poll Loop (~15 tests)

**Modified files:**
- `argus/core/orchestrator.py` — Add `_poll_loop()`, `_run_regime_recheck()`, `_on_position_closed()`, `run_end_of_day()`

**Logic:**
- `start()`: Subscribe to `PositionClosedEvent`. Launch `_poll_loop()` as background task.
- `_poll_loop()`: Every 30s, check clock:
  - If pre-market time and haven't run today → `run_pre_market()`
  - If market hours and regime check interval elapsed → `_run_regime_recheck()`
  - If EOD time and haven't run today → `run_end_of_day()`
- `_run_regime_recheck()`: Fetch fresh SPY data → classify → if changed, re-evaluate eligibility → deactivate ineligible → publish events
- `_on_position_closed(event)`: Track consecutive losses intraday. If threshold hit, suspend strategy immediately.
- `run_end_of_day()`: Compute final metrics, record to CorrelationTracker, log decisions.
- `stop()`: Cancel poll task, unsubscribe from events.

**Tests:** Poll loop triggers pre-market at correct time, regime re-check at interval, regime change mid-day triggers deactivation, position closed triggers throttle check, EOD review records metrics, mid-day restart (detects market hours, runs abbreviated pre-market), graceful shutdown.

### Session 7: main.py Integration (~10 tests)

**Modified files:**
- `argus/main.py` — 12-phase startup, Orchestrator owns strategy lifecycle

**Changes:**
- Phase 8: Create strategy instances but don't activate (`is_active=False`, `allocated_capital=0`)
- Phase 9 (NEW): Create Orchestrator, register strategies, run pre-market routine
- Phase 12: Add orchestrator to AppState
- Move `_reconstruct_strategy_state()` into Orchestrator (called during pre-market if mid-day restart)
- Change component count from `[1/11]` to `[1/12]` throughout

**Tests:** Integration test verifying 12-phase startup completes, strategy activated by Orchestrator (not hardcoded), Orchestrator in AppState.

### Session 8: API Endpoints + WebSocket + Dev Mode (~12 tests)

**New files:**
- `argus/api/routes/orchestrator.py` — Three endpoints
- `tests/api/test_orchestrator.py`

**Modified files:**
- `argus/api/server.py` — Register orchestrator router
- `argus/api/dependencies.py` — Add `orchestrator: Orchestrator | None = None` to AppState
- `argus/api/websocket/live.py` — Add `RegimeChangeEvent`, `AllocationUpdateEvent`, `StrategyActivatedEvent`, `StrategySuspendedEvent` to `standard_events`
- `argus/api/dev_state.py` — Add mock orchestrator data (regime, allocations, decisions)

**Tests:** GET status (regime, allocations), GET decisions (pagination), POST rebalance, auth required on all, WebSocket forwards new events.

### Session 9: DEF-016 Part 1 — SimulatedBroker Verification + Order Manager Refactor (~15 tests)

**Modified files:**
- `argus/execution/order_manager.py` — Refactor `on_approved()` and `_handle_entry_fill()`
- `argus/execution/simulated_broker.py` — Verify/adjust `place_bracket_order()` compatibility

**Changes to `on_approved()`:**
```python
# OLD: submit entry only, wait for fill, then submit stop/targets in _handle_entry_fill
entry_order = Order(...)
result = await self._broker.place_order(entry_order)

# NEW: construct full bracket, submit atomically
entry_order = Order(strategy_id=..., symbol=..., side=BUY, order_type=MARKET, quantity=...)
stop_order = Order(strategy_id=..., symbol=..., side=SELL, order_type=STOP, quantity=..., stop_price=signal.stop_price)
t1_order = Order(strategy_id=..., symbol=..., side=SELL, order_type=LIMIT, quantity=t1_shares, limit_price=t1_price)
targets = [t1_order]
if t2_price > 0:
    t2_order = Order(strategy_id=..., symbol=..., side=SELL, order_type=LIMIT, quantity=t2_shares, limit_price=t2_price)
    targets.append(t2_order)
bracket_result = await self._broker.place_bracket_order(entry_order, stop_order, targets)
```

**Changes to `_handle_entry_fill()`:**
- Remove `_submit_stop_order()`, `_submit_t1_order()`, `_submit_t2_order()` calls
- Set `position.stop_order_id`, `position.t1_order_id`, `position.t2_order_id` from bracket result IDs stored in pending order
- These methods still exist for mid-position modifications (stop-to-breakeven, etc.)

**Tests:** Entry via bracket submission (verify place_bracket_order called, not place_order), sync fill handling (SimulatedBroker), bracket rejection (entry rejected → no stops submitted), bracket with T1 only, bracket with T1+T2, existing T1/stop/flatten fill tests still pass.

### Session 10: DEF-016 Part 2 — Test Rewrite + Integration Verification (~10 tests)

**Modified files:**
- `tests/execution/test_order_manager.py` — Update mocks for bracket flow
- Run full test suite: `python -m pytest tests/ -x`

**Focus:**
- Ensure all 33 existing Order Manager tests pass (with updated mocks)
- Ensure all integration tests pass (they use SimulatedBroker which has working bracket orders)
- Add new tests specific to bracket edge cases: partial fill on entry (bracket cancellation), order cancellation cascading, bracket order tracking in pending orders

### Session 11: UX — Segmented Controls + Badge System (~0 backend tests)

**New/modified frontend files:**
- `argus/ui/src/components/SegmentedTab.tsx` — Reusable segmented control component
- `argus/ui/src/components/Badge.tsx` — Extended badge variants
- Apply SegmentedTab to Dashboard (Open/Closed positions), Trade Log (Wins/Losses/BE), System (Healthy/Degraded/Down)
- Add strategy badges (ORB=blue), regime badges (Bullish=green, Range-Bound=yellow, etc.), risk level badges

**Design specs:**
- SegmentedTab: rounded-pill segments, active segment highlighted, count badge inside each, Framer Motion layout animation on switch
- Badge variants: `strategy` (colored by strategy name), `regime` (colored by market condition), `risk` (green/yellow/red gradient)
- Touch targets ≥44px on mobile
- Match Sprint 16 dark theme and animation quality

### Session 12: UX — Allocation Donut + Risk Gauge (~0 backend tests)

**New/modified frontend files:**
- `argus/ui/src/components/AllocationDonut.tsx` — Recharts donut chart
- `argus/ui/src/components/RiskGauge.tsx` — Radial gauge component
- Dashboard integration: add donut to Dashboard, add risk gauge
- API integration: fetch orchestrator status for allocation data, fetch risk utilization from existing performance endpoint

**Design specs:**
- AllocationDonut: Recharts PieChart (donut), colored segments per strategy (P&L contribution), center text shows total deployed %, click segment filters dashboard, Framer Motion entry animation
- RiskGauge: SVG radial arc, 0–100% fill, color transitions (green 0–50%, yellow 50–75%, red 75–100%), secondary gauges smaller below main, pulse animation at >90%
- Responsive: donut and gauge resize gracefully at all breakpoints

### Session 13: Final Test Suite + Polish + Ruff

**No new files.** Full test suite run, fix any failures, ruff compliance, verify all 12 startup phases work in integration.

Run: `python -m pytest tests/ -v` and `ruff check argus/ tests/`

---

## Code Review Plan

### Checkpoint 1: After Session 7 (Orchestrator Backend Complete)

**Timing:** After main.py integration is done and all backend tests pass.

**What to verify:**
- Orchestrator initializes correctly in 12-phase startup
- Pre-market routine works end-to-end (regime → allocate → activate)
- Intraday regime re-evaluation fires at correct intervals
- Intraday throttle check triggers on consecutive losses
- Strategy lifecycle is owned by Orchestrator (not hardcoded in main.py)
- CorrelationTracker records data and computes matrix
- Decision logging writes to orchestrator_decisions table
- All existing 942 tests still pass + new tests pass
- Ruff clean

**Materials needed:**
- Full test output: `python -m pytest tests/ -v 2>&1 | tail -20`
- Ruff output: `ruff check argus/ tests/`
- `git diff --stat` from sprint start
- Key new files: `orchestrator.py`, `regime.py`, `throttle.py`, `correlation.py`, `main.py`

**Procedure:** Steven kicks off a new Claude.ai conversation with the Checkpoint 1 Handoff Brief (below). Claude reviews the code, verifies test coverage, flags any architectural concerns.

### Checkpoint 2: After Session 10 (DEF-016 Complete)

**Timing:** After bracket refactor is done and all tests pass.

**What to verify:**
- Order Manager uses `place_bracket_order()` for all entry submissions
- SimulatedBroker bracket flow works (sync fills handled correctly)
- Stop/T1/T2 order IDs are set on ManagedPosition from bracket result
- Mid-position modifications (stop-to-breakeven) still work
- All 33 existing Order Manager tests pass with updated mocks
- All integration tests pass
- No regressions in other test files

**Materials needed:**
- Full test output
- Ruff output
- `git diff argus/execution/order_manager.py`
- `git diff tests/execution/test_order_manager.py`

### Final Review: After Session 13 (Sprint Complete)

**Timing:** After all sessions including UX, final test suite run, ruff clean.

**What to verify:**
- Full end-to-end: Orchestrator → regime → allocate → strategy activated → signal → bracket order → fill → position managed → EOD review
- UX components render correctly (screenshots at 3 breakpoints)
- WebSocket forwards new Orchestrator events
- Dev mode includes mock orchestrator data
- API endpoints return correct data
- All tests pass, ruff clean
- Documentation updates drafted

**Materials needed:**
- Full test output with count
- Ruff output
- `git log --oneline` for sprint commits
- Screenshots: Dashboard with donut + gauge (desktop, tablet, mobile)
- Screenshots: Trade Log with segmented controls + badges
- Screenshots: System page with regime badge

---

## Copy-Paste Prompts for Claude Code Sessions

### Session 1 Prompt

```
I'm building ARGUS, an automated day trading system. Sprint 17: Orchestrator V1. Session 1 of 13.

Read CLAUDE.md first, then these files:
- config/orchestrator.yaml
- argus/core/config.py (see existing config patterns)
- argus/core/events.py (RegimeChangeEvent, AllocationUpdateEvent, StrategyActivatedEvent, StrategySuspendedEvent already defined)
- argus/db/manager.py (see table creation pattern)

This session creates the foundational types and config.

## Tasks

### 1. Create `argus/core/regime.py`
- `MarketRegime` enum: BULLISH_TRENDING, BEARISH_TRENDING, RANGE_BOUND, HIGH_VOLATILITY, CRISIS
- `RegimeIndicators` frozen dataclass: spy_price (float), spy_sma_20 (float | None), spy_sma_50 (float | None), spy_roc_5d (float | None), spy_realized_vol_20d (float | None), spy_vs_vwap (float | None), timestamp (datetime)

### 2. Create `argus/core/throttle.py`
- `ThrottleAction` enum: NONE, REDUCE, SUSPEND
- `StrategyAllocation` dataclass: strategy_id (str), allocation_pct (float), allocation_dollars (float), throttle_action (ThrottleAction), eligible (bool), reason (str)

### 3. Create `argus/core/correlation.py`
- `CorrelationTracker` class:
  - `__init__()`: Internal storage dict[str, dict[str, float]] mapping strategy_id → {date_str → daily_pnl}
  - `record_daily_pnl(strategy_id: str, date: str, pnl: float) -> None`
  - `seed_from_backtest(strategy_id: str, daily_pnl: dict[str, float]) -> None` — bulk load from backtested returns
  - `get_correlation_matrix() -> pd.DataFrame | None` — returns None if insufficient data (fewer strategies than 2 or fewer days than min_correlation_days)
  - `get_pairwise_correlation(strategy_a: str, strategy_b: str) -> float | None`
  - `has_sufficient_data(min_days: int = 20) -> bool`
  - Uses pandas for correlation computation. Only considers overlapping date ranges.

### 4. Add `OrchestratorConfig` to `argus/core/config.py`
Follow the existing Pydantic BaseModel pattern. Fields:
- allocation_method: str = "equal_weight"
- max_allocation_pct: float = 0.40
- min_allocation_pct: float = 0.10
- cash_reserve_pct: float = 0.20
- performance_lookback_days: int = 20
- consecutive_loss_throttle: int = 5
- suspension_sharpe_threshold: float = 0.0
- suspension_drawdown_pct: float = 0.15
- recovery_days_required: int = 10
- regime_check_interval_minutes: int | None = 30
- spy_symbol: str = "SPY"
- vol_low_threshold: float = 0.08
- vol_normal_threshold: float = 0.16
- vol_high_threshold: float = 0.25
- vol_crisis_threshold: float = 0.35
- pre_market_time: str = "09:25"
- eod_review_time: str = "16:05"
- poll_interval_seconds: int = 30
- correlation_enabled: bool = True
- min_correlation_days: int = 20
- max_combined_correlated_allocation: float = 0.60

Wire it into the SystemConfig (add `orchestrator: OrchestratorConfig` field, loaded from `config/orchestrator.yaml`).

### 5. Extend `config/orchestrator.yaml`
Add new fields with defaults matching the config model above.

### 6. Add orchestrator_decisions table to `argus/db/manager.py`
Add to the `initialize()` method's table creation. Schema:
```sql
CREATE TABLE IF NOT EXISTS orchestrator_decisions (
    id TEXT PRIMARY KEY,
    date TEXT NOT NULL,
    decision_type TEXT NOT NULL,
    strategy_id TEXT,
    details TEXT,
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### 7. Tests
Create `tests/core/test_correlation.py`:
- test_record_and_retrieve_daily_pnl
- test_correlation_matrix_two_strategies
- test_correlation_matrix_insufficient_data_returns_none
- test_pairwise_correlation
- test_seed_from_backtest
- test_has_sufficient_data
- test_overlapping_dates_only

Also add tests for OrchestratorConfig validation in the appropriate test file.

Target: ~15 new tests. Run `python -m pytest tests/ -x` at end. Ruff clean.
```

### Session 2 Prompt

```
ARGUS Sprint 17, Session 2 of 13. Orchestrator V1. Session 1 complete — config, models, correlation tracker, DB schema done.

Read CLAUDE.md, then:
- argus/core/regime.py (Session 1 created MarketRegime enum + RegimeIndicators)
- argus/core/config.py (OrchestratorConfig added in Session 1)
- docs/01_PROJECT_BIBLE.md Section 7 (Market Regime Classification)

This session builds the RegimeClassifier.

## Tasks

### 1. Add RegimeClassifier to `argus/core/regime.py`

```python
class RegimeClassifier:
    """Rules-based market regime classification.

    V1 uses SPY indicators only (no VIX, no breadth — DEC-113).
    Designed for indicator-count growth without interface changes.
    """

    def __init__(self, config: OrchestratorConfig) -> None: ...

    def compute_indicators(self, daily_bars: pd.DataFrame) -> RegimeIndicators:
        """Compute regime indicators from SPY daily OHLCV bars.

        Args:
            daily_bars: DataFrame with columns [timestamp, open, high, low, close, volume].
                       Must be sorted oldest-first. Minimum 50 rows for SMA-50.

        Returns:
            RegimeIndicators with all computable values filled in.
            Missing indicators (insufficient data) set to None.
        """

    def classify(self, indicators: RegimeIndicators) -> MarketRegime:
        """Classify market regime from indicators.

        Scoring system:
        1. Trend score (-2 to +2):
           - SPY > SMA-20 AND > SMA-50 → +2 (strong bull)
           - SPY > SMA-20 OR > SMA-50 → +1 (mild bull)
           - SPY < SMA-20 AND < SMA-50 → -2 (strong bear)
           - SPY < SMA-20 OR < SMA-50 → -1 (mild bear)
           - SMA data missing → 0

        2. Volatility bucket:
           - realized_vol < vol_low_threshold → LOW
           - realized_vol < vol_normal_threshold → NORMAL
           - realized_vol < vol_high_threshold → HIGH
           - realized_vol >= vol_crisis_threshold → CRISIS
           - None → NORMAL (conservative default)

        3. Momentum confirmation:
           - ROC-5d > +1% → bullish confirmation (+1)
           - ROC-5d < -1% → bearish confirmation (-1)
           - Otherwise → neutral (0)

        Decision matrix:
        - Crisis vol → CRISIS (overrides everything)
        - High vol + strong trend → HIGH_VOLATILITY
        - Trend score >= +1 → BULLISH_TRENDING
        - Trend score <= -1 → BEARISH_TRENDING
        - Otherwise → RANGE_BOUND
        """
```

**Realized volatility computation:**
```python
# 20-day realized volatility (annualized)
daily_returns = daily_bars['close'].pct_change().dropna()
realized_vol = daily_returns.tail(20).std() * (252 ** 0.5)  # annualize
```

**VWAP relative position:**
```python
# Today's VWAP approximation from daily bar
# (proper intraday VWAP requires minute bars — this is a daily approximation)
typical_price = (row.high + row.low + row.close) / 3
spy_vs_vwap = (spy_price - typical_price) / typical_price
```

### 2. Tests — `tests/core/test_regime.py`

Create comprehensive tests:
- test_compute_indicators_basic (60 bars of synthetic data)
- test_compute_indicators_insufficient_data (10 bars → SMA-50 is None)
- test_compute_indicators_empty_dataframe
- test_classify_bullish_trending (SPY above both SMAs, low vol, positive momentum)
- test_classify_bearish_trending (SPY below both SMAs, normal vol, negative momentum)
- test_classify_range_bound (SPY between SMAs, low vol, flat momentum)
- test_classify_high_volatility (high vol + strong trend)
- test_classify_crisis (crisis-level vol overrides trend)
- test_classify_missing_indicators (graceful degradation)
- test_classify_boundary_conditions (SPY exactly at SMA, vol exactly at threshold)
- test_momentum_confirmation (ROC confirms vs contradicts trend)
- test_volatility_thresholds (each bucket boundary)

Use synthetic DataFrames with controlled prices for deterministic testing.

Target: ~20 new tests. Run full suite. Ruff clean.
```

### Session 3 Prompt

```
ARGUS Sprint 17, Session 3 of 13. Sessions 1-2 complete — config, models, correlation tracker, DB schema, RegimeClassifier all done.

Read CLAUDE.md, then:
- argus/core/throttle.py (Session 1 created ThrottleAction + StrategyAllocation)
- argus/core/config.py (OrchestratorConfig)
- argus/analytics/performance.py (compute_sharpe_ratio, compute_max_drawdown_pct already exist)
- argus/analytics/trade_logger.py (get_trades_by_strategy, get_daily_pnl)
- docs/01_PROJECT_BIBLE.md Section 5.4 (Performance-Based Throttling)

This session builds the PerformanceThrottler.

## Tasks

### 1. Add PerformanceThrottler to `argus/core/throttle.py`

```python
class PerformanceThrottler:
    """Evaluates strategy performance for throttling/suspension decisions.

    Rules (from Bible Section 5.4):
    1. 5 consecutive losses → REDUCE (allocation to minimum)
    2. 20-day rolling Sharpe < 0 → SUSPEND
    3. Drawdown from equity peak > 15% → SUSPEND

    Returns the worst action (SUSPEND > REDUCE > NONE).
    """

    def __init__(self, config: OrchestratorConfig) -> None: ...

    def check(
        self,
        strategy_id: str,
        trades: list[Trade],
        daily_pnl: list[dict],  # from TradeLogger.get_daily_pnl()
    ) -> ThrottleAction:
        """Evaluate a strategy's performance and return throttle action."""

    def get_consecutive_losses(self, trades: list[Trade]) -> int:
        """Count consecutive losses from most recent trade backward.
        A loss is defined as net_pnl < 0. Breakeven (net_pnl == 0) breaks the streak.
        """

    def get_rolling_sharpe(self, daily_pnl: list[dict], lookback_days: int) -> float | None:
        """Compute rolling Sharpe ratio from daily P&L data.
        Returns None if insufficient data (< 5 days).
        Uses compute_sharpe_ratio() from analytics/performance.py.
        """

    def get_drawdown_from_peak(self, daily_pnl: list[dict]) -> float:
        """Compute current drawdown from equity peak as a percentage.
        Equity curve = cumulative sum of daily P&L.
        Drawdown = (peak - current) / peak.
        Returns 0.0 if equity is at or above peak.
        """
```

### 2. Tests — `tests/core/test_throttle.py`

- test_no_throttle_healthy_strategy (good trades, positive Sharpe)
- test_reduce_on_consecutive_losses (exactly 5 losses → REDUCE)
- test_no_reduce_on_4_losses (4 losses → NONE)
- test_reduce_on_6_losses (6 losses → REDUCE, not SUSPEND)
- test_suspend_on_negative_sharpe
- test_suspend_on_drawdown_exceeding_threshold
- test_suspend_overrides_reduce (both consecutive losses AND negative Sharpe → SUSPEND)
- test_consecutive_losses_with_breakeven (BE breaks streak)
- test_consecutive_losses_empty_trades
- test_consecutive_losses_single_trade
- test_rolling_sharpe_insufficient_data
- test_drawdown_at_peak (returns 0.0)
- test_drawdown_from_peak_calculation
- test_check_with_all_conditions_healthy

Use realistic Trade objects with proper net_pnl values.

Target: ~20 new tests. Run full suite. Ruff clean.
```

### Session 4 Prompt

```
ARGUS Sprint 17, Session 4 of 13. Sessions 1-3 complete — all supporting classes built and tested (RegimeClassifier, PerformanceThrottler, CorrelationTracker, config, models).

Read CLAUDE.md, then:
- argus/core/regime.py (RegimeClassifier)
- argus/core/throttle.py (PerformanceThrottler)
- argus/core/correlation.py (CorrelationTracker)
- argus/core/config.py (OrchestratorConfig)
- argus/core/events.py (4 Orchestrator events already defined)
- argus/core/event_bus.py (publish/subscribe pattern)
- argus/strategies/base_strategy.py (is_active, allocated_capital, get_market_conditions_filter)
- argus/analytics/trade_logger.py (get_trades_by_strategy, get_daily_pnl)
- argus/db/manager.py (database access pattern)

This session builds the main Orchestrator class. This is the core of Sprint 17.

## Tasks

### 1. Create `argus/core/orchestrator.py`

```python
class Orchestrator:
    """Manages strategy lifecycle, capital allocation, and market regime classification.

    V1 is rules-based. Designed for AI enhancement in V2+ (Sprint 22).

    Responsibilities:
    - Pre-market routine: classify regime, allocate capital, activate strategies
    - Intraday monitoring: re-evaluate regime every N minutes, throttle on losses
    - End-of-day review: log decisions, update correlation data
    - Strategy lifecycle: register, activate, deactivate, suspend
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        event_bus: EventBus,
        clock: Clock,
        trade_logger: TradeLogger,
        broker: Broker,
        data_service: DataService,
    ) -> None:
        self._config = config
        self._event_bus = event_bus
        self._clock = clock
        self._trade_logger = trade_logger
        self._broker = broker
        self._data_service = data_service
        self._regime_classifier = RegimeClassifier(config)
        self._throttler = PerformanceThrottler(config)
        self._correlation_tracker = CorrelationTracker()
        self._strategies: dict[str, BaseStrategy] = {}
        self._current_regime: MarketRegime = MarketRegime.RANGE_BOUND  # safe default
        self._current_allocations: dict[str, StrategyAllocation] = {}
        self._current_indicators: RegimeIndicators | None = None
        self._poll_task: asyncio.Task | None = None
        self._pre_market_done_today: bool = False
        self._eod_done_today: bool = False
        self._last_regime_check: datetime | None = None
        self._intraday_losses: dict[str, list[float]] = {}  # strategy_id → [pnl, pnl, ...]

    # --- Lifecycle ---
    async def start(self) -> None:
        """Subscribe to events and launch poll loop."""
        self._event_bus.subscribe(PositionClosedEvent, self._on_position_closed)
        self._poll_task = asyncio.create_task(self._poll_loop())
        logger.info("Orchestrator started")

    async def stop(self) -> None:
        """Cancel poll loop, unsubscribe."""
        if self._poll_task:
            self._poll_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._poll_task
        self._event_bus.unsubscribe(PositionClosedEvent, self._on_position_closed)
        logger.info("Orchestrator stopped")

    # --- Strategy Management ---
    def register_strategy(self, strategy: BaseStrategy) -> None: ...
    def get_strategies(self) -> dict[str, BaseStrategy]: ...
    def get_strategy(self, strategy_id: str) -> BaseStrategy | None: ...

    # --- Properties ---
    @property
    def current_regime(self) -> MarketRegime: ...
    @property
    def current_allocations(self) -> dict[str, StrategyAllocation]: ...
    @property
    def current_indicators(self) -> RegimeIndicators | None: ...
    @property
    def correlation_tracker(self) -> CorrelationTracker: ...

    # --- Pre-Market Routine ---
    async def run_pre_market(self) -> None:
        """Full pre-market sequence. Called at configured time or on mid-day restart."""
        # 1. Fetch SPY daily bars
        spy_bars = await self._data_service.fetch_daily_bars(
            self._config.spy_symbol, lookback_days=60
        )

        # 2. Classify regime
        if spy_bars is not None and len(spy_bars) >= 20:
            indicators = self._regime_classifier.compute_indicators(spy_bars)
            new_regime = self._regime_classifier.classify(indicators)
            self._current_indicators = indicators
        else:
            logger.warning("SPY data unavailable — using previous regime: %s", self._current_regime)
            new_regime = self._current_regime

        old_regime = self._current_regime
        self._current_regime = new_regime

        if old_regime != new_regime:
            await self._event_bus.publish(RegimeChangeEvent(
                old_regime=old_regime.value,
                new_regime=new_regime.value,
                indicators=self._indicators_to_dict(),
            ))

        # 3. Get account equity for allocation calculation
        account = await self._broker.get_account()
        total_equity = account.equity if account else 100000.0  # fallback

        # 4. Calculate allocations
        allocations = await self._calculate_allocations(total_equity)
        self._current_allocations = {a.strategy_id: a for a in allocations}

        # 5. Apply allocations
        for alloc in allocations:
            strategy = self._strategies.get(alloc.strategy_id)
            if strategy is None:
                continue
            strategy.allocated_capital = alloc.allocation_dollars
            was_active = strategy.is_active
            strategy.is_active = alloc.eligible and alloc.throttle_action != ThrottleAction.SUSPEND

            # Publish events
            await self._event_bus.publish(AllocationUpdateEvent(
                strategy_id=alloc.strategy_id,
                new_allocation_pct=alloc.allocation_pct,
                reason=alloc.reason,
            ))
            if strategy.is_active and not was_active:
                await self._event_bus.publish(StrategyActivatedEvent(
                    strategy_id=alloc.strategy_id,
                    reason=alloc.reason,
                ))
            elif not strategy.is_active and was_active:
                await self._event_bus.publish(StrategySuspendedEvent(
                    strategy_id=alloc.strategy_id,
                    reason=alloc.reason,
                ))

        # 6. Log decisions
        await self._log_decisions(allocations, new_regime)

        self._pre_market_done_today = True
        self._last_regime_check = self._clock.now()
        logger.info("Pre-market routine complete. Regime: %s", new_regime.value)

    async def _calculate_allocations(self, total_equity: float) -> list[StrategyAllocation]:
        """Calculate per-strategy allocations. Equal weight V1."""
        allocations = []
        deployable = total_equity * (1.0 - self._config.cash_reserve_pct)

        # Step 1: Filter by regime
        eligible_ids = []
        for sid, strategy in self._strategies.items():
            mcf = strategy.get_market_conditions_filter()
            if self._current_regime.value in mcf.allowed_regimes:
                eligible_ids.append(sid)

        # Step 2: Check throttling for eligible strategies
        throttle_results: dict[str, ThrottleAction] = {}
        for sid in eligible_ids:
            trades = await self._trade_logger.get_trades_by_strategy(
                sid, limit=200
            )
            daily_pnl = await self._trade_logger.get_daily_pnl()
            # Filter daily_pnl to this strategy (need strategy-specific daily P&L)
            # For V1 with single strategy, this works. Multi-strategy needs per-strategy daily P&L.
            throttle_results[sid] = self._throttler.check(sid, trades, daily_pnl)

        active_ids = [sid for sid in eligible_ids if throttle_results[sid] != ThrottleAction.SUSPEND]
        throttled_ids = [sid for sid in eligible_ids if throttle_results[sid] == ThrottleAction.REDUCE]

        # Step 3: Equal weight allocation
        n_active = len(active_ids)
        if n_active == 0:
            # All suspended or ineligible — give each strategy 0
            for sid in self._strategies:
                allocations.append(StrategyAllocation(
                    strategy_id=sid, allocation_pct=0.0, allocation_dollars=0.0,
                    throttle_action=throttle_results.get(sid, ThrottleAction.NONE),
                    eligible=sid in eligible_ids, reason="No eligible active strategies",
                ))
            return allocations

        base_pct = min(1.0 / n_active, self._config.max_allocation_pct)
        min_pct = self._config.min_allocation_pct

        for sid in self._strategies:
            if sid not in eligible_ids:
                allocations.append(StrategyAllocation(
                    strategy_id=sid, allocation_pct=0.0, allocation_dollars=0.0,
                    throttle_action=ThrottleAction.NONE, eligible=False,
                    reason=f"Regime {self._current_regime.value} not in allowed_regimes",
                ))
            elif throttle_results[sid] == ThrottleAction.SUSPEND:
                allocations.append(StrategyAllocation(
                    strategy_id=sid, allocation_pct=0.0, allocation_dollars=0.0,
                    throttle_action=ThrottleAction.SUSPEND, eligible=True,
                    reason="Suspended: performance threshold breached",
                ))
            elif throttle_results[sid] == ThrottleAction.REDUCE:
                pct = min_pct
                allocations.append(StrategyAllocation(
                    strategy_id=sid, allocation_pct=pct,
                    allocation_dollars=total_equity * pct,
                    throttle_action=ThrottleAction.REDUCE, eligible=True,
                    reason=f"Throttled to minimum ({pct:.0%}): consecutive losses",
                ))
            else:
                pct = base_pct
                allocations.append(StrategyAllocation(
                    strategy_id=sid, allocation_pct=pct,
                    allocation_dollars=total_equity * pct,
                    throttle_action=ThrottleAction.NONE, eligible=True,
                    reason=f"Active: {pct:.0%} allocation",
                ))

        return allocations

    # --- Manual Controls ---
    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Re-run allocation with current state. API-triggered."""
        account = await self._broker.get_account()
        total_equity = account.equity if account else 100000.0
        allocations = await self._calculate_allocations(total_equity)
        # Apply same as pre-market (abbreviated version)
        for alloc in allocations:
            strategy = self._strategies.get(alloc.strategy_id)
            if strategy:
                strategy.allocated_capital = alloc.allocation_dollars
                strategy.is_active = alloc.eligible and alloc.throttle_action != ThrottleAction.SUSPEND
        self._current_allocations = {a.strategy_id: a for a in allocations}
        return self._current_allocations

    # --- Intraday Event Handlers ---
    async def _on_position_closed(self, event: PositionClosedEvent) -> None:
        """Track intraday losses for throttle checks."""
        sid = event.strategy_id
        pnl = event.realized_pnl if hasattr(event, 'realized_pnl') else 0.0
        if sid not in self._intraday_losses:
            self._intraday_losses[sid] = []
        self._intraday_losses[sid].append(pnl)

        # Check consecutive losses intraday
        recent_losses = self._intraday_losses[sid]
        consecutive = 0
        for p in reversed(recent_losses):
            if p < 0:
                consecutive += 1
            else:
                break
        if consecutive >= self._config.consecutive_loss_throttle:
            strategy = self._strategies.get(sid)
            if strategy and strategy.is_active:
                strategy.is_active = False
                await self._event_bus.publish(StrategySuspendedEvent(
                    strategy_id=sid,
                    reason=f"Intraday throttle: {consecutive} consecutive losses",
                ))
                logger.warning("Strategy %s suspended intraday: %d consecutive losses", sid, consecutive)

    # --- Poll Loop ---
    async def _poll_loop(self) -> None:
        """Background task for time-based triggers."""
        while True:
            await asyncio.sleep(self._config.poll_interval_seconds)
            now = self._clock.now()
            now_et = now.astimezone(ZoneInfo("America/New_York"))
            today_str = now_et.strftime("%Y-%m-%d")

            # Reset daily flags at midnight
            if hasattr(self, '_last_date') and self._last_date != today_str:
                self._pre_market_done_today = False
                self._eod_done_today = False
                self._intraday_losses.clear()
            self._last_date = today_str

            # Pre-market trigger
            pre_market_time = datetime.strptime(self._config.pre_market_time, "%H:%M").time()
            if not self._pre_market_done_today and now_et.time() >= pre_market_time:
                try:
                    await self.run_pre_market()
                except Exception:
                    logger.exception("Pre-market routine failed")

            # Intraday regime re-check
            if (self._config.regime_check_interval_minutes
                and self._pre_market_done_today
                and self._last_regime_check):
                elapsed = (now - self._last_regime_check).total_seconds() / 60
                market_open = time(9, 30)
                market_close = time(16, 0)
                if market_open <= now_et.time() <= market_close:
                    if elapsed >= self._config.regime_check_interval_minutes:
                        try:
                            await self._run_regime_recheck()
                        except Exception:
                            logger.exception("Regime re-check failed")

            # EOD review trigger
            eod_time = datetime.strptime(self._config.eod_review_time, "%H:%M").time()
            if not self._eod_done_today and now_et.time() >= eod_time:
                try:
                    await self.run_end_of_day()
                except Exception:
                    logger.exception("EOD review failed")

    async def _run_regime_recheck(self) -> None:
        """Re-evaluate regime during market hours."""
        spy_bars = await self._data_service.fetch_daily_bars(self._config.spy_symbol, 60)
        if spy_bars is None or len(spy_bars) < 20:
            return

        indicators = self._regime_classifier.compute_indicators(spy_bars)
        new_regime = self._regime_classifier.classify(indicators)
        self._current_indicators = indicators
        self._last_regime_check = self._clock.now()

        if new_regime != self._current_regime:
            old = self._current_regime
            self._current_regime = new_regime
            logger.info("Regime changed intraday: %s → %s", old.value, new_regime.value)
            await self._event_bus.publish(RegimeChangeEvent(
                old_regime=old.value, new_regime=new_regime.value,
                indicators=self._indicators_to_dict(),
            ))
            # Re-evaluate strategy eligibility
            for sid, strategy in self._strategies.items():
                if not strategy.is_active:
                    continue
                mcf = strategy.get_market_conditions_filter()
                if new_regime.value not in mcf.allowed_regimes:
                    strategy.is_active = False
                    await self._event_bus.publish(StrategySuspendedEvent(
                        strategy_id=sid,
                        reason=f"Regime changed to {new_regime.value} — not in allowed regimes",
                    ))

    # --- End of Day ---
    async def run_end_of_day(self) -> None:
        """Post-close review."""
        # Record daily P&L per strategy to correlation tracker
        for sid in self._strategies:
            trades = await self._trade_logger.get_trades_by_strategy(sid, limit=50)
            today_pnl = sum(t.net_pnl for t in trades if t.net_pnl and t.exit_time and t.exit_time.date() == self._clock.today())
            self._correlation_tracker.record_daily_pnl(sid, self._clock.today().isoformat(), today_pnl)

        # Log EOD summary
        await self._log_decision("eod_review", None, {"regime": self._current_regime.value}, "End of day review")
        self._eod_done_today = True
        logger.info("EOD review complete")

    # --- Helpers ---
    def _indicators_to_dict(self) -> dict[str, float]:
        """Convert RegimeIndicators to dict for event payload."""
        if self._current_indicators is None:
            return {}
        return {
            "spy_price": self._current_indicators.spy_price,
            "spy_sma_20": self._current_indicators.spy_sma_20 or 0.0,
            "spy_sma_50": self._current_indicators.spy_sma_50 or 0.0,
            "spy_roc_5d": self._current_indicators.spy_roc_5d or 0.0,
            "spy_realized_vol_20d": self._current_indicators.spy_realized_vol_20d or 0.0,
        }

    async def _log_decision(self, decision_type: str, strategy_id: str | None, details: dict, rationale: str) -> None:
        """Log an orchestrator decision to the database."""
        import json
        from argus.models.trading import generate_id
        decision_id = generate_id()
        today = self._clock.today().isoformat()
        sql = """INSERT INTO orchestrator_decisions (id, date, decision_type, strategy_id, details, rationale)
                 VALUES (?, ?, ?, ?, ?, ?)"""
        await self._trade_logger._db.execute(
            sql, (decision_id, today, decision_type, strategy_id, json.dumps(details), rationale)
        )

    async def _log_decisions(self, allocations: list[StrategyAllocation], regime: MarketRegime) -> None:
        """Log all pre-market decisions."""
        for alloc in allocations:
            await self._log_decision(
                decision_type="allocation" if alloc.eligible else "exclusion",
                strategy_id=alloc.strategy_id,
                details={
                    "allocation_pct": alloc.allocation_pct,
                    "allocation_dollars": alloc.allocation_dollars,
                    "throttle_action": alloc.throttle_action.value,
                    "eligible": alloc.eligible,
                    "regime": regime.value,
                },
                rationale=alloc.reason,
            )
```

### 2. Tests — `tests/core/test_orchestrator.py`

This is the most critical test file of the sprint. Test thoroughly:
- test_register_strategy
- test_register_multiple_strategies
- test_pre_market_single_strategy_bullish (regime → eligible → allocated → activated)
- test_pre_market_strategy_excluded_by_regime (regime doesn't match allowed_regimes → not activated)
- test_pre_market_strategy_throttled (5 consecutive losses → REDUCE → min allocation)
- test_pre_market_strategy_suspended (negative Sharpe → SUSPEND → deactivated)
- test_pre_market_spy_data_unavailable (fallback to previous regime)
- test_allocation_math_equal_weight (verify percentages for 1, 2, 3 strategies)
- test_allocation_respects_max_cap (single strategy can't exceed max_allocation_pct)
- test_allocation_cash_reserve (total deployed ≤ 1 - cash_reserve_pct)
- test_event_publishing_regime_change
- test_event_publishing_allocation_update
- test_event_publishing_strategy_activated
- test_event_publishing_strategy_suspended
- test_decision_logging (verify rows written to orchestrator_decisions table)
- test_intraday_throttle_on_consecutive_losses (PositionClosedEvent triggers suspension)
- test_regime_recheck_triggers_deactivation
- test_manual_rebalance
- test_eod_review_records_correlation

Use FixedClock, mock DataService.fetch_daily_bars(), mock TradeLogger, SimulatedBroker.

Target: ~25 new tests. Run full suite. Ruff clean.
```

### Session 5 Prompt

```
ARGUS Sprint 17, Session 5 of 13. Sessions 1-4 complete — full Orchestrator core built and tested.

Read CLAUDE.md, then:
- argus/data/service.py (DataService ABC)
- argus/data/alpaca_data_service.py (AlpacaDataService)
- argus/data/databento_data_service.py (DatabentoDataService)
- argus/data/replay_data_service.py (ReplayDataService)
- argus/backtest/backtest_data_service.py (BacktestDataService)

This session adds fetch_daily_bars() to DataService ABC and implements it.

## Tasks

### 1. Add abstract method to `argus/data/service.py`

```python
@abstractmethod
async def fetch_daily_bars(
    self, symbol: str, lookback_days: int = 60
) -> pd.DataFrame | None:
    """Fetch daily OHLCV bars for regime classification.

    Args:
        symbol: Ticker symbol (e.g., "SPY").
        lookback_days: Number of calendar days of history to fetch.

    Returns:
        DataFrame with columns [timestamp, open, high, low, close, volume],
        sorted oldest-first. Returns None if data unavailable.
    """
```

### 2. Implement in AlpacaDataService

Use alpaca-py REST client to fetch daily bars. The AlpacaDataService already has `self._config` with API credentials.

```python
async def fetch_daily_bars(self, symbol: str, lookback_days: int = 60) -> pd.DataFrame | None:
    try:
        from alpaca.data.historical import StockHistoricalDataClient
        from alpaca.data.requests import StockBarsRequest
        from alpaca.data.timeframe import TimeFrame
        # Compute date range
        end = datetime.now(UTC)
        start = end - timedelta(days=lookback_days)
        # Fetch via REST
        client = StockHistoricalDataClient(self._config.api_key, self._config.api_secret)
        request = StockBarsRequest(symbol_or_symbols=symbol, timeframe=TimeFrame.Day, start=start, end=end)
        bars = client.get_stock_bars(request)
        # Convert to DataFrame
        df = bars.df.reset_index()
        df = df.rename(columns={"timestamp": "timestamp"})
        df = df[["timestamp", "open", "high", "low", "close", "volume"]]
        df = df.sort_values("timestamp").reset_index(drop=True)
        return df
    except Exception:
        logger.exception("Failed to fetch daily bars for %s", symbol)
        return None
```

Note: The actual alpaca-py API may differ slightly — read the existing AlpacaDataService code to match the established patterns for API client usage.

### 3. Stub implementations

For DatabentoDataService, ReplayDataService, and BacktestDataService:
```python
async def fetch_daily_bars(self, symbol: str, lookback_days: int = 60) -> pd.DataFrame | None:
    """Daily bars not available from this data service."""
    return None
```

### 4. Tests

Add to existing data service test files:
- test_alpaca_fetch_daily_bars_success (mock REST response)
- test_alpaca_fetch_daily_bars_api_error (returns None)
- test_alpaca_fetch_daily_bars_empty_response
- test_databento_fetch_daily_bars_returns_none
- test_replay_fetch_daily_bars_returns_none
- test_backtest_fetch_daily_bars_returns_none

Target: ~10 new tests. Run full suite. Ruff clean.
```

### Session 6 Prompt

```
ARGUS Sprint 17, Session 6 of 13. Sessions 1-5 complete — Orchestrator core + DataService.fetch_daily_bars() done.

Read CLAUDE.md, then:
- argus/core/orchestrator.py (the poll loop and intraday monitoring code from Session 4)
- argus/core/event_bus.py (subscribe/unsubscribe pattern)
- argus/core/clock.py (Clock protocol, FixedClock for tests)

This session focuses on testing the time-based behavior: poll loop, intraday regime re-check, EOD review. Session 4 wrote the code; this session ensures it's thoroughly tested and handles edge cases.

## Tasks

### 1. Add/enhance tests in `tests/core/test_orchestrator.py`

Focus on time-based behavior with FixedClock:

- test_poll_loop_triggers_pre_market_at_configured_time
  - Set FixedClock to 9:24 AM ET → poll fires → pre_market_done_today still False
  - Advance to 9:25 AM ET → poll fires → run_pre_market called → pre_market_done_today = True
  - Poll fires again → run_pre_market NOT called again (already done today)

- test_poll_loop_triggers_eod_at_configured_time
  - Similar pattern for 4:05 PM ET → run_end_of_day

- test_regime_recheck_fires_at_interval
  - FixedClock at 10:00 AM, regime_check_interval_minutes=30
  - Advance to 10:15 → no recheck
  - Advance to 10:30 → recheck fires
  - Advance to 10:45 → no recheck
  - Advance to 11:00 → recheck fires

- test_regime_recheck_outside_market_hours_no_op
  - FixedClock at 8:00 AM → even if interval elapsed, no recheck

- test_daily_flags_reset_at_midnight
  - Pre-market done at 9:25 AM, advance to next day 9:25 AM → pre-market runs again

- test_mid_day_restart_runs_pre_market
  - FixedClock set to 11:00 AM (market hours, pre_market_done_today=False)
  - Poll fires → detects pre-market time passed → runs pre-market immediately

- test_orchestrator_start_stop_lifecycle
  - start() subscribes to PositionClosedEvent, launches poll task
  - stop() cancels poll task, unsubscribes

- test_eod_records_correlation_data
  - After run_end_of_day(), correlation tracker has entries for each strategy

### 2. Fix any issues discovered during testing

The code from Session 4 is a design blueprint. Adjust as needed during testing.

Target: ~15 new tests. Run full suite. Ruff clean.
```

### Session 7 Prompt

```
ARGUS Sprint 17, Session 7 of 13. Sessions 1-6 complete — Orchestrator fully built and tested.

Read CLAUDE.md, then:
- argus/main.py (current 11-phase startup)
- argus/api/dependencies.py (AppState)
- argus/strategies/base_strategy.py
- argus/strategies/orb_breakout.py

This session integrates the Orchestrator into main.py, changing from 11-phase to 12-phase startup. The Orchestrator now owns strategy lifecycle.

## Tasks

### 1. Refactor `argus/main.py`

**Phase 8 changes:**
- Create strategy instances but do NOT set is_active=True or allocated_capital
- Keep all existing strategy creation logic
- Remove hardcoded `strategy.is_active = True` if present

**Insert Phase 9 (new):**
```python
# --- Phase 9: Orchestrator ---
logger.info("[9/12] Initializing orchestrator...")
from argus.core.orchestrator import Orchestrator
orchestrator_config = OrchestratorConfig(**load_yaml_file(self._config_dir / "orchestrator.yaml"))
self._orchestrator = Orchestrator(
    config=orchestrator_config,
    event_bus=self._event_bus,
    clock=self._clock,
    trade_logger=self._trade_logger,
    broker=self._broker,
    data_service=self._data_service,
)
self._orchestrator.register_strategy(self._strategy)
await self._orchestrator.start()

# Run pre-market routine (sets regime, allocations, activates strategies)
# If mid-day restart, this also handles state reconstruction
await self._orchestrator.run_pre_market()
self._health_monitor.update_component("orchestrator", ComponentStatus.HEALTHY)
```

**Renumber phases 10-12:** Order Manager becomes [10/12], Streaming [11/12], API [12/12].

**Phase 12 (API) changes:**
Add orchestrator to AppState:
```python
app_state = AppState(
    ...
    orchestrator=self._orchestrator,  # NEW
    strategies=self._orchestrator.get_strategies(),  # Use Orchestrator's registry
    ...
)
```

**Move strategy reconstruction:** The existing `_reconstruct_strategy_state()` method should be called by the Orchestrator as part of `run_pre_market()`, not by main.py directly. Either:
a) Move the logic into Orchestrator, or
b) Have Orchestrator call a method on main.py (less clean), or
c) Move strategy reconstruction into BaseStrategy.reconstruct_state() (already exists) and have Orchestrator call it for each registered strategy.

Option (c) is cleanest — Orchestrator calls `strategy.reconstruct_state(trade_logger)` during pre-market for each strategy. The historical bar replay for ORB's opening range reconstruction is ORB-specific and should stay in ORB's `reconstruct_state()` override.

**Add orchestrator to instance variables:**
```python
self._orchestrator: Orchestrator | None = None
```

**Shutdown:** Add `self._orchestrator.stop()` to shutdown sequence.

### 2. Update `argus/api/dependencies.py`

Add to AppState:
```python
from argus.core.orchestrator import Orchestrator  # in TYPE_CHECKING block
orchestrator: Orchestrator | None = None
```

### 3. Tests

Add integration test(s):
- test_12_phase_startup_completes (mock all externals, verify Orchestrator phase runs)
- test_strategy_activated_by_orchestrator (verify strategy.is_active set by Orchestrator, not hardcoded)
- test_orchestrator_in_app_state

Target: ~10 new tests. Run full suite. Ruff clean.

THIS IS CHECKPOINT 1. After this session:
1. Run `python -m pytest tests/ -v 2>&1 | tail -30` and save output
2. Run `ruff check argus/ tests/` and save output
3. Run `git diff --stat` from sprint start
4. Commit everything: `git add -A && git commit -m "sprint-17: orchestrator core + main.py integration (sessions 1-7)"`
5. Push to GitHub
6. Give Steven the test count, any failures, and the commit hash for code review
```

### Session 8 Prompt

```
ARGUS Sprint 17, Session 8 of 13. Sessions 1-7 complete, Checkpoint 1 passed.

Read CLAUDE.md, then:
- argus/api/routes/ (existing route patterns — especially controls.py and strategies.py)
- argus/api/server.py (router registration)
- argus/api/auth.py (require_auth dependency)
- argus/api/websocket/live.py (standard_events list)
- argus/api/dev_state.py (mock data factory)
- argus/core/orchestrator.py (Orchestrator class from Sessions 4-6)

This session adds Orchestrator API endpoints, WebSocket event forwarding, and dev mode mock data.

## Tasks

### 1. Create `argus/api/routes/orchestrator.py`

Three endpoints, following existing patterns in routes/:

```python
# GET /api/v1/orchestrator/status
# Returns: current regime, indicators, allocations, next check time
# Requires auth

# GET /api/v1/orchestrator/decisions?limit=50&offset=0
# Returns: paginated decision history from orchestrator_decisions table
# Requires auth

# POST /api/v1/controls/orchestrator/rebalance
# Triggers manual_rebalance() on the Orchestrator
# Requires auth
# Returns: new allocations
```

Response models (Pydantic):
```python
class OrchestratorStatusResponse(BaseModel):
    regime: str
    regime_indicators: dict[str, float]
    regime_updated_at: str | None
    allocations: list[AllocationInfo]
    cash_reserve_pct: float
    total_deployed_pct: float
    next_regime_check: str | None

class AllocationInfo(BaseModel):
    strategy_id: str
    allocation_pct: float
    allocation_dollars: float
    throttle_action: str
    eligible: bool
    reason: str

class DecisionInfo(BaseModel):
    id: str
    date: str
    decision_type: str
    strategy_id: str | None
    details: dict | None
    rationale: str | None
    created_at: str

class DecisionsResponse(BaseModel):
    decisions: list[DecisionInfo]
    total: int

class RebalanceResponse(BaseModel):
    success: bool
    message: str
    regime: str
    allocations: list[AllocationInfo]
```

### 2. Register router in `argus/api/server.py`

```python
from argus.api.routes.orchestrator import router as orchestrator_router
app.include_router(orchestrator_router, prefix="/api/v1/orchestrator")
```

Also register the rebalance endpoint under controls:
```python
# In controls.py or orchestrator.py — your call on organization
```

### 3. Update WebSocket bridge `argus/api/websocket/live.py`

Add to `standard_events` list:
```python
RegimeChangeEvent,
AllocationUpdateEvent,
StrategyActivatedEvent,
StrategySuspendedEvent,
```

Import them from `argus.core.events`.

### 4. Update `argus/api/dev_state.py`

Add mock orchestrator data so `--dev` mode works:
- Mock current regime (BULLISH_TRENDING)
- Mock allocations (1 strategy at 40%)
- Mock a few orchestrator decisions

### 5. Tests — `tests/api/test_orchestrator.py`

- test_get_status_returns_regime_and_allocations
- test_get_status_requires_auth
- test_get_decisions_paginated
- test_get_decisions_requires_auth
- test_post_rebalance_triggers_rebalance
- test_post_rebalance_requires_auth
- test_websocket_forwards_regime_change_event
- test_websocket_forwards_allocation_update_event

Target: ~12 new tests. Run full suite. Ruff clean.
```

### Session 9 Prompt

```
ARGUS Sprint 17, Session 9 of 13. DEF-016 Bracket Refactor Part 1.

Read CLAUDE.md, then carefully read:
- argus/execution/order_manager.py (full file — focus on on_approved and _handle_entry_fill)
- argus/execution/broker.py (Broker ABC — place_bracket_order signature and BracketOrderResult)
- argus/execution/simulated_broker.py (place_bracket_order implementation)
- argus/execution/ibkr_broker.py (place_bracket_order implementation)
- argus/execution/alpaca_broker.py (place_bracket_order implementation)
- argus/models/trading.py (BracketOrderResult, Order, OrderResult, OrderStatus)
- tests/execution/test_order_manager.py (existing tests)

DEC-117: Refactor Order Manager to use place_bracket_order() for atomic entry+stop+T1+T2 submission. All broker implementations already have working place_bracket_order() methods. The refactor is in Order Manager only.

## Current Flow (sequential)

```
on_approved() → broker.place_order(entry) → wait for fill →
_handle_entry_fill() → broker.place_order(stop) + broker.place_order(t1) + broker.place_order(t2)
```

## New Flow (atomic bracket)

```
on_approved() → construct entry+stop+t1+t2 → broker.place_bracket_order() →
track bracket order IDs → wait for entry fill →
_handle_entry_fill() → create ManagedPosition with pre-set order IDs (no separate order submission)
```

## Tasks

### 1. Modify PendingManagedOrder

Add fields to track bracket order IDs:
```python
@dataclass
class PendingManagedOrder:
    order_id: str
    symbol: str
    strategy_id: str
    order_type: str
    shares: int = 0
    signal: OrderApprovedEvent | None = None
    # NEW: bracket order IDs (set when entry is part of a bracket)
    bracket_stop_order_id: str | None = None
    bracket_t1_order_id: str | None = None
    bracket_t2_order_id: str | None = None
```

### 2. Refactor `on_approved()`

Replace the single place_order(entry) call with place_bracket_order():

```python
async def on_approved(self, event: OrderApprovedEvent) -> None:
    signal = event.signal
    # ... existing validation and modification logic ...

    # Construct bracket orders
    entry_order = Order(
        strategy_id=signal.strategy_id,
        symbol=signal.symbol,
        side=OrderSide.BUY,
        order_type=TradingOrderType.MARKET,
        quantity=share_count,
    )

    t1_shares = int(share_count * self._config.t1_position_pct)
    if t1_shares == 0 and share_count > 0:
        t1_shares = 1
    t2_shares = share_count - t1_shares

    stop_order = Order(
        strategy_id=signal.strategy_id,
        symbol=signal.symbol,
        side=OrderSide.SELL,
        order_type=TradingOrderType.STOP,
        quantity=share_count,
        stop_price=signal.stop_price,
    )

    targets = []
    t1_price = target_prices[0] if len(target_prices) >= 1 else 0.0
    if t1_price > 0 and t1_shares > 0:
        t1_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.SELL,
            order_type=TradingOrderType.LIMIT,
            quantity=t1_shares,
            limit_price=t1_price,
        )
        targets.append(t1_order)

    t2_price = target_prices[1] if len(target_prices) >= 2 else 0.0
    if t2_price > 0 and t2_shares > 0:
        t2_order = Order(
            strategy_id=signal.strategy_id,
            symbol=signal.symbol,
            side=OrderSide.SELL,
            order_type=TradingOrderType.LIMIT,
            quantity=t2_shares,
            limit_price=t2_price,
        )
        targets.append(t2_order)

    try:
        bracket_result = await self._broker.place_bracket_order(entry_order, stop_order, targets)
        entry_order_id = bracket_result.entry.order_id
    except Exception:
        logger.exception("Failed to submit bracket order for %s", signal.symbol)
        return

    # Track as pending with bracket IDs
    pending = PendingManagedOrder(
        order_id=entry_order_id,
        symbol=signal.symbol,
        strategy_id=signal.strategy_id,
        order_type="entry",
        shares=share_count,
        signal=event,
        bracket_stop_order_id=bracket_result.stop.order_id,
        bracket_t1_order_id=bracket_result.targets[0].order_id if bracket_result.targets else None,
        bracket_t2_order_id=bracket_result.targets[1].order_id if len(bracket_result.targets) > 1 else None,
    )
    self._pending_orders[entry_order_id] = pending

    # Also track stop and target orders as pending (so fill events route correctly)
    if bracket_result.stop.order_id:
        self._pending_orders[bracket_result.stop.order_id] = PendingManagedOrder(
            order_id=bracket_result.stop.order_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            order_type="stop",
        )
    for i, target_result in enumerate(bracket_result.targets):
        order_type = "t1_target" if i == 0 else "t2"
        self._pending_orders[target_result.order_id] = PendingManagedOrder(
            order_id=target_result.order_id,
            symbol=signal.symbol,
            strategy_id=signal.strategy_id,
            order_type=order_type,
        )

    # Publish OrderSubmittedEvent (unchanged)
    await self._event_bus.publish(OrderSubmittedEvent(...))

    # Handle sync fill (SimulatedBroker)
    if bracket_result.entry.status == OrderStatus.FILLED:
        fill_event = OrderFilledEvent(
            order_id=entry_order_id,
            fill_price=bracket_result.entry.filled_avg_price,
            fill_quantity=bracket_result.entry.filled_quantity,
        )
        await self.on_fill(fill_event)
```

### 3. Refactor `_handle_entry_fill()`

The key change: do NOT call _submit_stop_order, _submit_t1_order, _submit_t2_order. The orders are already placed as part of the bracket.

```python
async def _handle_entry_fill(self, pending: PendingManagedOrder, event: OrderFilledEvent) -> None:
    # ... existing position creation logic ...

    position = ManagedPosition(
        symbol=pending.symbol,
        strategy_id=pending.strategy_id,
        entry_price=event.fill_price,
        entry_time=self._clock.now(),
        shares_total=filled_shares,
        shares_remaining=filled_shares,
        stop_price=signal.stop_price,
        original_stop_price=signal.stop_price,
        stop_order_id=pending.bracket_stop_order_id,     # FROM BRACKET
        t1_price=t1_price,
        t1_order_id=pending.bracket_t1_order_id,          # FROM BRACKET
        t1_shares=t1_shares,
        t1_filled=False,
        t2_price=t2_price,
        t2_order_id=pending.bracket_t2_order_id,          # FROM BRACKET (DEC-093)
        high_watermark=event.fill_price,
    )

    # Add to managed positions
    if pending.symbol not in self._managed_positions:
        self._managed_positions[pending.symbol] = []
    self._managed_positions[pending.symbol].append(position)

    # NO LONGER NEEDED:
    # await self._submit_stop_order(position, filled_shares, signal.stop_price)
    # await self._submit_t1_order(position, t1_shares, t1_price)
    # await self._submit_t2_order(position, t2_shares, t2_price)

    # Publish PositionOpenedEvent (unchanged)
    await self._event_bus.publish(PositionOpenedEvent(...))
```

IMPORTANT: Keep _submit_stop_order(), _submit_t1_order(), _submit_t2_order() methods! They're still used for:
- Stop-to-breakeven after T1 fill (cancel old stop, submit new)
- Any mid-position modifications

### 4. Update tests in `tests/execution/test_order_manager.py`

Tests that mock `broker.place_order()` for entry submission need to mock `broker.place_bracket_order()` instead.

The mock should return a BracketOrderResult with appropriate order IDs and statuses.

For SimulatedBroker-based tests, no mock changes needed — SimulatedBroker's place_bracket_order works.

Target: ~15 modified/new tests. Run full suite after each change. Ruff clean.
```

### Session 10 Prompt

```
ARGUS Sprint 17, Session 10 of 13. DEF-016 Part 2 — verify all tests pass and add bracket-specific edge case tests.

Read CLAUDE.md, then:
- argus/execution/order_manager.py (refactored in Session 9)
- tests/execution/test_order_manager.py (updated in Session 9)

## Tasks

### 1. Run full test suite and fix any failures

```
python -m pytest tests/ -x -v
```

Fix all failures. The most likely issues:
- Tests that expected place_order() for entry now need place_bracket_order()
- Integration tests using SimulatedBroker should still work (it has place_bracket_order)
- Tests that checked pending_orders dict structure need updating

### 2. Add bracket-specific edge case tests

- test_bracket_entry_rejected (broker rejects entry → stop/targets not tracked)
- test_bracket_with_t1_only_no_t2 (single target)
- test_bracket_with_t1_and_t2 (dual targets)
- test_bracket_stop_to_breakeven_after_t1_fill (stop cancelled and resubmitted — this is the mid-position modification path)
- test_bracket_stop_cancelled_resubmit (stop order cancelled by broker → resubmit still works)
- test_bracket_order_ids_on_managed_position (verify IDs propagated from bracket result)
- test_bracket_with_simulated_broker_sync_fill (entry fills immediately, verify position created with bracket IDs)
- test_bracket_flatten_cancels_bracket_orders (emergency flatten cancels stop + targets)

### 3. Run full test suite again

```
python -m pytest tests/ -v 2>&1 | tail -30
ruff check argus/ tests/
```

THIS IS CHECKPOINT 2. After this session:
1. Save test output and ruff output
2. Commit: `git add -A && git commit -m "sprint-17: DEF-016 bracket refactor (sessions 9-10)"`
3. Push to GitHub
4. Report test count, any failures, and commit hash
```

### Session 11 Prompt

```
ARGUS Sprint 17, Session 11 of 13. UX Session 1: Segmented Controls + Badge System.

Read CLAUDE.md (UI/UX Rules section), then:
- argus/ui/src/components/ (existing component patterns)
- argus/ui/src/pages/Dashboard.tsx
- argus/ui/src/pages/TradeLog.tsx
- argus/ui/src/pages/System.tsx
- docs/ui/UX_FEATURE_BACKLOG.md (items 17-B and 17-D)

Design principles: information over decoration, mobile as primary trading surface, motion with purpose (<500ms). Match Sprint 16's animation quality and dark theme.

## Tasks

### 1. Create SegmentedTab component (17-B)

`argus/ui/src/components/SegmentedTab.tsx`

Props:
```typescript
interface SegmentedTabProps {
  segments: Array<{
    label: string;
    count?: number;
    value: string;
  }>;
  activeValue: string;
  onChange: (value: string) => void;
  size?: 'sm' | 'md';
}
```

Design:
- Rounded pill container with dark background (zinc-800)
- Active segment: lighter background (zinc-700), smooth Framer Motion layoutId animation
- Count badges: small pill inside segment, colored by context
- Touch targets ≥44px on mobile
- Responsive: full width on mobile, inline on desktop

### 2. Apply SegmentedTab to pages

**Dashboard:** "Open {n} | Closed {n}" filter for positions section
**Trade Log:** "All | Wins {n} | Losses {n} | BE {n}" filter for trade table
**System:** "All | Healthy {n} | Degraded {n} | Down {n}" filter for components

### 3. Create Badge component variants (17-D)

`argus/ui/src/components/Badge.tsx`

Extend existing exit reason badges with new variants:

```typescript
type BadgeVariant = 
  | 'exit_reason'    // existing: target_1, stop_loss, time_stop, etc.
  | 'strategy'       // ORB=blue, Scalp=purple, VWAP=teal, Momentum=amber
  | 'regime'         // Bullish=green, Bearish=red, Range=yellow, HighVol=orange, Crisis=red-600
  | 'risk'           // Normal=green, Approaching=yellow, AtLimit=red
  | 'throttle';      // Active=green, Reduced=yellow, Suspended=red
```

Color mapping configurable via a lookup object. Consistent size (text-xs, px-2, py-0.5, rounded-full).

### 4. Apply badges to pages

**Dashboard:** Strategy badge on open positions, regime badge in header area
**Trade Log:** Strategy badge on each trade row
**System:** Strategy status badges on strategy cards

### 5. Verify responsive behavior

Test at all breakpoints: 393px, 834px, 1194px, 1512px. Segmented tabs should wrap or scroll horizontally on narrow screens.

No backend tests needed. Run `cd argus/ui && npm run build` to verify no build errors.
```

### Session 12 Prompt

```
ARGUS Sprint 17, Session 12 of 13. UX Session 2: Allocation Donut + Risk Gauge.

Read CLAUDE.md (UI/UX Rules section), then:
- argus/ui/src/pages/Dashboard.tsx
- argus/ui/src/components/ (existing chart patterns — look for Lightweight Charts usage)
- argus/api/routes/orchestrator.py (status endpoint — provides allocation data)
- argus/api/routes/performance.py (provides risk metrics)
- docs/ui/UX_FEATURE_BACKLOG.md (items 17-A and 17-C)

## Tasks

### 1. Create AllocationDonut component (17-A)

`argus/ui/src/components/AllocationDonut.tsx`

Uses Recharts PieChart (already in project dependencies from Sprint 15).

```typescript
interface AllocationDonutProps {
  allocations: Array<{
    strategy_id: string;
    allocation_pct: number;
    daily_pnl: number;
  }>;
  cashReservePct: number;
}
```

Design:
- Donut chart (inner radius 60%, outer radius 100%)
- Segments colored by strategy (use Badge color mapping for consistency)
- Cash reserve segment in zinc-700
- Center text: total deployed percentage, large bold number
- Framer Motion entry animation (segments grow from 0)
- Click segment → future: filter dashboard to that strategy (for now, just highlight)
- Responsive: 200px diameter on mobile, 250px on desktop

### 2. Create RiskGauge component (17-C)

`argus/ui/src/components/RiskGauge.tsx`

SVG-based radial gauge.

```typescript
interface RiskGaugeProps {
  label: string;
  value: number;     // 0-100 percentage
  maxLabel?: string;  // e.g., "3% daily limit"
  size?: 'sm' | 'md';
}
```

Design:
- SVG arc (270 degrees, gap at bottom)
- Background arc: zinc-700
- Fill arc: animated, color transitions:
  - 0–50%: green-500
  - 50–75%: yellow-500
  - 75–100%: red-500
- Center text: percentage value
- Label below
- Framer Motion: arc fills on mount
- Pulse animation when >90% (subtle opacity oscillation)

### 3. Add to Dashboard

Fetch orchestrator status via API hook (add to existing API service):
```typescript
// useOrchestratorStatus() hook
const { data } = useQuery(['orchestrator-status'], () => api.get('/orchestrator/status'));
```

Layout:
- Desktop: Donut and risk gauges in a row below account summary cards
- Tablet: Same row, slightly smaller
- Mobile: Donut full width, risk gauges in a 2-column grid below

Risk gauges to show:
- Daily risk budget consumed (from daily P&L vs daily loss limit)
- Weekly risk budget consumed (from weekly P&L vs weekly loss limit)

### 4. Handle dev mode / empty state

When orchestrator data is unavailable (dev mode without mock data, or no strategies registered):
- Donut shows "No strategies active" in center
- Risk gauges show 0% with "—" label
- Graceful, not broken

No backend tests needed. Run `cd argus/ui && npm run build` to verify no build errors.
```

### Session 13 Prompt

```
ARGUS Sprint 17, Session 13 of 13. Final verification and polish.

Read CLAUDE.md.

## Tasks

### 1. Full test suite

```
python -m pytest tests/ -v 2>&1
```

Count total tests. Fix any failures. Target: ~1,100+ tests.

### 2. Ruff compliance

```
ruff check argus/ tests/
```

Fix all issues.

### 3. Frontend build

```
cd argus/ui && npm run build
```

Fix any build errors.

### 4. Dev mode verification

```
python -m argus.api --dev
```

Verify API starts, orchestrator endpoints return mock data, WebSocket connects.

### 5. Quick integration check

Verify imports are clean:
```
python -c "from argus.core.orchestrator import Orchestrator; print('OK')"
python -c "from argus.api.routes.orchestrator import router; print('OK')"
```

### 6. Final commit

```
git add -A
git commit -m "sprint-17: orchestrator v1 + DEF-016 bracket refactor + UX (complete)"
git push
```

Report:
- Total test count
- Any remaining issues
- Files changed (`git diff --stat` from sprint start)
- Ready for final code review
```

---

## Code Review Handoff Briefs

### Checkpoint 1 Handoff Brief (After Session 7)

```
# Sprint 17 Checkpoint 1 — Orchestrator Backend Review

I'm building ARGUS, an automated day trading system. Sprint 17 adds the Orchestrator V1 — the component that manages strategy lifecycle, market regime classification, capital allocation, and performance-based throttling.

Sessions 1-7 of 13 are complete. The Orchestrator backend is fully built and integrated into main.py. I need a code review before proceeding to the API layer and DEF-016 bracket refactor.

## What was built (Sessions 1-7):

1. **RegimeClassifier** (`argus/core/regime.py`): Rules-based market regime classification using SPY daily bars. Computes SMAs, realized volatility (VIX proxy), momentum. Classifies into 5 regimes. DEC-113.

2. **PerformanceThrottler** (`argus/core/throttle.py`): Evaluates strategy performance for throttling/suspension. 3 rules: consecutive losses → reduce, negative Sharpe → suspend, drawdown > 15% → suspend.

3. **CorrelationTracker** (`argus/core/correlation.py`): Records daily P&L per strategy, computes pairwise correlation matrix. Infrastructure for future correlation-adjusted allocation. DEC-116.

4. **Orchestrator** (`argus/core/orchestrator.py`): Main coordinator. Pre-market routine, continuous regime monitoring (every 30 min, DEC-115), intraday throttle checks on PositionClosedEvent, EOD review, decision logging.

5. **DataService.fetch_daily_bars()**: Added to ABC + AlpacaDataService implementation (Alpaca REST). Other DataServices return None.

6. **main.py integration**: 12-phase startup. Phase 9 = Orchestrator. Strategy lifecycle owned by Orchestrator.

## Key design decisions:
- DEC-113: SPY realized vol as VIX proxy (real VIX requires separate CBOE dataset)
- DEC-114: Equal-weight allocation V1 (performance-weighted deferred)
- DEC-115: Continuous regime monitoring every 30 min during market hours
- DEC-116: CorrelationTracker infrastructure built, not yet wired into allocation
- DEC-118: Self-contained poll loop (no APScheduler dependency)

## What to review:

Please read these files and check:

1. `argus/core/orchestrator.py` — Architecture, pre-market flow, allocation math, event publishing, intraday monitoring, poll loop. Does it handle edge cases? Any race conditions in the async flow?

2. `argus/core/regime.py` — Classification logic. Are the scoring rules reasonable? Edge cases with missing indicators?

3. `argus/core/throttle.py` — Performance checks. Are the consecutive loss, Sharpe, and drawdown calculations correct?

4. `argus/core/correlation.py` — Correlation computation. Edge cases with overlapping dates?

5. `argus/main.py` — 12-phase startup. Is the Orchestrator placed correctly in the dependency chain? Is shutdown clean?

6. `argus/core/config.py` — OrchestratorConfig. Are the defaults sensible?

7. Test coverage — run `python -m pytest tests/core/test_orchestrator.py tests/core/test_regime.py tests/core/test_throttle.py tests/core/test_correlation.py -v` and check for gaps.

## Specific concerns:
- Is the allocation math correct for the single-strategy case? (1 strategy gets min(1/1, max_allocation_pct) = 40%)
- Does intraday regime re-evaluation handle the case where DataService.fetch_daily_bars() returns cached data?
- Is the PositionClosedEvent handler safe to call from Event Bus thread?
- Are there any circular dependencies I should worry about?

The repo is at https://github.com/stevengizzi/argus.git, latest commit on main branch.
```

### Checkpoint 2 Handoff Brief (After Session 10)

```
# Sprint 17 Checkpoint 2 — DEF-016 Bracket Refactor Review

Sprint 17 DEF-016 is complete (Sessions 9-10). The Order Manager now uses place_bracket_order() for atomic entry+stop+T1+T2 submission instead of sequential place_order() calls.

## What changed:

1. **Order Manager `on_approved()`**: Now constructs full bracket (entry + stop + targets) and calls `broker.place_bracket_order()`. Previously submitted entry only, then stop/T1/T2 in `_handle_entry_fill()`.

2. **PendingManagedOrder**: New fields `bracket_stop_order_id`, `bracket_t1_order_id`, `bracket_t2_order_id` to track bracket IDs.

3. **`_handle_entry_fill()`**: No longer calls `_submit_stop_order()`, `_submit_t1_order()`, `_submit_t2_order()`. Sets ManagedPosition order IDs from bracket result instead.

4. **Preserved**: `_submit_stop_order()` etc. still exist for mid-position modifications (stop-to-breakeven after T1 fill).

## What to review:

1. `argus/execution/order_manager.py` — Focus on `on_approved()` and `_handle_entry_fill()`. Is the bracket flow correct? Are all order IDs tracked properly in pending_orders?

2. `tests/execution/test_order_manager.py` — Are the updated mocks correct? Are bracket edge cases covered?

3. Run the full test suite — are there any regressions? Especially check:
   - `tests/test_integration_sprint4b.py` (Order Manager integration)
   - `tests/test_integration_sprint13.py` (IBKR integration)
   - `tests/backtest/test_replay_harness.py` (uses SimulatedBroker)

## Specific concerns:
- SimulatedBroker fills entry synchronously inside `place_bracket_order()`. Does the `on_approved()` method handle this correctly?
- When emergency_flatten cancels all orders, does it properly cancel the bracket stop and target orders?
- Are there any edge cases where a fill event arrives for a bracket order that we haven't tracked yet?

The repo is at https://github.com/stevengizzi/argus.git, latest commit.
```

### Final Review Handoff Brief (After Session 13)

```
# Sprint 17 Final Review — Orchestrator V1 + DEF-016 + UX

Sprint 17 is complete (13 sessions). Full Orchestrator V1, DEF-016 bracket refactor, and 4 UX features delivered.

## Sprint 17 deliverables:

### Backend:
1. **Orchestrator** (`argus/core/orchestrator.py`): Pre-market routine, continuous regime monitoring (30 min), capital allocation (equal-weight), performance throttling (consecutive losses, Sharpe, drawdown), intraday monitoring, EOD review, decision logging. DEC-113–118.
2. **RegimeClassifier** (`argus/core/regime.py`): SPY-based regime classification (5 categories). Realized vol as VIX proxy.
3. **PerformanceThrottler** (`argus/core/throttle.py`): 3-rule throttle engine.
4. **CorrelationTracker** (`argus/core/correlation.py`): Daily P&L recording + correlation matrix. Infrastructure for future correlation-adjusted allocation.
5. **DataService.fetch_daily_bars()**: ABC method + AlpacaDataService implementation.
6. **DEF-016 resolved**: Order Manager uses `place_bracket_order()` for atomic bracket submission. DEC-117.
7. **main.py**: 12-phase startup. Orchestrator as Phase 9.
8. **API**: 3 new endpoints (orchestrator status, decisions, rebalance). WebSocket forwards 4 new event types.

### Frontend:
9. **SegmentedTab** component (17-B): Reusable with live counts. Applied to Dashboard, Trade Log, System.
10. **Badge system** (17-D): Strategy, regime, risk, throttle badge variants.
11. **AllocationDonut** (17-A): Recharts donut on Dashboard showing capital allocation.
12. **RiskGauge** (17-C): SVG radial gauge showing risk budget consumption.

## What to review:

Full code review. Key files:
- `argus/core/orchestrator.py`, `regime.py`, `throttle.py`, `correlation.py`
- `argus/execution/order_manager.py` (DEF-016 changes)
- `argus/main.py` (12-phase startup)
- `argus/api/routes/orchestrator.py`
- `argus/api/websocket/live.py` (new events)
- All new test files
- UX components (SegmentedTab, Badge, AllocationDonut, RiskGauge)

Please verify:
1. Test count (target: ~1,100+)
2. All tests passing
3. Ruff clean
4. UX renders correctly at 3 device classes (will provide screenshots)
5. Architectural integrity — Orchestrator correctly owns strategy lifecycle
6. Decision log entries ready for documentation

## Screenshots attached:
[Steven will add screenshots at 393px, 834px, 1512px showing Dashboard with donut/gauge, Trade Log with segmented controls, System page with regime badge]

The repo is at https://github.com/stevengizzi/argus.git, latest commit.

After review, please draft the docs update (Decision Log entries for DEC-113–118, Project Knowledge updates, Sprint Plan completion entry, CLAUDE.md updates, Risk Register if applicable). Use the standard "## Docs Sync" output format.
```

---

## Deferred Items to Document

### DEF-017: Performance-Weighted Allocation + Correlation-Adjusted Allocation
- **Trigger:** 20+ days of multi-strategy parallel trading data exists
- **Context:** V1 uses equal-weight allocation (DEC-114). Performance-weighted shifts ±10% based on trailing Sharpe/profit factor (Bible Section 5.2). Correlation-adjusted reduces combined allocation for highly correlated strategy pairs (DEC-116 infrastructure already built). Both require sufficient historical data to be statistically meaningful.

### DEF-018: Real VIX Data Integration
- **Trigger:** IQFeed subscription activated OR CBOE Databento dataset added
- **Context:** V1 uses SPY 20-day realized volatility as VIX proxy (DEC-113). Actual VIX requires separate data source. Architecture supports swap with zero Orchestrator changes — only RegimeClassifier.compute_indicators() needs modification.

### DEF-019: Breadth Indicator (Advance/Decline) Integration
- **Trigger:** IQFeed subscription activated
- **Context:** V1 skips breadth in regime classification (DEC-113). Adding advance/decline ratio improves regime accuracy, especially for distinguishing broad-based moves from sector rotations. RegimeClassifier scoring system designed for indicator-count growth.

---

## Config File Update

### config/orchestrator.yaml (final)

```yaml
# Orchestrator V1 Configuration
# See DEC-113 through DEC-118 for design decisions

# Capital Allocation
allocation_method: "equal_weight"  # V1. Future: "performance_weighted" (DEF-017)
max_allocation_pct: 0.40
min_allocation_pct: 0.10
cash_reserve_pct: 0.20

# Performance Throttling
performance_lookback_days: 20
consecutive_loss_throttle: 5
suspension_sharpe_threshold: 0.0
suspension_drawdown_pct: 0.15
recovery_days_required: 10

# Market Regime Classification
regime_check_interval_minutes: 30  # null = pre-market only (DEC-115)
spy_symbol: "SPY"
# Realized volatility thresholds (annualized, VIX proxy — DEC-113)
vol_low_threshold: 0.08      # ~VIX < 12
vol_normal_threshold: 0.16   # ~VIX 12-22
vol_high_threshold: 0.25     # ~VIX 22-35
vol_crisis_threshold: 0.35   # ~VIX > 35

# Schedule (Eastern Time)
pre_market_time: "09:25"
eod_review_time: "16:05"
poll_interval_seconds: 30

# Correlation Tracking (DEC-116)
correlation_enabled: true
min_correlation_days: 20
max_combined_correlated_allocation: 0.60
```
