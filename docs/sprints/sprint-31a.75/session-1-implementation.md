# Sprint 31A.75, Session 1: Universe-Aware Sweep Flags (Sweep Tooling Impromptu)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `scripts/run_experiment.py`
   - `argus/intelligence/experiments/runner.py` (confirm `run_sweep()` accepts `symbols` param)
   - `argus/data/historical_query_service.py` (confirm `validate_symbol_coverage()` and `get_available_symbols()` exist)
   - `argus/data/historical_query_config.py`
   - `argus/core/config.py` (find `UniverseFilterConfig`)
   - `config/universe_filters/narrow_range_breakout.yaml` (example filter)
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest tests/ -x -q --tb=short -n auto`
   Expected: ~4811 tests, all passing
3. Verify you are on the correct branch: `main` (or create `feat/sprint-31A.75`)

## Objective
Add `--symbols` and `--universe-filter` CLI flags to `scripts/run_experiment.py`
so that parameter sweeps can target specific symbol populations instead of the
full 24,321-symbol Parquet cache. Wire `HistoricalQueryService.validate_symbol_coverage()`
into the flow to eliminate symbols without sufficient cache data. Resolves DEF-145.

## Requirements

### 1. Add `--symbols` argument to `parse_args()` in `scripts/run_experiment.py`

- Type: `str`, default `None`
- Help: `"Comma-separated symbol list OR @filepath (one symbol per line)"`
- Add a helper function `_parse_symbols(raw: str) -> list[str]` in the script:
  - If `raw` starts with `@`: treat remainder as file path, read lines, strip
    whitespace, filter empty lines, uppercase each symbol
  - Else: split on comma, strip whitespace, uppercase each symbol
  - Return deduplicated list (preserve order via `dict.fromkeys()`)

### 2. Add `--universe-filter` argument to `parse_args()`

- Type: `str`, default `None`, use `nargs='?'` with `const='__from_pattern__'`
- Help: `"Pattern name to load universe filter from config/universe_filters/{name}.yaml. If flag used without value, defaults to --pattern value."`
- Add a helper function `_load_universe_filter(filter_name: str) -> UniverseFilterConfig`:
  - Resolve path: `config/universe_filters/{filter_name}.yaml`
  - If file doesn't exist: raise `SystemExit` with clear error message listing
    available filter files from `config/universe_filters/`
  - Load YAML, parse into `UniverseFilterConfig` (import from `argus.core.config`)
  - Return the config

### 3. Add a helper function `_apply_universe_filter()` in `scripts/run_experiment.py`

```python
def _apply_universe_filter(
    filter_config: UniverseFilterConfig,
    cache_dir: str,
    start_date: str,
    end_date: str,
    candidate_symbols: list[str] | None = None,
) -> list[str]:
```

This function:
1. Creates a `HistoricalQueryService` from `HistoricalQueryConfig(enabled=True, cache_dir=cache_dir)`
2. If the service is not available (`is_available` is False): print ERROR and `sys.exit(1)`
3. Builds a DuckDB filter query against the `historical` VIEW:
   ```sql
   SELECT symbol, AVG(close) AS avg_price, AVG(volume) AS avg_volume
   FROM historical
   WHERE date >= ? AND date <= ?
   GROUP BY symbol
   HAVING 1=1
   ```
   - If `filter_config.min_price` is not None: append `AND AVG(close) >= {min_price}`
   - If `filter_config.max_price` is not None: append `AND AVG(close) <= {max_price}`
   - If `filter_config.min_avg_volume` is not None: append `AND AVG(volume) >= {min_avg_volume}`
   - Use string formatting for the HAVING clauses (these are operator-controlled
     config values, not user input — safe from injection). The date params use `?`
     placeholders via `service.query(sql, params)`.
4. If `candidate_symbols` is not None: add `AND symbol IN (...)` clause to the
   WHERE to restrict to only those symbols (intersection behavior)
5. Log dynamic filters that are present but skipped:
   - `min_relative_volume`, `min_gap_percent`, `min_premarket_volume`,
     `min_market_cap`, `max_market_cap`, `min_float`, `sectors`, `exclude_sectors`
   - Log at WARNING: `"Skipping dynamic filter '{name}' (not applicable to historical sweeps)"`
   - Only log for filters that have non-None / non-empty values
6. Execute the query, extract symbol list from result DataFrame
7. Close the `HistoricalQueryService` (call `.close()`)
8. Return sorted symbol list

### 4. Add coverage validation helper `_validate_coverage()` in `scripts/run_experiment.py`

```python
def _validate_coverage(
    symbols: list[str],
    cache_dir: str,
    start_date: str,
    end_date: str,
    min_bars: int = 100,
) -> list[str]:
```

This function:
1. Creates a `HistoricalQueryService` (or reuse pattern — accept service as param
   if cleaner)
2. Calls `service.validate_symbol_coverage(symbols, start_date, end_date, min_bars)`
3. Separates passed/failed symbols
4. Logs: `"Coverage validation: {passed}/{total} symbols have sufficient data ({min_bars}+ bars)"`
5. For failed symbols: log WARNING with up to 20 symbol names, then `"... and {N} more"` if > 20
6. Closes the service
7. Returns list of passed symbols only

### 5. Wire the filtering pipeline in `run()` async function

In `scripts/run_experiment.py`, modify the `run()` function after date range
parsing but before the `runner.run_sweep()` call. Add this pipeline:

```python
# --- Symbol filtering pipeline ---
symbols: list[str] | None = None

