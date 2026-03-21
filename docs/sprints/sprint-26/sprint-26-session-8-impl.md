# Sprint 26, Session 8: Generic VectorBT Pattern Backtester

## Pre-Flight Checks
1. Read:
   - `argus/strategies/patterns/base.py`, `bull_flag.py`, `flat_top_breakout.py`
   - `argus/backtest/vectorbt_red_to_green.py` (S7 reference)
   - `argus/backtest/walk_forward.py`
   - `config/strategies/bull_flag.yaml`, `config/strategies/flat_top_breakout.yaml`
2. Scoped test: `python -m pytest tests/backtest/ tests/strategies/patterns/ -x -q`
3. Verify branch

## Objective
Build a reusable VectorBT backtester that accepts any PatternModule + config, and run walk-forward validation for Bull Flag and Flat-Top Breakout.

## Requirements

1. **Create `argus/backtest/vectorbt_pattern.py`:**

   a. **`PatternBacktester` class:**
      - `__init__(pattern: PatternModule, config_path: Path)` — stores pattern and loads config
      - `generate_signals(ohlcv_df, params)`:
        - Iterate through historical bars with sliding window (pattern.lookback_bars)
        - At each bar, construct list[CandleBar] from window + basic indicators
        - Call pattern.detect() and pattern.score()
        - Generate entry/exit signals from detections
      - `build_parameter_grid()`:
        - Extract sweepable params from pattern.get_default_params()
        - Create variations (±20%, ±40%) around defaults
      - `run_sweep(ohlcv_df)`:
        - VectorBT parameter sweep over grid
        - Return results DataFrame
      - `run_walk_forward(ohlcv_df)`:
        - Walk-forward validation using walk_forward.py
        - Return WFE metrics

   b. **Run for Bull Flag:**
      - Load historical data
      - Instantiate BullFlagPattern, create backtester
      - Run parameter sweep + walk-forward
      - Update bull_flag.yaml backtest_summary

   c. **Run for Flat-Top Breakout:**
      - Same process with FlatTopBreakoutPattern
      - Update flat_top_breakout.yaml backtest_summary

2. **Results handling:** Same as S7 — WFE > 0.3 → "validation", else "exploration"

## Constraints
- Do NOT modify existing VectorBT modules, walk_forward.py, pattern modules
- Generic backtester works with ANY PatternModule (not hardcoded to specific patterns)

## Test Targets
New tests in `tests/backtest/test_vectorbt_pattern.py`:
1. `test_generic_backtester_with_mock_pattern` — mock PatternModule, verify signals generated
2. `test_parameter_grid_from_defaults` — grid built from get_default_params
3. `test_sliding_window_correct_size` — window matches pattern.lookback_bars
4. `test_candle_bar_conversion` — historical OHLCV row → CandleBar correct
5. `test_bull_flag_walk_forward` — runs without error (may need mock data)
6. `test_flat_top_walk_forward` — runs without error
- Minimum new test count: 6
- Test: `python -m pytest tests/backtest/test_vectorbt_pattern.py -x -v`

**⚠️ HUMAN REVIEW POINT:** Review Bull Flag and Flat-Top backtest results after session.

## Definition of Done
- [ ] Generic pattern backtester works with any PatternModule
- [ ] Walk-forward executed for both patterns
- [ ] Results documented, configs updated
- [ ] 6+ new tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-8-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-8-closeout.md`

## Tier 2 Review
Review context: `docs/sprints/sprint-26/review-context.md`
Close-out: `docs/sprints/sprint-26/session-8-closeout.md`
Test: `python -m pytest tests/backtest/test_vectorbt_pattern.py -x -v`
Do-not-modify: existing VectorBT modules, walk_forward.py, pattern modules

## Session-Specific Review Focus
1. Generic backtester truly generic (no hardcoded pattern references in core logic)
2. Sliding window uses pattern.lookback_bars
3. CandleBar construction from OHLCV data is correct
4. Walk-forward results match WFE threshold logic

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-26/review-context.md`.
