# Sprint 26: Red-to-Green + Pattern Library Foundation

## Goal

Deliver ARGUS's fifth trading strategy (Red-to-Green gap-down reversal), establish the PatternModule ABC infrastructure for all future pattern development, and validate two pattern modules (Bull Flag, Flat-Top Breakout) — bringing the system from 4 to 7 active strategies/patterns with VectorBT backtesting and walk-forward validation for each.

## Scope

### Deliverables

1. **PatternModule ABC** (`argus/strategies/patterns/base.py`) — Abstract base class defining the interface for reusable pattern detection modules with methods: `detect(candles, indicators) → PatternDetection | None`, `score(detection) → float (0–100)`, `get_default_params() → dict`. Package at `argus/strategies/patterns/`.

2. **PatternBasedStrategy** (`argus/strategies/pattern_strategy.py`) — Generic BaseStrategy subclass that wraps any PatternModule. Handles all BaseStrategy boilerplate (operating window, daily state, position sizing, signal generation, evaluation telemetry) and delegates pattern detection to the wrapped module. Reads operating window, risk limits, and targets from strategy config YAML.

3. **RedToGreenStrategy** (`argus/strategies/red_to_green.py`) — Full BaseStrategy subclass implementing gap-down reversal at key support levels (VWAP, premarket low, prior close). 5-state machine: WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED → EXHAUSTED. Operating window 9:45–11:00 AM ET. Includes `_calculate_pattern_strength()` implementation, scanner criteria, market conditions filter, and `reconstruct_state()`.

4. **RedToGreenConfig** (`argus/core/config.py`) — Pydantic config model + YAML config file + loader function. Includes all R2G-specific parameters, operating window, risk limits, benchmarks, universe filter, and backtest summary.

5. **BullFlagPattern** (`argus/strategies/patterns/bull_flag.py`) — PatternModule implementation detecting bull flag continuation patterns: strong upward pole (min bars, min move %), followed by flag consolidation (declining volume, max retrace %), with breakout above flag high on volume confirmation.

6. **BullFlagConfig** (`argus/core/config.py`) — Pydantic config model + YAML config file + loader. Includes pole/flag/breakout parameters, operating window, risk limits, and targets.

7. **FlatTopBreakoutPattern** (`argus/strategies/patterns/flat_top_breakout.py`) — PatternModule implementation detecting flat-top horizontal resistance breakouts: multiple touches of resistance level (within tolerance), consolidation below resistance, breakout above resistance on volume.

8. **FlatTopBreakoutConfig** (`argus/core/config.py`) — Pydantic config model + YAML config file + loader. Includes resistance/consolidation/breakout parameters, operating window, risk limits, and targets.

9. **VectorBT Red-to-Green backtest** (`argus/backtest/vectorbt_red_to_green.py`) — Parameter sweep + walk-forward validation. Uses Alpaca historical data (provisional per DEC-132).

10. **Generic VectorBT Pattern Backtester** (`argus/backtest/vectorbt_pattern.py`) — Reusable backtester that accepts any PatternModule + PatternBasedStrategy config. Walk-forward validation for Bull Flag and Flat-Top Breakout.

11. **Integration wiring** — R2G, Bull Flag, and Flat-Top registered in `main.py` Phase 8, Orchestrator, and Universe Manager routing. All 7 strategies/patterns served by `/api/v1/strategies` endpoint.

12. **UI** — Pattern Library page displays 3 new strategy/pattern cards with metadata, backtest results, and parameter specs. No new pages or components — existing PatternCard/PatternDetail infrastructure handles new strategies automatically via API data.

13. **Strategy spec sheets** — `STRATEGY_RED_TO_GREEN.md`, `STRATEGY_BULL_FLAG.md`, `STRATEGY_FLAT_TOP_BREAKOUT.md` in `docs/strategies/`.

14. **Tests** — ~76 new pytest + ~8 new Vitest. Total target: ~2,891 pytest + ~619 Vitest.

