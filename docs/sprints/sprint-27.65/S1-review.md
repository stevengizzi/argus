```markdown
---BEGIN-REVIEW---

**Reviewing:** Sprint 27.65 S1 — Order Management Safety
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-24
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All R1/R2/R3 requirements implemented. Strategy file changes in working tree are from S3, not S1. |
| Close-Out Accuracy | PASS | Change manifest matches actual diff. Judgment calls documented. Self-assessment CLEAN is justified for S1-scoped changes. |
| Test Health | PASS | 3,377 tests passing (full suite). 13 new tests in test_order_manager_safety.py (spec required 10+). |
| Regression Checklist | PASS | Normal stop/target paths unaffected (verified by test_flatten_pending_does_not_block_normal_stop_loss). Time-stop guard verified. Shutdown ordering verified by code inspection. |
| Architectural Compliance | PASS | No new order paths bypass Risk Manager. Broker ABC extended cleanly. Reconciliation is read-only. |
| Escalation Criteria | NONE_TRIGGERED | No bypass paths introduced, reconciliation is warn-only, flatten guard does not affect stop/target fills, SimulatedBroker works correctly. |

### Findings

**MEDIUM — Shutdown cancel_all_orders integration test gap**
File: `tests/execution/test_order_manager_safety.py`, line 358-367
The `test_graceful_shutdown_cancels_orders` test only verifies that a mock broker's `cancel_all_orders()` method can be called and returns a value. It does not test the actual shutdown sequence in `ArgusSystem.stop()` where `cancel_all_orders()` must execute before `order_manager.stop()` and `broker.disconnect()`. The ordering is correct by code inspection (cancel at step 2a, line 1573; disconnect at line 1605), but there is no integration test that would catch a future reordering regression.

**LOW — Type escape hatch in reconciliation endpoint**
File: `argus/api/routes/positions.py`, line 170
The expression `list(result.get("discrepancies", []))  # type: ignore[arg-type]` uses a type ignore because `_last_reconciliation` is typed as `dict[str, object]`. A stricter approach would be to define a `ReconciliationResult` dataclass/model and use that instead of `dict[str, object]`, but this is cosmetic and does not affect correctness.

**LOW — SimulatedBroker cancel_all_orders clears pending brackets**
File: `argus/execution/simulated_broker.py`
The SimulatedBroker implementation clears `_pending_brackets` on `cancel_all_orders()`. The close-out report describes this as a no-op, but it actually clears state. This is fine for shutdown scenarios but worth noting for accuracy. During backtesting, `cancel_all_orders()` would not normally be called, so this has no practical impact.

**INFO — Working tree contains uncommitted changes from multiple sessions**
The working tree has modifications from both S1 and S3 (strategy file changes in `pattern_strategy.py` and `red_to_green.py`). This makes it harder to isolate S1-specific changes for review. The S1 changes were verified by examining only the S1-scoped files in the diff. The strategy changes are clearly S3 scope (backfill_candles, initialize_prior_closes, candle window reordering) and are not attributable to S1.

