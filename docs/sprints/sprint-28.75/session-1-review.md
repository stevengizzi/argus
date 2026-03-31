---BEGIN-REVIEW---

# Sprint 28.75 Session 1 Review: Backend Operational Fixes

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-30
**Diff range:** main..sprint-28.75
**Close-out self-assessment:** MINOR_DEVIATIONS

---

## 1. Scope Compliance

All four requirements (R1-R4) are implemented as specified:

| Requirement | Status | Notes |
|-------------|--------|-------|
| R1: Diagnose trailing stops not firing | DONE | Config timing root cause confirmed. 2 verification tests added. No code bug. |
| R2: Flatten-pending timeout mechanism | DONE | `_check_flatten_pending_timeouts()` added with cancel+resubmit, max retries, configurable via `OrderManagerConfig` |
| R3: Rate-limit "flatten already pending" log | DONE | ThrottledLogger, 60s per-symbol |
| R4: Rate-limit "portfolio snapshot missing" log | DONE | ThrottledLogger, 600s per-symbol |
| Minimum 7 new tests | DONE | 8 new tests |

No scope gaps. No scope additions beyond what was specified.

## 2. Forbidden File Check

| Protected Area | Modified? | Verdict |
|----------------|-----------|---------|
| argus/strategies/ | No | PASS |
| argus/core/events.py | No | PASS |
| argus/data/ | No | PASS |
| argus/analytics/ | No | PASS |
| argus/api/ | No | PASS |
| argus/ui/ | No | PASS |
| argus/core/exit_math.py | No | PASS |

Only `argus/core/config.py`, `argus/execution/order_manager.py`, test files, and the close-out report were modified. All within scope.

## 3. Session-Specific Review Focus

### F1: Trail activation fires after T1 fill

VERIFIED. Code path traced:
- `_handle_t1_fill()` calls trail activation when `exit_config.trailing_stop.enabled` and `activation == "after_t1"`
- Test `test_trail_activation_after_t1` confirms: exit_config populated, trail_active becomes True, trail_stop_price computed from ATR
- Test `test_trail_stop_computed_on_tick` confirms: `on_tick` ratchets trail upward on new high watermark
- Root cause was correctly identified as config timing (operator changed YAML mid-session; ARGUS loads config at startup only). No code bug.

### F2: Flatten-pending timeout race with _flatten_pending guard

VERIFIED. No race condition identified.
- `_check_flatten_pending_timeouts()` iterates `list(self._flatten_pending.items())` (snapshot copy), allowing safe mutation during iteration
- After cancelling stale order, the method checks position existence and `shares_remaining > 0` before resubmitting
- The new order ID replaces the old entry atomically: `self._flatten_pending[symbol] = (result.order_id, _time.monotonic(), retry_count + 1)`
- The timeout check runs in the poll loop (single-threaded async), so there is no concurrent mutation risk

### F3: New order ID tracked after flatten resubmission

VERIFIED. In `_check_flatten_pending_timeouts()`:
- Line 1857: `self._pending_orders.pop(order_id, None)` removes old pending entry
- Line 1866: `self._pending_orders[result.order_id] = new_pending` registers new order
- Line 1867: `self._flatten_pending[symbol] = (result.order_id, ...)` updates guard with new ID
- No orphaned entries possible -- old order is removed from both dicts before new one is added.

### F4: max_flatten_retries prevents infinite loops

VERIFIED. When `retry_count >= max_retries`:
- Entry is removed from `_flatten_pending` via `.pop()`
- An ERROR-level log is emitted noting manual intervention or EOD flatten is needed
- No broker calls are made
- Test `test_flatten_pending_max_retries_stops` validates this path

### F5: Log rate-limiting uses ThrottledLogger

VERIFIED.
- `self._throttled = ThrottledLogger(logger)` initialized in `__init__`
- R3 uses `self._throttled.warn_throttled(f"flatten_pending:{symbol}", ..., interval_seconds=60.0)`
- R4 uses `self._throttled.warn_throttled(f"recon_missing:{sym}", ..., interval_seconds=600.0)`
- Both use per-symbol keys, consistent with ThrottledLogger's existing pattern from Sprint 27.75

### F6: No changes to exit_math.py

VERIFIED. `git diff main..sprint-28.75 -- argus/core/exit_math.py` returns empty.

## 4. Regression Checklist

| Check | Result | Evidence |
|-------|--------|----------|
| Order Manager bracket invariant (DEC-117) | PASS | Bracket order creation code untouched |
| Flatten-pending guard (DEC-363) | PASS | Guard logic preserved; only type widened from `str` to `tuple[str, float, int]`. All existing guard checks (`in`, `.get()`, `.pop()`) still work correctly. |
| Stop resubmission cap (DEC-372) | PASS | Stop retry code untouched |
| Reconciliation safety (DEC-369) | PASS | Only change is log throttling; `_broker_confirmed` logic untouched |
| Execution tests pass | PASS | 349 passed (verified independently) |

## 5. Escalation Criteria Check

