# Sprint 32.5, Session 4: DEF-134 Reference-Data Patterns (gap_and_go, premarket_high_break)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/backtest/backtest_engine.py` (understand per-day simulation loop, how patterns are invoked)
   - `argus/intelligence/experiments/runner.py` (pattern mapping — updated in S3)
   - `argus/strategies/patterns/gap_and_go.py` (focus on `set_reference_data()` — what keys it expects)
   - `argus/strategies/patterns/premarket_high_break.py` (focus on `set_reference_data()` — what keys it expects)
   - `argus/strategies/patterns/base.py` (PatternModule ABC, `set_reference_data()` default no-op)
   - `argus/strategies/pattern_strategy.py` (`initialize_reference_data()`)
2. Run the scoped test baseline (DEC-328):
   ```
   cd /Users/stevengizzi/argus && python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q
   ```
   Expected: all passing (S3 patterns included)
3. Verify you are on branch: `main` (S3 merged)
4. Create working branch: `git checkout -b sprint-32.5-session-4`

## Objective
Add BacktestEngine support for gap_and_go and premarket_high_break — the two patterns that require reference data (prior day close, pre-market high) supplied via `set_reference_data()`. Build the reference data derivation mechanism within BacktestEngine's per-day simulation loop.

## Requirements

1. **In `argus/backtest/backtest_engine.py`:**
   - In the per-day simulation loop, before running pattern detection for each symbol:
     - **Prior day close:** Look up the last close price from the previous trading day's data in the Parquet cache. This is straightforward — the prior day's last OHLCV-1m bar's close.
     - **Pre-market high:** Scan the current day's candles for bars timestamped before 9:30 AM ET (pre-market). The PM high is the max of all such bars' high prices. If no PM bars exist (PM data not in cache), the PM high is None.
   - Call `pattern.set_reference_data({"prior_close": float, "premarket_high": float | None})` before detection on each symbol for each day
   - **First day of data range:** No prior day available. Log a DEBUG-level warning and skip that day for reference-data patterns. Do NOT crash.
   - This mechanism should be generic: check if the pattern's `set_reference_data` is overridden (not the base no-op), and only compute reference data for patterns that need it. Or simpler: compute it for all patterns (the cost is minimal) and let the base no-op ignore it.

2. **In `argus/intelligence/experiments/runner.py`:**
   - Add entries for `gap_and_go` and `premarket_high_break` to the pattern mapping
   - These use PatternBasedStrategy wrapper like all other patterns

3. **Verify for each pattern:**
   - Factory constructs the pattern with default params
   - BacktestEngine supplies reference data correctly
   - Backtest produces a BacktestResult (may be 0 trades if test data doesn't have suitable gaps/PM activity — that's acceptable)
   - No crashes or unhandled exceptions

## Constraints
- Do NOT modify: gap_and_go.py, premarket_high_break.py (pattern logic is correct)
- Do NOT modify: PatternModule ABC, PatternBasedStrategy wrapper
- Do NOT modify: dip_and_rip, hod_break, abcd entries (S3 work, regression)
- Do NOT modify: bull_flag, flat_top_breakout entries (original, regression)
- Do NOT modify: HistoricalDataFeed, SynchronousEventBus, TheoreticalFillModel
- The reference data mechanism must be localized within backtest_engine.py — if it requires changes to other files, ESCALATE (Tier 3 trigger)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. **Prior close derivation:** Given 2 days of data, prior close for day 2 = day 1's last bar close
  2. **PM high derivation:** Given candles with some before 9:30 AM ET, PM high = max of pre-9:30 highs
  3. **No PM data:** All candles after 9:30 AM → PM high is None
  4. **gap_and_go construct + backtest:** factory construct, run backtest, valid result
  5. **premarket_high_break construct + backtest:** same
  6. **First day skip:** Single-day data range → day skipped with warning, no crash
  7. **Non-ref-data patterns unaffected:** bull_flag backtest identical with reference data mechanism active
  8. **All 7 patterns sweep:** `run_experiment.py --pattern <name>` works for all 7
- Minimum new test count: 8
- Test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q`

## Definition of Done
- [ ] BacktestEngine derives prior close from previous day's data
- [ ] BacktestEngine derives PM high from pre-9:30 AM candles
- [ ] gap_and_go receives reference data and produces valid BacktestResult
- [ ] premarket_high_break receives reference data and produces valid BacktestResult
- [ ] First day of range: warning + skip (no crash)
- [ ] Missing PM data: None value (no crash)
- [ ] All 5 previously-mapped patterns unchanged (regression)
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| bull_flag backtest unchanged | Run existing test |
| flat_top_breakout backtest unchanged | Run existing test |
| dip_and_rip/hod_break/abcd unchanged | Run S3 tests |
| BacktestEngine risk_overrides still work | Existing test |

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-4-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/backtest/ -x -q`
5. Files NOT modified: any pattern files, pattern_strategy.py, core/events.py, execution/order_manager.py, HistoricalDataFeed, SynchronousEventBus, TheoreticalFillModel

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify reference data derivation is localized within backtest_engine.py (no other files modified for this mechanism)
2. Verify prior close uses the actual last bar close of the previous day (not day's open, not OHLC aggregation)
3. Verify PM high correctly handles timezone — pre-market is before 9:30 AM ET, data may be in different timezone
4. Verify first-day skip doesn't silently skip ALL days (off-by-one risk)
5. Verify non-reference-data patterns (bull_flag etc.) are completely unaffected by the new mechanism
6. Check that all 7 patterns now have mapping entries

## Sprint-Level Regression Checklist (for @reviewer)

### BacktestEngine Existing Patterns
- [ ] bull_flag backtest identical before/after
- [ ] flat_top_breakout backtest identical before/after
- [ ] dip_and_rip, hod_break, abcd entries from S3 unchanged
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
1. BacktestEngine reference data requires changes beyond backtest_engine.py
2. Fingerprint backward incompatibility

### Scope Reduction Triggers
1. PM candle data missing >50% of test symbols → reduce test scope
2. ABCD backtest >5 min → document limitation
