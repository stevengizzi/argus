---BEGIN-REVIEW---

# Tier 2 Review: Impromptu DEF-158 Duplicate SELL Bug Fix — Session 1

**Reviewer:** Automated Tier 2
**Date:** 2026-04-20
**Commit:** c09805d
**Diff range:** HEAD~1

## 1. Spec Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| R1: Diagnose DEF-158 root cause | PASS | 3 root causes identified with file:line references and timeline evidence (ARX 120s gap). Narrative is coherent and evidence-based, not speculative. |
| R2: Fix DEF-158 | PASS | 4 method changes in `order_manager.py` addressing all 3 root causes plus a bonus guard in `_handle_flatten_fill`. |
| R2: 3+ regression tests | PASS | 5 tests in `test_order_manager_def158.py`. Each maps to a specific root cause. |
| R2: DEF-158 RESOLVED in CLAUDE.md | PASS | Full root cause explanation with all 3 causes documented. |
| R3: DEF-159 stretch | PASS | Correctly deferred. Logged in CLAUDE.md with root cause and fix options. |
| R4: Log DEF-160 | PASS | Logged in CLAUDE.md, not fixed. Cosmetic-only. Correctly noted as potentially subsumed by DEF-158. |
| Sprint-history entry | PASS | AU entry with root cause summary and fix description. |
| Dev log | PASS | `dev-logs/2026-04-20_duplicate-sell.md` with incident description, 3 root causes, and file list. |
| Close-out report | PASS | Complete structured report with all required sections. |

## 2. Protected File Verification

No protected files were modified. `git diff HEAD~1 --name-only` shows exactly 6 files changed:
- `CLAUDE.md` (doc update)
- `argus/execution/order_manager.py` (the fix)
- `dev-logs/2026-04-20_duplicate-sell.md` (new)
- `docs/sprint-history.md` (doc update)
- `docs/sprints/impromptu-2026-04-20-duplicate-sell/session-1-closeout.md` (new)
- `tests/execution/test_order_manager_def158.py` (new)

