# Sprint 27.65, Session S4.5: Pattern Strategy Backfill Wire-Up + Final Integration

## Dependency Note
This session requires S3 (backfill hook exposed) and S4 (IntradayCandleStore
built). It wires the two together. This is the final session of Sprint 27.65.

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md`
   - `argus/data/intraday_candle_store.py` (created in S4)
   - `argus/strategies/pattern_strategy.py` (backfill hook from S3)
   - `__main__.py` (initialization order)
   - `docs/sprints/sprint-27.65/S3-closeout.md` (verify S3 complete)
   - `docs/sprints/sprint-27.65/S4-closeout.md` (verify S4 complete)
2. Run the test baseline (DEC-328 — final session, full suite):
   Full suite: `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   Expected: all tests passing (includes S1-S5 additions)
   Also: `cd argus/ui && npx vitest run`
   Expected: all passing
3. Verify you are on the correct branch
4. Verify IntradayCandleStore exists and has `get_bars()` API
5. Verify PatternBasedStrategy has `backfill_candles()` method

## Objective
Wire IntradayCandleStore into PatternBasedStrategy so that on the first
CandleEvent for a symbol, the strategy backfills its candle deque from the
centralized store — eliminating the 20-30 minute warm-up dead zone.

## Requirements

### R1: Backfill wire-up in PatternBasedStrategy
1. Give PatternBasedStrategy a reference to IntradayCandleStore:
   - Add an optional `candle_store: IntradayCandleStore | None` parameter
     to `__init__` (or set it via a setter after construction)
   - In `__main__.py`, pass the store reference when constructing
     PatternBasedStrategy instances (Bull Flag, Flat-Top Breakout)
2. On first CandleEvent for a symbol (when the per-symbol deque is empty or
   below `lookback_bars`):
   - If `candle_store` is available and `candle_store.has_bars(symbol)`:
     - Fetch bars: `bars = candle_store.get_latest(symbol, self.lookback_bars)`
     - Call `self.backfill_candles(symbol, bars)` (the hook from S3)
     - Log at INFO: `"{strategy}: backfilled {len(bars)} bars for {symbol} from IntradayCandleStore"`
   - Then append the current CandleEvent bar as usual
3. Backfill should only happen once per symbol per session. Add a
   `_backfilled: set[str]` to track which symbols have been backfilled.
   Don't re-backfill on every candle.
4. If IntradayCandleStore is None (e.g., not initialized, or running in
   test/backtest mode), skip backfill silently — fall back to the S3
   reduced-confidence behavior.

### R2: Remove reduced-confidence fallback (if backfill works)
1. If the backfill successfully provides full history on first candle,
   the reduced-confidence evaluation from S3 becomes unnecessary during
   the backfill window (since the strategy has full history immediately).
2. Keep the reduced-confidence path as a fallback for cases where the
   IntradayCandleStore doesn't have enough bars yet (early in the session
   before enough candles have accumulated in the store).
3. The expected behavior is:
   - First 20-30 minutes of market: store is accumulating, backfill provides
     partial history, reduced-confidence evaluation kicks in
   - After 30 minutes: backfill provides full history, normal evaluation

### R3: Verify full integration end-to-end
1. Run the full test suite (final session checkpoint)
2. Verify all S1-S5 changes work together without conflicts
3. If any merge conflicts were encountered during parallel execution,
   resolve them and document in the close-out

## Constraints
- Do NOT modify: IntradayCandleStore internals (from S4) — only consume its API
- Do NOT modify: PatternModule ABC interface
- Do NOT modify: Order Manager, Risk Manager, or other non-strategy code
- Backfill must not introduce duplicate bars (if the candle deque already has
  some bars from live events, backfill should only prepend older bars)
- Backfill must use CandleBar objects consistent with what the strategy expects

## Test Targets
After implementation:
- Existing tests: ALL must pass (final session — full suite)
- New tests to write:
  1. `test_pattern_strategy_backfills_from_candle_store` — store has 30 bars, first CandleEvent triggers backfill, deque has 31 bars
  2. `test_pattern_strategy_backfill_only_once_per_symbol` — second CandleEvent for same symbol does not re-backfill
  3. `test_pattern_strategy_backfill_skipped_when_no_store` — candle_store=None, no error, falls back to accumulation
  4. `test_pattern_strategy_backfill_no_duplicate_bars` — deque has 5 bars, backfill adds 25 older ones, total is 30 (not 35)
  5. `test_pattern_strategy_full_evaluation_after_backfill` — after backfill, strategy evaluates normally (not reduced-confidence)
  6. `test_pattern_strategy_reduced_confidence_when_store_insufficient` — store has only 10 bars for 30-bar lookback, reduced-confidence used
- Minimum new test count: 6
- Test commands (final session — full suite):
  - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
  - `cd argus/ui && npx vitest run`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Bull Flag still detects patterns with full history | Existing pattern tests pass |
| Flat-Top Breakout still detects patterns | Existing pattern tests pass |
| IntradayCandleStore not modified | `git diff` shows no changes to `intraday_candle_store.py` |
| All S1-S5 changes still work | Full test suite passes |
| No merge conflict residue | `grep -r "<<<<<<" argus/` returns nothing |

## Definition of Done
- [ ] PatternBasedStrategy wired to IntradayCandleStore for backfill
- [ ] Backfill triggers on first candle per symbol, once only
- [ ] Graceful fallback when store is unavailable or insufficient
- [ ] No duplicate bars in candle deques
- [ ] Full test suite passes (all S1-S5 + S4.5 tests)
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write close-out to: `docs/sprints/sprint-27.65/S4.5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.65/review-context.md`
2. Close-out path: `docs/sprints/sprint-27.65/S4.5-closeout.md`
3. Diff range: full sprint diff (`git diff` from sprint start tag/commit)
4. Test command (final session — full suite):
   - `python -m pytest tests/ --ignore=tests/test_main.py -x -q -n auto`
   - `cd argus/ui && npx vitest run`
5. Files NOT to modify: `argus/data/intraday_candle_store.py`, `argus/execution/`, `argus/core/risk_manager.py`

Write review to: `docs/sprints/sprint-27.65/S4.5-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify backfill doesn't introduce duplicate bars
2. Verify backfill only happens once per symbol (check `_backfilled` set)
3. Verify graceful degradation when store is None
4. Verify no merge conflicts from parallel session execution
5. Full regression pass — this is the final session of the sprint
