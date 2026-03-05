# Sprint 21.7 — Escalation Criteria (all sessions)

Escalate to Tier 3 review if ANY of the following occur:

1. WatchlistItem changes in events.py break existing strategy signal tests
2. main.py scanner routing introduces a regression where strategies receive
   incorrect or empty watchlists in replay/backtest mode
3. FMPScannerSource introduces any import-time dependency on DatabentoScanner
   or AlpacaScanner
4. AppState changes to support cached_watchlist break existing API endpoint tests
5. The frontend Pre-Market Watchlist panel introduces new state management
   outside of useWatchlist() (e.g., new Zustand store, new API endpoint)
6. Any modification to files outside declared scope (strategies/, risk_manager.py,
   orchestrator.py, WatchlistSidebar.tsx)
