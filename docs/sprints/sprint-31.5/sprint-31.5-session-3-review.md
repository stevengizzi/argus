# Tier 2 Review: Sprint 31.5, Session 3

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31.5/session-3-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-31.5/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-31.5/session-3-closeout.md

## Review Scope
- Diff to review: git diff HEAD~1
- Test command (final session — full suite): `python -m pytest -x -q --tb=short -n auto`
- Files that should NOT have been modified: `argus/intelligence/experiments/runner.py`, `argus/backtest/engine.py`, `argus/data/historical_query_service.py`, existing universe filter YAMLs (abcd, dip_and_rip, gap_and_go, hod_break, micro_pullback, narrow_range_breakout, premarket_high_break, vwap_bounce), any frontend files, any strategy files

## Session-Specific Review Focus
1. Verify Bull Flag and Flat-Top filter values are reasonable (not just copy-paste of another pattern)
2. Verify `--workers` flag defaults to `config.max_workers`, not hardcoded 4
3. Verify `max_workers: 4` in experiments.yaml is recognized by ExperimentConfig (extra="forbid" would catch typos)
4. Verify existing universe filter YAMLs are NOT modified (only new files created)
5. Verify full test suite passes (this is the final session — full suite required)
6. Verify Vitest suite passes: `cd ui && npx vitest run`

## Additional Context
This is Session 3 of 3 (final session). Sessions 1 (parallel infra) and 2 (DEF-146 filtering) are already committed. This session adds the remaining CLI integration and config files. Full suite run is mandatory for the final review.
