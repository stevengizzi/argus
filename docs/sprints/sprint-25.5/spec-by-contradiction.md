# Sprint 25.5: What This Sprint Does NOT Do

## Out of Scope
1. **Performance optimization for large symbol counts.** If strategies work correctly with 2,101 symbols but show measurable slowdown, that is a separate sprint. This sprint's goal is correctness, not throughput tuning.
2. **Changes to Universe Manager filters or routing logic.** The UM is working correctly — it routes symbols to strategies. The bug is that the strategy-side gate doesn't know about the routed symbols.
3. **Observatory frontend changes.** The Observatory should populate automatically once evaluation data flows. If it doesn't, that's a separate bug.
4. **Quality pipeline or catalyst pipeline changes.** The quality engine already processes signals downstream of strategy evaluation. Once signals flow, the quality pipeline activates. No changes needed.
5. **New evaluation event types or telemetry schema changes.** The existing `evaluation_events` schema is sufficient.
6. **Backfilling lost paper trading data.** The 10 days of inert paper trading (March 7–18) cannot be recovered. No attempt should be made to simulate or reconstruct that data.
7. **Removing the strategy-level watchlist check entirely.** The `_watchlist` is used for logging, API responses, and serves as a defense-in-depth gate. It stays.
8. **Changes to the candle routing path in main.py (lines 724-745).** The Universe Manager routing and legacy fallback both work correctly. Only the watchlist population at startup is broken.

## Edge Cases to Reject
1. **Scanner symbol not in UM viable universe:** Log at DEBUG, do not warn or block. The scanner and UM use different filter criteria; slight mismatches are expected.
2. **Strategy has 0 routed symbols from UM:** This is legitimate (e.g., if all symbols fail a strategy's `universe_filter`). Set an empty watchlist, do NOT warn. The health warning distinguishes this case.
3. **`set_watchlist()` called with duplicate symbols:** `set` storage handles deduplication automatically. No special handling needed.
4. **`set_watchlist()` called multiple times in one session:** Last call wins. This is existing behavior and should not change.
5. **Strategy time window has not opened yet when health check runs:** No warning. The health check only evaluates after the strategy's configured window start + 5 minutes.

## Scope Boundaries
- Do NOT modify: `argus/data/universe_manager.py`, `argus/strategies/orb_base.py`, `argus/strategies/vwap_reclaim.py`, `argus/strategies/afternoon_momentum.py`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py`, `argus/analytics/observatory_service.py`, any config YAML files, any frontend files
- Do NOT optimize: Strategy per-symbol state management (opening range dicts, VWAP state machines). If 2,101 symbols causes memory or CPU issues, defer to a performance sprint.
- Do NOT refactor: The dual-path candle routing in main.py (UM path vs legacy path). Both work; they just need the watchlist populated.
- Do NOT add: New API endpoints, new config fields, new database tables, new WebSocket channels, new frontend components

## Interaction Boundaries
- This sprint does NOT change the behavior of: `on_candle()` logic in any strategy, `route_candle()` in Universe Manager, `_process_signal()` in main.py, Risk Manager gating, Order Manager execution, Event Bus delivery, Observatory WebSocket push, any REST API response schema
- This sprint does NOT affect: AI Copilot, catalyst pipeline, quality engine scoring logic, briefing generator, trade logger, performance calculator, backtesting infrastructure

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Performance profiling with 2,100+ symbol watchlists | Unscheduled (only if issues observed) | — |
| Observatory REST polling alongside WS (double-fetch) | Sprint 26 or later | — |
| Remove redundant strategy watchlist check when UM active | Unscheduled (defense-in-depth; keep for now) | — |
