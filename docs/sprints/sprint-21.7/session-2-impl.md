# Sprint 21.7, Session 2: Config Routing + API Endpoint Wiring

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - argus/main.py (scanner initialization, lines ~233–270)
   - config/scanner.yaml (current structure)
   - argus/data/fmp_scanner.py (just created in Session 1)
   - argus/api/routes/watchlist.py (current endpoint implementation)
   - argus/api/dependencies.py or argus/api/dev_state.py (AppState structure)
2. Run: pytest tests/ -x -q
   Expected: 1,737 + ~15 new = ~1,752 tests, all passing
3. Confirm Session 1 is merged/complete before beginning.

## Objective
Wire FMPScannerSource into the startup sequence (main.py), update scanner.yaml
with FMP config section and scanner_type: "fmp", and update the watchlist API
endpoint to populate scan_source and selection_reason on WatchlistItems.

## Requirements

### 1. Update argus/main.py — Scanner Routing

Replace the current if/else scanner selection block (around line 238) with
a scanner_type-based dispatch that reads from scanner.yaml directly:
```python
scanner_type = scanner_yaml.get("scanner_type", "static")

if scanner_type == "fmp":
    logger.info("Using FMP scanner")
    from argus.data.fmp_scanner import FMPScanner, FMPScannerConfig
    fmp_scanner_data = scanner_yaml.get("fmp_scanner", {})
    fmp_config = FMPScannerConfig(**fmp_scanner_data)
    self._scanner = FMPScanner(config=fmp_config)
elif scanner_type == "databento":
    logger.info("Using Databento scanner")
    # existing DatabentoScanner branch
elif scanner_type == "alpaca":
    logger.info("Using Alpaca scanner")
    # existing AlpacaScanner branch
else:
    logger.info("Using static scanner (type=%s)", scanner_type)
    static_symbols = scanner_yaml.get("static_symbols", [])
    self._scanner = StaticScanner(symbols=static_symbols)
```

NOTE: The existing elif branches (databento, alpaca) remain identical to
current code — just reorganized under the new dispatch. Do NOT change
their logic.

Import FMPScannerSource and FMPScannerConfig at top of file alongside
other scanner imports (lazy import inside the if block is also acceptable
to avoid circular imports — use whichever works cleanly).

### 2. Update config/scanner.yaml

Change scanner_type to "fmp" and add fmp_scanner section:
```yaml
# Scanner Configuration
# scanner_type: "fmp" | "databento" | "alpaca" | "static"
# "fmp" uses Financial Modeling Prep REST API (DEC-258, Sprint 21.7)
# "static" used for replay/backtest; "databento"/"alpaca" retained for fallback
scanner_type: "fmp"

# Static scanner symbols (fallback for all scanner types when API fails)
static_symbols:
  - "AAPL"
  - "MSFT"
  - "NVDA"
  - "TSLA"
  - "AMD"
  - "AMZN"
  - "META"
  - "GOOGL"

# FMP scanner configuration (used when scanner_type = "fmp")
fmp_scanner:
  min_price: 10.0
  max_price: 500.0
  min_volume: 500000
  max_symbols_returned: 15
  fallback_symbols:
    - "AAPL"
    - "MSFT"
    - "NVDA"
    - "TSLA"
    - "AMD"
    - "AMZN"
    - "META"
    - "GOOGL"

# Databento scanner (retained for replay/backtest, scanner_type: "databento")
databento_scanner:
  [... existing content unchanged ...]

# Alpaca scanner (retained as fallback option, scanner_type: "alpaca")
alpaca_scanner:
  [... existing content unchanged ...]
```

### 3. Update argus/api/routes/watchlist.py — Production Path

In the `if state.data_service is not None` branch (currently has `pass`),
add real watchlist population:
```python
# Production mode: aggregate from scanner
scanner = getattr(state, '_scanner', None)
if scanner is not None:
    from argus.data.scanner import StaticScanner
    # Get scanner's last watchlist from state cache
    cached_watchlist = getattr(state, '_cached_watchlist', [])
    for core_item in cached_watchlist:
        watchlist_items.append(WatchlistItem(
            symbol=core_item.symbol,
            current_price=0.0,  # populated from data_service in Sprint 22+
            gap_pct=core_item.gap_pct,
            strategies=[],      # populated from strategy states in Sprint 22+
            vwap_state=VwapState.WATCHING,
            sparkline=[],
            scan_source=core_item.scan_source,
            selection_reason=core_item.selection_reason,
        ))
```

Also add scan_source and selection_reason fields to the WatchlistItem API model
in watchlist.py:
```python
class WatchlistItem(BaseModel):
    ...
    scan_source: str = ""
    selection_reason: str = ""
```

NOTE: The `_cached_watchlist` will need to be stored on AppState after
the scanner runs. Check argus/api/dependencies.py for AppState definition.
Add `cached_watchlist: list = []` field if it doesn't exist, and populate
it in main.py after the scan completes:
```python
# After scanner.scan() completes:
self._app_state.cached_watchlist = watchlist  # the WatchlistItem list from events.py
```
(Find where AppState is constructed and populated in main.py / dependencies.py)

### 4. Update argus/ui/src/api/types.ts

Add to the WatchlistItem interface:
```typescript
scan_source: string;       // "fmp" | "fmp_fallback" | "static" | ""
selection_reason: string;  // "gap_up_3.2%" | "gap_down_1.8%" | "high_volume" | ""
```

### 5. Write new integration test

In tests/api/test_watchlist.py (or create if it doesn't exist):
- test_watchlist_response_includes_scan_source_field
- test_watchlist_response_includes_selection_reason_field
(Can be simple tests against the mock dev state, confirming field presence)

## Constraints
- Do NOT change DatabentoScanner initialization logic in the existing elif branch
- Do NOT change AlpacaScanner initialization logic in the existing elif branch
- Do NOT modify any strategy files
- Do NOT break the fallback to static_symbols when scanner returns nothing
- scanner.yaml for non-live configs (system.yaml/replay): leave scanner_type as "static"
  (or leave scanner.yaml unchanged for replay — only the production config needs "fmp")

## Test Targets
- pytest tests/api/ -v (watchlist endpoint tests)
- pytest tests/ -x -q (full suite)

## Definition of Done
- [ ] main.py routes to FMPScannerSource when scanner_type: "fmp"
- [ ] scanner.yaml has fmp_scanner section with scanner_type: "fmp"
- [ ] watchlist API endpoint has scan_source + selection_reason fields
- [ ] api/types.ts WatchlistItem interface updated
- [ ] Full test suite passes
- [ ] ruff check passes

## Regression Checklist
| Check | How to Verify |
|-------|---------------|
| Static scanner still works | scanner_type: "static" in scanner.yaml → StaticScanner instantiated |
| Databento branch intact | scanner_type: "databento" → DatabentoScanner (grep diff) |
| Startup sequence unchanged | main.py Phase 7/8 log order preserved |
| Watchlist endpoint backward compat | existing tests pass, new fields have defaults |

## Close-Out
Follow .claude/skills/close-out.md
