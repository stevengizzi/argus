# Sprint 31A: Session Breakdown

## Dependency Chain

```
S1 (DEF-143 + DEF-144) → S2 (PMH fix) → S3 (Micro Pullback) → S4 (VWAP Bounce) → S5 (NR Breakout) → S6 (Sweep)
```

All sessions are strictly sequential. S3–S5 modify overlapping files (config.py, main.py, engine.py, factory.py, runner.py). S6 depends on all prior sessions.

**Parallelizable sessions:** None.

---

## Session 1: DEF-143 BacktestEngine Fix + DEF-144 Debrief Safety Summary

**Objective:** Replace 7 no-arg pattern constructors in BacktestEngine with `build_pattern_from_config()`. Add safety tracking attributes to OrderManager and wire into debrief export.

**Creates:**
- Tests: config_override passthrough tests for BacktestEngine pattern creation (~7 tests, one per pattern type); debrief safety_summary population tests (~3 tests)

**Modifies:**
- `argus/backtest/engine.py` — 7 `_create_*_strategy()` methods: replace `PatternXyz()` with `build_pattern_from_config(config, "pattern_name")`
- `argus/execution/order_manager.py` — Add tracking attributes: `margin_circuit_breaker_open_time`, `margin_circuit_breaker_reset_time`, `margin_entries_blocked_count`, `eod_flatten_pass1_count`, `eod_flatten_pass2_count`, `signal_cutoff_skipped_count`; increment in relevant code paths
- `argus/analytics/debrief_export.py` — Wire OrderManager tracking attrs into `safety_summary` section

**Integrates:** N/A (fixes existing code)

**Parallelizable:** No

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 3 (engine.py, order_manager.py, debrief_export.py) | 3 |
| Pre-flight context reads | 5 (engine.py, factory.py, order_manager.py, debrief_export.py, existing tests) | 5 |
| New tests | ~10 | 5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **13 (Medium)** |

---

## Session 2: PMH 0-Trade Fix

**Objective:** Add `min_detection_bars` to PatternModule ABC. Update PatternBasedStrategy detection threshold. Fix PMH lookback. Wire reference data for PMH and GapAndGo.

**Root cause:** `lookback_bars=30` truncates PM candle history to ~25 minutes (only 9:05–9:30 AM retained in deque). PM high computed from partial data. By 9:55 AM, zero PM candles remain → detection impossible. Secondary: `initialize_reference_data()` never called for PatternBasedStrategy patterns, so PMH/GapAndGo gap scoring always 0.0.

**Creates:**
- Tests: min_detection_bars behavior (~2 tests), PMH detection with full PM deque (~2 tests), reference data wiring verification (~2 tests), backward compatibility for existing patterns (~2 tests)

**Modifies:**
- `argus/strategies/patterns/base.py` — Add `min_detection_bars` property (default: `lookback_bars`)
- `argus/strategies/pattern_strategy.py` — Change `bar_count < self._pattern.lookback_bars` to `bar_count < self._pattern.min_detection_bars` on the detection-eligibility check (line ~293); also update the partial-history threshold computation
- `argus/strategies/patterns/premarket_high_break.py` — `lookback_bars` → 400, add `min_detection_bars` property returning 10
- `argus/main.py` — After UM routing populates strategy watchlists (Phase 9.5), call `initialize_reference_data()` on PMH and GapAndGo strategy instances with UM reference data (prior_closes dict built from `universe_manager.get_reference_data()`)

**Integrates:** N/A (fixes existing code)

**Parallelizable:** No

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 (base.py, pattern_strategy.py, premarket_high_break.py, main.py) | 4 |
| Pre-flight context reads | 6 (premarket_high_break.py, pattern_strategy.py, base.py, main.py, gap_and_go.py, universe_manager.py) | 6 |
| New tests | ~8 | 4 |
| Complex integration wiring | 0 (main.py change is straightforward addition) | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **14 (High — borderline)** |

**Mitigation:** Each change is small and self-contained (1 property, 1 comparison, 1 value, ~15 lines wiring). If session runs long, reference data wiring (main.py) can be deferred to a 2b micro-session.

---

## Session 3: Micro Pullback Pattern (Complete)

**Objective:** Implement MicroPullbackPattern with full wiring into BacktestEngine, experiment pipeline, and startup.

