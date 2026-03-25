# Tier 2 Review: Sprint 27.7, Session 3b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
`docs/sprints/sprint-27.7/session-3b-review.md`

## Review Context
`docs/sprints/sprint-27.7/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.7/session-3b-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/intelligence/ tests/test_signal_rejected.py -x -q`
- Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/core/regime.py`, `argus/data/intraday_candle_store.py`, `argus/core/events.py`, any files in `argus/strategies/`, any files in `argus/ui/`

## Session-Specific Review Focus
1. Verify `_on_signal_rejected_for_counterfactual` is wrapped in try/except — must never disrupt signal pipeline
2. Verify CandleEvent subscription handler short-circuits for symbols with no open counterfactual positions
3. Verify `_counterfactual_enabled` is only set to True after tracker initialization succeeds
4. Verify EOD close is called during shutdown (not just on a timer)
5. Verify store.close() is called during shutdown cleanup
6. Verify counterfactual config section in system.yaml and system_live.yaml matches the Pydantic model fields exactly

## Additional Context
Session 3b of 6. This is the integration session — the most complex wiring in the sprint. The tracker, store, config, event bus subscriptions, EOD task, and timeout check all come together here. Pay special attention to error handling — the counterfactual system must never disrupt the core trading pipeline.
