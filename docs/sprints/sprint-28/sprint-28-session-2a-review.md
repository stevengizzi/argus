# Tier 2 Review: Sprint 28, Session 2a

## Instructions
READ-ONLY review. Follow .claude/skills/review.md. Write to: `docs/sprints/sprint-28/session-2a-review.md`

## Review Context
Read `docs/sprints/sprint-28/review-context.md`

## Close-Out: `docs/sprints/sprint-28/session-2a-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test: `python -m pytest tests/intelligence/learning/ -x -q`
- Files NOT modified: everything outside `argus/intelligence/learning/` and tests

## Session-Specific Review Focus
1. Verify source separation: trade correlations computed separately from counterfactual
2. Verify p-value check: correlations with p > threshold tagged INSUFFICIENT_DATA
3. Verify weight formula: recommended weights sum to 1.0, stub dimensions held constant
4. Verify threshold decision criteria match Amendment 12 (0.40 / 0.50)
5. Verify zero-variance guards return INSUFFICIENT_DATA not NaN
