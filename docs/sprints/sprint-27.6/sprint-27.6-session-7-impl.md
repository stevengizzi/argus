# Sprint 27.6, Session 7: BacktestEngine Integration

## Pre-Flight Checks
1. Read: `argus/backtest/engine.py` (_compute_regime_tags, to_multi_objective_result), `argus/core/regime.py` (RegimeClassifierV2)
2. Scoped test: `python -m pytest tests/backtest/ tests/core/test_regime.py -x -q`
3. Verify branch

## Objective
Extend BacktestEngine's `_compute_regime_tags()` to use RegimeClassifierV2 with all calculators as None (backtest mode — trend+vol only). Verify identical results to V1 via golden-file parity.

## Requirements

1. In `argus/backtest/engine.py`:
   - Import RegimeClassifierV2 and RegimeIntelligenceConfig
   - `_compute_regime_tags()`: Create `RegimeClassifierV2(config, regime_config, breadth=None, correlation=None, sector=None, intraday=None)`. Use V2.classify() instead of V1.classify(). Since V2 delegates to V1, results are identical.
   - If `regime_intelligence` not in config or disabled: fall back to V1 directly (backward compat).

2. Create a golden-file test fixture: Generate V1 regime tags for 100 trading days of SPY daily bars (synthetic or real from test data). Freeze as a JSON fixture file. Assert V2 produces identical tags.

## Constraints
- Do NOT modify: `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`
- V2 in backtest MUST produce identical tags to V1 for existing test data
- No calculator instances in backtest mode (all None)

## Test Targets
- New tests (~8) in `tests/backtest/test_engine_regime.py`:
  - _compute_regime_tags with V2: same results as V1 for known SPY data
  - Golden-file parity: 100-day fixture → V2 tags match frozen V1 tags exactly
  - Regime tags dict values are MarketRegime.value strings
  - to_multi_objective_result produces valid regime_results with V2 tags
  - V2 in backtest: only trend+vol dimensions populated in RegimeVector
  - Breadth/correlation/sector/intraday are defaults
  - BacktestEngine with regime_intelligence disabled: V1 behavior
  - Existing backtest integration tests still pass
- Minimum: 8
- Test command: `python -m pytest tests/backtest/test_engine_regime.py tests/backtest/ -x -q -v`

## Definition of Done
- [ ] BacktestEngine uses V2 with None calculators
- [ ] Golden-file parity test (100 days) passes
- [ ] Existing backtest tests unchanged
- [ ] 8+ new tests passing
- [ ] Close-out: `docs/sprints/sprint-27.6/session-7-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-7-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-7-closeout.md`
3. Test command: `python -m pytest tests/backtest/ -x -q -v`
4. Files NOT to modify: `evaluation.py`, `comparison.py`, `ensemble_evaluation.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.6/session-7-review.md`

## Session-Specific Review Focus
1. Verify V2 in backtest mode has all calculators as None
2. Verify golden-file test uses frozen fixture (not dynamically generated V1 tags)
3. Verify no changes to MultiObjectiveResult regime_results key structure
4. Verify fallback to V1 when regime_intelligence disabled