### Acceptance Criteria

1. **PatternModule ABC:**
   - ABC cannot be instantiated directly (raises TypeError)
   - `detect()`, `score()`, `get_default_params()` are abstract methods
   - `PatternDetection` dataclass contains: pattern_type, confidence (0–100), entry_price, stop_price, metadata dict
   - ≥8 tests covering ABC enforcement, dataclass construction, edge cases

2. **PatternBasedStrategy:**
   - Extends BaseStrategy, passes all abstract method checks
   - Constructor takes `pattern: PatternModule` and `config: StrategyConfig`
   - `on_candle()` delegates to `pattern.detect()`, generates SignalEvent on detection
   - `_calculate_pattern_strength()` delegates to `pattern.score()`
   - Operating window enforced from config
   - Evaluation telemetry recorded via `record_evaluation()`
   - ≥10 tests covering delegation, operating window, signal generation, edge cases

3. **RedToGreenStrategy:**
   - State machine has exactly 5 states with correct transition logic
   - WATCHING → GAP_DOWN_CONFIRMED requires gap_pct < -min_gap_down_pct (negative gap)
   - GAP_DOWN_CONFIRMED → TESTING_LEVEL requires price approaching a key level (VWAP, premarket low, or prior close) within level_proximity_pct
   - TESTING_LEVEL → ENTERED requires: price closes above key level, volume confirmation, within operating window, max_chase guard
   - State machine handles re-tests (TESTING_LEVEL → GAP_DOWN_CONFIRMED on level break)
   - EXHAUSTED state on max_gap_down_pct exceeded, operating window expired, or daily trade limit hit
   - `_calculate_pattern_strength()` returns 0–100 based on: level type quality, volume ratio, gap magnitude, distance from level
   - `get_scanner_criteria()` returns criteria for gap-down stocks (min_gap_pct negative)
   - `get_market_conditions_filter()` allows: bullish_trending, range_bound (excludes crisis, high_volatility)
   - `reconstruct_state()` rebuilds from DB on mid-day restart
   - Config validation: min_gap_down_pct < max_gap_down_pct
   - ≥18 tests covering all state transitions, edge cases, config validation, pattern_strength

4. **RedToGreenConfig:**
   - All YAML keys map to Pydantic model fields (no silently ignored keys)
   - Validator: min_gap_down_pct < max_gap_down_pct
   - Inherits StrategyConfig base fields (operating_window, risk_limits, benchmarks, universe_filter, backtest_summary)
   - Config validation test passes

5. **BullFlagPattern:**
   - `detect()` identifies bull flag: pole (min_bars, min_move_pct), flag (max_bars, max_retrace_pct, declining volume), breakout (close above flag high, volume confirmation)
   - `detect()` returns None for incomplete/invalid patterns
   - `score()` returns 0–100 based on: pole strength, flag tightness, volume profile
   - `get_default_params()` returns sensible defaults for all parameters
   - ≥8 tests covering detection, scoring, edge cases, no-pattern cases

6. **FlatTopBreakoutPattern:**
   - `detect()` identifies flat-top: resistance level (min touches within tolerance), consolidation below, breakout above on volume
   - `detect()` returns None when criteria not met
   - `score()` returns 0–100 based on: number of resistance touches, consolidation quality, breakout volume
   - ≥8 tests covering detection, scoring, edge cases

7. **VectorBT Red-to-Green:**
   - Parameter sweep covers: min_gap_down_pct, level_proximity_pct, volume_confirmation, time_stop
   - Walk-forward validation with WFE calculation
   - Results persisted to backtest_summary in config
   - If WFE < 0.3: strategy set to `pipeline_stage: "exploration"` (not promoted)
   - ≥5 tests covering sweep execution, walk-forward, report generation

