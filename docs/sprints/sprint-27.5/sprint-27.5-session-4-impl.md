# Sprint 27.5, Session 4: Ensemble Evaluation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/analytics/evaluation.py` (MultiObjectiveResult, RegimeMetrics, ConfidenceTier)
   - `argus/analytics/comparison.py` (compare(), ComparisonVerdict)
   - `docs/sprints/sprint-27.5/review-context.md`
2. Run scoped test baseline (DEC-328):
   ```bash
   python -m pytest tests/analytics/test_evaluation.py tests/analytics/test_comparison.py -x -q
   ```
   Expected: all passing
3. Verify S1 and S3 are committed

## Objective
Build ensemble-level evaluation — `EnsembleResult`, `MarginalContribution`, cohort addition simulation, deadweight identification — enabling cohort-based promotion and portfolio-level comparison in downstream sprints.

## Requirements

1. Create `argus/analytics/ensemble_evaluation.py` with:

   a. **`MarginalContribution` dataclass** (frozen):
      - `strategy_id: str`
      - `marginal_sharpe: float` — ensemble Sharpe WITH minus WITHOUT this strategy
      - `marginal_drawdown: float` — change in max drawdown (positive = less drawdown = better)
      - `correlation_to_ensemble: float` — correlation of this strategy's daily returns to the ensemble's
      - `trade_count: int`
      - `confidence_tier: ConfidenceTier`
      - `to_dict()` / `from_dict()`

   b. **`EnsembleResult` dataclass**:
      - Identity: `cohort_id: str`, `strategy_ids: list[str]`, `evaluation_date: datetime`, `data_range: tuple[date, date]`
      - Aggregate: `aggregate: MultiObjectiveResult` — portfolio-level metrics
      - Ensemble-specific:
        - `diversification_ratio: float` — portfolio vol / weighted sum of individual vols. >1.0 means diversification helps.
        - `marginal_contributions: dict[str, MarginalContribution]` — keyed by strategy_id
        - `tail_correlation: float` — avg pairwise correlation on bottom 25% return days
        - `max_concurrent_drawdown: float` — worst case when all strategies draw down together
        - `capital_utilization: float` — avg % of capital deployed (0.0–1.0)
        - `turnover_rate: float` — annual turnover
      - Comparison: `baseline_ensemble: EnsembleResult | None = None`
      - `improvement_verdict: ComparisonVerdict = ComparisonVerdict.INCOMPARABLE`
      - `to_dict()` / `from_dict()`

   c. **`build_ensemble_result(results: list[MultiObjectiveResult], cohort_id: str = "", capital: float = 100_000.0) → EnsembleResult`**:
      - Aggregate: combine daily equity curves (proportional allocation), compute portfolio-level MOR
      - Diversification ratio: portfolio daily return std / mean of individual daily return stds
      - Marginal contributions: for each strategy, recompute aggregate without it, diff Sharpe and drawdown
      - Tail correlation: average pairwise correlation of strategy returns on days where portfolio return is in bottom 25%
      - Max concurrent drawdown: sum of individual max drawdowns (worst case assumption)
      - Capital utilization and turnover: estimated from trade counts and average hold durations
      - Handle single-strategy: diversification_ratio=1.0, tail_correlation=1.0, marginal Sharpe = ensemble Sharpe

   d. **`evaluate_cohort_addition(baseline: EnsembleResult, candidates: list[MultiObjectiveResult]) → EnsembleResult`**:
      - Build a new ensemble from `baseline.strategy_ids` + `candidates`
      - Set `baseline_ensemble = baseline`
      - Set `improvement_verdict = compare(new_aggregate, baseline.aggregate)`
      - Return the new EnsembleResult with comparison data

   e. **`marginal_contribution(ensemble: EnsembleResult, strategy_id: str) → MarginalContribution`**:
      - Shortcut: return `ensemble.marginal_contributions[strategy_id]`
      - Raise `KeyError` if strategy not in ensemble

   f. **`identify_deadweight(ensemble: EnsembleResult, threshold: float = 0.0) → list[str]`**:
      - Return strategy_ids where `marginal_contributions[sid].marginal_sharpe < threshold`
      - Empty list if all positive

   g. **`format_ensemble_report(result: EnsembleResult) → str`**:
      - Header: cohort_id, strategy count, date range
      - Aggregate metrics summary
      - Ensemble health: diversification ratio, tail correlation, capital utilization
      - Marginal contributions table (sorted by marginal Sharpe desc)
      - Deadweight warning if any
      - Improvement verdict (if baseline present)

