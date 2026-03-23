# Sprint 27.5: Session Breakdown

## Dependency Chain

```
S1 (Core Data Models)
├── S2 (Regime Tagging — depends on S1)
├── S3 (Comparison API — depends on S1, parallel-capable with S2)
└── S5 (Slippage Model — depends on S1 only for types, parallel-capable with S2/S3)
         │
S4 (Ensemble Evaluation — depends on S1 + S3)
         │
S6 (Integration Wiring — depends on all)
```

**Parallel opportunity:** After S1 completes, S2, S3, and S5 can execute in any order. S3 and S5 have zero file overlap with S2. In human-in-the-loop mode this is informational — execute sequentially S1→S2→S3→S4→S5→S6, or reorder S3/S5 before S2 if desired.

---

## Session 1: Core Data Models

**Objective:** Create the foundational data models that every other session and every downstream sprint depends on.

**Creates:**
- `argus/analytics/evaluation.py` — `MultiObjectiveResult`, `RegimeMetrics`, `ConfidenceTier` enum, `ComparisonVerdict` enum, `compute_confidence_tier()`, `parameter_hash()`, `from_backtest_result()` factory, JSON serialization (`to_dict()` / `from_dict()`)

**Modifies:** —

**Integrates:** N/A (foundational)

**Parallelizable:** false

**Compaction Risk Score: 12**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (evaluation.py) | 2 |
| Files modified | 0 | 0 |
| Pre-flight context reads | 2 (backtest/metrics.py for BacktestResult fields, core/regime.py for MarketRegime enum) | 2 |
| New tests | ~12 | 6 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 1 (evaluation.py ~250 lines) | 2 |
| **Total** | | **12** |

**Test estimate:** ~12 tests
- MultiObjectiveResult construction with all fields
- `from_backtest_result()` mapping correctness (every BacktestResult field maps to correct MOR field)
- `parameter_hash` determinism (same dict → same hash, different key order → same hash)
- JSON serialization round-trip (`to_dict()` → `from_dict()` → identical object)
- RegimeMetrics construction
- ConfidenceTier boundary tests: 50→HIGH, 49→MODERATE, 30→MODERATE, 29→LOW, 10→LOW, 9→ENSEMBLE_ONLY
- ConfidenceTier with insufficient regime coverage (50 trades but only 1 regime → downgrades)
- ComparisonVerdict enum values
- Edge: zero trades → ENSEMBLE_ONLY tier, zeroed metrics
- Edge: NaN detection in metrics fields

---

## Session 2: Regime Tagging in BacktestEngine

**Objective:** Make BacktestEngine produce regime-tagged results so every evaluation includes per-regime breakdown.

**Creates:** —

**Modifies:**
- `argus/backtest/engine.py` — add SPY daily bar aggregation from Parquet cache, RegimeClassifier instantiation, per-day regime tagging, trade-to-regime partitioning, `to_multi_objective_result()` method
- `argus/backtest/config.py` — no structural changes needed in this session (slippage_model_path added in S6)

**Integrates:** S1 (`evaluation.py` — imports `MultiObjectiveResult`, `RegimeMetrics`, `compute_confidence_tier()`)

**Parallelizable:** false (depends on S1)

**Compaction Risk Score: 13**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 (engine.py, config.py) | 2 |
| Pre-flight context reads | 3 (core/regime.py, analytics/evaluation.py, backtest/historical_data_feed.py) | 3 |
| New tests | ~10 | 5 |
| Complex integration wiring (RegimeClassifier + HistoricalDataFeed + BacktestEngine + evaluation.py) | 1 | 3 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **13** |

