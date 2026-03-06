# Sprint 23: Escalation Criteria

These are specific, evaluable conditions. If ANY of these are true after a session's implementation, the Tier 2 reviewer should verdict ESCALATE.

## Performance Escalations

1. **Candle routing adds >50μs per event**: The Universe Manager's `route_candle()` must be a fast dict lookup. If profiling or timing shows >50μs overhead per candle event, this threatens the ~2–4% CPU budget from DEC-263. ESCALATE — may need architectural change to routing.

2. **FMP reference data fetch takes >5 minutes for 4,000 symbols**: The batch endpoint should complete in <2 minutes. If it takes >5 minutes, either the batch endpoint isn't available on Starter or the batching strategy is wrong. ESCALATE — may need alternative data source or approach.

3. **Memory overhead >500MB above baseline with full universe loaded**: 4,000 IndicatorEngine instances should use ~4–50MB. If memory growth exceeds 500MB, there's a leak or unexpected allocation pattern. ESCALATE.

4. **Startup time increase >5 minutes when Universe Manager enabled**: The UM path adds FMP fetch + universe construction + routing table build. If total startup exceeds existing time + 5 minutes, ESCALATE.

## Correctness Escalations

5. **Any existing strategy test fails after Session 4b integration**: The Universe Manager must not change existing behavior when disabled, and must correctly route candles when enabled. Any existing test failure indicates a regression. ESCALATE.

6. **ORB same-symbol mutual exclusion (DEC-261) broken**: If both ORB Breakout and ORB Scalp can fire on the same symbol on the same day when Universe Manager is active, the exclusion logic was disrupted. ESCALATE.

7. **Strategies receive candles for symbols that don't match their filter**: Routing table correctness is fundamental. If a strategy's `on_candle` is called with a symbol that shouldn't pass its `universe_filter`, ESCALATE.

8. **Strategies do NOT receive candles for symbols that DO match their filter**: Candle loss is the inverse failure. If a valid symbol's candles are being discarded, ESCALATE.

## Integration Escalations

9. **Databento ALL_SYMBOLS subscription causes session errors, rate limiting, or unexpected costs**: The subscription model change is the highest-risk integration point. Any session-level errors from Databento when using ALL_SYMBOLS mode → ESCALATE.

10. **Backtesting or replay modes affected by Universe Manager changes**: These modes must be completely unaffected regardless of `universe_manager.enabled` setting. Any behavior change in non-live modes → ESCALATE.

11. **AI Copilot (Sprint 22) functionality degraded**: The AI layer must not be affected by Universe Manager changes. If Copilot context injection, streaming, or action proposals break → ESCALATE.

## Scope Escalations

12. **Session requires modifying files in the "Do not modify" list**: If a session discovers it needs to change `argus/ai/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/analytics/`, or `argus/strategies/*.py` → ESCALATE before making the change.

13. **Config field mismatch between YAML and Pydantic model discovered late**: If any YAML key is silently ignored by Pydantic (not validated), this is a config integrity failure. ESCALATE — the field naming must be corrected before proceeding.
