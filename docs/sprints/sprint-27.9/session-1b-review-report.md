```markdown
---BEGIN-REVIEW---

**Reviewing:** Sprint 27.9 S1b -- yfinance Integration + Derived Metrics
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-26
**Verdict:** CONCERNS (post-fix: CLEAR)

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 9 spec requirements implemented. Two justified scope additions (_flatten_columns, _fetch_range). |
| Close-Out Accuracy | PASS | Change manifest matches actual diff. Judgment calls documented. MINOR_DEVIATIONS self-assessment is accurate. |
| Test Health | PASS | 18 tests passing (11 S1a + 7 S1b). All yfinance calls mocked. |
| Regression Checklist | PASS | R13 (YAML/Pydantic alignment) verified via existing test. S1a tests unchanged and passing. |
| Architectural Compliance | PASS | Minor concerns noted below but nothing blocking. |
| Escalation Criteria | NONE_TRIGGERED | No escalation criteria met. |

### Findings

**[MEDIUM] VRP test does not exercise compute_derived_metrics() end-to-end for VRP**
File: `tests/data/test_vix_derived_metrics.py`, lines 164-184 (TestVarianceRiskPremium)
The test calls `compute_derived_metrics()` but then overrides `realized_vol_20d` to 0.15 and recomputes VRP inline, verifying only the arithmetic formula (20^2 - 15^2 = 175). It does not verify that `compute_derived_metrics()` itself produces a correct VRP from its own computed realized vol. A synthetic SPX series with known constant returns would yield near-zero RV, making end-to-end VRP verification trivial (VRP ~ VIX^2), but the test does not assert this either. The formula is correct upon code inspection, so this is a coverage gap rather than a correctness issue.

**[LOW] `_flatten_columns()` mutates its input DataFrame in-place**
File: `argus/data/vix_data_service.py`, line 398
`df.columns = df.columns.get_level_values(0)` modifies the input DataFrame's columns. Per project coding standards ("No mutation -- Functions should not alter/mutate their inputs"), this should return a copy. In practice, the callers only pass freshly-downloaded DataFrames that are not referenced elsewhere, so the impact is negligible.

**[LOW] No shutdown/cancellation mechanism for daily update task**
File: `argus/data/vix_data_service.py`, lines 567-631
`_start_daily_update_task()` creates an asyncio task with `while True` but there is no `stop()` or `shutdown()` method to cancel it. The project's universal coding standards prohibit `while(true)` loops. For a background service task this is a common pattern, and the task is cancellable via `self._update_task.cancel()` externally, but no public method exposes this. Future sessions will likely add shutdown wiring.

**[INFO] scipy dependency not documented**
`scipy.stats.percentileofscore` is imported but scipy is not mentioned in deferred items or requirements tracking. The close-out notes this for scipy but does not create a DEF item. This is informational -- scipy is already a transitive dependency via other packages.

### Post-Review Fixes Applied
1. **[MEDIUM] VRP test** — Added end-to-end VRP assertion: verifies `compute_derived_metrics()` produces non-NaN VRP with correct value for known inputs (VIX=20, near-zero RV → VRP ≈ 400).
2. **[LOW] `_flatten_columns()` mutation** — Added `df.copy()` before modifying columns to avoid input mutation.
3. **[LOW] No shutdown method** — Acknowledged; will be wired in future session when service lifecycle is integrated.
4. **[INFO] scipy** — Acknowledged; scipy is a transitive dependency via existing packages.

### Recommendation
POST-FIX: CLEAR. Both actionable concerns (VRP test gap, input mutation) have been resolved. Remaining items (shutdown method, scipy tracking) are low-priority future work.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.9",
  "session": "S1b",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "VRP test overrides realized_vol_20d manually rather than verifying compute_derived_metrics() end-to-end VRP output",
      "severity": "MEDIUM",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/data/test_vix_derived_metrics.py",
      "recommendation": "Add assertion that compute_derived_metrics() produces non-NaN VRP with expected sign for known inputs"
    },
    {
      "description": "_flatten_columns() mutates input DataFrame columns in-place via direct assignment",
      "severity": "LOW",
      "category": "ARCHITECTURE",
      "file": "argus/data/vix_data_service.py",
      "recommendation": "Return df.copy() before modifying columns, or use df.columns.get_level_values(0) on a copy"
    },
    {
      "description": "No shutdown/cancellation method for the daily update asyncio task; uses while True loop",
      "severity": "LOW",
      "category": "ARCHITECTURE",
      "file": "argus/data/vix_data_service.py",
      "recommendation": "Add a stop() or shutdown() method that cancels self._update_task"
    },
    {
      "description": "scipy dependency used (percentileofscore) but not tracked in requirements or deferred items",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/data/vix_data_service.py",
      "recommendation": "Verify scipy is in requirements.txt or note as assumed transitive dependency"
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "fetch_historical years parameter made optional (spec said required). _flatten_columns and _fetch_range added as implementation helpers (justified). All spec requirements met.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/data/vix_data_service.py",
    "tests/data/test_vix_derived_metrics.py",
    "argus/data/vix_config.py",
    "config/vix_regime.yaml",
    "tests/data/test_vix_data_service.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 18,
    "new_tests_adequate": true,
    "test_quality_notes": "7 new tests cover all 5 derived metrics, sigma-zero guard, and incremental update. VRP test verifies formula math but not end-to-end computation path."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "R13: YAML keys match Pydantic model", "passed": true, "notes": "test_config_yaml_matches_pydantic_model passes"},
      {"check": "S1a tests still pass", "passed": true, "notes": "11/11 S1a tests passing"},
      {"check": "No import errors", "passed": true, "notes": "VIXDataService imports cleanly"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Add end-to-end VRP assertion in test_vrp_known_values or a new test",
    "Add stop()/shutdown() method for daily update task in a future session"
  ]
}
```
