# Sprint 29: Pattern Expansion I

## Goal
Add 5 new PatternModule strategies (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, Pre-Market High Break) and introduce the PatternParam structured type (DEF-088) with machine-readable parameter metadata. Reach 12 active strategies, expand midday signal coverage, and establish the metadata foundation that Sprint 32's StrategyTemplate and Sprint 34's systematic search will consume.

## Scope

### Deliverables

1. **PatternParam dataclass** — frozen dataclass in `strategies/patterns/base.py` with fields: `name` (str), `param_type` (type), `default` (Any), `min_value` (float | None), `max_value` (float | None), `step` (float | None), `description` (str), `category` (str). `get_default_params()` ABC signature changes from `dict[str, Any]` to `list[PatternParam]`.

2. **Reference data hook** — optional `set_reference_data(data: dict[str, Any])` method on PatternModule with default no-op. PatternBasedStrategy calls it during initialization with UM reference data. Enables patterns to receive prior close, pre-market context, etc.

3. **Bull Flag + Flat-Top Breakout retrofit** — existing patterns' `get_default_params()` returns converted to `list[PatternParam]` with accurate ranges, steps, descriptions, and categories.

4. **PatternBacktester grid generation update** — `vectorbt_pattern.py` generates parameter sweep grids from PatternParam `(min_value, max_value, step)` instead of hardcoded ±20%/±40% percentage variations.

5. **Dip-and-Rip pattern** — PatternModule implementation. Sharp intraday dip detection (configurable % or ATR-based), rapid recovery validation, VWAP/support level interaction, volume confirmation. Window: 9:45–11:30 AM. Differentiated from R2G: intraday dip only (no gap-based), dip must occur after 9:35 AM.

6. **HOD Break pattern** — PatternModule implementation. Dynamic high-of-day tracking, consolidation detection near HOD, breakout confirmation with volume, multi-test resistance scoring. Window: 10:00–15:30. Primary midday coverage provider.

7. **Gap-and-Go pattern** — PatternModule implementation. Gap-up detection from prior close (min 3%), relative volume confirmation, VWAP hold validation, first-pullback or direct-breakout entry modes. Window: 9:35–10:30 AM. Uses `set_reference_data()` for prior close. `initialize_prior_closes()` pattern from R2G.

8. **ABCD pattern** — PatternModule implementation. Swing point detection algorithm (local minima/maxima with configurable lookback and tolerance), Fibonacci retracement validation at B (38.2–61.8%) and C (61.8–78.6%) points, leg ratio checking (AB ≈ CD in price and time), completion zone calculation for entry. Window: 10:00–15:00. Highest parameterization density — ideal Sprint 32 candidate.

9. **Pre-Market High Break pattern** [STRETCH] — PatternModule implementation. Pre-market high computation from extended-hours candles in deque (4:00 AM–9:30 AM via EQUS.MINI), breakout detection, PM volume qualification, gap context scoring. Window: 9:35–10:30 AM. Uses `set_reference_data()` for prior close context.

10. **Strategy configs, universe filters, exit overrides** — per-pattern YAML configs, UM routing filters with pattern-appropriate parameters, exit management strategy overrides in `exit_management.yaml`.

11. **Strategy registration** — all 5 new patterns registered in orchestrator config, system config updated.

12. **Smoke backtests** — each new pattern validated via PatternBacktester on 5 symbols × 6 months. Not walk-forward — just sanity check that detection fires on historical data and produces non-degenerate metrics.

### Acceptance Criteria

1. **PatternParam:**
   - `PatternParam` is a frozen dataclass importable from `strategies.patterns.base`
   - All 8 fields present with correct types
   - `get_default_params()` ABC method returns `list[PatternParam]`
   - All existing tests pass after signature change
   - `set_reference_data()` exists on PatternModule with default no-op

2. **Retrofit:**
   - Bull Flag `get_default_params()` returns `list[PatternParam]` with ≥8 params
   - Flat-Top Breakout `get_default_params()` returns `list[PatternParam]` with ≥8 params
   - Every param has non-empty `description`, valid `param_type`, non-None `min_value`/`max_value` for numeric types
   - PatternBacktester produces parameter grids from PatternParam ranges
   - Backward compatibility: PatternBacktester on Bull Flag produces results (not necessarily identical grids)

3. **Each new pattern (Dip-and-Rip, HOD Break, Gap-and-Go, ABCD, PM High Break):**
   - Implements all 5 PatternModule abstract members
   - `detect()` returns `PatternDetection | None`
   - `score()` returns 0–100
   - `get_default_params()` returns `list[PatternParam]` with all params having complete metadata
   - Strategy YAML config parses without error via Pydantic
   - Universe filter routes symbols correctly via UM
   - Exit management overrides apply via `deep_update()`
   - Registered in orchestrator, loads at system startup
   - Smoke backtest completes on 5 symbols × 6 months without error
   - Unit tests cover: positive detection, negative detection (reject non-matching), scoring weights, edge cases (empty candles, insufficient history), PatternParam completeness

4. **ABCD-specific:**
   - Swing detection identifies local peaks and valleys with configurable lookback
   - Fibonacci retracement validation at B and C points with configurable tolerance
   - Leg ratio checking (price and time) with configurable bounds
   - Incomplete patterns (AB-BC without CD) do not produce signals
   - Completion zone calculation produces valid entry level

