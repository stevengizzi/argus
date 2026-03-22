# Sprint 27: Session Breakdown

## Dependency Chain

```
S1 (SyncBus + Config) ──┐
                         ├──→ S3 (Engine setup) → S4 (Bar loop) → S5 (Multi-day + CLI) → S6 (WF + equiv)
S2 (HistoricalDataFeed) ─┘
```

S1 and S2 are parallelizable (no shared files, independent outputs).
S3 depends on S1. S4 depends on S2 and S3. S5–S6 are strictly sequential.

---

## Session 1: SynchronousEventBus + BacktestEngineConfig

**Objective:** Build the synchronous event dispatch mechanism and the configuration model for BacktestEngine runs.

**Creates:**
- `argus/core/sync_event_bus.py` — SynchronousEventBus class (~40 lines)

**Modifies:**
- `argus/backtest/config.py` — Add BULL_FLAG and FLAT_TOP_BREAKOUT to StrategyType enum; add BacktestEngineConfig Pydantic model

**Integrates:** N/A (foundational)

**Parallelizable:** true — independent of S2, no shared files

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (sync_event_bus.py) | 2 |
| Files modified | 1 (config.py) | 1 |
| Context reads | 2 (event_bus.py, config.py) | 2 |
| New tests | ~13 | 6.5 |
| Complex integration | — | 0 |
| External API debugging | — | 0 |
| Large files (>150 lines) | — | 0 |
| **Total** | | **11.5** |

**Risk Level:** Medium — proceed

**Test Estimates:**
- SyncEventBus: subscribe handler, publish dispatches to all, publish with no subscribers, sequence number assignment, error isolation (handler raises), unsubscribe, drain is no-op, reset clears state = **8 tests**
- BacktestEngineConfig: model validates defaults, rejects invalid engine_mode, all StrategyType values present, cache_dir path handling = **3 tests**
- StrategyType enum: BULL_FLAG and FLAT_TOP_BREAKOUT resolve correctly, existing values unchanged = **2 tests**
- **Total: ~13 tests**

---

## Session 2: HistoricalDataFeed

**Objective:** Build the Databento OHLCV-1m download, caching, and CandleEvent conversion layer.

**Creates:**
- `argus/backtest/historical_data_feed.py` — HistoricalDataFeed class (~180 lines)

**Modifies:** None

**Integrates:** N/A (standalone data layer)

