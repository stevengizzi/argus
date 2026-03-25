# Tier 2 Review: Sprint 27.7, Session 3a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
`docs/sprints/sprint-27.7/session-3a-review.md`

## Review Context
`docs/sprints/sprint-27.7/review-context.md`

## Tier 1 Close-Out Report
`docs/sprints/sprint-27.7/session-3a-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/test_signal_rejected.py tests/intelligence/ -x -q`
- Files that should NOT have been modified: `argus/core/risk_manager.py`, `argus/intelligence/startup.py`, `config/system.yaml`, `config/system_live.yaml`, any files in `argus/strategies/`, any files in `argus/ui/`

## Session-Specific Review Focus
1. Verify `rejection_stage` is a string literal, NOT an import from intelligence module — preserves core→intelligence dependency direction
2. Verify `_counterfactual_enabled` defaults to False and is checked before every publish
3. Verify the signal in each SignalRejectedEvent has entry_price/stop_price/target_prices populated (not zeroed)
4. Verify no new `await` calls on the critical path when `_counterfactual_enabled=False`
5. Verify the OrderApprovedEvent/OrderRejectedEvent publish is not moved or reordered — SignalRejectedEvent is published AFTER the existing event flow
6. At the Risk Manager rejection point, verify SignalRejectedEvent is published after `await self._event_bus.publish(result)`

## Additional Context
Session 3a of 6. This is the first session that modifies `main.py`. The critical invariant is that `_process_signal()` behavior for live-mode strategies with counterfactual disabled is identical to pre-sprint. The `_counterfactual_enabled` flag defaults to False, so all changes are inert until Session 3b.
