# Sprint 31.75, Session 2: DEF-154 — VWAP Bounce Parameter Rework

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/vwap_bounce.py`
   - `argus/strategies/patterns/base.py` (PatternModule ABC, PatternParam)
   - `tests/strategies/patterns/test_vwap_bounce.py`
   - `config/universe_filters/vwap_bounce.yaml`
   - `config/strategies/vwap_bounce.yaml` (if exists)
2. Run the scoped test baseline (DEC-328):
   `python -m pytest tests/strategies/patterns/test_vwap_bounce.py tests/strategies/patterns/test_pattern_base.py tests/strategies/patterns/test_factory.py -x -q`
   Expected: all passing (full suite confirmed by S1 close-out)
3. Verify you are on the `main` branch
4. Verify S1 close-out was committed

## Objective
Rework VwapBouncePattern to control signal density, which was 2–22 signals per
symbol per day in overnight sweeps — making parameter optimization meaningless.
Add four new controls: minimum approach distance (filters oscillation noise),
minimum bounce follow-through, per-symbol daily signal cap, and floor on
min_prior_trend_bars.

## Requirements

### 1. Add `min_approach_distance_pct` parameter

In `argus/strategies/patterns/vwap_bounce.py`:

a. Add constructor parameter `min_approach_distance_pct: float = 0.003`
   (0.3% of price). Store as `self._min_approach_distance_pct`.

b. In `_scan_for_bounce()`, before checking the touch, add an approach distance
   gate. Require that at least one bar in the lookback window BEFORE the touch
   had its close >= `vwap * (1 + self._min_approach_distance_pct)`. This
   confirms the price was meaningfully above VWAP before approaching it, not
   just oscillating around it:
   ```python
   # Approach distance gate — price must have been meaningfully above
   # VWAP before pulling back to it (DEF-154)
   approach_window = candles[max(0, touch_idx - 10):touch_idx]
   if not any(
       c.close >= vwap * (1 + self._min_approach_distance_pct)
       for c in approach_window
   ):
       continue
   ```
   Place this BEFORE the existing `_check_approach_zone()` call.

c. Add PatternParam:
   ```python
   PatternParam(
       name="min_approach_distance_pct",
       param_type=float,
       default=self._min_approach_distance_pct,
       min_value=0.001,
       max_value=0.010,
       step=0.001,
       description="Min distance price must be above VWAP before approach counts (fraction)",
       category="detection",
   )
   ```

### 2. Add `min_bounce_follow_through_bars` parameter

a. Add constructor parameter `min_bounce_follow_through_bars: int = 2`
   (number of additional bars after the bounce confirmation that must stay
   above VWAP). Store as `self._min_bounce_follow_through_bars`.

b. In `_scan_for_bounce()`, after `_check_bounce()` succeeds and returns
   `(bounce_end_idx, bounce_volume_ratio)`, add a follow-through check:
   ```python
   # Bounce follow-through — bars after bounce must stay above VWAP (DEF-154)
   follow_end = min(bounce_end_idx + self._min_bounce_follow_through_bars, n - 1)
   follow_bars = candles[bounce_end_idx + 1 : follow_end + 1]
   if len(follow_bars) < self._min_bounce_follow_through_bars:
       continue  # Not enough bars yet for follow-through
   if not all(c.close > vwap for c in follow_bars):
       continue  # Follow-through failed
   ```
   Update `entry_candle` to be `candles[follow_end]` (the last follow-through bar)
   so entry is AFTER confirmation, not at the bounce itself.

c. Add PatternParam:
   ```python
   PatternParam(
       name="min_bounce_follow_through_bars",
       param_type=int,
       default=self._min_bounce_follow_through_bars,
       min_value=0,
       max_value=5,
       step=1,
       description="Bars after bounce that must close above VWAP",
       category="detection",
   )
   ```

### 3. Add `max_signals_per_symbol` session-state cap

a. Add constructor parameter `max_signals_per_symbol: int = 3`.
   Store as `self._max_signals_per_symbol`.

b. Add a session-state tracking dict: `self._signal_counts: dict[str, int] = {}`.

c. In `detect()`, at the top (after the `vwap` and `atr` extraction), check:
   ```python
   symbol = str(indicators.get("symbol", ""))
   if symbol and self._signal_counts.get(symbol, 0) >= self._max_signals_per_symbol:
       return None
   ```

d. At the end of `detect()`, just before the `return PatternDetection(...)`,
   increment the counter:
   ```python
   if symbol:
       self._signal_counts[symbol] = self._signal_counts.get(symbol, 0) + 1
   ```

e. Add a `reset_session_state()` method (NOT part of PatternModule ABC —
   just a public method on VwapBouncePattern):
   ```python
   def reset_session_state(self) -> None:
       """Reset per-session state (call at start of each trading day)."""
       self._signal_counts.clear()
   ```

f. **IMPORTANT for backtesting:** The BacktestEngine processes multiple days.
   The `_signal_counts` dict must be cleared between trading days. This happens
   naturally because the PatternBasedStrategy creates a new pattern instance per
   BacktestEngine run (verify this in review). If the same instance IS reused
   across days, the `_track_symbol_evaluated()` or daily reset in
   PatternBasedStrategy would need to call `reset_session_state()`. Add a
   comment documenting this assumption.

g. Add PatternParam:
   ```python
   PatternParam(
       name="max_signals_per_symbol",
       param_type=int,
       default=self._max_signals_per_symbol,
       min_value=1,
       max_value=10,
       step=1,
       description="Max detections per symbol per session (prevents over-signaling)",
       category="filtering",
   )
   ```

### 4. Raise `min_prior_trend_bars` floor

a. Change the default from `10` to `15` in the constructor.

b. Update the PatternParam `min_value` from `5` to `10`:
   ```python
   PatternParam(
       name="min_prior_trend_bars",
       ...
       min_value=10,  # was 5 — too low allows noise (DEF-154)
       max_value=30,  # was 20 — wider range for sweeps
       step=5,
       ...
   )
   ```

### 5. Update `min_detection_bars` property

The `min_detection_bars` property currently returns
`self._min_prior_trend_bars + self._min_bounce_bars + 3`. Update it to also
account for the follow-through bars:
```python
@property
def min_detection_bars(self) -> int:
    return (
        self._min_prior_trend_bars
        + self._min_bounce_bars
        + self._min_bounce_follow_through_bars
        + 3
    )
