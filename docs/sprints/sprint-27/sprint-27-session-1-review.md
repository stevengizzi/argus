# Tier 2 Review: Sprint 27, Session 1

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict.

**Write the review report to a file:**
docs/sprints/sprint-27/session-1-review.md

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

docs/sprints/sprint-27/review-context.md

## Tier 1 Close-Out Report
Read the close-out report from:
docs/sprints/sprint-27/session-1-closeout.md

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/core/test_sync_event_bus.py tests/backtest/test_config.py -x -q`
- Files that should NOT have been modified: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/strategies/`, `argus/ui/`, `argus/api/`

## Session-Specific Review Focus
1. Verify SyncEventBus dispatches handlers in subscription order (FIFO) — test must prove ordering
2. Verify SyncEventBus uses `await handler(event)` directly — NOT `asyncio.create_task()`
3. Verify no `asyncio.Lock` in SyncEventBus
4. Verify `drain()` is a no-op (not `asyncio.gather` on pending)
5. Verify new StrategyType values don't appear in any existing switch/match logic
6. Verify BacktestEngineConfig has all fields from the spec
