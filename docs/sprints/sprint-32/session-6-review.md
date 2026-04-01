# Sprint 32 Session 6 — Tier 2 Review Report

---BEGIN-REVIEW---

## Session Under Review
**Sprint 32, Session 6: Experiment Runner (Backtest Pre-Filter)**
**Reviewer:** Tier 2 Automated Review (Opus 4.6)
**Date:** 2026-04-01

---

## 1. Scope Compliance

| Spec Requirement | Implemented | Notes |
|-----------------|-------------|-------|
| `runner.py` with ExperimentRunner | YES | Clean single-file implementation |
| `generate_parameter_grid()` via PatternParam introspection | YES | No hardcoded param names |
| Grid generation: int/float/bool/default routing | YES | All four paths covered |
| Grid cap at 500 with WARNING | YES | `_GRID_CAP = 500`, WARNING logged |
| Grid is deterministic | YES | Tested via `test_grid_is_deterministic` |
| `run_sweep()` with BacktestEngine | YES | Full lifecycle implemented |
| Duplicate fingerprint detection | YES | Checked before running backtest |
| Pre-filter: expectancy + trade count | YES | Thresholds from config |
| Dry run mode | YES | Returns empty, no engine calls |
| Exception handling around BacktestEngine | YES | Graceful FAILED status |
| `estimate_sweep_time()` | YES | ~30s/point baseline |
| Results stored in ExperimentStore | YES | Via `save_experiment()` |
| No modifications to backtest/ directory | YES | Verified via git status |
| No numpy dependency | YES | Pure Python float ranges |
| No imports from argus/ui/ | YES | Confirmed by inspection |

**Verdict: All spec requirements met. No scope deviations.**

---

## 2. Review Focus Items

### F1: Grid generation uses PatternParam introspection only
**PASS.** `generate_parameter_grid()` calls `get_pattern_class()` from factory, instantiates with defaults, and calls `get_default_params()` to obtain `PatternParam` objects. Value generation is driven entirely by `PatternParam.param_type`, `min_value`, `max_value`, and `step` attributes. No param names are hardcoded anywhere in the grid generation logic.

### F2: BacktestEngine is mocked in tests
**PASS.** All sweep tests use `patch("argus.intelligence.experiments.runner.BacktestEngine", ...)` to inject mock engines. No real backtest runs occur. The `_make_engine_mock()` helper constructs appropriately configured mock objects.

### F3: Pre-filter thresholds from config
**PASS.** `backtest_min_expectancy` and `backtest_min_trades` are read from the `config` dict in `__init__()` with sensible defaults (0.0 and 10 respectively). Tests exercise different threshold values to confirm they are respected.

### F4: Grid cap at 500 with WARNING
**PASS.** `_GRID_CAP = 500` is a module constant. When `len(combos) > _GRID_CAP`, a `logger.warning()` is emitted. Two tests verify this: `test_grid_cap_warning_logged` (synthetic 600-point grid) and `test_grid_bull_flag_exceeds_cap_and_warns` (real BullFlagPattern).

Note: The grid is not actually truncated at 500 -- only a WARNING is logged. The spec says "cap grid size: if cartesian product exceeds 500 points, log WARNING and suggest param_subset." This matches the spec. However, callers should be aware that grids can be arbitrarily large (BullFlag is ~192,000 points). This is documented in the close-out.

### F5: Exception handling around BacktestEngine calls
**PASS.** The outer `try/except Exception` block at line 270 catches any `BacktestEngine.run()` failure and sets `record.status = ExperimentStatus.FAILED`. The inner `try/except` at line 249 handles `to_multi_objective_result()` failures with a fallback to `_backtest_result_to_dict()`. Both paths persist the record and log appropriately.

### F6: Duplicate fingerprint check before running backtest
**PASS.** `_find_by_fingerprint()` is called before creating the ExperimentRecord at line 185. If a match is found, the grid point is skipped with an INFO log and `continue`. The test `test_duplicate_fingerprint_is_skipped` verifies no engine calls or store writes occur for duplicates.

---

## 3. Findings

### F-01: Linear scan for duplicate detection (LOW)
`_find_by_fingerprint()` calls `list_experiments(pattern_name=..., limit=10_000)` and does a linear scan. For practical experiment counts this is fine, but at scale (e.g., 10,000+ experiments for a single pattern), this becomes O(N) per grid point, making the full sweep O(N*M) where M is the grid size. The close-out report acknowledges this as judgment call #3 and correctly notes that adding a dedicated query would require modifying `store.py` (out of scope). This is acceptable for the current stage.

### F-02: `config_overrides` vs `risk_overrides` naming (INFORMATIONAL)
The runner passes `config_overrides=params` to `BacktestEngineConfig` (line 239), which is the correct field for strategy detection parameters. The `risk_overrides` field uses its permissive default (DEC-359). The close-out mentions "permissive risk_overrides (DEC-359)" which is accurate since the default handles this. No action needed.