**Detection logic:** After a strong impulse (≥ min_impulse_percent over min_impulse_bars), first pullback into EMA zone (within pullback_tolerance_atr × ATR), bounce candle closes above EMA with volume confirmation.

**Creates:**
- `argus/strategies/patterns/micro_pullback.py` (~200 lines: class, detect, score, get_default_params)
- `config/strategies/micro_pullback.yaml` (template from dip_and_rip.yaml)
- `config/universe_filters/micro_pullback.yaml` (template from existing)
- Tests: detection, scoring, edge cases, cross-validation (~10 tests)

**Modifies:**
- `argus/core/config.py` — Add `MicroPullbackConfig(StrategyConfig)` Pydantic model
- `argus/main.py` — Add micro_pullback strategy creation block (following existing pattern)
- `argus/backtest/config.py` — Add `MICRO_PULLBACK = "micro_pullback"` to StrategyType enum
- `argus/backtest/engine.py` — Add `_create_micro_pullback_strategy()` method using `build_pattern_from_config()`
- `argus/strategies/patterns/factory.py` — Add entries to `_PATTERN_REGISTRY` and `_SNAKE_CASE_ALIASES`
- `argus/intelligence/experiments/runner.py` — Add `"micro_pullback": StrategyType.MICRO_PULLBACK` to `_PATTERN_TO_STRATEGY_TYPE`

**Integrates:** S1 DEF-143 fix (engine creation method uses `build_pattern_from_config()`)

**Parallelizable:** No (modifies config.py, main.py, engine.py shared with S4/S5)

**Compaction Risk Scoring (with template-following adjustment):**

| Factor | Count | Points | Adjusted |
|--------|-------|--------|----------|
| New files created | 1 (micro_pullback.py) | 2 | 2 |
| Template config YAMLs | 2 (strategy + filter) | 4 | 2† |
| Files modified | 6 (config.py, main.py, backtest/config.py, engine.py, factory.py, runner.py) | 6 | 3† |
| Pre-flight context reads | 5 (base.py, dip_and_rip.py ref, factory.py, config.py, main.py) | 5 | 3† |
| New tests | ~10 | 5 | 5 |
| Complex integration wiring | 1 (6 files but template-following) | 3 | 1.5† |
| Large files (>150 lines) | 1 (micro_pullback.py) | 2 | 2 |
| **Total** | | **27 raw** | **18.5 adjusted → ~13 effective†** |

†Template-following adjustment rationale: All 6 file modifications are 1–5 lines each, copied from existing patterns verbatim. Config YAMLs are YAML templates with changed values. Context reads reduced because the pattern follows a well-established ABC interface. Integration wiring is mechanical copy-paste. The creative work is only the 200-line pattern file.

---

## Session 4: VWAP Bounce Pattern (Complete)

**Objective:** Implement VwapBouncePattern with full wiring.

**Detection logic:** Price trading above VWAP for min_prior_trend_bars pulls back to within vwap_approach_distance_pct, tests VWAP (low within vwap_touch_tolerance_pct), bounces with min_bounce_bars consecutive bars closing above VWAP + volume confirmation.

**Creates:**
- `argus/strategies/patterns/vwap_bounce.py` (~200 lines)
- `config/strategies/vwap_bounce.yaml`
- `config/universe_filters/vwap_bounce.yaml`
- Tests: detection, scoring, edge cases, cross-validation (~10 tests)

**Modifies:**
- `argus/core/config.py` — Add `VwapBounceConfig(StrategyConfig)`
- `argus/main.py` — Add vwap_bounce strategy creation block
- `argus/backtest/config.py` — Add `VWAP_BOUNCE` to StrategyType enum
- `argus/backtest/engine.py` — Add creation method
- `argus/strategies/patterns/factory.py` — Add registry entries
- `argus/intelligence/experiments/runner.py` — Add mapping entry

**Integrates:** S1 DEF-143 fix

**Parallelizable:** No

**Compaction Risk Scoring (adjusted):**

| Factor | Points (adjusted) |
|--------|-------------------|
| New files | 2 |
| Template YAMLs | 2 |
| Files modified (6 × 0.5†) | 3 |
| Context reads (reduced — S3 established pattern) | 2 |
| New tests (~10) | 5 |
| Integration wiring (template) | 1 |
| Large file | 2 |
| **Total** | **~17 raw → ~12 effective** |

