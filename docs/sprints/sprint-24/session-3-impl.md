# Sprint 24, Session 3: DEC-327 Firehose Source Refactoring

## Pre-Flight Checks
1. Read: `argus/intelligence/sources/finnhub.py`, `argus/intelligence/sources/sec_edgar.py`, `argus/intelligence/models.py`, `argus/intelligence/config.py`
2. Scoped test: `python -m pytest tests/intelligence/ -x -q`
3. Branch: `sprint-24`

## Objective
Refactor Finnhub and SEC EDGAR sources from per-symbol polling to feed-level firehose pulls. Add `firehose: bool` parameter to `fetch_catalysts()`. Retain per-symbol methods unchanged.

## Requirements

### 1. In `argus/intelligence/sources/finnhub.py`:

Add `_fetch_general_news(fetch_time) -> list[CatalystRawItem]`:
- `GET {BASE_URL}/news?category=general&token={api_key}`
- Returns last 24h of market-wide news in one call
- Rate-limited via existing `_make_rate_limited_request()`

Add `_associate_symbols(items: list[dict], fetch_time) -> list[CatalystRawItem]`:
- Each Finnhub news item has a `related` field (comma-separated tickers)
- Split `related` into individual symbols, create one CatalystRawItem per (item, symbol) pair
- Items with empty/missing `related` → CatalystRawItem with `symbol=""`

Modify `fetch_catalysts()` signature: `async def fetch_catalysts(self, symbols: list[str], firehose: bool = False) -> list[CatalystRawItem]`
- When `firehose=True`: call `_fetch_general_news()` + `_associate_symbols()`. Skip per-symbol company news. Still fetch recommendations per-symbol (no firehose endpoint for those).
- When `firehose=False`: existing per-symbol behavior unchanged.

### 2. In `argus/intelligence/sources/sec_edgar.py`:

Add `_fetch_recent_filings_firehose(fetch_time) -> list[CatalystRawItem]`:
- `GET https://efts.sec.gov/LATEST/search-index?dateRange=custom&startdt={yesterday}&forms=8-K,4`
- Parse response, extract filing metadata (form type, filed date, company CIK, description)
- Map CIK → ticker via existing `_cik_map` (reverse lookup)
- Filings for CIKs not in map → CatalystRawItem with `symbol=""`
- SEC fair-access User-Agent header required

Modify `fetch_catalysts()` signature: add `firehose: bool = False`
- When `firehose=True`: call `_fetch_recent_filings_firehose()`. Skip per-CIK loop.
- When `firehose=False`: existing behavior unchanged.

### 3. Update `CatalystSource` ABC:
Add `firehose: bool = False` to the `fetch_catalysts()` signature in the abstract base class. `FMPNewsSource` ignores this parameter (returns empty list when called with firehose=True, same as current disabled behavior).

## Constraints
- Do NOT modify: `argus/intelligence/sources/fmp_news.py` (beyond making it accept the new parameter), `argus/intelligence/classifier.py`, `argus/intelligence/storage.py`, `argus/intelligence/models.py`
- Do NOT change: existing per-symbol behavior when firehose=False

## Test Targets
- `test_finnhub_firehose_single_api_call`: Mock `/news?category=general`, verify 1 call made
- `test_finnhub_firehose_symbol_association`: Items with `related: "AAPL,MSFT"` → 2 CatalystRawItems
- `test_finnhub_firehose_no_related_field`: Item stored with symbol=""
- `test_finnhub_per_symbol_still_works`: firehose=False → existing behavior
- `test_finnhub_firehose_recommendations_still_per_symbol`: Recommendations fetched per-symbol even in firehose mode
- `test_sec_edgar_firehose_single_api_call`: Mock EFTS search, verify 1 call
- `test_sec_edgar_firehose_cik_mapping`: Filing with known CIK → correct ticker
- `test_sec_edgar_firehose_unknown_cik`: Filing with unknown CIK → symbol=""
- `test_sec_edgar_per_symbol_still_works`: firehose=False → existing behavior
- `test_catalyst_source_abc_firehose_param`: ABC accepts firehose parameter
- Edge cases: empty response, API error, rate limiting
- Minimum new test count: 16
- Test command: `python -m pytest tests/intelligence/ -x -q`

## Definition of Done
- [ ] Finnhub firehose makes 1 API call for general news
- [ ] SEC EDGAR firehose makes 1 API call for recent filings
- [ ] Symbol association works correctly for both sources
- [ ] Per-symbol mode unchanged
- [ ] All existing tests pass
- [ ] 16+ new tests passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Per-symbol mode unchanged | Existing intelligence tests pass |
| CatalystClassifier not modified | `git diff argus/intelligence/classifier.py` empty |
| CatalystStorage not modified | `git diff argus/intelligence/storage.py` empty |

## Close-Out
Write report to `docs/sprints/sprint-24/session-3-closeout.md`.

## Sprint-Level Regression Checklist & Escalation Criteria
*(See review-context.md)*
