---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 — Session 2: Order Management Hardening
**Date:** 2026-03-27
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| `argus/execution/order_manager.py` | modified | Stop retry cap, revision-rejected handling, fill dedup |
| `argus/core/config.py` | modified | `stop_retry_max` default 1→3 |
| `tests/execution/test_order_manager_hardening.py` | added | 13 new tests for all 3 features |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- **Stop retry counter reset timing:** Prompt says "reset when stop is successfully acknowledged." Since ARGUS has no separate broker acknowledgment callback, the counter resets only on position close (not on submission success). This prevents the backoff progression from resetting between cancel→resubmit cycles, which is the conservative/safe behavior. If the stop keeps getting cancelled, backoff increases; if the position closes normally, the counter is cleaned up.
- **`_submit_stop_order` internal retry loop unchanged:** The existing `_submit_stop_order` has its own retry loop for submission failures (broker connectivity). The new `_resubmit_stop_with_retry` handles *cancel* events from IBKR (different failure mode). Both coexist — submit retries handle "can't reach broker," cancel retries handle "broker cancelled my stop."
- **`_amended_prices` storage:** Added a dict to store the prices computed during `_amend_bracket_on_slippage` so the revision-rejected handler can use the correct amended prices when resubmitting fresh orders, rather than falling back to possibly-stale position prices.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Stop retry tracking (`_stop_retry_count`) | DONE | `order_manager.py:__init__` + `_resubmit_stop_with_retry` |
| Config field `max_stop_retries` | DONE | Reused existing `stop_retry_max` on `OrderManagerConfig`, default changed 1→3 |
| Retry cap with emergency flatten | DONE | `_resubmit_stop_with_retry`: count > max → `_flatten_position` |
| Exponential backoff (1s, 2s, 4s) | DONE | `asyncio.sleep(2 ** (count - 1))` in `_resubmit_stop_with_retry` |
| Reset counter on acknowledgment | DONE | Counter resets on position close (`_close_position`) |
| Clear counter on position close | DONE | `_close_position` clears `_stop_retry_count[symbol]` |
| Revision-rejected detection | DONE | `on_cancel` checks `"Revision rejected" in event.reason` |
| Fresh order submission (not retry) | DONE | `_handle_revision_rejected` submits via `_submit_stop_order`/`_submit_t1_order`/`_submit_t2_order` |
| Fresh order fail → retry flow | DONE | `_handle_revision_rejected` catches exception, calls `_resubmit_stop_with_retry` |
| Fill dedup (`_last_fill_state`) | DONE | `on_fill` checks `(order_id, cumulative_qty)` before processing |
| Fill dedup state cleared on close | DONE | `_close_position` clears matching entries |
| 12+ new tests | DONE | 13 tests in `test_order_manager_hardening.py` |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Normal bracket placement unchanged | PASS | All existing bracket tests pass (65/65) |
| Normal fill processing unchanged for first fill | PASS | Dedup allows first fill through; existing fill tests pass |
| `_flatten_pending` guard intact | PASS | Test 4 explicitly verifies guard respected |
| Bracket amendment price calculation (DEC-366) unchanged | PASS | `_amend_bracket_on_slippage` logic not modified; only added `_amended_prices` storage |
| Stop order success path unaffected | PASS | `_submit_stop_order` unchanged except removal of premature counter reset |

### Test Results
- Tests run: 304
- Tests passed: 304
- Tests failed: 0
- New tests added: 13
- Command used: `python -m pytest tests/execution/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- The `stop_retry_max` config default changed from 1 to 3. This affects the *internal* retry loop in `_submit_stop_order` (submission failures) as well as the new cancel-retry flow. Existing test at `test_order_manager.py:868` explicitly sets `stop_retry_max=1` so is not affected.
- The fill dedup uses `float` comparison for cumulative quantity. This is safe because IBKR reports integer share counts (no fractional shares for equities).
- `_handle_revision_rejected` handles all three bracket leg types (stop, T1, T2) even though the prompt focused on stop. This is because IBKR may reject amendments on any bracket leg.

### Post-Review Fixes
Reviewer verdict: CONCERNS (no blockers). Fixed the MEDIUM finding:
- **Fill dedup cleanup inefficiency:** Added `_fill_order_ids_by_symbol` reverse index so `_close_position` can reliably clean up fill dedup entries by symbol, regardless of whether `_pending_orders` entries were already popped. Previously the cleanup loop was largely dead code.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S2",
  "verdict": "COMPLETE",
  "tests": {
    "before": 291,
    "after": 304,
    "new": 13,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_order_manager_hardening.py"
  ],
  "files_modified": [
    "argus/execution/order_manager.py",
    "argus/core/config.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [
    {
      "description": "Revision-rejected handling extended to T1 and T2 legs (not just stop)",
      "justification": "IBKR may reject amendments on any bracket leg; handling only stop would leave T1/T2 unprotected"
    },
    {
      "description": "_amended_prices dict stores prices from bracket amendment for revision-rejected resubmission",
      "justification": "Fresh order after revision-rejected needs the amended prices, not the original signal prices"
    }
  ],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "stop_retry_max default change (1→3) affects _submit_stop_order internal retry loop too; may want separate config fields if cancel-retry and submit-retry need different limits"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Stop retry counter does not reset on submit success — only on position close. This is because ARGUS lacks a separate 'order acknowledged' callback from IBKR. The conservative approach ensures backoff progression works correctly across repeated cancel events."
}
```
