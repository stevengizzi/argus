# Sprint 21.7: What This Sprint Does NOT Do

## Out of Scope
1. Catalyst tags on watchlist symbols: Deferred to Sprint 23 (NLP Pipeline).
   The "Catalyst" column in the Pre-Market Watchlist panel is NOT activated.
2. Quality scores on watchlist symbols: Deferred to Sprint 24 (Quality Engine).
   The "Quality" column is NOT activated.
3. Full-universe scanning: DEF-015 still deferred. FMP Starter screener endpoint
   will not be used to scan 8,000 symbols. V1 uses gainers/losers/actives results
   from FMP (which are already filtered by FMP).
4. FMP Premium/Ultimate upgrade: Not needed for Sprint 21.7. Upgrade happens
   in Sprint 23 when NLP endpoints are required.
5. Pre-market data streaming: FMP provides REST snapshots, not streaming.
   No WebSocket or polling during market hours from FMP.

## Edge Cases to Reject
1. FMP returns 0 symbols: Fall back to static symbol list from scanner.yaml.
   Do NOT fail startup. Log as DEGRADED, not ERROR.
2. FMP API key missing: Raise RuntimeError at scanner.start(), caught by main.py
   startup sequence. System falls back to static list with DEGRADED status.
3. FMP returns symbols not in any strategy's criteria: Include them. Strategies
   filter their own watchlists at signal evaluation time.
4. FMP returns the same symbol from multiple endpoints (gainers + actives):
   Deduplicate. Keep the entry with the stronger selection_reason signal.

## Scope Boundaries
- Do NOT modify: DatabentoScanner, AlpacaScanner, StaticScanner
- Do NOT modify: any Strategy files (ORB, Scalp, VWAP, Afternoon Momentum)
- Do NOT modify: Risk Manager, Orchestrator, Order Manager, EventBus
- Do NOT modify: WatchlistSidebar.tsx or WatchlistItem.tsx (the live-session
  sidebar is unchanged; only PreMarketLayout.tsx gets the new panel)
- Do NOT optimize: FMP HTTP client (plain aiohttp ClientSession, no connection
  pooling needed for 3 calls/day)
- Do NOT add: Retry logic beyond a single try/except with fallback
- Do NOT add: FMP symbol metadata (sector, market cap, float) to WatchlistItem
  (these are Sprint 23+ concerns)

## Interaction Boundaries
- This sprint does NOT change the behavior of: DatabentoScanner, AlpacaScanner,
  StaticScanner, EventBus, any strategy signal generation
- This sprint does NOT affect: IBKR execution, Risk Manager limits, Order Manager
  behavior, Performance page, Orchestrator page

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|-------------|---------------|
| Catalyst tags on Pre-Market Watchlist | Sprint 23 | DEF-015 |
| Quality scores on Pre-Market Watchlist | Sprint 24 | — |
| Full-universe FMP screener | Unscheduled | DEF-015 |
| FMP Premium/Ultimate for NLP | Sprint 23 | — |
