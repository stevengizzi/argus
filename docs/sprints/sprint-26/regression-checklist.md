# Sprint 26: Regression Checklist

After each session, verify each applicable check. All checks must pass at sprint close-out.

## Strategy Integrity

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R1 | Existing 4 strategies untouched | `git diff HEAD -- argus/strategies/orb_base.py argus/strategies/orb_breakout.py argus/strategies/orb_scalp.py argus/strategies/vwap_reclaim.py argus/strategies/afternoon_momentum.py` shows no changes | All |
| R2 | BaseStrategy abstract interface unchanged | `git diff HEAD -- argus/strategies/base_strategy.py` shows no changes | All |
| R3 | Existing strategy config files untouched | `git diff HEAD -- config/strategies/orb_breakout.yaml config/strategies/orb_scalp.yaml config/strategies/vwap_reclaim.yaml config/strategies/afternoon_momentum.yaml` shows no changes | All |
| R4 | Existing strategy tests pass | `python -m pytest tests/strategies/test_orb*.py tests/strategies/test_vwap*.py tests/strategies/test_afternoon*.py -x -q` | S2, S3, S9 |

## Event & Data Integrity

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R5 | SignalEvent schema unchanged | `git diff HEAD -- argus/core/events.py` shows no changes | All |
| R6 | CandleEvent schema unchanged | `git diff HEAD -- argus/core/events.py` shows no changes | All |
| R7 | Event Bus subscription model unchanged | `git diff HEAD -- argus/core/event_bus.py` shows no changes | All |

## Quality Engine & Risk

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R8 | Quality Engine unchanged | `git diff HEAD -- argus/intelligence/quality_engine.py argus/intelligence/position_sizer.py` shows no changes | All |
| R9 | Risk Manager unchanged | `git diff HEAD -- argus/core/risk_manager.py` shows no changes | All |
| R10 | New strategies emit share_count=0 | Unit test: R2G SignalEvent has share_count=0, PatternBasedStrategy SignalEvent has share_count=0 | S3, S4 |
| R11 | New strategies emit pattern_strength 0–100 | Unit test: verify pattern_strength is in [0, 100] range | S3, S4 |

## Config Validation

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R12 | RedToGreenConfig YAML↔Pydantic key match | Config validation test: load red_to_green.yaml, compare keys to RedToGreenConfig.model_fields | S2 |
| R13 | BullFlagConfig YAML↔Pydantic key match | Config validation test: load bull_flag.yaml, compare keys to BullFlagConfig.model_fields | S5 |
| R14 | FlatTopBreakoutConfig YAML↔Pydantic key match | Config validation test: load flat_top_breakout.yaml, compare keys to FlatTopBreakoutConfig.model_fields | S6 |
| R15 | All 3 configs inherit StrategyConfig base fields | Verify operating_window, risk_limits, benchmarks, universe_filter, backtest_summary present | S2, S5, S6 |

## Integration

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R16 | main.py creates R2G conditionally (config-gated) | Code review: R2G follows same if yaml.exists() pattern as VWAP/AfMo | S9 |
| R17 | main.py creates pattern strategies conditionally | Code review: Bull Flag and Flat-Top follow same conditional pattern | S9 |
| R18 | All 7 strategies registered with Orchestrator | Integration test: Orchestrator.strategies has 7 entries | S9 |
| R19 | Universe Manager routes to new strategies | Integration test: UM routing table includes R2G, Bull Flag, Flat-Top strategy IDs | S9 |
| R20 | API /strategies returns 7 strategies | Integration test: GET /api/v1/strategies response has 7 items | S9 |
| R21 | Orchestrator unchanged | `git diff HEAD -- argus/core/orchestrator.py` shows no changes | All |
| R22 | Universe Manager unchanged | `git diff HEAD -- argus/data/universe_manager.py argus/data/fmp_scanner.py` shows no changes | All |

## Frontend

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R23 | Pattern Library shows 7 cards | Vitest: render PatternLibraryPage with 7-strategy mock data, verify 7 cards | S10 |
| R24 | Existing 4 cards unchanged | Vitest: existing PatternCard tests still pass | S10 |
| R25 | No new pages or routes added | `git diff HEAD -- argus/ui/src/App.tsx argus/ui/src/router.tsx` shows no route changes | S10 |

## Backtesting

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R26 | Existing VectorBT modules untouched | `git diff HEAD -- argus/backtest/vectorbt_orb.py argus/backtest/vectorbt_orb_scalp.py argus/backtest/vectorbt_vwap_reclaim.py argus/backtest/vectorbt_afternoon_momentum.py` shows no changes | S7, S8 |
| R27 | Walk-forward validation uses WFE > 0.3 threshold | Code review: walk-forward output includes WFE, strategies failing < 0.3 are flagged | S7, S8 |

## Test Suite

| # | Check | How to Verify | Sessions |
|---|-------|---------------|----------|
| R28 | Full pytest suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` — 0 failures | All close-outs |
| R29 | Full Vitest suite passes | `cd argus/ui && npx vitest run --reporter=verbose` — 0 failures | S10 close-out |
| R30 | Test count monotonically increases | Each session adds tests; final count ≥ 2,891 pytest + 619 Vitest | All |
