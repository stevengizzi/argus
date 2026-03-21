# Sprint 26, Session 5 — Tier 2 Review

Read `docs/sprints/sprint-26/review-context.md` for full context.
Close-out: `docs/sprints/sprint-26/session-5-closeout.md`

## Session Scope
BullFlagPattern (PatternModule) + BullFlagConfig + YAML + loader. Also 3 PatternBasedStrategy edge-case tests.

## Review Focus
1. detect() logic: pole→flag→breakout sequence
2. Measured move target: entry + pole_height
3. Score 0–100 with meaningful components
4. Config YAML↔Pydantic match
5. No operating window in pattern module
6. PatternBasedStrategy edge-case tests (from S4 revision) added

## Test Command
`python -m pytest tests/strategies/patterns/ -x -v`

## Do-Not-Modify
base_strategy.py, events.py, pattern_strategy.py, base.py, existing strategies

## Diff Range
`git diff HEAD~1`
