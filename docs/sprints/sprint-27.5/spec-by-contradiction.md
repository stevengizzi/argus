# Sprint 27.5: What This Sprint Does NOT Do

## Out of Scope

1. **Experiment tracking/registry:** No `ExperimentRegistry`, no `Experiment` model, no experiment persistence — deferred to Sprint 32.5. `MultiObjectiveResult` is designed to serialize to JSON for future registry storage, but this sprint does not build the storage layer.

2. **FDR correction or p-values:** `MultiObjectiveResult.p_value` and `confidence_interval` remain `None`. Sprint 33 (Statistical Validation) populates these fields. This sprint defines the fields and their types but does not implement any statistical significance testing.

3. **Frontend/UI work:** No new pages, components, panels, charts, or API endpoints. No Observatory integration, no Copilot context injection, no Performance page additions. Pure backend infrastructure.

4. **Automatic promotion or experiment decisions:** No `PromotionPipeline`, no `PromotionCohort`, no stage gates, no kill switches — all Sprint 32.5. The comparison API provides the tools for making decisions; it does not make decisions.

5. **Learning Loop integration:** Sprint 28 consumes `MultiObjectiveResult` and comparison API. This sprint builds the framework; it does not wire it into the Quality Engine weight optimization loop.

6. **RegimeVector (multi-dimensional regime):** Sprint 27.6 replaces `MarketRegime` enum with `RegimeVector`. This sprint uses the existing `MarketRegime` enum for regime tagging. Forward-compatibility is ensured by string-keyed `regime_results` dict — no enum dependency in the serialized format.

7. **Counterfactual tracking:** Sprint 27.7's `CounterfactualTracker` is entirely separate. No shadow position tracking, no filter accuracy metrics.

8. **REST API endpoints:** No `/api/v1/evaluation/*` or `/api/v1/comparison/*` endpoints. There are no consumers for these yet. API exposure comes when Research Console (Sprint 31) or Copilot context needs it.

9. **Walk-forward integration:** `walk_forward.py` is not modified. It continues to produce `WalkForwardResult`. A future sprint may add a `to_multi_objective_result()` bridge from `WalkForwardResult`, but that is not in scope here.

10. **Real-time ensemble monitoring:** No WebSocket feeds, no live ensemble health tracking, no rolling result computation. `EnsembleResult` is a batch computation, not a real-time stream.

## Edge Cases to Reject

1. **Cross-date-range comparison:** `compare(a, b)` where A and B cover completely different date ranges — proceed with comparison (metrics are comparable regardless of date range), but log an INFO-level note. Do NOT reject or return `INSUFFICIENT_DATA` for this case.

2. **Regime with zero trades:** If a regime is present in the tagging but no trades occurred during days with that regime, omit it from `regime_results` (do not include a zeroed-out `RegimeMetrics` entry). `is_regime_robust()` counts only regimes present in `regime_results`.

3. **Infinite profit factor:** When a strategy has no losing trades, `profit_factor` is `float('inf')`. Preserve this convention (matches existing `BacktestResult`). `compare()` handles `inf` values: `inf > any finite value` is True.

4. **NaN in metrics:** If any metric is NaN (e.g., from 0/0 in a degenerate case), treat the entire `MultiObjectiveResult` as `INSUFFICIENT_DATA` for comparison purposes. Do NOT propagate NaN through comparison logic.

5. **Single-strategy ensemble:** `EnsembleResult` with exactly 1 strategy — valid, but `diversification_ratio` is 1.0 (no diversification), `marginal_contributions` has one entry whose marginal Sharpe equals the ensemble Sharpe, and `tail_correlation` is 1.0. Do NOT reject or special-case.

6. **Slippage calibration with all-zero slippage records:** If all execution records show zero actual slippage — produce a model with `estimated_mean_slippage_bps = 0.0`. Do NOT flag as anomalous; paper trading with simulated fills legitimately produces zero slippage.

7. **Empty Parquet cache directory:** If the Parquet cache directory exists but contains no files — fall back to FMP for SPY daily bars. If FMP also unavailable, assign all days `RANGE_BOUND` regime with WARNING log.

## Scope Boundaries

- **Do NOT modify:** `argus/backtest/metrics.py`, `argus/backtest/walk_forward.py`, `argus/core/regime.py`, `argus/analytics/performance.py`, `argus/analytics/trade_logger.py`, any strategy file (`argus/strategies/*`), any frontend file (`argus/ui/*`), `argus/execution/order_manager.py`, `argus/execution/execution_record.py`, `argus/api/*`, `argus/ai/*`, `argus/intelligence/*`, `argus/core/events.py`
- **Do NOT optimize:** `pareto_frontier()` performance beyond the 1,000-result benchmark. O(n²) pairwise comparison is acceptable for Sprint 27.5 volumes. Algorithmic optimization (e.g., NSGA-II fast non-dominated sort) deferred to Sprint 34 when volumes reach 50,000+.
- **Do NOT refactor:** `BacktestResult` — it stays as-is. `MultiObjectiveResult` is a new parallel structure, not a replacement. The `from_backtest_result()` factory bridges old → new.
- **Do NOT add:** Database tables, SQLite schemas, or persistence for `MultiObjectiveResult` or `EnsembleResult`. These are in-memory data structures that serialize to JSON. Persistent storage comes in Sprint 32.5 (ExperimentRegistry).

## Interaction Boundaries

- This sprint does NOT change the behavior of: `BacktestEngine.run()` return type (still `BacktestResult`), `compute_metrics()` in `metrics.py`, `RegimeClassifier.classify()`, `walk_forward.py` outputs, any existing API endpoint
- This sprint does NOT affect: Live trading pipeline, paper trading pipeline, Data Service, Event Bus, strategy evaluation flow, Quality Engine, Catalyst Pipeline, Observatory, AI Copilot, Order Manager, Risk Manager

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| FDR correction / p-values | Sprint 33 (Statistical Validation) | — |
| Experiment Registry persistence | Sprint 32.5 (Experiment Registry) | — |
| RegimeVector multi-dimensional regime | Sprint 27.6 (Regime Intelligence) | — |
| Counterfactual tracking | Sprint 27.7 (Counterfactual Engine) | — |
| Learning Loop consumption | Sprint 28 (Learning Loop V1) | — |
| REST API endpoints for evaluation | Sprint 31 (Research Console) or later | — |
| Algorithmic Pareto frontier (NSGA-II) | Sprint 34 (Systematic Search) if needed | — |
| Real-time ensemble monitoring | Post-Sprint 32.5 | — |
| Walk-forward → MultiObjectiveResult bridge | Unscheduled | — |
