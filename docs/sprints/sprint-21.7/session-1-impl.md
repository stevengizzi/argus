# Sprint 21.7, Session 1: FMPScannerSource + WatchlistItem Extension

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - argus/data/scanner.py (Scanner ABC)
   - argus/data/databento_scanner.py (reference implementation to mirror)
   - argus/core/events.py (WatchlistItem dataclass)
   - pyproject.toml (confirm aiohttp in production deps — it is)
2. Run test suite: pytest tests/ -x -q
   Expected: 1,737 tests, all passing
3. Verify branch: git status (should be clean, main or sprint-21.7 branch)

## Objective
Implement FMPScannerSource — a Scanner ABC implementation that queries
FMP's biggest-gainers, biggest-losers, and most-actives REST endpoints
(new /stable/ API, not legacy /api/v3/). Also extend WatchlistItem in
events.py with scan_source and selection_reason fields (backward-compatible).

## Requirements

### 1. Extend WatchlistItem in argus/core/events.py
Add two optional fields with empty-string defaults (backward-compatible):
- scan_source: str = ""  — e.g., "fmp", "static", "fmp_fallback"
- selection_reason: str = ""  — e.g., "gap_up_3.2%", "gap_down_1.8%", "high_volume"

### 2. Create argus/data/fmp_scanner.py

FMPScannerConfig (dataclass or simple class, NOT Pydantic — follow
DatabentoScannerConfig pattern which is a plain class):
  - base_url: str = "https://financialmodelingprep.com/stable"
  - api_key_env_var: str = "FMP_API_KEY"
  - min_price: float = 10.0
  - max_price: float = 500.0
  - min_volume: int = 500_000   # Reserved — not returned by current FMP endpoints.
                                 # Kept for future use (screener endpoint, Sprint 23+).
  - max_symbols_returned: int = 15
  - fallback_symbols: list[str] = field(default_factory=list)

FMPScannerSource(Scanner):
  __init__(config: FMPScannerConfig)

  async def start(self) -> None:
    - Read FMP_API_KEY from os.getenv(config.api_key_env_var)
    - If key is None: raise RuntimeError("FMP API key not found. Set FMP_API_KEY.")
    - Store key as self._api_key
    - Log "FMPScannerSource started"

  async def stop(self) -> None:
    - Clear self._api_key
    - Log "FMPScannerSource stopped"

  async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
    - Log "FMPScannerSource starting scan"
    - Call self._fetch_candidates() → list[WatchlistItem]
    - If result is empty or exception: fall back to static list via _fallback_candidates()
    - Log count of candidates returned
    - Return list

  async def _fetch_candidates(self) -> list[WatchlistItem]:
    - Use aiohttp.ClientSession (context manager, single session for all three calls)
    - Make 3 concurrent calls using asyncio.gather():
        GET {base_url}/biggest-gainers?apikey={key}
        GET {base_url}/biggest-losers?apikey={key}
        GET {base_url}/most-actives?apikey={key}
    - Each response is a JSON array. Each item has these confirmed fields:
        symbol (str)           — e.g., "AAPL"
        price (float)          — e.g., 183.04
        change (float)         — dollar change, e.g., 2.99
        changesPercentage (float) — percent change as a float, e.g., 186.55 (NOT a string)
        name (str)             — company name
        exchange (str)         — e.g., "NASDAQ", "AMEX", "NYSE"
      NOTE: There is NO volume field in these endpoints. Do not attempt to read
      or filter by volume. The min_volume config field is reserved for future use.
    - For gainers: selection_reason = f"gap_up_{abs(changesPercentage):.1f}%"
    - For losers: selection_reason = f"gap_down_{abs(changesPercentage):.1f}%"
    - For actives: selection_reason = "high_volume"
    - Apply filter: min_price <= price <= max_price  (only price filter — no volume filter)
    - Deduplicate by symbol: gainers entry wins over actives if symbol appears in both;
      losers entry wins over actives if symbol appears in both
    - Set scan_source = "fmp" on all items
    - Map changesPercentage to WatchlistItem.gap_pct by dividing by 100
      (e.g., changesPercentage=186.55 → gap_pct=1.8655)
    - Sort: gainers and losers first (by abs(gap_pct) descending), then actives
    - Return top max_symbols_returned items

  async def _fallback_candidates(self) -> list[WatchlistItem]:
    - Return [WatchlistItem(symbol=s, scan_source="fmp_fallback")
              for s in self._config.fallback_symbols[:self._config.max_symbols_returned]]

