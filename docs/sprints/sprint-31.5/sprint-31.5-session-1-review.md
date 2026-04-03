# Tier 2 Review: Sprint 31.5, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-1-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-31.5/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-31.5/session-1-closeout.md

## Review Scope
- Diff to review: git diff HEAD~1
- Test command: `python -m pytest tests/intelligence/experiments/ -x -q`
- Files that should NOT have been modified: `argus/backtest/engine.py`, `argus/backtest/historical_data_feed.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, any frontend files, any strategy files

## Session-Specific Review Focus
1. Verify `_run_single_backtest()` is module-level (not a method) — required for pickling
2. Verify no `ExperimentStore` import or usage in the worker function
3. Verify `asyncio.run()` is used inside the worker (not awaiting in the main event loop)
4. Verify fingerprint dedup query happens BEFORE ProcessPoolExecutor dispatch
5. Verify KeyboardInterrupt handler calls `shutdown(wait=False, cancel_futures=True)`
6. Verify `workers=1` uses the existing sequential loop (not ProcessPoolExecutor with 1 worker)

## Additional Context
This is Session 1 of 3. It adds parallel execution infrastructure to ExperimentRunner. Session 2 will add universe filtering and Session 3 will add CLI flags and filter configs.
