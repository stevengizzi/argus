# Sprint 27.5: Evaluation Framework

## Goal

Build the universal evaluation framework — `MultiObjectiveResult`, `EnsembleResult`, confidence tiers, Pareto comparison API, and slippage calibration — that becomes the shared currency for every downstream optimization and experiment sprint (Learning Loop, Statistical Validation, Systematic Search, Ensemble Orchestrator, Continuous Discovery). This sprint delivers pure backend infrastructure with no frontend and no new API endpoints.

## Scope

### Deliverables

1. **`MultiObjectiveResult` dataclass** (`argus/analytics/evaluation.py`) — structured evaluation output capturing primary metrics (Sharpe ratio, max drawdown %, profit factor, win rate, total trades, expectancy per trade), per-regime `RegimeMetrics` breakdown (string-keyed for forward-compatibility with Sprint 27.6 `RegimeVector`), `ConfidenceTier`, walk-forward efficiency, `execution_quality_adjustment`, and placeholder fields for future p-value/CI. Includes `parameter_hash` for deterministic config fingerprinting and `from_backtest_result()` factory method.

2. **`ConfidenceTier` enum + computation** (`argus/analytics/evaluation.py`) — four-tier classification (HIGH / MODERATE / LOW / ENSEMBLE_ONLY) computed from trade count and regime distribution, gating which comparison operations produce meaningful results.

3. **`RegimeMetrics` dataclass** (`argus/analytics/evaluation.py`) — per-regime metric container with the same shape as primary `MultiObjectiveResult` metrics (Sharpe, drawdown, profit factor, win rate, total trades, expectancy). Keys are strings matching `MarketRegime.value` today, `RegimeVector` dimension labels in Sprint 27.6+.

4. **Regime tagging in BacktestEngine** (`argus/backtest/engine.py`) — aggregate SPY 1-minute bars from the historical Parquet cache into daily bars, instantiate `RegimeClassifier`, assign a `MarketRegime` to each trading day, partition trades by regime, compute per-regime `RegimeMetrics`, and expose `to_multi_objective_result()` on `BacktestEngine`. Falls back to FMP `fetch_daily_bars()` if SPY is not in the Parquet cache.

5. **Individual comparison API** (`argus/analytics/comparison.py`) — `compare(a, b) → ComparisonVerdict` (DOMINATES / DOMINATED / INCOMPARABLE / INSUFFICIENT_DATA), `pareto_frontier(results) → list[MultiObjectiveResult]`, `soft_dominance(a, b, tolerance) → bool`, `is_regime_robust(result, min_regimes) → bool`, `format_comparison_report(a, b) → str`.

6. **Ensemble evaluation** (`argus/analytics/ensemble_evaluation.py`) — `EnsembleResult` (aggregate portfolio-level `MultiObjectiveResult` + diversification ratio, per-strategy `MarginalContribution`, tail correlation, max concurrent drawdown, capital utilization, turnover rate, `improvement_verdict`). Functions: `evaluate_cohort_addition()`, `marginal_contribution()`, `identify_deadweight()`, `format_ensemble_report()`.

7. **Slippage model calibration** (`argus/analytics/slippage_model.py`) — `StrategySlippageModel` dataclass, `calibrate_slippage_model()` querying the `execution_records` table, time-of-day and size adjustments, confidence assessment based on sample count.

8. **Integration wiring** — optional `slippage_model_path` parameter on `BacktestEngineConfig`, `execution_quality_adjustment` populated on `MultiObjectiveResult` output when slippage model is available, end-to-end integration tests covering BacktestEngine → `MultiObjectiveResult` → compare → ensemble evaluation round-trip.

### Acceptance Criteria

1. **MultiObjectiveResult:**
   - Constructs from all required fields with no optional fields missing
   - `from_backtest_result()` correctly maps every `BacktestResult` field to the corresponding `MultiObjectiveResult` field
   - `parameter_hash` is deterministic: same config dict → same hash regardless of key ordering
   - Serializes to JSON and deserializes back to identical object (round-trip)
   - `execution_quality_adjustment` defaults to `None`; `p_value` and `confidence_interval` default to `None`

2. **ConfidenceTier:**
   - `compute_confidence_tier(total_trades=50, regime_trade_counts={...3+ regimes with 15+...})` → `HIGH`
   - `compute_confidence_tier(total_trades=49, ...)` → `MODERATE`
   - `compute_confidence_tier(total_trades=30, regime_trade_counts={...2+ regimes with 10+...})` → `MODERATE`
   - `compute_confidence_tier(total_trades=29, ...)` → `LOW`
   - `compute_confidence_tier(total_trades=10, ...)` → `LOW`
   - `compute_confidence_tier(total_trades=9, ...)` → `ENSEMBLE_ONLY`
   - Tier is computed automatically from trade data, not manually set

3. **RegimeMetrics:**
   - Contains Sharpe, max drawdown %, profit factor, win rate, total trades, expectancy
   - Keyed by string (not `MarketRegime` enum) in `MultiObjectiveResult.regime_results`

