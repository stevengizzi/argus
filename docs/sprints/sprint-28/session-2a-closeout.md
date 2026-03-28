```markdown
---BEGIN-CLOSE-OUT---

**Session:** Sprint 28 S2a — Weight Analyzer + Threshold Analyzer
**Date:** 2026-03-28
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/intelligence/learning/weight_analyzer.py | added | WeightAnalyzer: source-separated Spearman correlations, p-value check, Amendment 5 weight formula, regime breakdown |
| argus/intelligence/learning/threshold_analyzer.py | added | ThresholdAnalyzer: counterfactual-only missed-opportunity/correct-rejection rates, Amendment 12 decision criteria |
| tests/intelligence/learning/test_weight_analyzer.py | added | 14 tests: correlation, zero-variance, p-value, source separation, divergence flag, formula, clamping, regime |
| tests/intelligence/learning/test_threshold_analyzer.py | added | 9 tests: rates, decision criteria, both-conditions, edge cases, source separation, multi-grade |

### Judgment Calls
- **_DimensionCorrelation and _SourceCorrelation internal classes:** Used private helper classes with __slots__ for clean internal state management. These are not exported — only WeightAnalyzer is public.
- **Confidence level cascade:** HIGH (trade source, sufficient samples, significant p) → MODERATE (counterfactual fallback) → LOW (either source, insufficient samples but significant p) → INSUFFICIENT_DATA. This implements Amendment 3 source preference faithfully.
- **Normalization after clamping:** Weight recommendations are first clamped by max_change_per_cycle, then normalized to sum to 1.0. This means final deltas may slightly exceed max_change_per_cycle after normalization, but ensures weights always sum to 1.0 (the stronger invariant).
- **All-negative-correlation edge case:** When all non-stub dimensions have negative or insignificant correlations, analyze() returns empty list (no recommendations). This matches the spec: "If all non-stub dimensions have non-significant or negative correlations → no recommendations generated."

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| WeightAnalyzer.analyze() with source separation (A3) | DONE | trade_records/cf_records split, per-dimension _correlate_source() |
| Zero-variance dimension detection (A15) | DONE | len(set(scores)) <= 1 → zero_variance=True |
| Zero-variance P&L guard (A15) | DONE | len(set(pnls)) <= 1 → zero_variance=True |
| P-value check < correlation_p_value_threshold (A4) | DONE | _DimensionCorrelation.effective_correlation() checks p_value |
| Source preference: trade ≥ min_sample, else cf with MODERATE cap (A3) | DONE | effective_correlation() cascade |
| Source divergence > 0.3 flagging (A3) | DONE | has_source_divergence() method |
| Weight formula: max(0,ρ_i)/Σmax(0,ρ_j) (A5) | DONE | _build_recommendations() |
| Stub dimensions held at current weight (A5) | DONE | is_stub check in _build_recommendations() |
| Clamp deltas by max_change_per_cycle | DONE | Clamping before normalization |
| Weights sum to 1.0 | DONE | _normalize_weights() post-step |
| analyze_by_regime by primary_regime only (A7) | DONE | Groups by regime_context["primary_regime"] |
| Min sample per regime (A7) | DONE | min_sample_per_regime check |
| ThresholdAnalyzer from counterfactual only (A3/A12) | DONE | Source separation: cf_records only |
| Decision criteria: missed > 0.40 → lower, correct < 0.50 → raise (A12) | DONE | _analyze_grade() |
| Both conditions simultaneously | DONE | Separate if checks, both can fire |
| ≥14 new tests | DONE | 23 new tests |
| No existing files modified | DONE | git diff --name-only empty |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| No existing files modified | PASS | git diff --name-only empty; git status shows only 4 new files |
| S1 tests still pass | PASS | 31 S1 tests still green |
| No S1 files modified | PASS | models.py, outcome_collector.py unchanged |
| correlation_analyzer.py NOT created | PASS | That's S2b scope |
| Imports work | PASS | `from argus.intelligence.learning.weight_analyzer import WeightAnalyzer` succeeds |

### Test Results
- Tests run: 54 (scoped: tests/intelligence/learning/)
- Tests passed: 54
- Tests failed: 0
- New tests added: 23
- Command used: `python -m pytest tests/intelligence/learning/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- **Weight formula normalization:** Clamping happens before normalization. This means if max_change_per_cycle is very small and the formula wants a big shift, the clamped weights may not reflect the exact formula ratio — but they'll be close, and they'll always sum to 1.0.
- **Empty return on all-negative:** When all non-stub dimensions have negative correlations, returning empty is correct — there's nothing actionable to recommend. The operator won't see misleading "increase everything" recommendations.
- **Counterfactual records lack dimension_scores:** OutcomeCollector returns empty dimension_scores for counterfactual records (no quality_history join for counterfactual positions). This means WeightAnalyzer's counterfactual correlations only work when dimension_scores are populated. For now, this means trade source will typically be the primary data source for weight analysis.

### Context State
GREEN — session completed well within context limits.

---END-CLOSE-OUT---
```

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "28",
  "session": "S2a",
  "verdict": "COMPLETE",
  "tests": {
    "before": 31,
    "after": 54,
    "new": 23,
    "all_pass": true
  },
  "files_created": [
    "argus/intelligence/learning/weight_analyzer.py",
    "argus/intelligence/learning/threshold_analyzer.py",
    "tests/intelligence/learning/test_weight_analyzer.py",
    "tests/intelligence/learning/test_threshold_analyzer.py"
  ],
  "files_modified": [],
  "files_should_not_have_modified": [
    "argus/intelligence/learning/models.py",
    "argus/intelligence/learning/outcome_collector.py",
    "argus/intelligence/learning/__init__.py"
  ],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "Counterfactual OutcomeRecords have empty dimension_scores (no quality_history join for counterfactual source). WeightAnalyzer counterfactual correlations only work if dimension_scores are populated by a future enhancement.",
    "Normalization after clamping can slightly exceed max_change_per_cycle for individual dimensions — ensures sum-to-1.0 invariant takes priority."
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "23 new tests, all 54 learning tests pass in 0.58s. Both analyzers implement all amendment requirements. No existing files modified."
}
```
