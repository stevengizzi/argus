# Sprint 27.5 — Review Context File

> This file contains the shared context for all Tier 2 reviews in Sprint 27.5.
> Each session review prompt references this file by path. Do not duplicate
> this content in individual review prompts.

---

## Sprint Spec

### Goal
Build the universal evaluation framework — `MultiObjectiveResult`, `EnsembleResult`, confidence tiers, Pareto comparison API, and slippage calibration — that becomes the shared currency for every downstream optimization and experiment sprint.

### Deliverables
1. `MultiObjectiveResult` dataclass with primary metrics, per-regime breakdown, confidence tier, WFE, execution quality adjustment, parameter hash, JSON serialization, factory from BacktestResult
2. `ConfidenceTier` enum (HIGH/MODERATE/LOW/ENSEMBLE_ONLY) with automatic computation from trade count + regime distribution
3. `RegimeMetrics` dataclass — per-regime metrics, string-keyed for forward-compat with Sprint 27.6
4. Regime tagging in BacktestEngine — SPY daily bars from Parquet cache, per-day regime assignment, `to_multi_objective_result()` method
5. Individual comparison API — `compare()`, `pareto_frontier()`, `soft_dominance()`, `is_regime_robust()`, `format_comparison_report()`
6. Ensemble evaluation — `EnsembleResult`, `MarginalContribution`, `evaluate_cohort_addition()`, `marginal_contribution()`, `identify_deadweight()`, `format_ensemble_report()`
7. Slippage model calibration — `StrategySlippageModel`, `calibrate_slippage_model()`, time-of-day/size adjustments
8. Integration wiring — optional `slippage_model_path` on BacktestEngineConfig, `execution_quality_adjustment` populated when model available, end-to-end tests

### Config Changes
| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| (CLI/constructor only) | `BacktestEngineConfig` | `slippage_model_path` | `None` |

### Comparison Metric Set
The five metrics used by `compare()` for Pareto dominance:
- Sharpe ratio (higher is better)
- max_drawdown_pct (less negative is better)
- profit_factor (higher is better)
- win_rate (higher is better)
- expectancy_per_trade (higher is better)

`total_trades` is NOT a comparison metric — it feeds ConfidenceTier, not Pareto dominance.

---

## Specification by Contradiction (Summary)

**Out of scope:** Experiment registry (32.5), FDR/p-values (33), frontend/UI, automatic promotion, Learning Loop integration (28), RegimeVector (27.6), counterfactual tracking (27.7), REST API endpoints, walk-forward.py modifications, real-time ensemble monitoring.

**Do NOT modify:** `backtest/metrics.py`, `backtest/walk_forward.py`, `core/regime.py`, `analytics/performance.py`, `analytics/trade_logger.py`, any strategy file, any frontend file, `execution/order_manager.py`, `execution/execution_record.py`, `api/*`, `ai/*`, `intelligence/*`, `core/events.py`

**Do NOT optimize:** Pareto frontier beyond O(n²) — acceptable for ≤1,000 results.

**Do NOT refactor:** `BacktestResult` — it stays as-is. `MultiObjectiveResult` is a new parallel structure.

**Do NOT add:** Database tables or SQLite schemas for MOR/EnsembleResult. These are in-memory + JSON serializable. Persistent storage comes in Sprint 32.5.

**Edge case handling:**
- Zero trades → ENSEMBLE_ONLY tier, zeroed metrics
- Regime with zero trades → omit from regime_results
- Infinite profit factor → preserve as `float('inf')`
- NaN in metrics → treat entire MOR as INSUFFICIENT_DATA for comparison
- Single-strategy ensemble → valid; diversification_ratio=1.0
- Cross-date-range comparison → proceed with INFO log

---

## Sprint-Level Regression Checklist

- [ ] Full pytest suite passes with `--ignore=tests/test_main.py` (≥3,071 pass, 0 fail)
- [ ] Full Vitest suite passes (≥620 pass, 0 fail)
- [ ] No new test hangs or timeouts
- [ ] Test count does not decrease from sprint entry baseline
- [ ] `BacktestEngine.run()` returns identical `BacktestResult` for same inputs
- [ ] Existing BacktestEngine tests pass without modification
- [ ] CLI entry point produces same output format
- [ ] `BacktestEngineConfig` with no `slippage_model_path` behaves identically
- [ ] `backtest/metrics.py` not modified (git diff)
- [ ] `backtest/walk_forward.py` not modified (git diff)
- [ ] `core/regime.py` not modified (git diff)
- [ ] `analytics/performance.py` not modified (git diff)
- [ ] No circular imports among new analytics modules
- [ ] Each new analytics module imports independently
- [ ] `BacktestEngineConfig` with existing YAML → no validation error
- [ ] Protected files have zero diff (list in regression-checklist.md)

---

## Sprint-Level Escalation Criteria

**Hard Stops:**
1. BacktestEngine test regression after S2 or S6 modifications
2. Circular import between analytics modules or with backtest/engine.py
3. BacktestResult interface change required

**Escalate to Tier 3:**
4. MultiObjectiveResult schema diverges from DEC-357 §3.1
5. ConfidenceTier thresholds miscalibrated (>80% ENSEMBLE_ONLY with real data)
6. Regime tagging produces >80% single-regime concentration
7. Ensemble metrics require unavailable trade-level data

**Scope Creep Warnings:**
8. Temptation to add API endpoints → log as DEF
9. Temptation to add persistence → Sprint 32.5
10. Temptation to modify walk_forward.py → log as DEF

---

## Session Dependency Chain

```
S1 (Core Data Models)
├── S2 (Regime Tagging)
├── S3 (Comparison API) — parallelizable with S2
└── S5 (Slippage Model) — parallelizable with S2/S3
         │
S4 (Ensemble Evaluation) — depends on S1 + S3
         │
S6 (Integration Wiring) — depends on all
```

## Files Created by This Sprint

| Session | File | Purpose |
|---------|------|---------|
| S1 | `argus/analytics/evaluation.py` | MultiObjectiveResult, RegimeMetrics, ConfidenceTier |
| S3 | `argus/analytics/comparison.py` | compare(), pareto_frontier(), soft_dominance() |
| S4 | `argus/analytics/ensemble_evaluation.py` | EnsembleResult, evaluate_cohort_addition() |
| S5 | `argus/analytics/slippage_model.py` | StrategySlippageModel, calibrate_slippage_model() |

## Files Modified by This Sprint

| Session | File | Change |
|---------|------|--------|
| S2 | `argus/backtest/engine.py` | Regime tagging, to_multi_objective_result() |
| S6 | `argus/backtest/engine.py` | Slippage model loading, execution_quality_adjustment |
| S6 | `argus/backtest/config.py` | slippage_model_path field |
