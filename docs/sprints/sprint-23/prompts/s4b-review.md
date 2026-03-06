# Tier 2 Review: Sprint 23, Session 4b — CRITICAL SESSION

## Instructions
READ-ONLY. Follow `.claude/skills/review.md`. This is the integration session — apply extra scrutiny.

## Review Context
Read `sprint-23/review-context.md`.

## Tier 1 Close-Out Report
[PASTE CLOSE-OUT REPORT HERE]

## Review Scope
- Diff: `git diff HEAD~1`
- Test command: `python -m pytest tests/ -x -q` (full suite)
- Frontend tests: `cd argus/ui && npx vitest run`
- Files that should NOT have been modified: `argus/ai/`, `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/`, `argus/analytics/`, `argus/strategies/*.py`, `argus/backtest/`

## Session-Specific Review Focus
1. **Backward compatibility:** When `universe_manager.enabled: false`, verify the startup flow is IDENTICAL to pre-Sprint-23 code. Diff the old path vs new — no functional change allowed.
2. **Candle routing correctness:** When UM enabled, verify strategies only receive candles for symbols in their routing set
3. **ORB mutual exclusion (DEC-261):** Verify the mutual exclusion logic still works with the new routing path
4. **Backtest/replay isolation:** Verify simulated broker mode bypasses Universe Manager entirely
5. **AppState wiring:** Verify universe_manager is accessible via AppState for API endpoints
6. **Error handling:** What happens if universe_manager.build_viable_universe() fails mid-startup? Verify graceful degradation.
7. **ALL EXISTING TESTS PASS:** This is non-negotiable for this session. Run the FULL test suite.
8. Verify no "Do not modify" files were changed: `git diff HEAD~1 --name-only | grep -E "(argus/ai/|orchestrator\.py|risk_manager\.py|execution/|analytics/|strategies/.*\.py|backtest/)"` should return nothing.
