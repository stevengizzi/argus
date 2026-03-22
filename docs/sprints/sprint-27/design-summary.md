# Sprint 27 Design Summary

**Sprint Goal:** Build the BacktestEngine Core — a production-code backtesting engine that runs real strategy code against Databento OHLCV-1m historical data via synchronous dispatch, achieving ≥5x speed over the Replay Harness. Backend only, no UI.

**Execution Mode:** Human-in-the-loop

**Session Breakdown:**
- Session 1: SynchronousEventBus + BacktestEngineConfig
  - Creates: `argus/core/sync_event_bus.py`, additions to `argus/backtest/config.py`
  - Modifies: `argus/backtest/config.py` (StrategyType enum: add BULL_FLAG, FLAT_TOP_BREAKOUT; new BacktestEngineConfig model)
  - Integrates: N/A (foundational)
  - Parallelizable: true (with S2)
  - Score: 11.5 (Medium)
- Session 2: HistoricalDataFeed (Databento download + cache + CandleEvent conversion)
  - Creates: `argus/backtest/historical_data_feed.py`
  - Modifies: None
  - Integrates: N/A (standalone data layer)
  - Parallelizable: true (with S1)
  - Score: 13 (Medium)
- Session 3: BacktestEngine — component assembly + strategy factory
  - Creates: `argus/backtest/engine.py` (partial: __init__, _setup, _create_strategy for all 7 types, _teardown)
  - Modifies: None
  - Integrates: S1 (SyncEventBus, BacktestEngineConfig), existing BacktestDataService
  - Parallelizable: false
  - Score: 14 (Borderline — justified by Replay Harness _setup() serving as direct template)
- Session 4: BacktestEngine — single-day bar loop + bar-level order fill model
  - Creates: None
  - Modifies: `argus/backtest/engine.py` (extend with _run_trading_day, _process_bar_fills)
  - Integrates: S3 output, S2 (HistoricalDataFeed for data loading)
  - Parallelizable: false
  - Score: 11.5 (Medium)
- Session 5: BacktestEngine — multi-day orchestration + scanner + results + CLI
  - Creates: None
  - Modifies: `argus/backtest/engine.py` (extend with run(), multi-day loop, CLI entry point)
  - Integrates: S4, existing metrics.py + scanner_simulator.py
  - Parallelizable: false
  - Score: 11.5 (Medium)
- Session 6: Walk-forward integration + equivalence validation tests
  - Creates: None
  - Modifies: `argus/backtest/walk_forward.py` (add BacktestEngine OOS path)
  - Integrates: S5 (complete engine) into existing walk-forward infrastructure
  - Parallelizable: false
  - Score: 10.5 (Medium)

**Key Decisions:**
- SynchronousEventBus as a new class (not a mode flag on EventBus) — ~40 lines, same async method signatures, sequential dispatch via direct await. Speed gain from eliminating task creation, locks, sleep(0), and tick synthesis.
- Result equivalence = "correct against OHLCV-1m with worst-case fill priority" — NOT trade-for-trade identical to Replay Harness. Bar-level fill model: stop > target > time_stop > EOD. More conservative than tick-synthesis approach. Directional comparison only.
- No tick synthesis — the biggest speed win. Strategies fire on CandleEvent, fill simulation checks bar OHLC directly.
- Strategy factory covers all 7 types: ORB Breakout, ORB Scalp, VWAP Reclaim, AfMo, Red-to-Green (BaseStrategy subclasses) + Bull Flag, Flat-Top Breakout (PatternBasedStrategy wrapper).
- HistoricalDataFeed downloads from Databento API (free OHLCV-1m on Standard plan per DEC-353). Cost validation via `metadata.get_cost()` before every download. Cache as Parquet per symbol-month in `data/databento_cache/`.
- DEF-088 (PatternParam structured type) stays deferred — not needed until Sprint 32.
- DEF-089 (new): In-memory ResultsCollector for parallel sweeps — deferred to Sprint 32. Sprint 27 uses existing TradeLogger → SQLite → compute_metrics() pipeline.
- Logging verbosity config option in BacktestEngineConfig (default WARNING during runs).

**Scope Boundaries:**
- IN: SyncEventBus, BacktestEngineConfig, HistoricalDataFeed, BacktestEngine (all 7 strategies), bar-level fill model, walk-forward integration, CLI, ~80 tests
- OUT: Research Console UI (Sprint 31), multiprocessing/parallel sweeps (Sprint 32), parameterized strategy templates (Sprint 32), multi-strategy concurrent backtesting, live Databento API calls in tests, DEF-088, modifying Replay Harness or VectorBT, any frontend changes, Quality Engine/NLP pipeline in backtest mode (bypass via BrokerSource.SIMULATED)

