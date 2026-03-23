# Tier 2 Review: Sprint 27.5, Session 4 — Ensemble Evaluation

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-27.5/session-4-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-27.5/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-27.5/session-4-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/analytics/test_ensemble_evaluation.py -x -v`
- Files that should NOT have been modified: all existing files, argus/analytics/evaluation.py, argus/analytics/comparison.py

## Session-Specific Review Focus
metric-level aggregation documented as approximation, diversification_ratio formula, tail_correlation bottom 25%, marginal_contribution removes one and recomputes, identify_deadweight configurable threshold, evaluate_cohort_addition uses compare(), single-strategy edge case

## Additional Context
Session 4 of 6 in Sprint 27.5 (Evaluation Framework). This is a pure backend sprint — no frontend, no API endpoints, no external service calls.
