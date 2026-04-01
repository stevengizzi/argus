# Sprint 32, Session 5: Variant Spawner + Startup Integration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/strategies/patterns/factory.py` (S2 — factory + fingerprint)
   - `argus/intelligence/experiments/store.py` (S4 — ExperimentStore)
   - `argus/intelligence/experiments/models.py` (S4 — VariantDefinition)
   - `argus/main.py` (startup sequence — pattern construction + orchestrator registration, ~lines 500–740)
   - `argus/strategies/pattern_strategy.py` (PatternBasedStrategy wrapper)
   - `argus/core/orchestrator.py` (`register_strategy` method signature)
2. Run the test baseline (DEC-328 — Session 2+):
   Scoped: `python -m pytest tests/intelligence/experiments/ tests/strategies/patterns/test_factory.py -v`
   Expected: all passing
3. Verify Sessions 1–4 committed

## Objective
Create the variant spawner that reads variant definitions from YAML config, uses the factory to instantiate each variant as a PatternBasedStrategy, and registers them with the Orchestrator at startup. Includes creating the experiments config file and wiring the spawner into main.py.

## Requirements

1. Create `config/experiments.yaml` with documented schema:
   ```yaml
   # Experiment Pipeline Configuration
   # Config-gated: system starts in experiments.enabled: false
   enabled: false
   auto_promote: false  # When true, PromotionEvaluator runs autonomously at session end
   max_shadow_variants_per_pattern: 5
   backtest_min_trades: 20
   backtest_min_expectancy: 0.0
   promotion_min_shadow_days: 5
   promotion_min_shadow_trades: 30
   cache_dir: "data/databento_cache"

   # Variant definitions — each pattern can have multiple named variants
   # Variants not defined here use the base strategy config only
   variants: {}
   # Example:
   # variants:
   #   bull_flag:
   #     - variant_id: "strat_bull_flag__v2_tight_flag"
   #       mode: "shadow"
   #       params:
   #         flag_max_retrace_pct: 0.35
   #         pole_min_move_pct: 0.05
   #     - variant_id: "strat_bull_flag__v3_loose"
   #       mode: "shadow"
   #       params:
   #         flag_max_retrace_pct: 0.65
   #         flag_max_bars: 30
   ```

2. Create `argus/intelligence/experiments/spawner.py` with **`VariantSpawner`**:

   a. `__init__(self, experiment_store: ExperimentStore, config: dict)` — takes the parsed experiments config section

   b. `spawn_variants(self, base_strategies: dict[str, tuple[StrategyConfig, PatternBasedStrategy]], data_service, clock) -> list[PatternBasedStrategy]`:
      - For each pattern in `config["variants"]`:
        - For each variant definition:
          - Compute fingerprint for the variant params
          - Check for duplicate fingerprint against base strategy → skip with INFO log if identical
          - Check against already-spawned variants → skip with INFO log if duplicate
          - Deep-copy the base strategy's Pydantic config
          - Override detection params with variant-specified params
          - Use factory to construct the pattern instance
          - Create PatternBasedStrategy wrapping the variant pattern with the modified config
          - Set `config.mode` to the variant's mode ("live" or "shadow")
          - Set `config.strategy_id` to the variant's `variant_id`
          - Set `_config_fingerprint` on the strategy
          - Record variant in ExperimentStore
          - Append to result list
      - Return list of spawned variant strategies

   c. `_apply_variant_params(base_config: StrategyConfig, variant_params: dict) -> StrategyConfig`:
      - Deep copy the config, override specified detection fields
      - Validate via Pydantic (re-parse with `model_validate()`) to catch invalid overrides
      - Raises `ValidationError` for invalid params (logged and skipped, not fatal)

3. In `argus/main.py`, wire the spawner into the startup sequence:
   - After all 7 base pattern strategies are constructed and registered (~line 740)
   - If `experiments.enabled` in config:
     - Initialize ExperimentStore
     - Create VariantSpawner
     - Call `spawn_variants()` passing base strategies
     - Register each variant strategy with the Orchestrator
     - Set watchlist and reference data on each variant (same as base strategy)
     - Set candle store on each variant
     - Log count of variants spawned at INFO level
   - Wrap in try/except — experiment spawning failure should NOT prevent base system startup

4. Ensure each spawned variant:
   - Has the same watchlist as its base strategy
   - Receives reference data via `initialize_reference_data()` (same as base)
   - Gets candle store via `set_candle_store()` (same as base)
   - Is subscribed to CandleEvent on the Event Bus

## Constraints
- Do NOT modify `argus/core/orchestrator.py` — variants register through the existing `register_strategy()` API
- Do NOT modify any pattern `.py` files
- Do NOT make experiment spawning failure fatal — wrap in try/except with ERROR log
- Variant strategies must be indistinguishable from base strategies to the Orchestrator and Event Bus
- Respect `max_shadow_variants_per_pattern` limit — skip with WARNING if exceeded

## Test Targets
After implementation:
- New tests in `tests/intelligence/experiments/test_spawner.py`:
  - Spawner with 2 bull_flag variants → 2 PatternBasedStrategy instances
  - Duplicate fingerprint (same params as base) → skipped
  - Invalid variant params → logged and skipped, not fatal
  - `mode: shadow` → strategy config mode is "shadow"
  - `mode: live` → strategy config mode is "live"
  - Max variants per pattern respected
  - `experiments.enabled: false` → zero variants
  - Variant receives same watchlist as base
- Minimum new test count: 8
- Test command: `python -m pytest tests/intelligence/experiments/test_spawner.py -v`

## Definition of Done
- [ ] `config/experiments.yaml` created with documented schema
- [ ] `spawner.py` created with variant spawning logic
- [ ] Spawner wired into main.py startup (config-gated)
- [ ] Variants registered with Orchestrator and receive proper subscriptions
- [ ] All existing tests pass
- [ ] New tests pass
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)

| Check | How to Verify |
|-------|---------------|
| R1: All 12 base strategies still register | Startup with `experiments.enabled: false` → 12 strategies |
| R6: Shadow mode routing works for variants | Variant with `mode: shadow` → signals to CounterfactualTracker |
| R11: `experiments.enabled: false` → no change | No variant strategies spawned |
| R16: Orchestrator unchanged | No diff to orchestrator.py |

## Close-Out
**Write the close-out report to:** docs/sprints/sprint-32/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32/review-context.md`
2. Close-out report: `docs/sprints/sprint-32/session-5-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/intelligence/experiments/test_spawner.py -v`
5. Files that should NOT have been modified: `orchestrator.py`, any pattern `.py` file, any non-PatternModule strategy

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify spawner failure doesn't prevent base system startup (try/except)
2. Verify variants get same watchlist and reference data as base strategy
3. Verify duplicate fingerprint detection works correctly
4. Verify Pydantic validation catches invalid variant params
5. Verify max_shadow_variants_per_pattern is enforced
6. Verify variant strategy IDs are unique and distinguishable from base IDs

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32/review-context.md`
