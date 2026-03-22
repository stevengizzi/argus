# Sprint 27, Session 4: BacktestEngine — Single-Day Bar Loop + Order Fill Model

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` (S3 output — engine skeleton)
   - `argus/backtest/replay_harness.py` (reference: lines 558–705 for _run_trading_day, bar processing, bracket triggers)
   - `argus/execution/simulated_broker.py` (SimulatedBroker.simulate_price_update — understand bracket order API)
   - `docs/sprints/sprint-27/design-summary.md`
2. Run the test baseline (DEC-328 — Session 2+, scoped):
   ```bash
   python -m pytest tests/backtest/test_engine.py -x -q
   ```
   Expected: all passing (S3 close-out confirmed)
3. Verify you are on the correct branch: `main`

## Objective
Implement the single-day execution loop: bar processing with chronological multi-symbol interleaving, bar-level order fill simulation with worst-case priority (stop > target > time_stop > EOD), and strategy signal routing. This is the correctness-critical session.

## Requirements

1. **Add `_run_trading_day()` to `argus/backtest/engine.py`:**
   Follow the ReplayHarness._run_trading_day() pattern (lines 558-657) but with these key differences:
   - **NO tick synthesis** — skip `synthesize_ticks()` entirely
   - **NO `asyncio.sleep(0)`** — SyncEventBus handles dispatch synchronously
   - **Bar-level fill checking** replaces per-tick bracket triggers

   Implementation:
   ```
   a. Set clock to pre-market (9:25 AM ET, same as replay harness)
   b. Reset daily state (strategy, risk_manager, order_manager, data_service)
   c. Set strategy watchlist from provided watchlist
   d. Get today's bars (all symbols, sorted by timestamp)
   e. For each bar:
      i.   Advance clock to bar timestamp
      ii.  Set broker price (for market order fills)
      iii. Feed bar to data_service (publishes CandleEvent + IndicatorEvents via SyncEventBus)
      iv.  After event dispatch: check bracket orders against this bar's OHLC
   f. EOD flatten at configured time
   ```

2. **Add `_on_candle_event()` handler:**
   Same as ReplayHarness (lines 317-325): call `strategy.on_candle(event)`, if signal returned → `risk_manager.evaluate_signal(signal)` → publish result to bus.

3. **Add `_check_bracket_orders()` — the bar-level fill model:**
   This replaces the Replay Harness's tick-by-tick `_process_bracket_triggers()`.

   For each open bracket order (from SimulatedBroker):
   - Get the bar's OHLC for the order's symbol
   - **Priority order (worst-case-for-longs, per .claude/rules/backtesting.md):**
     1. **Stop loss:** If `bar.low <= stop_price` → trigger stop at `stop_price`
     2. **Target:** If `bar.high >= target_price` → trigger target at `target_price`
     3. **Time stop:** If time_stop condition met → trigger at `bar.close`, BUT first check if `bar.low <= stop_price` (if so, use stop price instead)
     4. **EOD:** Handled separately in EOD flatten
   - When both stop and target could trigger on the same bar (bar.low <= stop AND bar.high >= target), **stop wins** (worst case for longs)
   - Call `SimulatedBroker.simulate_price_update(symbol, trigger_price)` for each triggered order
   - Publish `OrderFilledEvent` for each fill (same as replay harness lines 685-704)

4. **Add `_get_daily_bars()`:**
   Same as ReplayHarness._get_daily_bars() (lines 660-683): filter bar_data by trading_day, interleave by timestamp.

5. **Wire the data loading from HistoricalDataFeed:**
   - In `_setup()` or a new `_load_data()` method:
     - Create `HistoricalDataFeed(cache_dir=config.cache_dir, verify_zero_cost=config.verify_zero_cost)`
     - Call `feed.load(symbols, start_date, end_date)` to get bar DataFrames
     - Store in `self._bar_data` (same format as replay harness)
     - Extract trading_days from the data

## Constraints
- Do NOT modify: `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, `argus/execution/simulated_broker.py`, any strategy files
- Do NOT add: tick synthesis, `asyncio.sleep(0)` calls, `asyncio.create_task()` calls
- Do NOT change: the _setup() or _teardown() from S3 (extend, don't rewrite)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write in `tests/backtest/test_engine.py` (extend):
  1. `test_single_day_bars_chronological` — bars fed in timestamp order across multiple symbols
  2. `test_clock_advances_per_bar` — FixedClock.set() called with each bar's timestamp
  3. `test_candle_event_dispatched` — strategy.on_candle() called for each bar's symbol
  4. `test_indicators_computed` — BacktestDataService produces VWAP/ATR after sufficient bars
  5. `test_fill_model_stop_priority` — bar hits both stop and target → stop fills
  6. `test_fill_model_stop_only` — bar low reaches stop, high doesn't reach target → stop fills
  7. `test_fill_model_target_only` — bar high reaches target, low doesn't reach stop → target fills
  8. `test_fill_model_time_stop_with_stop_check` — time stop bar where low also hits stop → stop price used
  9. `test_fill_model_time_stop_clean` — time stop bar where low doesn't hit stop → close price used
  10. `test_fill_model_no_trigger` — bar doesn't reach stop or target → no fill
  11. `test_no_trade_day` — no signals generated → zero fills
  12. `test_multi_symbol_day` — 3 symbols, signals and fills on each
  13. `test_watchlist_scoping` — strategy only receives candles for watchlist symbols
  14. `test_signal_to_order_pipeline` — signal → risk eval → order submission end-to-end
  15. `test_daily_state_reset` — strategy.reset_daily_state() called at start of day
- Minimum new test count: 15
- Test command (scoped): `python -m pytest tests/backtest/test_engine.py -x -q`

## Definition of Done
- [ ] _run_trading_day() implements bar-by-bar processing without tick synthesis
- [ ] _check_bracket_orders() implements bar-level fill model with correct priority
- [ ] _on_candle_event() routes signals through risk manager
- [ ] _get_daily_bars() returns chronologically sorted multi-symbol bars
- [ ] Data loading from HistoricalDataFeed integrated
- [ ] All existing tests pass
- [ ] 15 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` → no changes |
| SimulatedBroker unchanged | `git diff HEAD argus/execution/simulated_broker.py` → no changes |
| No tick_synthesizer import in engine.py | `grep "tick_synthesizer" argus/backtest/engine.py` → no matches |
| No asyncio.sleep in engine.py | `grep "asyncio.sleep" argus/backtest/engine.py` → no matches |
| No create_task in engine.py | `grep "create_task" argus/backtest/engine.py` → no matches |

## Close-Out
Write to: docs/sprints/sprint-27/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-27/review-context.md`
2. Close-out: `docs/sprints/sprint-27/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/backtest/test_engine.py -x -q`
5. Do-not-modify: `argus/backtest/replay_harness.py`, `argus/execution/simulated_broker.py`, `argus/strategies/`

@reviewer writes to: docs/sprints/sprint-27/session-4-review.md

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL: Verify fill model priority order.** Stop must win when both stop and target trigger on same bar. Review every code path in _check_bracket_orders().
2. Verify NO tick synthesis (no import of tick_synthesizer, no synthesize_ticks call)
3. Verify NO asyncio.sleep(0) anywhere in the bar processing loop
4. Verify time_stop check also checks for stop hit (worst case)
5. Verify _get_daily_bars() interleaves symbols by timestamp (not all of symbol A then all of symbol B)
6. Verify strategy receives CandleEvents only for its watchlist symbols

## Sprint-Level Regression Checklist (for @reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| R2 | Replay Harness unchanged | `git diff HEAD argus/backtest/replay_harness.py` |
| R3 | BacktestDataService unchanged | `git diff HEAD argus/backtest/backtest_data_service.py` |
| R4 | All VectorBT files unchanged | `git diff HEAD argus/backtest/vectorbt_*.py` |
| R5 | All strategy files unchanged | `git diff HEAD argus/strategies/` |

## Sprint-Level Escalation Criteria (for @reviewer)
2. Bar-level fill model produces clearly incorrect results (profit when impossible, stop triggered when bar low never reached stop).
3. Strategy behavior differs between BacktestEngine and direct unit test invocation.
6. BacktestEngine is slower than the Replay Harness on equivalent data.
9. Any existing backtest test fails.