# Layer 1: --symbols flag
if args.symbols:
    symbols = _parse_symbols(args.symbols)
    print(f"Symbols from --symbols: {len(symbols)}")

# Layer 2: --universe-filter flag
filter_name = args.universe_filter
if filter_name == "__from_pattern__":
    filter_name = args.pattern

if filter_name is not None:
    filter_config = _load_universe_filter(filter_name)
    filtered = _apply_universe_filter(
        filter_config=filter_config,
        cache_dir=cache_dir,
        start_date=start_date_str,
        end_date=end_date_str,
        candidate_symbols=symbols,  # None if --symbols not provided
    )
    symbols = filtered
    print(f"Symbols after universe filter '{filter_name}': {len(symbols)}")

# Layer 3: Coverage validation
if symbols is not None:
    symbols = _validate_coverage(
        symbols=symbols,
        cache_dir=cache_dir,
        start_date=start_date_str,
        end_date=end_date_str,
    )
    print(f"Symbols after coverage validation: {len(symbols)}")
    if not symbols:
        print("ERROR: No symbols remaining after filtering. Aborting.")
        return 1
```

**Important:** The date range needs to be resolved before the filtering pipeline.
Currently `_resolve_date_range()` is called inside `run_sweep()`. You need to
resolve dates earlier in `run()` so they're available for the filter queries.
Extract the date resolution to happen before the filtering pipeline:

```python
# Resolve dates early (needed for symbol filtering)
config = load_config()
config_dict = config.model_dump()
# ... existing code ...

# Resolve date range for filtering (mirrors runner._resolve_date_range logic)
if args.date_range:
    parts = args.date_range.split(",")
    start_date_str, end_date_str = parts[0].strip(), parts[1].strip()
elif config.backtest_start_date and config.backtest_end_date:
    start_date_str = str(config.backtest_start_date)
    end_date_str = str(config.backtest_end_date)
else:
    start_date_str, end_date_str = None, None

# ... filtering pipeline uses start_date_str/end_date_str ...
# For --universe-filter and coverage validation, dates are required
```

If `--universe-filter` is used but no date range is available, print ERROR and exit 1.
Coverage validation also needs dates — skip it if dates are None (symbols will be
passed through unvalidated).

### 6. Pass filtered symbols to `run_sweep()`

Change the `runner.run_sweep()` call to pass the filtered symbol list:

```python
records = await runner.run_sweep(
    pattern_name=args.pattern,
    cache_dir=cache_dir,
    param_subset=param_subset,
    date_range=date_range,
    symbols=symbols,  # NEW: filtered symbol list (or None for auto-detect)
    dry_run=False,
)
```

**Verification:** Confirm that `ExperimentRunner.run_sweep()` passes `symbols`
to `BacktestEngineConfig(symbols=symbols, ...)` on line ~312. It should already
do this based on the existing parameter. If not, wire it.

### 7. Update dry-run output

Add symbol information to the dry-run print section:

```python
if args.dry_run:
    if symbols is not None:
        print(f"Symbols: {len(symbols)} (filtered)")
    else:
        print("Symbols: all (auto-detect from cache)")
    # ... existing grid sample output ...