5. **Gap-and-Go-specific:**
   - Gap calculated from prior close via `set_reference_data()`
   - Returns None when prior close unavailable
   - Rejects gaps below threshold (default 3%)

6. **PM High Break-specific:**
   - PM high computed from candles in deque with timestamp between 4:00 AM and 9:30 AM ET
   - Returns None when insufficient PM candles
   - PM volume qualification enforced

7. **Integration:**
   - All 12 strategies load at system startup without error
   - No existing strategy behavior changed
   - Quality Engine processes signals from new patterns (automatic via `share_count=0`)
   - Counterfactual Engine tracks rejected signals from new patterns (automatic)
   - Exit Management per-strategy overrides applied correctly for each new pattern

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Pattern detection latency (per candle) | < 5ms for all patterns | Smoke backtest timing (ABCD may be higher) |
| ABCD swing detection | < 10ms per candle | Unit test with timing assertion |
| Smoke backtest completion | < 5 min per pattern (5 sym × 6 mo) | PatternBacktester CLI run |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default | Session |
|-----------|---------------|------------|---------|---------|
| strategies/dip_and_rip.yaml (entire file) | PatternStrategyConfig | (shared model) | — | S3 |
| strategies/hod_break.yaml (entire file) | PatternStrategyConfig | (shared model) | — | S4 |
| strategies/gap_and_go.yaml (entire file) | PatternStrategyConfig | (shared model) | — | S5 |
| strategies/abcd.yaml (entire file) | PatternStrategyConfig | (shared model) | — | S6b |
| strategies/premarket_high_break.yaml (entire file) | PatternStrategyConfig | (shared model) | — | S7 |
| universe_filters/dip_and_rip.yaml | UniverseFilterConfig | min_relative_volume | 1.5 | S3 |
| universe_filters/gap_and_go.yaml | UniverseFilterConfig | min_gap_percent | 3.0 | S5 |
| universe_filters/premarket_high_break.yaml | UniverseFilterConfig | min_premarket_volume | 50000 | S7 |
| exit_management.strategy_exit_overrides.dip_and_rip | ExitManagementConfig | (nested) | see spec | S3 |
| exit_management.strategy_exit_overrides.hod_break | ExitManagementConfig | (nested) | see spec | S4 |
| exit_management.strategy_exit_overrides.gap_and_go | ExitManagementConfig | (nested) | see spec | S5 |
| exit_management.strategy_exit_overrides.abcd | ExitManagementConfig | (nested) | see spec | S6b |
| exit_management.strategy_exit_overrides.premarket_high_break | ExitManagementConfig | (nested) | see spec | S7 |

**CRITICAL CONFIG VERIFICATION:** Universe filter fields `min_relative_volume`, `min_gap_percent`, and `min_premarket_volume` must be verified against the UniverseFilterConfig Pydantic model. If these fields do not exist in the model, they must be ADDED to the model in the session that creates the filter — otherwise Pydantic silently ignores them and the filter applies no constraint. Each session's implementation prompt must include verification of config field existence.

## Dependencies
- Sprint 28.5 (Exit Management) complete — exit config infrastructure available
- PatternModule ABC, PatternBasedStrategy, PatternBacktester all operational (Sprint 26)
- IntradayCandleStore operational (Sprint 27.65) — PM High Break depends on pre-window candle accumulation
- Full-universe Parquet cache available in `data/databento_cache` for smoke backtests
- Universe Manager operational for filter routing
- Sprint 27.65 fix: bar accumulation before operating window check — required for PM High Break pre-market candle availability

## Relevant Decisions
- **DEC-378**: Sprint 29 scope expansion — ABCD mandatory, DEF-088 promoted, Pre-Market High Break optional
- **DEC-028**: Strategy statefulness — daily-stateful, session-stateless
- **DEC-330/331**: All strategies implement `_calculate_pattern_strength()` returning 0–100, emit `share_count=0`
- **DEC-343**: Watchlist population from Universe Manager routing via `set_watchlist(symbols, source="universe_manager")`
- **DEC-047**: Walk-forward validation mandatory, WFE > 0.3 (post-sprint)
- **DEC-167**: Original pattern expansion planning
- **DEC-275**: Compaction risk scoring system (adjusted scoring applied for templated sessions)
- **DEC-366**: Bracket leg amendment on fill slippage (new patterns inherit this automatically)

## Relevant Risks
- **RSK-045**: Quality Engine running on partial signal — 45% returns neutral defaults. New patterns initially contribute zero historical data, so Quality Engine grades will be based on partial signal. Mitigated: automatic via existing pipeline, improves as paper trading data accumulates.
- **RSK-048**: Quality Engine grade clustering under partial signal. New patterns may cluster around B/B+ grades until sufficient data distinguishes them. Mitigated: informational only — does not affect signal generation, only position sizing.

## Session Count Estimate
9 sessions estimated. S1–S2 build foundation (PatternParam + retrofit). S3–S5 build 3 straightforward patterns. S6a–S6b handle ABCD (split due to algorithm complexity). S7 builds PM High Break (stretch). S8 runs integration verification. No frontend work — no visual-review contingency needed.
