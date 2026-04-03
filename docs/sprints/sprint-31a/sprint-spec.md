# Sprint 31A: Pattern Expansion III — Reach 15 Strategies

## Goal

Fix two blocking defects (DEF-143 BacktestEngine pattern init, DEF-144 debrief safety_summary), resolve the Pre-Market High Break 0-trade root cause (lookback_bars truncation + missing reference data wiring), add 3 new PatternModule strategies (Micro Pullback, VWAP Bounce, Narrow Range Breakout) to reach 15 base strategies, and run a full parameter sweep across all 10 PatternModule patterns to populate experiments.yaml with qualifying shadow variants.

## Scope

### Deliverables

1. **DEF-143 Fix: BacktestEngine Pattern Init** — Replace 7 no-arg pattern constructors in `_create_*_strategy()` methods with `build_pattern_from_config()` calls, mirroring main.py's established pattern. `--params` sweeps now change detection behavior for all 7 PatternModule patterns.

2. **DEF-144 Fix: Debrief Export Safety Summary** — Add tracking attributes to OrderManager for margin circuit breaker state (open_time, reset_time, entries_blocked), EOD flatten pass results (pass_1_count, pass_2_count), and signal cutoff count (signals_skipped). Wire into debrief export safety_summary section.

3. **PMH 0-Trade Fix** — Add `min_detection_bars` optional property to PatternModule ABC. Update PatternBasedStrategy to use `lookback_bars` for deque maxlen and `min_detection_bars` for detection-eligibility threshold. Set PMH `lookback_bars=400` and `min_detection_bars=10`. Wire `initialize_reference_data()` for PMH and GapAndGo in main.py's UM routing phase.

4. **Micro Pullback Pattern** — New PatternModule detecting the first shallow pullback to a short-term EMA after a strong directional move. Window: 10:00–14:00 ET. Complete with Pydantic config, universe filter, BacktestEngine integration, and experiment pipeline wiring.

5. **VWAP Bounce Pattern** — New PatternModule detecting price testing VWAP from above and holding, with volume confirmation on the bounce candle. Window: 10:30–15:00 ET. Complete with full integration stack.

6. **Narrow Range Breakout Pattern** — New PatternModule detecting consolidation via narrowing range bars followed by a volume-confirmed breakout. Window: 10:00–15:00 ET. Complete with full integration stack.

7. **Full Parameter Sweep** — Run `scripts/run_experiment.py` for all 10 PatternModule patterns against the 96-month Parquet cache. Write qualifying variants (trades ≥ 30, expectancy > 0, Sharpe > 0.5) to `config/experiments.yaml` as shadow variants.

### Acceptance Criteria

1. **DEF-143 Fix:**
   - `BacktestEngine._create_bull_flag_strategy()` (and all 6 other pattern methods) calls `build_pattern_from_config()` instead of no-arg constructor
   - New test: passing `config_overrides={"min_dip_percent": 0.05}` to BacktestEngine with DipAndRip strategy type produces different detection behavior than default params
   - All existing BacktestEngine tests pass unchanged (default params produce identical results)

2. **DEF-144 Fix:**
   - OrderManager exposes `margin_circuit_breaker_open_time`, `margin_circuit_breaker_reset_time`, `margin_entries_blocked_count`, `eod_flatten_pass1_count`, `eod_flatten_pass2_count`, `signal_cutoff_skipped_count` as readable attributes
   - Debrief export `safety_summary` section contains non-null values for these fields after relevant events occur
   - Debrief export without relevant events produces zero/None values (no crash)

3. **PMH 0-Trade Fix:**
   - `PatternModule.min_detection_bars` property exists, defaults to `lookback_bars`
   - `PatternBasedStrategy` uses `min_detection_bars` for the `bar_count < threshold` check
   - PMH `lookback_bars` is 400, `min_detection_bars` is 10
   - New test: PMH detect() with 330 PM candles + 10 market candles finds PM high from the full PM session (not truncated)
   - New test: PMH pattern wrapped in PatternBasedStrategy receives prior_closes via `initialize_reference_data()` and `_resolve_prior_close()` returns non-None
   - Existing patterns with default `min_detection_bars` unchanged: behavior identical to current (lookback check uses lookback_bars)

