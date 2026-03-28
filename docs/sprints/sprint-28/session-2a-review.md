---BEGIN-REVIEW---

# Sprint 28, Session 2a — Tier 2 Review
**Weight Analyzer + Threshold Analyzer**
**Reviewed:** 2026-03-28
**Reviewer:** Tier 2 Automated Review

## Summary

Session 2a implemented `WeightAnalyzer` and `ThresholdAnalyzer` for the Learning Loop. Both modules are new files with no modifications to existing code. Implementation faithfully follows the sprint spec and all relevant amendments (A3, A4, A5, A7, A12, A15). 23 new tests pass, exceeding the 14-test minimum. No regressions detected.

## Per-Focus-Area Findings

### 1. Source Separation (Amendment 3)

**PASS.** Trade and counterfactual records are split at the top of `WeightAnalyzer.analyze()` (lines 61-62) and processed separately through `_correlate_source()`. The `_DimensionCorrelation` class tracks both sources independently. Source preference is correctly implemented: trade preferred when `sample_size >= min_sample_count`, counterfactual fallback with MODERATE confidence cap. Divergence > 0.3 flagged via `has_source_divergence()`.

`ThresholdAnalyzer.analyze()` correctly filters to counterfactual records only (line 61) per Amendment 3/12.

### 2. P-value Check (Amendment 4)

**PASS.** `effective_correlation()` requires `p_value < p_value_threshold` before returning a usable correlation at any confidence level (HIGH, MODERATE, or LOW). When p-value fails, the cascade falls through to `INSUFFICIENT_DATA`. The `correlation_p_value_threshold` config field (default 0.10) is correctly threaded through.

### 3. Weight Formula (Amendment 5)

**PASS.** The formula `max(0, rho_i) / sum(max(0, rho_j))` is implemented in `_build_recommendations()` (lines 254-258). Stub (zero-variance) dimensions are held at current weight. Non-stub allocation is correctly computed as `1.0 - stub_weight_sum`. Normalization after clamping ensures weights sum to 1.0. When all non-stub dimensions have negative or insignificant correlations, an empty list is returned (no recommendations generated), matching spec.

### 4. Threshold Decision Criteria (Amendment 12)

**PASS.** `_analyze_grade()` implements exactly the specified thresholds:
- `missed_opportunity_rate > 0.40` generates "lower" recommendation (line 116)
- `correct_rejection_rate < 0.50` generates "raise" recommendation (line 135)
- Both can fire simultaneously via separate `if` checks (not `elif`)

### 5. Zero-Variance Guards (Amendment 15)

**PASS.** Both dimension scores (`len(set(scores)) <= 1`, line 187) and P&L outcomes (`len(set(pnls)) <= 1`, line 196) are checked before calling `spearmanr`. Zero-variance results in `_SourceCorrelation(correlation=None, zero_variance=True)`, which cascades to `ConfidenceLevel.INSUFFICIENT_DATA` -- never NaN.

### 6. NaN/Inf Risk Assessment

**PASS.** `spearmanr` is only invoked after both zero-variance guards pass. The `float()` casts on `corr` and `p_value` (lines 206-207) safely convert numpy floats. No division-by-zero risk: `positive_sum` is checked `> 0.0` before division (line 284).

### 7. Regime Grouping (Amendment 7)

**PASS.** `analyze_by_regime()` groups by `record.regime_context.get("primary_regime")` only. Records without `primary_regime` are excluded. Per-regime minimum sample count enforced.

## Regression Checklist

| Check | Result |
|-------|--------|
| No existing files modified | PASS -- `git diff --name-only` empty |
| S1 tests still pass | PASS -- 31 S1 tests green within the 54 total |
| No S1 files modified (models.py, outcome_collector.py, __init__.py) | PASS |
| correlation_analyzer.py NOT created | PASS -- not present in directory listing |
| OutcomeCollector queries remain read-only | PASS -- not imported or modified |

## Minor Observations (Non-Blocking)

1. **Normalization after clamping can exceed max_change_per_cycle**: As noted in the close-out, clamping happens before normalization. After normalization, individual deltas may slightly exceed `max_change_per_cycle`. This is an intentional trade-off (sum-to-1.0 invariant takes priority) and is documented. Not a bug.

2. **`is_zero_variance()` uses AND logic**: Both trade AND counterfactual sources must be zero-variance for the dimension to be treated as stub. This is correct behavior -- if one source has variance, it can potentially produce a useful correlation.

3. **Counterfactual records may lack dimension_scores**: As noted in the close-out, `OutcomeCollector` currently returns empty `dimension_scores` for counterfactual records. This means `WeightAnalyzer` counterfactual correlations will effectively be empty until a future enhancement populates these scores. This is a known data limitation, not a code bug.

4. **`type: ignore[operator]` on line 269**: The `effective_corrs[d] <= 0.0` comparison has a `type: ignore[operator]` because `effective_corrs[d]` could be `None`. Python's short-circuit `or` on the preceding `is None` check makes this safe at runtime. Minor type-safety gap but correct behavior.

## Test Coverage Assessment

- **23 new tests** (14 weight analyzer + 9 threshold analyzer), exceeding the 14-test minimum
- **Weight analyzer coverage**: Positive correlation, zero-variance dimension, zero-variance P&L, p-value filtering, trade/counterfactual preference, counterfactual fallback with MODERATE cap, source divergence flagging, weights sum to 1.0, max_change_per_cycle clamping, empty inputs, regime grouping, insufficient regime samples, missing regime key
- **Threshold analyzer coverage**: High missed-opportunity rate, low correct-rejection rate, both conditions simultaneous, normal rates (no recommendation), empty records, no counterfactual records, insufficient samples, source separation (trade records ignored), multiple grades
- **All 54 learning tests pass** in 0.56s

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Mathematically impossible results (correlation outside [-1,1]) | No -- `spearmanr` produces bounded results; zero-variance guards prevent NaN |
| Config application causes scoring regression | N/A -- no config writing in this session |
| Auto trigger blocks/delays shutdown | N/A -- no auto trigger in this session |
| OutcomeCollector returns mismatched data | N/A -- OutcomeCollector not modified |

No escalation criteria triggered.

## Verdict

**CLEAR.** Implementation faithfully follows the spec and all relevant amendments. Source separation, p-value checks, weight formula, threshold criteria, and zero-variance guards are all correctly implemented. 23 tests pass, no regressions, no existing files modified.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "28",
  "session": "S2a",
  "verdict": "CLEAR",
  "summary": "WeightAnalyzer and ThresholdAnalyzer correctly implement all amendment requirements (A3, A4, A5, A7, A12, A15). Source separation, p-value checks, weight formula, threshold criteria, and zero-variance guards all verified. 23 new tests, all 54 learning tests pass. No existing files modified, no regressions.",
  "findings": [],
  "concerns": [
    "Normalization after clamping can cause individual deltas to slightly exceed max_change_per_cycle (documented, intentional trade-off)",
    "Counterfactual OutcomeRecords currently have empty dimension_scores, limiting counterfactual weight correlations until future enhancement"
  ],
  "escalation_triggers": [],
  "tests": {
    "total": 54,
    "new": 23,
    "passing": 54,
    "failing": 0
  },
  "files_reviewed": [
    "argus/intelligence/learning/weight_analyzer.py",
    "argus/intelligence/learning/threshold_analyzer.py",
    "tests/intelligence/learning/test_weight_analyzer.py",
    "tests/intelligence/learning/test_threshold_analyzer.py"
  ],
  "regression_check": "PASS"
}
```
