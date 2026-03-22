# Sprint 27, Session 5: BacktestEngine — Multi-Day Orchestration + Scanner + Results + CLI

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` (S4 output — single-day execution works)
   - `argus/backtest/metrics.py` (compute_metrics — reuse for results)
   - `argus/backtest/scanner_simulator.py` (ScannerSimulator — reuse for watchlists)
   - `argus/backtest/replay_harness.py` (reference: lines 104-161 for run() flow, 706-750 for _compute_results/_empty_result, 768-886 for CLI)
   - `docs/sprints/sprint-27/design-summary.md`
2. Run the test baseline (DEC-328 — Session 2+, scoped):
   ```bash
   python -m pytest tests/backtest/test_engine.py -x -q
   ```
   Expected: all passing (S4 close-out confirmed)
3. Verify you are on the correct branch: `main`

## Objective
Complete the BacktestEngine with multi-day orchestration loop, scanner simulation for watchlist generation, results computation via existing compute_metrics(), engine metadata recording (AR-1), and CLI entry point.

## Requirements

1. **Implement `run()` method in `argus/backtest/engine.py`:**
   Follow ReplayHarness.run() pattern (lines 104-161):
   ```
   a. Log start info
   b. Load data (via HistoricalDataFeed or from pre-loaded bar_data)
   c. If no trading days → return _empty_result()
   d. Initialize all components via _setup()
   e. Pre-compute watchlists via ScannerSimulator
   f. For each trading day:
      i.  Call _run_trading_day(day, watchlist)
      ii. Log progress every 20 days
   g. Compute results via _compute_results()
   h. Teardown
   i. Log completion summary
   j. Return BacktestResult
   ```

2. **Scanner integration:**
   - Create `ScannerSimulator` with config params (min_gap_pct, min_price, max_price, fallback)
   - Call `scanner.compute_watchlists(bar_data, trading_days)` to get per-day watchlists
   - Pass watchlist to `_run_trading_day()` per day

3. **Results computation:**
   - Call `compute_metrics()` from `argus/backtest/metrics.py` with trade_logger, strategy_id, dates, capital, trading_days
   - Same as ReplayHarness._compute_results() (lines 706-718)

4. **Engine metadata recording (AR-1):**
   After computing results, record metadata in the output database:
   - Add a `backtest_metadata` table (or write to an existing metadata mechanism) with:
     - `engine_type`: `"backtest_engine"`
     - `fill_model`: `"bar_level_worst_case"`
     - `strategy_type`: config.strategy_type value
     - `start_date`, `end_date`: from config
     - `symbol_count`: number of symbols processed
     - `run_timestamp`: current UTC time
   - If adding a table is complex, an alternative is writing a JSON metadata file alongside the SQLite DB: `{db_path}.meta.json`

5. **CLI entry point (`python -m argus.backtest.engine`):**
   Follow ReplayHarness CLI pattern (lines 768-886):
   ```python
   def parse_args():
       parser = argparse.ArgumentParser(description="Argus BacktestEngine")
       parser.add_argument("--strategy", type=str, required=True,
                           choices=[e.value for e in StrategyType])
       parser.add_argument("--start", type=date.fromisoformat, required=True)
       parser.add_argument("--end", type=date.fromisoformat, required=True)
       parser.add_argument("--symbols", type=str, default=None,
                           help="Comma-separated symbols (default: all cached)")
       parser.add_argument("--cache-dir", default="data/databento_cache")
       parser.add_argument("--output-dir", default="data/backtest_runs")
       parser.add_argument("--initial-cash", type=float, default=100_000.0)
       parser.add_argument("--slippage", type=float, default=0.01)
       parser.add_argument("--no-cost-check", action="store_true")
       parser.add_argument("--log-level", default="WARNING",
                           choices=["DEBUG", "INFO", "WARNING", "ERROR"])
       parser.add_argument("--config-override", action="append", default=[])
       parser.add_argument("-v", "--verbose", action="store_true")
       return parser.parse_args()

   def main():
       args = parse_args()
       # Configure logging with args.log_level (or DEBUG if verbose)
       # Build BacktestEngineConfig from args
       # Run engine via asyncio.run()
       # Print summary results to stdout
   ```

6. **Add `if __name__ == "__main__": main()` block**

7. **Known limitation docstring (AR-2):**
   Add to the BacktestEngine class docstring:
   ```
   Note: The bar-level fill model is least accurate for strategies with risk
   parameters smaller than the typical 1-minute bar range (e.g., ORB Scalp
   with 0.3R target). For these strategies, the Replay Harness with tick
   synthesis provides higher-fidelity results.
   ```

## Constraints
- Do NOT modify: `argus/backtest/metrics.py`, `argus/backtest/scanner_simulator.py`, `argus/backtest/replay_harness.py`
- Do NOT change: _setup(), _run_trading_day(), _check_bracket_orders() from S3/S4
- Do NOT add: any frontend or API endpoint code

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/backtest/test_engine.py` (extend):
  1. `test_run_multi_day` — 5 trading days, verify each day processed (trade count or log)
  2. `test_daily_state_reset_across_days` — verify strategy/RM/OM/DS reset between days
  3. `test_scanner_generates_watchlists` — ScannerSimulator called, watchlists used per day
  4. `test_results_computed` — BacktestResult has valid fields after run
  5. `test_empty_data_returns_empty_result` — no trading days → BacktestResult with 0 trades
  6. `test_end_to_end_orb_breakout` — ORB Breakout on 1-month mocked data → trades > 0
  7. `test_end_to_end_no_signals` — strategy with no matching setups → 0 trades, no error
  8. `test_db_output_created` — SQLite file exists at expected path with DEC-056 naming
  9. `test_metadata_recorded` — engine_type and fill_model present in output (AR-1)
  10. `test_cli_parse_args` — parse_args handles all required flags correctly
  11. `test_cli_main_runs` — main() with mocked data completes without error
  12. `test_log_level_config` — WARNING level suppresses debug, INFO level enables info
  13. `test_progress_logging` — progress logged every 20 days (verify log output)
  14. `test_config_overrides_applied` — strategy parameter overrides reflected in strategy config
  15. `test_symbols_filter` — only specified symbols processed when symbols list provided
