# Sprint 29: Regression Checklist

## Critical Invariants

### Strategy Behavior (verify after every session that modifies strategy code)
- [ ] ORB Breakout detection unchanged (run existing ORB tests)
- [ ] ORB Scalp detection unchanged
- [ ] VWAP Reclaim 5-state machine unchanged
- [ ] Afternoon Momentum 8 entry conditions unchanged
- [ ] Red-to-Green 5-state machine unchanged
- [ ] Bull Flag detection + scoring unchanged (critical: verify after S2 retrofit)
- [ ] Flat-Top Breakout detection + scoring unchanged (critical: verify after S2 retrofit)

### PatternModule Framework (verify after S1, S2)
- [ ] PatternModule ABC enforces all 5 abstract members
- [ ] PatternBasedStrategy wrapper handles operating window correctly
- [ ] PatternBasedStrategy candle deque accumulation works (pre-window + in-window)
- [ ] PatternBasedStrategy `backfill_candles()` from IntradayCandleStore works
- [ ] `set_reference_data()` is no-op for patterns that don't override it
- [ ] `_calculate_pattern_strength()` returns 0–100 for all patterns

### PatternBacktester (verify after S2)
- [ ] Bull Flag backtest completes without error with new grid generation
- [ ] Flat-Top backtest completes without error with new grid generation
- [ ] Grid generation produces valid parameter combinations (no empty grids, no degenerate values)
- [ ] PatternBacktester CLI entry point still works

### Pipeline Integration (verify in S8)
- [ ] Quality Engine processes signals from new patterns (share_count=0 → quality pipeline → sized)
- [ ] Risk Manager applies all checks to new pattern signals (including Check 0 for share_count ≤ 0)
- [ ] Counterfactual Engine tracks SignalRejectedEvent from new patterns
- [ ] Learning Loop can collect outcomes from new pattern trades (OutcomeCollector query)
- [ ] Event Bus handles additional strategy subscriptions without FIFO ordering issues
- [ ] Observatory service includes new patterns in pipeline stage counts

### Exit Management (verify for each new pattern)
- [ ] Per-strategy exit overrides in exit_management.yaml parse correctly for each new pattern
- [ ] `deep_update()` merges overrides correctly (global defaults + per-strategy overrides)
- [ ] Trailing stop config (ATR/percent/fixed mode) resolves correctly per pattern
- [ ] Partial profit-taking targets apply per pattern
- [ ] Time escalation config applies per pattern

### Universe Manager (verify for each new pattern)
- [ ] New universe filter configs parse without error
- [ ] Filters route symbols to new strategies via routing table
- [ ] Existing strategy routing unchanged (no symbol loss)
- [ ] Fail-closed behavior preserved (DEC-277): missing reference data → reject, not pass-through

### Config Validation (verify for each new config file)
- [ ] All new config fields verified against Pydantic model (no silently ignored keys)
- [ ] Specifically: `min_relative_volume` exists in UniverseFilterConfig (S3)
- [ ] Specifically: `min_gap_percent` exists in UniverseFilterConfig (S5)
- [ ] Specifically: `min_premarket_volume` exists in UniverseFilterConfig (S7)
- [ ] Strategy registration in orchestrator config matches exactly (no typos in strategy IDs)

### General
- [ ] All pre-existing pytest pass (0 failures)
- [ ] All pre-existing Vitest pass (0 failures)
- [ ] No modifications to files in "Do not modify" list
- [ ] No new event types added to Event Bus
- [ ] No new REST API endpoints added
- [ ] No frontend changes
