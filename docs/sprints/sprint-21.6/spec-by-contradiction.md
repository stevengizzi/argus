# Sprint 21.6: What This Sprint Does NOT Do

## Out of Scope

1. **Slippage model calibration (§5.2):** Building the `StrategySlippageModel` or calibration utility. Deferred to Sprint 27.5. Sprint 21.6 only collects raw execution records.
2. **MultiObjectiveResult format:** Sprint 27.5 defines the multi-objective evaluation framework. This sprint produces raw metrics in JSON/YAML — not structured evaluation objects.
3. **execution_quality_adjustment field:** Adding this to any result type. Sprint 27.5 scope.
4. **RegimeVector multi-dimensional classification:** Sprint 27.6 scope. This sprint only notes the forward-compatibility requirement.
5. **Full re-optimization:** This sprint runs fixed-parameter walk-forward (current params through OOS windows). It does NOT run VectorBT grid search to find new optimal parameters. Re-optimization only occurs if WFE < 0.3, and even then is documented as a remediation need, not executed in this sprint.
6. **Strategy logic changes:** No strategy `.py` files are modified. If parameters need adjustment, only YAML config values change.
7. **Frontend work:** Zero frontend changes. No new pages, components, or API endpoints for displaying validation results.
8. **New API endpoints:** No REST or WebSocket endpoints added. ExecutionRecord data is persisted to DB but not yet exposed via API (deferred to when a consumer needs it).
9. **BacktestEngine modifications:** The engine is used as-is from Sprint 27. No changes to fill model, component wiring, or orchestration.
10. **Walk-forward engine modifications:** The existing `run_fixed_params_walk_forward()` and `_validate_oos_backtest_engine()` are used as-is.
11. **Databento Plus upgrade or L2 data:** Standard plan only. No order book data.
12. **Automated parameter tuning pipeline:** No auto-update-and-rerun workflow. Parameter changes are manual and documented.

## Edge Cases to Reject

1. **Strategy produces zero trades with Databento data:** Log a WARNING in the validation results JSON (`"status": "ZERO_TRADES"`). Do not attempt automated parameter adjustment. Document in validation report for human review.
2. **WFE < 0.3 for a strategy:** Mark as `"status": "WFE_BELOW_THRESHOLD"` in results. Do not suspend the strategy or trigger re-optimization. Document with recommendation.
3. **Databento API rate limit or download failure:** The `HistoricalDataFeed` has built-in retry logic. If a download fails after retries, the script exits with a clear error message. Do not implement additional retry/resume logic in the harness.
4. **ExecutionRecord persistence failure during live trading:** Log at WARNING level and continue. The order fill must succeed regardless of whether the execution record was saved. Never retry the DB write — fire-and-forget.
5. **Missing baseline data in YAML** (e.g., `wfe_pnl: null`): Mark old value as "N/A" in the comparison. Still run the BacktestEngine validation and report new results.
6. **Databento cost check failure (`verify_zero_cost`):** Let BacktestEngine's existing cost verification handle this. The harness does not add additional cost guards.
7. **Symbol mismatch between Databento data and scanner simulation:** Use `scanner_fallback_all_symbols=True` (default). Do not add Databento-specific symbol mapping logic.

## Scope Boundaries

- **Do NOT modify:** Any strategy `.py` file (`argus/strategies/`), `engine.py`, `walk_forward.py`, `historical_data_feed.py`, `sync_event_bus.py`, any frontend file (`argus/ui/`), `events.py`, `risk_manager.py`
- **Do NOT optimize:** BacktestEngine performance, walk-forward execution speed, Parquet caching strategy
- **Do NOT refactor:** OrderManager's fill handling architecture, PendingManagedOrder lifecycle, walk-forward's strategy-specific OOS validation paths
- **Do NOT add:** API endpoints for execution records, UI components for validation results, automated CI/CD backtest pipelines, notification hooks for validation completion

## Interaction Boundaries

- This sprint does NOT change the behavior of: OrderManager order routing, Risk Manager gating, Event Bus dispatch, strategy signal generation, Orchestrator allocation, or any API endpoint
- This sprint does NOT affect: Frontend rendering, AI Copilot behavior, catalyst pipeline, Universe Manager routing, Observatory service
- ExecutionRecord logging is purely additive — zero behavioral change to the order execution path

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| StrategySlippageModel calibration utility | Sprint 27.5 | — (in-scope for 27.5) |
| execution_quality_adjustment field on results | Sprint 27.5 | — (in-scope for 27.5) |
| BacktestEngine calibrated slippage parameter | Sprint 27.5 | — (in-scope for 27.5) |
| API endpoint to query execution_records | Unscheduled | DEF-090 (if assigned) |
| Full re-optimization for strategies failing WFE threshold | Post-21.6 impromptu | — (decision depends on results) |
| PatternModule walk-forward optimization (Bull Flag, Flat-Top) | Post-21.6 or Sprint 28 | — (depends on 21.6 results) |