4. **Micro Pullback Pattern:**
   - `MicroPullbackPattern` implements PatternModule ABC (name, lookback_bars, detect, score, get_default_params)
   - Detection logic: identifies rolling high from recent bars, detects pullback to EMA zone (within configurable tolerance), confirms recovery candle (close above EMA with volume), computes entry/stop/target
   - `get_default_params()` returns `list[PatternParam]` with min/max/step for all tunable params
   - `MicroPullbackConfig` Pydantic model in config.py with Field bounds matching PatternParam ranges
   - Cross-validation test: PatternParam defaults match config Field defaults
   - Cross-validation test: PatternParam min/max within Pydantic Field ge/le bounds
   - Wired into main.py, BacktestEngine (via `build_pattern_from_config()`), factory registry, experiment runner mapping
   - `StrategyType.MICRO_PULLBACK` added to enum
   - Config YAML and universe filter YAML created
   - Unit tests for detect() with synthetic candles (positive detection, edge case rejection)
   - Unit tests for score() boundary values

5. **VWAP Bounce Pattern:**
   - Same criteria as Micro Pullback, with detection logic: price approaches VWAP from above (within configurable distance), tests/touches VWAP support level, bounce candle closes above VWAP with volume confirmation, entry above bounce candle high
   - `VwapBounceConfig` Pydantic model
   - `StrategyType.VWAP_BOUNCE` added to enum
   - Full wiring + tests

6. **Narrow Range Breakout Pattern:**
   - Same criteria as Micro Pullback, with detection logic: identifies N consecutive bars where range narrows (each bar's range ≤ previous bar's range × tolerance), breakout candle closes outside the consolidation range with volume confirmation, directional bias from candle body alignment
   - `NarrowRangeBreakoutConfig` Pydantic model
   - `StrategyType.NARROW_RANGE_BREAKOUT` added to enum
   - Full wiring + tests

