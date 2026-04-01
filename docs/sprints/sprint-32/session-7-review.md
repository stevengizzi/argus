---BEGIN-REVIEW---

**Reviewing:** Sprint 32, Session 7 — Autonomous Promotion Evaluator
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-01
**Verdict:** CONCERNS

### Assessment Summary
| Category | Result | Notes |
|----------|--------|-------|
| Scope Compliance | PASS | All 10 spec requirements verified in code. No out-of-scope modifications. |
| Close-Out Accuracy | PASS | Change manifest matches diff. Judgment calls documented. Self-assessment CLEAN is slightly optimistic given F1 below. |
| Test Health | PASS | 4373 passed, 0 failed. 8 new tests covering promotion, demotion, hysteresis, persistence order, idempotency. |
| Regression Checklist | PASS | R6, R7, R8, R11 verified. Protected files untouched. Full suite green. |
| Architectural Compliance | PASS | Uses compare() from comparison.py, duck-typed deps match codebase pattern, config-gated. |
| Escalation Criteria | NONE_TRIGGERED | No throughput, memory, contention, or collision concerns from this session. |

### Findings

**F1 (MEDIUM): NoneType crash path when counterfactual is disabled**
File: `argus/intelligence/experiments/promotion.py`, lines 378-388.
`_build_result_from_shadow()` calls `self._counterfactual_store.query(...)` without guarding for `None`. In `main.py` line 847, `self._counterfactual_store` (which can be `None` if the counterfactual subsystem is disabled) is passed directly to `PromotionEvaluator.__init__`. If `experiments.enabled=true` but `counterfactual.enabled=false`, `evaluate_all_variants()` will raise `AttributeError` when evaluating any shadow variant. The comment on line 839-840 claims "PromotionEvaluator accepts duck-typed dependencies and handles missing data gracefully" but no None-guard exists in the evaluator code.

Mitigation: The crash is caught by the `try/except` in `_publish_session_end_event()` (line 1920), so it will not block shutdown. However, promotion evaluation silently fails entirely rather than gracefully skipping shadow-only comparisons. In practice, counterfactual is likely always enabled when experiments are enabled, but the code does not enforce this coupling.

**F2 (LOW): Dead code in live_variants update after promotion (lines 116-129)**
File: `argus/intelligence/experiments/promotion.py`, lines 116-129.
After a successful promotion, the code rebuilds `live_variants` via a list comprehension that replaces any variant matching `event.variant_id`. However, the promoted variant was a shadow variant (not in `live_variants`), so the comprehension is a no-op — no element in the list will match. The newly promoted variant is never actually added to `live_variants`. This is harmless (multiple shadows can each independently compare against the original live set, which aligns with the non-zero-sum spec constraint), but the code appears to intend something it does not accomplish.

**F3 (LOW): Hardcoded limit=1000 on shadow and trade queries**
File: `argus/intelligence/experiments/promotion.py`, lines 353, 378, 400.
All three query methods use `limit=1000`. A variant with more than 1000 shadow positions or trades would have metrics computed from a truncated dataset. This is unlikely in early operation but could matter as the system matures over months. No config option to adjust this limit.

**F4 (LOW): No test for counterfactual_store=None path**
File: `tests/intelligence/experiments/test_promotion.py`.
The 8 tests all provide functioning mock counterfactual stores. There is no test verifying behavior when `counterfactual_store` is `None` (the F1 path), nor a test for the `_trade_logger` returning empty results for a live variant being evaluated for demotion.

### Recommendation
CONCERNS verdict due to F1. The NoneType crash path is a real configuration scenario (experiments enabled, counterfactual disabled) where the promotion evaluator silently fails entirely. While the try/except prevents hard failures, the operator gets no indication that promotion evaluation was skipped — only a warning log buried in shutdown output. Recommend adding a None-guard in `_build_result_from_shadow()` (return None early if counterfactual_store is None) or validating that counterfactual is enabled before constructing the evaluator. This can be addressed in Session 8 or a follow-up.

