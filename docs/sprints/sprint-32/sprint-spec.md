# Sprint 32: Parameterized Strategy Templates + Experiment Pipeline

## Goal
Build the complete parameter externalization and experiment pipeline for PatternModule strategies. When complete, ARGUS can instantiate multiple parameterized variants of each pattern template, run them simultaneously (live and shadow), and autonomously promote or demote variants based on accumulated live shadow performance — without human intervention. This sprint combines the original Sprint 32 (Parameterized Templates) and Sprint 32.5 (Experiment Registry + Promotion Pipeline) into a single delivery.

## Scope

### Deliverables

1. **Pydantic config alignment:** All 7 PatternModule pattern constructors have every parameter represented in their corresponding Pydantic config model with matching names, types, defaults, and bounds. 28 missing fields added across 6 pattern configs (DipAndRipConfig is already complete).

2. **Generic pattern factory:** A `build_pattern_from_config()` function that takes a Pydantic strategy config, introspects `PatternParam` metadata from the target pattern class, extracts matching fields from the config, validates bounds, and returns a fully constructed `PatternModule` instance. No hardcoded pattern switch statements.

3. **Parameter fingerprint:** A `ParameterFingerprint` utility that computes a stable, deterministic hash of the active detection parameters for any strategy config. Stored on every trade record for retroactive config-vs-outcome analysis.

4. **Runtime wiring:** `main.py` uses the factory for all 7 PatternModule pattern constructions. `PatternBacktester._create_pattern_by_name()` replaced with factory (resolves DEF-121 for all 7 patterns). `TradeLogger` stores fingerprint on every trade.

5. **Experiment registry:** SQLite-backed `ExperimentStore` (DEC-345 pattern) tracking variant definitions, parameter fingerprints, backtest results (`MultiObjectiveResult`), shadow performance, and promotion history.

6. **Variant spawner:** `VariantSpawner` reads variant definitions from `config/experiments.yaml`, uses the factory to instantiate each variant, registers them with the Orchestrator (live or shadow mode per config). Unique strategy IDs per variant (e.g., `strat_bull_flag__v2_aggressive`).

7. **Experiment runner (backtest pre-filter):** `ExperimentRunner` generates parameter grids from `PatternParam` metadata, runs `BacktestEngine` for each configuration against the Parquet cache, stores `MultiObjectiveResult` per config. Only variants passing minimum bar (positive expectancy, minimum trade count) are eligible for shadow spawning.

8. **Promotion evaluator:** `PromotionEvaluator` compares shadow variant performance against live variants using Pareto comparison from the evaluation framework. Autonomous mode: variants with sustained edge graduate from shadow to live; underperforming live variants demote to shadow. Mode changes happen intraday via strategy mode update.

9. **CLI + REST API:** `scripts/run_experiment.py` for manual sweep triggering. REST endpoints for experiment listing, detail, baseline query, and sweep triggering. Config-gated via `experiments.enabled`.

### Acceptance Criteria

1. **Pydantic config alignment:**
   - A programmatic test instantiates each of the 7 PatternModule patterns, calls `get_default_params()`, and verifies every `PatternParam.name` exists as a field in the corresponding Pydantic config model
   - All 7 pattern YAML configs load without error with both default and non-default detection param values
   - Invalid values (outside `min_value`/`max_value`) are rejected at config load time by Pydantic Field validators

2. **Generic pattern factory:**
   - `build_pattern_from_config(BullFlagConfig(...))` returns a `BullFlagPattern` with parameters matching the config values
   - Works for all 7 PatternModule patterns without any pattern-specific code in the factory
   - Raises `ValueError` for unrecognized pattern types
   - Logs a warning if a config field exists but the pattern doesn't accept it (forward compat)

3. **Parameter fingerprint:**
   - Identical configs produce identical fingerprints across process restarts
   - Different detection params produce different fingerprints
   - Non-detection params (strategy_id, name, operating_window, etc.) do not affect the fingerprint
   - Fingerprint is a short hex string (≤16 chars)

4. **Runtime wiring:**
   - All 7 PatternModule patterns construct via factory at startup
   - Changing a detection parameter in YAML and restarting changes the pattern's behavior
   - `PatternBacktester` supports all 7 patterns via factory (was 3)
   - Every trade record in the `trades` table includes a `config_fingerprint` column

