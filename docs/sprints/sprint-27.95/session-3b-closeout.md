```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 27.95 S3b — Overflow Routing Logic
**Date:** 2026-03-27
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/main.py | modified | Added OrderApprovedEvent import; inserted overflow check in _process_signal() after RM approval, before event publish |
| argus/core/events.py | modified | Updated SignalRejectedEvent.rejection_stage comment to include BROKER_OVERFLOW |
| tests/test_overflow_routing.py | added | 9 tests covering overflow routing: below/at/above capacity, SIMULATED bypass, disabled flag, event fields, RM rejection non-interference |

### Judgment Calls
- Used `getattr(self, '_order_manager', None)` instead of `self._order_manager is not None` to avoid AttributeError in test harnesses that use `object.__new__(ArgusSystem)` without `__init__`. This ensures backward compatibility with existing test patterns in test_signal_rejected.py.
- OverflowConfig was already wired into SystemConfig (via `overflow: OverflowConfig` on SystemConfig, Session 3a), so no additional init/start wiring was needed — accessed directly as `config.system.overflow`.
- Wrote 9 tests (3 more than the 6 minimum) to cover edge cases: quality metadata pass-through, counterfactual-disabled + overflow, and RM rejection non-interference.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Overflow check in _process_signal() after RM approval, before order placement | DONE | argus/main.py:1396-1426 |
| Expose active_position_count from OrderManager | DONE | Already existed as `open_position_count` property (order_manager.py:1728-1734) |
| Wire OverflowConfig into main application | DONE | Already on SystemConfig from S3a; accessed as config.system.overflow |
| Publish SignalRejectedEvent with correct fields | DONE | argus/main.py:1416-1425 — stage, reason, quality, regime snapshot |
| Add INFO logging for overflow routing | DONE | argus/main.py:1407-1413 |
| BrokerSource.SIMULATED bypass | DONE | argus/main.py:1399 |
| 6+ new tests | DONE | 9 tests in tests/test_overflow_routing.py |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| _process_signal() flow order preserved | PASS | quality -> RM -> overflow -> order placement confirmed in code |
| Quality pipeline unchanged | PASS | No modifications to quality engine code or tests |
| Risk Manager gating unchanged | PASS | No modifications to RM code or tests |
| Order placement for sub-capacity signals unchanged | PASS | Test 1 confirms below-capacity signals publish OrderApprovedEvent |
| BacktestEngine unaffected | PASS | Test 4 confirms SIMULATED bypass; overflow check short-circuits |

### Test Results
- Tests run: 913 (scoped) + 9 (new)
- Tests passed: 922
- Tests failed: 0
- New tests added: 9
- Command used: `python -m pytest tests/test_signal_rejected.py tests/test_overflow_routing.py tests/execution/ tests/core/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- The overflow check uses `open_position_count` (existing property) rather than adding a new `active_position_count` — same semantics, avoids redundant API surface.
- The check is positioned between RM evaluation and `await self._event_bus.publish(result)`, so an overflow-routed signal never triggers OrderManager subscription.
- When counterfactual is disabled but overflow triggers, the signal is still dropped (returns early) but no SignalRejectedEvent is published — consistent with existing behavior for other rejection stages.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S3b",
  "verdict": "COMPLETE",
  "tests": {
    "before": 913,
    "after": 922,
    "new": 9,
    "all_pass": true
  },
  "files_created": ["tests/test_overflow_routing.py"],
  "files_modified": ["argus/main.py", "argus/core/events.py"],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Used existing open_position_count property instead of adding new active_position_count. Used getattr for _order_manager to maintain compatibility with object.__new__ test pattern."
}
```