```

### 8. Update CLI help text and epilog

Add new examples to the epilog:

```
  # Sweep using pattern's production universe filter
  python scripts/run_experiment.py --pattern narrow_range_breakout --universe-filter

  # Sweep with a specific universe filter
  python scripts/run_experiment.py --pattern bull_flag --universe-filter hod_break

  # Sweep a specific symbol list
  python scripts/run_experiment.py --pattern bull_flag --symbols AAPL,NVDA,TSLA

  # Sweep from a file (one symbol per line)
  python scripts/run_experiment.py --pattern bull_flag --symbols @symbols.txt

  # Combine: filter from file, then validate coverage
  python scripts/run_experiment.py --pattern bull_flag --symbols @symbols.txt --date-range 2025-01-01,2025-12-31
```

### 9. Add `backtest_start_date` and `backtest_end_date` to `ExperimentConfig` if not already present

Check `argus/intelligence/experiments/config.py`. The `ExperimentConfig` Pydantic
model needs `backtest_start_date: str | None = None` and `backtest_end_date: str | None = None`
fields if they aren't already there. The `run()` function accesses them for date
resolution. If they're already defined (they're used by ExperimentRunner), no change needed.

## Constraints
- Do NOT modify: `argus/data/historical_query_service.py` — use as-is
- Do NOT modify: `argus/backtest/engine.py` — use as-is
- Do NOT modify: `argus/core/config.py` — use as-is (import `UniverseFilterConfig`)
- Do NOT modify: `config/universe_filters/*.yaml` — use as-is
- Do NOT modify: `argus/intelligence/experiments/runner.py` unless `symbols` is not
  being passed through to `BacktestEngineConfig` (verify first; fix only if needed)
- Do NOT modify any production runtime files (anything in `argus/` that runs during
  live/paper trading)
- Default behavior (no new flags) MUST be identical to before (all symbols auto-detected)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/scripts/test_run_experiment_filters.py`:

1. **`test_parse_symbols_comma_separated`**: `_parse_symbols("AAPL,NVDA,TSLA")` → `["AAPL", "NVDA", "TSLA"]`
2. **`test_parse_symbols_with_whitespace`**: `_parse_symbols(" aapl , nvda , tsla ")` → `["AAPL", "NVDA", "TSLA"]`
3. **`test_parse_symbols_from_file`**: Write temp file with symbols, `_parse_symbols("@{path}")` reads correctly
4. **`test_parse_symbols_deduplicates`**: `_parse_symbols("AAPL,NVDA,AAPL")` → `["AAPL", "NVDA"]`
5. **`test_parse_symbols_uppercase`**: `_parse_symbols("aapl,nvda")` → `["AAPL", "NVDA"]`
6. **`test_load_universe_filter_valid`**: loads `narrow_range_breakout` → returns `UniverseFilterConfig` with `min_price=5.0, max_price=200.0, min_avg_volume=300000`
7. **`test_load_universe_filter_missing`**: nonexistent pattern → `SystemExit`
8. **`test_parse_args_symbols_flag`**: `parse_args(["--pattern", "bull_flag", "--symbols", "AAPL,NVDA"])` has correct `.symbols`
9. **`test_parse_args_universe_filter_with_value`**: `parse_args(["--pattern", "bull_flag", "--universe-filter", "hod_break"])` → `.universe_filter == "hod_break"`
10. **`test_parse_args_universe_filter_no_value`**: `parse_args(["--pattern", "bull_flag", "--universe-filter"])` → `.universe_filter == "__from_pattern__"`
11. **`test_parse_args_defaults_unchanged`**: `parse_args(["--pattern", "bull_flag"])` → `.symbols is None`, `.universe_filter is None`

- If feasible without heavy mocking, add integration-style tests for `_apply_universe_filter()`
  and `_validate_coverage()` using a mock `HistoricalQueryService`. If mocking is
  too complex for a CLI script, the unit tests above + manual verification are sufficient.

- Minimum new test count: 11
- Test command: `python -m pytest tests/scripts/test_run_experiment_filters.py -x -q --tb=short`

## Regression Checklist (Session-Specific)
After implementation, verify each of these:

| Check | How to Verify |
|-------|---------------|
| Default behavior unchanged | `python scripts/run_experiment.py --pattern bull_flag --dry-run` works without --symbols or --universe-filter |
| --symbols comma parsing | `python scripts/run_experiment.py --pattern bull_flag --symbols AAPL,NVDA --dry-run` shows "Symbols: 2 (filtered)" |
| --universe-filter flag | `python scripts/run_experiment.py --pattern narrow_range_breakout --universe-filter --dry-run --date-range 2025-01-01,2025-12-31` shows filtered symbol count |
| --help shows new examples | `python scripts/run_experiment.py --help` includes new flag documentation |
| No production files modified | `git diff --name-only` shows only `scripts/run_experiment.py` and test files |
| ExperimentRunner symbols pass-through | Verify `run_sweep()` passes `symbols` to `BacktestEngineConfig` |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass (4811 pytest + 846 Vitest)
- [ ] New tests written and passing (11+ new tests)
- [ ] `--symbols` works with comma-separated list and @filepath
- [ ] `--universe-filter` loads YAML and queries DuckDB
- [ ] `--universe-filter` (no value) defaults to `--pattern` name
- [ ] Coverage validation drops symbols without sufficient data
- [ ] Dynamic filters logged as skipped (not silently ignored)
- [ ] Default behavior (no flags) identical to before
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-31A.75/session-1-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31A.75/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31A.75/session-1-closeout.md`
3. The diff range: `git diff HEAD~1` (or appropriate range)
4. The test command: `python -m pytest tests/ -x -q --tb=short -n auto` (final session — full suite)
5. Files that should NOT have been modified: any file under `argus/` except
   potentially `argus/intelligence/experiments/runner.py` (only if symbols
   pass-through was missing) and `argus/intelligence/experiments/config.py`
   (only if date fields were missing)

The @reviewer will produce its review report (including a structured JSON
verdict fenced with ```json:structured-verdict) and write it to:
`docs/sprints/sprint-31A.75/session-1-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the standard protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `--symbols` parsing handles edge cases: empty file, file with blank lines, duplicate symbols
2. Verify `--universe-filter` DuckDB query uses parameterized dates (not string interpolation for dates)
3. Verify dynamic filters (min_relative_volume, min_gap_percent, etc.) are logged as skipped, NOT silently applied or silently ignored
4. Verify coverage validation correctly drops symbols and logs the drops
5. Verify intersection logic when both `--symbols` and `--universe-filter` are used
6. Verify default behavior (no new flags) produces identical output to before
7. Verify `HistoricalQueryService` is properly closed after use (`.close()` called)
8. Verify no production runtime files were modified

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| Existing CLI behavior preserved | `--pattern bull_flag --dry-run` works unchanged |
| No production runtime modifications | `git diff --name-only` limited to `scripts/` and `tests/` (plus potentially `argus/intelligence/experiments/config.py` or `runner.py` for minor fixes) |
| All tests pass | `python -m pytest tests/ -x -q --tb=short -n auto` |

## Sprint-Level Escalation Criteria (for @reviewer)
- ESCALATE if any production runtime file (`argus/core/`, `argus/execution/`, `argus/data/`, `argus/strategies/`) was modified
- ESCALATE if default CLI behavior (no --symbols, no --universe-filter) changed
- ESCALATE if `BacktestEngine` or `HistoricalQueryService` internals were modified
