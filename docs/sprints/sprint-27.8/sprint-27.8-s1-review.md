# Tier 2 Review: Sprint 27.8, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-27.8/session-1-review.md

Create the file, write the full report (including the structured JSON
verdict) to it, and commit it. This is the ONE exception to "do not
modify any files" — the review report file is the sole permitted write.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-27.8/sprint-27.8-review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-27.8/session-1-closeout.md

## Review Scope
- Diff to review: git diff HEAD~1
- Test command: `python -m pytest tests/execution/ tests/backtest/test_engine_sizing.py tests/core/test_config.py -x -q`
- Files that should NOT have been modified: anything in `argus/strategies/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`

## Session-Specific Review Focus
1. Verify auto-cleanup is gated by `self._auto_cleanup_orphans` — NEVER reachable when False
2. Verify synthetic close records use `exit_price=entry_price` and `realized_pnl=0`
3. Verify bracket exhaustion detection only fires when ALL bracket legs are None
4. Verify per-strategy health loop doesn't change aggregate count logic
5. Verify `_close_position_and_log()` calls are properly awaited
6. Verify no race conditions between reconciliation cleanup and `on_tick()`/`on_fill()`
7. Verify rewritten test assertions are config-value-independent

## Additional Context
This is Session 1 of a 2-session impromptu sprint. Session 2 is a standalone
validation script with zero production code changes. This session carries the
higher regression risk due to Order Manager position lifecycle changes.
