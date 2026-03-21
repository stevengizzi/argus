# Sprint 26 — Review Context File

> This file is read by the @reviewer subagent during Tier 2 reviews.
> It contains the Sprint Spec, Spec by Contradiction, Regression Checklist,
> and Escalation Criteria — everything the reviewer needs for context.

---

## Sprint Goal

Deliver ARGUS's fifth trading strategy (Red-to-Green gap-down reversal), establish the PatternModule ABC infrastructure for all future pattern development, and validate two pattern modules (Bull Flag, Flat-Top Breakout) — bringing the system from 4 to 7 active strategies/patterns with VectorBT backtesting and walk-forward validation for each.

## Key Architecture Decisions (from Adversarial Review)

1. **CandleBar dataclass** — PatternModule.detect() uses `list[CandleBar]` (frozen dataclass with timestamp/OHLCV) for type safety. PatternBasedStrategy converts CandleEvent → CandleBar.
2. **lookback_bars property** — Each PatternModule declares how many candles it needs. PatternBasedStrategy maintains per-symbol rolling deque.
3. **PatternDetection.target_prices** — Optional field for pattern-derived targets. PatternBasedStrategy falls back to R-multiple config targets if empty.
4. **R2G max_level_attempts** — Config parameter (default 2). After N level failures → EXHAUSTED.
5. **get_default_params() returns dict** — Deferred refinement to structured PatternParam type (DEF-088, Sprint 27).

## Deliverables

1. PatternModule ABC + CandleBar + PatternDetection (`argus/strategies/patterns/base.py`)
2. PatternBasedStrategy generic wrapper (`argus/strategies/pattern_strategy.py`)
3. RedToGreenStrategy with 5-state machine (`argus/strategies/red_to_green.py`)
4. RedToGreenConfig + YAML + loader (`argus/core/config.py`, `config/strategies/red_to_green.yaml`)
5. BullFlagPattern + config (`argus/strategies/patterns/bull_flag.py`, `config/strategies/bull_flag.yaml`)
6. FlatTopBreakoutPattern + config (`argus/strategies/patterns/flat_top_breakout.py`, `config/strategies/flat_top_breakout.yaml`)
7. VectorBT R2G backtest + walk-forward (`argus/backtest/vectorbt_red_to_green.py`)
8. Generic VectorBT Pattern Backtester (`argus/backtest/vectorbt_pattern.py`)
9. Integration wiring in main.py
10. UI — 3 new Pattern Library cards
11. ~76 pytest + ~8 Vitest new tests

## Config Changes

All new config fields listed in sprint-spec.md Config Changes table. Key additions:
- `config/strategies/red_to_green.yaml` → `RedToGreenConfig` (10+ fields incl. `max_level_attempts`)
- `config/strategies/bull_flag.yaml` → `BullFlagConfig` (8 fields)
- `config/strategies/flat_top_breakout.yaml` → `FlatTopBreakoutConfig` (7 fields)

## Files That Must NOT Be Modified

- `argus/strategies/base_strategy.py`
- `argus/strategies/orb_base.py`, `orb_breakout.py`, `orb_scalp.py`
- `argus/strategies/vwap_reclaim.py`, `afternoon_momentum.py`
- `argus/core/events.py`
- `argus/intelligence/quality_engine.py`, `position_sizer.py`
- `argus/core/orchestrator.py`, `risk_manager.py`, `event_bus.py`
- `argus/data/universe_manager.py`, `fmp_scanner.py`
- Existing config YAMLs: `orb_breakout.yaml`, `orb_scalp.yaml`, `vwap_reclaim.yaml`, `afternoon_momentum.yaml`
- Existing VectorBT modules: `vectorbt_orb.py`, `vectorbt_orb_scalp.py`, `vectorbt_vwap_reclaim.py`, `vectorbt_afternoon_momentum.py`

---

## Specification by Contradiction (Embedded)

### Out of Scope
1. Replay Harness cross-validation (deferred to post-BacktestEngine Sprint 27)
2. Short selling infrastructure (Sprint 29–31)
3. Pattern parameterization / templates (Sprint 32)
4. Ensemble orchestration (Sprint 32–38)
5. BacktestEngine integration (Sprint 27)
6. Learning Loop weight optimization (Sprint 28)
7. FMP Premium / FMP news integration (DEC-356)
8. Historical data purchase (DEC-353)
9. Observatory code changes (handles new strategies automatically)
10. Order Flow analysis (DEC-238, post-revenue)