5. **Experiment registry:**
   - CRUD operations: create experiment, query by pattern/fingerprint, get baseline, update status
   - WAL mode, fire-and-forget writes, retention enforcement (90 days)
   - Separate DB file: `data/experiments.db`

6. **Variant spawner:**
   - Reads variant definitions from `config/experiments.yaml`
   - Instantiates N variants per pattern template with distinct parameters
   - Registers each variant with the Orchestrator (respects `mode: live|shadow` per variant)
   - Variants receive the same watchlist and reference data as the base strategy
   - Default config has 0 variants (system behavior unchanged when `experiments.enabled: false`)

7. **Experiment runner:**
   - Generates parameter grid from `PatternParam` min/max/step ranges
   - Runs BacktestEngine for each grid point against specified Parquet cache directory
   - Stores `MultiObjectiveResult` per configuration in experiment store
   - Supports `--pattern`, `--cache-dir`, `--dry-run` CLI args
   - Pre-filter: only configs with positive expectancy and ≥ N trades (configurable) pass

8. **Promotion evaluator:**
   - Compares shadow variant's accumulated CounterfactualTracker results against live variant's trade results
   - Uses `compare()` from evaluation framework for Pareto dominance check
   - Minimum shadow days + minimum shadow trades thresholds before evaluation
   - Autonomous promotion: updates strategy mode from shadow→live
   - Autonomous demotion: updates strategy mode from live→shadow when performance degrades below baseline
   - Promotion/demotion events logged to experiment store with full context

9. **CLI + REST API:**
   - `scripts/run_experiment.py --pattern bull_flag --cache-dir data/databento_cache` runs a sweep
   - `GET /api/v1/experiments` lists experiments (JWT-protected)
   - `GET /api/v1/experiments/{id}` returns experiment detail
   - `GET /api/v1/experiments/baseline/{pattern}` returns current baseline config
   - `POST /api/v1/experiments/run` triggers a sweep (JWT-protected)
   - All endpoints return 404/503 when experiments disabled

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Variant spawning (5 variants × 7 patterns) | < 5s at startup | Timer in startup sequence |
| Shadow variant signal processing overhead | < 5% throughput impact on live strategies | Compare candle processing latency with/without shadow variants |
| Parameter fingerprint computation | < 1ms per strategy | Benchmark in test |
| Experiment runner sweep (50-point grid, 1 pattern) | < 30 min | CLI timing with Parquet cache |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Type | Default |
|-----------|---------------|------------|------|---------|
| `experiments.enabled` | ExperimentConfig | enabled | bool | false |
| `experiments.max_shadow_variants_per_pattern` | ExperimentConfig | max_shadow_variants_per_pattern | int | 5 |
| `experiments.backtest_min_trades` | ExperimentConfig | backtest_min_trades | int | 20 |
| `experiments.backtest_min_expectancy` | ExperimentConfig | backtest_min_expectancy | float | 0.0 |
| `experiments.promotion_min_shadow_days` | ExperimentConfig | promotion_min_shadow_days | int | 5 |
| `experiments.promotion_min_shadow_trades` | ExperimentConfig | promotion_min_shadow_trades | int | 30 |
| `experiments.cache_dir` | ExperimentConfig | cache_dir | str | "data/databento_cache" |
| `experiments.auto_promote` | ExperimentConfig | auto_promote | bool | false |
| `experiments.variants` | ExperimentConfig | variants | dict | {} |
| BullFlagConfig: `min_score_threshold` | BullFlagConfig | min_score_threshold | float | 0.0 |
| BullFlagConfig: `pole_strength_cap_pct` | BullFlagConfig | pole_strength_cap_pct | float | 0.10 |
| BullFlagConfig: `breakout_excess_cap_pct` | BullFlagConfig | breakout_excess_cap_pct | float | 0.02 |
| FlatTopBreakoutConfig: `min_score_threshold` | FlatTopBreakoutConfig | min_score_threshold | float | 0.0 |
| FlatTopBreakoutConfig: `max_range_narrowing` | FlatTopBreakoutConfig | max_range_narrowing | float | 0.5 |
| HODBreakConfig: `vwap_extended_pct` | HODBreakConfig | vwap_extended_pct | float | 0.02 |
| GapAndGoConfig: `prior_day_avg_volume` | GapAndGoConfig | prior_day_avg_volume | float | 1000000.0 |
| GapAndGoConfig: `min_score_threshold` | GapAndGoConfig | min_score_threshold | float | 0.0 |
| GapAndGoConfig: `gap_atr_cap` | GapAndGoConfig | gap_atr_cap | float | 3.0 |
| GapAndGoConfig: `volume_score_cap` | GapAndGoConfig | volume_score_cap | float | 5.0 |
| GapAndGoConfig: `vwap_hold_score_divisor` | GapAndGoConfig | vwap_hold_score_divisor | float | 3.0 |
| GapAndGoConfig: `catalyst_base_score` | GapAndGoConfig | catalyst_base_score | float | 10.0 |
| ABCDConfig: `swing_lookback` | ABCDConfig | swing_lookback | int | 5 |
| ABCDConfig: `min_swing_atr_mult` | ABCDConfig | min_swing_atr_mult | float | 0.5 |
| ABCDConfig: `fib_b_min` | ABCDConfig | fib_b_min | float | 0.382 |
| ABCDConfig: `fib_b_max` | ABCDConfig | fib_b_max | float | 0.618 |
| ABCDConfig: `fib_c_min` | ABCDConfig | fib_c_min | float | 0.500 |
| ABCDConfig: `fib_c_max` | ABCDConfig | fib_c_max | float | 0.786 |
| ABCDConfig: `leg_price_ratio_min` | ABCDConfig | leg_price_ratio_min | float | 0.8 |
| ABCDConfig: `leg_price_ratio_max` | ABCDConfig | leg_price_ratio_max | float | 1.2 |
| ABCDConfig: `leg_time_ratio_min` | ABCDConfig | leg_time_ratio_min | float | 0.5 |
| ABCDConfig: `leg_time_ratio_max` | ABCDConfig | leg_time_ratio_max | float | 2.0 |
| ABCDConfig: `completion_tolerance_percent` | ABCDConfig | completion_tolerance_percent | float | 1.0 |
| ABCDConfig: `stop_buffer_atr_mult` | ABCDConfig | stop_buffer_atr_mult | float | 0.5 |
| ABCDConfig: `target_extension` | ABCDConfig | target_extension | float | 1.272 |
| PreMarketHighBreakConfig: `min_score_threshold` | PreMarketHighBreakConfig | min_score_threshold | float | 0.0 |
| PreMarketHighBreakConfig: `vwap_extended_pct` | PreMarketHighBreakConfig | vwap_extended_pct | float | 0.02 |
| PreMarketHighBreakConfig: `gap_up_bonus_pct` | PreMarketHighBreakConfig | gap_up_bonus_pct | float | 3.0 |

