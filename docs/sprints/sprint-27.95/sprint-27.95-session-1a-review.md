# Tier 2 Review: Sprint 27.95, Session 1a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-27.95/session-1a-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-27.95/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-27.95/session-1a-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/execution/ tests/test_config* -x -q`
- Files that should NOT have been modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/data/`

## Session-Specific Review Focus
1. Verify `_broker_confirmed` is set ONLY on confirmed IBKR entry fill (not on order submission)
2. Verify confirmed positions are NEVER auto-closed regardless of config settings
3. Verify miss counter resets when position reappears in snapshot
4. Verify cleanup of tracking dicts on position close (no memory leaks)
5. Verify `auto_cleanup_unconfirmed=False` makes reconciliation fully warn-only

## Additional Context
This is the first session and the most critical fix. The March 26 log showed 336/371 positions destroyed by reconciliation. The core invariant is: a position with a confirmed IBKR fill must NEVER be auto-closed based on a portfolio snapshot miss.
