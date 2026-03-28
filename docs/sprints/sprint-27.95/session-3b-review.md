```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 27.95 S3b] — Overflow Routing Logic
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-27
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 7 spec requirements implemented. Only main.py and events.py modified (plus new test file). No protected files touched. |
| Close-Out Accuracy | PASS | Change manifest matches diff exactly. Judgment calls documented (getattr pattern, existing open_position_count reuse). Self-assessment CLEAN is justified. |
| Test Health | PASS | 913 passed, 0 failed. 9 new tests added covering all spec-required cases plus 3 extras. |
| Regression Checklist | PASS | All 6 sprint-level checks verified (see details below). |
| Architectural Compliance | PASS | Overflow check correctly positioned in pipeline. Event Bus pattern followed. No new dependencies. |
| Escalation Criteria | NONE_TRIGGERED | No overflow routing blocks valid signals. No pipeline flow disruption. No signal count divergence. |

### Findings

**Review Focus Item 1: Overflow check is AFTER Risk Manager approval** -- VERIFIED
Line 1394 calls `self._risk_manager.evaluate_signal(signal)`. The overflow check at line 1396-1426 begins with `isinstance(result, OrderApprovedEvent)`, confirming it only fires after RM returns an approval. Signals rejected by RM skip the overflow block entirely.

**Review Focus Item 2: Overflow check is BEFORE order placement** -- VERIFIED
The `await self._event_bus.publish(result)` that triggers OrderManager's `on_approved()` subscription is at line 1428, after the overflow block's `return` at line 1426. An overflow-routed signal never reaches the OrderApprovedEvent publish.

**Review Focus Item 3: BrokerSource.SIMULATED bypass is unconditional** -- VERIFIED
Line 1399: `config.system.broker_source != BrokerSource.SIMULATED` is the second condition in the compound `if`. Short-circuit evaluation means SIMULATED broker exits the condition immediately regardless of overflow.enabled, capacity, or position count. Test 4 confirms this.

**Review Focus Item 4: SignalRejectedEvent fields match CounterfactualTracker expectations** -- VERIFIED
The handler `_on_signal_rejected_for_counterfactual` (line 1490) reads: `event.signal`, `event.rejection_reason`, `event.rejection_stage` (converted via `RejectionStage(event.rejection_stage)`), `event.quality_score`, `event.quality_grade`, `event.regime_vector_snapshot`, `event.metadata`. The overflow code sets all these fields. `RejectionStage("broker_overflow")` will resolve correctly since `BROKER_OVERFLOW = "broker_overflow"` exists in the enum (added in S3a at counterfactual.py:41).

**Review Focus Item 5: Position count source is real positions only** -- VERIFIED
`OrderManager.open_position_count` (order_manager.py:1729-1734) counts from `self._managed_positions`, which only contains real broker positions. Counterfactual shadow positions are tracked separately in `CounterfactualTracker._open_positions`.

**Review Focus Item 6: No modification to existing rejection paths** -- VERIFIED
The diff shows no changes to quality_filter (lines 1322), position_sizer (lines 1360), risk_manager (lines 1430-1439), or shadow (lines 1255) rejection paths. The overflow block is purely additive between RM evaluation and result publish.

### Regression Checklist Results
| Check | Result |
|-------|--------|
| Signal pipeline flow order preserved (quality -> RM -> overflow -> order) | PASS |
| Quality Engine unchanged | PASS -- no quality engine files in diff |
| Risk Manager unchanged | PASS -- no risk manager files in diff |
| BacktestEngine unaffected (SIMULATED bypass) | PASS -- test 4 confirms; no backtest files in diff |
| Existing rejection paths unchanged | PASS -- diff is purely additive |
| Full test suite passes, no hangs | PASS -- 913 passed in 7.15s |

### Recommendation
Proceed to next session. Implementation is clean, correctly positioned in the pipeline, and well-tested.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S3b",
  "verdict": "CLEAR",
  "findings": [],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 7 spec requirements implemented. Used existing open_position_count instead of adding new active_position_count -- functionally equivalent, avoids redundant API surface.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/main.py",
    "argus/core/events.py",
    "argus/execution/order_manager.py",
    "argus/intelligence/counterfactual.py",
    "tests/test_overflow_routing.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 913,
    "new_tests_adequate": true,
    "test_quality_notes": "9 new tests cover all 6 spec-required scenarios plus 3 extras (quality metadata pass-through, counterfactual-disabled + overflow, RM rejection non-interference). Tests use realistic event bus assertions, not just mock verification."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Signal pipeline flow order preserved", "passed": true, "notes": "Code inspection confirms quality -> RM -> overflow -> order placement"},
      {"check": "Quality Engine unchanged", "passed": true, "notes": "No quality engine files in diff"},
      {"check": "Risk Manager unchanged", "passed": true, "notes": "No risk manager files in diff"},
      {"check": "BacktestEngine unaffected (SIMULATED bypass)", "passed": true, "notes": "Test 4 confirms SIMULATED bypass; no backtest files in diff"},
      {"check": "Existing rejection paths unchanged", "passed": true, "notes": "Diff is purely additive between RM eval and result publish"},
      {"check": "Full test suite passes, no hangs", "passed": true, "notes": "913 passed in 7.15s, 0 failures"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": []
}
```