## Dependencies

- Sprint 29.5 complete (4,212 pytest + 700 Vitest, 12 active strategies)
- Full-universe Parquet cache populated (44.73 GB, 24,321 symbols)
- BacktestEngine functional (Sprint 27)
- CounterfactualTracker functional with shadow mode routing (Sprint 27.7)
- Evaluation Framework comparison API functional (Sprint 27.5)
- ConfigProposalManager exists (Sprint 28) — not extended in this sprint, but architectural pattern reused

## Relevant Decisions

- DEC-032: Pydantic config validation — all new config fields must follow this pattern
- DEC-047: Walk-forward validation mandatory — experiment runner uses BacktestEngine which respects this
- DEC-300: Config-gated feature pattern — experiments.enabled follows this
- DEC-328: Test suite tiering — Session 1 full suite, others scoped
- DEC-345: Separate SQLite DB pattern — experiments.db follows this
- DEC-375: Overflow routing — shadow variants subject to same overflow capacity limits

## Relevant Risks

- RSK-032 (new): Shadow variant throughput impact — many shadow variants processing candles could slow live strategy processing. Mitigated by: capping max_shadow_variants_per_pattern, measuring throughput impact.
- RSK-033 (new): Promotion oscillation — a variant repeatedly promoted and demoted due to regime changes. Mitigated by: minimum shadow days threshold, hysteresis in promotion criteria.

## Session Count Estimate

8 sessions estimated. The sprint combines two originally separate sprints (32 + 32.5). Sessions 1–3 cover parameter externalization (original Sprint 32 scope). Sessions 4–8 cover the experiment pipeline (original Sprint 32.5 scope). All sessions score ≤14 on compaction risk. No frontend work, so no visual-review contingency needed.