### F-03: Float range generation is sound (POSITIVE)
The close-out's judgment call #1 explains the choice of `round((max-min)/step)` over `int()`. This is correct: `int(4.999...)` yields 4, but `round(4.999...)` yields 5. The implementation at line 403 avoids floating-point drift. Tests verify float values match expected ranges.

### F-04: No `risk_overrides` explicitly set in BacktestEngineConfig construction (INFORMATIONAL)
Line 232-239 constructs `BacktestEngineConfig` without explicitly passing `risk_overrides`. This relies on the default value in `BacktestEngineConfig` which provides permissive overrides (DEC-359). This is correct behavior -- the defaults were specifically designed for single-strategy backtesting.

### F-05: `_backtest_result_to_dict` uses `dataclasses.asdict()` with `# type: ignore` (LOW)
Line 445 has `# type: ignore[call-overload]` on `dataclasses.asdict(result)`. This is necessary because the function accepts `object` as the `result` parameter type (for flexibility), but `asdict()` expects a dataclass instance. The preceding `is_dataclass()` check guards correctness. The type ignore is appropriately scoped with the specific error code.

---

## 4. Protected File Verification

| File/Directory | Modified? | Status |
|---------------|-----------|--------|
| `argus/backtest/` | NO | PASS |
| `argus/main.py` | NO | PASS |
| `argus/strategies/` | NO | PASS |
| `argus/intelligence/experiments/store.py` | NO | PASS |
| `argus/intelligence/experiments/models.py` | NO | PASS |
| `argus/intelligence/experiments/__init__.py` | NO | PASS |

All verified via `git status` and `git diff`. Session 6 files are untracked (new additions only).

---

## 5. Test Results

| Suite | Result |
|-------|--------|
| `tests/intelligence/experiments/test_runner.py` | 21/21 passed |
| `tests/intelligence/experiments/` (full) | 42/42 passed |

Test coverage is thorough across all code paths:
- 5 unit tests for `_generate_param_values` (int, float, bool, string, subset exclusion)
- 7 grid generation tests (size, types, subset, cap warning, determinism, real BullFlag)
- 7 sweep tests (store persistence, pre-filter pass/fail, dry run, duplicate skip, engine exception)
- 2 utility tests (estimate_sweep_time formatting and zero case)

---

## 6. Regression Checklist

| # | Check | Result |
|---|-------|--------|
| R1-R16 | Sprint-level regression items | No violations detected (no protected files modified) |
| Session-specific | No existing files modified | PASS |
| Session-specific | BacktestEngine API unchanged | PASS |
| Session-specific | Grid generation deterministic | PASS (test verified) |
| Session-specific | Pre-existing experiment tests pass | PASS (42/42) |

---

## 7. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Shadow variants cause >10% throughput degradation | N/A (no live variants) |
| Variant spawning >2x memory | N/A (no spawning in this session) |
| Event Bus contention from 35+ subscribers | N/A |
| Parameter fingerprint hash collision | NOT TRIGGERED |
| CounterfactualTracker volume handling | N/A |
| Factory fails existing pattern construction | NOT TRIGGERED |
| ARGUS fails to start with experiments.enabled: false | N/A (no startup changes) |
| Pre-existing test failure introduced | NOT TRIGGERED |
| YAML param silently ignored | N/A (no YAML changes) |

**No escalation criteria triggered.**

---

## 8. Close-Out Report Assessment

The close-out report is accurate and complete:
- Change manifest correctly lists only new files
- Implementation summary matches actual code
- Judgment calls are well-reasoned and documented
- Scope verification table is accurate (all items verified)
- Test results match actual runs (21 new, 42 total)
- Self-assessment of CLEAN is justified
- Context state GREEN is appropriate

---

## 9. Verdict

**CLEAR** -- Implementation matches spec precisely, all tests pass, no protected files modified, no regressions detected, no escalation criteria triggered. Code quality is high with good separation of concerns (pure functions for grid generation and fingerprinting, async methods for sweep orchestration). The linear scan for duplicate detection (F-01) is a known limitation acknowledged in the close-out and constrained by the no-modify rule on store.py.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F-01",
      "severity": "LOW",
      "category": "performance",
      "description": "_find_by_fingerprint() uses linear scan over list_experiments(limit=10_000). O(N) per grid point. Acceptable given store.py is out of scope for modification.",
      "file": "argus/intelligence/experiments/runner.py",
      "line": 361,
      "recommendation": "Add get_by_fingerprint() to ExperimentStore in a future session."
    },
    {
      "id": "F-05",
      "severity": "LOW",
      "category": "type-safety",
      "description": "_backtest_result_to_dict uses type: ignore[call-overload] on dataclasses.asdict(). Guarded by is_dataclass() check.",
      "file": "argus/intelligence/experiments/runner.py",
      "line": 445,
      "recommendation": "No action needed — type ignore is appropriately scoped."
    }
  ],
  "tests_passed": true,
  "tests_new": 21,
  "tests_total_suite": 42,
  "protected_files_clean": true,
  "escalation_triggered": false,
  "close_out_accurate": true
}
```
