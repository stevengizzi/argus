# Tier 2 Review: Sprint 31.5, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-2-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-31.5/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-31.5/session-2-closeout.md

## Review Scope
- Diff to review: git diff HEAD~1
- Test command: `python -m pytest tests/intelligence/experiments/ tests/scripts/ -x -q`
- Files that should NOT have been modified: `argus/data/historical_query_service.py`, `argus/intelligence/experiments/store.py`, `argus/intelligence/experiments/models.py`, `argus/backtest/engine.py`, any frontend files, any strategy files

## Session-Specific Review Focus
1. Verify `_resolve_universe_symbols()` closes the HistoricalQueryService after use (no leaked DuckDB connections)
2. Verify dynamic filter fields are logged as skipped (not silently ignored)
3. Verify the CLI still works identically when `--universe-filter` is NOT passed (symbols=None, universe_filter=None path)
4. Verify the intersection logic: when both `symbols` and `universe_filter` provided, the filter restricts the candidate list
5. Verify no circular imports from `UniverseFilterConfig` usage in runner.py
6. Verify `run_sweep()` signature is backward compatible (all new params have defaults)

## Additional Context
This is Session 2 of 3. It resolves DEF-146 by moving universe filtering into ExperimentRunner's programmatic API. Session 1 (parallel infra) is already committed. Session 3 will add CLI flags and filter configs.
