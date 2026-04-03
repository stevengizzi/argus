# Sprint 31A Design Summary

**Sprint Goal:** Fix two blocking defects (DEF-143 BacktestEngine pattern init, DEF-144 debrief safety_summary), resolve the Pre-Market High Break 0-trade issue (lookback_bars truncation + missing reference data wiring), add 3 new PatternModule strategies (Micro Pullback, VWAP Bounce, Narrow Range Breakout) to reach 15 base strategies, and run a full parameter sweep across all 10 PatternModule patterns to populate experiments.yaml with qualifying shadow variants.

**Execution Mode:** Human-in-the-loop

**Session Breakdown:**

- Session 1: DEF-143 fix (BacktestEngine `_create_*_strategy()` → `build_pattern_from_config()`) + DEF-144 fix (OrderManager safety tracking attributes → debrief export wiring)
  - Creates: tests for config_override passthrough + safety_summary population
  - Modifies: `argus/backtest/engine.py` (7 pattern creation methods), `argus/execution/order_manager.py` (tracking attrs), `argus/analytics/debrief_export.py` (safety_summary)
  - Integrates: N/A (fixes existing code)
  - Score: 13 (Medium)

- Session 2: PMH 0-trade fix — add `min_detection_bars` to PatternModule ABC, increase PMH `lookback_bars` to 400, wire `initialize_reference_data()` for PMH + GapAndGo in main.py
  - Creates: tests for lookback/detection threshold behavior, reference data wiring, full PM high computation from expanded deque
  - Modifies: `argus/strategies/patterns/base.py` (+min_detection_bars property), `argus/strategies/pattern_strategy.py` (use min_detection_bars for detection check), `argus/strategies/patterns/premarket_high_break.py` (lookback_bars=400, min_detection_bars=10), `argus/main.py` (wire initialize_reference_data for PMH + GapAndGo)
  - Integrates: N/A (fixes existing code)
  - Score: 14 (High — borderline; each change is small/contained)

- Session 3: Micro Pullback pattern — complete implementation with all wiring
  - Creates: `argus/strategies/patterns/micro_pullback.py`, `config/strategies/micro_pullback.yaml`, `config/universe_filters/micro_pullback.yaml`
  - Modifies: `argus/core/config.py` (+MicroPullbackConfig), `argus/main.py` (+strategy wiring), `argus/backtest/config.py` (+StrategyType.MICRO_PULLBACK), `argus/backtest/engine.py` (+creation method), `argus/strategies/patterns/factory.py` (+registry entries), `argus/intelligence/experiments/runner.py` (+mapping entry)
  - Integrates: S1 DEF-143 fix (engine uses build_pattern_from_config)
  - Score: 17→13 adjusted (template-following PatternModule; 6 file mods are 1–3 lines each)

- Session 4: VWAP Bounce pattern — complete implementation with all wiring
  - Creates: `argus/strategies/patterns/vwap_bounce.py`, `config/strategies/vwap_bounce.yaml`, `config/universe_filters/vwap_bounce.yaml`
  - Modifies: same 6-file set as S3
  - Integrates: S1 DEF-143 fix
  - Score: 16→12 adjusted (S3 established wiring pattern; reduced context reads)

- Session 5: Narrow Range Breakout pattern — complete implementation with all wiring
  - Creates: `argus/strategies/patterns/narrow_range_breakout.py`, `config/strategies/narrow_range_breakout.yaml`, `config/universe_filters/narrow_range_breakout.yaml`
  - Modifies: same 6-file set as S3
  - Integrates: S1 DEF-143 fix
  - Score: 16→12 adjusted (same rationale as S4)

- Session 6: Full parameter sweep across all 10 PatternModule patterns + experiments.yaml update
  - Creates: sweep results documentation (optional: `docs/sprints/sprint-31a/sweep-results.md`)
  - Modifies: `config/experiments.yaml`
  - Integrates: S1 (BacktestEngine properly wires config_overrides), S2 (PMH can fire in backtest with full PM data), S3–S5 (new patterns available)
  - Score: 5 (Low)

**Key Decisions:**