**Regression Invariants:**
- All existing walk_forward.py CLI modes produce identical output
- All existing backtest tests pass unchanged (VectorBT, Replay Harness)
- Production EventBus class untouched
- No production runtime code modified (all changes in argus/backtest/ + argus/core/sync_event_bus.py)
- Existing StrategyType enum values unchanged (additive only)
- BacktestDataService unchanged (reused as-is)

**File Scope:**
- Create: `argus/core/sync_event_bus.py`, `argus/backtest/historical_data_feed.py`, `argus/backtest/engine.py`
- Modify: `argus/backtest/config.py`, `argus/backtest/walk_forward.py`
- Do not modify: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, `argus/backtest/vectorbt_*.py`, any `argus/strategies/` files, any `argus/ui/` files, any `argus/api/` files

**Config Changes:**
New `BacktestEngineConfig` model in `argus/backtest/config.py`:

| Field | Pydantic Field Name | Type | Default |
|-------|-------------------|------|---------|
| engine_mode | `engine_mode` | `str` | `"sync"` |
| data_source | `data_source` | `str` | `"databento"` |
| cache_dir | `cache_dir` | `Path` | `Path("data/databento_cache")` |
| verify_zero_cost | `verify_zero_cost` | `bool` | `True` |
| log_level | `log_level` | `str` | `"WARNING"` |

New StrategyType enum values:

| Value | Enum Name |
|-------|-----------|
| `"bull_flag"` | `BULL_FLAG` |
| `"flat_top_breakout"` | `FLAT_TOP_BREAKOUT` |

No system.yaml or system_live.yaml changes. These are CLI/config-file parameters for the backtest subsystem only.

**Test Strategy:**
- ~80 new tests total across 6 sessions
- S1: ~13 tests (SyncEventBus: subscribe/publish/drain/sequence/error isolation/reset; EngineConfig: validation, strategy type enum)
- S2: ~12 tests (download mock, cache hit/miss, incremental update, cost validation, CandleEvent conversion, date range filtering, error handling)
- S3: ~12 tests (component assembly, strategy factory for all 7 types, teardown cleanup)
- S4: ~15 tests (single-day bar processing, fill model: stop priority, target hits, time stop, EOD flatten, no-trade days, multi-symbol interleaving)
- S5: ~15 tests (multi-day orchestration, daily state reset, scanner integration, results computation, CLI argument parsing, empty data handling)
- S6: ~13 tests (walk-forward BacktestEngine OOS path, existing WF modes preserved, directional equivalence with Replay Harness)
- All tests use mocked data / fixtures — no live Databento API calls
- Test baseline: 2,925 pytest + 620 Vitest

**Runner Compatibility:**
- Mode: human-in-the-loop (work journal handoff generated)
- Parallelizable sessions: S1 and S2 (independent outputs, no shared files)
- Estimated token budget: ~6 sessions × ~15K tokens avg = ~90K tokens
- Runner config generated as fallback but not primary execution mode

**Dependencies:**
- Sprint 26 complete (all 7 strategies implemented and tested)
- Databento Standard plan active (EQUS.MINI OHLCV-1m access)
- Existing backtest infrastructure unchanged (BacktestDataService, SimulatedBroker, FixedClock, compute_metrics, ScannerSimulator)

**Escalation Criteria:**
- SynchronousEventBus produces different event ordering than expected (sequence number assignment, handler dispatch order)
- Bar-level fill model produces nonsensical results (negative P&L on clearly profitable setups, or vice versa)
- Databento OHLCV-1m cost is non-zero (blocks HistoricalDataFeed)
- Speed benchmark fails (<5x vs Replay Harness)
- Any existing strategy test fails after BacktestEngine changes

**Doc Updates Needed:**
- `docs/project-knowledge.md` — add BacktestEngine to architecture, update test counts, add Sprint 27 to history
- `CLAUDE.md` — update active sprint, test counts, known issues
- `docs/decision-log.md` — new DEC entries (DEC-357+)
- `docs/dec-index.md` — index new DECs
- `docs/sprint-history.md` — Sprint 27 entry
- `docs/roadmap.md` — mark Sprint 27 complete, update current state
- `docs/architecture.md` — add BacktestEngine section

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with scoring tables)
4. Escalation Criteria
5. Regression Checklist
6. Doc Update Checklist
7. Review Context File
8. Implementation Prompts ×6
9. Review Prompts ×6
10. Work Journal Handoff Prompt
11. Runner Configuration (fallback)
