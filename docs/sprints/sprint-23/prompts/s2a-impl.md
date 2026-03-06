# Sprint 23, Session 2a: Universe Filter Config Model

## Pre-Flight Checks
1. Read: `argus/core/config.py` (full file — understand StrategyConfig, SystemConfig, existing patterns), `argus/strategies/base_strategy.py` (how config is consumed)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Add Pydantic config models for universe filtering: `UniverseFilterConfig` (per-strategy) and `UniverseManagerConfig` (system-level).

## Requirements

1. In `argus/core/config.py`, add `UniverseFilterConfig` model:
   ```python
   class UniverseFilterConfig(BaseModel):
       min_price: float | None = None
       max_price: float | None = None
       min_market_cap: float | None = None  # USD
       max_market_cap: float | None = None  # USD
       min_float: float | None = None       # shares
       min_avg_volume: int | None = None
       sectors: list[str] = Field(default_factory=list)        # empty = all sectors
       exclude_sectors: list[str] = Field(default_factory=list) # empty = no exclusions
   ```

2. Add `UniverseManagerConfig` model:
   ```python
   class UniverseManagerConfig(BaseModel):
       enabled: bool = False
       min_price: float = 5.0
       max_price: float = 10000.0
       min_avg_volume: int = 100000
       exclude_otc: bool = True
       reference_cache_ttl_hours: int = 24
       fmp_batch_size: int = 50
   ```

3. Add `universe_filter: UniverseFilterConfig | None = None` to `StrategyConfig`.

4. Add `universe_manager: UniverseManagerConfig = Field(default_factory=UniverseManagerConfig)` to `SystemConfig`.

5. Ensure existing config loading functions handle the new optional fields gracefully (missing sections use defaults).

## Constraints
- Do NOT modify strategy YAML files (Session 2b/2c)
- Do NOT modify `universe_manager.py` (Session 4a will wire the real config)
- Do NOT add universe_manager section to system.yaml yet (Session 4a)
- Preserve all existing config behavior — new fields are additive with defaults

## Config Validation
Write a test that loads `config/system.yaml` and verifies the `universe_manager` section (when present) has no keys unrecognized by `UniverseManagerConfig`. Since system.yaml doesn't have this section yet, test with a fixture YAML that includes it.

## Test Targets
- New tests (in `tests/core/test_config.py` or new file):
  1. `test_universe_filter_config_defaults`: all None/empty
  2. `test_universe_filter_config_full`: all fields set, validates correctly
  3. `test_universe_filter_config_invalid_types`: wrong types rejected
  4. `test_universe_manager_config_defaults`: verify default values
  5. `test_strategy_config_with_universe_filter`: StrategyConfig accepts universe_filter
  6. `test_strategy_config_without_universe_filter`: StrategyConfig works without it (backward compat)
  7. `test_system_config_with_universe_manager`: SystemConfig accepts universe_manager
  8. `test_config_yaml_pydantic_field_match`: fixture YAML keys vs model_fields — no unrecognized keys
- Minimum: 8 tests
- Command: `python -m pytest tests/core/test_config.py -v -k "universe"`

## Definition of Done
- [ ] UniverseFilterConfig and UniverseManagerConfig models added
- [ ] Integrated into StrategyConfig and SystemConfig
- [ ] All existing tests pass (no config loading regressions)
- [ ] 8+ new tests passing
- [ ] Ruff clean

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R6–R9 (strategy configs still load), R16–R19 (config validation).

## Sprint-Level Escalation Criteria
E5: Any existing config loading test fails → ESCALATE. E13: YAML↔Pydantic mismatch → ESCALATE.
