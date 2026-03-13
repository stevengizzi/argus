# Sprint 24, Session 3: Close-Out Report

## Session Summary
Implemented DEC-327 Firehose Source Refactoring. Finnhub and SEC EDGAR sources now support
a `firehose: bool = False` parameter on `fetch_catalysts()`, enabling single-call market-wide
fetching. Per-symbol mode is unchanged.

## Change Manifest

| File | Change |
|------|--------|
| `argus/intelligence/sources/__init__.py` | Added `firehose: bool = False` to `CatalystSource.fetch_catalysts()` abstract signature |
| `argus/intelligence/sources/fmp_news.py` | Added `firehose: bool = False` param; returns `[]` when `firehose=True` (no FMP endpoint) |
| `argus/intelligence/sources/finnhub.py` | Added `_fetch_general_news()`, `_associate_symbols()`, modified `fetch_catalysts()` |
| `argus/intelligence/sources/sec_edgar.py` | Added `_EFTS_SEARCH_URL`, `_fetch_recent_filings_firehose()`, `_parse_firehose_filings()`, modified `fetch_catalysts()` |
| `tests/intelligence/test_sources/test_finnhub.py` | Added `TestFinnhubFirehose` class with 9 new tests |
| `tests/intelligence/test_sources/test_sec_edgar.py` | Added `TestSECEdgarFirehose` class with 8 new tests |

## Definition of Done Verification

- [x] Finnhub firehose makes 1 API call for general news — `_fetch_general_news()` calls `/news?category=general` once
- [x] SEC EDGAR firehose makes 1 API call for recent filings — `_fetch_recent_filings_firehose()` calls EFTS search-index once
- [x] Symbol association works correctly for both sources — `_associate_symbols()` splits `related` field; EFTS CIK reverse lookup
- [x] Per-symbol mode unchanged — existing tests pass, new per-symbol regression tests added
- [x] All existing tests pass — 146 intelligence tests pass (was 107 pre-session)
- [x] 16+ new tests passing — 17 new targeted firehose tests added

## Judgment Calls

1. **`_fetch_general_news` calls `_associate_symbols` internally** — Spec said "call `_fetch_general_news()` + `_associate_symbols()`" in firehose path. Cleaner to have `_fetch_general_news` orchestrate `_associate_symbols` so `fetch_catalysts` is unaware of the symbol-splitting detail. Tests verify both methods independently.

2. **FMPNewsClient returns `[]` for `firehose=True`** — Spec says "FMPNewsSource ignores this parameter (returns empty list when called with firehose=True)." Implemented as explicit early return to avoid unnecessary per-symbol work.

3. **SEC EDGAR `_parse_firehose_filings` is a separate method** — Makes the EFTS parsing independently testable without making live HTTP calls.

4. **Reverse CIK map built inline in `_fetch_recent_filings_firehose`** — Built per-call from `_cik_map`. Acceptable because firehose is called infrequently (once per polling cycle), not in a tight loop.

## Regression Checklist

| Check | Result |
|-------|--------|
| Per-symbol mode unchanged | All pre-existing intelligence tests pass (107 → 146 total, 0 failures) |
| CatalystClassifier not modified | `git diff argus/intelligence/classifier.py` — empty |
| CatalystStorage not modified | `git diff argus/intelligence/storage.py` — empty |
| CatalystRawItem model not modified | `git diff argus/intelligence/models.py` — empty |
| Core/strategy tests unaffected | 644 tests pass in core/ + strategies/ |

## Test Results

```
tests/intelligence/: 146 passed (was 107 pre-session, +39 net including 17 firehose-specific)
tests/core/ + tests/strategies/: 644 passed
```

## Self-Assessment

**CLEAN** — All spec items implemented. 17 new firehose-specific tests (exceeds 16 minimum).
Per-symbol behavior unchanged. No prohibited files modified. No scope expansion.

## Context State

GREEN — Session completed well within context limits.
