# Sprint 24.1: What This Sprint Does NOT Do

## Out of Scope
These items are related to the sprint goal but are explicitly excluded:

1. **New API endpoints:** The sprint does not add any new REST or WebSocket endpoints. Quality API routes already exist from Sprint 24.
2. **New database tables:** Only adds columns to the existing `trades` table. No new tables.
3. **Strategy logic changes:** No changes to any strategy's entry/exit logic, pattern detection, or parameter values.
4. **Intelligence Pipeline changes:** No changes to CatalystPipeline, CatalystClassifier, source polling, or classification logic. Only the CatalystStorage init log level in main.py is touched.
5. **Quality Engine scoring logic:** No changes to SetupQualityEngine.score_setup(), dimension weights, or grade thresholds. Only adds public accessors.
6. **Dynamic Position Sizer logic:** No changes to DynamicPositionSizer.calculate_shares().
7. **Risk Manager logic:** No changes to risk evaluation rules, circuit breakers, or gating conditions.
8. **Donut chart clickable segments (filter by grade):** Stretch goal for item 9 — deferred if not trivially achievable within the session.
9. **Config schema changes:** No new Pydantic model fields, no new YAML config keys. Only YAML comment additions.
10. **Dependency upgrades:** No package version changes in requirements.txt or package.json.
11. **Mobile-specific layout work:** Responsive stacking should work via existing Tailwind breakpoints. No mobile-specific debugging or layout overhaul.
12. **Backtest re-validation:** Sprint 21.6 remains separately planned. No backtest work here.

## Edge Cases to Reject
The implementation should NOT handle these cases in this sprint:

1. **Database migration rollback:** ALTER TABLE ADD COLUMN is one-way in SQLite. No rollback mechanism needed — columns are nullable and harmless if unused.
2. **Quality data backfill for historical trades:** Existing trades will have NULL quality columns. No attempt to backfill from quality_history table. Frontend already handles null gracefully (shows "—").
3. **ManagedPosition quality update after entry:** Quality data is set once at position creation from the signal. If the quality engine re-scores (it doesn't currently), the position's quality data is not updated.
4. **EFTS API rate limiting or authentication:** The diagnostic curl is a single request. No retry logic, no rate limit handling.
5. **TypeScript strict-mode perfection:** Fix the 22 existing errors. Do not chase additional warnings, enable stricter flags, or refactor surrounding code for type purity.
6. **Signal detail panel deep-linking:** Clicking a signal row shows inline detail. No URL routing, no shareable link, no browser back-button handling.

## Scope Boundaries
- **Do NOT modify:** `argus/core/events.py` (SignalEvent already has quality fields), `argus/strategies/*` (no strategy changes), `argus/intelligence/__init__.py` (pipeline orchestration), `argus/intelligence/classifier.py`, `argus/intelligence/sources/*` (except possibly sec_edgar.py for EFTS fix), `argus/core/risk_manager.py`, `argus/data/*`, `argus/core/orchestrator.py`, `argus/intelligence/config.py` (config models)
- **Do NOT optimize:** TradeLogger query performance, quality engine scoring speed, or frontend rendering performance
- **Do NOT refactor:** Order Manager architecture, Trade model inheritance, or TradeLogger method signatures beyond the minimum needed to add quality fields
- **Do NOT add:** New quality dimensions, new quality grade levels, new risk tiers, new dashboard pages, new navigation routes

## Interaction Boundaries
- This sprint does NOT change the behavior of: the quality scoring pipeline (_process_signal flow), the event bus contract, the Risk Manager evaluation contract, the broker abstraction interface, any API response shapes (quality fields already present in trades API response, just null)
- This sprint does NOT affect: backtesting (BrokerSource.SIMULATED bypass path unchanged), live trading execution logic, Databento data service, scanner, or FMP reference client

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Donut chart clickable segments (filter by grade) | Unscheduled | Part of DEF-052 |
| Quality data backfill for historical trades | Unscheduled | New (if needed) |
| Mobile-specific layout polish | Unscheduled | — |
