# Tier 2 Review: Sprint 32.5, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to:**
docs/sprints/sprint-32.5/session-1-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-32.5/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-32.5/session-1-closeout.md`

## Review Scope
- Diff to review: `git diff main...HEAD`
- Test command (scoped): `python -m pytest tests/intelligence/experiments/ tests/strategies/patterns/ -x -q`
- Files that should NOT have been modified: `core/events.py`, `core/regime.py`, `execution/order_manager.py`, `intelligence/counterfactual.py`, any strategy files under `strategies/` (except `patterns/factory.py`), `core/exit_math.py`, `core/config.py`

## Session-Specific Review Focus
1. Verify `compute_parameter_fingerprint()` with `exit_overrides=None` produces byte-identical hash to the pre-expansion function
2. Verify `exit_overrides={}` is treated identically to `exit_overrides=None`
3. Verify canonical JSON uses `sort_keys=True` and compact separators
4. Verify ExperimentStore schema migration handles fresh DB and existing DB with data
5. Verify `extra="forbid"` preserved on ExperimentConfig

## Additional Context
This is the first session of Sprint 32.5. It establishes the data model that S2 (spawner/runner) and S5 (API) build on. Backward compatibility of the fingerprint function is the highest-priority check.
