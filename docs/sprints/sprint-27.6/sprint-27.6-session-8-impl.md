# Sprint 27.6, Session 8: End-to-End Integration Tests + Cleanup

## Pre-Flight Checks
1. Read: `argus/core/regime.py`, `argus/core/orchestrator.py`, `argus/main.py`, `argus/backtest/engine.py` (all as modified by S1–S7)
2. Scoped test: `python -m pytest tests/core/ tests/backtest/ -x -q`
3. Verify branch

## Objective
Comprehensive end-to-end integration tests covering the full regime intelligence pipeline from startup through market hours. Golden-file parity test. Config permutation tests. Cleanup.

## Requirements

1. Create `tests/core/test_regime_e2e.py` with integration tests:
   - E2E: pre-market startup → calculators init → V2 run_pre_market → RegimeVector produced
   - E2E: market hours → mock candles flow → breadth updates → reclassify → RegimeVector evolves
   - E2E: all config permutations (all enabled, all disabled, individual dimensions disabled)
   - E2E: FMP unavailable → graceful degradation across all dimensions
   - Golden-file parity: V1 and V2 on 100-day SPY fixture (if not already in S7, consolidate here)
   - Stress test: BreadthCalculator with 5,000 symbols, verify < 1ms per candle
   - Config-gate complete isolation: when disabled, verify zero V2 code paths execute (mock + assertion)
   - All new modules importable (no circular imports test)
   - RegimeVector JSON roundtrip: serialize → deserialize → equal for all field combinations
   - Multiple reclassification cycles: RegimeVector consistency over time

2. Code cleanup:
   - Verify no TODO/FIXME/HACK left in new code (`grep -rn "TODO\|FIXME\|HACK" argus/core/breadth.py argus/core/market_correlation.py argus/core/sector_rotation.py argus/core/intraday_character.py argus/core/regime_history.py`)
   - Verify docstrings on all public methods of new classes
   - Verify type hints complete on all new functions

## Constraints
- Do NOT modify source code in this session (test-only + cleanup)
- If cleanup reveals issues, fix them but document in close-out

## Test Targets
- New tests (~11):
  - E2E pre-market → market hours flow
  - Config permutation: all enabled
  - Config permutation: all disabled
  - Config permutation: mixed (breadth off, others on)
  - FMP unavailable degradation
  - Stress: 5,000 symbols < 1ms per candle
  - Config-gate isolation
  - No circular imports
  - RegimeVector JSON roundtrip
  - Multiple reclassification cycles
  - Cleanup verification (no TODOs)
- Minimum: 10
- Test command: `python -m pytest tests/core/test_regime_e2e.py -x -q -v`

## Definition of Done
- [ ] 10+ E2E tests passing
- [ ] Golden-file parity confirmed
- [ ] Performance benchmark passes (< 1ms per candle)
- [ ] No TODO/FIXME/HACK in new code
- [ ] Close-out: `docs/sprints/sprint-27.6/session-8-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-8-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-8-closeout.md`
3. Test command: `python -m pytest tests/core/ tests/backtest/ -x -q -v`
4. Files NOT to modify: `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`, `strategies/*.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.6/session-8-review.md`

## Session-Specific Review Focus
1. Verify E2E tests exercise the full pipeline (not just unit-level)
2. Verify config-gate isolation test actually asserts zero V2 execution
3. Verify performance benchmark methodology is sound
4. Verify cleanup is complete (no TODOs, docstrings present)
