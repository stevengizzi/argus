# Sprint 27, Session 2: HistoricalDataFeed

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/data_fetcher.py` (existing Databento download pattern — reference, lines ~441–500 for `fetch_symbol_month_databento()`)
   - `argus/data/databento_utils.py` (normalize_databento_df — reuse this)
   - `argus/backtest/config.py` (DataFetcherConfig for cache path conventions, BacktestEngineConfig from S1)
   - `docs/sprints/sprint-27/design-summary.md`
2. Run the test baseline (DEC-328 — Session 2+, scoped):
   ```bash
   python -m pytest tests/backtest/test_config.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on the correct branch: `main`

## Objective
Build the HistoricalDataFeed — a module that downloads Databento OHLCV-1m data, validates zero cost, caches as Parquet files, supports incremental updates, and provides a clean API for loading historical bar data for any symbol set and date range.

## Requirements

1. **Create `argus/backtest/historical_data_feed.py`:**

   Class `HistoricalDataFeed` with the following interface:

   ```python
   class HistoricalDataFeed:
       """Downloads and caches Databento OHLCV-1m historical data.

       Data is cached as Parquet files: {cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet
       Incremental updates download only missing months.
       Cost validation ensures $0.00 before every download (DEC-353).
       """

       def __init__(self, cache_dir: Path, dataset: str = "EQUS.MINI",
                    verify_zero_cost: bool = True):
           ...

       async def download(self, symbols: list[str], start_date: date,
                          end_date: date) -> dict[str, Path]:
           """Download OHLCV-1m data for symbols in date range.

           Checks cache first. Downloads only missing symbol-months.
           Returns mapping of symbol → cache directory path.
           """

       async def load(self, symbols: list[str], start_date: date,
                      end_date: date) -> dict[str, pd.DataFrame]:
           """Load cached data for symbols in date range.

           Returns mapping of symbol → DataFrame with columns:
           [timestamp, open, high, low, close, volume, trading_date]
           timestamp is UTC-aware. trading_date is ET date.
           """

       def get_cached_months(self, symbol: str) -> list[tuple[int, int]]:
           """Return list of (year, month) tuples cached for a symbol."""

       def _month_range(self, start_date: date, end_date: date) -> list[tuple[int, int]]:
           """Generate list of (year, month) tuples in date range."""
   ```

2. **Download implementation:**
   - Use `databento.Historical` client (same pattern as `data_fetcher.py` line ~220)
   - API key from `DATABENTO_API_KEY` environment variable
   - For each symbol-month not in cache:
     a. Call `client.metadata.get_cost(dataset=self._dataset, symbols=[symbol], schema="ohlcv-1m", start=month_start, end=month_end)` — this returns cost in dollars
     b. **If cost > 0.00 or get_cost() raises any exception (AR-3):** raise `HistoricalDataFeedError(f"Cost validation failed for {symbol} {year}-{month}: {reason}. Set verify_zero_cost=False to bypass.")`
     c. If `verify_zero_cost` is False, skip the cost check entirely
     d. Call `client.timeseries.get_range(dataset=self._dataset, symbols=[symbol], schema="ohlcv-1m", start=month_start, end=month_end)`
     e. Convert to DataFrame via `.to_df()`, normalize via `normalize_databento_df()`
     f. Save as Parquet to `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`
   - Log progress: "Downloading {symbol} {year}-{month}..." and "Cached {symbol} {year}-{month} ({N} bars)"

3. **Cache implementation:**
   - Directory structure: `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet` (matching `data_fetcher.py` convention at line ~424)
   - Create directories as needed (`mkdir(parents=True, exist_ok=True)`)
   - Cache check: `Path.exists()` on expected Parquet path
   - `get_cached_months()`: list parquet files in symbol directory, parse filenames

4. **Load implementation:**
   - Read Parquet files for requested symbol-months
   - Concatenate, sort by timestamp
   - Add `trading_date` column (ET date from timestamp, same as replay_harness.py line 218)
   - Filter to requested date range
   - Return empty DataFrame (with correct columns) for symbols with no data