**Test estimate:** ~10 tests
- SPY 1-minute bars → daily OHLCV aggregation correctness
- RegimeClassifier receives correct daily bars and produces expected regimes for known test data
- Trade partitioning: trades on a BULLISH_TRENDING day appear in the correct regime bucket
- `to_multi_objective_result()` produces valid MOR with populated regime_results
- `to_multi_objective_result()` correctly maps BacktestResult fields + adds regime data
- ConfidenceTier computed from actual regime-tagged trade distribution
- Fallback: SPY not in Parquet cache → logs warning, assigns RANGE_BOUND to all days
- Fallback: empty Parquet directory → same behavior
- Edge: backtest with zero trades → MOR with empty regime_results, ENSEMBLE_ONLY tier
- Edge: all trades on single day → single regime in results

**Implementation notes:**
- SPY daily bar aggregation: read SPY 1-min Parquet files for the backtest date range, resample to daily OHLCV using pandas groupby on date. Use the same Parquet directory as `HistoricalDataFeed`.
- Regime tagging happens after the backtest run completes, not during. The engine collects `(trade, exit_date)` pairs, then retroactively tags each trading day via RegimeClassifier.
- `to_multi_objective_result()` is a method on `BacktestEngine` (not on `BacktestResult`) because it needs access to the regime tagging data computed during the run.

---

## Session 3: Individual Comparison API

**Objective:** Build the comparison functions that Learning Loop and all downstream sprints use to evaluate whether changes are improvements.

**Creates:**
- `argus/analytics/comparison.py` — `compare()`, `pareto_frontier()`, `soft_dominance()`, `is_regime_robust()`, `format_comparison_report()`

**Modifies:** —

**Integrates:** S1 (`evaluation.py` — imports `MultiObjectiveResult`, `ConfidenceTier`, `ComparisonVerdict`)