F2 (dead code in live_variants update) and F3 (hardcoded limit) are minor and do not need immediate action.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "32",
  "session": "7",
  "verdict": "CONCERNS",
  "findings": [
    {
      "description": "_build_result_from_shadow() calls self._counterfactual_store.query() without None guard. If counterfactual subsystem is disabled, self._counterfactual_store is None and evaluate_all_variants() raises AttributeError. Caught by try/except in main.py but causes silent total failure of promotion evaluation.",
      "severity": "MEDIUM",
      "category": "ERROR_HANDLING",
      "file": "argus/intelligence/experiments/promotion.py",
      "recommendation": "Add early return None in _build_result_from_shadow() if self._counterfactual_store is None, or validate counterfactual.enabled before constructing PromotionEvaluator."
    },
    {
      "description": "live_variants list comprehension after promotion (lines 116-129) is a no-op: the promoted variant's ID belongs to a shadow variant not present in live_variants, so no element is ever replaced. The newly promoted variant is never added to the list.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/intelligence/experiments/promotion.py",
      "recommendation": "Either remove the dead comprehension or fix it to append the promoted variant to live_variants if that was the intent."
    },
    {
      "description": "Hardcoded limit=1000 on shadow position and trade queries. Variants with more than 1000 data points would have metrics computed from truncated data.",
      "severity": "LOW",
      "category": "OTHER",
      "file": "argus/intelligence/experiments/promotion.py",
      "recommendation": "Consider making the query limit configurable or documenting the 1000-record cap as a known limitation."
    },
    {
      "description": "No test covers the counterfactual_store=None path (F1 scenario).",
      "severity": "LOW",
      "category": "TEST_COVERAGE_GAP",
      "file": "tests/intelligence/experiments/test_promotion.py",
      "recommendation": "Add a test that passes None as counterfactual_store and verifies graceful handling."
    }
  ],
  "spec_conformance": {
    "status": "CONFORMANT",
    "notes": "All 10 spec requirements are implemented. The None-guard gap is an error-handling robustness issue, not a spec violation.",
    "spec_by_contradiction_violations": []
  },
  "files_reviewed": [
    "argus/intelligence/experiments/promotion.py",
    "tests/intelligence/experiments/test_promotion.py",
    "argus/main.py",
    "argus/intelligence/experiments/store.py",
    "argus/intelligence/counterfactual_store.py",
    "argus/analytics/comparison.py",
    "argus/analytics/evaluation.py"
  ],
  "files_not_modified_check": {
    "passed": true,
    "violations": []
  },
  "tests_verified": {
    "all_pass": true,
    "count": 4373,
    "new_tests_adequate": true,
    "test_quality_notes": "8 new tests cover promotion, demotion, hysteresis, persistence ordering, idempotency, and mode update. Missing: counterfactual_store=None edge case."
  },
  "regression_checklist": {
    "all_passed": true,
    "results": [
      {"check": "R6: Shadow mode routing", "passed": true, "notes": "Existing shadow tests pass"},
      {"check": "R7: CounterfactualTracker handles shadow signals", "passed": true, "notes": "No changes to counterfactual code"},
      {"check": "R8: Non-PatternModule strategies untouched", "passed": true, "notes": "git diff confirms zero changes to protected files"},
      {"check": "R9: Test suite passes", "passed": true, "notes": "4373 passed, 0 failed"},
      {"check": "R11: experiments disabled -> no promotion", "passed": true, "notes": "_promotion_evaluator only set inside experiments.enabled block"}
    ]
  },
  "escalation_triggers": [],
  "recommended_actions": [
    "Add None-guard in _build_result_from_shadow() for counterfactual_store=None",
    "Add test covering counterfactual_store=None scenario",
    "Fix or remove dead live_variants update comprehension (lines 116-129)"
  ]
}
```
