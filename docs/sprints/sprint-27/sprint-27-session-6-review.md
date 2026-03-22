# Tier 2 Review: Sprint 27, Session 6

## Instructions
You are conducting a Tier 2 code review. READ-ONLY session.
Follow the review skill in .claude/skills/review.md.
Include structured JSON verdict fenced with ```json:structured-verdict.

**Write the review report to:** docs/sprints/sprint-27/session-6-review.md

This is the **final session** review. Full regression check required.

## Review Context
Read: docs/sprints/sprint-27/review-context.md

## Tier 1 Close-Out Report
Read: docs/sprints/sprint-27/session-6-closeout.md

## Review Scope
- Diff: `git diff HEAD~1`
- **Test command (final session — full suite):**
  ```bash
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```
- Do-not-modify: `argus/backtest/replay_harness.py`, `argus/backtest/vectorbt_*.py`, `argus/strategies/`, `argus/ui/`, `argus/api/`

## Session-Specific Review Focus
1. **CRITICAL: Verify existing Replay Harness OOS path completely unchanged.** The BacktestEngine path must be additive — conditional branch, existing code untouched.
2. Verify oos_engine defaults to "replay_harness" everywhere (WindowResult, WalkForwardResult, WalkForwardConfig, CLI)
3. Verify directional equivalence tests use same data for both engines
4. Verify speed benchmark methodology is fair (same data, strategy, machine)
5. Verify --oos-engine CLI flag is optional with default "replay_harness"
6. Verify JSON output includes oos_engine field
7. **Full regression check** — all R1–R19 from the regression checklist

## Additional Context
This is the final session of Sprint 27. The review should confirm:
- Total new test count across all sessions (~80)
- No existing tests broken
- Speed benchmark: BacktestEngine ≥5x faster than Replay Harness
- All adversarial review items addressed (AR-1 through AR-4)
