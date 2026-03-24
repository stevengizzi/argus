# Sprint 27.6, Session 2: BreadthCalculator

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/regime.py` (RegimeVector — for return types)
   - `argus/core/events.py` (CandleEvent — subscription target)
   - `argus/core/config.py` (BreadthConfig)
2. Run the scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/core/test_regime.py -x -q
   ```
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on the correct branch

## Objective
Build BreadthCalculator as a standalone module that tracks intraday universe participation breadth from 1-minute CandleEvents. Returns `universe_breadth_score` and `breadth_thrust`. This is a passive Event Bus consumer — no modifications to DatabentoDataService.

## Requirements

1. Create `argus/core/breadth.py` with class `BreadthCalculator`:
   - Constructor: `(config: BreadthConfig)`
   - Internal state: `dict[str, deque[float]]` — per-symbol rolling close prices, deque maxlen = `config.ma_period`
   - `on_candle(event: CandleEvent) -> None`: Update rolling close for the symbol. O(1) per call.
   - `get_breadth_snapshot() -> dict`: Returns `{"universe_breadth_score": float|None, "breadth_thrust": bool|None, "symbols_tracked": int, "symbols_qualifying": int}`
   - Breadth computation:
     - A symbol qualifies when it has >= `min_bars_for_valid` candles in its deque
     - If fewer than `min_symbols` symbols qualify → return None for all outputs
     - For qualifying symbols: compare current close (last in deque) to MA (mean of deque)
     - `universe_breadth_score = (above_count - below_count) / total_qualifying` → range -1.0 to +1.0
     - `breadth_thrust = True` if `above_count / total_qualifying >= thrust_threshold`
   - `reset() -> None`: Clear all state (new trading day)
   - Memory bounded: deque maxlen enforced automatically

## Constraints
- Do NOT modify: `argus/data/databento_data_service.py`, `argus/core/regime.py`, `argus/core/events.py`
- Do NOT subscribe to Event Bus in this session — that happens in S6
- BreadthCalculator is a standalone module with no side effects

## Test Targets
- New tests to write (~14) in `tests/core/test_breadth.py`:
  - Construction with config
  - on_candle updates rolling deque per symbol
  - universe_breadth_score: all above MA → +1.0
  - universe_breadth_score: all below MA → -1.0
  - universe_breadth_score: mixed → between -1 and +1
  - breadth_thrust: True when >= thrust_threshold above MA
  - breadth_thrust: False when below threshold
  - Configurable thrust_threshold
  - Ramp-up: < min_bars_for_valid candles → symbol doesn't qualify
  - Pre-threshold: fewer than min_symbols qualifying → returns None
  - Memory bounded: deque maxlen enforced
  - Single symbol edge case
  - Empty universe → None
  - reset() clears all state
- Minimum new test count: 14
- Test command: `python -m pytest tests/core/test_breadth.py -x -q -v`

## Definition of Done
- [ ] BreadthCalculator implemented with all methods
- [ ] Ramp-up handling with min_bars_for_valid
- [ ] Returns None when thresholds not met
- [ ] Memory bounded via fixed-size deques
- [ ] 14+ new tests passing
- [ ] Close-out report written to `docs/sprints/sprint-27.6/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No files modified outside breadth.py | `git diff --name-only` shows only new file |
| O(1) per candle | Code inspection: dict lookup + deque append |
| Memory bounded | deque maxlen set in constructor |

## Close-Out
Follow close-out skill. Write to: `docs/sprints/sprint-27.6/session-2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-2-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/core/test_breadth.py -x -q -v`
5. Files NOT to modify: `databento_data_service.py`, `regime.py`, `events.py`, `orchestrator.py`, `main.py`

## Session-Specific Review Focus (for @reviewer)
1. Verify O(1) per-candle update (no loops over all symbols per candle)
2. Verify deque maxlen is enforced (memory bounded)
3. Verify None returned when thresholds not met (not 0.0)
4. Verify field name is `universe_breadth_score` (not `breadth_score`)
5. Verify no Event Bus subscription in this module (that's S6)
