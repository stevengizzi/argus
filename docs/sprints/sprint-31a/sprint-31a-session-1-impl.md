# Sprint 31A, Session 1: DEF-143 BacktestEngine Fix + DEF-144 Debrief Safety Summary

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/engine.py` (focus on `_create_bull_flag_strategy()` through `_create_premarket_high_break_strategy()`, lines ~1211–1440)
   - `argus/strategies/patterns/factory.py` (the `build_pattern_from_config()` function)
   - `argus/execution/order_manager.py` (margin circuit breaker section, EOD flatten methods, signal cutoff)
   - `argus/analytics/debrief_export.py` (safety_summary section)
   - `argus/main.py` (pattern strategy creation blocks, lines ~519–650 — this is the reference for how build_pattern_from_config is used correctly)
2. Run the test baseline (DEC-328):
   Full suite: `python -m pytest -x -q -n auto && cd ui && npx vitest run --reporter=verbose 2>&1 | tail -5`
   Expected: ~4,674 pytest + 846 Vitest, all passing
3. Verify you are on the correct branch: `main`

## Objective
Replace 7 no-arg pattern constructors in BacktestEngine's `_create_*_strategy()` methods with `build_pattern_from_config()` calls (fixing DEF-143), and add safety tracking attributes to OrderManager for the debrief export safety_summary section (fixing DEF-144).

## Requirements

### DEF-143: BacktestEngine Pattern Init Fix

1. In `argus/backtest/engine.py`, modify each of the 7 pattern creation methods to use `build_pattern_from_config()` instead of no-arg constructors. The pattern is already used correctly in `main.py` — mirror that approach:

   **Before (current, broken):**
   ```python
   def _create_bull_flag_strategy(self, config_dir: Path) -> PatternBasedStrategy:
       # ... config loading ...
       config = self._apply_config_overrides(config)
       pattern = BullFlagPattern()  # <-- IGNORES config overrides
       return PatternBasedStrategy(pattern=pattern, config=config, ...)
   ```

   **After (fixed):**
   ```python
   def _create_bull_flag_strategy(self, config_dir: Path) -> PatternBasedStrategy:
       # ... config loading ...
       config = self._apply_config_overrides(config)
       pattern = build_pattern_from_config(config, "bull_flag")  # <-- USES config
       return PatternBasedStrategy(pattern=pattern, config=config, ...)
   ```

   Apply this change to all 7 methods:
   - `_create_bull_flag_strategy()` — `BullFlagPattern()` → `build_pattern_from_config(config, "bull_flag")`
   - `_create_flat_top_breakout_strategy()` — `FlatTopBreakoutPattern()` → `build_pattern_from_config(config, "flat_top_breakout")`
   - `_create_dip_and_rip_strategy()` — `DipAndRipPattern()` → `build_pattern_from_config(config, "dip_and_rip")`
   - `_create_hod_break_strategy()` — `HODBreakPattern()` → `build_pattern_from_config(config, "hod_break")`
   - `_create_abcd_strategy()` — `ABCDPattern()` → `build_pattern_from_config(config, "abcd")`
   - `_create_gap_and_go_strategy()` — `GapAndGoPattern()` → `build_pattern_from_config(config, "gap_and_go")`
   - `_create_premarket_high_break_strategy()` — `PreMarketHighBreakPattern()` → `build_pattern_from_config(config, "premarket_high_break")`

2. Add the import for `build_pattern_from_config` at the top of `engine.py` (from `argus.strategies.patterns.factory`). Remove any now-unused direct pattern class imports (BullFlagPattern, FlatTopBreakoutPattern, etc.) — verify each is truly unused before removing.

3. **Parity verification:** Write a test that creates a BacktestEngine with DipAndRipConfig using default values, inspects the constructed strategy's pattern, and verifies the pattern's internal parameter values match the config's field values. This confirms `build_pattern_from_config()` extracts and passes the correct params.

4. **Override verification:** Write a test that creates a BacktestEngine with DipAndRipConfig where `min_dip_percent` is overridden to 0.05 (vs default 0.02), then verifies the pattern's `_min_dip_percent` is 0.05. This is the specific test that was impossible before DEF-143.

### DEF-144: Debrief Export Safety Summary

5. In `argus/execution/order_manager.py`, add tracking attributes initialized in `__init__`:
   - `self.margin_circuit_breaker_open_time: datetime | None = None`
   - `self.margin_circuit_breaker_reset_time: datetime | None = None`
   - `self.margin_entries_blocked_count: int = 0`
   - `self.eod_flatten_pass1_count: int = 0`
   - `self.eod_flatten_pass2_count: int = 0`
   - `self.signal_cutoff_skipped_count: int = 0`

6. Wire the tracking attributes into the existing code paths:
   - Margin circuit breaker open: set `margin_circuit_breaker_open_time = datetime.now(UTC)` when the breaker opens
   - Margin circuit breaker reset: set `margin_circuit_breaker_reset_time = datetime.now(UTC)` when it resets
   - Margin entries blocked: increment `margin_entries_blocked_count` each time an entry is blocked by the margin breaker
   - EOD flatten: increment `eod_flatten_pass1_count` / `eod_flatten_pass2_count` as positions are closed in each pass
   - Signal cutoff: the cutoff logic is in main.py/orchestrator — the OrderManager may not be the right place. Check where signal cutoff happens and add tracking there, or add an `increment_signal_cutoff()` method on OrderManager if it's called from main.py's signal processing.

7. In `argus/analytics/debrief_export.py`, update the `safety_summary` section builder to read from the OrderManager tracking attributes instead of returning None. Handle the case where OrderManager reference is unavailable (degrade gracefully to None values).

## Constraints
- Do NOT modify any pattern files (bull_flag.py, flat_top.py, etc.) — they are read-only reference
- Do NOT modify main.py in this session (S2 modifies main.py)
- Do NOT change the BacktestEngine's strategy creation flow beyond the pattern constructor replacement
- Do NOT change `_apply_config_overrides()` behavior
- Do NOT modify any existing test assertions — only add new tests
- The 5 non-PatternModule strategy creation methods (`_create_orb_breakout_strategy`, `_create_orb_scalp_strategy`, `_create_vwap_reclaim_strategy`, `_create_afternoon_momentum_strategy`, `_create_red_to_green_strategy`) must remain unchanged

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test that BacktestEngine creates BullFlag strategy with pattern params matching config defaults
  2. Test that BacktestEngine creates DipAndRip with overridden params (verify override reaches pattern)
  3. Test all 7 PatternModule StrategyType values produce runnable strategies via BacktestEngine
  4. Test debrief export safety_summary with mock OrderManager attributes (non-null values)
  5. Test debrief export safety_summary with no events (null/zero values, no crash)
  6. Test margin_entries_blocked_count increments on margin rejection
- Minimum new test count: 8
- Test command: `python -m pytest tests/backtest/ tests/analytics/ -x -q -n auto`

## Definition of Done
- [ ] All 7 pattern creation methods use `build_pattern_from_config()`
- [ ] Unused direct pattern imports removed from engine.py
- [ ] Config overrides reach pattern constructors (verified by test)
- [ ] Default params produce identical behavior (verified by parity test)
- [ ] OrderManager has 6 new tracking attributes
- [ ] Tracking attributes wired into existing code paths
- [ ] Debrief export reads tracking attributes
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Default-params parity | Run BacktestEngine with DipAndRip default config, compare pattern params to DipAndRipPattern() no-arg defaults |
| Non-PatternModule strategies untouched | `git diff argus/backtest/engine.py` shows no changes to `_create_orb_breakout_strategy` through `_create_red_to_green_strategy` |
| No pattern file changes | `git diff argus/strategies/patterns/` shows no changes |
| Existing tests pass | Full suite green |

## Sprint-Level Escalation Criteria
1. DEF-143 fix breaks existing backtest results → STOP, escalate
2. min_detection_bars changes existing pattern behavior → STOP (not this session, but flag if noticed)
3. Test count decreases → STOP, investigate
4. Parameter sweep shows BacktestEngine still ignoring overrides → STOP

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
Write the close-out report to: `docs/sprints/sprint-31a/session-1-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context file: `docs/sprints/sprint-31a/review-context.md`
2. Close-out report: `docs/sprints/sprint-31a/session-1-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `python -m pytest tests/backtest/ tests/analytics/ tests/execution/ -x -q -n auto`
5. Files NOT modified: main.py, any pattern file, orchestrator.py, risk_manager.py, any frontend file

## Session-Specific Review Focus (for @reviewer)
1. Verify all 7 pattern creation methods use `build_pattern_from_config()` — no remaining no-arg constructors
2. Verify unused pattern class imports are removed
3. Verify `_apply_config_overrides()` is called BEFORE `build_pattern_from_config()` — the config object must have overrides applied before params are extracted
4. Verify OrderManager tracking attributes are initialized to safe defaults (None/0)
5. Verify debrief export handles missing OrderManager gracefully (no crash)