- PMH root cause is `lookback_bars=30` truncating PM candle history to ~25 minutes vs 5.5-hour session. Fix via new `min_detection_bars` property on PatternModule ABC (backward-compatible; defaults to `lookback_bars`). PMH sets `lookback_bars=400` (storage), `min_detection_bars=10` (detection threshold). PatternBasedStrategy uses `lookback_bars` for deque maxlen and `min_detection_bars` for the detection-eligibility check.
- PMH and GapAndGo missing `initialize_reference_data()` wiring in main.py — secondary bug causing gap context scoring to always use 0.0. Fix by wiring in UM routing phase alongside R2G's existing `initialize_prior_closes()`.
- DEF-143 fix: replace 7 no-arg pattern constructors in BacktestEngine with `build_pattern_from_config()` calls, mirroring main.py's pattern. Config overrides flow through Pydantic config → `extract_detection_params()` → pattern constructor kwargs.
- New pattern selection rationale: Micro Pullback (first pullback to EMA after strong move, covers 10:00–14:00 midday gap), VWAP Bounce (VWAP support continuation, complements VWAP Reclaim's from-below approach, covers 10:30–15:00), Narrow Range Breakout (consolidation breakout via narrowing range bars, ideal for midday lull → afternoon expansion, covers 10:00–15:00).
- All 3 new patterns implement PatternModule ABC with `list[PatternParam]` metadata, Pydantic config models with cross-validation tests, and are fully wired into BacktestEngine + experiment pipeline from day one.

**Scope Boundaries:**

- IN: DEF-143 fix, DEF-144 fix, PMH lookback/detection/reference fix, 3 new PatternModule patterns (Micro Pullback, VWAP Bounce, Narrow Range Breakout), BacktestEngine + experiment pipeline integration for all new patterns, full parameter sweep on all 10 patterns, experiments.yaml population
- OUT: DEF-122 (ABCD O(n³) optimization), DEF-125 (time-of-day conditioning), DEF-126 (regime-strategy profiles), standalone strategy changes (ORB, VWAP Reclaim, AfMo, R2G), experiment pipeline infrastructure changes, frontend/UI work, exit management changes, Learning Loop changes, short selling (Sprint 30)

**Regression Invariants:**

- Existing 12 strategies produce identical signals (no behavioral change)
- BacktestEngine default-params runs produce identical results for all existing patterns (DEF-143 fix is behavior-preserving for default params)
- Experiment pipeline's 2 existing Dip-and-Rip shadow variants remain functional
- `min_detection_bars` defaults to `lookback_bars` → existing patterns unchanged
- All existing tests pass (pytest ~4,674 + Vitest 846)

**File Scope:**

- Modify: `argus/backtest/engine.py`, `argus/execution/order_manager.py`, `argus/analytics/debrief_export.py`, `argus/strategies/patterns/base.py`, `argus/strategies/pattern_strategy.py`, `argus/strategies/patterns/premarket_high_break.py`, `argus/main.py`, `argus/core/config.py`, `argus/backtest/config.py`, `argus/strategies/patterns/factory.py`, `argus/intelligence/experiments/runner.py`, `config/experiments.yaml`
- Do not modify: `argus/core/orchestrator.py`, `argus/core/risk_manager.py`, `argus/execution/order_manager.py` (beyond DEF-144 tracking attrs), `argus/intelligence/learning/`, `argus/ai/`, `argus/api/` (no API changes), `argus/ui/` (no frontend changes), existing pattern files (bull_flag, flat_top, dip_and_rip, hod_break, gap_and_go, abcd — read-only reference), existing strategy configs (no parameter changes to existing strategies)

**Config Changes:**

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `strategies/micro_pullback.yaml` | `MicroPullbackConfig` | (all detection params per PatternParam) | (per pattern defaults) |
| `strategies/vwap_bounce.yaml` | `VwapBounceConfig` | (all detection params per PatternParam) | (per pattern defaults) |
| `strategies/narrow_range_breakout.yaml` | `NarrowRangeBreakoutConfig` | (all detection params per PatternParam) | (per pattern defaults) |
| `universe_filters/micro_pullback.yaml` | `UniverseFilterConfig` | min_price, max_price, min_avg_volume | (per pattern) |
| `universe_filters/vwap_bounce.yaml` | `UniverseFilterConfig` | min_price, max_price, min_avg_volume | (per pattern) |
| `universe_filters/narrow_range_breakout.yaml` | `UniverseFilterConfig` | min_price, max_price, min_avg_volume | (per pattern) |

No changes to existing config fields.

**Test Strategy:**

- S1: ~10 tests (7 config passthrough for each pattern type + 3 safety_summary)
- S2: ~8 tests (lookback/detection threshold, reference data, expanded PM detection)
- S3: ~10 tests (pattern detection, scoring, edge cases, cross-validation, wiring)
- S4: ~10 tests (same pattern)
- S5: ~10 tests (same pattern)
- S6: ~3 tests (integration verification, sweep sanity checks)
- Estimated total: ~51 new tests
- Full suite target: ~4,725 pytest + 846 Vitest (0 failures)

**Runner Compatibility:**

- Mode: Human-in-the-loop
- Parallelizable sessions: None (S3/S4/S5 modify overlapping files; S1→S2→S3→S4→S5→S6 strictly sequential)
- Work journal handoff prompt: Yes

**Dependencies:**

- S2 depends on S1 (DEF-143 fix in engine.py; S2 also modifies main.py)
- S3–S5 depend on S1 (engine uses build_pattern_from_config)
- S3–S5 are sequential (shared file modifications)
- S6 depends on S1–S5 (all patterns available, BacktestEngine fixed, PMH firing)
- External: 96-month Parquet cache on LaCie drive (for S6 sweep)

**Escalation Criteria:**

- DEF-143 fix causes existing BacktestEngine tests to fail → investigate before proceeding
- PMH fix causes other PatternBasedStrategy patterns to change behavior → min_detection_bars default must equal lookback_bars
- Any new pattern scores below Sharpe 0.3 across all parameter configurations → assess whether pattern mechanic is sound before completing S6
- Test count drops during any session → immediate investigation

**Doc Updates Needed:**

- `CLAUDE.md`: DEF-143 resolved, DEF-144 resolved, new DEF items from PMH investigation, 3 new strategies added, test counts updated
- `docs/project-knowledge.md`: new strategies table, architecture updates, build track queue, sprint history
- `docs/sprint-history.md`: Sprint 31A entry
- `docs/roadmap.md`: Sprint 31A completion
- `docs/dec-index.md`: any new DECs (unlikely — all decisions follow established patterns)

**Artifacts to Generate:**

1. Sprint Spec
2. Specification by Contradiction
3. Session Breakdown (with Creates/Modifies/Integrates/Score per session)
4. Implementation Prompt ×6
5. Review Prompt ×6
6. Escalation Criteria
7. Regression Checklist
8. Doc Update Checklist
9. Review Context File
10. Work Journal Handoff Prompt
