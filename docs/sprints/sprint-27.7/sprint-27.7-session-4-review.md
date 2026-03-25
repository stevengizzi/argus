# Tier 2 Review: Sprint 27.7, Session 4

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
`docs/sprints/sprint-27.7/session-4-review.md`

## Review Context
`docs/sprints/sprint-27.7/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.7/session-4-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/test_filter_accuracy.py tests/api/test_counterfactual_api.py tests/intelligence/test_counterfactual_integration.py -x -q`
- Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/intelligence/counterfactual.py`, `argus/intelligence/counterfactual_store.py`, any files in `argus/strategies/`, any files in `argus/ui/`

## Session-Specific Review Focus
1. Verify "correct rejection" definition: theoretical_pnl <= 0 means the filter was right to reject
2. Verify accuracy handles zero-division (no rejections in a category)
3. Verify min_sample_count threshold is respected — breakdowns with fewer samples flagged but included
4. Verify API endpoint returns 200 with empty report when no data (not 404 or 500)
5. Verify integration tests cover the full lifecycle (rejection → candle → close → accuracy query)
6. Verify filter_accuracy.py only reads from the store — no writes

## Additional Context
Session 4 of 6. This session builds analytics and the API endpoint. The integration tests are the most important deliverable — they prove the entire counterfactual pipeline works end-to-end for the first time.
