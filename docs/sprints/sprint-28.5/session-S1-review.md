```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 28.5] S1 — Exit Math Pure Functions
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-29
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All spec requirements implemented. Only new files created. No existing files modified. |
| Close-Out Accuracy | PASS | Change manifest matches actual diff. Self-assessment of CLEAN is justified. Judgment calls documented. |
| Test Health | PASS | 25/25 new tests pass. Full suite 3,870 pass (3,845 baseline + 25 new). |
| Regression Checklist | PASS | No existing files modified; no regression possible from this session. |
| Architectural Compliance | PASS | Pure-function module with zero argus imports. Matches fill_model.py pattern. |
| Escalation Criteria | NONE_TRIGGERED | No escalation criteria apply to this foundation session. |

### Findings

**F1 (MEDIUM): `compute_escalation_stop` does not guard against `time_stop_seconds == 0.0`**
File: `argus/core/exit_math.py`, line 119
The function guards against `time_stop_seconds is None` but not against `time_stop_seconds == 0.0`. Line 119 performs `elapsed_pct = elapsed_seconds / time_stop_seconds`, which would raise `ZeroDivisionError` if `time_stop_seconds` is `0.0`. While a zero time stop is nonsensical and would likely be caught by upstream validation (Pydantic config in S2), a pure function that advertises `float | None` should be robust to all valid float inputs. Recommended fix: add `if time_stop_seconds is None or time_stop_seconds <= 0:` on lines 113-114.

**F2 (LOW): No test for `time_stop_seconds == 0.0` edge case**
File: `tests/unit/core/test_exit_math.py`
No test exercises the zero-time-stop path. If F1 is addressed, a corresponding test should be added.

**F3 (INFO): `compute_escalation_stop` phase loop `break` assumes sorted input**
File: `argus/core/exit_math.py`, line 127
The `break` statement on line 127 is an optimization that only works correctly when phases are sorted ascending by threshold. The docstring states this assumption (line 103: "sorted ascending by elapsed_pct_threshold"), which is appropriate. However, an unsorted list would silently produce incorrect results rather than raising an error. This is acceptable for a pure function with a documented contract, but worth noting for S2 when the Pydantic model is built -- the model should enforce sort order.

### Recommendation
CONCERNS: One medium-severity finding (F1) regarding `ZeroDivisionError` on `time_stop_seconds == 0.0`. This does not block proceeding to S2, as S2 will introduce Pydantic config validation that can enforce `time_stop_seconds > 0`. However, the pure function should ideally handle this defensively. Recommend adding the guard in S2 alongside the Pydantic models, or as a quick fix at the start of S2.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28.5",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "compute_escalation_stop does not guard against time_stop_seconds == 0.0, which causes ZeroDivisionError on line 119",
      "severity": "MEDIUM",
      "category": "ERROR_HANDLING",
      "file": "argus/core/exit_math.py",
      "recommendation": "Change line 113-114 guard to: if time_stop_seconds is None or time_stop_seconds <= 0: return None"
    },
    {
      "description": "No test for time_stop_seconds == 0.0 edge case",
      "severity": "LOW",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/unit/core/test_exit_math.py",
      "recommendation": "Add test_zero_time_stop_returns_none test case"
    },
    {
      "description": "Phase loop break assumes sorted input; unsorted list silently produces wrong result",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/core/exit_math.py",
      "recommendation": "S2 Pydantic model should enforce ascending sort order on phases"
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All spec requirements met. Functions are pure, AMD-5 formulas use high_watermark, AMD-12 guards present, StopToLevel has all 4 values, min_trail_distance floor applied correctly, compute_effective_stop returns max of non-None values.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/exit_math.py",
    "tests/unit/core/test_exit_math.py",
    "tests/unit/__init__.py",
    "tests/unit/core/__init__.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 3870,
    "new_tests_adequate": true,
    "test_quality_notes": "25 well-structured tests covering all 3 functions, enum validation, edge cases (disabled, None ATR, negative ATR, zero ATR, empty phases, no phase reached, latest-phase-wins). Missing: time_stop_seconds=0.0 edge case."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "No existing files modified", "passed": true, "notes": "git diff HEAD~1 --name-only shows only new files + closeout"},
      {"check": "exit_math.py is pure (no I/O)", "passed": true, "notes": "grep for open(/print(/logging/import os clean"},
      {"check": "StopToLevel has all 4 AMD-5 values", "passed": true, "notes": "BREAKEVEN, QUARTER_PROFIT, HALF_PROFIT, THREE_QUARTER_PROFIT"},
      {"check": "AMD-5 formulas use high_watermark", "passed": true, "notes": "Line 134: entry_price + fraction * (high_watermark - entry_price)"},
      {"check": "AMD-12 negative/zero ATR guard", "passed": true, "notes": "Line 68: atr_value is None or atr_value <= 0 returns None"},
      {"check": "compute_effective_stop returns max of non-None", "passed": true, "notes": "Line 160: max(candidates) where candidates always includes original_stop"},
      {"check": "min_trail_distance floor applied after computation", "passed": true, "notes": "Line 79: max(trail_distance, min_trail_distance) after type-specific computation"},
      {"check": "Full pytest suite passes", "passed": true, "notes": "3,870 passed in 47.36s"},
      {"check": "Risk Manager not touched", "passed": true, "notes": "No existing files modified"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Add time_stop_seconds <= 0 guard to compute_escalation_stop (can be done at start of S2)",
    "S2 Pydantic model should validate phases are sorted ascending and time_stop_seconds > 0"
  ]
}
```
