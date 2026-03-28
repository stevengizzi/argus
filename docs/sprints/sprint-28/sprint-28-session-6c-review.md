# Tier 2 Review: Sprint 28, Session 6c

## Instructions
READ-ONLY review. Follow .claude/skills/review.md. Write to: `docs/sprints/sprint-28/session-6c-review.md`

**This is the FINAL session — run FULL test suites.**

## Review Context
Read `docs/sprints/sprint-28/review-context.md`

## Close-Out: `docs/sprints/sprint-28/session-6c-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test (FULL): `python -m pytest --ignore=tests/test_main.py -n auto -q` AND `cd argus/ui && npm test`

## Visual Review
1. Health Bands render per strategy with correct colors on Performance Learning tab
2. Correlation Matrix renders as heatmap on Performance Learning tab
3. Dashboard card shows pending count and links to Performance
4. Dashboard card hidden when learning_loop disabled
5. No visual regression on existing content

## Session-Specific Review Focus
1. Verify health bands are observational only (no throttle/boost)
2. Verify correlation matrix uses accessible color scale (blue-red)
3. Verify Dashboard card hidden when disabled
4. Verify no layout regression on existing pages
5. **FULL suite verification** — both pytest and Vitest
