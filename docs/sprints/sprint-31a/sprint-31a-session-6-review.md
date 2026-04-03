# Tier 2 Review: Sprint 31A, Session 6

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31a/session-6-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31a/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-31a/session-6-closeout.md`

## Session Scope
**Session 6: Full Parameter Sweep + Experiments Config**

## Diff
`git diff HEAD~1`

## Test Command
Full suite (final session): `python -m pytest -x -q -n auto && cd ui && npx vitest run --reporter=verbose 2>&1 | tail -5`

## Files That Should NOT Have Been Modified
any Python source file

## Session-Specific Review Focus
- -e 1. No Python source changes (only config + docs)
- 2. Existing Dip-and-Rip variants preserved
- 3. All new variants use mode: shadow
- 4. Variant naming follows convention
- 5. Qualification criteria applied consistently
- 6. Sweep results covers all 10 patterns
- 7. Full test suite green
