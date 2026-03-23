---BEGIN-REVIEW---

# Sprint 27.5 S4 — Tier 2 Review

**Verdict:** CONCERNS
**Date:** 2026-03-24

## Findings

### CONCERN-1: Diversification ratio docstring inverts the formula (LOW)

The `EnsembleResult` docstring (line 116-117) states:

> Portfolio vol / weighted sum of individual vols. >1.0 means diversification helps.

But the actual code at `_compute_diversification_ratio()` line 367 computes:

```python
return weighted_vol_sum / portfolio_vol
```

This is the **inverse** of what the docstring claims. The code is correct -- in portfolio theory, the diversification ratio is weighted_vol_sum / portfolio_vol, which is >= 1.0 when diversification reduces risk. The docstring has the numerator and denominator swapped. The `_compute_diversification_ratio()` function's own docstring (lines 328-330) also describes it ambiguously. The spec itself uses the same inverted wording, so this is a spec-level inconsistency carried into the docstring.

**Impact:** Documentation-only. The code behavior is correct; tests pass with the correct semantics.

### CONCERN-2: Tail correlation approximation does not use "bottom 25%" (LOW)

The spec requires: "tail_correlation uses bottom 25% of return days." The implementation (lines 370-405) uses coefficient of variation of max drawdown magnitudes across strategies as a proxy for tail correlation, since daily return series are unavailable. The docstring accurately notes this is "approximated from drawdown correlation at metric level."

This is an acceptable metric-level approximation given the design constraints (no daily equity curves in MultiObjectiveResult). However, the approximation has a specific weakness: it measures similarity of drawdown severity across strategies, not whether drawdowns co-occur temporally. Two strategies could have identical max drawdown magnitudes occurring at completely different times, producing high "tail correlation" when actual tail correlation is zero.

**Impact:** The metric is directionally informative but can mislead. Documented appropriately in docstrings. Trade-level fix deferred to Sprint 32.5.

### CONCERN-3: `evaluate_cohort_addition` loses per-strategy granularity (LOW)

When `evaluate_cohort_addition()` is called, it cannot recover the original per-strategy MORs from the baseline `EnsembleResult` -- only the aggregate is available. The implementation treats the baseline aggregate as a single "strategy" combined with candidates (line 648). This means:

- Marginal contributions in the new ensemble reflect the baseline aggregate as one unit rather than individual strategies.
- `strategy_ids` is manually overridden (line 657) to list the original strategies, but the marginal contribution dict keys will not match those IDs (they will contain "ensemble" from the aggregate).

The close-out report documents this limitation and defers to Sprint 32.5. This is acceptable for Sprint 27.5 scope.

**Impact:** Callers inspecting `marginal_contributions` on a cohort-addition result will see contributions for "ensemble" + candidate IDs, not the original per-strategy breakdown. Not a runtime error but could confuse downstream consumers.

## Session-Specific Focus Items

1. **Metric-level approximation documented:** YES. Module docstring (lines 7-13), `build_ensemble_result` docstring (lines 565-567), and `EnsembleResult` class docstring (lines 105-108) all document this clearly.

2. **Diversification ratio formula:** Code is correct (`weighted_vol_sum / portfolio_vol`). Docstring describes the inverse -- see CONCERN-1.

3. **Tail correlation bottom 25%:** Approximated from drawdown CV, not from actual bottom 25% of return days. Acceptable given design constraints. Documented as approximation -- see CONCERN-2.

4. **Marginal contribution exact removal:** YES. `_compute_marginal_contributions()` (lines 481-552) removes exactly one strategy via list slicing (`results[:i] + results[i+1:]`) and recomputes the full aggregate. This is exact, not an approximation.

5. **`identify_deadweight` threshold configurable, defaults to 0.0:** YES. Parameter `threshold: float = 0.0` at line 689. Implementation at line 707: `mc.marginal_sharpe < threshold`.

6. **`evaluate_cohort_addition` sets `improvement_verdict` from `compare()`:** YES. Line 661: `new_ensemble.improvement_verdict = compare(new_ensemble.aggregate, baseline.aggregate)`.