5. **Error handling:**
   - Custom `HistoricalDataFeedError` exception class
   - Symbol not found in Databento → log warning, skip symbol, continue
   - Empty result for a symbol-month → log info, write empty Parquet (prevents re-download)
   - API connection failure → raise with clear message

## Constraints
- Do NOT modify: `argus/backtest/data_fetcher.py`, `argus/data/databento_utils.py`, any production files
- Do NOT use: live Databento API in tests (mock the client)
- Do NOT create: any Databento client at module import time (lazy creation on first use)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/backtest/test_historical_data_feed.py`:
  1. `test_download_caches_parquet` — mocked client, verify Parquet file created
  2. `test_cache_hit_skips_download` — pre-existing Parquet, verify no API call
  3. `test_incremental_download` — 3 months requested, 1 cached, verify 2 downloaded
  4. `test_cost_validation_zero_passes` — get_cost returns 0.0, download proceeds
  5. `test_cost_validation_nonzero_raises` — get_cost returns 5.0, HistoricalDataFeedError raised
  6. `test_cost_validation_exception_raises` — get_cost raises network error, HistoricalDataFeedError raised (AR-3)
  7. `test_verify_zero_cost_false_skips_check` — verify_zero_cost=False, no get_cost call
  8. `test_load_returns_normalized_dataframe` — correct columns, UTC timestamps, trading_date
  9. `test_load_filters_date_range` — data outside range excluded
  10. `test_load_empty_symbol` — symbol with no data returns empty DataFrame with correct schema
  11. `test_symbol_not_found_skips` — Databento returns empty, logged, other symbols continue
  12. `test_month_range_generation` — _month_range produces correct (year, month) list
- Minimum new test count: 12
- Test command (scoped): `python -m pytest tests/backtest/test_historical_data_feed.py -x -q`

## Definition of Done
- [ ] `argus/backtest/historical_data_feed.py` created with HistoricalDataFeed class
- [ ] HistoricalDataFeedError exception defined
- [ ] All existing tests pass
- [ ] 12 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| data_fetcher.py unchanged | `git diff HEAD argus/backtest/data_fetcher.py` → no changes |
| databento_utils.py unchanged | `git diff HEAD argus/data/databento_utils.py` → no changes |
| No production files modified | `git diff HEAD argus/core/ argus/strategies/ argus/api/ argus/ui/` → no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
docs/sprints/sprint-27/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-27/review-context.md`
2. The close-out report path: `docs/sprints/sprint-27/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/backtest/test_historical_data_feed.py -x -q`
5. Files that should NOT have been modified: `argus/backtest/data_fetcher.py`, `argus/data/databento_utils.py`, `argus/core/`, `argus/strategies/`

The @reviewer writes to: docs/sprints/sprint-27/session-2-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix findings within this session,
update both close-out and review files per template instructions.

## Session-Specific Review Focus (for @reviewer)
1. Verify cost validation is fail-closed: if get_cost() raises ANY exception, download halts (AR-3)
2. Verify verify_zero_cost=False completely skips the cost check (no get_cost call at all)
3. Verify Parquet cache path convention matches: `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`
4. Verify normalize_databento_df() is imported from argus.data.databento_utils (not reimplemented)
5. Verify Databento client is lazy-created (not at __init__ or import time)
6. Verify no live API calls in tests (all Databento interactions mocked)

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Production EventBus unchanged | `git diff HEAD argus/core/event_bus.py` → no changes |
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` → no changes |
| R8 | No system.yaml changes | `git diff HEAD config/system.yaml config/system_live.yaml` → no changes |

## Sprint-Level Escalation Criteria (for @reviewer)
4. Databento `metadata.get_cost()` returns non-zero for OHLCV-1m on EQUS.MINI (if any live validation was attempted).
9. Any existing backtest test fails.
10. Session compaction occurs before completing core deliverables.
