# Sprint 23.6: What This Sprint Does NOT Do

## Out of Scope
1. **New intelligence data sources:** No new CatalystSource implementations. Only the existing three (SEC EDGAR, FMP News, Finnhub) are wired.
2. **Intelligence router URL prefix change (DEF-036):** Routes stay at `/api/v1/catalysts/*` and `/api/v1/premarket/*`. Prefix standardization deferred to avoid frontend coupling.
3. **Frontend/UI changes:** No React components, hooks, or pages modified. Dashboard, Orchestrator, and Debrief views are untouched.
4. **Fuzzy/embedding-based dedup:** Semantic dedup uses `(symbol, category, time_window)` key only — no NLP similarity.
5. **Transactional publish guarantee (M2 full solution):** Batch store → batch publish ordering is implemented, but there is no retry queue or guaranteed delivery. Failed publishes are logged but not retried.
6. **Strategy code changes:** No files in `argus/strategies/` are modified.
7. **New runner execution capabilities:** Runner decomposition (S4) is pure refactoring. Conformance monitoring (S5) is observability only. No new runner modes or behaviors.
8. **Automated pre-market scheduling:** The polling loop runs when the app is running. There is no cron-style scheduler or auto-start mechanism for ARGUS itself.
9. **Cache sharing across instances:** Reference data cache is a local file. No network-shared cache, no Redis, no distributed invalidation.
10. **FMP Premium upgrade (DEF-024):** Cache optimization reduces the need. FMP Starter is adequate.

## Edge Cases to Reject
1. **Concurrent pipeline poll cycles:** If a poll cycle takes longer than the interval, the next poll waits — no overlapping execution. Log WARNING.
2. **Cache file locked by another process:** Treat as corrupt; fall back to full fetch with WARNING.
3. **FMP stock-list returns 0 symbols with valid cache:** Use cached symbols as fallback; log WARNING.
4. **Universe Manager disabled but catalyst enabled:** Pipeline polls with cached watchlist symbols only; log INFO about reduced coverage.
5. **All three catalyst sources disabled but pipeline enabled:** Pipeline starts successfully but `run_poll()` returns empty results each cycle. Log WARNING at startup.

## Scope Boundaries
- **Do NOT modify:** `argus/strategies/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/analytics/`, `argus/backtest/`, `argus/ai/`, `argus/data/scanner.py`, `argus/data/databento_data_service.py`, `argus/ui/` (entire frontend)
- **Do NOT optimize:** CatalystClassifier internals, Claude API prompt engineering, Event Bus performance
- **Do NOT refactor:** AI layer initialization in server.py (it works, leave it), existing storage table schemas (catalyst_classifications_cache, intelligence_briefs)
- **Do NOT add:** New Event Bus event types, new API endpoints beyond existing intelligence routes, new Pydantic models in `argus/core/config.py` beyond the single `catalyst` field addition

## Interaction Boundaries
- This sprint does NOT change the behavior of: Event Bus (FIFO, sequence numbers), WebSocket bridge, AI layer (ClaudeClient, PromptManager, ActionManager), any strategy's `on_candle()` or signal generation, Risk Manager gating, Orchestrator allocation, Order Manager lifecycle
- This sprint does NOT affect: Databento data flow, IBKR broker connectivity, trade logging, performance calculation, backtesting infrastructure

## Deferred to Future Sprints

| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Intelligence router URL prefix | Unscheduled | DEF-036 |
| Fuzzy/embedding-based dedup | Sprint 28+ | DEF (new, assign at doc sync) |
| FMP Premium upgrade | Unscheduled | DEF-024 |
| Runner main.py further decomposition (beyond cli.py) | When runner needs changes | DEF-039 |
| Push `since` filter to SQL for briefing queries | Unscheduled | DEF-037 (partially addressed — catalyst queries fixed, briefing queries unchanged) |
