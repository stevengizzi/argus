# Sprint 31.75, Session 1: DEF-152 + DEF-153 Bug Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/gap_and_go.py`
   - `argus/backtest/engine.py` (lines 338–370: setup, lines 2605–2640: trade close)
   - `argus/backtest/config.py` (lines 145–209: BacktestEngineConfig)
   - `argus/execution/order_manager.py` (lines 278–330: fingerprint registry)
   - `argus/intelligence/experiments/runner.py` (lines 80–158: _run_single_backtest)
   - `docs/sprints/` (verify directory exists for close-out report)
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest tests/ -x -q -n auto`
   Expected: ~4,858 tests, all passing
3. Verify you are on the `main` branch: `git branch --show-current`
4. Verify no uncommitted changes: `git status`

## Objective
Fix two bugs that corrupt sweep results: (1) GapAndGo produces degenerate
R-multiples when stop is too close to entry (DEF-152), and (2) BacktestEngine
trades have NULL config_fingerprint, preventing trade-to-config correlation
(DEF-153).

## Requirements

### DEF-152: GapAndGo minimum risk guard

1. In `argus/strategies/patterns/gap_and_go.py`, add a `min_risk_per_share`
   constructor parameter (default `0.10`) that sets a floor on the minimum
   distance between entry and stop.

2. In the `detect()` method, after the stop calculation block (after line 218,
   `if stop_price >= entry_price: return None`), add a minimum risk guard:
   ```python
   # Minimum risk guard — prevent degenerate R-multiples (DEF-152)
   risk_per_share = entry_price - stop_price
   if risk_per_share < self._min_risk_per_share:
       return None
   ```
   This catches the case where stop is barely below entry (e.g., $0.01–0.09),
   which produces enormous R-multiples on any profit.

3. Add a `PatternParam` entry for `min_risk_per_share` in `get_default_params()`:
   ```python
   PatternParam(
       name="min_risk_per_share",
       param_type=float,
       default=self._min_risk_per_share,
       min_value=0.05,
       max_value=0.50,
       step=0.05,
       description="Minimum absolute risk (entry - stop) to emit signal",
       category="filtering",
   )
   ```

4. **Also** add a relative minimum risk check using ATR when available:
   ```python
   atr = indicators.get("atr", 0.0)
   if atr > 0 and risk_per_share < atr * 0.1:
       return None
   ```
   This prevents signals where risk is less than 10% of ATR (implausibly
   tight for a gap-and-go trade).

### DEF-153: BacktestEngine config_fingerprint wiring

5. In `argus/backtest/config.py`, add a `config_fingerprint` field to
   `BacktestEngineConfig`:
   ```python
   # Config fingerprint for experiment tracking (DEF-153)
   config_fingerprint: str | None = Field(
       default=None,
       description=(
           "16-char hex fingerprint from compute_parameter_fingerprint(). "
           "When set, registered with OrderManager so trades carry the "
           "fingerprint in the trades table."
       ),
   )
   ```

6. In `argus/backtest/engine.py`, in the `_setup()` method, after the
   OrderManager is created and started (after line 364, `await self._order_manager.start()`),
   and after the strategy is created (after line 367), register the fingerprint:
   ```python
   # Register config fingerprint for trade-level tracking (DEF-153)
   if self._config.config_fingerprint and self._order_manager is not None:
       strategy_id = self._strategy.strategy_id if self._strategy else self._config.strategy_id
       self._order_manager.register_strategy_fingerprint(
           strategy_id, self._config.config_fingerprint
       )
   ```
   Place this AFTER line 368 (`self._strategy.allocated_capital = ...`) so
   the strategy exists and has its ID.

7. In `argus/intelligence/experiments/runner.py`, in the `_run_single_backtest()`
   worker function, pass the fingerprint into BacktestEngineConfig construction.
   At line 105–113 where `engine_config = _BEConfig(...)` is constructed, add:
   ```python
   config_fingerprint=fingerprint,
   ```
   alongside the existing `config_overrides=args["detection_params"]` line.

## Constraints
- Do NOT modify: `argus/execution/order_manager.py` (fingerprint registry
  already works — we only consume it)
- Do NOT modify: `argus/analytics/trade_logger.py` (already handles
  config_fingerprint in Trade objects)
- Do NOT modify: `argus/core/events.py` (SignalEvent doesn't need changes —
  fingerprint flows through OrderManager registry, not signals)
- Do NOT modify: `argus/intelligence/experiments/store.py` (DEF-151 already fixed)
- Do NOT modify: any frontend files
- Do NOT change the behavior of the live trading pipeline — the fingerprint
  registration only fires in BacktestEngine context
- Do NOT change GapAndGo's detection logic beyond the minimum risk guard

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:

  **DEF-152 tests** (in `tests/strategies/patterns/test_gap_and_go.py`):
  1. `test_detect_rejects_near_zero_risk` — construct candles where stop is
     $0.03 below entry. Verify `detect()` returns None.
  2. `test_detect_rejects_zero_breakout_margin` — construct candles where
     entry and stop are within `min_risk_per_share`. Verify None.
  3. `test_detect_passes_adequate_risk` — construct candles where entry - stop
     > min_risk_per_share. Verify detection is returned.
  4. `test_min_risk_per_share_in_default_params` — verify the new PatternParam
     appears in `get_default_params()` with correct bounds.
  5. `test_detect_rejects_risk_below_atr_threshold` — when ATR is provided
     and risk < 10% of ATR, detection is rejected even if absolute minimum
     is met.

  **DEF-153 tests** (in `tests/backtest/test_engine.py` or a new
  `tests/backtest/test_engine_fingerprint.py`):
  6. `test_backtest_engine_config_fingerprint_field` — verify
     `BacktestEngineConfig(config_fingerprint="abc123...")` stores the value.
  7. `test_backtest_engine_registers_fingerprint` — run a minimal
     BacktestEngine with `config_fingerprint` set, verify trades have
     non-NULL `config_fingerprint` in the output DB. This requires either
     mocking or a very minimal backtest run.
  8. `test_run_single_backtest_passes_fingerprint` — verify the worker function
     passes fingerprint into BacktestEngineConfig. Can unit test by inspecting
     the config construction (mock BacktestEngine).

- Minimum new test count: 6
- Test command: `python -m pytest tests/strategies/patterns/test_gap_and_go.py tests/backtest/ tests/intelligence/experiments/test_runner.py -x -q`

## Config Validation
No new YAML config files. The `config_fingerprint` field on BacktestEngineConfig
is set programmatically by ExperimentRunner, not from YAML. No config validation
test needed.

## Definition of Done
- [ ] DEF-152: GapAndGo rejects signals with risk < min_risk_per_share
- [ ] DEF-152: GapAndGo rejects signals with risk < 10% of ATR
- [ ] DEF-152: New PatternParam for min_risk_per_share
- [ ] DEF-153: BacktestEngineConfig has config_fingerprint field
- [ ] DEF-153: BacktestEngine._setup() registers fingerprint with OrderManager
- [ ] DEF-153: _run_single_backtest passes fingerprint to BacktestEngineConfig
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| GapAndGo default-param detections still work | `python -m pytest tests/strategies/patterns/test_gap_and_go.py -x -q` — existing detection tests pass |
| BacktestEngine runs complete | `python -m pytest tests/backtest/ -x -q` — no regressions |
| ExperimentRunner worker function still works | `python -m pytest tests/intelligence/experiments/test_runner.py -x -q` |
| No live pipeline changes | `git diff argus/execution/order_manager.py` shows no changes |
| No event model changes | `git diff argus/core/events.py` shows no changes |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
docs/sprints/sprint-31.75/session-1-closeout.md

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-31.75/review-context.md`
   (copy from the sprint package if not already committed)