- Minimum new test count: 15
- Test command (scoped): `python -m pytest tests/backtest/test_engine.py -x -q`

## Definition of Done
- [ ] run() orchestrates multi-day execution with scanner watchlists
- [ ] Results computed via compute_metrics()
- [ ] Engine metadata recorded in output (AR-1)
- [ ] CLI entry point works: `python -m argus.backtest.engine --strategy orb --start 2024-01-01 --end 2024-01-31`
- [ ] Known limitation documented in class docstring (AR-2)
- [ ] All existing tests pass
- [ ] 15 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| metrics.py unchanged | `git diff HEAD argus/backtest/metrics.py` → no changes |
| scanner_simulator.py unchanged | `git diff HEAD argus/backtest/scanner_simulator.py` → no changes |
| Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |

## Close-Out
Write to: docs/sprints/sprint-27/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27/review-context.md`
2. Close-out: `docs/sprints/sprint-27/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/backtest/test_engine.py -x -q`
5. Do-not-modify: `argus/backtest/metrics.py`, `argus/backtest/scanner_simulator.py`, `argus/backtest/replay_harness.py`

@reviewer writes to: docs/sprints/sprint-27/session-5-review.md

## Session-Specific Review Focus (for @reviewer)
1. Verify run() follows ReplayHarness.run() flow (load → setup → loop → compute → teardown)
2. Verify ScannerSimulator is used for watchlist generation (not hardcoded symbols)
3. Verify engine metadata is written to output (AR-1): engine_type and fill_model
4. Verify CLI argument parsing covers all BacktestEngineConfig fields
5. Verify known limitation docstring is present (AR-2)
6. Verify _empty_result() is used for zero-data case

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` |
| R4 | All VectorBT files unchanged | `git diff HEAD argus/backtest/vectorbt_*.py` |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` |
| R15 | ScannerSimulator unchanged | `git diff HEAD argus/backtest/scanner_simulator.py` |
| R16 | compute_metrics() unchanged | `git diff HEAD argus/backtest/metrics.py` |

## Sprint-Level Escalation Criteria (for @reviewer)
2. Bar-level fill model produces clearly incorrect results.
6. BacktestEngine is slower than the Replay Harness on equivalent data.
9. Any existing backtest test fails.
