# Tier 2 Review: Sprint 31A, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file** (DEC-330):
docs/sprints/sprint-31a/session-2-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-31a/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-31a/session-2-closeout.md`

## Session Scope
**Session 2: PMH 0-Trade Fix**

## Diff
`git diff HEAD~1`

## Test Command
Scoped: `python -m pytest tests/strategies/ -x -q -n auto`

## Files That Should NOT Have Been Modified
any pattern except premarket_high_break.py and base.py, orchestrator.py, engine.py, any frontend

## Session-Specific Review Focus
- -e 1. min_detection_bars defaults to lookback_bars (property delegation)
- 2. _get_candle_window uses lookback_bars for maxlen (NOT min_detection_bars)
- 3. PMH lookback=400 covers full PM session
- 4. Reference data uses correct SymbolReferenceData field
- 5. Reference data re-wires on periodic refresh
- 6. No import cycles from main.py