2. The close-out report path: `docs/sprints/sprint-31.75/session-1-closeout.md`
3. The diff range: `git diff HEAD~1` (or appropriate range)
4. The test command: `python -m pytest tests/strategies/patterns/test_gap_and_go.py tests/backtest/ tests/intelligence/experiments/test_runner.py -x -q`
5. Files that should NOT have been modified: `argus/execution/order_manager.py`, `argus/analytics/trade_logger.py`, `argus/core/events.py`, `argus/intelligence/experiments/store.py`, any `ui/` files

The @reviewer will produce its review report and write it to:
docs/sprints/sprint-31.75/session-1-review.md

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, you MUST update the artifact trail:
1. Append a "Post-Review Fixes" section to the close-out report file
2. Append a "Resolved" annotation to the review report file
3. Update the structured verdict JSON to CONCERNS_RESOLVED

## Session-Specific Review Focus (for @reviewer)
1. Verify GapAndGo minimum risk guard fires BEFORE the PatternDetection is
   returned — not after in PatternBasedStrategy.
2. Verify DEF-153 fingerprint registration happens AFTER strategy creation
   in BacktestEngine._setup(), not before.
3. Verify _run_single_backtest passes `config_fingerprint=fingerprint` (the
   computed hash, not a hardcoded string).
4. Verify no changes to OrderManager._close_managed_position() or the
   _fingerprint_registry dict initialization.
5. Verify the min_risk_per_share PatternParam has min_value > 0 (a value of
   0 would defeat the purpose).

## Sprint-Level Regression Checklist (for @reviewer)
(See review-context.md)

## Sprint-Level Escalation Criteria (for @reviewer)
(See review-context.md)
