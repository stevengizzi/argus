```markdown
---BEGIN-REVIEW---

**Reviewing:** [Sprint 27.95] — Session 2: Order Management Hardening
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-27
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 3 features implemented (stop retry cap, revision-rejected, fill dedup). No out-of-scope files modified. T1/T2 revision-rejected handling is a justified scope addition. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented (counter reset timing, amended prices storage). Self-assessment MINOR_DEVIATIONS is accurate. |
| Test Health | PASS | 304/304 execution tests pass. 8 failures in full suite are pre-existing (ai/, backtest/, intelligence/ — unrelated to session changes). 13 new tests cover all spec requirements. |
| Regression Checklist | PASS | Normal lifecycle, flatten_pending guard, bracket amendment logic, fill processing all verified. |
| Architectural Compliance | PASS | Uses existing close_position/flatten_position paths. No new external dependencies. Consistent naming and patterns. |
| Escalation Criteria | NONE_TRIGGERED | Stop retry exhaustion triggers emergency flatten (not unprotected position). No test hangs. Execution tests all pass. |

### Findings

**MEDIUM: Fill dedup cleanup in _close_position is largely ineffective (line 1663-1666)**

The fill dedup cleanup loop in `_close_position` iterates `_last_fill_state` keys and checks `_pending_orders` for matching symbol. However, by the time `_close_position` runs, the pending orders that triggered fills have already been popped from `_pending_orders` in `on_fill()` (line 448). This means the cleanup will rarely find matching entries. The comment acknowledges this ("cleared lazily... harmless but waste memory") and `_reset_state()` clears everything at EOD, so this is not a correctness bug, but the cleanup code is dead code in practice for the fill-triggered close path. It only works for flatten-triggered closes where some pending orders may still be registered.

**LOW: Fill dedup uses ARGUS ULID, not IBKR broker order ID**

The spec (review focus item 4) asks to verify dedup uses IBKR order ID. In practice, `OrderFilledEvent.order_id` carries the ARGUS ULID (mapped from IBKR orderId in `ibkr_broker.py:224`). The dedup still works correctly because duplicate callbacks from IBKR map to the same ULID with the same cumulative quantity. The close-out describes the key as "IBKR order_id" which is imprecise — it is the ARGUS-side order identifier. Functionally equivalent for dedup purposes.

**LOW: stop_retry_max default change (1 to 3) affects two distinct retry paths**

The `stop_retry_max` config field is shared between the pre-existing `_submit_stop_order` internal retry loop (broker connectivity failures) and the new `_resubmit_stop_with_retry` (IBKR cancel events). Changing the default from 1 to 3 increases both. The close-out correctly documented this as a deferred observation. No immediate risk — 3 retries for connectivity is reasonable — but separate config fields may be warranted if the two failure modes need different tuning.

**LOW: Float comparison for cumulative quantity dedup (line 439)**

The dedup uses `cumulative_qty == last_qty` with float comparison. The close-out notes this is safe because IBKR reports integer share counts for equities. This is correct for the current use case but would break silently if fractional shares were ever supported. No action needed for V1 (long-only equities).

**INFO: Revision-rejected handler has no retry/flatten fallback for T1/T2 failures**

The `_handle_revision_rejected` method handles T1 and T2 revision rejections by submitting fresh orders, but unlike the stop path, T1/T2 failures do not enter a retry flow or trigger any fallback. This is acceptable because T1/T2 are profit-taking orders (not protective), so failure is less critical than stop failure. The position remains protected by the stop order.

### Recommendation

CONCERNS: The implementation is functionally correct and all critical safety paths work as designed. The fill dedup cleanup inefficiency is a minor code quality issue that does not affect correctness (entries are harmless and cleared at EOD via `_reset_state()`). The shared `stop_retry_max` config should be tracked as a future cleanup item. No blocking issues found.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S2",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "Fill dedup cleanup in _close_position (lines 1663-1666) is largely ineffective: by the time _close_position runs, pending orders have already been popped from _pending_orders in on_fill(). The cleanup only catches flatten-path closes, not fill-triggered closes.",
      "severity": "MEDIUM",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "Consider keying fill dedup entries by symbol as a secondary index, or accept the current behavior with a more accurate comment explaining that entries persist until _reset_state()."
    },
    {
      "description": "Fill dedup uses ARGUS ULID (not IBKR broker order ID as spec review focus item 4 requested). Functionally correct because duplicate callbacks map to same ULID, but close-out description is imprecise.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "No code change needed. Update documentation to clarify the dedup key is the ARGUS-side order ID (which is 1:1 with IBKR order ID)."
    },
    {
      "description": "stop_retry_max default changed from 1 to 3, affecting both _submit_stop_order (broker connectivity retries) and _resubmit_stop_with_retry (IBKR cancel retries). Two distinct failure modes share one config knob.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/core/config.py",
      "recommendation": "Track as deferred item: consider separate config fields if the two retry paths need different limits."
    },
    {
      "description": "Float equality comparison for cumulative quantity dedup. Safe for integer share counts (equities) but fragile if fractional shares are ever supported.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "No action needed for V1. If fractional shares are added, switch to >= comparison or integer cast."
    },
    {
      "description": "T1/T2 revision-rejected handler has no retry/flatten fallback on failure (unlike stop path). Acceptable because these are profit-taking orders, not protective.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "No action needed. Protective stop has full retry+flatten; profit targets are best-effort."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "All spec requirements implemented. Minor deviations: (1) counter resets on position close instead of stop acknowledgment (documented judgment call — no separate ack callback exists), (2) revision-rejected handling extended to T1/T2 (justified scope addition).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/execution/order_manager.py",
    "argus/core/config.py",
    "tests/execution/test_order_manager_hardening.py",
    "argus/execution/ibkr_broker.py",
    "argus/core/events.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 304,
    "new_tests_adequate": true,
    "test_quality_notes": "13 new tests cover all 3 features with good edge case coverage including per-symbol isolation (test 13), flatten_pending guard interaction (test 4), and exponential backoff progression (test 7). Full suite: 3648 passed, 8 failed (pre-existing in ai/backtest/intelligence — unrelated to session changes)."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Normal position lifecycle unchanged", "passed": true, "notes": "All existing 291 execution tests pass"},
      {"check": "_flatten_pending guard (DEC-363) intact", "passed": true, "notes": "Test 4 explicitly verifies guard respected during emergency flatten"},
      {"check": "Bracket amendment (DEC-366) price calculation intact", "passed": true, "notes": "_amend_bracket_on_slippage logic unchanged; only _amended_prices storage added after existing price computation"},
      {"check": "Fill processing for non-duplicate callbacks unchanged", "passed": true, "notes": "Dedup check allows first fill through; existing fill tests all pass"},
      {"check": "Full test suite passes, no hangs", "passed": true, "notes": "3648 passed, 8 pre-existing failures (ai/backtest/intelligence), no hangs (218s runtime)"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Track fill dedup cleanup inefficiency as minor tech debt (LOW priority)",
    "Track shared stop_retry_max config as deferred item for potential split"
  ]
}
```
