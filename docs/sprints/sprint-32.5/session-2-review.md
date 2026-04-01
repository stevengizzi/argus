---BEGIN-REVIEW---

# Tier 2 Review: Sprint 32.5, Session 2

**Reviewer:** Tier 2 Automated Review
**Session:** Sprint 32.5, Session 2 (DEF-132: exit_overrides in spawner + runner grid)
**Commit:** c60569f
**Date:** 2026-04-01

---

## 1. Scope Compliance

The session implemented exactly what was specified:

1. **Spawner exit_overrides wiring** -- `_dotpath_to_nested()` helper converts flat dot-path keys to nested dicts, `deep_update` (from `argus.core.config`) is imported for runtime application, `exit_overrides_raw` is passed to `compute_parameter_fingerprint()` and to `VariantDefinition`, and `exit_overrides_nested` is stored as `_exit_overrides` on the spawned strategy instance.

2. **Runner grid expansion** -- `generate_parameter_grid()` accepts optional `exit_sweep_params`, `_generate_exit_values()` produces step-spaced floats, cross-product of detection x exit grids is computed via `itertools.product`, and `run_sweep()` handles both flat and structured grid formats.

3. **16 new tests** written (minimum was 8), covering all specified requirements plus bonus unit tests for helpers.

No scope expansion detected. No files outside the expected set were modified.

## 2. Do-Not-Modify Compliance

Verified via `git diff main...HEAD` scoped to protected files:
- `core/events.py` -- CLEAN
- `core/config.py` -- CLEAN
- `core/exit_math.py` -- CLEAN
- `execution/order_manager.py` -- CLEAN
- `intelligence/counterfactual.py` -- CLEAN
- Strategy files under `strategies/` -- CLEAN (only `strategies/patterns/factory.py` was modified, which is the pattern factory, not a strategy file)

## 3. Review Focus Items

### 3.1 Spawner uses `deep_update()` correctly
PASS. Line 18 of spawner.py imports `deep_update` from `argus.core.config`. The helper `_dotpath_to_nested()` converts flat dot-path keys to nested dicts suitable for `deep_update()`. No custom merge logic was introduced.

### 3.2 Grid cross-product math: N detection x M exit = NxM points
PASS. `itertools.product(detection_grid, exit_grid)` on runner.py line 161. Test 5 (`test_combined_grid_size_is_detection_times_exit`) verifies 6 detection x 4 exit = 24 grid points.

### 3.3 `exit_overrides=None` path identical to pre-change spawner behavior
PASS. When `exit_overrides` is absent from variant def, `exit_overrides_raw` evaluates to `None` (via `variant_def.get("exit_overrides") or None`), `exit_overrides_nested` is `None`, fingerprint receives `exit_overrides=None` which falls through to detection-only hash, `_exit_overrides` is set to `None`, and `VariantDefinition` uses the default `None`. Test 15 (`test_spawner_without_exit_overrides_unchanged`) and Test 16 (`test_fingerprint_with_none_exit_overrides_matches_detection_only`) verify this.

### 3.4 Fingerprint includes exit_overrides
PASS. Spawner line 194-195 passes `exit_overrides=exit_overrides_raw` to `compute_parameter_fingerprint()`. The factory function (lines 234-241) namespaces the payload as `{"detection": ..., "exit": ...}` when exit_overrides is truthy, producing a different hash. Test 6 (`test_spawner_fingerprint_changes_with_exit_overrides`) verifies two variants identical except for exit_overrides get different fingerprints.

### 3.5 ExitSweepParam dot-path resolution tested
PASS. Tests 9-12 cover `_dotpath_to_nested` for single-level, multi-level, multiple-keys-same-parent, and empty input. Tests 1 and 3 verify end-to-end that dot-path strings in exit_overrides are correctly carried through to the grid and strategy.

## 4. Regression Checklist

