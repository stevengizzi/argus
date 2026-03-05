# Sprint 21.7 — Regression Checklist (post all sessions)

| Invariant | How to Verify |
|-----------|---------------|
| All 1,737 existing pytest pass | pytest tests/ -x -q (ignore new tests) |
| All 291 existing Vitest pass | cd argus/ui && npx vitest run |
| Static scanner path works | scanner_type: "static" → StaticScanner, symbols returned |
| Databento scanner path works | scanner_type: "databento" → DatabentoScanner instantiated |
| Strategies receive watchlist | log output shows strategy.set_watchlist() called with symbols |
| Watchlist API returns valid response | GET /watchlist → WatchlistResponse with scan_source/selection_reason fields |
| WatchlistSidebar unchanged | git diff argus/ui/src/features/watchlist/ = no changes |
| No regression in PreMarketLayout tests | cd argus/ui && npx vitest run PreMarketLayout |
| Risk Manager limits unchanged | pytest tests/core/test_risk_manager.py |
| Orchestrator behavior unchanged | pytest tests/core/test_orchestrator.py |
