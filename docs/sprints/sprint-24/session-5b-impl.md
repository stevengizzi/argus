# Sprint 24, Session 5b: Config Wiring + YAML + DB Schema

## Pre-Flight Checks
1. Read: `argus/intelligence/config.py` (QualityEngineConfig from 5a), `argus/core/config.py` (SystemConfig), `argus/db/schema.sql`, `config/system.yaml`, `config/system_live.yaml`
2. Scoped test: `python -m pytest tests/core/test_config.py tests/db/ -x -q`
3. Branch: `sprint-24`

## Pre-Flight Fixes (from Work Journal carry-forwards)

Complete these three items BEFORE starting the session's main work. They are small,
isolated, and have no dependencies on future sessions.

### Fix A: Add pre-existing test failure to CLAUDE.md DEF list
In `CLAUDE.md`, add to the DEF (deferred) items list:
```
DEF-049: test_orchestrator_uses_strategies_from_registry in tests/test_main.py fails
when run in isolation but passes in full suite. Pre-existing test isolation issue.
Discovered Sprint 24 S1. (Source: S1 review, INFO finding)
```

### Fix B: Tighten bare `dict` type annotations
Three files need `dict` → `dict[str, object]`:
- `argus/core/events.py`: `signal_context: dict` → `signal_context: dict[str, object]`
  on SignalEvent AND `components: dict` → `components: dict[str, object]` on
  QualitySignalEvent
- `argus/intelligence/quality_engine.py`: `components: dict` → `components: dict[str, float]`
  on SetupQuality (this one is specifically `str, float` since all component values are floats)

### Fix C: Remove unused import
In `argus/intelligence/position_sizer.py`, remove the unused `VALID_GRADES` import.

### Verification
After all three fixes, run: `python -m pytest tests/core/test_events.py tests/intelligence/test_quality_engine.py tests/intelligence/test_position_sizer.py -x -q`
All must pass with zero changes to test files.

## Objective
Wire QualityEngineConfig into SystemConfig. Create quality_engine.yaml. Add quality_history table. Update both system YAML files.

## Requirements

### 1. In `argus/core/config.py`:
Add import: `from argus.intelligence.config import QualityEngineConfig`
Add field to `SystemConfig`:
```python
quality_engine: QualityEngineConfig = Field(default_factory=QualityEngineConfig)
```

### 2. Create `config/quality_engine.yaml`:
Full config with all weights, thresholds, risk tiers. Include the provisional note comment.

### 3. In `argus/db/schema.sql`:
Add quality_history table with indexes (exact schema from session breakdown).

### 4. In `config/system.yaml` and `config/system_live.yaml`:
Add `quality_engine:` section referencing the YAML config or inline.

## Config Validation
Write a test that loads `config/quality_engine.yaml` and verifies all keys match QualityEngineConfig model fields. No silently ignored keys.

| YAML Key | Model Field |
|----------|-------------|
| enabled | enabled |
| weights.pattern_strength | weights.pattern_strength |
| (all remaining as per sprint spec config table) |

## Test Targets
- `test_system_config_loads_quality_engine`: SystemConfig with quality_engine section parses correctly
- `test_system_config_default_quality_engine`: Missing section → valid defaults (enabled=true)
- `test_quality_engine_yaml_keys_match_model`: No silently ignored keys
- `test_quality_history_table_created`: DB initialization creates table + indexes
- `test_system_yaml_has_quality_engine`: config/system.yaml parseable with section
- `test_system_live_yaml_has_quality_engine`: config/system_live.yaml parseable
- Minimum: 8
- Test command: `python -m pytest tests/core/test_config.py tests/db/ -x -q`

## Definition of Done
- [ ] SystemConfig includes quality_engine field
- [ ] quality_engine.yaml created with correct values
- [ ] quality_history table in schema.sql
- [ ] Both system YAML files updated
- [ ] Config validation test passing
- [ ] 8+ new tests

## Close-Out
Write report to `docs/sprints/sprint-24/session-5b-closeout.md`.