```

### 6. Update `lookback_bars` if needed

The current `lookback_bars` is 30. With `min_prior_trend_bars=15` +
`min_bounce_bars=2` + `min_bounce_follow_through_bars=2` + 3 = 22, plus
headroom for approach scanning, 30 is adequate. Increase to 40 if the new
`min_detection_bars` exceeds 30 with any valid parameter combination (check
`max(min_value)` for each param).

## Constraints
- Do NOT modify: `argus/strategies/patterns/base.py` (PatternModule ABC)
- Do NOT modify: `argus/strategies/pattern_strategy.py`
- Do NOT modify: any other pattern file
- Do NOT add `max_signals_per_symbol` to the PatternModule ABC — this is
  VwapBounce-specific for now
- Do NOT change the `score()` method weighting (30/25/25/20)
- Preserve all existing constructor parameters and their types

## Test Targets
After implementation:
- Existing tests: all must still pass (existing detection tests may need
  updated fixture data if the stricter parameters filter them out — adjust
  fixture candle data to satisfy new conditions, don't weaken the new checks)
- New tests to write:

  1. `test_detect_rejects_no_approach_distance` — candles oscillating around
     VWAP (never >=0.3% above) produce None.
  2. `test_detect_requires_approach_distance` — candles that were 0.5% above
     VWAP before approaching produce a detection.
  3. `test_detect_requires_bounce_follow_through` — bounce without follow-through
     bars returns None.
  4. `test_detect_with_follow_through` — bounce with 2 follow-through bars above
     VWAP returns detection with entry at last follow-through bar.
  5. `test_max_signals_per_symbol_cap` — after 3 detections for same symbol,
     subsequent calls return None.
  6. `test_max_signals_per_symbol_different_symbols` — cap is per-symbol, not global.
  7. `test_reset_session_state` — after reset, signal count starts fresh.
  8. `test_min_prior_trend_bars_floor` — verify PatternParam min_value is 10.
  9. `test_new_params_in_default_params` — all 3 new PatternParams appear with
     correct bounds in `get_default_params()`.
  10. `test_min_detection_bars_includes_follow_through` — property returns
      correct value including follow-through bars.

- Minimum new test count: 8
- Test command: `python -m pytest tests/strategies/patterns/test_vwap_bounce.py tests/strategies/patterns/test_factory.py -x -q`

## Config Validation
If `config/strategies/vwap_bounce.yaml` exists, add the new parameters with
their defaults. Write a test that loads the YAML and verifies all keys map to
the Pydantic config model (if one exists for VwapBounce configs).

If no Pydantic config model exists (VwapBounce params are passed via
constructor / config_overrides only), this section is N/A.

## Definition of Done
- [ ] min_approach_distance_pct parameter and gate implemented
- [ ] min_bounce_follow_through_bars parameter and check implemented
- [ ] max_signals_per_symbol session-state cap implemented
- [ ] reset_session_state() method implemented
- [ ] min_prior_trend_bars default raised to 15, PatternParam min_value to 10
- [ ] min_detection_bars property updated for follow-through
- [ ] All existing tests pass (with fixture adjustments if needed)
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| VWAP Bounce still detects valid patterns | Existing detection tests pass (with adjusted fixtures if needed) |
| Pattern factory builds VwapBounce | `python -m pytest tests/strategies/patterns/test_factory.py -x -q` |
| PatternParam cross-validation | Run any existing cross-validation tests |
| No changes to other patterns | `git diff argus/strategies/patterns/` shows only vwap_bounce.py |
| lookback_bars >= min_detection_bars for all valid param combos | New test or manual check |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.75/session-2-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.75/review-context.md`
2. The close-out report path: `docs/sprints/sprint-31.75/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command: `python -m pytest tests/strategies/patterns/test_vwap_bounce.py tests/strategies/patterns/test_factory.py -x -q`
5. Files that should NOT have been modified: any pattern file other than `vwap_bounce.py`, `base.py`, `pattern_strategy.py`, any `ui/` files, any `store.py` files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.75/session-2-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the standard
protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify `_signal_counts` is a per-instance dict, NOT a class variable (would
   leak state between instances/tests).
2. Verify the entry price is set from the LAST follow-through bar, not the
   bounce bar (entry should be after confirmation, not during).
3. Verify the approach distance check looks at bars BEFORE the touch, not after.
4. Verify `lookback_bars >= max(min_detection_bars)` across all valid parameter
   combinations (use max values from PatternParam ranges).
5. Verify `max_signals_per_symbol` defaults to a small number (≤5), not a large
   number that defeats the purpose.
6. Check that existing tests were adjusted by changing fixture data to satisfy
   new conditions, NOT by weakening the new checks or setting permissive defaults.

## Sprint-Level Regression Checklist (for @reviewer)
(See review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(See review-context.md)