**Parallelizable:** true
- Justification: Creates `comparison.py` (new file, no overlap with S2's `engine.py`). Only imports from `evaluation.py` (S1 output). S2 and S3 have zero modified-file overlap. Neither session reads the other's output.

**Compaction Risk Score: 12**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (comparison.py) | 2 |
| Files modified | 0 | 0 |
| Pre-flight context reads | 1 (analytics/evaluation.py) | 1 |
| New tests | ~15 | 7.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 1 (comparison.py ~200 lines) | 2 |
| **Total** | | **12.5** |

**Test estimate:** ~15 tests
- `compare()`: A dominates B (all metrics better)
- `compare()`: A dominated by B
- `compare()`: incomparable (A better on Sharpe, B better on drawdown)
- `compare()`: both ENSEMBLE_ONLY → INSUFFICIENT_DATA
- `compare()`: one ENSEMBLE_ONLY, one HIGH → INSUFFICIENT_DATA
- `compare()`: A equals B on all metrics → INCOMPARABLE (neither dominates)
- `compare()` with `inf` profit factor handling
- `pareto_frontier()`: known 5-element set → correct 2-element frontier
- `pareto_frontier()`: all identical → all returned (none dominated)
- `pareto_frontier()`: single element → returned as-is
- `pareto_frontier()`: filters out LOW and ENSEMBLE_ONLY
- `soft_dominance()`: A improves Sharpe beyond tolerance, doesn't degrade others → True
- `soft_dominance()`: A improves Sharpe but degrades drawdown beyond tolerance → False
- `is_regime_robust()`: positive expectancy in 4 regimes, min_regimes=3 → True
- `is_regime_robust()`: positive expectancy in 2 regimes, min_regimes=3 → False
- `format_comparison_report()`: produces readable string with metric-by-metric comparison

**Implementation notes:**
- `compare()` metric set: Sharpe ratio (higher better), max_drawdown_pct (less negative better), profit_factor (higher better), win_rate (higher better), expectancy_per_trade (higher better). A dominates B iff A is ≥ B on all metrics and strictly > on at least one.
- `soft_dominance()`: A soft-dominates B with tolerance dict `{metric: threshold}` iff A improves at least one metric by ≥ threshold AND A does not degrade any metric by > threshold.
- `pareto_frontier()` uses O(n²) pairwise comparison. Acceptable for current volumes (≤1,000). NSGA-II fast non-dominated sort deferred to Sprint 34 if needed.

---

## Session 4: Ensemble Evaluation

**Objective:** Build the first-class ensemble evaluation that enables cohort-based promotion and marginal contribution analysis.

**Creates:**
- `argus/analytics/ensemble_evaluation.py` — `EnsembleResult`, `MarginalContribution`, `evaluate_cohort_addition()`, `marginal_contribution()`, `identify_deadweight()`, `format_ensemble_report()`

**Modifies:** —

**Integrates:** S1 (`evaluation.py`) + S3 (`comparison.py` — uses `compare()` for `improvement_verdict`)

**Parallelizable:** false (depends on S3 for comparison logic)

**Compaction Risk Score: 12**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (ensemble_evaluation.py) | 2 |
| Files modified | 0 | 0 |
| Pre-flight context reads | 2 (analytics/evaluation.py, analytics/comparison.py) | 2 |
| New tests | ~12 | 6 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 1 (ensemble_evaluation.py ~250 lines) | 2 |
| **Total** | | **12** |

**Test estimate:** ~12 tests
- `EnsembleResult` construction with valid aggregate + marginal contributions
- `diversification_ratio` > 1.0 for uncorrelated strategies (synthetic test data)
- `diversification_ratio` ≤ 1.0 for perfectly correlated strategies
- `marginal_contribution()`: removing a good strategy decreases ensemble Sharpe → positive marginal
- `marginal_contribution()`: removing a bad strategy increases ensemble Sharpe → negative marginal
- `evaluate_cohort_addition()`: candidate ensemble dominates baseline → improvement detected
- `evaluate_cohort_addition()`: baseline dominates candidate → degradation detected
- `evaluate_cohort_addition()`: incomparable → verdict reflects this
- `identify_deadweight()`: strategies with marginal Sharpe below threshold returned
- `identify_deadweight()`: all positive → empty list
- Single-strategy ensemble: diversification_ratio=1.0, tail_correlation=1.0
- `format_ensemble_report()`: produces readable summary with marginal contributions

**Implementation notes:**
- Ensemble aggregate metrics: compute portfolio-level daily returns by summing strategy daily P&L weighted by allocation, then compute Sharpe/drawdown/etc. from portfolio returns. This is a batch computation from `list[MultiObjectiveResult]`, not a live stream.
- `evaluate_cohort_addition(baseline, candidates)`: construct aggregate MOR for `baseline` strategies, construct aggregate MOR for `baseline + candidates`, then `compare(candidate_aggregate, baseline_aggregate)` for verdict.
- `tail_correlation`: average pairwise correlation of daily returns on days when the ensemble return is negative (bottom 25%). This measures how strategies behave during drawdowns — the dangerous correlation that destroys diversification when you need it most.
- `MarginalContribution` per strategy: recompute ensemble metrics excluding that strategy, diff against full ensemble.

---

## Session 5: Slippage Model Calibration

**Objective:** Build the slippage model calibration utility that enables BacktestEngine to use real execution data instead of fixed assumptions.

**Creates:**
- `argus/analytics/slippage_model.py` — `StrategySlippageModel`, `calibrate_slippage_model()`, `load_slippage_model()`, `save_slippage_model()`

**Modifies:** —

**Integrates:** N/A (standalone utility; reads existing `execution_records` table via `DatabaseManager`)

**Parallelizable:** true
- Justification: Creates `slippage_model.py` (new file, no overlap with any other session's creates/modifies). Only reads existing `execution_record.py` module and `execution_records` DB table. No dependency on S2, S3, or S4. Can run any time after S1 (imports `evaluation.py` types only for type consistency, but could even be independent).

**Compaction Risk Score: 6**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 1 (slippage_model.py) | 2 |
| Files modified | 0 | 0 |
| Pre-flight context reads | 1 (execution/execution_record.py) | 1 |
| New tests | ~6 | 3 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files | 0 (slippage_model.py ~120 lines) | 0 |
| **Total** | | **6** |

**Test estimate:** ~6 tests
- `calibrate_slippage_model()` from known execution records → correct mean/std slippage
- Time-of-day adjustment: records clustered in morning vs afternoon → different adjustments
- Size adjustment: larger orders → higher slippage → positive slope
- Insufficient data: <5 records → model flagged as low confidence
- Zero-slippage records (paper trading) → model with 0.0 mean, no error
- JSON serialization round-trip: `save_slippage_model()` → `load_slippage_model()` → identical model

**Implementation notes:**
- `calibrate_slippage_model()` queries the `execution_records` table filtered by `strategy_id`. Groups by time-of-day buckets (pre-10:00, 10:00–14:00, post-14:00 ET) for time adjustment. Linear regression of `actual_slippage_bps` on `order_size_shares` for size adjustment slope.
- The model is a simple statistical summary, not a predictive model. It captures observed slippage patterns for BacktestEngine to use as a more realistic fill assumption.
- Persistence: JSON file at the path specified by `slippage_model_path`. Not in SQLite — this is a small, infrequently-updated calibration file.

---

## Session 6: Integration Wiring + End-to-End Tests

**Objective:** Wire the slippage model into BacktestEngine, populate `execution_quality_adjustment` on MultiObjectiveResult, and verify the full pipeline works end-to-end.

**Creates:** —

**Modifies:**
- `argus/backtest/engine.py` — add optional `slippage_model` loading in constructor, use calibrated slippage in `to_multi_objective_result()` to compute `execution_quality_adjustment`
- `argus/backtest/config.py` — add `slippage_model_path: str | None = None` field to `BacktestEngineConfig`

**Integrates:** S1–S5 (full pipeline — integration tests exercise every module)

**Parallelizable:** false (depends on all prior sessions)

**Compaction Risk Score: 14 (flagged)**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 2 (engine.py, config.py) | 2 |
| Pre-flight context reads | 4 (evaluation.py, comparison.py, ensemble_evaluation.py, slippage_model.py) | 4 |
| New tests | ~10 | 5 |
| Complex integration wiring (slippage model → engine + full pipeline verification) | 1 | 3 |
| External API debugging | 0 | 0 |
| Large files | 0 | 0 |
| **Total** | | **14** |

**Note on score:** 14 is at the "must split" threshold. Accepted because: (a) the engine.py modification is small (~20 lines — load model in constructor, apply in `to_multi_objective_result()`), (b) the config.py modification is a single field addition, (c) the bulk of the session is writing integration tests which are read-heavy but low-risk. The 4 context reads are necessary for test imports but don't indicate modification complexity. If compaction occurs during implementation, log the planning score (14) and the compaction point in the close-out report.

**Test estimate:** ~10 tests
- `BacktestEngineConfig` with `slippage_model_path=None` → backward-compatible, no model loaded
- `BacktestEngineConfig` with valid path → model loaded, stored on engine
- `to_multi_objective_result()` with slippage model → `execution_quality_adjustment` populated
- `to_multi_objective_result()` without slippage model → `execution_quality_adjustment` is None
- Full round-trip: BacktestEngine run → `to_multi_objective_result()` → valid MOR with regime data
- Compare two MORs from different BacktestEngine runs → correct ComparisonVerdict
- Build EnsembleResult from multiple MORs → valid aggregate + marginal contributions
- `evaluate_cohort_addition()` with MORs from actual BacktestEngine runs → correct improvement_verdict
- `format_comparison_report()` + `format_ensemble_report()` produce non-empty strings
- No circular imports: all 4 new analytics modules + modified engine/config import cleanly

**Implementation notes:**
- Engine constructor: `if config.slippage_model_path: self._slippage_model = load_slippage_model(config.slippage_model_path)` else `self._slippage_model = None`
- `to_multi_objective_result()`: if `self._slippage_model` exists and strategy has records, compute the expected Sharpe degradation from real vs model slippage and store as `execution_quality_adjustment`. This is a scalar: estimated Sharpe impact from using real slippage instead of fixed.
- Integration tests can use a small synthetic backtest (2–3 days, 1 strategy, known trades) rather than full historical runs. The goal is pipeline correctness, not performance validation.