8. **Generic VectorBT Pattern Backtester:**
   - Accepts any PatternModule + PatternBasedStrategy config
   - Runs parameter sweep + walk-forward for both Bull Flag and Flat-Top
   - Results persisted per pattern
   - ≥5 tests covering generic backtester with mock pattern

9. **Integration:**
   - R2G created in main.py Phase 8 with config-gated optional pattern (like VWAP Reclaim)
   - Bull Flag and Flat-Top created as PatternBasedStrategy instances in main.py Phase 8
   - All 3 registered with Orchestrator
   - Universe Manager routing works for R2G (static filters, dynamic gap-down check in strategy)
   - `/api/v1/strategies` returns 7 strategies
   - ≥8 integration tests

10. **UI:**
    - Pattern Library shows 7 strategy/pattern cards (4 existing + 3 new)
    - New cards display: name, family, pipeline stage, operating window, backtest summary
    - PatternDetail panel works for new strategies
    - ≥8 Vitest tests

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| R2G VectorBT walk-forward WFE | > 0.3 | Walk-forward analysis output |
| Bull Flag VectorBT walk-forward WFE | > 0.3 | Walk-forward analysis output |
| Flat-Top VectorBT walk-forward WFE | > 0.3 | Walk-forward analysis output |
| Pattern detection latency | < 1ms per candle | Unit test with timing assertion |
| No regression in existing strategy signal generation | All existing strategy tests pass | pytest full suite |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `red_to_green.yaml → min_gap_down_pct` | `RedToGreenConfig` | `min_gap_down_pct` | `0.02` |
| `red_to_green.yaml → max_gap_down_pct` | `RedToGreenConfig` | `max_gap_down_pct` | `0.10` |
| `red_to_green.yaml → level_proximity_pct` | `RedToGreenConfig` | `level_proximity_pct` | `0.003` |
| `red_to_green.yaml → min_level_test_bars` | `RedToGreenConfig` | `min_level_test_bars` | `2` |
| `red_to_green.yaml → volume_confirmation_multiplier` | `RedToGreenConfig` | `volume_confirmation_multiplier` | `1.2` |
| `red_to_green.yaml → max_chase_pct` | `RedToGreenConfig` | `max_chase_pct` | `0.003` |
| `red_to_green.yaml → target_1_r` | `RedToGreenConfig` | `target_1_r` | `1.0` |
| `red_to_green.yaml → target_2_r` | `RedToGreenConfig` | `target_2_r` | `2.0` |
| `red_to_green.yaml → time_stop_minutes` | `RedToGreenConfig` | `time_stop_minutes` | `20` |
| `red_to_green.yaml → stop_buffer_pct` | `RedToGreenConfig` | `stop_buffer_pct` | `0.001` |
| `bull_flag.yaml → pole_min_bars` | `BullFlagConfig` | `pole_min_bars` | `5` |
| `bull_flag.yaml → pole_min_move_pct` | `BullFlagConfig` | `pole_min_move_pct` | `0.03` |
| `bull_flag.yaml → flag_max_bars` | `BullFlagConfig` | `flag_max_bars` | `20` |
| `bull_flag.yaml → flag_max_retrace_pct` | `BullFlagConfig` | `flag_max_retrace_pct` | `0.50` |
| `bull_flag.yaml → breakout_volume_multiplier` | `BullFlagConfig` | `breakout_volume_multiplier` | `1.3` |
| `bull_flag.yaml → target_1_r` | `BullFlagConfig` | `target_1_r` | `1.0` |
| `bull_flag.yaml → target_2_r` | `BullFlagConfig` | `target_2_r` | `2.0` |
| `bull_flag.yaml → time_stop_minutes` | `BullFlagConfig` | `time_stop_minutes` | `30` |
| `flat_top_breakout.yaml → resistance_touches` | `FlatTopBreakoutConfig` | `resistance_touches` | `3` |
| `flat_top_breakout.yaml → resistance_tolerance_pct` | `FlatTopBreakoutConfig` | `resistance_tolerance_pct` | `0.002` |
| `flat_top_breakout.yaml → consolidation_min_bars` | `FlatTopBreakoutConfig` | `consolidation_min_bars` | `10` |
| `flat_top_breakout.yaml → breakout_volume_multiplier` | `FlatTopBreakoutConfig` | `breakout_volume_multiplier` | `1.3` |
| `flat_top_breakout.yaml → target_1_r` | `FlatTopBreakoutConfig` | `target_1_r` | `1.0` |
| `flat_top_breakout.yaml → target_2_r` | `FlatTopBreakoutConfig` | `target_2_r` | `2.0` |
| `flat_top_breakout.yaml → time_stop_minutes` | `FlatTopBreakoutConfig` | `time_stop_minutes` | `30` |