### Edge Cases to Reject
1. R2G on gap-UP stocks → return None (WATCHING state stays)
2. Gap > max_gap_down_pct → EXHAUSTED ("gap_too_large")
3. Insufficient candle data for pattern → detect() returns None
4. Pattern outside operating window → PatternBasedStrategy blocks signal
5. Multiple patterns on same symbol → ALLOW_ALL (DEC-121/160)
6. WFE < 0.3 → pipeline_stage: "exploration", enabled: false, document results
7. No VWAP data for R2G → check prior close and premarket low levels only
8. Disabled pattern config → strategy not created in main.py

### Do NOT Add
- New Event types
- New API endpoints
- New WebSocket channels
- New database tables
- New frontend pages or routes
- AI Copilot context modifications

---

## Regression Checklist (Embedded)

### Strategy Integrity
| # | Check | How to Verify |
|---|-------|---------------|
| R1 | Existing 4 strategies untouched | `git diff HEAD -- argus/strategies/orb_base.py argus/strategies/orb_breakout.py argus/strategies/orb_scalp.py argus/strategies/vwap_reclaim.py argus/strategies/afternoon_momentum.py` shows no changes |
| R2 | BaseStrategy abstract interface unchanged | `git diff HEAD -- argus/strategies/base_strategy.py` shows no changes |
| R3 | Existing strategy config files untouched | `git diff HEAD -- config/strategies/orb_breakout.yaml config/strategies/orb_scalp.yaml config/strategies/vwap_reclaim.yaml config/strategies/afternoon_momentum.yaml` shows no changes |
| R4 | Existing strategy tests pass | `python -m pytest tests/strategies/test_orb*.py tests/strategies/test_vwap*.py tests/strategies/test_afternoon*.py -x -q` |

### Event & Data Integrity
| # | Check | How to Verify |
|---|-------|---------------|
| R5 | SignalEvent schema unchanged | `git diff HEAD -- argus/core/events.py` shows no changes |
| R6 | Event Bus unchanged | `git diff HEAD -- argus/core/event_bus.py` shows no changes |

### Quality Engine & Risk
| # | Check | How to Verify |
|---|-------|---------------|
| R7 | Quality Engine unchanged | `git diff HEAD -- argus/intelligence/quality_engine.py argus/intelligence/position_sizer.py` shows no changes |
| R8 | Risk Manager unchanged | `git diff HEAD -- argus/core/risk_manager.py` shows no changes |
| R9 | New strategies emit share_count=0 | Unit test assertion |
| R10 | New strategies emit pattern_strength 0–100 | Unit test assertion |

### Config Validation
| # | Check | How to Verify |
|---|-------|---------------|
| R11 | RedToGreenConfig YAML↔Pydantic key match | Config validation test |
| R12 | BullFlagConfig YAML↔Pydantic key match | Config validation test |
| R13 | FlatTopBreakoutConfig YAML↔Pydantic key match | Config validation test |

### Integration
| # | Check | How to Verify |
|---|-------|---------------|
| R14 | All 7 strategies registered with Orchestrator | Integration test |
| R15 | API /strategies returns 7 | Integration test |
| R16 | Orchestrator unchanged | `git diff HEAD -- argus/core/orchestrator.py` shows no changes |
| R17 | Universe Manager unchanged | `git diff HEAD -- argus/data/universe_manager.py` shows no changes |

### Test Suite
| # | Check | How to Verify |
|---|-------|---------------|
| R18 | Full pytest passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |
| R19 | Full Vitest passes | `cd argus/ui && npx vitest run --reporter=verbose` |
| R20 | Test count increases | Each session adds tests |

---

## Escalation Criteria (Embedded)

### Critical (Halt Immediately)
1. PatternModule ABC doesn't support BacktestEngine use case
2. Existing strategy tests fail
3. BaseStrategy interface modification required
4. SignalEvent schema change required
5. Quality Engine changes required

### Significant (Document and Assess)
6. R2G WFE < 0.3
7. Both Bull Flag AND Flat-Top WFE < 0.3
8. R2G state machine requires >5 states
9. Integration wiring causes allocation failures
10. config.py exceeds 1000 lines

### Informational
11. R2G gap-down pattern scarce in historical data (<50 trades)
12. Pattern detection latency >1ms
13. Fewer Vitest needed than estimated (positive outcome)
