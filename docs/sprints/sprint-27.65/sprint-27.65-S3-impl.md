# Sprint 27.65, Session S3: Strategy Fixes

## Parallelization Note
This session has NO file overlap with S1, S2, S4, or S5. It can run in
parallel with any of them. It touches only `argus/strategies/` files.

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/strategies/red_to_green.py`
   - `argus/strategies/pattern_strategy.py`
   - `argus/strategies/base_strategy.py`
   - `argus/strategies/patterns/base.py` (PatternModule ABC)
   - `docs/sprints/sprint-27.65/review-context.md`
2. Run the test baseline (DEC-328):
   Scoped: `python -m pytest tests/strategies/ -x -q`
   Expected: all passing
3. Verify you are on the correct branch

## Objective
Diagnose and fix Red-to-Green's zero evaluation issue (3,324 symbols routed,
zero evaluations after 30+ minutes). Improve pattern strategy warm-up to
reduce the initial "Insufficient history" dead zone.

## Background
- R2G health monitor warned every 60s for 30+ minutes: "0 evaluation events
  after window opened (watchlist: 3324 symbols) — possible pipeline issue"
- R2G uses a 5-state machine: WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL →
  ENTERED / EXHAUSTED. Requires gap-down detection which may need pre-market
  data not available via Databento EQUS.MINI in live mode.
- Bull Flag (lookback_bars=30) and Flat-Top (lookback_bars=20) showed
  "Insufficient history (15/30)" for liquid stocks like NFLX 45 minutes after
  market open. This seems too slow — NFLX should have a candle every minute.

## Requirements

### R1: Diagnose and fix Red-to-Green zero evaluations
1. **Investigation phase** (do this before writing any fix):
   - Read the R2G strategy code thoroughly
   - Identify the evaluation entry point — what method is called when a
     CandleEvent arrives? Is it `evaluate()`, `on_candle()`, or something else?
   - Check: does R2G subscribe to CandleEvent via the event bus?
   - Check: does R2G's gap-down detection require prior_close or pre-market
     data? If so, where does it get this data in live mode?
   - Check: does R2G's operating window check work with the current time format?
   - Check: does the `record_evaluation()` telemetry call happen before or after
     the gap-down filter? If after, it would show zero evaluations even if
     candles are arriving.
   - Document findings before implementing fix.

2. **Fix** (based on investigation):
   - If the issue is pre-market data dependency: wire in a data source for
     prior_close (e.g., from FMP daily bars, which are already fetched for
     regime classification), or compute prior_close from the first candle of
     the day.
   - If the issue is telemetry placement: move `record_evaluation()` to fire
     on every symbol evaluation attempt, not just after gap-down confirmation.
   - If the issue is event subscription: wire R2G into the CandleEvent bus.
   - Whatever the root cause, the fix must result in R2G producing evaluation
     events during its operating window (9:35-11:30 ET).

### R2: Improve pattern strategy warm-up
1. **Investigate the accumulation rate:** NFLX showed only 15/30 bars after
   45 minutes. This is too slow for a liquid stock with a candle every minute.
   Determine if bars are being dropped, if the deque is being reset, or if the
   strategy isn't receiving all CandleEvents for its watchlist.
2. **Expose a backfill hook** in `PatternBasedStrategy`: add a method
   `backfill_candles(symbol: str, bars: list[CandleBar])` that prepends
   historical bars to the front of the per-symbol deque (respecting max length).
   This will be wired to IntradayCandleStore in Session S4.5 — for now, just
   expose the method and test it.
3. **Temporary fallback** for the current session: if the candle deque has fewer
   than `lookback_bars` but at least 50% of them, allow evaluation with a
   `reduced_confidence=True` flag in the evaluation telemetry. Log at INFO:
   `"{strategy}: evaluating {symbol} with partial history ({N}/{lookback_bars})"`
   This ensures the strategies produce some data during the warm-up window
   rather than being completely silent for 30 minutes.
4. Fix the root cause of slow accumulation if investigation reveals dropped bars.

## Constraints
- Do NOT modify: other strategies (ORB, VWAP, AfMo)
- Do NOT modify: PatternModule ABC interface
- Do NOT modify: BaseStrategy evaluation telemetry infrastructure
- R2G fix must not require new external data sources (use existing FMP/Databento)
- Pattern warm-up fallback must be clearly marked as temporary if
   IntradayCandleStore (S4) is the proper solution

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. `test_r2g_produces_evaluations_in_live_mode` — simulate CandleEvents for R2G watchlist symbols, verify evaluation events recorded
  2. `test_r2g_gap_down_detection_without_premarket` — verify R2G can detect gap-downs using available data sources
  3. `test_r2g_state_machine_transitions` — verify WATCHING → GAP_DOWN_CONFIRMED path works
  4. `test_pattern_strategy_backfill_on_first_candle` — if backfill source available, deque populated
  5. `test_pattern_strategy_evaluation_with_partial_history` — reduced history mode if applicable
  6. `test_pattern_strategy_full_history_evaluation` — normal path once history sufficient
- Minimum new test count: 6
- Test command: `python -m pytest tests/strategies/ -x -q`

## Definition of Done
- [ ] R2G root cause identified and documented in close-out
- [ ] R2G fix implemented — strategy produces evaluations during operating window
- [ ] Pattern strategy warm-up improved or root cause of slow accumulation fixed
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S3-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/strategies/ -x -q`
5. Files NOT to modify: `argus/execution/`, `argus/core/risk_manager.py`

Write review to: `docs/sprints/sprint-27.65/S3-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify R2G evaluation telemetry fires on every evaluation attempt
2. Verify R2G doesn't depend on data that's unavailable in live mode
3. Verify pattern backfill doesn't introduce stale data or incorrect timestamps
4. Verify no changes to other strategies' behavior
