# Sprint 26, Session 8 — Tier 2 Review

Read `docs/sprints/sprint-26/review-context.md`.
Close-out: `docs/sprints/sprint-26/session-8-closeout.md`

## Session Scope
Generic VectorBT Pattern Backtester + walk-forward for Bull Flag and Flat-Top.

## Review Focus
1. Backtester is truly generic (no hardcoded pattern references)
2. Sliding window = pattern.lookback_bars
3. CandleBar from OHLCV correct
4. Walk-forward results match WFE threshold

## Test Command
`python -m pytest tests/backtest/test_vectorbt_pattern.py -x -v`

## Do-Not-Modify
Existing VectorBT modules, walk_forward.py, pattern modules

## Diff
`git diff HEAD~1`
