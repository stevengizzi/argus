# Tier 2 Review: Sprint 28.5, Session S1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session. Do NOT modify any source code files. Follow the review skill in `.claude/skills/review.md`.

Write the review report (including structured JSON verdict) to:
`docs/sprints/sprint-28.5/session-S1-review.md`

## Review Context
Read: `docs/sprints/sprint-28.5/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-28.5/session-S1-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/unit/core/test_exit_math.py -x -q -v`
- Files NOT modified: all existing files (S1 creates only new files)

## Session-Specific Review Focus
1. Verify all 3 functions are pure (no side effects, no I/O, no state)
2. Verify AMD-5 formulas use `high_watermark` not T1/T2 targets
3. Verify AMD-12: negative and zero ATR values return None
4. Verify StopToLevel enum has exactly: breakeven, quarter_profit, half_profit, three_quarter_profit
5. Verify `min_trail_distance` floor applied after trail distance computation
6. Verify `compute_effective_stop` returns max of non-None values (never below original_stop)

## Additional Context
Foundation session — no existing files should be modified. Only new files created.
