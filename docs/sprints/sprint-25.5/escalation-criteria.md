# Sprint 25.5: Escalation Criteria

## Tier 3 Escalation Triggers

1. **Performance degradation observed.** If after the watchlist fix, Databento heartbeat candle counts drop significantly (e.g., from ~11,000/5min to <8,000/5min) or event loop latency is observable (API response times degrade), halt and escalate. This would indicate that 2,100+ symbols hitting strategy `on_candle()` is too much for the current architecture.

2. **More than 5 existing tests break from list→set conversion.** The `_watchlist` type change from `list` to `set` should be transparent, but if more than 5 tests fail due to ordering assumptions, iteration behavior, or type checks, escalate to assess whether the change should be approached differently.

3. **Evaluation events not appearing in SQLite despite ring buffer being populated.** This would indicate a persistence wiring issue between `StrategyEvaluationBuffer` and `EvaluationEventStore` that predates this sprint and requires deeper investigation.

4. **Observatory endpoints return empty despite evaluation_events table having rows.** This would indicate an `ObservatoryService` query issue unrelated to the watchlist fix, requiring separate investigation.

## Session-Level Halt Conditions

### Session 1
- Pre-flight full test suite fails with errors unrelated to sprint scope → halt, investigate
- `get_strategy_symbols()` returns unexpected results (e.g., 0 symbols when routing table logged 2,101) → halt, investigate UM state

### Session 2
- Session 1 review verdict is REJECT → do not start Session 2
- HealthMonitor has no mechanism for time-delayed checks → design required before implementation, may need to restructure the session scope
