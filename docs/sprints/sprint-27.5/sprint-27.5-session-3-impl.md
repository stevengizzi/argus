# Sprint 27.5, Session 3: Individual Comparison API

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/analytics/evaluation.py` (S1 output — MultiObjectiveResult, ConfidenceTier, ComparisonVerdict)
   - `docs/sprints/sprint-27.5/review-context.md` (comparison metric set defined there)
2. Run scoped test baseline (DEC-328):
   ```bash
   python -m pytest tests/analytics/test_evaluation.py -x -q
   ```
   Expected: all passing
3. Verify S1 is committed and `argus/analytics/evaluation.py` exists

## Objective
Build the individual comparison functions that Learning Loop and all downstream sprints use to evaluate whether changes are improvements: Pareto dominance, soft dominance, regime robustness, and human-readable formatting.

## Requirements

1. Create `argus/analytics/comparison.py` with:

   a. **`COMPARISON_METRICS`** — named constant tuple defining the 5 metrics and their directions:
      ```python
      COMPARISON_METRICS = (
          ("sharpe_ratio", "higher"),
          ("max_drawdown_pct", "higher"),      # Less negative = higher = better
          ("profit_factor", "higher"),
          ("win_rate", "higher"),
          ("expectancy_per_trade", "higher"),
      )
      ```

   b. **`compare(a: MultiObjectiveResult, b: MultiObjectiveResult) → ComparisonVerdict`**:
      - If either `a` or `b` has `confidence_tier == ENSEMBLE_ONLY` → `INSUFFICIENT_DATA`
      - Extract the 5 comparison metrics from both
      - Handle `float('inf')`: `inf > any finite value` is True, `inf == inf` is equal
      - Handle NaN: if any metric is NaN in either result → `INSUFFICIENT_DATA`
      - A dominates B: A ≥ B on all 5 metrics AND A > B on at least 1
      - B dominates A: B ≥ A on all 5 metrics AND B > A on at least 1
      - Otherwise: `INCOMPARABLE`

   c. **`pareto_frontier(results: list[MultiObjectiveResult]) → list[MultiObjectiveResult]`**:
      - Filter to HIGH and MODERATE confidence only (exclude LOW and ENSEMBLE_ONLY)
      - From filtered set, return the non-dominated subset
      - A result is non-dominated if no other result in the set dominates it
      - O(n²) pairwise comparison is acceptable
      - Empty input → empty output
      - Single element → returned as-is (if HIGH or MODERATE)

   d. **`soft_dominance(a: MultiObjectiveResult, b: MultiObjectiveResult, tolerance: dict[str, float] | None = None) → bool`**:
      - Default tolerance: `{"sharpe_ratio": 0.1, "max_drawdown_pct": 0.02, "profit_factor": 0.1, "win_rate": 0.02, "expectancy_per_trade": 0.05}`
      - A soft-dominates B if:
        1. A improves at least one metric by ≥ its tolerance (e.g., `a.sharpe_ratio - b.sharpe_ratio >= tolerance["sharpe_ratio"]`)
        2. A does NOT degrade any metric by > its tolerance (e.g., `b.profit_factor - a.profit_factor <= tolerance["profit_factor"]`)
      - Returns `False` if either has ENSEMBLE_ONLY confidence

   e. **`is_regime_robust(result: MultiObjectiveResult, min_regimes: int = 3) → bool`**:
      - Requires HIGH or MODERATE confidence (else False)
      - Count regimes in `result.regime_results` where `expectancy_per_trade > 0`
      - Return `count >= min_regimes`

   f. **`format_comparison_report(a: MultiObjectiveResult, b: MultiObjectiveResult) → str`**:
      - Header: strategy IDs, date ranges, confidence tiers
      - Metric-by-metric table: metric name, A value, B value, winner (A/B/tie)
      - Verdict line from `compare(a, b)`
      - Regime breakdown if both have regime data
      - Human-readable, suitable for CLI output and Copilot context injection

2. Add `__all__` exports.

3. Import only from `argus.analytics.evaluation` — no other internal imports needed.

## Constraints
- Do NOT modify any existing files
- Do NOT import from `argus/backtest/` (comparison is pure analytics, not backtest-dependent)
- Do NOT add API endpoints
- `total_trades` is NOT a comparison metric — it only feeds ConfidenceTier

## Test Targets
New tests in `tests/analytics/test_comparison.py`:
1. `test_compare_dominates` — A better on all 5 metrics → DOMINATES
2. `test_compare_dominated` — B better on all 5 → DOMINATED
3. `test_compare_incomparable` — A better on Sharpe, B better on drawdown → INCOMPARABLE
4. `test_compare_equal` — identical metrics → INCOMPARABLE (neither strictly better)
5. `test_compare_ensemble_only` — either ENSEMBLE_ONLY → INSUFFICIENT_DATA
6. `test_compare_nan_handling` — NaN in any metric → INSUFFICIENT_DATA
7. `test_compare_inf_profit_factor` — inf > finite is True
8. `test_pareto_frontier_basic` — 5 results, 2 non-dominated → frontier size 2
9. `test_pareto_frontier_all_identical` — all same metrics → all returned
10. `test_pareto_frontier_filters_low_confidence` — LOW/ENSEMBLE_ONLY excluded
11. `test_pareto_frontier_single` — one HIGH result → returned
12. `test_pareto_frontier_empty` — empty input → empty output
13. `test_soft_dominance_improves_one` — A improves Sharpe beyond tolerance, rest within → True
14. `test_soft_dominance_degrades_one` — A improves Sharpe but degrades drawdown beyond tolerance → False
15. `test_soft_dominance_custom_tolerance` — non-default tolerance values
16. `test_is_regime_robust_true` — 4 positive-expectancy regimes, min=3 → True
17. `test_is_regime_robust_false` — 2 positive, min=3 → False
18. `test_is_regime_robust_low_confidence` — LOW tier → False regardless of regimes
19. `test_format_comparison_report_nonempty` — produces non-empty string with all sections
- Minimum new test count: 15
- Test command: `python -m pytest tests/analytics/test_comparison.py -x -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥15)
- [ ] `import argus.analytics.comparison` succeeds independently
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-3-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing file modifications | `git diff --name-only` shows only new files |
| No circular imports | `python -c "from argus.analytics.comparison import compare"` succeeds |
| COMPARISON_METRICS has exactly 5 entries | Grep or inspect constant |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.5/review-context.md`
2. Close-out: `docs/sprints/sprint-27.5/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/analytics/test_comparison.py tests/analytics/test_evaluation.py -x -v`
5. Files NOT modified: all existing files

Write review to: `docs/sprints/sprint-27.5/session-3-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the template
instructions (Post-Review Fixes section + CONCERNS_RESOLVED verdict).

## Session-Specific Review Focus (for @reviewer)
1. Verify `compare()` correctly handles `float('inf')` — inf > finite, inf == inf
2. Verify `compare()` correctly handles NaN — returns INSUFFICIENT_DATA, not crashes
3. Verify `pareto_frontier()` filters out LOW and ENSEMBLE_ONLY before dominance check
4. Verify `soft_dominance()` checks BOTH improvement AND non-degradation (not just improvement)
5. Verify `is_regime_robust()` gates on confidence tier (LOW/ENSEMBLE_ONLY → always False)
6. Verify the 5 comparison metrics match the review context file's "Comparison Metric Set" section exactly
7. Verify `max_drawdown_pct` comparison direction: less negative = better (both values are negative, so -0.05 > -0.10)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (≥3,071)
- [ ] No existing file modifications
- [ ] No circular imports

## Sprint-Level Escalation Criteria (for @reviewer)
**Hard Stops:** Circular imports. **Scope Creep:** API endpoints, persistence.