| Criterion | Triggered? | Details |
|-----------|-----------|---------|
| Changes to flatten-pending guard beyond timeout | No | Guard logic preserved; type change is additive (stores more info). Guard still prevents duplicates via `in` check. |
| Changes to bracket order creation | No | Bracket code untouched |
| Changes to risk manager or quality engine | No | Not modified |
| Modification to exit_math.py | No | Not modified |
| Trail fix requires changes outside order_manager.py | No | Trail was config timing issue, not code bug. No fix needed. |

No escalation criteria triggered.

## 6. Code Quality Assessment

**Positive observations:**
- Tuple type for `_flatten_pending` is reasonable for an internal-only dict with 3 fields. A dataclass would be slightly more readable but the close-out correctly notes this is a judgment call.
- `list(self._flatten_pending.items())` for safe iteration during mutation is the correct pattern.
- SimulatedBroker immediate-fill handling in the timeout resubmit mirrors the existing pattern in `_trail_flatten` and `_flatten_position`.
- Config fields have sensible validation constraints (`ge=10` for timeout, `ge=1` for retries).

**Minor observations (non-blocking):**
- F7: The `_check_flatten_pending_timeouts()` method finds the position via `next((p for p in positions if not p.is_fully_closed), None)`. If a symbol has multiple open positions from different strategies (ALLOW_ALL policy, DEC-121), this picks the first one regardless of strategy. The resubmitted flatten order uses that position's `strategy_id` and `shares_remaining`. This matches how the existing `_trail_flatten` finds positions but could theoretically flatten the wrong strategy's position if both are open on the same symbol with a stale flatten. Risk is very low -- multi-strategy same-symbol is rare and the flatten is a safety net.
- F8: When `max_flatten_retries` exhausts, the position has no active flatten attempt and relies on EOD flatten or manual intervention. The log is ERROR-level which is appropriate. If the poll loop's EOD flatten also checks `_flatten_pending`, it would skip the symbol since the entry was removed. I verified the EOD flatten path calls `_flatten_position()` which re-checks `_flatten_pending` -- since the entry was popped, EOD flatten will proceed. This is correct behavior.

## 7. Test Assessment

8 new tests cover the core scenarios:
- R1: 2 tests (trail activation after T1, trail ratchet on tick)
- R2: 4 tests (timeout resubmit, max retries stop, timestamp tracking, fresh entry skip)
- R3: 1 test (throttled flatten-pending log)
- R4: 1 test (throttled reconciliation log)

Test quality is good. Tests use proper async fixtures, mock broker interactions, and verify internal state directly. The 2 pre-existing test fixes (YAML assertion updates) are appropriate -- the tests were broken by a prior config commit, not by this session's changes.

## 8. Close-Out Report Accuracy

- Self-assessment of MINOR_DEVIATIONS is accurate (fixing 2 pre-existing test failures was outside strict scope but necessary and appropriate).
- Change manifest is complete and matches the actual diff.
- Test counts match (3963 total, 8 new).
- No undocumented changes found.

## 9. Findings Summary

| ID | Severity | Finding |
|----|----------|---------|
| F1-F6 | -- | All session-specific review focus items verified clean |
| F7 | LOW | Multi-position same-symbol edge case in timeout resubmit (theoretical, matches existing pattern) |
| F8 | INFO | EOD flatten interaction verified correct -- entry removal allows EOD to proceed |

---

**Verdict: CLEAR**

All four requirements implemented correctly. No escalation criteria triggered. No forbidden files modified. All code paths traced and verified. Test coverage is adequate. The `_flatten_pending` type change is the most impactful modification and all 15+ access sites use the new tuple format correctly. The timeout mechanism integrates cleanly into the existing poll loop without creating races or interaction issues with EOD flatten.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28.75",
  "session": "S1",
  "verdict": "CLEAR",
  "findings": [
    {
      "id": "F7",
      "severity": "LOW",
      "category": "edge_case",
      "description": "Multi-position same-symbol edge case in _check_flatten_pending_timeouts() — picks first non-closed position regardless of strategy. Matches existing _trail_flatten pattern. Theoretical risk only.",
      "recommendation": "No action needed. Document if multi-strategy same-symbol becomes common in production."
    },
    {
      "id": "F8",
      "severity": "INFO",
      "category": "interaction_analysis",
      "description": "EOD flatten interaction with exhausted retries verified correct — popping entry from _flatten_pending allows EOD _flatten_position to proceed normally.",
      "recommendation": "None."
    }
  ],
  "escalation_triggers_checked": [
    "flatten-pending guard changes beyond timeout: NOT triggered",
    "bracket order creation changes: NOT triggered",
    "risk manager or quality engine changes: NOT triggered",
    "exit_math.py modification: NOT triggered",
    "trail fix outside order_manager.py: NOT triggered"
  ],
  "tests_pass": true,
  "test_count": 349,
  "test_command": "python -m pytest tests/execution/ -x -q",
  "forbidden_files_violated": false,
  "close_out_accurate": true
}
```
