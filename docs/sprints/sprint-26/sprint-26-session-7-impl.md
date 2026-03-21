# Sprint 26, Session 7: VectorBT Red-to-Green + Walk-Forward

## Pre-Flight Checks
1. Read:
   - `argus/strategies/red_to_green.py` (S3 output — strategy logic)
   - `argus/backtest/vectorbt_vwap_reclaim.py` (VectorBT module reference)
   - `argus/backtest/walk_forward.py` (walk-forward validation engine)
   - `argus/backtest/data_fetcher.py` (historical data access)
   - `config/strategies/red_to_green.yaml`
2. Scoped test: `python -m pytest tests/backtest/ -x -q`
3. Verify branch

## Objective
Build VectorBT backtest module for Red-to-Green strategy. Run parameter sweep and walk-forward validation. Document results in config backtest_summary.

## Requirements

1. **Create `argus/backtest/vectorbt_red_to_green.py`:**
   Follow the exact pattern of `vectorbt_vwap_reclaim.py`:

   a. **Signal generation functions (vectorized):**
      - `generate_r2g_entries(ohlcv_df, params)` — vectorized gap-down detection + level testing logic
      - Gap-down identification: compare open vs prior close
      - Level identification: VWAP (computed from OHLCV), prior close
      - Entry signal when price reclaims level on volume
      - Exit signals: stop below level, T1/T2 R-multiple targets, time stop

   b. **Parameter grid:**
      - `min_gap_down_pct`: [0.015, 0.02, 0.03, 0.04]
      - `level_proximity_pct`: [0.002, 0.003, 0.005]
      - `volume_confirmation_multiplier`: [1.0, 1.2, 1.5]
      - `time_stop_minutes`: [15, 20, 30]

   c. **Walk-forward integration:**
      - Use `walk_forward.py` engine with standard window configuration
      - Calculate WFE for P&L and Sharpe
      - Report: OOS performance, trade count, win rate, profit factor

   d. **Report generation:**
      - Summary dict with: status, wfe_pnl, oos_sharpe, total_trades, data_months, last_run
      - Parameter sensitivity heatmap data
      - Best parameter set identification

2. **Results handling:**
   - If WFE > 0.3: update `red_to_green.yaml` backtest_summary with results, set pipeline_stage to "validation"
   - If WFE < 0.3: update backtest_summary with results, keep pipeline_stage as "exploration", log warning

## Constraints
- Do NOT modify existing VectorBT modules
- Do NOT modify walk_forward.py
- Use existing Alpaca historical data (per DEC-132, results are provisional)
- This is a standalone backtesting module — no live trading integration

## Test Targets
New tests in `tests/backtest/test_vectorbt_red_to_green.py`:
1. `test_r2g_signal_generation_basic` — synthetic OHLCV data with gap-down → entries generated
2. `test_r2g_no_signals_no_gap` — data without gaps → no entries
3. `test_parameter_grid_construction` — grid has expected parameter combinations
4. `test_walk_forward_execution` — walk-forward runs without error (may need mock data)
5. `test_report_generation` — report contains expected keys
- Minimum new test count: 5
- Test: `python -m pytest tests/backtest/test_vectorbt_red_to_green.py -x -v`

**⚠️ HUMAN REVIEW POINT:** After this session, review VectorBT results. If WFE < 0.3, discuss before proceeding with S9 integration. R2G can be wired in as `enabled: false`.

## Definition of Done
- [ ] VectorBT R2G module with signal generation, parameter sweep, walk-forward
- [ ] Walk-forward validation executed with WFE calculated
- [ ] Results documented (in close-out report + config yaml update)
- [ ] 5+ new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-7-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-7-closeout.md`

## Tier 2 Review
Review context: `docs/sprints/sprint-26/review-context.md`
Close-out: `docs/sprints/sprint-26/session-7-closeout.md`
Test: `python -m pytest tests/backtest/test_vectorbt_red_to_green.py -x -v`
Do-not-modify: existing VectorBT modules, walk_forward.py, data_fetcher.py

## Session-Specific Review Focus
1. Signal generation matches R2G strategy logic (gap-down + level reclaim + volume)
2. Walk-forward window configuration is reasonable
3. WFE calculation is correct
4. Results correctly written to backtest_summary

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-26/review-context.md`.
