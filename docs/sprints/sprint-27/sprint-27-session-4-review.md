# Tier 2 Review: Sprint 27, Session 4

## Instructions
You are conducting a Tier 2 code review. READ-ONLY session.
Follow the review skill in .claude/skills/review.md.
Include structured JSON verdict fenced with ```json:structured-verdict.

**Write the review report to:** docs/sprints/sprint-27/session-4-review.md

## Review Context
Read: docs/sprints/sprint-27/review-context.md

## Tier 1 Close-Out Report
Read: docs/sprints/sprint-27/session-4-closeout.md

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/backtest/test_engine.py -x -q`
- Do-not-modify: `argus/backtest/replay_harness.py`, `argus/execution/simulated_broker.py`, `argus/strategies/`

## Session-Specific Review Focus
1. **CRITICAL: Verify fill model priority order.** Stop must win when both stop and target trigger on same bar. Review every code path in _check_bracket_orders().
2. Verify NO tick synthesis (no import of tick_synthesizer, no synthesize_ticks call)
3. Verify NO asyncio.sleep(0) in bar processing loop
4. Verify time_stop check also checks for stop hit (worst case)
5. Verify _get_daily_bars() interleaves symbols by timestamp
6. Verify strategy receives CandleEvents only for watchlist symbols