**Parallelizable:** true — independent of S1, no shared files

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (historical_data_feed.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 3 (data_fetcher.py, databento_utils.py, config.py) | 3 |
| New tests | ~12 | 6 |
| Complex integration | — | 0 |
| External API debugging | — | 0 |
| Large files (>150 lines) | 1 (~180 lines) | 2 |
| **Total** | | **13** |

**Risk Level:** Medium — proceed

**Test Estimates:**
- Download path (mocked Databento client): successful download, cost validation passes, cost validation fails (raises), empty result handling = **4 tests**
- Cache layer: cache miss triggers download, cache hit skips download, incremental update downloads only missing months, cache directory creation = **4 tests**
- Data conversion: normalized DataFrame schema correct, UTC timestamps, date range filtering, multi-symbol loading = **3 tests**
- Error handling: symbol not found gracefully, API error propagation = **1 test**
- **Total: ~12 tests**

---

## Session 3: BacktestEngine — Component Assembly + Strategy Factory

**Objective:** Build the core engine skeleton: constructor, component wiring (_setup), strategy factory for all 7 types, teardown.

**Creates:**
- `argus/backtest/engine.py` (partial: __init__, _setup, _create_strategy, _teardown) (~200 lines)

**Modifies:** None

**Integrates:** S1 (SyncEventBus from sync_event_bus.py, BacktestEngineConfig from config.py)

**Parallelizable:** false — depends on S1

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (engine.py) | 2 |
| Files modified | 0 | 0 |
| Context reads | 3 (sync_event_bus.py, backtest_data_service.py, config.py) | 3 |
| New tests | ~12 | 6 |
| Complex integration | 1 (wires SyncBus + BacktestDataService + FixedClock + Strategy + RM + OM + SimBroker) | 3 |
| External API debugging | — | 0 |
| Large files (>150 lines) | — | 0 |
| **Total** | | **14** |

**Risk Level:** Borderline High — justified proceed

**Justification for proceeding at 14:** The component wiring directly follows the pattern in `ReplayHarness._setup()` (lines 238–315). The implementer adapts an existing ~80-line method, not inventing new integration. The strategy factory extends `ReplayHarness._create_strategy()` from 4 types to 7. Both reference implementations are in the pre-flight reads. The +3 integration penalty accurately reflects the component count but overweights the actual difficulty.

**Test Estimates:**
- Component assembly: _setup creates all components, SyncEventBus used (not EventBus), FixedClock used, SimulatedBroker connected, BacktestDataService created = **3 tests**
- Strategy factory: creates ORB Breakout, ORB Scalp, VWAP Reclaim, AfMo, Red-to-Green (BaseStrategy subclasses), Bull Flag (PatternBasedStrategy + BullFlagPattern), Flat-Top (PatternBasedStrategy + FlatTopBreakoutPattern) = **7 tests** (one per strategy type)
- Teardown: components cleaned up, DB closed = **1 test**
- Error paths: unknown strategy type raises, missing config file raises = **1 test**
- **Total: ~12 tests**

---

## Session 4: BacktestEngine — Single-Day Bar Loop + Order Fill Model

**Objective:** Implement the single-day execution loop: bar processing, bar-level order fill simulation with worst-case priority, and price/bracket updates.

**Creates:** None

**Modifies:**
- `argus/backtest/engine.py` (extend with _run_trading_day, _process_bar_fills, _check_bracket_orders)

**Integrates:** S2 (HistoricalDataFeed for loading data into bar format), S3 (engine skeleton)

**Parallelizable:** false — depends on S3

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (engine.py) | 1 |
| Context reads | 3 (engine.py from S3, replay_harness.py ref, simulated_broker.py ref) | 3 |
| New tests | ~15 | 7.5 |
| Complex integration | — | 0 |
| External API debugging | — | 0 |
| Large files (>150 lines) | — | 0 |
| **Total** | | **11.5** |

**Risk Level:** Medium — proceed

**Test Estimates:**
- Bar processing loop: bars fed in chronological order, clock advances per bar, multi-symbol bars interleaved by timestamp, indicators computed via BacktestDataService = **4 tests**
- Fill model — stop priority: bar where both stop and target could trigger → stop wins = **2 tests**
- Fill model — target hit: bar high exceeds target → target fill at target price = **2 tests**
- Fill model — time stop: position held beyond time limit → close at bar close, but check stop hit first = **2 tests**
- Fill model — EOD: open position at EOD → flattened at configured time = **1 test**
- No-trade day: no signals generated → no trades, no errors = **1 test**
- Multi-symbol single day: bars from 3 symbols processed correctly, trades on each = **1 test**
- Watchlist scoping: strategy only receives bars for watchlist symbols = **1 test**
- Strategy on_candle integration: signal → risk eval → order submission works end-to-end for one bar = **1 test**
- **Total: ~15 tests**

---

## Session 5: BacktestEngine — Multi-Day Orchestration + Scanner + Results + CLI

**Objective:** Complete the engine with multi-day loop, daily state resets, scanner simulation for watchlist generation, results computation, and CLI entry point.

**Creates:** None

**Modifies:**
- `argus/backtest/engine.py` (extend with run(), _run_all_days, _generate_watchlists, CLI section)

**Integrates:** S4 (single-day execution), existing metrics.py (compute_metrics), existing scanner_simulator.py (ScannerSimulator)

**Parallelizable:** false — depends on S4

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (engine.py) | 1 |
| Context reads | 3 (engine.py from S4, metrics.py, scanner_simulator.py) | 3 |
| New tests | ~15 | 7.5 |
| Complex integration | — | 0 |
| External API debugging | — | 0 |
| Large files (>150 lines) | — | 0 |
| **Total** | | **11.5** |

**Risk Level:** Medium — proceed

**Test Estimates:**
- Multi-day loop: runs 5 trading days, daily state resets verified (strategy, RM, OM, data service), progress logging = **3 tests**
- Daily state reset: strategy reset_daily_state() called per day, risk manager reset, order manager reset, data service reset = **1 test** (integration, verifies all four)
- Scanner integration: ScannerSimulator produces watchlists from historical data, watchlists passed to strategy per day = **2 tests**
- Results computation: compute_metrics() called with correct parameters, BacktestResult contains expected fields = **2 tests**
- Empty data handling: no trading days found → empty result returned = **1 test**
- CLI: parse_args handles required flags, main() runs successfully with mocked data = **2 tests**
- End-to-end: ORB Breakout on 1-month mocked data → produces BacktestResult with trades > 0 = **1 test**
- End-to-end: strategy with no signals → BacktestResult with 0 trades, no error = **1 test**
- DB output: SQLite file created at expected path with correct naming convention (DEC-056) = **1 test**
- Log level config: WARNING suppresses per-bar debug, DEBUG enables it = **1 test**
- **Total: ~15 tests**

---

## Session 6: Walk-Forward Integration + Equivalence Validation

**Objective:** Wire BacktestEngine into walk_forward.py as an alternative OOS engine, and write directional equivalence tests comparing BacktestEngine output against Replay Harness on the same data.

**Creates:** None

**Modifies:**
- `argus/backtest/walk_forward.py` (add BacktestEngine OOS execution path alongside existing Replay Harness path)

**Integrates:** S5 (complete BacktestEngine) into existing walk-forward infrastructure

**Parallelizable:** false — depends on S5

**Compaction Risk Score:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (walk_forward.py) | 1 |
| Context reads | 3 (walk_forward.py, engine.py from S5, config.py) | 3 |
| New tests | ~13 | 6.5 |
| Complex integration | — | 0 |
| External API debugging | — | 0 |
| Large files (>150 lines) | — | 0 |
| **Total** | | **10.5** |

**Risk Level:** Medium — proceed

**Test Estimates:**
- WF integration: BacktestEngine OOS path produces WindowResult with valid metrics = **2 tests**
- WF integration: engine selection parameter correctly routes to BacktestEngine vs Replay Harness = **2 tests**
- WF preservation: existing Replay Harness OOS path still works identically = **2 tests**
- WF preservation: existing CLI modes produce same output (regression) = **1 test**
- Directional equivalence: ORB Breakout on same 1-month data → BacktestEngine and Replay Harness produce similar trade count (within 20%), similar gross P&L direction (same sign) = **2 tests**
- Directional equivalence: VWAP Reclaim on same data → similar directional results = **1 test**
- Divergence documentation: test that explicitly documents expected divergence sources (fill price differences from tick synthesis vs bar-level) = **1 test**
- Speed benchmark: BacktestEngine ≥5x faster than Replay Harness on same data (timed execution) = **1 test**
- WF config: BacktestEngine works with WalkForwardConfig date windows = **1 test**
- **Total: ~13 tests**

---

## Summary

| Session | Scope | Score | Risk | Tests | Parallelizable |
|---------|-------|-------|------|-------|----------------|
| S1 | SyncEventBus + Config | 11.5 | Medium | ~13 | ✅ (with S2) |
| S2 | HistoricalDataFeed | 13 | Medium | ~12 | ✅ (with S1) |
| S3 | Engine setup + factory | 14 | Borderline* | ~12 | ❌ |
| S4 | Bar loop + fill model | 11.5 | Medium | ~15 | ❌ |
| S5 | Multi-day + results + CLI | 11.5 | Medium | ~15 | ❌ |
| S6 | WF integration + equiv | 10.5 | Medium | ~13 | ❌ |
| **Total** | | | | **~80** | |

*S3 justified at 14: direct adaptation of ReplayHarness._setup() pattern, not novel integration.