7. **Full Parameter Sweep:**
   - All 10 PatternModule patterns swept via `scripts/run_experiment.py`
   - Each pattern: single-param sensitivity sweep on top 2–3 params, then multi-param optimization
   - Qualifying variants (trades ≥ 30, expectancy > 0, Sharpe > 0.5) added to `config/experiments.yaml`
   - Sweep uses `--cache-dir data/databento_cache` (96-month Parquet cache)
   - Symbol set: 24 representative momentum symbols (established from Sprint 31A prep)
   - Non-qualifying patterns documented (which patterns, best results achieved, why rejected)

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| BacktestEngine default-params parity | Identical results pre/post DEF-143 fix | Run DipAndRip default sweep, compare trade count + Sharpe |
| PMH detection in expanded deque | detect() returns non-None with 330 PM + 10 market candles | Unit test with synthetic candle data |
| New pattern sweep | Each pattern produces ≥ 1 configuration with Sharpe > 0 | run_experiment.py output |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `strategies/micro_pullback.yaml: ema_period` | `MicroPullbackConfig` | `ema_period` | `9` |
| `strategies/micro_pullback.yaml: pullback_tolerance_atr` | `MicroPullbackConfig` | `pullback_tolerance_atr` | `0.3` |
| `strategies/micro_pullback.yaml: min_impulse_percent` | `MicroPullbackConfig` | `min_impulse_percent` | `0.02` |
| `strategies/micro_pullback.yaml: min_impulse_bars` | `MicroPullbackConfig` | `min_impulse_bars` | `3` |
| `strategies/micro_pullback.yaml: max_pullback_bars` | `MicroPullbackConfig` | `max_pullback_bars` | `5` |
| `strategies/micro_pullback.yaml: min_bounce_volume_ratio` | `MicroPullbackConfig` | `min_bounce_volume_ratio` | `1.2` |
| `strategies/micro_pullback.yaml: stop_buffer_atr_mult` | `MicroPullbackConfig` | `stop_buffer_atr_mult` | `0.5` |
| `strategies/micro_pullback.yaml: target_ratio` | `MicroPullbackConfig` | `target_ratio` | `2.0` |
| `strategies/micro_pullback.yaml: target_1_r` | `MicroPullbackConfig` | `target_1_r` | `1.0` |
| `strategies/micro_pullback.yaml: target_2_r` | `MicroPullbackConfig` | `target_2_r` | `2.0` |
| `strategies/micro_pullback.yaml: time_stop_minutes` | `MicroPullbackConfig` | `time_stop_minutes` | `30` |
| `strategies/vwap_bounce.yaml: vwap_approach_distance_pct` | `VwapBounceConfig` | `vwap_approach_distance_pct` | `0.005` |
| `strategies/vwap_bounce.yaml: vwap_touch_tolerance_pct` | `VwapBounceConfig` | `vwap_touch_tolerance_pct` | `0.002` |
| `strategies/vwap_bounce.yaml: min_bounce_bars` | `VwapBounceConfig` | `min_bounce_bars` | `2` |
| `strategies/vwap_bounce.yaml: min_bounce_volume_ratio` | `VwapBounceConfig` | `min_bounce_volume_ratio` | `1.3` |
| `strategies/vwap_bounce.yaml: min_prior_trend_bars` | `VwapBounceConfig` | `min_prior_trend_bars` | `10` |
| `strategies/vwap_bounce.yaml: min_price_above_vwap_pct` | `VwapBounceConfig` | `min_price_above_vwap_pct` | `0.003` |
| `strategies/vwap_bounce.yaml: stop_buffer_atr_mult` | `VwapBounceConfig` | `stop_buffer_atr_mult` | `0.5` |
| `strategies/vwap_bounce.yaml: target_ratio` | `VwapBounceConfig` | `target_ratio` | `2.0` |
| `strategies/vwap_bounce.yaml: target_1_r` | `VwapBounceConfig` | `target_1_r` | `1.0` |
| `strategies/vwap_bounce.yaml: target_2_r` | `VwapBounceConfig` | `target_2_r` | `2.0` |
| `strategies/vwap_bounce.yaml: time_stop_minutes` | `VwapBounceConfig` | `time_stop_minutes` | `30` |
| `strategies/narrow_range_breakout.yaml: nr_lookback` | `NarrowRangeBreakoutConfig` | `nr_lookback` | `7` |
| `strategies/narrow_range_breakout.yaml: min_narrowing_bars` | `NarrowRangeBreakoutConfig` | `min_narrowing_bars` | `3` |
| `strategies/narrow_range_breakout.yaml: range_decay_tolerance` | `NarrowRangeBreakoutConfig` | `range_decay_tolerance` | `1.05` |
| `strategies/narrow_range_breakout.yaml: breakout_margin_percent` | `NarrowRangeBreakoutConfig` | `breakout_margin_percent` | `0.001` |
| `strategies/narrow_range_breakout.yaml: min_breakout_volume_ratio` | `NarrowRangeBreakoutConfig` | `min_breakout_volume_ratio` | `1.5` |
| `strategies/narrow_range_breakout.yaml: consolidation_max_range_atr` | `NarrowRangeBreakoutConfig` | `consolidation_max_range_atr` | `0.8` |
| `strategies/narrow_range_breakout.yaml: stop_buffer_atr_mult` | `NarrowRangeBreakoutConfig` | `stop_buffer_atr_mult` | `0.5` |
| `strategies/narrow_range_breakout.yaml: target_ratio` | `NarrowRangeBreakoutConfig` | `target_ratio` | `2.0` |
| `strategies/narrow_range_breakout.yaml: target_1_r` | `NarrowRangeBreakoutConfig` | `target_1_r` | `1.0` |
| `strategies/narrow_range_breakout.yaml: target_2_r` | `NarrowRangeBreakoutConfig` | `target_2_r` | `2.0` |
| `strategies/narrow_range_breakout.yaml: time_stop_minutes` | `NarrowRangeBreakoutConfig` | `time_stop_minutes` | `45` |

