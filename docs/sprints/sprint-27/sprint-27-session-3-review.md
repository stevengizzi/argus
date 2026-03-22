# Tier 2 Review: Sprint 27, Session 3

## Instructions
You are conducting a Tier 2 code review. READ-ONLY session.
Follow the review skill in .claude/skills/review.md.
Include structured JSON verdict fenced with ```json:structured-verdict.

**Write the review report to:** docs/sprints/sprint-27/session-3-review.md

## Review Context
Read: docs/sprints/sprint-27/review-context.md

## Tier 1 Close-Out Report
Read: docs/sprints/sprint-27/session-3-closeout.md

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/backtest/test_engine.py -x -q`
- Do-not-modify: `argus/core/event_bus.py`, `argus/backtest/replay_harness.py`, `argus/backtest/backtest_data_service.py`, `argus/strategies/`

## Session-Specific Review Focus
1. Verify engine.py imports SyncEventBus, NOT EventBus
2. Verify _setup() follows ReplayHarness._setup() pattern (same component set, same config loading)
3. Verify PatternBasedStrategy used for BULL_FLAG and FLAT_TOP_BREAKOUT
4. Verify config_overrides applied to strategy configs
5. Verify allocated_capital set on strategy after creation
6. Verify _teardown matches ReplayHarness._teardown pattern