2. **Important design note on daily return aggregation:**
   - `MultiObjectiveResult` contains aggregate metrics but NOT daily equity curves
   - For ensemble computation, we need to simulate portfolio-level daily returns
   - Approach: use each strategy's `sharpe_ratio`, `max_drawdown_pct`, `total_trades`, and `expectancy_per_trade` to estimate contribution. This is an approximation — exact portfolio simulation requires trade-level data that comes from BacktestEngine directly.
   - For Sprint 27.5, the ensemble computation uses metric-level aggregation (not trade-level). Sprint 32.5 can wire in trade-level data from BacktestEngine for higher fidelity.
   - Diversification ratio approximation: use metric-based estimation. Flag in docstring that trade-level aggregation is a future enhancement.

3. Add `__all__` exports.

## Constraints
- Do NOT modify any existing files
- Do NOT import from `argus/backtest/` — ensemble evaluation works from MultiObjectiveResult, not BacktestResult
- Do NOT add persistence or database tables
- Acknowledge in docstrings that metric-level ensemble aggregation is an approximation; trade-level aggregation deferred

## Test Targets
New tests in `tests/analytics/test_ensemble_evaluation.py`:
1. `test_marginal_contribution_construction` — all fields present
2. `test_ensemble_result_construction` — valid aggregate + contributions
3. `test_build_ensemble_basic` — 3 MORs → valid EnsembleResult
4. `test_build_ensemble_single_strategy` — 1 MOR → diversification=1.0, tail_corr=1.0
5. `test_build_ensemble_diversification_ratio` — uncorrelated strategies → ratio > 1.0
6. `test_marginal_contribution_positive` — good strategy → positive marginal Sharpe
7. `test_marginal_contribution_negative` — bad strategy → negative marginal Sharpe
8. `test_evaluate_cohort_addition_improvement` — candidates improve ensemble → DOMINATES verdict
9. `test_evaluate_cohort_addition_degradation` — candidates hurt ensemble → DOMINATED verdict
10. `test_identify_deadweight_none` — all positive marginals → empty list
11. `test_identify_deadweight_found` — one negative marginal → returned
12. `test_ensemble_result_serialization_roundtrip` — to_dict → from_dict → identical
13. `test_format_ensemble_report_nonempty` — produces non-empty readable string
- Minimum new test count: 10
- Test command: `python -m pytest tests/analytics/test_ensemble_evaluation.py -x -v`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] New tests written and passing (≥10)
- [ ] `import argus.analytics.ensemble_evaluation` succeeds independently
- [ ] Close-out report written to `docs/sprints/sprint-27.5/session-4-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No existing file modifications | `git diff --name-only` shows only new files |
| No circular imports | `python -c "from argus.analytics.ensemble_evaluation import EnsembleResult"` |
| comparison.py not modified | `git diff argus/analytics/comparison.py` empty |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-27.5/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.5/review-context.md`
2. Close-out: `docs/sprints/sprint-27.5/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped): `python -m pytest tests/analytics/test_ensemble_evaluation.py -x -v`
5. Files NOT modified: all existing files, `argus/analytics/evaluation.py`, `argus/analytics/comparison.py`

Write review to: `docs/sprints/sprint-27.5/session-4-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the template
instructions (Post-Review Fixes section + CONCERNS_RESOLVED verdict).

## Session-Specific Review Focus (for @reviewer)
1. Verify ensemble aggregation approach is documented as metric-level approximation (not trade-level)
2. Verify `diversification_ratio` formula: portfolio vol / weighted individual vol sum
3. Verify `tail_correlation` uses bottom 25% of return days (not arbitrary threshold)
4. Verify `marginal_contribution` removes exactly one strategy and recomputes (not approximation)
5. Verify `identify_deadweight` threshold is configurable and defaults to 0.0
6. Verify `evaluate_cohort_addition` sets `improvement_verdict` from `compare()`
7. Verify single-strategy edge case produces valid results (not crash)

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Full pytest suite passes (≥3,071)
- [ ] No existing file modifications
- [ ] No circular imports

## Sprint-Level Escalation Criteria (for @reviewer)
**Escalate to Tier 3:** Ensemble metrics require trade-level data unavailable from MultiObjectiveResult.