## Dependencies

- All existing tests passing on `main` branch (2,815 pytest + 611 Vitest)
- Phase 5 Gate doc sync completed (confirmed March 21, 2026)
- Alpaca historical data available for VectorBT sweeps (existing data source in backtest/)
- FMP Scanner provides biggest-losers for R2G scanner-mode fallback
- No external API changes required

## Relevant Decisions

- **DEC-028** (strategy statefulness): Daily-stateful, session-stateless. R2G follows same pattern.
- **DEC-047** (walk-forward mandatory): WFE > 0.3 required for all three strategies/patterns.
- **DEC-120** (OrbBaseStrategy ABC): Established pattern for strategy family ABCs — PatternModule follows similar approach.
- **DEC-132** (re-validation required): All VectorBT results are provisional until BacktestEngine (Sprint 27).
- **DEC-163** (expanded pattern library): 15+ artisanal patterns — this sprint establishes the infrastructure.
- **DEC-239** (quality engine): pattern_strength feeds quality scoring. R2G and pattern modules must implement `_calculate_pattern_strength()`.
- **DEC-277** (fail-closed): Missing reference data blocks signals. R2G must not trade without gap confirmation data.
- **DEC-300** (config-gating): New features config-gated by default. Pattern strategies gated via `enabled` field in their YAML.
- **DEC-330/331** (SignalEvent enrichment): Strategies emit `share_count=0`, `pattern_strength` 0–100. Quality Engine + Position Sizer handle sizing.
- **DEC-342** (evaluation telemetry): All strategies use `record_evaluation()` for diagnostic events. R2G and PatternBasedStrategy must do the same.
- **DEC-343** (watchlist wiring): UM populates strategy watchlists via `set_watchlist(symbols, source="universe_manager")`. New strategies follow same pattern.
- **DEC-353** (free historical data): Databento OHLCV-1m available. Not used in this sprint (Sprint 27 BacktestEngine will use it).
- **DEC-354** (Phase 6 compression): This is the last sprint using VectorBT before BacktestEngine.
- **DEC-356** (FMP Premium deferred): Catalyst pipeline runs on Finnhub + SEC EDGAR only. Quality Engine catalyst_quality at neutral defaults for most setups.

## Relevant Risks

- **RSK-042** (pre-Databento re-validation): VectorBT results are provisional. R2G backtesting inherits this risk.
- **RSK-045** (FMP API availability): FMP Scanner provides R2G's losers list. If FMP is down, scanner falls back to static symbols.
- **NEW (to be numbered)** — R2G reversal thesis risk: Buying gap-down stocks carries higher risk than existing momentum/mean-reversion strategies. A strong gap-down may indicate fundamental problems (earnings miss, regulatory action). The `max_gap_down_pct` parameter and catalyst integration (Quality Engine catalyst_quality dimension) provide some protection, but the fundamental risk of catching falling knives exists.

## Session Count Estimate

10 implementation sessions + 0.5 visual-review fix contingency = 10.5 sessions. Driven by compaction risk scoring (DEC-275): the sprint creates 11 new production files, 3 config files, 2 VectorBT modules, and modifies 5 existing files across backend/frontend. Every session scores ≤13 on the compaction risk scale.
