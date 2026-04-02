---BEGIN-REVIEW---

# Sprint 32.9 Session 2 — Tier 2 Review Report

**Reviewer:** Automated Tier 2  
**Date:** 2026-04-02  
**Commit:** Uncommitted working tree changes (S2 changes not yet committed)  
**Close-out self-assessment:** CLEAN  

---

## Summary

Session 2 implements a margin circuit breaker in OrderManager (Sprint 32.9 S2),
fixes the intelligence polling loop crash (DEF-141), and fixes the reconciliation
qty-to-shares bug in main.py (DEF-142). The implementation is well-scoped with
12 new tests covering the margin circuit breaker, polling loop resilience, and
reconciliation fix. The full test suite passes at 4,579 (matching the expected
count). No unauthorized files were modified.

---

## Review Checklist

| # | Focus Item | Verdict | Notes |
|---|-----------|---------|-------|
| 1 | Circuit breaker only blocks entries | PASS | Gate is in `on_approved()` at line 467, before `place_bracket_order`. Flatten uses `_flatten_position` -> `place_order` (not `on_approved`). Stop resubmission, bracket amendments, and EOD flatten all bypass `on_approved`. |
| 2 | Rejection callback identifies margin Error 201 | PASS | Line 648: checks `pending.order_type == "entry"`, then `reason.lower()` for "available funds" or "insufficient". |
| 3 | SignalRejectedEvent rejection_stage value | FAIL | See F2 below. Uses `"RISK_MANAGER"` (uppercase) but `RejectionStage.RISK_MANAGER.value` is `"risk_manager"` (lowercase). |
| 4 | Auto-reset queries broker positions | PASS | Line 1413: `await self._broker.get_positions()`, compares `len()` against threshold. |
| 5 | startup.py symbols fix | PASS | `symbols: list[str] = []` at line 302, before the `if firehose:` branch. The `asyncio.TimeoutError` handler at line 331 can now safely reference `symbols` regardless of branch. Empty list is safe -- `len(symbols)` returns 0. |
| 6 | except Exception logs exc_info=True | PASS | Line 337: `logger.error("Poll cycle failed: %s", e, exc_info=True)` |
| 7 | No changes to EOD flatten beyond S1 | PASS | S2 diff touches only margin circuit breaker additions, not the `eod_flatten()` method body. |
| 8 | main.py reconciliation uses pos.shares | PASS | Line 1400: `getattr(pos, "shares", 0)`. Grep confirms no `getattr(pos, "qty"` remaining in `argus/`. One `getattr(order, "qty"` at order_manager.py:1971 is correct (Order object). |
| 9 | Full test suite 4,579 passing | PASS | 4,579 passed, 0 failures, 62 warnings (pre-existing aiosqlite cleanup noise). |

---

## Findings

### F1 (blocking): None

### F2 (non-blocking): Incorrect rejection_stage case for counterfactual tracking

**File:** `argus/execution/order_manager.py`, line 476  
**Issue:** The margin circuit breaker publishes `SignalRejectedEvent` with
`rejection_stage="RISK_MANAGER"` (uppercase). However, the counterfactual
tracker at `argus/main.py:1789` converts this via
`RejectionStage(event.rejection_stage)`, and `RejectionStage.RISK_MANAGER` has
value `"risk_manager"` (lowercase, per StrEnum convention). The mismatch causes
a `ValueError` which is caught by the broad `except Exception` at line 1797 and
logged as a warning. The system does not crash, but counterfactual tracking
silently fails for margin-circuit-rejected signals.

All other rejection sites in `main.py` use lowercase values (`"risk_manager"`,
`"quality_filter"`, `"position_sizer"`, `"shadow"`, `"broker_overflow"`).

**Fix:** Change line 476 from `rejection_stage="RISK_MANAGER"` to
`rejection_stage="risk_manager"`.

**Severity:** MEDIUM -- counterfactual data loss for margin rejections, but no
runtime crash.

### F3 (informational): Typo in test assertion class name

**File:** `tests/execution/test_order_manager_sprint329.py`, line 960  
**Issue:** `raise AssertionError(...)` -- missing second "s", should be
`AssertionError`. This is a `NameError` if the branch executes. Currently latent
because the test passes (the fix is in place), but would produce a confusing
`NameError` instead of a proper assertion message if someone reintroduced
`pos.qty` in main.py.

### F3 (informational): Changes not committed

The close-out report states "CLEAN" and references 4,579 passing tests, but the
S2 changes exist only in the working tree (unstaged). `git status` shows
modified files for order_manager.py, config.py, startup.py, main.py,
order_manager.yaml, and the test file, plus untracked session-2-closeout.md.
This is likely a procedural gap (the implementation session completed but the
commit was not created), not a code quality issue.

---

## Scope Verification

All scope items from the close-out report verified independently:

- Margin rejection counter increments correctly on entry-order cancellations
- Circuit opens at threshold with WARNING log
- Entry gate in on_approved before place_bracket_order
- SignalRejectedEvent published on gate (with case issue noted in F2)
- Flatten, bracket leg, stop resubmission paths are NOT gated
- Auto-reset queries broker.get_positions() and resets below threshold
- Daily reset clears both fields in reset_daily_state()
- Config fields present in OrderManagerConfig and order_manager.yaml
- DEF-141 fix: symbols initialized, exc_info=True added
- DEF-142 fix: main.py reads pos.shares

---

## Verdict

**CONCERNS**

The implementation is functionally correct and well-tested. The margin circuit
breaker correctly gates only new entries, leaves all exit/flatten paths
unblocked, and provides auto-reset via broker position count. The DEF-141 and
DEF-142 fixes are minimal and correct. However, the `rejection_stage` case
mismatch (F2) will silently break counterfactual tracking for margin-rejected
signals, which should be fixed in the next available session.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "findings": [
    {
      "id": "F2",
      "severity": "non-blocking",
      "category": "correctness",
      "summary": "rejection_stage='RISK_MANAGER' (uppercase) mismatches RejectionStage enum value 'risk_manager' (lowercase), causing silent counterfactual tracking failure for margin-rejected signals",
      "file": "argus/execution/order_manager.py",
      "line": 476,
      "fix": "Change rejection_stage='RISK_MANAGER' to rejection_stage='risk_manager'"
    },
    {
      "id": "F3a",
      "severity": "informational",
      "category": "test-quality",
      "summary": "Typo 'AssertionError' (missing 's') at line 960 of test file — latent NameError if branch executes",
      "file": "tests/execution/test_order_manager_sprint329.py",
      "line": 960,
      "fix": "Change AssertionError to AssertionError"
    },
    {
      "id": "F3b",
      "severity": "informational",
      "category": "process",
      "summary": "S2 changes exist only in working tree — not yet committed",
      "file": null,
      "line": null,
      "fix": "Commit the S2 changes"
    }
  ],
  "tests_passed": 4579,
  "tests_failed": 0,
  "escalation_triggers": []
}
```
