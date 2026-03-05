# Sprint 21.7 Design Summary

**Sprint Goal:** Integrate FMP Starter ($22/mo) as the pre-market scanning
data source, replacing the broken Databento historical daily bar path
(DEC-247). Surface scanner results with selection reasoning on the Dashboard
Pre-Market Watchlist panel.

**Session Breakdown:**
- Session 1: Backend — FMPScannerSource class + WatchlistItem extension + tests
- Session 2: Backend — Config wiring (main.py routing, scanner.yaml, API endpoint)
- Session 3: Frontend — Activate Pre-Market Watchlist panel in PreMarketLayout

**Key Decisions:**
- FMP endpoints: /api/v3/gainers, /api/v3/losers, /api/v3/actives (3 calls max)
- aiohttp.ClientSession for async HTTP (already in production deps)
- main.py scanner routing: read scanner_type from scanner.yaml (fix ignored key)
  scanner_type: "fmp" → FMPScannerSource
  scanner_type: "databento" → DatabentoScanner (unchanged, for replay)
  scanner_type: "static" → StaticScanner (default)
- FMP_API_KEY env var, existing secrets infrastructure
- Add scan_source: str and selection_reason: str to WatchlistItem (events.py)
- Pre-Market Watchlist panel replaces RankedWatchlistPlaceholder in PreMarketLayout.tsx
  Columns activated: Rank, Symbol, Gap%, Source badge, Selection Reason
  Columns deferred: Catalyst (Sprint 23), Quality (Sprint 24) — shown as "—"
- DatabentoScanner: untouched; retained for replay/backtest workflows

**Scope Boundaries:**
- IN: FMPScannerSource, scanner_type routing in main.py, WatchlistItem fields,
  Pre-Market Watchlist panel, scanner.yaml fmp_scanner section
- OUT: Catalyst tags, quality scores, full-universe scanning (DEF-015),
  FMP Premium upgrade, WatchlistSidebar changes, DatabentoScanner changes,
  AlpacaScanner changes, any strategy files

**Regression Invariants:**
- StaticScanner: behavior unchanged
- DatabentoScanner: behavior unchanged
- All strategies receive correct watchlist symbols
- GET /watchlist continues to return valid WatchlistResponse
- All 1,737 pytest + 291 Vitest tests pass

**File Scope:**
- Create: argus/data/fmp_scanner.py, tests/data/test_fmp_scanner.py
- Modify: argus/core/events.py (WatchlistItem fields),
          argus/main.py (scanner routing),
          config/scanner.yaml (add fmp_scanner section, scanner_type: "fmp"),
          argus/api/routes/watchlist.py (populate scan_source/selection_reason),
          argus/ui/src/api/types.ts (WatchlistItem interface),
          argus/ui/src/features/dashboard/PreMarketLayout.tsx (activate panel)
- Do NOT modify: DatabentoScanner, AlpacaScanner, any strategy files,
                  Risk Manager, Orchestrator, Order Manager, EventBus

**Test Strategy:**
- New: tests/data/test_fmp_scanner.py (~15 tests, mocked aiohttp responses)
- Update: tests/api/test_watchlist.py (scan_source/selection_reason field validation)

**Escalation Criteria:**
- Tier 3 if: FMPScannerSource changes strategy behavior or watchlist contract
- Tier 3 if: main.py changes break existing scanner startup sequence
- ESCALATE from Tier 2 if: events.py WatchlistItem changes break event publishing

**Doc Updates:**
- CLAUDE.md: Add FMP_API_KEY to required env vars section
- decision-log.md: DEC-258/259 already logged; add session notes
- config/scanner.yaml: Update comments to reflect FMP as primary path

**Artifacts to Generate:**
1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown
4. Implementation Prompt × 3
5. Review Prompt × 3
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
