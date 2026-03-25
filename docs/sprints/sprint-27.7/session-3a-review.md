---BEGIN-REVIEW---

# Sprint 27.7, Session 3a — Tier 2 Review

**Reviewer:** Tier 2 Automated Review (Opus 4.6)
**Date:** 2026-03-25
**Commit:** 779f58e feat(intelligence): Sprint 27.7 S3a — SignalRejectedEvent + rejection publishing

## Verdict: CLEAR

## Session-Specific Checks

| # | Focus Item | Result | Notes |
|---|-----------|--------|-------|
| 1 | `rejection_stage` is a string literal, not an import from intelligence | PASS | `rejection_stage: str = ""` in events.py. No `from argus.intelligence` import in events.py. Values are inline string literals `"QUALITY_FILTER"`, `"POSITION_SIZER"`, `"RISK_MANAGER"` at publish sites. |
| 2 | `_counterfactual_enabled` defaults to False, checked before every publish | PASS | Initialized as `self._counterfactual_enabled: bool = False` at main.py:160. All 3 publish sites guard with `getattr(self, '_counterfactual_enabled', False)`. |
| 3 | Signal in each SignalRejectedEvent has entry/stop/target populated | PASS | Quality filter and sizer rejections pass the original `signal` (strategies populate entry/stop/target). RM rejection passes the enriched `signal` (still has prices). Test 7 explicitly verifies entry=150.0, stop=148.0, target[0]=153.0. |
| 4 | No new `await` on critical path when disabled | PASS | `getattr()` is synchronous. When False, the `if` block is skipped entirely -- no `await` reached. `_capture_regime_snapshot()` is also synchronous (`def`, not `async def`). |
| 5 | OrderApprovedEvent/OrderRejectedEvent publish not moved or reordered | PASS | Lines 1353-1354 (`result = await self._risk_manager.evaluate_signal(signal)` / `await self._event_bus.publish(result)`) are unchanged. SignalRejectedEvent publish is at line 1356, strictly after. Quality/sizer rejections add publishing after existing `record_quality_history` and before the existing `return`. |
| 6 | RM rejection: SignalRejectedEvent published after `publish(result)` | PASS | Line 1354: `await self._event_bus.publish(result)` (OrderRejectedEvent). Line 1356-1365: SignalRejectedEvent publish. Correct ordering confirmed. Test `test_risk_manager_rejection_publishes_event` validates both events are published with OrderRejectedEvent first. |

## Sprint-Level Regression Checks

| Check | Result | Notes |
|-------|--------|-------|
| All existing pytest tests pass | PASS | 3,455 passed + 5 xdist-flaky (pre-existing, pass in isolation). No new failures. |
| Do-not-modify files untouched | PASS | `git diff HEAD~1 HEAD --name-only` shows only events.py, main.py, closeout, and test file. risk_manager.py, startup.py, system.yaml, system_live.yaml, strategies/, ui/ all untouched. |
| `_process_signal()` identical code path when disabled | PASS | `getattr` returns False, `if` block skipped. No other code in `_process_signal` was altered. Existing test suite passes unchanged. |
| `_process_signal()` identical order results when enabled | PASS | SignalRejectedEvent is published after existing event flow at each point, not instead of. The function's return points and OrderApproved/OrderRejected publish are unmodified. |
| Event bus FIFO ordering preserved | PASS | SignalRejectedEvent uses standard `await self._event_bus.publish()`. No priority mechanism or reordering introduced. |

## Code Quality

The implementation is clean, focused, and well-structured.

**Positive observations:**
- `_capture_regime_snapshot()` extraction as a DRY helper is a good judgment call -- avoids 12 lines of duplication across 3 sites.
- Using `dict[str, Any]` instead of bare `dict` aligns with project code style rules (parameterized generics).
- The `getattr(self, '_counterfactual_enabled', False)` pattern is a pragmatic solution to the `__new__()` bypass problem in test helpers. The deviation from spec is well-documented in the close-out report.
- The SignalRejectedEvent dataclass follows the established frozen dataclass pattern used by other events in the file.

**No concerns identified.**

## Test Coverage

12 new tests covering all 7 spec test targets:

| Test Target | Tests | Coverage |
|-------------|-------|----------|
| Event creation (frozen dataclass) | 3 | All fields, frozen behavior, defaults |
| Quality filter rejection | 1 | Stage, score, grade, reason verified |
| Position sizer rejection | 1 | Stage, score, grade, "0 shares" in reason |
| Risk Manager rejection | 1 | Stage, reason, OrderRejectedEvent ordering |
| Disabled flag suppression | 3 | One per rejection point |
| Regime vector capture | 2 | Present + absent cases |
| Signal price data | 1 | entry, stop, target verified non-zero |

Test quality is strong -- the tests use the real EventBus (not mocks), verify actual event delivery via subscribers, and check field values rather than just event counts.

## Findings

No issues found.

The `getattr()` pattern for `_counterfactual_enabled` is a minor deviation from the spec but is well-justified and correctly documented with a MINOR_DEVIATIONS self-assessment. The underlying problem (test helpers using `__new__()`) is a real constraint, and the chosen solution has zero behavioral difference from direct attribute access in production code.

## Recommendation

Proceed to Session 3b. The implementation is correct, complete, and safe. All spec requirements are met. No regressions detected. The session is ready for the next step (tracker subscription and startup wiring).

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.7",
  "session": "S3a",
  "verdict": "CLEAR",
  "findings": [],
  "escalation_triggers": [],
  "tests": {
    "total": 3455,
    "passed": 3455,
    "failed": 0,
    "flaky_preexisting": 5,
    "new": 12
  },
  "files_reviewed": [
    "argus/core/events.py",
    "argus/main.py",
    "tests/test_signal_rejected.py"
  ],
  "do_not_modify_violations": [],
  "recommendation": "Proceed to Session 3b"
}
```
