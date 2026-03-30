---BEGIN-CLOSE-OUT---

**Session:** Sprint 28.75 — Session 1: Backend Operational Fixes
**Date:** 2026-03-30
**Self-Assessment:** MINOR_DEVIATIONS

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/core/config.py | modified | Added `flatten_pending_timeout_seconds` and `max_flatten_retries` to OrderManagerConfig (R2) |
| argus/execution/order_manager.py | modified | R2: flatten-pending timeout with cancel+resubmit. R3: ThrottledLogger for flatten-pending log. R4: ThrottledLogger for reconciliation log. Changed `_flatten_pending` type from `dict[str, str]` to `dict[str, tuple[str, float, int]]` for timestamp+retry tracking. |
| config/exit_management.yaml | not modified | Already had `trailing_stop.enabled: true` from operator change (commit 02afd29) |
| tests/execution/test_order_manager_sprint2875.py | added | 8 new tests for R1-R4 |
| tests/execution/test_order_manager_safety.py | modified | Updated `_flatten_pending` references to use new tuple format |
| tests/execution/test_order_manager_hardening.py | modified | Updated `_flatten_pending` reference to use new tuple format |
| tests/execution/test_order_manager_exit_management.py | modified | Updated `_flatten_pending` references to use new tuple format |
| tests/unit/core/test_exit_management_config.py | modified | Fixed pre-existing failure: YAML round-trip test now asserts `enabled=True` matching current config |
| tests/unit/strategies/test_atr_emission.py | modified | Fixed pre-existing failure: YAML load test now asserts `enabled=True` matching current config |

### Judgment Calls
- **Tuple format for _flatten_pending:** Changed from `dict[str, str]` to `dict[str, tuple[str, float, int]]` (order_id, monotonic_time, retry_count) instead of introducing a new dataclass. Rationale: minimal change, all access patterns are simple tuple indexing, and the dict is internal-only.
- **Fixed 2 pre-existing test failures:** `test_exit_management_config_round_trip_from_yaml` and `test_exit_management_yaml_loads` were asserting `enabled is False` but the YAML was changed to `true` in commit 02afd29 (before this sprint). Updated assertions to match current YAML state.
- **ThrottledLogger reuse:** Used existing `ThrottledLogger` from `argus/utils/log_throttle.py` rather than reimplementing rate-limiting. Consistent with Sprint 27.75 pattern.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| R1: Diagnose trailing stops not firing | DONE | Config timing confirmed as root cause. Code paths verified correct. 2 verification tests added. |
| R2: Flatten-pending timeout mechanism | DONE | `_check_flatten_pending_timeouts()` in order_manager.py, `flatten_pending_timeout_seconds` + `max_flatten_retries` on OrderManagerConfig |
| R3: Rate-limit "flatten already pending" logs | DONE | ThrottledLogger in `_flatten_position()`, 60s per-symbol suppression |
| R4: Rate-limit "portfolio snapshot missing" logs | DONE | ThrottledLogger in `reconcile_positions()`, 600s (10min) per-symbol suppression |
| Minimum 7 new tests | DONE | 8 new tests written and passing |
| All existing tests pass | DONE | 3963 passed (3955 existing + 8 new) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| DEC-117: Bracket orders on managed positions | PASS | Existing tests pass |
| DEC-363: Flatten-pending guard prevents duplicates | PASS | `test_flatten_pending_prevents_duplicate_orders` passes |
| DEC-372: Stop resubmission cap works | PASS | `test_stop_retry_max_*` tests pass |
| DEC-374: Duplicate fill dedup unchanged | PASS | `test_duplicate_fill_*` tests pass |
| Exit management config loads correctly | PASS | `test_trail_activation_after_t1` verifies exit_config is not None |
| Trailing stop activates after T1 | PASS | `test_trail_activation_after_t1` + `test_trail_stop_computed_on_tick` |

### Test Results
- Tests run: 3963
- Tests passed: 3963
- Tests failed: 0
- New tests added: 8
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None

### Notes for Reviewer
- R1 root cause is config timing (operator changed YAML mid-session, no hot-reload). No code bug found. The 2 pre-existing test failures (`test_exit_management_config_round_trip_from_yaml`, `test_exit_management_yaml_loads`) were caused by the same config change and are fixed in this session.
- The `_flatten_pending` type change from `dict[str, str]` to `dict[str, tuple[str, float, int]]` required updating 6 existing test files. Verify all access patterns are updated.
- The timeout check runs inside the poll loop (every 5s by default). It iterates `list(self._flatten_pending.items())` to allow mutation during iteration.
- Max retries exhausted removes the entry from `_flatten_pending` — the position will be caught by EOD flatten or manual intervention.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28.75",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 3955,
    "after": 3963,
    "new": 8,
    "all_pass": true
  },
  "files_created": [
    "tests/execution/test_order_manager_sprint2875.py",
    "docs/sprints/sprint-28.75/session-1-closeout.md"
  ],
  "files_modified": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "tests/execution/test_order_manager_safety.py",
    "tests/execution/test_order_manager_hardening.py",
    "tests/execution/test_order_manager_exit_management.py",
    "tests/unit/core/test_exit_management_config.py",
    "tests/unit/strategies/test_atr_emission.py"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [
    {
      "description": "2 tests asserting trailing_stop.enabled=False broke when operator changed exit_management.yaml to enabled=true (commit 02afd29)",
      "affected_session": "S2 (Sprint 28.5)",
      "affected_files": [
        "tests/unit/core/test_exit_management_config.py",
        "tests/unit/strategies/test_atr_emission.py"
      ],
      "severity": "LOW",
      "blocks_sessions": []
    }
  ],
  "deferred_observations": [
    "DEF-111: Trailing stop not firing was config timing — root cause documented, no code fix needed",
    "DEF-112: Flatten-pending timeout implemented (120s default, 3 retries)",
    "DEF-113: Flatten-pending log rate-limited (60s per symbol)",
    "DEF-114: Reconciliation log rate-limited (600s per symbol)"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "R1 confirmed as config timing issue — operator changed YAML while ARGUS was running, but ARGUS only loads config at startup. All trail code paths verified correct via 2 end-to-end tests. R2-R4 are straightforward additive changes to order_manager.py."
}
```
