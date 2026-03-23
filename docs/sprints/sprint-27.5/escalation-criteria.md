# Sprint 27.5: Escalation Criteria

These conditions trigger escalation to Tier 3 review or sprint suspension.

## Hard Stops (Suspend Sprint)

1. **BacktestEngine regression:** Any existing BacktestEngine test fails after S2 or S6 modifications. Root-cause before proceeding — these modifications must be purely additive.

2. **Circular import between analytics modules:** If `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, or `slippage_model.py` create a circular dependency with each other or with `backtest/engine.py`, stop and redesign the module boundaries. Circular imports in foundational infrastructure cascade into every downstream consumer.

3. **`BacktestResult` interface change required:** If implementing `to_multi_objective_result()` requires modifying the `BacktestResult` dataclass (adding fields, changing types), escalate. `BacktestResult` is consumed by `walk_forward.py`, `report_generator.py`, CLI tooling, and the revalidation script. Any change requires impact analysis across all consumers.

## Escalate to Tier 3 Review

4. **MultiObjectiveResult schema diverges from amendment:** If implementation reveals that the field set specified in DEC-357 §3.1 is insufficient — a downstream consumer (Sprint 28, 32.5, 33, 34) needs a field that was not anticipated — document the gap and escalate. Schema changes to the universal evaluation currency have cascading effects.

5. **ConfidenceTier thresholds prove miscalibrated:** If regime tagging of existing backtest data shows that the tier boundaries (50/30/10) don't distribute results across tiers in a useful way (e.g., everything lands in ENSEMBLE_ONLY because no strategy reaches 50 trades in 3+ regimes with the current 3-year data range), escalate for threshold recalibration.

6. **Regime tagging produces >80% single-regime concentration:** If regime tagging the existing Parquet data (EQUS.MINI 2023–2026) assigns >80% of trading days to a single regime, the regime-conditional evaluation provides minimal value. Escalate to assess whether Sprint 27.6 (Regime Intelligence) should be pulled forward.

7. **Ensemble metrics require trade-level data unavailable in BacktestResult:** If computing `diversification_ratio`, `tail_correlation`, or `marginal_contribution` requires per-trade timing data (entry/exit timestamps at sub-daily granularity) that `BacktestResult` does not provide, escalate. The workaround (aggregate at daily level) may be acceptable but needs explicit decision.

## Scope Creep Warnings

8. **Temptation to add API endpoints:** The comparison and ensemble evaluation functions are useful enough that someone might want to expose them via REST immediately. Resist — no consumers exist yet. Log as a DEF item if the need feels pressing.

9. **Temptation to add persistence:** `MultiObjectiveResult` and `EnsembleResult` serialize to JSON, which makes it tempting to add a SQLite storage layer. This is Sprint 32.5's job. The JSON schema stability is sufficient for now.

10. **Temptation to modify walk_forward.py:** Adding a `to_multi_objective_result()` bridge from `WalkForwardResult` is a natural extension but out of scope. The walk-forward module has its own metric conventions that differ subtly from BacktestEngine (per-window results vs aggregate). Log as DEF item.
