# Sprint 23, Session 4a: Universe Manager System Config

## Pre-Flight Checks
1. Read: `argus/core/config.py` (Session 2a output — UniverseManagerConfig model), `config/system.yaml` (current config)
2. Run: `python -m pytest tests/ -x -q` — all passing
3. Branch: `sprint-23`

## Objective
Wire the UniverseManagerConfig Pydantic model into SystemConfig and add the corresponding YAML section to system.yaml.

## Requirements

1. In `argus/core/config.py`:
   - Ensure `UniverseManagerConfig` is added to `SystemConfig` (may already be done in Session 2a — verify and complete if needed)
   - Ensure `load_system_config()` handles missing `universe_manager` section gracefully (defaults apply)

2. In `config/system.yaml`, add the `universe_manager` section at the end:
   ```yaml
   # Universe Manager (Sprint 23 — DEC-263)
   # Broad-universe monitoring with strategy-specific filtering
   # Set enabled: true to activate. Requires FMP_API_KEY.
   universe_manager:
     enabled: false          # Start disabled — operator activates when ready
     min_price: 5.0          # System-level: exclude penny stocks
     max_price: 10000.0      # System-level: exclude extreme price outliers
     min_avg_volume: 100000  # System-level: minimum average daily volume
     exclude_otc: true       # System-level: exclude OTC symbols
     reference_cache_ttl_hours: 24  # FMP reference data cache lifetime
     fmp_batch_size: 50      # Symbols per FMP batch API call
   ```

3. Also update `config/system_live.yaml` if it exists with the same section (enabled: false default).

4. Replace the temporary config dataclass in `argus/data/universe_manager.py` (from Session 1b) with an import of the real `UniverseManagerConfig` from `argus/core/config`. This is a simple swap — the field names are identical by design.

## Config Validation
Write a test that:
1. Loads `config/system.yaml`
2. Extracts all keys under `universe_manager`
3. Compares against `UniverseManagerConfig.model_fields.keys()`
4. Asserts no keys in YAML are absent from the model (would be silently ignored)

## Constraints
- Do NOT modify `argus/main.py` (Session 4b)
- Do NOT modify strategy YAMLs
- Preserve all existing system.yaml content exactly

## Test Targets
- New tests:
  1. `test_system_yaml_loads_with_universe_manager`: actual system.yaml loads
  2. `test_system_yaml_universe_manager_defaults`: verify default values match
  3. `test_system_yaml_missing_universe_manager`: remove section → defaults apply
  4. `test_universe_manager_yaml_keys_match_pydantic`: no silently ignored keys
  5. `test_universe_manager_config_swap_in_manager`: UniverseManager accepts real config
  6. `test_system_live_yaml_loads`: system_live.yaml loads if it exists
- Minimum: 6 tests
- Command: `python -m pytest tests/ -k "universe_manager" -k "config" -v`

## Definition of Done
- [ ] universe_manager section in system.yaml (and system_live.yaml)
- [ ] UniverseManagerConfig wired into SystemConfig
- [ ] Temporary config dataclass in universe_manager.py replaced with real import
- [ ] YAML↔Pydantic field name match verified by test
- [ ] All existing tests pass
- [ ] 6+ new tests passing

## Close-Out
Follow `.claude/skills/close-out.md`.

## Sprint-Level Regression Checklist
R1–R3, R16 (system.yaml loads with UM section), R17 (loads without UM section), R18 (no ignored keys).

## Sprint-Level Escalation Criteria
E13: YAML↔Pydantic mismatch → ESCALATE.
