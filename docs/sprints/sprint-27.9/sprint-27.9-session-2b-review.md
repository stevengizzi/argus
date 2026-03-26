# Tier 2 Review: Sprint 27.9, Session 2b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
docs/sprints/sprint-27.9/session-2b-review.md

## Review Context
Read the following file for Sprint Spec, Spec by Contradiction, Regression Checklist, and Escalation Criteria:
`docs/sprints/sprint-27.9/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-27.9/session-2b-closeout.md`

## Review Scope
- Diff: git diff HEAD~1
- Test command: `python -m pytest tests/core/test_vix_calculators.py tests/core/test_regime*.py -x -q`
- Files that should NOT have been modified: argus/core/breadth.py, argus/core/market_correlation.py, argus/core/sector_rotation.py, argus/core/intraday_character.py, argus/strategies/, argus/execution/

## Session-Specific Review Focus
1. Verify CRISIS check has highest priority in VolRegimePhaseCalculator
2. Verify all 4 calculators return None (not default enum) when VIXDataService returns None
3. Verify existing 6 calculator outputs are IDENTICAL with and without VIXDataService
4. Verify RegimeClassifierV2 constructor accepts VIXDataService=None gracefully
5. Verify momentum calculator handles insufficient history (< momentum_window days)
6. If compaction occurred: verify all 4 calculators present (not just 2)
