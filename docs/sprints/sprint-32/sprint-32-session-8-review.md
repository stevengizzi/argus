# Tier 2 Review: Sprint 32, Session 8

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-32/session-8-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-32/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-32/session-8-closeout.md

## Review Scope
- Diff to review: git diff HEAD~1
- Test command: python -m pytest tests/ -n auto -q
- Files that should NOT have been modified: any file in experiments/ from S4-S7, any strategy file, any frontend file

## Session-Specific Review Focus
-e 1. Verify ExperimentConfig has extra="forbid"
2. Verify REST returns 503 when disabled (not 404)
3. Verify POST /experiments/run uses background task
4. Verify CLI works standalone
5. Verify JWT on all endpoints
6. Verify server lifespan init only when enabled
7. Verify config validation test is programmatic
8. Run full regression checklist (final session)

## Additional Context
Session 8 of 8 in Sprint 32: CLI + REST API + Server Integration + Config Gating.
