# Sprint 26, Session 6 — Tier 2 Review

Read `docs/sprints/sprint-26/review-context.md`.
Close-out: `docs/sprints/sprint-26/session-6-closeout.md`

## Session Scope
FlatTopBreakoutPattern + FlatTopBreakoutConfig + YAML + loader.

## Review Focus
1. Resistance clustering within tolerance
2. Consolidation: bars below resistance, range narrowing
3. Score 0–100 meaningful
4. Config YAML↔Pydantic match
5. No execution logic in pattern module

## Test Command
`python -m pytest tests/strategies/patterns/test_flat_top_breakout.py -x -v`

## Do-Not-Modify
base_strategy.py, events.py, pattern_strategy.py, base.py, bull_flag.py, existing strategies

## Diff
`git diff HEAD~1`
