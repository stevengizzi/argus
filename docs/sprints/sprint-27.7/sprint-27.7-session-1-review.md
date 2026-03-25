# Tier 2 Review: Sprint 27.7, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-27.7/session-1-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-27.7/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-27.7/session-1-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/test_counterfactual.py tests/core/test_fill_model.py tests/backtest/ -x -q`
- Files that should NOT have been modified: `argus/core/events.py`, `argus/main.py`, `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, any files in `argus/strategies/`, any files in `argus/ui/`

## Session-Specific Review Focus
1. Verify `evaluate_bar_exit()` fill priority exactly matches BacktestEngine's original logic — compare line-by-line if needed
2. Verify the BacktestEngine refactor is behavior-preserving — no new edge cases, no priority changes
3. Verify CounterfactualTracker uses T1 only from `signal.target_prices` tuple
4. Verify IntradayCandleStore backfill processes bars through the same `evaluate_bar_exit()` function
5. Verify MAE/MFE tracking logic is correct for LONG positions (MAE = max of entry-low, MFE = max of high-entry)
6. Verify empty `target_prices` guard exists and logs warning

## Additional Context
This is Session 1 of 6. It creates foundational library code (no wiring into main.py yet). The fill model extraction from BacktestEngine is the highest-risk change — if behavior changes, it's a hard halt. Prioritize reviewing the fill model extraction and regression test.