Note: Config field names listed above are the primary detection and trade parameters. All 3 new configs also inherit standard StrategyConfig fields (strategy_id, name, version, enabled, mode, asset_class, pipeline_stage, family, description_short, time_window_display, operating_window, risk_limits, benchmarks, backtest_summary, universe_filter, exit_management). These are not listed individually as they follow the established template exactly.

## Dependencies

- Sprint 32.9 complete (experiments.enabled: true, max_concurrent_positions: 50, EOD flatten sync)
- Sprint 32.75 complete (The Arena, strategy identity system — new strategies need colors/badges)
- Good Friday hotfix complete (market_calendar.py, OHLCV-1m observability)
- 96-month Parquet cache on LaCie drive populated and mounted at `/Volumes/LaCie/argus-cache` or `data/databento_cache` (for S6 sweep)
- `build_pattern_from_config()` factory in `argus/strategies/patterns/factory.py` (Sprint 32) — existing, no changes needed
- PatternModule ABC in `argus/strategies/patterns/base.py` (Sprint 26/29) — modified in S2 for min_detection_bars

## Relevant Decisions

- DEC-028: Strategy statefulness — daily-stateful, session-stateless plugins. New patterns must conform.
- DEC-047: Walk-forward validation mandatory, WFE > 0.3. Applies to new patterns when validated.
- DEC-132: Pre-Databento parameter optimization requires re-validation. DEF-143 fix enables proper re-validation.
- DEC-277: Fail-closed on missing reference data. Universe filter configs must specify conservative defaults.
- DEC-300: Config-gated features. New patterns enabled via strategy YAML `enabled: true`.
- DEC-343: Watchlist population from UM routing via `set_watchlist(symbols, source="universe_manager")`.
- DEC-345: Separate SQLite databases per domain (evaluation.db, counterfactual.db, etc.). No new DBs in this sprint.

## Relevant Risks

- RSK-022: IBKR Gateway nightly resets — no impact on this sprint (code-only, no live infra changes).
- General: new patterns may have zero edge. Parameter sweep (D7) is the validation gate. Patterns with no qualifying configurations are documented but still kept in codebase as shadow-mode candidates.

## Session Count Estimate

6 sessions estimated. S1 (defect fixes), S2 (PMH fix), S3–S5 (one session per new pattern, strictly sequential due to shared file modifications), S6 (operational sweep + config). No frontend sessions — no visual-review fix budget needed.

## Pattern Design Details

### Micro Pullback (Strategy 13)

**Mechanic:** After a strong impulsive move (≥ min_impulse_percent over min_impulse_bars), the first pullback that touches or enters the short-term EMA zone (within pullback_tolerance_atr × ATR of the EMA) is a continuation entry. The bounce candle must close above the EMA with volume confirmation.

**Why it's distinct:** Dip-and-Rip requires a deep dip (≥ 2%) and looks for VWAP/level interaction. Micro Pullback targets shallow retracements (typically < 1%) to a moving average after a proven impulse. The pullback is measured against the EMA, not against absolute price drop.

**Detection flow:**
1. Compute EMA(ema_period) from candle closes
2. Identify impulse: rolling high - low_N_bars_ago ≥ min_impulse_percent × price, completed within min_impulse_bars
3. Check pullback: price retraces to within pullback_tolerance_atr × ATR of EMA, within max_pullback_bars of impulse end
4. Bounce confirmation: candle closes above EMA with volume ≥ min_bounce_volume_ratio × avg recent volume
5. Entry at bounce candle close, stop below pullback low - ATR buffer, target via ratio