†S3 establishes the exact wiring pattern; S4 is mechanical repetition.

---

## Session 5: Narrow Range Breakout Pattern (Complete)

**Objective:** Implement NarrowRangeBreakoutPattern with full wiring.

**Detection logic:** Scan for min_narrowing_bars consecutive bars where range(i) ≤ range(i-1) × range_decay_tolerance. Consolidation overall range ≤ consolidation_max_range_atr × ATR. Breakout candle closes above consolidation high + breakout_margin_percent with volume ≥ min_breakout_volume_ratio × avg consolidation volume.

**Creates:**
- `argus/strategies/patterns/narrow_range_breakout.py` (~200 lines)
- `config/strategies/narrow_range_breakout.yaml`
- `config/universe_filters/narrow_range_breakout.yaml`
- Tests: detection, scoring, edge cases, cross-validation (~10 tests)

**Modifies:**
- `argus/core/config.py` — Add `NarrowRangeBreakoutConfig(StrategyConfig)`
- `argus/main.py` — Add narrow_range_breakout strategy creation block
- `argus/backtest/config.py` — Add `NARROW_RANGE_BREAKOUT` to StrategyType enum
- `argus/backtest/engine.py` — Add creation method
- `argus/strategies/patterns/factory.py` — Add registry entries
- `argus/intelligence/experiments/runner.py` — Add mapping entry

**Integrates:** S1 DEF-143 fix

**Parallelizable:** No

**Compaction Risk Scoring (adjusted):**

| Factor | Points (adjusted) |
|--------|-------------------|
| Same profile as S4 | ~12 effective |

---

## Session 6: Full Parameter Sweep + Experiments Config

**Objective:** Run parameter sweeps across all 10 PatternModule patterns against the 96-month Parquet cache. Write qualifying variants to experiments.yaml.

**Workflow per pattern:**
1. `python scripts/run_experiment.py --pattern {name} --cache-dir data/databento_cache --dry-run` — check grid size
2. Single-param sensitivity sweeps on top 2–3 params
3. Multi-param optimization on best param combinations
4. Evaluate: trades ≥ 30, expectancy > 0, Sharpe > 0.5
5. Qualifying variants added to `config/experiments.yaml`

**Creates:**
- Sweep results documentation (optional: `docs/sprints/sprint-31a/sweep-results.md`)
- Integration verification tests (~3 tests: verify all 10 patterns runnable in BacktestEngine)

**Modifies:**
- `config/experiments.yaml` — Add qualifying variant definitions

**Integrates:** S1 (BacktestEngine config passthrough), S2 (PMH can fire with expanded deque), S3–S5 (new patterns in BacktestEngine + experiment runner)

**Parallelizable:** No (single sweep session)

**Compaction Risk Scoring:**

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 1 (experiments.yaml) | 1 |
| Pre-flight context reads | 2 (experiments.yaml, run_experiment.py) | 2 |
| New tests | ~3 | 1.5 |
| Complex integration wiring | 0 | 0 |
| External API debugging | 0 | 0 |
| Large files (>150 lines) | 0 | 0 |
| **Total** | | **4.5 (Low)** |

---

## Summary Table

| Session | Scope | Creates | Modifies | Integrates | Score | Risk |
|---------|-------|---------|----------|------------|-------|------|
| S1 | DEF-143 + DEF-144 | tests | engine.py, order_manager.py, debrief_export.py | N/A | 13 | Medium |
| S2 | PMH 0-trade fix | tests | base.py, pattern_strategy.py, premarket_high_break.py, main.py | N/A | 14 | High (borderline) |
| S3 | Micro Pullback | micro_pullback.py + YAMLs + tests | config.py, main.py, backtest/config.py, engine.py, factory.py, runner.py | S1 | ~13 adj | Medium (adj) |
| S4 | VWAP Bounce | vwap_bounce.py + YAMLs + tests | same 6 files | S1 | ~12 adj | Medium (adj) |
| S5 | NR Breakout | narrow_range_breakout.py + YAMLs + tests | same 6 files | S1 | ~12 adj | Medium (adj) |
| S6 | Parameter sweep | results doc + experiments.yaml | experiments.yaml | S1–S5 | 5 | Low |

**Estimated test delta:** ~51 new pytest tests. Target: ~4,725 pytest + 846 Vitest.
