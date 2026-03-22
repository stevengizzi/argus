# Sprint 27: Regression Checklist

Verify each of these after every session:

## Core Invariants

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

## Test Suite Integrity

| # | Check | How to Verify |
|---|-------|---------------|
| R9 | Existing pytest count unchanged | Run full suite; count ≥ 2,925 (excluding new tests) |
| R10 | Existing Vitest count unchanged | `cd argus/ui && npx vitest run`; count = 620 |
| R11 | No test hangs | Full suite completes within 10 minutes |
| R12 | xdist compatibility preserved | `python -m pytest --ignore=tests/test_main.py -n auto -q` passes |

## Backtest Subsystem

| # | Check | How to Verify |
|---|-------|---------------|
| R13 | Existing StrategyType enum values resolve | `StrategyType("orb")`, `StrategyType("orb_scalp")`, etc. all work |
| R14 | BacktestConfig model backward compatible | Existing BacktestConfig instantiation (no new required fields) works |
| R15 | ScannerSimulator unchanged | `git diff HEAD argus/backtest/scanner_simulator.py` → no changes |
| R16 | compute_metrics() unchanged | `git diff HEAD argus/backtest/metrics.py` → no changes |
| R17 | Walk-forward existing modes preserved | Existing WF CLI modes produce identical output (tested in S6) |

## Config Validation

| # | Check | How to Verify |
|---|-------|---------------|
| R18 | New StrategyType values don't break existing switch logic | Grep for StrategyType usage in walk_forward.py and replay_harness.py — existing branches still match |
| R19 | BacktestEngineConfig fields match intended names | Load config, verify all fields recognized by Pydantic (no silently ignored keys) |
