---BEGIN-CLOSE-OUT---

**Session:** Sprint 27 S2 — HistoricalDataFeed
**Date:** 2026-03-22
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/backtest/historical_data_feed.py | added | Core deliverable: HistoricalDataFeed class with download, load, cache, cost validation |
| tests/backtest/test_historical_data_feed.py | added | 15 tests covering all spec requirements |

### Judgment Calls
- Used `{YYYY}-{MM}.parquet` naming (not `{SYMBOL}_{YYYY}-{MM}.parquet` from data_fetcher.py) to match prompt spec exactly (`{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`). The two modules use separate cache directories so there's no conflict.
- `_download_month()` catches "not found" / "no data" strings in exceptions to distinguish symbol-not-found from hard API errors. This is a heuristic but matches the Databento error patterns.
- TestMonthRangeGeneration contains 4 sub-test methods (single, multi, cross-year, same-day) for thorough coverage of edge cases, bringing total test count to 15.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| HistoricalDataFeed class with __init__, download, load, get_cached_months, _month_range | DONE | historical_data_feed.py |
| HistoricalDataFeedError exception | DONE | historical_data_feed.py:29 |
| Download with Databento client (lazy init) | DONE | _db_client property, _download_month() |
| Cost validation — zero passes, nonzero raises | DONE | _download_month() cost check block |
| Cost validation — exception raises (AR-3) | DONE | _download_month() except block re-raises as HistoricalDataFeedError |
| verify_zero_cost=False skips check | DONE | _download_month() `if self._verify_zero_cost` guard |
| Parquet cache: {cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet | DONE | _parquet_path() |
| Cache hit skips download | DONE | download() checks cached set |
| Incremental updates | DONE | download() compares needed vs cached months |
| Load with trading_date (ET), UTC timestamps, date range filter | DONE | load() |
| Empty DataFrame with correct schema for missing data | DONE | load() empty path |
| normalize_databento_df imported from databento_utils | DONE | import at top of file |
| Lazy Databento client creation | DONE | _db_client property |
| 12+ new tests | DONE | 15 tests (12 spec + 3 bonus month_range edge cases) |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| data_fetcher.py unchanged | PASS | `git diff HEAD argus/backtest/data_fetcher.py` → empty |
| databento_utils.py unchanged | PASS | `git diff HEAD argus/data/databento_utils.py` → empty |
| No production files modified | PASS | `git diff HEAD argus/core/ argus/strategies/ argus/api/ argus/ui/` → empty |

### Test Results
- Tests run: 2,953
- Tests passed: 2,953
- Tests failed: 0
- New tests added: 15
- Command used: `python -m pytest --ignore=tests/test_main.py -n auto -q`
- Scoped command: `python -m pytest tests/backtest/test_historical_data_feed.py -x -q` (15 passed)

### Unfinished Work
None

### Notes for Reviewer
- Verify cost validation is fail-closed: any exception from get_cost() raises HistoricalDataFeedError (AR-3 compliance).
- Verify verify_zero_cost=False completely bypasses the cost check (no get_cost call).
- The `_download_month()` method uses string matching on exception messages to detect "not found" symbols. This is acceptable for the Databento API but fragile if error messages change.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "27",
  "session": "S2",
  "verdict": "COMPLETE",
  "tests": {
    "before": 2938,
    "after": 2953,
    "new": 15,
    "all_pass": true
  },
  "files_created": [
    "argus/backtest/historical_data_feed.py",
    "tests/backtest/test_historical_data_feed.py"
  ],
  "files_modified": [],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Used {YYYY}-{MM}.parquet naming per prompt spec (differs from data_fetcher's {SYMBOL}_{YYYY}-{MM}.parquet convention but uses separate cache directory). 15 tests written (3 over minimum). All Databento interactions mocked."
}
```
