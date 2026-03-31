---BEGIN-CLOSE-OUT---

**Session:** Sprint 29.5 S1 — Flatten/Zombie Safety Overhaul
**Date:** 2026-03-31
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/execution/ibkr_errors.py | modified | Added error 404 to IBKR_ERROR_MAP (qty mismatch on SELL) |
| argus/execution/ibkr_broker.py | modified | Added error_404_symbols set + error 404 handler in _on_error |
| argus/core/config.py | modified | Added max_flatten_cycles field to OrderManagerConfig |
| argus/execution/order_manager.py | modified | R1-R5: broker re-query on 404, circuit breaker, EOD broker-only pass, startup queue, log suppression |
| config/order_manager.yaml | modified | Added flatten_pending_timeout, max_flatten_retries, max_flatten_cycles entries |
| tests/execution/test_ibkr_errors.py | modified | Added 404 to expected error codes set |
| tests/execution/test_order_manager_sprint295.py | added | 14 new tests for all 6 requirements |

### Judgment Calls
- Used `warn_throttled` (WARNING level) for suppressed time-stop logs instead of adding a new `info_throttled` method to ThrottledLogger. ThrottledLogger only has `warn_throttled`; adding a new method was out of scope. WARNING level is acceptable since these only fire when something is already wrong (flatten pending/abandoned).
- Added `et_tz2`/`now_et2` variables in the poll loop drain check to avoid shadowing the `et_tz`/`now_et` from the EOD flatten check (which may not execute due to the `if not self._flattened_today` guard).

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| R1: IBKR error 404 root-cause fix | DONE | ibkr_broker.py:error_404_symbols set + order_manager.py:_check_flatten_pending_timeouts broker re-query |
| R2: Global circuit breaker | DONE | order_manager.py:_flatten_cycle_count, _flatten_abandoned, cycle tracking in _check_flatten_pending_timeouts |
| R3: EOD flatten covers broker-only positions | DONE | order_manager.py:eod_flatten Pass 2 with get_positions + _flatten_unknown_position |
| R4: Startup zombie flatten queued for market open | DONE | order_manager.py:_startup_flatten_queue, _flatten_unknown_position market-hours gate, _drain_startup_flatten_queue, poll loop drain |
| R5: Time-stop log suppression | DONE | order_manager.py:_suppress_log flag + warn_throttled in time-stop section |
| R6: max_flatten_cycles config | DONE | config.py:OrderManagerConfig.max_flatten_cycles + config/order_manager.yaml |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Existing flatten-pending timeout still works | PASS | test_flatten_pending_timeout (existing tests in sprint2875) all pass |
| EOD flatten still triggers shutdown | PASS | ShutdownRequestedEvent still published in eod_flatten |
| Broker-confirmed positions still protected | PASS | _broker_confirmed dict unchanged |
| Trailing stop flatten path unchanged | PASS | _trail_flatten and trail tests unchanged and passing |

### Test Results
- Tests run: 4192
- Tests passed: 4192
- Tests failed: 0
- New tests added: 14 (12 required + 2 bonus config tests)
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- Verify error 404 detection in _on_error does NOT interfere with normal SELL order flow (error 404 only adds to the set; normal orders are unaffected since the set is only checked during _check_flatten_pending_timeouts)
- The _flatten_abandoned set is cleared by eod_flatten BEFORE iterating managed positions, ensuring abandoned symbols get one final EOD attempt
- EOD broker-only flatten uses get_positions which returns all broker positions; managed_symbols filter ensures it only flattens untracked ones (no overlap with _broker_confirmed since those are tracked in _managed_positions)
- Startup queue drain fires in the poll loop, not via event subscription. The queue empties on first drain, so repeated poll iterations are no-ops.
- _flatten_unknown_position now checks market hours via clock (not datetime.now), making it testable with FixedClock

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "29.5",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 4178,
    "after": 4192,
    "new": 14,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_order_manager_sprint295.py",
    "docs/sprints/sprint-29.5/session-1-closeout.md"
  ],
  "files_modified": [
    "argus/execution/ibkr_errors.py",
    "argus/execution/ibkr_broker.py",
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "config/order_manager.yaml",
    "tests/execution/test_ibkr_errors.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Used warn_throttled for time-stop log suppression since ThrottledLogger lacks info_throttled. Market-hours check uses clock injection for testability."
}
```
