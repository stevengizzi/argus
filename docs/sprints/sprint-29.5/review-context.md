# Sprint 29.5 Review Context

## Sprint Spec Reference
See: `docs/sprints/sprint-29.5/sprint-spec.md`

## Specification by Contradiction Reference
See: `docs/sprints/sprint-29.5/spec-by-contradiction.md`

## Sprint-Level Regression Checklist

| # | Invariant | Verification |
|---|-----------|-------------|
| 1 | All pre-existing pytest tests pass | `python -m pytest --ignore=tests/test_main.py -n auto -q` — 4178+ pass |
| 2 | All pre-existing Vitest tests pass | `cd argus/ui && npx vitest run` — 689 pass (1 pre-existing GoalTracker failure) |
| 3 | Trailing stop exits produce only winners | Verify `exit_math.py` unchanged; `compute_trail_stop_price()` signature preserved |
| 4 | Broker-confirmed positions never auto-closed | Verify `_broker_confirmed` dict in Order Manager preserved; reconciliation still skips confirmed |
| 5 | Config-gating pattern preserved | All new features have config toggle with safe defaults |
| 6 | EOD flatten triggers auto-shutdown | `eod_flatten()` still publishes `ShutdownRequestedEvent` |
| 7 | Quality Engine scoring unchanged | No modifications to `argus/analytics/quality_engine.py` or `argus/analytics/position_sizer.py` |
| 8 | Catalyst pipeline unchanged | No modifications to `argus/intelligence/` except debrief export |
| 9 | CounterfactualTracker logic unchanged | No modifications to `argus/intelligence/counterfactual.py` |
| 10 | No files in "do not modify" list touched | `argus/intelligence/learning/`, `argus/backtest/`, `argus/analytics/evaluation.py`, `argus/strategies/patterns/` |

## Sprint-Level Escalation Criteria

Escalate to Tier 3 (human review required) if ANY of:
1. Fill callback handling in Order Manager is modified beyond the specified error-404 + qty-correction scope
2. Position close/reconciliation logic is modified beyond the specified EOD broker-only flatten scope
3. Any regression in trailing stop test behavior
4. Any modification to files in the "do not modify" list
5. Any new DEC decision that contradicts existing DECs (especially DEC-261, DEC-369, DEC-372)
6. Test count decreases from pre-sprint baseline
7. MFE/MAE tracking introduces performance regression (tick handler should remain O(1))
