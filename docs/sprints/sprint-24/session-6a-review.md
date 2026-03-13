# Tier 2 Review: Sprint 24, Session 6a

## Instructions
READ-ONLY review. Follow `.claude/skills/review.md`.
**Write report to:** `docs/sprints/sprint-24/session-6a-review.md`

## Review Context
Read `docs/sprints/sprint-24/review-context.md`

## Tier 1 Close-Out Report
Read: `docs/sprints/sprint-24/session-6a-closeout.md`

## Review Scope
- Diff: `git diff HEAD~1`
- Test command (non-final): `python -m pytest tests/test_main.py tests/core/test_risk_manager.py tests/intelligence/test_quality_engine.py -x -q`
- Should NOT have been modified: `orchestrator.py`, `order_manager.py`, `trade_logger.py`, `backtest/*`

## Session-Specific Review Focus
1. **CRITICAL:** Verify backtest bypass: `BrokerSource.SIMULATED` → legacy sizing, NO quality pipeline
2. **CRITICAL:** Verify config bypass: `enabled=false` → legacy sizing
3. **CRITICAL:** Verify Risk Manager check 0 is the ONLY change to risk_manager.py — no other checks modified
4. Verify C/C- signals never reach evaluate_signal()
5. Verify enriched signal uses `dataclasses.replace()` (original never mutated)
6. Verify quality_history recorded for BOTH passed and filtered signals
7. Verify QualitySignalEvent published for scored signals (informational only)
8. Verify legacy sizing formula matches pre-Sprint-24 strategy calculation