7. **Single-strategy edge case:** YES. `_compute_diversification_ratio` returns 1.0 for n<=1 (line 344). `_compute_tail_correlation` returns 1.0 for n<=1 (line 387). `_compute_marginal_contributions` handles n==1 with marginal_sharpe = full Sharpe and correlation = 1.0 (lines 503-513). Test `test_build_ensemble_single_strategy` validates this.

## Sprint-Level Regression

- [x] Full pytest suite passes: 3,153 passed. 6 failures are xdist race conditions in `test_databento_data_service.py` (pass sequentially, confirmed pre-existing pattern).
- [x] No existing file modifications: `git diff --name-only HEAD` shows only the pre-existing deleted `amendment-doc-sync.patch`. New files are untracked only.
- [x] No circular imports: `python -c "from argus.analytics.ensemble_evaluation import EnsembleResult"` succeeds.
- [x] comparison.py not modified: zero diff confirmed.
- [x] evaluation.py not modified: zero diff confirmed.
- [x] No imports from `argus.backtest` in ensemble_evaluation.py.

## Escalation Criteria Check

**"Ensemble metrics require trade-level data unavailable from MultiObjectiveResult":** NOT TRIGGERED. All ensemble metrics are computed from metric-level data available in MultiObjectiveResult. The approximations are documented and do not require trade-level data. The design explicitly defers trade-level computation to Sprint 32.5.

## Verdict Rationale

CONCERNS, not CLEAR, due to three documentation/design issues:

1. The diversification ratio docstring states the formula inversely from what the code computes. While the code is correct, this will confuse anyone reading the docstring without examining the implementation.
2. The tail correlation approximation has a known weakness (measures drawdown magnitude similarity, not temporal co-occurrence) that is worth noting beyond the generic "metric-level approximation" label.
3. The cohort addition function produces marginal contribution keys that do not match the `strategy_ids` list, which could confuse downstream consumers.

None of these are blocking -- the implementation is functionally correct, well-tested (22 tests, all passing), and properly scoped. All three issues are documentable and fixable in future sessions.

## Post-Review Resolution

**Updated Verdict: CONCERNS_RESOLVED**

CONCERN-1 and CONCERN-2 fixed in the same session:
- CONCERN-1: Diversification ratio docstrings corrected to match code (`weighted_vol_sum / portfolio_vol`).
- CONCERN-2: Tail correlation docstrings updated with explicit temporal co-occurrence limitation note.
- CONCERN-3: Accepted as known limitation. Documented in close-out, deferred to Sprint 32.5.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.5",
  "session": "S4",
  "verdict": "CONCERNS",
  "findings": [
    {
      "id": "CONCERN-1",
      "severity": "LOW",
      "category": "documentation",
      "description": "Diversification ratio docstring inverts the formula (says portfolio_vol/weighted_sum but code computes weighted_sum/portfolio_vol)",
      "file": "argus/analytics/ensemble_evaluation.py",
      "line": 117,
      "recommendation": "Fix docstring to match code: weighted sum of individual vols / portfolio vol"
    },
    {
      "id": "CONCERN-2",
      "severity": "LOW",
      "category": "design",
      "description": "Tail correlation approximation uses drawdown magnitude CV, not temporal co-occurrence. Can report high tail corr for strategies with similar but temporally independent drawdowns.",
      "file": "argus/analytics/ensemble_evaluation.py",
      "line": 370,
      "recommendation": "Add explicit docstring note about temporal co-occurrence limitation. Resolve with trade-level data in Sprint 32.5."
    },
    {
      "id": "CONCERN-3",
      "severity": "LOW",
      "category": "design",
      "description": "evaluate_cohort_addition produces marginal_contributions keyed by 'ensemble' + candidate IDs, not matching the overridden strategy_ids list",
      "file": "argus/analytics/ensemble_evaluation.py",
      "line": 648,
      "recommendation": "Document this key mismatch explicitly or accept original MOR list as parameter in Sprint 32.5"
    }
  ],
  "tests": {
    "scoped_pass": 22,
    "scoped_fail": 0,
    "full_suite_pass": 3153,
    "full_suite_fail": 6,
    "full_suite_fail_preexisting": true
  },
  "regression": {
    "existing_files_modified": false,
    "circular_imports": false,
    "protected_files_clean": true
  },
  "escalation_triggered": false,
  "escalation_reason": null
}
```
