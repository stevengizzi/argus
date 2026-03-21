# Sprint 26, Session 4 — Tier 2 Review

Read `docs/sprints/sprint-26/review-context.md` for full context.

## Close-Out Report
[Read from: `docs/sprints/sprint-26/session-4-closeout.md`]

## Session Scope
PatternBasedStrategy generic wrapper — delegates to PatternModule, handles operating window, candle windows, signal generation, telemetry.

## Review Focus
1. Wrapper is generic — no imports from concrete patterns
2. CandleEvent→CandleBar conversion correct
3. Operating window from config.operating_window
4. deque maxlen = pattern.lookback_bars
5. detect() only when deque full
6. Pattern-derived targets used if present, R-multiple fallback
7. share_count=0 in all signals

## Test Command
`python -m pytest tests/strategies/patterns/test_pattern_strategy.py -x -v`

## Files That Should NOT Have Been Modified
base_strategy.py, events.py, existing strategies, config.py

## Diff Range
`git diff HEAD~1`
