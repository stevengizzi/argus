# Tier 2 Review: Sprint 27.95, Session 3b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to:**
`docs/sprints/sprint-27.95/session-3b-review.md`

## Review Context
`docs/sprints/sprint-27.95/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.95/session-3b-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/test_main* tests/execution/ tests/core/ -x -q`
- Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/counterfactual.py`, `argus/data/`

## Session-Specific Review Focus
1. CRITICAL: Verify overflow check is AFTER Risk Manager approval (not before)
2. CRITICAL: Verify overflow check is BEFORE order placement (not after)
3. Verify BrokerSource.SIMULATED bypass is unconditional
4. Verify SignalRejectedEvent fields match what CounterfactualTracker expects
5. Verify position count source is real positions only (not counterfactual shadow positions)
6. Verify no modification to existing rejection paths (quality filter, sizer, RM)

## Additional Context
This is the primary feature session — dynamic overflow routing. The core invariant is pipeline ordering: quality → RM → overflow → order placement. The overflow check must be purely additive — inserting it must not change any existing behavior for signals below capacity.
