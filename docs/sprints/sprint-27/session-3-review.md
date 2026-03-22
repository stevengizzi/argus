---BEGIN-REVIEW---

# Sprint 27 Session 3 — Tier 2 Review

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-22
**Session:** Sprint 27 S3 — BacktestEngine Component Assembly + Strategy Factory
**Verdict:** CLEAR

## Summary

Session 3 delivers `argus/backtest/engine.py` containing the `BacktestEngine` class with full component assembly (`_setup`), a strategy factory covering all 7 strategy types, teardown logic, and a stub `run()` method. The implementation closely follows the `ReplayHarness._setup()` pattern as specified, substituting `SyncEventBus` for `EventBus`. All 14 tests pass. The full suite (2,967 tests) passes with no regressions. All do-not-modify files are untouched.

## Session-Specific Focus Items

### 1. engine.py imports SyncEventBus, NOT EventBus
**PASS.** Line 39: `from argus.core.sync_event_bus import SyncEventBus`. Grep for `from argus.core.event_bus import` in engine.py returns no matches. The production EventBus is never imported.

### 2. _setup() follows ReplayHarness._setup() pattern
**PASS.** The BacktestEngine._setup() (lines 110-193) mirrors ReplayHarness._setup() (lines 238-315) component-for-component in the same order: output directory creation, DB filename generation (DEC-056), event bus initialization (SyncEventBus instead of EventBus), FixedClock, DatabaseManager + TradeLogger, SimulatedBroker with slippage, BacktestDataService, risk config + order manager config from YAML, RiskManager, OrderManager, strategy creation via factory, allocated_capital assignment, candle event subscription. The only structural difference is that BacktestEngine uses `self._config.start_date` directly for the FixedClock initial time rather than `self._trading_days[0]` (since trading_days are not yet populated at setup time in the engine -- they will be populated in S5). This is a reasonable adaptation.

### 3. PatternBasedStrategy used for BULL_FLAG and FLAT_TOP_BREAKOUT
**PASS.** `_create_bull_flag_strategy()` (lines 396-425) creates `BullFlagPattern()` and wraps it in `PatternBasedStrategy(pattern=pattern, config=config, ...)`. `_create_flat_top_breakout_strategy()` (lines 427-456) does the same with `FlatTopBreakoutPattern()`. Tests `test_factory_bull_flag` and `test_factory_flat_top` verify the wrapper type and inner pattern type.

### 4. config_overrides applied to strategy configs
**PASS.** Every factory method calls `self._apply_config_overrides(config)` before constructing the strategy. The `_apply_config_overrides()` method (lines 458-490) uses a generic `model_dump()` -> dict merge -> reconstruct approach that works uniformly across all config types. The test `test_config_overrides_applied` verifies this with `orb_window_minutes: 20`.

### 5. allocated_capital set on strategy after creation
**PASS.** Line 180: `self._strategy.allocated_capital = self._config.initial_cash`. Test `test_allocated_capital_set_on_strategy` verifies this with a custom value of 50,000.

### 6. _teardown matches ReplayHarness._teardown pattern
**PASS.** BacktestEngine._teardown() (lines 564-572) is structurally identical to ReplayHarness._teardown() (lines 752-760): stops OrderManager, closes DatabaseManager, logs DB path.

## Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R1 | Production EventBus unchanged | PASS — `git diff HEAD argus/core/event_bus.py` empty |
| R2 | Replay Harness unchanged | PASS — `git diff HEAD argus/backtest/replay_harness.py` empty |
| R3 | BacktestDataService unchanged | PASS — `git diff HEAD argus/backtest/backtest_data_service.py` empty |
| R5 | All strategy files unchanged | PASS — `git diff HEAD argus/strategies/` empty |

## Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|------------|
| 3 | Strategy behavior differs between BacktestEngine and direct unit test | No — strategy factory creates identical instances |
| 9 | Any existing backtest test fails | No — 2,967 passed, 0 failed |
| 10 | Session compaction before completing core deliverables | No — close-out reports GREEN context state |

## Test Results

- **Scoped tests:** `python -m pytest tests/backtest/test_engine.py -x -q` -- 14 passed in 0.18s
- **Full suite:** `python -m pytest --ignore=tests/test_main.py -n auto -q` -- 2,967 passed in 41.05s
- **New tests added:** 14 (spec required 12 minimum)

## Minor Observations (Non-Blocking)

1. **`type: ignore` comments (3 instances):** The `# type: ignore[arg-type]` on lines 152, 163, 170 are documented in the close-out as a judgment call. SyncEventBus has the same interface as EventBus but is not a subclass. This is acceptable for now; a Protocol-based typing approach could eliminate these in the future but is out of scope.

2. **`_apply_config_overrides` typing:** The method signature uses `object` as parameter and return type rather than a generic or union of config types. This works at runtime but loses type narrowing. The `# type: ignore` comments are the consequence. Minor style concern, not a functional issue.

3. **`_trading_days` typed as `list[object]`:** Line 93 uses `list[object]` as placeholder. This will be refined in S5 when the execution loop populates it. Acceptable for a stub.

## Verdict

**CLEAR** — The implementation matches the spec precisely across all 6 focus areas. All 7 strategy types are supported with correct factory methods. No do-not-modify files were touched. No escalation criteria were triggered. The 14 tests provide good coverage of component assembly, all strategy types, teardown, overrides, and allocated_capital wiring.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 27 S3",
  "title": "BacktestEngine Component Assembly + Strategy Factory",
  "focus_items": {
    "sync_event_bus_import": "PASS",
    "setup_follows_replay_harness": "PASS",
    "pattern_based_strategy_for_patterns": "PASS",
    "config_overrides_applied": "PASS",
    "allocated_capital_set": "PASS",
    "teardown_matches_replay_harness": "PASS"
  },
  "regression_checks": {
    "R1_event_bus_unchanged": "PASS",
    "R2_replay_harness_unchanged": "PASS",
    "R3_backtest_data_service_unchanged": "PASS",
    "R5_strategy_files_unchanged": "PASS"
  },
  "escalation_criteria_triggered": [],
  "tests_scoped": "14 passed",
  "tests_full_suite": "2967 passed",
  "tests_failed": 0,
  "observations_count": 3,
  "blocking_issues": 0
}
```
