# Sprint 31A: Regression Checklist

## Critical Invariants

### BacktestEngine Behavioral Parity (S1)
- [ ] BacktestEngine with StrategyType.BULL_FLAG and default config produces identical trade count + Sharpe to pre-fix behavior
- [ ] BacktestEngine with StrategyType.DIP_AND_RIP and default config produces identical results
- [ ] All 7 PatternModule StrategyType values produce runnable strategies (no import errors, no missing config)
- [ ] `build_pattern_from_config()` with default Pydantic config extracts same params as no-arg constructor for all 7 patterns
- [ ] Non-PatternModule strategies (ORB_BREAKOUT, ORB_SCALP, VWAP_RECLAIM, AFTERNOON_MOMENTUM, RED_TO_GREEN) are completely unchanged

### PatternModule min_detection_bars Backward Compatibility (S2)
- [ ] All 9 existing PatternModule patterns (Bull Flag, Flat-Top, Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, PMH + 3 new) have `min_detection_bars == lookback_bars` by default (except PMH)
- [ ] PatternBasedStrategy with an existing pattern (e.g., BullFlag, lookback=20) fires detection at exactly the same bar count as before
- [ ] PMH with `lookback_bars=400` and `min_detection_bars=10` allows detection after 10 bars (not 400)

### Strategy Signal Generation (All Sessions)
- [ ] Existing 12 strategies produce identical signals under identical market conditions (no code changes to detection logic of existing strategies)
- [ ] New strategies only fire within their configured operating windows
- [ ] New strategies emit `share_count=0` with `pattern_strength` for quality pipeline sizing (BaseStrategy contract)
- [ ] New strategies include `atr_value` on SignalEvent (exit management contract)

### Experiment Pipeline (S3–S6)
- [ ] Existing 2 Dip-and-Rip shadow variants remain functional after new patterns are added
- [ ] VariantSpawner correctly registers new pattern types from experiments.yaml
- [ ] ExperimentRunner correctly maps new pattern names to StrategyType enum values
- [ ] `compute_parameter_fingerprint()` produces consistent fingerprints for new patterns

### Config Integrity (S3–S5)
- [ ] New Pydantic config fields match YAML field names exactly (no silently ignored keys)
- [ ] PatternParam default values match Pydantic Field defaults for each new pattern
- [ ] PatternParam min/max ranges fall within Pydantic Field ge/le bounds for each new pattern
- [ ] Cross-validation tests exist for all 3 new pattern configs

### Test Suite Health (All Sessions)
- [ ] No test count decrease at any session close-out
- [ ] All pre-existing tests pass at every session close-out
- [ ] Vitest 846 tests unchanged (no frontend modifications in this sprint)
- [ ] Full suite run (pytest + Vitest) green at sprint entry and exit

### File Scope Compliance
- [ ] No modifications to: orchestrator.py, risk_manager.py, intelligence/learning/, ai/, api/ (routes), ui/, existing pattern files, existing strategy config YAMLs
- [ ] order_manager.py modifications limited to DEF-144 tracking attributes (no behavioral changes)
- [ ] pattern_strategy.py modifications limited to min_detection_bars threshold change
- [ ] base.py modifications limited to min_detection_bars property addition

### Reference Data Wiring (S2)
- [ ] PMH strategy instance receives prior_closes via `initialize_reference_data()` after UM routing
- [ ] GapAndGo strategy instance receives prior_closes via `initialize_reference_data()` after UM routing
- [ ] R2G existing `initialize_prior_closes()` wiring is unchanged and still functional
- [ ] Reference data wiring is skipped gracefully when UM is disabled or reference cache is empty
