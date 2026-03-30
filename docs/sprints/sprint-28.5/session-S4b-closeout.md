```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 28.5 S4b — Order Manager: Trailing Stop + Escalation Logic
**Date:** 2026-03-30
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/execution/order_manager.py | modified | Added trailing stop activation (after_t1, after_profit_pct, immediate), trail check in on_tick using exit_math, _trail_flatten (AMD-2/4/8), escalation in poll loop (AMD-3/6/8), _escalation_update_stop (AMD-3/6), trail exit reason in _handle_flatten_fill |
| tests/execution/test_order_manager_exit_management.py | added | 18 new tests covering all spec requirements: trail activation, ratchet-up, flatten guards, escalation phases, AMD-2/3/4/6/8 safety invariants |

### Judgment Calls
- Added `ExitReason.TRAILING_STOP` detection in `_handle_flatten_fill` by checking `position.trail_active` — the spec did not specify how flatten fills would know the exit reason, but trail_active is the cleanest indicator without adding a new field.
- Trail flatten also cancels T1/T2 orders if still open (not just the safety stop) — follows the pattern of `_flatten_position` for completeness.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Trail activation in _handle_t1_fill (after_t1) | DONE | order_manager.py:_handle_t1_fill, lines after breakeven stop submission |
| Trail check in on_tick using exit_math | DONE | order_manager.py:on_tick, replaced V1 skeleton with compute_trailing_stop + compute_effective_stop |
| _trail_flatten with AMD-2 (sell first, cancel second) | DONE | order_manager.py:_trail_flatten — place_order before cancel_order |
| AMD-4 shares_remaining > 0 guard | DONE | order_manager.py:_trail_flatten step 2 |
| AMD-8 _flatten_pending check FIRST | DONE | order_manager.py:_trail_flatten step 1, escalation poll loop guard |
| Escalation in fallback poll loop | DONE | order_manager.py:_poll_loop, after time stop checks |
| AMD-3 escalation failure recovery (flatten) | DONE | order_manager.py:_escalation_update_stop exception handler |
| AMD-6 escalation exempt from retry cap | DONE | _escalation_update_stop does not touch _stop_retry_count |
| after_profit_pct activation mode | DONE | order_manager.py:on_tick, before trail check |
| immediate activation mode | DONE | order_manager.py:_handle_entry_fill, after position creation |
| 15+ new tests | DONE | 18 tests in test_order_manager_exit_management.py |
| All existing OM tests passing | DONE | 153 existing + 18 new = 171 total |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Non-trail positions unchanged | PASS | Test 14 confirms no exit_config → identical behavior |
| T1/T2 bracket flow preserved | PASS | All 153 existing OM tests pass |
| EOD flatten still works | PASS | Existing EOD tests pass |
| _flatten_pending covers trail path | PASS | Test 8 (AMD-8) confirms complete no-op |
| DEC-374 dedup still works | PASS | Existing dedup tests pass |
| _stop_retry_count unaffected by escalation | PASS | Test 12 (AMD-6) confirms |

### Test Results
- Tests run: 171 (OM suite) + 223 (broader execution + exit_math)
- Tests passed: 171 + 223
- Tests failed: 0
- New tests added: 18
- Command used: `python -m pytest tests/execution/test_order_manager*.py -x -q` and `python -m pytest tests/execution/ tests/unit/core/test_exit_math.py tests/unit/core/test_exit_management_config.py -x -q`

### Unfinished Work
None

### Notes for Reviewer
- CRITICAL (AMD-2): In `_trail_flatten`, `place_order` (market sell) is called at step 3, `cancel_order` (safety stop) at step 4. This order-of-operations is the #1 safety requirement.
- CRITICAL (AMD-8): `_flatten_pending` check is the absolute first line in `_trail_flatten` (before any broker calls or state changes). Defense-in-depth guard also added inside `_escalation_update_stop`.
- The old V1 trailing stop skeleton (`enable_trailing_stop` config flag, `trailing_stop_atr_multiplier`) is fully replaced. The V1 config fields still exist in `OrderManagerConfig` but are no longer referenced in `on_tick`.
- Trail flatten exit reason is determined in `_handle_flatten_fill` by checking `position.trail_active`.

### Tier 2 Review Findings Addressed
- **F1 (MEDIUM):** Test 17 rewritten to call `_escalation_update_stop` directly (production code) instead of reimplementing the logic in test code.
- **F2 (MEDIUM):** Test 9 rewritten to call `_escalation_update_stop` directly and verify broker stop was updated.
- **F4 (LOW):** Added defense-in-depth `_flatten_pending` guard inside `_escalation_update_stop` itself (not just poll loop caller).

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28.5",
  "session": "S4b",
  "verdict": "COMPLETE",
  "tests": {
    "before": 153,
    "after": 171,
    "new": 18,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_order_manager_exit_management.py"
  ],
  "files_modified": [
    "argus/execution/order_manager.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "V1 trailing stop config fields (enable_trailing_stop, trailing_stop_atr_multiplier) on OrderManagerConfig are now dead code — could be removed in a cleanup pass"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Trail flatten exit reason detection uses position.trail_active flag in _handle_flatten_fill rather than adding a new 'reason' field to PendingManagedOrder. This is simpler and avoids schema changes. Trail flatten also cancels T1/T2 if open (not just stop) for safety completeness."
}
```
