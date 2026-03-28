```markdown
---BEGIN-REVIEW---

**Reviewing:** Sprint 27.95 S5 — Carry-Forward Cleanup
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-28
**Verdict:** CLEAR

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 3 spec fixes implemented. S4 restoration was necessary (documented as judgment call). No protected files modified. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. MINOR_DEVIATIONS self-assessment is appropriate given S4 restoration scope addition. |
| Test Health | PASS | 417 tests pass (scoped). 18 new tests added. No hangs. |
| Regression Checklist | PASS | All sprint-level regression checks pass. See details below. |
| Architectural Compliance | PASS | Config split follows existing pattern. Zero-qty guard is clean. Attribute access split is idiomatic. |
| Escalation Criteria | NONE_TRIGGERED | No position lifecycle breakage, no reconciliation regression, stop resubmission cap intact, startup flatten guarded correctly. |

### Session-Specific Focus Verification

1. **Zero-qty guard fires BEFORE `_flatten_unknown_position()`:** VERIFIED. At line 1351, `if abs(qty) <= 0` check with `continue` fires before line 1358 `_flatten_unknown_position()` call.

2. **Normal close path uses direct `position.original_stop_price`:** VERIFIED. At line 1771, `stop = position.original_stop_price or 0.0` — no `getattr`.

3. **Reconciliation close path still uses `getattr` with fallback:** VERIFIED. At line 1766, `stop = getattr(position, "original_stop_price", 0.0) or 0.0` with explanatory comment at lines 1763-1765.

4. **`_resubmit_stop_with_retry` references `stop_cancel_retry_max`:** VERIFIED. Lines 600 and 616 both reference `self._config.stop_cancel_retry_max`.

5. **`_submit_stop_order` still references `stop_retry_max`:** VERIFIED. Lines 1539, 1563, 1568 all reference `self._config.stop_retry_max` — unchanged.

6. **Both YAML files have `stop_cancel_retry_max`:** The spec said to add to system.yaml and system_live.yaml, but the session correctly identified that OrderManager config lives in `config/order_manager.yaml` (line 31 has `stop_cancel_retry_max: 3`). This is the right file. Documented as judgment call.

7. **Startup YAML sections in both system.yaml and system_live.yaml:** VERIFIED. system.yaml line 44 and system_live.yaml line 175 both have `startup: flatten_unknown_positions: true`.

### Regression Checklist Results

| Check | Result |
|-------|--------|
| Normal position lifecycle unchanged | PASS — all existing lifecycle tests pass |
| Reconciliation redesign (S1a) intact | PASS — test_order_manager_reconciliation_redesign.py passes |
| Trade logger fix (S1b) intact | PASS — test_trade_logger_reconciliation.py passes |
| Order mgmt hardening (S2) intact | PASS — test_order_manager_hardening.py passes |
| Startup zombie cleanup (S4) intact | PASS — 11 startup tests in test_order_manager.py pass |
| Overflow routing (S3b) intact | PASS — test_overflow_routing.py passes |
| Overflow to counterfactual (S3c) intact | PASS — test_counterfactual_overflow.py passes |
| Full scoped test suite passes, no hangs | PASS — 417 passed in 5.97s |

### Findings

No findings with severity MEDIUM or above.

**INFO: S4 restoration was necessary due to S3b overwrite.** The close-out correctly documents that commit 800695b (S3b) overwrote all S4 changes. The session restored S4 code before applying S5 fixes. This is a larger diff than the S5 spec alone would suggest but was unavoidable. The restored code matches the S4 intent (zombie classification, helper extraction, StartupConfig wiring).

**INFO: YAML location correction.** The spec directed adding `stop_cancel_retry_max` to system.yaml and system_live.yaml, but OrderManager config lives in `config/order_manager.yaml`. The session correctly placed it there instead. This is a spec correction, not a deviation.

### Recommendation

Proceed to next session. All three carry-forward fixes are correctly implemented, the S4 restoration is sound, and all tests pass.

---END-REVIEW---
```

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.95",
  "session": "S5",
  "verdict": "CLEAR",
  "findings": [
    {
      "description": "S4 restoration was necessary because S3b (800695b) overwrote all S4 changes. Diff is larger than S5 spec alone would suggest.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "argus/execution/order_manager.py",
      "recommendation": "No action needed — documented in close-out judgment calls."
    },
    {
      "description": "stop_cancel_retry_max added to config/order_manager.yaml instead of system.yaml/system_live.yaml as spec directed. This is correct — OrderManager config lives in order_manager.yaml.",
      "severity": "INFO",
      "category": "OTHER",
      "file": "config/order_manager.yaml",
      "recommendation": "No action needed — spec correction documented."
    }
  ],
  "spec_conformance": {
    "status": "MINOR_DEVIATION",
    "notes": "All 3 fixes implemented correctly. S4 restoration was out-of-spec but necessary. YAML location corrected from spec (order_manager.yaml instead of system.yaml).",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/core/config.py",
    "argus/execution/order_manager.py",
    "argus/main.py",
    "config/order_manager.yaml",
    "config/system.yaml",
    "config/system_live.yaml",
    "tests/execution/test_order_manager.py",
    "tests/execution/test_order_manager_hardening.py",
    "tests/core/test_config.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 417,
    "new_tests_adequate": true,
    "test_quality_notes": "18 new tests covering zero-qty guard, config split, YAML alignment, and cancel retry config usage. Exceeds spec minimum of 4."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "Normal position lifecycle unchanged", "passed": true, "notes": "All existing lifecycle tests pass"},
      {"check": "Reconciliation redesign (S1a) intact", "passed": true, "notes": "test_order_manager_reconciliation_redesign.py passes"},
      {"check": "Trade logger fix (S1b) intact", "passed": true, "notes": "test_trade_logger_reconciliation.py passes"},
      {"check": "Order mgmt hardening (S2) intact", "passed": true, "notes": "test_order_manager_hardening.py passes"},
      {"check": "Startup zombie cleanup (S4) intact", "passed": true, "notes": "11 startup tests pass"},
      {"check": "Overflow routing (S3b) intact", "passed": true, "notes": "test_overflow_routing.py passes"},
      {"check": "Overflow to counterfactual (S3c) intact", "passed": true, "notes": "test_counterfactual_overflow.py passes"},
      {"check": "Full scoped test suite passes, no hangs", "passed": true, "notes": "417 passed in 5.97s"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": []
}
```
