# Sprint 27.95, Session 3c: Overflow → CounterfactualTracker Wiring + Integration Tests

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/intelligence/counterfactual.py` — `_on_signal_rejected()` handler, RejectionStage handling
   - `argus/intelligence/filter_accuracy.py` — FilterAccuracy breakdown by stage
   - `argus/core/events.py` — SignalRejectedEvent, RejectionStage (post-3a)
   - `argus/main.py` — `_process_signal()` overflow path (post-3b)
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/intelligence/ tests/core/ tests/test_main* -x -q
   ```
   Expected: all passing (full suite confirmed by Session 3b close-out)
3. Verify all prior sessions committed

## Objective
Verify and complete the end-to-end overflow → CounterfactualTracker pipeline. Ensure overflow signals are correctly received, tracked, and persisted by CounterfactualTracker. Add integration tests for the full flow.

## Requirements

1. **Verify CounterfactualTracker handles BROKER_OVERFLOW stage:**
   - Read `_on_signal_rejected()` in `counterfactual.py`
   - Check if it filters by `RejectionStage` (e.g., only processes certain stages)
   - If it filters: add `BROKER_OVERFLOW` to the allowed set
   - If it accepts all stages: no change needed — verify with a test

2. **Verify FilterAccuracy handles BROKER_OVERFLOW breakdown:**
   - Read `filter_accuracy.py` — check if it groups accuracy by `stage`
   - BROKER_OVERFLOW should naturally work as a new grouping key
   - If there's hardcoded stage handling, add BROKER_OVERFLOW

3. **Write integration tests** for the full pipeline:
   - Test that constructs a mock signal pipeline where:
     a. Position count is set at/above broker_capacity
     b. A signal passes quality and RM approval
     c. The overflow check triggers
     d. SignalRejectedEvent is published
     e. CounterfactualTracker receives it and opens a shadow position
     f. The counterfactual position has correct metadata (stage=BROKER_OVERFLOW, original signal data)

4. **Verify counterfactual store records** have correct fields:
   - RejectionStage stored as "broker_overflow"
   - Reason string contains count/capacity info
   - All signal fields (symbol, entry, stop, target, strategy) preserved

5. **Verify coexistence** with existing rejection paths:
   - In the same test session: some signals rejected by quality filter, some by RM, some by overflow → all three tracked correctly by CounterfactualTracker with correct stages

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/execution/`
- Do NOT change: CounterfactualTracker core logic (shadow position tracking, MAE/MFE, bar monitoring, EOD close)
- Modifications to `counterfactual.py` should be MINIMAL — only adding BROKER_OVERFLOW to a filter list if needed
- Do NOT change: FilterAccuracy core computation logic

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~6):
  1. End-to-end: overflow signal → CounterfactualTracker opens shadow position
  2. Counterfactual store record has stage=BROKER_OVERFLOW
  3. Counterfactual store record has correct signal data (symbol, entry, stop, target)
  4. FilterAccuracy includes BROKER_OVERFLOW in breakdown
  5. Coexistence: quality_filter + position_sizer + broker_overflow rejections all tracked in same session
  6. Overflow counterfactual position closes correctly (stop/target/EOD via TheoreticalFillModel)
- Minimum new test count: 6
- Test command (final session — full suite): `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`

## Definition of Done
- [ ] All requirements implemented (or verified no changes needed)
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Full test suite passes (final session — full suite run)
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-3c-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| CounterfactualTracker shadow mode unchanged | Run existing shadow mode tests |
| CounterfactualTracker rejected signal tracking unchanged for existing stages | Run existing counterfactual tests |
| FilterAccuracy computation unchanged for existing stages | Run existing filter accuracy tests |
| TheoreticalFillModel unchanged | Run existing fill model tests |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-3c-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-3c-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (FINAL SESSION): `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/execution/`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-3c-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify CounterfactualTracker changes are MINIMAL (only filter list addition if needed)
2. Verify overflow counterfactual positions use the same TheoreticalFillModel as other counterfactuals
3. Verify FilterAccuracy correctly groups BROKER_OVERFLOW as a separate breakdown category
4. Verify integration tests cover the full pipeline (not just unit-level mocks)
5. Verify coexistence — existing rejection stages still produce correct counterfactual records
6. FULL SUITE RUN — this is the final session, verify ~3,660+ tests pass with 0 failures

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Normal position lifecycle unchanged
- [ ] Risk Manager gating logic unchanged
- [ ] Quality Engine pipeline unchanged
- [ ] EOD flatten still works
- [ ] CounterfactualTracker shadow mode still works
- [ ] CounterfactualTracker existing rejection stages still work
- [ ] BacktestEngine unaffected
- [ ] Reconciliation redesign (Session 1a) intact
- [ ] Stop retry cap (Session 2) intact
- [ ] Startup zombie cleanup (Session 4) intact
- [ ] All config fields verified
- [ ] Full test suite passes (~3,660+), no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. CounterfactualTracker changes break existing functionality → halt, escalate
2. Signal pipeline flow changed → halt
3. Full suite failures → investigate