**Scoring (30/25/25/20):**
- Impulse strength (30): larger % move + faster completion
- Pullback quality (25): shallower pullback + clean EMA touch
- Volume profile (25): stronger bounce volume ratio
- Trend context (20): price position relative to VWAP

**Operating window:** 10:00 AM – 14:00 ET. Covers the midday gap where only wide-window patterns operate.

**Universe filter:** min_price: 5.0, max_price: 200.0, min_avg_volume: 500000. Higher volume floor than some patterns because EMA pullbacks work best on liquid names.

### VWAP Bounce (Strategy 14)

**Mechanic:** Stock trading above VWAP pulls back to test VWAP as support. Price touches or slightly penetrates VWAP, then bounces with volume confirmation. This is the continuation-side complement to VWAP Reclaim (which enters when price reclaims VWAP from below).

**Why it's distinct:** VWAP Reclaim enters on a cross from below. VWAP Bounce enters on a bounce from above — the stock was already bullish (above VWAP) and is retesting the mean. Different entry mechanics, different risk/reward profile.

**Detection flow:**
1. Confirm prior uptrend: price was above VWAP for ≥ min_prior_trend_bars
2. Approach: price moves within vwap_approach_distance_pct of VWAP
3. Touch/test: candle low within vwap_touch_tolerance_pct of VWAP (can slightly undershoot)
4. Bounce: min_bounce_bars consecutive bars with close > VWAP, bounce bar volume ≥ min_bounce_volume_ratio × avg
5. Entry at bounce confirmation close, stop below VWAP - ATR buffer, target via ratio

**Scoring (30/25/25/20):**
- VWAP interaction quality (30): cleaner touch (low within tolerance) + faster bounce
- Prior trend strength (25): duration above VWAP + distance maintained
- Volume profile (25): bounce volume ratio
- Price structure (20): higher lows during approach

**Operating window:** 10:30 AM – 15:00 ET. Avoids the open (VWAP unstable) and extends into afternoon.

**Universe filter:** min_price: 5.0, max_price: 200.0, min_avg_volume: 500000.

### Narrow Range Breakout (Strategy 15)

**Mechanic:** Identifies consolidation via progressively narrowing bar ranges (each bar's high-low range ≤ prior bar's range × range_decay_tolerance). After min_narrowing_bars of range contraction within a tight ATR-relative band, a breakout candle closes outside the consolidation range with volume surge. Long-biased (breakout above consolidation high).

**Why it's distinct:** HOD Break requires proximity to session high + specific resistance mechanics. Flat-Top Breakout requires resistance clustering at a flat level. Narrow Range Breakout is purely about volatility compression → expansion, with no directional or level requirement at the setup stage. It works in the midday lull when volatility compresses before afternoon expansion.

**Detection flow:**
1. Scan for narrowing range sequence: N consecutive bars where range(i) ≤ range(i-1) × range_decay_tolerance
2. Validate consolidation: overall range of the consolidation ≤ consolidation_max_range_atr × ATR
3. Identify consolidation boundaries: high = max(highs), low = min(lows) of narrowing bars
4. Breakout detection: candle close > consolidation high + breakout_margin_percent × price
5. Volume confirmation: breakout bar volume ≥ min_breakout_volume_ratio × avg consolidation volume
6. Entry at breakout close, stop below consolidation low - ATR buffer, target via ratio

**Scoring (30/25/25/20):**
- Consolidation quality (30): more narrowing bars + tighter final range
- Breakout strength (25): margin above consolidation + volume ratio
- Volume profile (25): volume during consolidation (lower = better) vs breakout (higher = better)
- Range context (20): consolidation range relative to ATR

**Operating window:** 10:00 AM – 15:00 ET. Wide window — NR breakouts happen throughout the day.

**Universe filter:** min_price: 5.0, max_price: 200.0, min_avg_volume: 300000.
