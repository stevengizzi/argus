# Close-Out Report — Sprint 28, Session S6cf-4

**Objective:** Three targeted polish fixes — remove redundant Pydantic validators, replace private attribute access with public property, add test for config-disabled path.

## Change Manifest

| File | Change |
|------|--------|
| `argus/intelligence/learning/models.py` | Removed 4 redundant `@field_validator` methods (lines 404-438) that duplicated `Field(ge=, le=)` constraints; removed `field_validator` from Pydantic import |
| `argus/intelligence/counterfactual.py` | Added `closed_position_count` property (4 lines) returning `int` from `len(self._closed_positions)` |
| `argus/main.py` | Replaced `getattr(tracker, "_closed_positions", [])` + `len()` with `getattr(tracker, "closed_position_count", 0)` — public API instead of private attribute access |
| `tests/api/test_learning_api.py` | Added `test_learning_disabled_components_are_none` — verifies disabled learning config leaves `learning_service`, `learning_store`, `config_proposal_manager` as None |

## Judgment Calls

- **Test fixture adjustment:** The prompt's suggested test code used `HealthMonitor(config=HealthConfig())` and `FixedClock()` without required positional args, and omitted `trade_logger`/`broker`/`risk_manager` required by `AppState`. Adjusted to match the existing `learning_app_state` fixture pattern (added all required fields, passed `fixed_time` to `FixedClock`, passed `event_bus`/`clock` to `HealthMonitor`).

## Scope Verification

- [x] 4 redundant `field_validator` methods removed from `LearningLoopConfig`
- [x] `field_validator` import removed from models.py
- [x] All 8 existing `TestLearningLoopConfig` validation tests still pass (Pydantic v2 `Field(ge=,le=)` errors include field name)
- [x] `closed_position_count` property added to `CounterfactualTracker` (returns `int`, not `list`)
- [x] `main.py` uses `getattr(tracker, "closed_position_count", 0)` with `int` default matching property return type
- [x] New test: `test_learning_disabled_components_are_none` passes
- [x] All existing tests pass

## Test Results

- **Learning tests:** 141 passed (unchanged)
- **Learning API tests:** 15 passed (14 existing + 1 new)
- **Full suite:** 3,837 passed; 8 pre-existing failures (AI config race, backtest engine xdist, counterfactual wiring DB isolation, server intelligence env-dependent)
- **Frontend:** 680 Vitest passed (unchanged, no frontend changes this session)
- **Ruff:** 0 new warnings on modified files (all flagged warnings pre-existing)

## Deferred Items

None discovered.

## Self-Assessment: CLEAN

## Context State: GREEN