### Recommendation
CONCERNS due to the shutdown integration test gap. The fix is straightforward: add a test that instantiates a minimal ArgusSystem (or mocks one) and verifies that `cancel_all_orders()` is called before `order_manager.stop()` in the shutdown sequence. This could be addressed in a future session or as part of S2+ if there is room. The core implementation is correct and safe to proceed with.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.65",
  "session": "S1",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "test_graceful_shutdown_cancels_orders only tests mock broker method call, not the actual shutdown sequence ordering in ArgusSystem.stop(). A future reordering could go undetected.",
      "severity": "MEDIUM",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/execution/test_order_manager_safety.py",
      "recommendation": "Add integration test verifying cancel_all_orders() is called before order_manager.stop() and broker.disconnect() in the shutdown sequence."
    },
    {
      "description": "Reconciliation endpoint uses type: ignore[arg-type] due to dict[str, object] typing on _last_reconciliation.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/api/routes/positions.py",
      "recommendation": "Consider replacing dict[str, object] with a typed dataclass or Pydantic model for _last_reconciliation."
    },
    {
      "description": "SimulatedBroker.cancel_all_orders() clears _pending_brackets (not truly a no-op as described in close-out). Correct behavior but description mismatch.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/execution/simulated_broker.py",
      "recommendation": "Minor documentation accuracy fix."
    },
    {
      "description": "Working tree has uncommitted changes from S1 and S3 sessions mixed together, making per-session review more complex.",
      "severity": "INFO",
      "category": "OTHER",
      "recommendation": "Commit session work separately to enable cleaner per-session diffs."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All three requirements (R1 flatten guard, R2 shutdown cancel, R3 reconciliation) implemented per spec. No deviations.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/execution/order_manager.py",
    "argus/execution/broker.py",
    "argus/execution/ibkr_broker.py",
    "argus/execution/alpaca_broker.py",
    "argus/execution/simulated_broker.py",
    "argus/api/routes/positions.py",
    "argus/main.py",
    "tests/execution/test_order_manager_safety.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 3377,
    "new_tests_adequate": true,
    "test_quality_notes": "13 new tests cover all specified scenarios (flatten guard prevent/clear on fill/cancel/reject/position close, stop-loss unblocked, shutdown cancel, reconciliation mismatch/synced/broker-only/endpoint/no-auto-correct). Missing: integration test for shutdown sequence ordering."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Normal stop-loss path works", "passed": true, "notes": "Verified by test_flatten_pending_does_not_block_normal_stop_loss"},
      {"check": "Normal target-hit path works", "passed": true, "notes": "Target fill path goes through on_fill, not _flatten_position; unaffected by guard"},
      {"check": "Time-stop fires exactly once", "passed": true, "notes": "Verified by test_flatten_pending_prevents_duplicate_orders (3 cycles, 1 order)"},
      {"check": "Shutdown cancels orders", "passed": true, "notes": "cancel_all_orders at step 2a before order_manager.stop at step 3 and disconnect; verified by code inspection"},
      {"check": "SimulatedBroker unaffected", "passed": true, "notes": "Full test suite passes including backtest tests; SimulatedBroker cancel_all_orders is safe"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Add shutdown-sequence integration test to verify cancel_all_orders ordering"
  ]
}
```

### Post-Review Resolution

All S1 reviewer findings were resolved in Sprint 27.65 S2:

| Finding | Severity | Status | Resolution Session |
|---------|----------|--------|-------------------|
| Shutdown ordering integration test gap | MEDIUM | RESOLVED | S2 — `test_shutdown_sequence_ordering` added |
| Reconciliation endpoint `type: ignore[arg-type]` | LOW | RESOLVED | S2 — `ReconciliationResult` dataclass replaces `dict[str, object]` |
| SimulatedBroker close-out description mismatch | LOW | RESOLVED | S2 — S1 close-out updated with correction |

**Updated Verdict:** CONCERNS_RESOLVED

```json:post-review-verdict
{
  "original_verdict": "CONCERNS",
  "updated_verdict": "CONCERNS_RESOLVED",
  "resolution_session": "S2",
  "post_review_fixes": [
    {
      "finding": "Shutdown cancel_all_orders integration test gap",
      "severity": "MEDIUM",
      "fix": "test_shutdown_sequence_ordering added to test_order_manager_safety.py"
    },
    {
      "finding": "Reconciliation endpoint type: ignore",
      "severity": "LOW",
      "fix": "ReconciliationResult dataclass replaces dict[str, object]; type: ignore removed"
    },
    {
      "finding": "SimulatedBroker cancel_all_orders described as no-op",
      "severity": "LOW",
      "fix": "S1 close-out corrected: clears _pending_brackets, not a no-op"
    }
  ]
}
```