None of the protected files (server.py, main.py, start_live.sh, telemetry_store.py, strategies/*, experiments/*, etc.) appear in the diff.

## 3. Root Cause Analysis Quality

The root cause narrative is coherent and well-supported:

1. **Flatten-pending timeout resubmission** (primary): The 120s timeout in `_check_flatten_pending_timeouts` was resubmitting when IBKR paper trading delayed fill callbacks beyond 120s. Evidence: ARX SELL at 09:55:29, second SELL at 09:57:30 (exactly 120s = timeout interval). This is concrete evidence, not hypothesis.

2. **Startup cleanup missing order cancellation**: `_flatten_unknown_position` placed a SELL without cancelling residual bracket orders. Straightforward code analysis -- the method previously had no cancel logic.

3. **Stop fill / flatten race**: `_handle_stop_fill` closed the position but left concurrent flatten orders live. Clear race condition in the code.

All three are independent causes that compound. The narrative is consistent and the evidence supports the diagnosis.

## 4. Fix Quality Assessment

**Root Cause 1 fix** (`_check_flatten_pending_timeouts`): Changed from querying broker only when `error_404_symbols` was flagged to always querying broker position before resubmission. If broker reports 0 shares, clears pending without resubmitting. This addresses the root cause directly -- no symptom suppression. The `error_404_symbols.discard()` is preserved for backward compatibility with Sprint 29.5 R1 but no longer gates the broker query.

**Root Cause 2 fix** (`_flatten_unknown_position`): Queries `get_open_orders()` and cancels orders matching the target symbol before placing the flatten SELL. Uses per-symbol filtering (not `reqGlobalCancel()`), which is correct -- global cancel would affect unrelated positions. The `getattr(order, "order_id", None) or getattr(order, "orderId", None)` dual-attribute lookup handles both IBKR and Alpaca broker implementations.

**Root Cause 3 fix** (`_handle_stop_fill`): After processing the stop fill, checks `_flatten_pending` for the symbol and cancels the pending flatten order. Cleans up both `_pending_orders` and `_flatten_pending`.

**Bonus fix** (`_handle_flatten_fill`): After a flatten fill closes the position, scans `_pending_orders` for other flatten orders on the same symbol and cancels them. This catches timeout-resubmitted duplicate flatten orders. The `_flatten_pending` dict is correctly cleaned up by the downstream `_close_position()` call (line 2641).

All fixes are defensive and independent -- each guard prevents its respective failure mode without relying on the others. No DEC behavior was rolled back; the flatten-pending timeout mechanism still works, it just verifies broker state first.

## 5. Race Condition Assessment

**No new race conditions introduced.** The fixes add pre-checks and post-cleanup to existing async methods. Since Python asyncio is single-threaded, the broker query + conditional resubmit in `_check_flatten_pending_timeouts` is atomic at the coroutine level. The cancel-before-flatten in `_flatten_unknown_position` is similarly safe. The only theoretical window is if IBKR fills arrive between the broker query and the cancel/resubmit, but:
- For Root Cause 1: A fill arriving after broker reports 0 shares is impossible (already flat).
- For Root Cause 2: A cancel failing is caught by try/except; the flatten SELL proceeds regardless.
- For Root Cause 3: The flatten cancel failing means a second SELL may execute, but this is strictly better than the prior state (no cancel attempt at all).

## 6. Test Quality

All 5 tests are well-structured regression tests:

1. `test_flatten_timeout_skips_resubmit_when_broker_position_closed` -- Verifies Root Cause 1 fix: timeout does NOT resubmit when broker position is 0. Properly sets up a timed-out flatten entry and verifies `place_order` is never called.
2. `test_flatten_timeout_does_resubmit_when_broker_position_exists` -- Positive case: timeout DOES resubmit when broker still holds shares. Ensures the fix did not break normal operation.
3. `test_startup_cleanup_cancels_existing_orders_before_flatten` -- Verifies Root Cause 2: cancels ARX orders but not TSLA orders. Properly asserts cancel was called with correct order IDs.
4. `test_stop_fill_cancels_concurrent_flatten_order` -- Verifies Root Cause 3: stop fill cancels the concurrent flatten order.
5. `test_flatten_fill_cancels_other_pending_flatten_orders` -- Verifies bonus fix: flatten fill cancels duplicate resubmitted flatten orders.

Tests use appropriate fixtures (EventBus, mock broker, FixedClock) and test at the right level of abstraction. The positive resubmit test (test 2) is important -- it confirms the fix doesn't break the normal timeout-resubmit path.

## 7. Test Suite Results

- **Full suite:** 4,915 passed, 0 failed (118.27s with xdist)
- **DEF-158 tests:** 5/5 passed (0.03s)
- **Delta:** +5 tests (4,910 -> 4,915), consistent with close-out report

## 8. Findings

No findings. The implementation is clean, well-scoped, and addresses the root causes directly.

## 9. Verdict

**CLEAR**

The fix is well-reasoned, addresses three independent root causes with evidence-based diagnosis, includes 5 regression tests covering all failure modes plus positive confirmation, does not modify protected files, does not roll back any DEC behavior, and introduces no new race conditions. DEF-159 was correctly deferred; DEF-160 was correctly logged without fixing.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "impromptu-2026-04-20-duplicate-sell",
  "session": "S1",
  "verdict": "CLEAR",
  "findings": [],
  "escalation_triggers": [],
  "test_results": {
    "total": 4915,
    "passed": 4915,
    "failed": 0,
    "new_tests": 5,
    "suite_command": "python -m pytest --ignore=tests/test_main.py -n auto -q"
  },
  "protected_files_ok": true,
  "dec_rollbacks": [],
  "notes": "Three independent root causes for duplicate SELL orders identified and fixed with evidence-based diagnosis. All 5 regression tests verify specific failure modes. No protected files modified, no DEC behavior changed, no new race conditions introduced."
}
```
