# Sprint 21.7: FMP Scanner Integration

## Goal
Integrate Financial Modeling Prep (FMP) Starter as the pre-market scanning
data source, replacing the broken Databento historical daily bar path
(DEC-247). Enable dynamic symbol selection each morning and surface scanner
results on the Dashboard Pre-Market Watchlist panel.

## Scope

### Deliverables
1. FMPScannerSource — a Scanner ABC implementation that queries FMP's gainers,
   losers, and actives endpoints to produce a ranked watchlist of candidates.
2. Config routing — main.py respects scanner_type from scanner.yaml;
   scanner_type: "fmp" activates FMPScannerSource.
3. WatchlistItem extension — scan_source and selection_reason fields added
   (events.py and API layer).
4. Pre-Market Watchlist panel — RankedWatchlistPlaceholder in PreMarketLayout.tsx
   replaced with a live panel showing FMP-selected symbols, gap%, and selection
   reason. Catalyst and Quality columns deferred (shown as "—").

### Acceptance Criteria

1. FMPScannerSource:
   - Makes at most 3 HTTP calls to FMP on scan() invocation
   - Returns WatchlistItems with gap_pct populated from FMP data
   - Returns WatchlistItems with scan_source="fmp" and selection_reason set
     (e.g., "gap_up_3.2%", "gap_down_1.8%", "high_volume")
   - Falls back to static symbol list if FMP API call fails (same fallback
     behavior as DatabentoScanner)
   - Respects min_price, max_price, min_volume, max_symbols_returned filters
   - All behavior covered by unit tests with mocked aiohttp responses

2. Config routing:
   - scanner.yaml with scanner_type: "fmp" → FMPScannerSource instantiated
   - scanner.yaml with scanner_type: "databento" → DatabentoScanner (unchanged)
   - scanner.yaml with scanner_type: "static" or absent → StaticScanner (unchanged)
   - FMP_API_KEY env var read at runtime; RuntimeError if absent when scanner starts

3. WatchlistItem extension:
   - scan_source: str field added with default "" (backward-compatible)
   - selection_reason: str field added with default "" (backward-compatible)
   - API watchlist endpoint returns scan_source and selection_reason per symbol
   - Frontend types updated (WatchlistItem interface in api/types.ts)

4. Pre-Market Watchlist panel:
   - Renders when PreMarketLayout is active (pre-market hours or ?premarket=true)
   - Shows columns: Rank, Symbol, Gap%, Source (badge), Reason
   - "Source" badge reads "FMP" when scan_source="fmp", "Static" otherwise
   - Catalyst and Quality columns not shown (deferred to Sprint 23/24)
   - Uses existing useWatchlist() hook — no new API calls
   - Loading skeleton shown while data fetches
   - Empty state shown when watchlist returns 0 symbols

### Performance Benchmarks
| Metric | Target | Method |
|--------|--------|--------|
| FMP scan() wall time | < 3 seconds | logged in scan() with time.perf_counter |
| Symbols returned | 5–15 | log count after filtering |

## Dependencies
- Sprint 21.5.1 complete (live system stable)
- FMP Starter subscription active ($22/mo, DEC-258)
- FMP_API_KEY available in secrets manager

## Relevant Decisions
- DEC-247: Databento historical scanner broken (multi-day lag) — this is what we're fixing
- DEC-257: Hybrid architecture — FMP for scanning, Databento for streaming
- DEC-258: FMP Starter plan selected for scanning
- DEC-259: Sprint 21.7 scoped as focused 2-3 session mini-sprint

## Relevant Risks
- RSK (new): FMP Starter endpoint availability — gainers/losers/actives may
  require a higher plan. Mitigation: test against FMP docs before Session 1;
  fallback to stock screener endpoint if needed.
- RSK-022: IBKR nightly reset (unrelated, pre-existing)

## Session Count Estimate
3 sessions. Session 1: FMPScannerSource (new class, tests). Session 2: config
routing + API wiring (main.py, scanner.yaml, watchlist endpoint). Session 3:
frontend panel (PreMarketLayout.tsx). Frontend is lower risk than backend
(existing panel structure to replace), so 1 session is realistic with 1
fix session budgeted if needed.
