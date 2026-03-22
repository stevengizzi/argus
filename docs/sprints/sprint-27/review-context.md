# Sprint 27: Review Context File

> This file is the shared context for all Tier 2 reviews in Sprint 27.
> Each review prompt references this file by path. Do not duplicate this
> content in individual review prompts.

---

## Sprint Spec Summary

**Sprint 27: BacktestEngine Core** — Production-code backtesting engine running real ARGUS strategy code against Databento OHLCV-1m historical data via synchronous event dispatch. ≥5x speed over Replay Harness. Backend only, no UI. 6 sessions, ~80 new tests.

### Deliverables
1. SynchronousEventBus (`argus/core/sync_event_bus.py`)
2. BacktestEngineConfig (additions to `argus/backtest/config.py`)
3. HistoricalDataFeed (`argus/backtest/historical_data_feed.py`)
4. BacktestEngine (`argus/backtest/engine.py`)
5. Walk-forward integration (modifications to `argus/backtest/walk_forward.py`)
6. CLI entry point (in `argus/backtest/engine.py`)

### Key Design Decisions
- SynchronousEventBus: new class, sequential dispatch via direct await, async method signatures preserved
- Bar-level fill model: no tick synthesis, worst-case priority (stop > target > time_stop > EOD)
- Result equivalence: directional (similar trade count/P&L direction), not trade-for-trade identical to Replay Harness
- Engine metadata recorded in output: engine_type + fill_model (AR-1)
- HistoricalDataFeed: fail-closed on cost validation failure (AR-3)
- Walk-forward: oos_engine field in results for attribution (AR-4)

### Session Dependency Chain
```
S1 (SyncBus + Config) ──┐
                         ├──→ S3 (Engine setup) → S4 (Bar loop) → S5 (Multi-day + CLI) → S6 (WF + equiv)
S2 (HistoricalDataFeed) ─┘
```

---

## Specification by Contradiction (Summary)

### Do NOT Modify
- `argus/core/event_bus.py`
- `argus/backtest/replay_harness.py`
- `argus/backtest/backtest_data_service.py`
- `argus/backtest/vectorbt_*.py`
- `argus/backtest/tick_synthesizer.py`
- Any file in `argus/strategies/`, `argus/ui/`, `argus/api/`, `argus/ai/`, `argus/intelligence/`
- `config/system.yaml`, `config/system_live.yaml`

### Out of Scope
- Research Console UI, multiprocessing/parallel sweeps, parameterized strategy templates
- Multi-strategy concurrent backtesting
- In-memory ResultsCollector (DEF-089)
- Quality Engine/NLP pipeline in backtest mode
- Tick synthesis in BacktestEngine

---

## Sprint-Level Regression Checklist

| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` → no changes |
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| R3 | BacktestDataService unchanged | `git diff HEAD argus/backtest/backtest_data_service.py` → no changes |
| R4 | All VectorBT files unchanged | `git diff HEAD argus/backtest/vectorbt_*.py` → no changes |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` → no changes |
| R6 | No frontend files modified | `git diff HEAD argus/ui/` → no changes |
| R7 | No API files modified | `git diff HEAD argus/api/` → no changes |
| R8 | No system.yaml changes | `git diff HEAD config/system.yaml config/system_live.yaml` → no changes |
| R9 | Existing pytest count unchanged | Run full suite; count ≥ 2,925 (excluding new tests) |
| R10 | Existing Vitest count unchanged | `cd argus/ui && npx vitest run`; count = 620 |
| R11 | No test hangs | Full suite completes within 10 minutes |
| R12 | xdist compatibility preserved | `python -m pytest --ignore=tests/test_main.py -n auto -q` passes |
| R13 | Existing StrategyType enum values resolve | `StrategyType("orb")`, `StrategyType("orb_scalp")`, etc. all work |
| R14 | BacktestConfig model backward compatible | Existing BacktestConfig instantiation (no new required fields) works |
| R15 | ScannerSimulator unchanged | `git diff HEAD argus/backtest/scanner_simulator.py` → no changes |
| R16 | compute_metrics() unchanged | `git diff HEAD argus/backtest/metrics.py` → no changes |
| R17 | Walk-forward existing modes preserved | Existing WF CLI modes produce identical output (tested in S6) |
| R18 | New StrategyType values don't break existing switch logic | Grep for StrategyType usage in walk_forward.py and replay_harness.py |
| R19 | BacktestEngineConfig fields match intended names | Config validation test |

---

## Sprint-Level Escalation Criteria

1. SynchronousEventBus produces different handler dispatch order than production EventBus for the same subscription set.
2. Bar-level fill model produces clearly incorrect results (profit when impossible, stop triggered when bar low never reached stop).
3. Strategy behavior differs between BacktestEngine and direct unit test invocation with identical inputs.
4. Databento `metadata.get_cost()` returns non-zero for OHLCV-1m on EQUS.MINI.
5. Databento OHLCV-1m data has significant gaps (>5% missing bars for active symbols during market hours).
6. BacktestEngine is slower than the Replay Harness on equivalent data.
7. BacktestEngine produces ≥50% more or fewer trades than Replay Harness on identical data.
8. Any existing walk_forward.py CLI mode produces different output after Sprint 27 changes.
9. Any existing backtest test fails.
10. Session compaction occurs before completing core deliverables.