4. **Regime tagging:**
   - Given a BacktestEngine run with SPY in the Parquet cache, each trading day is tagged with the correct `MarketRegime`
   - Per-regime `RegimeMetrics` are computed from trades occurring on days with that regime
   - `to_multi_objective_result()` produces a valid `MultiObjectiveResult` with populated `regime_results`
   - When SPY is not in the Parquet cache, falls back to FMP or produces a single `RANGE_BOUND` regime with a logged warning

5. **Comparison API:**
   - `compare(a, b)` returns `DOMINATES` when A is strictly better on all metrics
   - `compare(a, b)` returns `DOMINATED` when B is strictly better on all metrics
   - `compare(a, b)` returns `INCOMPARABLE` when A is better on some, B on others
   - `compare(a, b)` returns `INSUFFICIENT_DATA` when either is `ENSEMBLE_ONLY`
   - `pareto_frontier()` returns the correct non-dominated set for known test data (filters to HIGH/MODERATE only)
   - `soft_dominance(a, b, tolerance)` returns True when A improves at least one metric beyond tolerance without degrading any metric beyond tolerance
   - `is_regime_robust(result, min_regimes=3)` returns False when positive expectancy exists in fewer than 3 regimes

6. **Ensemble evaluation:**
   - `EnsembleResult` constructs with valid aggregate metrics and non-empty `marginal_contributions`
   - `evaluate_cohort_addition()` detects improvement (candidate ensemble Pareto-dominates baseline)
   - `evaluate_cohort_addition()` detects degradation (baseline dominates candidate)
   - `identify_deadweight()` returns strategies with marginal Sharpe below threshold
   - `marginal_contribution()` returns negative values for strategies that hurt the ensemble
   - `diversification_ratio` > 1.0 when strategies are uncorrelated, ≤ 1.0 when concentrated

7. **Slippage model:**
   - `calibrate_slippage_model()` produces valid statistics from ≥5 execution records
   - Returns model flagged as low confidence with <5 records
   - Time-of-day adjustment varies across morning/afternoon windows
   - Size adjustment produces non-negative slope

8. **Integration:**
   - Full round-trip test: BacktestEngine run → `to_multi_objective_result()` → `compare()` two results → `evaluate_cohort_addition()` → correct `improvement_verdict`
   - Slippage model loads from `slippage_model_path` when configured
   - `execution_quality_adjustment` is populated when slippage model available and strategy has sufficient records
   - All new modules import with no circular dependencies

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| `pareto_frontier()` on 1,000 results | < 2 seconds | Unit test with synthetic data |
| `evaluate_cohort_addition()` with 50 strategies | < 500ms | Unit test with synthetic data |
| `calibrate_slippage_model()` with 10,000 records | < 1 second | Unit test with synthetic records |
| JSON serialization round-trip for `MultiObjectiveResult` | < 10ms | Unit test |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| (CLI/constructor only) | `BacktestEngineConfig` | `slippage_model_path` | `None` |

No new YAML config files. The `slippage_model_path` is an optional constructor parameter, not exposed in system YAML since BacktestEngine is invoked via CLI or programmatically.

## Dependencies

- Sprint 27 (BacktestEngine Core) ✅ — `BacktestEngine`, `BacktestResult`, `BacktestEngineConfig`, `HistoricalDataFeed`
- Sprint 21.6 (Execution Logging) ✅ — `execution_records` table, `ExecutionRecord` model
- `RegimeClassifier` in `argus/core/regime.py` — existing, unchanged
- Historical Parquet cache with SPY data — existing (`data/historical/1m/`)
- No new external dependencies or Python packages

## Relevant Decisions

- DEC-047: Walk-forward validation mandatory, WFE > 0.3 — `MultiObjectiveResult.wfe` field preserves this
- DEC-054: Fixed slippage model in backtest — this sprint adds optional calibrated slippage alongside, not replacing
- DEC-132: Pre-Databento backtests provisional, re-validation required — `MultiObjectiveResult` standardizes what "validated" means
- DEC-357: Experiment Infrastructure amendment adopted — defines Sprint 27.5 scope (§3: Evaluation Framework)
- DEC-358: Intelligence Architecture amendment adopted — adds `execution_quality_adjustment` field requirement (§5.2) and forward-compatibility with RegimeVector (§3)
- DEC-359: BacktestEngine risk overrides — `to_multi_objective_result()` works with both default and overridden risk configs

## Relevant Risks

- RSK-022 (IBKR Gateway nightly resets) — not directly relevant; slippage calibration uses historical records, not live connection
- No new risks introduced. This sprint is pure computation with no external dependencies, no state machines, and no concurrency.

## Session Count Estimate

6 sessions estimated. Pure backend infrastructure: 4 new files (each ~150–250 lines), 2 files modified (additive changes only). No frontend, no external APIs, no WebSocket work. Parallel execution possible for S3+S5 after S1 completes.
