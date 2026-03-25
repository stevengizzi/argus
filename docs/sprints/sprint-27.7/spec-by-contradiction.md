# Sprint 27.7: What This Sprint Does NOT Do

## Out of Scope

1. **Automated filter adjustment based on counterfactual data:** The Counterfactual Engine provides data; the Learning Loop (Sprint 28) acts on it. This sprint does not modify quality weights, grade thresholds, or risk limits based on accuracy metrics.

2. **Strategy-level near-miss tracking:** Strategy condition failures (e.g., "failed on condition 6 of 8") happen before a SignalEvent is created. Capturing these requires each strategy to emit theoretical trade parameters on failure — touching all 7 strategy files. Deferred to a future sprint, possibly a Sprint 28 enhancement.

3. **Dedicated counterfactual UI:** No new Command Center page, no Observatory integration, no Copilot context injection. The REST endpoint exposes data; the Research Console (Sprint 31) will build a UI for it.

4. **Shadow strategy comparison tooling:** Shadow mode routes signals to the tracker, but there is no "shadow vs live" performance comparison dashboard or report. That analysis tooling belongs in Sprint 32.5 (Experiment Registry).

5. **Experiment Registry integration:** Counterfactual data will eventually feed the experiment queue. The integration API is not built in this sprint — Sprint 32.5 will consume CounterfactualStore data.

6. **Short-side counterfactual tracking:** All 7 active strategies are LONG only. The fill model assumes long-side priority (low breaches stop, high breaches target). Short-side support is deferred until short selling infrastructure (Sprint 30).

7. **WebSocket streaming of counterfactual positions:** No real-time push of counterfactual position state to the frontend. The REST endpoint provides point-in-time queries.

8. **Symbols not in viable universe:** Only signals that entered the pipeline and were explicitly rejected are tracked. Symbols that never passed Universe Manager filters are not tracked.

9. **Shadow-specific metrics or performance calculations:** Shadow mode records outcomes in the counterfactual store. It does not compute separate Sharpe ratios, drawdown curves, or performance summaries for shadow strategies. That's Sprint 32.5 consumption tooling.

10. **Counterfactual data in Observatory:** The Observatory's pipeline visualization (Funnel, Radar, Matrix) is not updated to show counterfactual flow. The counterfactual system operates as a parallel data collector, not a pipeline stage.

## Edge Cases to Reject

1. **Signal with empty `target_prices` tuple:** Log warning, do not open counterfactual position. A signal without a target price cannot have a meaningful counterfactual outcome.

2. **Signal with `entry_price == stop_price` (zero R):** Should not occur (BaseStrategy._has_zero_r() guard added in Sprint 27.65 suppresses these). If it does reach the tracker, log warning and skip — R-multiple computation would divide by zero.

3. **CandleEvent for symbol with no open counterfactual positions:** Ignore silently. The tracker only processes candles for symbols with active positions. No wasted computation.

4. **Counterfactual position for symbol removed from viable universe mid-session:** Continue monitoring. The Databento stream may or may not continue delivering candles. If no candles arrive within `no_data_timeout_seconds`, position expires as EXPIRED. Do not attempt to re-subscribe or force data.

5. **Multiple counterfactual positions for the same symbol from different rejection points in the same bar:** Track independently. Each has its own entry parameters and rejection metadata. Common scenario: ORB Breakout signal rejected by quality filter, ORB Scalp signal for same symbol rejected by risk manager.

6. **Race condition: signal rejected and candle arrives in same event loop iteration:** Not a concern. Event bus is FIFO per subscriber (DEC-025). SignalRejectedEvent is processed before subsequent CandleEvents because the rejection is published during `_process_signal()` which runs in the candle processing pipeline.

7. **IntradayCandleStore has no bars for symbol at backfill time:** Normal for the first candle of the day. Skip backfill, proceed with forward monitoring only.

8. **System restart mid-session with open counterfactual positions:** Counterfactual positions are in-memory only during monitoring. On restart, open positions from the store (status=MONITORING) are stale. Do NOT attempt to resume monitoring — mark them as EXPIRED with reason "system_restart". The data loss is acceptable (counterfactual data is statistical; individual position accuracy is less important than aggregate accuracy over days/weeks).

## Scope Boundaries

- **Do NOT modify:** `argus/core/risk_manager.py` (rejection reasons are already structured in OrderRejectedEvent — just publish a SignalRejectedEvent after receiving the rejection), `argus/core/regime.py` (RegimeVector is read-only), `argus/analytics/evaluation.py` (MultiObjectiveResult is a future consumer, not modified now), `argus/analytics/comparison.py`, `argus/data/intraday_candle_store.py` (read-only consumer via public API), individual strategy files (`argus/strategies/orb_breakout.py`, etc. — shadow mode is routing, not strategy logic), `argus/execution/order_manager.py`, `argus/ui/` (no frontend changes).

- **Do NOT optimize:** FilterAccuracy computation. Correctness over performance for V1. If 90-day query becomes slow (>1s), add indexes in a future sprint. Do not pre-optimize with materialized views or in-memory caching.

- **Do NOT refactor:** BacktestEngine beyond the fill model extraction. The extraction is surgical — pull out the fill priority logic into a shared function, call it from both places. Do not restructure BacktestEngine's position management, bracket handling, or orchestration.

- **Do NOT add:** Counterfactual position streaming via WebSocket, counterfactual data to Observatory views, shadow strategy performance dashboard, automated filter tuning, multi-target tracking (T2/T3), short-side fill model.

## Interaction Boundaries

- This sprint does NOT change the behavior of: `_process_signal()` for live-mode strategies with counterfactual disabled, Risk Manager's `evaluate_signal()` method, BacktestEngine's trade results (fill model extraction is behavior-preserving), any strategy's internal evaluation or signal generation logic, Order Manager's order submission flow, the Databento subscription model (no new subscriptions).

- This sprint does NOT affect: Frontend rendering or behavior, AI Copilot context (no new context injected), Observatory service, Catalyst Pipeline, Quality Engine scoring logic (quality scores are read, not modified), Performance Calculator, Trade Logger.

## Deferred to Future Sprints

| Item | Target Sprint | Rationale |
|------|--------------|-----------|
| Strategy-level near-miss events | Sprint 28 or future | Requires per-strategy changes to all 7 strategies to emit theoretical trade params on condition failure |
| Counterfactual data → Learning Loop consumption | Sprint 28 | Learning Loop queries counterfactual store for filter calibration |
| Counterfactual UI (Research Console) | Sprint 31 | Dedicated visualization of filter accuracy, counterfactual outcomes |
| Shadow strategy comparison tooling | Sprint 32.5 | Shadow vs live performance comparison requires Experiment Registry |
| Experiment Registry integration | Sprint 32.5 | Counterfactual store becomes a data source for experiment evaluation |
| Short-side fill model | Sprint 30 | Short selling infrastructure prerequisite |
| Counterfactual data in Observatory | Unscheduled | Low priority — Observatory is operational monitoring, not analytics |
| Multi-target counterfactual tracking (T2/T3) | Unscheduled | T1-only is sufficient for filter accuracy. Multi-target adds complexity for marginal value. |
