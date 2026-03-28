# Sprint 28, Session 4: Tier 2 Review Report

---BEGIN-REVIEW---

## Review Summary

**Session:** Sprint 28, Session 4 — ConfigProposalManager + Config Change History
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CONCERNS

## Scope Verification

| Requirement | Status | Notes |
|------------|--------|-------|
| ConfigProposalManager with apply_pending() for startup-only application | PASS | Implemented correctly, no in-memory reload |
| Cumulative drift guard (Amendment 2) | PASS | Queries change_history, sums absolute deltas, respects window |
| Atomic write: backup + tempfile + os.rename (Amendment 9) | PASS | Pattern correctly implemented with cleanup on failure |
| YAML parse failure -> CRITICAL + raise (Amendment 1) | PASS | Raises RuntimeError on parse failure and missing file |
| No in-memory config reload (Amendment 1) | PASS | Confirmed: no reload/swap/hot-reload patterns found |
| config/learning_loop.yaml created with all 13 fields | PASS | All 13 fields present, match LearningLoopConfig model exactly |
| Config validation test passing | PASS | test_config_validation_learning_loop_yaml covers all 13 keys |
| >= 12 new tests | PASS | 18 new tests |

## Session-Specific Review Focus Results

### 1. CRITICAL: No in-memory config reload (Amendment 1)
**PASS.** Grep for reload/swap/hot-reload patterns returned zero matches. The `load_quality_engine_config()` helper in quality_engine.py is explicitly documented as NOT used at runtime. `apply_pending()` writes to YAML only; changes take effect at next restart.

### 2. Atomic write pattern: backup -> tempfile -> os.rename
**PASS.** `_write_yaml_atomic()` at line 108 follows the correct pattern: (1) backup current file, (2) mkstemp in same directory, (3) write via fdopen, (4) os.rename for atomic swap, (5) cleanup on exception. Tests verify backup creation and no leftover temp files.

### 3. Cumulative drift guard queries change history correctly
**PASS.** `get_cumulative_drift()` queries `get_change_history(start_date=...)` with a window-based cutoff, filters by field_path, and sums absolute deltas. Test `test_cumulative_drift_query` verifies correctness with two changes (0.05 + 0.03 = 0.08).

### 4. Weight redistribution maintains sum-to-1.0
**PASS.** `_redistribute_weights()` proportionally distributes remaining weight. `validate_proposal()` checks the 0.01 floor. Tests `test_apply_pending_single_proposal` and `test_revert_via_apply_single_change` both assert sum-to-1.0 with pytest.approx.

### 5. YAML parse failure raises exception
**PASS.** Two tests cover this: `test_yaml_parse_failure_raises` (malformed YAML) and `test_yaml_missing_file_raises` (nonexistent file). Both assert RuntimeError with descriptive messages.

### 6. config/learning_loop.yaml has all 13 fields matching LearningLoopConfig
**PASS.** YAML has exactly 13 keys. Test `test_config_validation_learning_loop_yaml` asserts bidirectional equality between YAML keys and `LearningLoopConfig.model_fields.keys()`.

## Findings

### F-1: LearningStore created in S4 despite being S3a's deliverable (MEDIUM)

The implementation created a full `LearningStore` in `argus/intelligence/learning/learning_store.py` as a dependency for `ConfigProposalManager`. The close-out report acknowledges this as a judgment call, noting S4 is parallelizable with S3a. This is documented and the implementation is correct, but creates a potential merge conflict if S3a runs independently. Since this is acknowledged in the close-out and both sessions share zero file overlap (except this new file), the risk is manageable.

### F-2: Import ordering in quality_engine.py (LOW)

The `import yaml` addition at line 21 is placed between the third-party `MarketRegime` import and the local `QualityEngineConfig` import, breaking the stdlib -> third-party -> local grouping convention. Should be grouped with stdlib/third-party imports above the local imports block. Cosmetic only.

### F-3: Pydantic validation test relies on threshold range assumption (LOW)

`test_pydantic_validation_failure_leaves_yaml_unchanged` sets `thresholds.a_plus` to 200 expecting Pydantic rejection. This works because `QualityThresholdsConfig` validates values are in [0, 100]. However, the test does not document this dependency. If the threshold validator were ever relaxed, this test would silently stop testing what it claims. The risk is low since threshold validation is unlikely to change.

### F-4: assert in _read_yaml for type checking (LOW)

`_read_yaml()` at line 105 uses `assert isinstance(parsed, dict)` for runtime type checking. In production with `python -O` (optimized mode), asserts are stripped. This is a minor concern since ARGUS does not run with `-O`, and the startup validation in `_validate_yaml_parseable()` would catch this case first. Still, a proper `if not isinstance: raise` would be safer.

### F-5: Multiple sequential proposals may use stale current_value in drift calculation (LOW)

When `apply_pending()` processes multiple proposals, the drift guard uses `proposal.current_value` (set at analysis time) for delta calculation. If a prior proposal in the same batch already changed the dimension, the actual current value differs from `proposal.current_value`. This is a design characteristic rather than a bug -- proposals are generated at analysis time and the drift calculation is conservative (may overcount drift). Noted for awareness.

## Regression Checklist (Session-Relevant Items)

| Check | Result |
|-------|--------|
| learning_loop.yaml keys recognized by LearningLoopConfig | PASS |
| config/learning_loop.yaml loads without error | PASS |
| ConfigProposalManager writes ONLY to quality_engine.yaml | PASS |
| Pydantic validation rejects invalid config values | PASS |
| LearningStore uses WAL mode | PASS (line 104) |
| No files modified outside scope | PASS (only __init__.py and quality_engine.py modified) |
| Test count >= 83 | PASS (83 = 65 existing + 18 new) |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| ConfigProposalManager writes invalid YAML | No |
| Config reload causes scoring regression | No (no reload exists) |
| Auto post-session trigger blocks shutdown | N/A (not in S4 scope) |
| Mathematically impossible results | No |
| Config change history gaps | No |

## Test Results

- Learning module: 83 passed (65 existing + 18 new) in 0.67s
- No test failures, no hangs

## Verdict

**CONCERNS** -- The implementation is functionally correct and meets all spec requirements. The LearningStore dual-creation (F-1) is the primary concern -- while documented and defensible, it creates a non-trivial merge risk if S3a runs independently. The remaining findings are low-severity style and robustness items that do not affect correctness.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "findings_count": 5,
  "critical_findings": 0,
  "medium_findings": 1,
  "low_findings": 4,
  "tests_pass": true,
  "test_count": 83,
  "escalation_triggered": false,
  "summary": "Implementation meets all spec requirements. ConfigProposalManager correctly implements startup-only application, atomic writes, cumulative drift guard, and weight redistribution. LearningStore dual-creation with S3a is the primary concern (documented judgment call). Minor style and robustness items noted."
}
```
