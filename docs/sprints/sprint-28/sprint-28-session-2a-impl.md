# Sprint 28, Session 2a: Weight Analyzer + Threshold Analyzer

**⚠️ PARALLELIZABLE with Session 2b.** If running simultaneously, ensure: S2a creates ONLY `weight_analyzer.py` and `threshold_analyzer.py`. S2b creates ONLY `correlation_analyzer.py`. No file overlap. Merge before Session 3a.

## Pre-Flight Checks
1. Read these files:
   - `argus/intelligence/learning/models.py` (S1 output — data models)
   - `argus/intelligence/learning/outcome_collector.py` (S1 output — data reader)
   - `argus/intelligence/filter_accuracy.py` (pattern reference for threshold analysis)
   - Session 1 close-out: `docs/sprints/sprint-28/session-1-closeout.md` (check quality_history schema finding)
   - `docs/sprints/sprint-28/sprint-28-adversarial-review-output.md` (Amendments 3, 4, 5, 7, 12, 15)
2. Run scoped test baseline:
   `python -m pytest tests/intelligence/learning/ -x -q`
   Expected: S1 tests all passing
3. Verify correct branch

## Objective
Build the Weight Analyzer (Spearman correlation between quality dimensions and P&L) and Threshold Analyzer (missed-opportunity and correct-rejection rates per grade) — the two analyzers that evaluate Quality Engine calibration.

## Requirements

1. **Create `argus/intelligence/learning/weight_analyzer.py`:**
   - `WeightAnalyzer` class
   - `analyze(records: list[OutcomeRecord], config: LearningLoopConfig, current_weights: dict[str, float]) -> list[WeightRecommendation]`:
     - **Separate by source (Amendment 3):** Split records by source ("trade" vs "counterfactual"). Compute correlations separately for each source.
     - For each quality dimension in current_weights:
       - Extract dimension scores from OutcomeRecord.dimension_scores dict
       - If dimension has zero variance (e.g., historical_match stubbed at 50), return INSUFFICIENT_DATA (Amendment 15: also check zero-variance P&L outcomes)
       - Compute Spearman rank correlation (scipy.stats.spearmanr) between dimension score and P&L
       - **P-value check (Amendment 4):** Only use for recommendation if p-value < `correlation_p_value_threshold`
       - **Source preference (Amendment 3):** Use trade-sourced correlation when trade sample count ≥ `min_sample_count`. Otherwise fall back to counterfactual-sourced with MODERATE confidence cap. Flag divergence > 0.3 between sources.
     - **Weight recommendation formula (Amendment 5):** For non-stub dimensions with significant correlations: recommended_weight_i = max(0, ρ_i) / Σ max(0, ρ_j), scaled to non-stub allocation. Zero-variance dimensions held at current weight. If all non-stub dimensions have non-significant or negative correlations → no recommendations generated.
     - Clamp deltas by `max_change_per_cycle`
     - Ensure recommended weights sum to 1.0
   - `analyze_by_regime(records, config, current_weights) -> dict[str, list[WeightRecommendation]]`:
     - **Regime grouping (Amendment 7):** Group by `primary_regime` from regime_context dict (5-value MarketRegime enum only)
     - Only analyze regimes with sample count ≥ `min_sample_per_regime`
     - Returns dict keyed by regime name

2. **Create `argus/intelligence/learning/threshold_analyzer.py`:**
   - `ThresholdAnalyzer` class
   - `analyze(records: list[OutcomeRecord], config: LearningLoopConfig, current_thresholds: dict[str, int]) -> list[ThresholdRecommendation]`:
     - **Source separation (Amendment 3/12):** Missed-opportunity and correct-rejection rates computed from counterfactual records only. Pass-through profitability from trade records only.
     - For each grade level (A+ through C+):
       - From counterfactual records at this grade: compute missed_opportunity_rate (fraction profitable) and correct_rejection_rate (fraction unprofitable)
       - **Decision criteria (Amendment 12):** Generate recommendation when: missed_opportunity_rate > 0.40 → "lower" (too aggressive), OR correct_rejection_rate < 0.50 → "raise" (too lenient)
       - Only when sample_size ≥ `min_sample_count`
     - Both conditions can be true simultaneously — generate both recommendations

## Constraints
- Do NOT modify any existing files
- Do NOT modify S1 files (models.py, outcome_collector.py)
- Do NOT create `correlation_analyzer.py` (that's S2b)
- Use `scipy.stats.spearmanr` for correlation (scipy already in ARGUS dependencies)

## Test Targets
- New tests in `tests/intelligence/learning/`:
  - `test_weight_analyzer.py`: per-dimension correlation, zero-variance dimension detection, zero-variance P&L guard, p-value filtering, source separation (trade vs counterfactual), source divergence flagging, weight formula normalization, max_change_per_cycle clamping, weights sum to 1.0, per-regime breakdown, insufficient regime samples
  - `test_threshold_analyzer.py`: per-grade rates from counterfactual, decision criteria (>0.40 missed → lower, <0.50 correct → raise), empty counterfactual, insufficient samples, both conditions simultaneous
- Minimum: 14 new tests
- Test command: `python -m pytest tests/intelligence/learning/ -x -q`

## Definition of Done
- [ ] WeightAnalyzer with source-separated correlations, p-value check, explicit formula
- [ ] ThresholdAnalyzer with decision criteria per Amendment 12
- [ ] Zero-variance guards on both dimensions and outcomes (Amendment 15)
- [ ] Regime breakdown by primary_regime only (Amendment 7)
- [ ] ≥14 new tests
- [ ] Close-out to `docs/sprints/sprint-28/session-2a-closeout.md`
- [ ] @reviewer with review context at `docs/sprints/sprint-28/review-context.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify source separation: trade correlations computed separately from counterfactual
2. Verify p-value check: correlations with p > threshold tagged INSUFFICIENT_DATA
3. Verify weight formula: recommended weights sum to 1.0, stub dimensions held constant
4. Verify threshold decision criteria match Amendment 12 (0.40 / 0.50 thresholds)
5. Verify zero-variance guards return INSUFFICIENT_DATA not NaN

## Sprint-Level Regression Checklist
*(See review-context.md)*

## Sprint-Level Escalation Criteria
*(See review-context.md)*
