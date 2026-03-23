# Tier 2 Review: Sprint 21.6, Session 3

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
`docs/sprints/sprint-21.6/session-3-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-21.6/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-21.6/session-3-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/backtest/test_revalidation_harness.py -x -q`
- Files that should NOT have been modified: any file in `argus/` (all changes should be in `scripts/` and `tests/`)

## Session-Specific Review Focus
1. Verify no existing source files were modified (only new files in `scripts/` and `tests/`)
2. Verify YAML → fixed-params mapping is correct for each strategy (compare against walk_forward.py CLI args)
3. Verify divergence thresholds match sprint spec (Sharpe > 0.5, win rate > 10pp, PF > 0.5)
4. Verify JSON output schema is complete and parseable
5. Verify PatternModule strategies (bull_flag, flat_top_breakout) have a sensible fallback
6. Verify tests don't actually run BacktestEngine (mock/unit test only)

## Additional Context
This is Session 3 of 4. It creates the re-validation harness script — a CLI tool used by the developer (not production code). After this session, the developer runs the script manually for all 7 strategies before Session 4.
