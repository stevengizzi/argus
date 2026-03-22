# Sprint 27 Session 6 — Tier 2 Review

---BEGIN-REVIEW---

## Verdict: CLEAR

## Findings

1. **[NOTE] Equivalence tests use mocked data, not shared real data.** The directional equivalence tests (tests 8-10, 12) mock both engines independently with predetermined values rather than running both engines against the same actual dataset. This means the tests verify the wiring and result-shape contract, but do not validate real-world directional agreement. This is acceptable for unit-level testing and is documented in the closeout (judgment call #3), but the user should be aware that real equivalence validation requires running both engines on actual historical data.

2. **[NOTE] Speed benchmark is simulated.** Test 12 (`test_speed_benchmark`) uses `asyncio.sleep` delays to simulate the 5x speed ratio. This tests the timing harness logic but not actual engine performance. Again, documented in the closeout and acceptable for CI stability, but real performance benchmarking should be done separately.

3. **[NOTE] `_build_config_overrides` fallback returns raw `best_params`.** For unknown strategy names, the function returns `dict(best_params)` without translation (line ~876 in the diff). This is a reasonable fallback but could silently pass incorrect parameter names if a new strategy is added to `_STRATEGY_TYPE_MAP` without a corresponding `_build_config_overrides` branch. Low risk since the map and overrides are co-located and both need updating together.

4. **[NOTE] `oos_engine` field is a plain string, not an enum or Literal type.** The field accepts any string value at the dataclass level, with validation only at the CLI argparse layer (`choices=["replay_harness", "backtest_engine"]`). Programmatic callers could pass invalid values. Low risk -- the `validate_out_of_sample` function falls through to the Replay Harness path for any value other than `"backtest_engine"`, so invalid values degrade gracefully.

## Regression Checks

| # | Check | Result |
|---|-------|--------|
| R1 | Production EventBus unchanged | PASS — no diff |
| R2 | Replay Harness unchanged | PASS — no diff |
| R3 | BacktestDataService unchanged | PASS — no diff |
| R4 | All VectorBT files unchanged | PASS — no diff |
| R5 | All strategy files unchanged | PASS — no diff |
| R6 | No frontend files modified | PASS — no diff |
| R7 | No API files modified | PASS — no diff |
| R8 | No system.yaml changes | PASS — no diff |
| R9 | Existing pytest count >= 2,925 | PASS — 3,010 total (2,925 baseline + 85 Sprint 27) |
| R10 | Vitest count = 620 | PASS — no frontend changes, count unchanged |
| R11 | No test hangs | PASS — completed in 40.57s |
| R12 | xdist compatibility | PASS — `-n auto` clean |
| R13 | Existing StrategyType enum values resolve | PASS — no changes to enum definition |
| R14 | BacktestConfig backward compatible | PASS — no changes to BacktestConfig |
| R15 | ScannerSimulator unchanged | PASS — no diff |
| R16 | compute_metrics() unchanged | PASS — no diff |
| R17 | Walk-forward existing modes preserved | PASS — default oos_engine="replay_harness", existing path untouched |
| R18 | New StrategyType values don't break existing switch logic | PASS — no new StrategyType values added in S6 |
| R19 | BacktestEngineConfig fields match intended names | PASS — config instantiation tested |

## Escalation Criteria Check

| # | Criterion | Triggered? |
|---|-----------|-----------|
| EC-8 | Any existing walk_forward.py CLI mode produces different output after changes | NO — default oos_engine is "replay_harness"; existing paths untouched |
| EC-9 | Any existing backtest test fails | NO — 3,010 passed, 0 failures |

No escalation criteria triggered.

## Test Results

- **Full pytest suite:** 3,010 passed, 0 failed (40.57s with `-n auto`)
- **New S6 tests:** 13 tests in `tests/backtest/test_walk_forward_engine.py`
- **Sprint 27 total new tests:** 85 (exceeds sprint target of ~80)
- **Vitest:** 620 (unchanged, no frontend modifications)

## Session-Specific Review Focus Results

1. **Existing Replay Harness OOS path unchanged:** VERIFIED. The new BacktestEngine path is an early-return conditional (`if config.oos_engine == "backtest_engine"`) inserted before the existing strategy dispatch if/elif chain. The existing code at lines 727-736 is byte-for-byte identical to the pre-session state.

2. **oos_engine defaults to "replay_harness" everywhere:** VERIFIED. WalkForwardConfig (line 140), WindowResult (line 183), WalkForwardResult (line 212), CLI `--oos-engine` default (line 2482), and `load_walk_forward_results` fallback (lines 1672, 1696) all default to `"replay_harness"`.

3. **Directional equivalence tests use same data for both engines:** PARTIALLY — tests use independently mocked data with predetermined values. Both engines receive the same date range and params, but results are mocked rather than computed from shared input data. This is acceptable for unit tests (see Finding #1).

4. **Speed benchmark methodology:** Fair within its simulated scope. Both paths go through the same `validate_out_of_sample` dispatch with controlled delays. Not a real performance test (see Finding #2).

5. **`--oos-engine` CLI flag:** VERIFIED. Properly wired in `parse_args()` with `choices` validation and propagated to both `run_walk_forward` and `run_fixed_params_walk_forward` config construction.

6. **JSON output includes oos_engine field:** VERIFIED. Present in both summary JSON (`save_walk_forward_results` line 1553) and windows CSV (line 1585). Round-trip loading handles missing field gracefully with `"replay_harness"` default.

## Summary

Session 6 cleanly wires the BacktestEngine as an alternative OOS validation engine in walk_forward.py. The implementation is purely additive -- the existing Replay Harness path is untouched, `oos_engine` defaults to `"replay_harness"` everywhere, and the CLI flag provides safe selection with argparse validation. All 3,010 tests pass, all 19 regression checks clear, and no escalation criteria are triggered.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "session": "Sprint 27 Session 6",
  "reviewer": "Tier 2 Automated Review",
  "timestamp": "2026-03-22T00:00:00Z",
  "findings_count": {
    "critical": 0,
    "major": 0,
    "minor": 0,
    "note": 4
  },
  "tests": {
    "pytest_total": 3010,
    "pytest_passed": 3010,
    "pytest_failed": 0,
    "new_tests": 13,
    "sprint_new_tests": 85,
    "vitest_total": 620
  },
  "regression_checks": {
    "total": 19,
    "passed": 19,
    "failed": 0
  },
  "escalation_criteria_triggered": false,
  "summary": "Clean additive integration of BacktestEngine as alternative OOS engine in walk_forward.py. Existing Replay Harness path untouched, defaults preserve backward compatibility, all tests pass."
}
```