| Check | Result |
|-------|--------|
| `compute_parameter_fingerprint()` with `exit_overrides=None` identical hash | PASS -- Test 16 verifies `fp_no_arg == fp_none == fp_empty` |
| Different exit_overrides produce different fingerprints | PASS -- Test 6 |
| Deterministic hashing | PASS -- sort_keys=True on canonical JSON |
| experiments.yaml without exit fields loads | PASS -- `exit_sweep_params: list[ExitSweepParam] | None = None` default |
| `ExperimentConfig` `extra="forbid"` rejects unknown keys | PASS -- model_config unchanged on line 66 |
| bull_flag and flat_top_breakout unchanged | PASS -- no changes to engine.py strategy factory |
| experiments.enabled=false gating | PASS -- no changes to gating logic |
| Full test suite health | PASS -- 4,457 passed (matches close-out) |

## 5. Findings

### F1: `_exit_overrides` set as dynamic instance attribute (LOW)

The spawner sets `variant_strategy._exit_overrides = exit_overrides_nested` as a dynamic instance attribute (spawner.py line 259) rather than declaring it on the class. This is intentional per judgment call #3 in the close-out (strategy files must not be modified). The close-out correctly identifies that the calling code in `main.py` will need to read this attribute when registering with OrderManager. This is acceptable for now but creates a coupling point that lacks type safety -- the attribute has no type annotation and could be missed by static analysis. Documented, not blocking.

### F2: Runner stores full structured dict in ExperimentRecord.parameters (INFO)

When exit_sweep_params is active, `ExperimentRecord.parameters` receives the structured dict `{"detection_params": {...}, "exit_overrides": {...}}` (runner.py line 271-272, via `parameters=params`). This means the parameters field has two possible shapes depending on whether exit sweep was used. Consumers of this field will need to handle both formats. This is acknowledged by the close-out (judgment call #4) and consistent with the grid format duality approach.

### F3: BacktestEngine does not apply exit_overrides (INFO)

As documented in judgment call #4, `BacktestEngineConfig.config_overrides` receives only detection params (runner.py line 309). Exit overrides are stored in the ExperimentRecord but not forwarded to BacktestEngine. This is intentional -- the runner's purpose is pre-filtering detection params; exit refinement happens during shadow trading. No action needed now, but a future session will need to wire exit_overrides into BacktestEngine if backtest-level exit param evaluation is desired.

## 6. Escalation Criteria Check

| Trigger | Status |
|---------|--------|
| Fingerprint backward incompatibility | NOT TRIGGERED -- golden hash test passes |
| BacktestEngine reference data changes beyond engine.py | NOT TRIGGERED |
| ExperimentConfig extra="forbid" conflict | NOT TRIGGERED -- exit_sweep_params added cleanly |
| Trade Log tab breaks existing page | N/A (not in S2 scope) |
| 9th page navigation breaks shortcuts | N/A (not in S2 scope) |

## 7. Test Results

- Scoped: `tests/intelligence/experiments/` -- 82 passed (66 baseline + 16 new)
- Full suite: 4,457 passed, 0 failures (47.69s with xdist)

## 8. Verdict

**CLEAR** -- All scope items implemented correctly. No deviations from spec. No do-not-modify violations. All regression checks pass. The two informational findings (F1, F2) are documented design decisions consistent with the close-out's judgment calls and do not rise to CONCERNS level. Full test suite green.

---END-REVIEW---

```json:structured-verdict
{
  "session": "Sprint 32.5, Session 2",
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F1",
      "severity": "LOW",
      "description": "_exit_overrides set as dynamic instance attribute on strategy — lacks type annotation, coupling point for future main.py wiring",
      "action": "none — intentional per do-not-modify constraint on strategy files"
    },
    {
      "id": "F2",
      "severity": "INFO",
      "description": "ExperimentRecord.parameters has two possible shapes (flat dict vs structured dict with detection_params/exit_overrides)",
      "action": "none — documented design decision, consumers must handle both formats"
    },
    {
      "id": "F3",
      "severity": "INFO",
      "description": "BacktestEngine does not apply exit_overrides from grid — only detection params forwarded",
      "action": "none — intentional per close-out judgment call #4"
    }
  ],
  "tests": {
    "scoped": "82 passed",
    "full_suite": "4457 passed, 0 failures"
  },
  "escalation_triggers": [],
  "regression_checklist": {
    "fingerprint_backward_compat": "PASS",
    "config_backward_compat": "PASS",
    "backtest_engine_unchanged": "PASS",
    "config_gating": "PASS",
    "test_suite_health": "PASS"
  }
}
```
