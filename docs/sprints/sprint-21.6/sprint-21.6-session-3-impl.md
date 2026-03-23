# Sprint 21.6, Session 3: Re-Validation Harness Script

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/walk_forward.py` — focus on: `WalkForwardConfig` (lines 54–145), `run_fixed_params_walk_forward()` (line 1970+), `_STRATEGY_TYPE_MAP` (lines 740–748), CLI args section (~line 2560+) for fixed-params usage patterns
   - `argus/backtest/config.py` — `BacktestEngineConfig`, `StrategyType` enum
   - `argus/backtest/historical_data_feed.py` — understand Parquet cache format: `{cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet`
   - `config/strategies/orb_breakout.yaml` — baseline example: `backtest_summary` structure and strategy parameter names
   - `config/strategies/vwap_reclaim.yaml` — different strategy param structure for comparison
2. Run scoped test baseline (DEC-328 — Session 3):
   ```
   python -m pytest tests/backtest/ -x -q
   ```
   Expected: all passing
3. Verify you are on branch: `main`

## Objective
Build a CLI script that runs BacktestEngine-based fixed-parameter walk-forward validation for any of the 7 active strategies, compares results against the YAML `backtest_summary` baseline, and outputs structured JSON with divergence flags. This script is the tooling that the developer runs manually for each strategy.

## Requirements

1. **Create `scripts/revalidate_strategy.py`** — a standalone CLI script:

   **CLI arguments:**
   - `--strategy` (required): Strategy key, one of `StrategyType` enum values (`orb`, `orb_scalp`, `vwap_reclaim`, `afternoon_momentum`, `red_to_green`, `bull_flag`, `flat_top_breakout`)
   - `--start` (required): Start date (YYYY-MM-DD), e.g., `2023-03-01`
   - `--end` (required): End date (YYYY-MM-DD), e.g., `2025-03-01`
   - `--cache-dir` (default: `data/databento_cache`): Databento Parquet cache directory. This serves BOTH as the VectorBT data source (`data_dir`) and the BacktestEngine cache.
   - `--output-dir` (default: `data/backtest_runs/validation`): Where to write result JSONs
   - `--is-months` (default: 4): In-sample window months
   - `--oos-months` (default: 2): Out-of-sample window months
   - `--step-months` (default: 2): Window step size
   - `--min-trades` (default: 20): Minimum trades to qualify per window
   - `--log-level` (default: `WARNING`)

   **Core logic:**

   a. **Load strategy config:** Read `config/strategies/{strategy_name}.yaml` using `load_yaml_file()` from `argus.core.config`. Extract current strategy parameters and `backtest_summary` baseline.

   b. **Build fixed params dict:** Map from YAML config keys to the walk-forward fixed-params naming convention. This is strategy-specific:
      - ORB Breakout: `or_minutes`, `target_r`, `stop_buffer_pct`, `max_hold_minutes`, `min_gap_pct`, `max_range_atr_ratio` (see walk_forward.py ~line 2605)
      - ORB Scalp: `scalp_target_r`, `max_hold_bars` (~line 2582)
      - VWAP Reclaim: `min_pullback_pct`, `min_pullback_bars`, `volume_multiplier`, `target_r`, `time_stop_bars` (~line 2591)
      - Afternoon Momentum: `consolidation_atr_ratio`, `min_consolidation_bars`, `volume_multiplier`, `target_r`, `time_stop_bars`
      - Red-to-Green: `min_gap_down_pct`, `level_proximity_pct`, `volume_confirmation_multiplier`, `time_stop_minutes`
      - Bull Flag / Flat-Top Breakout: These use PatternModule and may not have VectorBT sweepers. If `run_fixed_params_walk_forward()` does not support them (check if their strategy key is handled), fall back to running BacktestEngine directly for the full date range and compute a single-run metric set (no WFE). Document this limitation in the output JSON.

      **Investigation required:** Check whether `run_fixed_params_walk_forward()` handles `bull_flag` and `flat_top_breakout` strategy keys. Look at `evaluate_fixed_params_on_is()` to see if it has VectorBT paths for these. If not, implement a BacktestEngine-only fallback that runs on IS and OOS windows manually and computes WFE from BacktestEngine results. This is a pragmatic workaround, not a walk_forward.py modification.

   c. **Run walk-forward:**
      ```python
      config = WalkForwardConfig(
          strategy=strategy_key,
          data_dir=str(cache_dir),  # Point at Databento cache
          in_sample_months=args.is_months,
          out_of_sample_months=args.oos_months,
          step_months=args.step_months,
          min_trades=args.min_trades,
          output_dir=str(output_dir / strategy_key),
          oos_engine="backtest_engine",
      )
      result = await run_fixed_params_walk_forward(config, fixed_params)
      ```

   d. **Compare against baseline:** Extract from `backtest_summary`:
      - `oos_sharpe` (old) vs `result.avg_oos_sharpe` (new)
      - `wfe_pnl` (old) vs `result.avg_wfe_pnl` (new)
      - `total_trades` (old) vs `result.total_oos_trades` (new)

      Flag divergence when:
      - Sharpe difference > 0.5
      - Win rate difference > 10 percentage points
      - Profit factor difference > 0.5

      Handle `null` baselines gracefully (mark as "N/A — no prior baseline").

   e. **Output structured JSON:** Write `{output_dir}/{strategy_name}_validation.json`:
      ```json
      {
        "strategy": "orb_breakout",
        "strategy_type": "orb",
        "date_range": {"start": "2023-03-01", "end": "2025-03-01"},
        "data_source": "databento_ohlcv_1m",
        "engine": "backtest_engine",
        "baseline": {
          "source": "alpaca_provisional",
          "oos_sharpe": 0.34,
          "wfe_pnl": 0.56,
          "total_trades": 137,
          "data_months": 35
        },
        "new_results": {
          "oos_sharpe": ...,
          "wfe_pnl": ...,
          "wfe_sharpe": ...,
          "total_oos_trades": ...,
          "avg_win_rate": ...,
          "avg_profit_factor": ...,
          "total_windows": ...,
          "data_months": ...
        },
        "divergence": {
          "sharpe_diff": ...,
          "flagged": true/false,
          "flags": ["sharpe_divergence", ...]
        },
        "status": "VALIDATED" | "DIVERGENT" | "WFE_BELOW_THRESHOLD" | "ZERO_TRADES" | "NEW_BASELINE",
        "walk_forward_available": true/false,
        "notes": "..."
      }
      ```

   f. **Print summary to stdout** after completion (similar to BacktestEngine CLI output).

2. **Create `tests/backtest/test_revalidation_harness.py`** with tests:
   - `test_extract_fixed_params_orb` — verify YAML → fixed-params mapping for ORB Breakout
   - `test_extract_fixed_params_vwap` — verify YAML → fixed-params mapping for VWAP Reclaim
   - `test_extract_baseline_from_yaml` — verify baseline extraction from `backtest_summary`
   - `test_extract_baseline_null_values` — verify null/missing baseline handled gracefully
   - `test_divergence_detection_flagged` — verify Sharpe diff > 0.5 triggers flag
   - `test_divergence_detection_clear` — verify small differences don't trigger flag

## Constraints
- Do NOT modify: `argus/backtest/walk_forward.py`, `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, or any other existing source file
- Do NOT modify: any strategy `.py` file or YAML config (that's Session 4)
- Do NOT add: API endpoints, frontend components
- The script must be runnable standalone: `python scripts/revalidate_strategy.py --strategy orb --start 2023-03-01 --end 2025-03-01`
- If `run_fixed_params_walk_forward()` doesn't support a strategy, implement a BacktestEngine-only fallback IN THE SCRIPT (not by modifying walk_forward.py)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests: 6 tests in `tests/backtest/test_revalidation_harness.py`
- Minimum new test count: 5
- Test command: `python -m pytest tests/backtest/test_revalidation_harness.py -x -q`

Note: Tests should NOT actually run BacktestEngine or walk-forward (those are expensive). Test the config building, baseline extraction, and divergence detection logic by importing helper functions from the script.

## Definition of Done
- [ ] `scripts/revalidate_strategy.py` exists and is runnable
- [ ] Supports all 7 strategy types (with BacktestEngine-only fallback for PatternModule strategies if needed)
- [ ] Reads current params from strategy YAML configs
- [ ] Outputs structured JSON result per strategy
- [ ] Divergence detection works with configurable thresholds
- [ ] All 5+ new tests passing
- [ ] All existing tests still pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No source files modified | `git diff --name-only` shows only new files under `scripts/` and `tests/` |
| Walk-forward module unchanged | `git diff argus/backtest/walk_forward.py` is empty |
| Script is independently runnable | `python scripts/revalidate_strategy.py --help` prints usage |
| Config loading uses load_yaml_file | `grep "load_yaml_file" scripts/revalidate_strategy.py` finds import |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout.

**Write the close-out report to a file:**
`docs/sprints/sprint-21.6/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer subagent.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-21.6/review-context.md`
2. The close-out report path: `docs/sprints/sprint-21.6/session-3-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/backtest/test_revalidation_harness.py -x -q`
5. Files that should NOT have been modified: any file in `argus/` (all changes should be in `scripts/` and `tests/`)

The @reviewer will write its report to:
`docs/sprints/sprint-21.6/session-3-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings, update both files per the protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify no existing source files were modified (only new files in `scripts/` and `tests/`)
2. Verify YAML → fixed-params mapping is correct for each strategy (compare against walk_forward.py CLI args section)
3. Verify divergence thresholds match sprint spec (Sharpe > 0.5, win rate > 10pp, PF > 0.5)
4. Verify JSON output schema is complete and parseable
5. Verify PatternModule strategies (bull_flag, flat_top_breakout) have a sensible fallback if walk-forward doesn't support them
6. Verify tests don't actually run BacktestEngine (mock/unit test only)

## Sprint-Level Regression Checklist
*(See `docs/sprints/sprint-21.6/review-context.md`)*

## Sprint-Level Escalation Criteria
*(See `docs/sprints/sprint-21.6/review-context.md`)*
