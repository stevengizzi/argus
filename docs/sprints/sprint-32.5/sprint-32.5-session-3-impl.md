# Sprint 32.5, Session 3: DEF-134 Straightforward Patterns (dip_and_rip, hod_break, abcd)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/experiments/runner.py` (focus on `_PATTERN_TO_STRATEGY_TYPE` or equivalent mapping)
   - `argus/backtest/backtest_engine.py` (understand how patterns are instantiated)
   - `argus/strategies/patterns/dip_and_rip.py`
   - `argus/strategies/patterns/hod_break.py`
   - `argus/strategies/patterns/abcd.py`
   - `argus/strategies/pattern_strategy.py`
   - `argus/strategies/patterns/factory.py` (build_pattern_from_config)
2. Run the scoped test baseline (DEC-328 — Session 2+):
   ```
   cd /Users/stevengizzi/argus && python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q
   ```
   Expected: all passing
3. Verify you are on branch: `main`
4. Create working branch: `git checkout -b sprint-32.5-session-3`

## Objective
Add BacktestEngine and ExperimentRunner support for three PatternModule patterns that don't require reference data: dip_and_rip, hod_break, and abcd.

## Requirements

1. **In `argus/intelligence/experiments/runner.py` (or `backtest/backtest_engine.py` — wherever the pattern mapping lives):**
   - Add entries for `dip_and_rip`, `hod_break`, `abcd` to the pattern-to-strategy-type mapping
   - These patterns use `PatternBasedStrategy` as their wrapper (same as bull_flag and flat_top_breakout)
   - Use `build_pattern_from_config()` factory for instantiation (same pattern as Sprint 32)

2. **For each of the 3 patterns, verify:**
   - Factory can construct the pattern with default params
   - BacktestEngine can run a backtest with the pattern (single symbol, 1 month minimum)
   - The backtest produces a BacktestResult with `trades > 0`
   - No crashes or unhandled exceptions during detection/scoring

3. **ABCD performance note:**
   - ABCD swing detection is O(n³) (DEF-122). Backtesting will be noticeably slower.
   - Add a code comment near the ABCD mapping noting this known performance characteristic.
   - Do NOT optimize — just document.

## Constraints
- Do NOT modify: any pattern detection logic (dip_and_rip.py, hod_break.py, abcd.py)
- Do NOT modify: PatternBasedStrategy wrapper logic
- Do NOT modify: build_pattern_from_config() factory logic
- Do NOT modify: bull_flag or flat_top_breakout entries (regression)
- Do NOT modify: core/events.py, execution/order_manager.py, intelligence/counterfactual.py

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **dip_and_rip construct:** factory builds pattern, default params valid
  2. **dip_and_rip backtest:** single symbol, 1 month → BacktestResult with trades (may be 0 for some symbols — choose a volatile small-cap if possible, or accept 0 trades and verify no crash)
  3. **hod_break construct + backtest:** same pattern
  4. **abcd construct + backtest:** same pattern (note expected slower execution)
  5. **bull_flag regression:** existing backtest still works identically
  6. **flat_top_breakout regression:** existing backtest still works identically
- Minimum new test count: 6
- Test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q`

Note: If specific test data produces 0 trades for a pattern (the pattern's conditions simply don't occur in that data window), the test should verify "no crash, valid BacktestResult structure, trades >= 0." A separate integration test with curated data is a future concern.

## Definition of Done
- [ ] dip_and_rip mapped and constructable via factory
- [ ] hod_break mapped and constructable via factory
- [ ] abcd mapped and constructable via factory
- [ ] All 3 patterns produce valid BacktestResult (no crashes)
- [ ] bull_flag and flat_top_breakout regression unchanged
- [ ] ABCD O(n³) documented in code comment
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| bull_flag backtest unchanged | Run existing bull_flag test, compare output |
| flat_top_breakout backtest unchanged | Run existing flat_top_breakout test, compare output |
| run_experiment.py --pattern bull_flag works | CLI invocation |
| run_experiment.py --pattern flat_top_breakout works | CLI invocation |

## Close-Out
Follow the close-out skill in .claude/skills/close-out.md.
**Write the close-out report to:** docs/sprints/sprint-32.5/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-3-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q`
5. Files NOT modified: pattern source files (dip_and_rip.py, hod_break.py, abcd.py), core/events.py, execution/order_manager.py, pattern_strategy.py, factory.py

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify no pattern detection logic was modified (only mapping added)
2. Verify factory instantiation uses build_pattern_from_config() (not hardcoded constructors)
3. Verify bull_flag and flat_top_breakout entries unchanged
4. Verify ABCD O(n³) documentation exists as code comment
5. Check test data: if any test uses unreliable data that produces 0 trades, verify the test still validates no-crash behavior

## Sprint-Level Regression Checklist (for @reviewer)

### BacktestEngine Existing Patterns
- [ ] bull_flag backtest identical before/after
- [ ] flat_top_breakout backtest identical before/after
- [ ] run_experiment.py --pattern bull_flag still works
- [ ] run_experiment.py --pattern flat_top_breakout still works
- [ ] risk_overrides behavior unchanged

### Fingerprint Backward Compatibility
- [ ] compute_parameter_fingerprint() unchanged for detection-only

### Config Gating
- [ ] experiments.enabled=false → features disabled

### Test Suite Health
- [ ] All pre-existing pytest pass
- [ ] All pre-existing Vitest pass

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. Fingerprint backward incompatibility
2. BacktestEngine reference data requires architectural changes beyond backtest_engine.py
3. ExperimentConfig extra="forbid" conflict

### Scope Reduction Triggers
1. ABCD backtest >5 min for single-symbol/month → document, exclude from quick examples