### 3. Create tests/data/test_fmp_scanner.py

Test cases (use pytest + pytest-asyncio, mock aiohttp with unittest.mock.patch).
Use this confirmed JSON schema in all mock data:
  {"symbol": "AAPL", "price": 150.0, "change": 5.0, "changesPercentage": 3.45,
   "name": "Apple Inc.", "exchange": "NASDAQ"}

1.  test_scan_returns_gap_up_candidates
    Mock biggest-gainers returning 5 symbols with price=50.0, changesPercentage=5.0.
    losers and actives return []. Assert 5 WatchlistItems returned.

2.  test_scan_returns_gap_down_candidates
    Mock biggest-losers returning 5 symbols with price=50.0, changesPercentage=-5.0.
    gainers and actives return []. Assert 5 WatchlistItems returned.

3.  test_scan_deduplicates_across_endpoints
    Same symbol appears in gainers (changesPercentage=10.0) and actives.
    Assert symbol appears once in output, with selection_reason from gainers ("gap_up_10.0%").

4.  test_scan_filters_by_min_price
    Symbol with price=5.0 (below min_price=10.0) in gainers. Assert excluded from output.

5.  test_scan_filters_by_max_price
    Symbol with price=600.0 (above max_price=500.0) in gainers. Assert excluded from output.

6.  test_scan_filters_price_boundary_inclusive
    Symbols with price=10.0 (== min_price) and price=500.0 (== max_price). Assert both included.

7.  test_scan_respects_max_symbols_returned
    gainers returns 20 symbols, all passing price filter. config.max_symbols_returned=15.
    Assert len(result) == 15.

8.  test_scan_sets_scan_source_to_fmp
    Any successful scan result. Assert all items have scan_source == "fmp".

9.  test_scan_sets_selection_reason_gap_up
    Gainer with changesPercentage=3.25. Assert selection_reason == "gap_up_3.2%".

10. test_scan_sets_selection_reason_gap_down
    Loser with changesPercentage=-1.84. Assert selection_reason == "gap_down_1.8%".

11. test_scan_sets_selection_reason_high_volume
    Symbol only in actives endpoint. Assert selection_reason == "high_volume".

12. test_scan_fallback_on_api_error
    aiohttp.ClientSession raises aiohttp.ClientError. Assert result equals
    fallback_symbols (with scan_source="fmp_fallback").

13. test_scan_fallback_on_empty_response
    All three endpoints return []. Assert result equals fallback_symbols.

14. test_start_raises_on_missing_api_key
    FMP_API_KEY not set in environment. Assert start() raises RuntimeError.

15. test_start_succeeds_with_api_key
    FMP_API_KEY="test_key" set in environment. Assert start() completes without exception
    and self._api_key == "test_key".

## Constraints
- Do NOT modify: DatabentoScanner, AlpacaScanner, StaticScanner
- Do NOT modify: any strategy files, Risk Manager, Orchestrator
- Do NOT use httpx (it's dev-only) — use aiohttp for production HTTP
- Do NOT add Pydantic to FMPScannerConfig — follow DatabentoScannerConfig pattern (plain class)
- FMP_API_KEY must be read from environment at start(), not hardcoded anywhere
- Do NOT attempt to filter by volume — these endpoints do not return volume data

## Test Targets
- Run: pytest tests/data/test_fmp_scanner.py -v
- Run: pytest tests/ -x -q (full suite — must still pass)
- Minimum new tests: 15

## Definition of Done
- [ ] WatchlistItem in events.py has scan_source and selection_reason (defaults = "")
- [ ] argus/data/fmp_scanner.py exists with FMPScannerConfig + FMPScannerSource
- [ ] FMPScannerSource implements Scanner ABC (scan, start, stop)
- [ ] All 15 new tests pass
- [ ] Full test suite passes (1,737 + ~15 new)
- [ ] ruff check passes

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| WatchlistItem backward compat | pytest tests/core/ tests/data/ -q |
| Scanner ABC compliance | FMPScannerSource passes isinstance(scanner, Scanner) |
| No imports from new file in existing files | grep -r fmp_scanner argus/ (should be 0 hits) |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.