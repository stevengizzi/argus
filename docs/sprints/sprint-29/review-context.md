# Sprint 29: Review Context

> This file is the shared reference for all Tier 2 reviews in Sprint 29.
> Each session's review prompt references this file by path.

---

## Sprint Spec (Summary)

**Goal:** Add 5 new PatternModule strategies (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, Pre-Market High Break) and introduce PatternParam structured type (DEF-088). Reach 12 active strategies.

**Deliverables:**
1. PatternParam frozen dataclass (8 fields) + `get_default_params()` returns `list[PatternParam]`
2. Optional `set_reference_data()` on PatternModule (default no-op)
3. Bull Flag + Flat-Top retrofit to PatternParam
4. PatternBacktester grid generation from PatternParam ranges
5. Dip-and-Rip pattern (9:45–11:30 AM, sharp dip + rapid recovery)
6. HOD Break pattern (10:00–15:30, HOD consolidation + breakout)
7. Gap-and-Go pattern (9:35–10:30, gap continuation, uses reference data hook)
8. ABCD pattern (10:00–15:00, harmonic Fibonacci legs, swing detection)
9. Pre-Market High Break pattern (9:35–10:30, PM high from deque candles) [STRETCH]
10. Per-pattern configs, universe filters, exit management overrides
11. Strategy registration + smoke backtests

**Key config verification requirement:** Universe filter fields `min_relative_volume`, `min_gap_percent`, and `min_premarket_volume` must exist in UniverseFilterConfig Pydantic model — Pydantic silently ignores unrecognized fields.

---

## Specification by Contradiction (Summary)

**Do NOT modify:** `core/events.py`, `execution/order_manager.py`, `core/risk_manager.py`, `analytics/evaluation.py`, `intelligence/learning/`, `intelligence/counterfactual.py`, `core/fill_model.py`, `ui/`, `api/`, `ai/`

**Do NOT modify after S1:** `strategies/patterns/base.py`, `strategies/pattern_strategy.py`
**Do NOT modify after S2:** `strategies/patterns/bull_flag.py`, `strategies/patterns/flat_top_breakout.py`, `backtest/vectorbt_pattern.py`

**Do NOT add:** New REST API endpoints, new WebSocket channels, new frontend components, new database tables, new event types

**Out of scope:** Walk-forward validation, parameter optimization, short selling, frontend changes, Quality Engine recalibration, swing detection extraction

**Edge cases:** ABCD incomplete patterns → None. Gap-and-Go no prior close → None. PM High Break no PM candles → None. Dip before 9:35 → reject. HOD false breakout → minimum hold duration.

---

## Sprint-Level Regression Checklist

### Strategy Behavior
- [ ] ORB Breakout detection unchanged
- [ ] ORB Scalp detection unchanged
- [ ] VWAP Reclaim 5-state machine unchanged
- [ ] Afternoon Momentum 8 entry conditions unchanged
- [ ] Red-to-Green 5-state machine unchanged
- [ ] Bull Flag detection + scoring unchanged (critical after S2)
- [ ] Flat-Top Breakout detection + scoring unchanged (critical after S2)

### PatternModule Framework
- [ ] PatternModule ABC enforces all 5 abstract members
- [ ] PatternBasedStrategy wrapper handles operating window correctly
- [ ] PatternBasedStrategy candle deque accumulation (pre-window + in-window)
- [ ] PatternBasedStrategy `backfill_candles()` works
- [ ] `set_reference_data()` is no-op for non-overriding patterns
- [ ] `_calculate_pattern_strength()` returns 0–100 for all patterns

### PatternBacktester
- [ ] Bull Flag backtest completes with new grid generation
- [ ] Flat-Top backtest completes with new grid generation
- [ ] Grid generation produces valid parameter combinations

### Pipeline Integration
- [ ] Quality Engine processes signals from new patterns
- [ ] Risk Manager applies all checks (including Check 0)
- [ ] Counterfactual Engine tracks rejected signals
- [ ] Event Bus FIFO ordering unaffected

### Exit Management
- [ ] Per-strategy exit overrides parse correctly per pattern
- [ ] `deep_update()` merges correctly
- [ ] Trailing stop mode resolves correctly per pattern

### Universe Manager
- [ ] New filter configs parse without error
- [ ] Filters route symbols correctly
- [ ] Existing routing unchanged
- [ ] Fail-closed preserved (DEC-277)

### Config Validation
- [ ] All new config fields verified against Pydantic model
- [ ] `min_relative_volume` in UniverseFilterConfig (S3)
- [ ] `min_gap_percent` in UniverseFilterConfig (S5)
- [ ] `min_premarket_volume` in UniverseFilterConfig (S7)

### General
- [ ] All pre-existing pytest pass (0 failures)
- [ ] All pre-existing Vitest pass (0 failures)
- [ ] No modifications to "Do not modify" files
- [ ] No new event types, endpoints, or frontend changes

---

## Sprint-Level Escalation Criteria

### Tier 3 Escalation
1. ABCD swing detection false positive rate >50%
2. PatternParam backward compatibility break outside pattern/backtester modules
3. Pre-market candle availability failure (EQUS.MINI not delivering extended-hours)
4. Universe filter field silently ignored requiring model redesign
5. Reference data hook causing initialization ordering issues

### Halt-and-Fix
1. Existing pattern behavior change after retrofit
2. PatternBacktester grid generation mismatch (degenerate results)
3. Config parse failure
4. Strategy registration collision

### Warning-and-Continue
1. Smoke backtest produces zero signals
2. Low test count for session
3. ABCD session exceeds expected complexity
