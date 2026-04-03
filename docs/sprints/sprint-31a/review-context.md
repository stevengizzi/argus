# Sprint 31A: Review Context File

> This file is referenced by all session-level Tier 2 review prompts.
> It contains the Sprint Spec, Specification by Contradiction, Regression Checklist,
> and Escalation Criteria. The reviewer reads this file once and applies it to each session.

---

## Sprint Spec (Embedded)

### Goal
Fix DEF-143 (BacktestEngine pattern init) and DEF-144 (debrief safety_summary), resolve PMH 0-trade root cause (lookback_bars truncation + missing reference data wiring), add 3 new PatternModule strategies (Micro Pullback, VWAP Bounce, Narrow Range Breakout) to reach 15 base strategies, and run full parameter sweep across all 10 PatternModule patterns.

### Deliverables
1. DEF-143: BacktestEngine `_create_*_strategy()` → `build_pattern_from_config()` for all 7 PatternModule patterns
2. DEF-144: OrderManager safety tracking attributes → debrief export safety_summary
3. PMH fix: `min_detection_bars` on PatternModule ABC, PMH `lookback_bars=400`/`min_detection_bars=10`, reference data wiring for PMH + GapAndGo
4. Micro Pullback pattern (complete: pattern + config + Pydantic + wiring + tests)
5. VWAP Bounce pattern (complete)
6. Narrow Range Breakout pattern (complete)
7. Full parameter sweep all 10 PatternModule patterns → experiments.yaml

### Session Structure
S1 (DEF-143+144) → S2 (PMH fix) → S3 (Micro Pullback) → S4 (VWAP Bounce) → S5 (NR Breakout) → S6 (Sweep). All sequential.

### Key Acceptance Criteria
- BacktestEngine `--params` sweeps change detection behavior for all 7 existing patterns
- Default-params BacktestEngine runs produce identical results to pre-fix
- `min_detection_bars` defaults to `lookback_bars` → existing patterns unchanged
- PMH detect() works with 330 PM + 10 market candles (full PM session in deque)
- Each new pattern: PatternModule ABC, Pydantic config with cross-validation, full wiring, tests
- Qualifying sweep variants (Sharpe > 0.5, trades ≥ 30, expectancy > 0) added to experiments.yaml

---

## Specification by Contradiction (Embedded)

### Out of Scope
- ABCD O(n³) optimization (DEF-122)
- Time-of-day conditioning (DEF-125), regime profiles (DEF-126)
- Standalone strategy changes (ORB, VWAP Reclaim, AfMo, R2G)
- Experiment pipeline infrastructure changes
- Frontend/UI work, strategy identity assignments
- Exit management tuning, Learning Loop changes
- Short selling (Sprint 30)

### Do NOT Modify
- `argus/core/orchestrator.py`, `argus/core/risk_manager.py`
- `argus/intelligence/learning/` (entire directory)
- `argus/ai/`, `argus/api/` (no route changes), `argus/ui/`
- Existing pattern files (bull_flag, flat_top, dip_and_rip, hod_break, gap_and_go, abcd — read-only)
- Existing strategy config YAMLs
- `argus/data/universe_manager.py`

### Edge Cases to Reject
- Micro Pullback with no clear impulse → return None
- VWAP Bounce when VWAP unavailable → return None
- VWAP Bounce when price below VWAP → return None (that's VWAP Reclaim)
- NR Breakout downward → return None (long-only)
- PMH with zero backfill → won't fire until bars accumulate (correct)

---

## Regression Checklist (Embedded)

### BacktestEngine Parity (S1)
- [ ] Default-config BacktestEngine runs produce identical results for all 7 existing patterns
- [ ] `build_pattern_from_config()` extracts same params as no-arg constructor
- [ ] Non-PatternModule strategies unchanged

### min_detection_bars Backward Compat (S2)
- [ ] All existing patterns: `min_detection_bars == lookback_bars` by default
- [ ] Existing patterns fire at same bar count as before
- [ ] PMH fires after 10 bars, not 400

### Signal Generation (All)
- [ ] Existing 12 strategies produce identical signals
- [ ] New strategies fire only within operating windows
- [ ] New strategies emit `share_count=0` + `pattern_strength` + `atr_value`

### Experiment Pipeline (S3–S6)
- [ ] Existing Dip-and-Rip variants functional
- [ ] VariantSpawner/ExperimentRunner/fingerprint consistent for new patterns

### Config Integrity (S3–S5)
- [ ] YAML field names match Pydantic exactly
- [ ] PatternParam defaults match Pydantic Field defaults
- [ ] PatternParam ranges within Pydantic bounds
- [ ] Cross-validation tests exist for all 3 new configs

### Test Suite Health
- [ ] No test count decrease at any close-out
- [ ] Vitest 846 unchanged
- [ ] Full suite green at sprint entry and exit

### File Scope
- [ ] No unauthorized file modifications (see Do NOT Modify list above)
- [ ] order_manager.py limited to tracking attributes
- [ ] pattern_strategy.py limited to min_detection_bars threshold
- [ ] base.py limited to min_detection_bars property

### Reference Data (S2)
- [ ] PMH + GapAndGo receive prior_closes via initialize_reference_data()
- [ ] R2G wiring unchanged
- [ ] Graceful skip when UM disabled

---

## Escalation Criteria (Embedded)

### Tier 3 (STOP — escalate to Claude.ai)
1. DEF-143 fix breaks existing backtest results
2. min_detection_bars changes existing pattern behavior
3. New pattern signals appear outside operating window
4. Test count decreases at any session
5. Parameter sweep shows BacktestEngine still ignoring config_overrides

### Handle Within Session
- Cross-validation failures → fix divergent values
- EMA/VWAP indicator unavailable → compute from candle data
- S2 reference data wiring exceeds budget → defer to S2b
- Pattern sweep finds 0 qualifying variants → document, don't lower thresholds
- ABCD sweep slow → expected (DEF-122), document timing

### Reserved Numbers
- DEF: 145–155
- DEC: 382–390 (if needed)
