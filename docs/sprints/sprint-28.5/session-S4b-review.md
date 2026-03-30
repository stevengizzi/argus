```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 28.5 S4b] — Order Manager: Trailing Stop + Escalation Logic
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-30
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All spec requirements implemented. No out-of-scope modifications. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. Self-assessment CLEAN is justified. |
| Test Health | PASS | 189 OM tests pass (18 new), 3934 full suite pass, 0 failures. |
| Regression Checklist | PASS | Non-trail positions unchanged, T1/T2 flow preserved, EOD flatten works, all existing tests pass. |
| Architectural Compliance | PASS | Changes respect event bus patterns, broker abstraction, risk manager isolation. |
| Escalation Criteria | NONE_TRIGGERED | No position leaks, no silent behavioral changes, no deadlocks, no regressions. |

### Findings

**F1 (MEDIUM): Test 17 (escalation AMD-8 guard) does not exercise production code path.**
File: `tests/execution/test_order_manager_exit_management.py`, lines 719-762.
Test 17 (`test_escalation_skips_when_flatten_pending`) manually reimplements the escalation logic with a Python `if` statement rather than invoking the actual poll loop or `_escalation_update_stop`. It proves the `compute_escalation_stop` math and the concept of the guard, but does not verify the production code at `order_manager.py:1348` actually executes the `continue`. A bug in the poll loop's `_flatten_pending` check (e.g., wrong variable name, wrong indentation) would not be caught. A proper test should either call `_escalation_update_stop` with a pre-set `_flatten_pending` or trigger the poll loop. This is mitigated by the fact that Test 8 (AMD-8 for `_trail_flatten`) does test production code directly.

**F2 (MEDIUM): Test 9 (escalation triggers at correct elapsed_pct) does not exercise production code.**
File: `tests/execution/test_order_manager_exit_management.py`, lines 447-482.
Similar to F1: Test 9 calls `compute_escalation_stop` directly rather than driving the poll loop. It validates the math function but not the integration in `order_manager.py:1323-1353`. The escalation integration in the poll loop is only implicitly covered by the fact that all existing tests pass. A dedicated integration test that advances the clock and verifies the broker stop was updated via the poll loop would be stronger.

**F3 (LOW): Exit reason misattribution when escalation_failure flatten occurs on a trail-active position.**
File: `argus/execution/order_manager.py`, lines 1252-1257.
In `_handle_flatten_fill`, the exit reason is set to `TRAILING_STOP` if `position.trail_active` is True. If a position has both trail and escalation enabled, and the escalation stop update fails (AMD-3), `_flatten_position` is called with `reason="escalation_failure"`. The flatten fill handler ignores this reason string and checks `trail_active` instead, logging `TRAILING_STOP` rather than a more accurate reason. This is informational only -- the position is correctly closed regardless. Documented as a judgment call in the close-out.

**F4 (LOW): AMD-8 guard for escalation is in the caller (poll loop) not in `_escalation_update_stop` itself.**
File: `argus/execution/order_manager.py`, line 1348 vs lines 1885-1947.
The spec states AMD-8 check should be "the absolute FIRST thing in _trail_flatten and escalation update paths." For `_trail_flatten`, the check is correctly the first line (line 1804). For escalation, the `_flatten_pending` check is in the poll loop at line 1348 rather than inside `_escalation_update_stop`. Functionally equivalent since the poll loop is the sole caller. But if `_escalation_update_stop` were called from another path in the future, the guard would be missing. Low risk given current architecture.

**F5 (INFO): V1 trailing stop config fields are now dead code.**
File: `argus/execution/order_manager.py`.
The old `enable_trailing_stop` and `trailing_stop_atr_multiplier` fields on `OrderManagerConfig` are no longer referenced in `on_tick`. Noted in close-out deferred observations. Should be cleaned up in a future session.

### Recommendation
CONCERNS: The implementation is correct and all safety-critical AMD requirements are properly implemented in production code. The two MEDIUM findings (F1, F2) are test coverage gaps -- the escalation integration in the poll loop is tested only at the math-function level, not through the actual production code path. This does not block progress but should be noted for the developer. Consider adding an integration-level escalation test (driving the poll loop or calling `_escalation_update_stop` with `_flatten_pending` pre-set) in a future session.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28.5",
  "session": "S4b",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "Test 17 (escalation AMD-8 guard) reimplements logic manually instead of testing production poll loop code path",
      "severity": "MEDIUM",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/execution/test_order_manager_exit_management.py",
      "recommendation": "Add integration test that verifies _flatten_pending guard in the actual poll loop or _escalation_update_stop method"
    },
    {
      "description": "Test 9 (escalation triggers at correct elapsed_pct) calls compute_escalation_stop directly, not the poll loop integration",
      "severity": "MEDIUM",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/execution/test_order_manager_exit_management.py",
      "recommendation": "Add integration test driving the poll loop to verify escalation stop update reaches broker"
    },
    {
      "description": "Exit reason misattribution when escalation_failure flatten occurs on a trail-active position — logs TRAILING_STOP instead of escalation-related reason",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Informational only. Consider adding reason field to PendingManagedOrder in future cleanup."
    },
    {
      "description": "AMD-8 guard for escalation is in poll loop caller, not inside _escalation_update_stop itself",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Consider adding defensive _flatten_pending check as first line of _escalation_update_stop for defense-in-depth"
    },
    {
      "description": "V1 trailing stop config fields (enable_trailing_stop, trailing_stop_atr_multiplier) on OrderManagerConfig are dead code",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Clean up in a future session"
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 11 Definition of Done items completed. All AMD requirements (2,3,4,6,8) implemented correctly in production code. 18 new tests (spec minimum: 15).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/execution/order_manager.py",
    "tests/execution/test_order_manager_exit_management.py",
    "argus/core/exit_math.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 3934,
    "new_tests_adequate": true,
    "test_quality_notes": "18 new tests cover all spec requirements. Two escalation tests (T9, T17) test math functions directly rather than production integration paths — adequate for correctness but not for integration confidence."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Non-trail positions unchanged", "passed": true, "notes": "Test 14 + all 153 existing OM tests pass"},
      {"check": "T1/T2 bracket flow preserved", "passed": true, "notes": "Existing bracket tests pass"},
      {"check": "EOD flatten still works", "passed": true, "notes": "Existing EOD tests pass"},
      {"check": "_flatten_pending covers trail path (AMD-8)", "passed": true, "notes": "Test 8 confirms complete no-op"},
      {"check": "DEC-374 dedup still works", "passed": true, "notes": "Existing dedup tests pass"},
      {"check": "_stop_retry_count unaffected by escalation (AMD-6)", "passed": true, "notes": "Test 12 confirms; grep confirms no _stop_retry_count reference in _escalation_update_stop"},
      {"check": "AMD-2 sell-before-cancel order", "passed": true, "notes": "Test 6 + code inspection confirm place_order before cancel_order"},
      {"check": "AMD-3 escalation failure recovery", "passed": true, "notes": "Test 11 confirms _flatten_position called on exception"},
      {"check": "AMD-4 shares_remaining guard", "passed": true, "notes": "Test 7 confirms no-op on 0 shares"},
      {"check": "Risk Manager not touched", "passed": true, "notes": "No diff on risk_manager.py"},
      {"check": "fill_model.py not touched", "passed": true, "notes": "No diff on fill_model.py"},
      {"check": "Full pytest suite passes", "passed": true, "notes": "3934 passed, 0 failures"},
      {"check": "Trail ratchet-up only", "passed": true, "notes": "Test 4 confirms; code uses max(current, new)"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Add integration-level test for escalation poll loop path (drives actual poll loop or calls _escalation_update_stop with _flatten_pending guard verification)",
    "Consider adding defensive _flatten_pending check inside _escalation_update_stop for defense-in-depth"
  ]
}
```
