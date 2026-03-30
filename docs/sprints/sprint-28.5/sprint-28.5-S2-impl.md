# Sprint 28.5, Session S2: Config Models + SignalEvent atr_value

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/config.py` (existing Pydantic models, OrderManagerConfig)
   - `argus/core/events.py` (SignalEvent, SignalRejectedEvent)
   - `argus/core/exit_math.py` (from S1 — StopToLevel enum, function signatures)
   - `config/order_manager.yaml` (existing exit-related config for reference)
2. Run the scoped test baseline (DEC-328 — Session 2+):
   ```
   python -m pytest tests/unit/core/test_exit_math.py -x -q
   ```
   Expected: all S1 tests passing
3. Verify branch: `sprint-28.5`

## Objective
Create Pydantic config models for exit management, create `config/exit_management.yaml`, implement field-level deep merge (AMD-1), and add `atr_value` field to SignalEvent and SignalRejectedEvent.

## Requirements

1. In `argus/core/config.py`, add these Pydantic models:

   a. `TrailingStopConfig(BaseModel)` with `model_config = ConfigDict(extra="forbid")`:
      - `enabled: bool = False`
      - `type: Literal["atr", "percent", "fixed"] = "atr"`
      - `atr_multiplier: float = Field(default=2.5, gt=0)`
      - `percent: float = Field(default=0.02, gt=0, le=0.2)`
      - `fixed_distance: float = Field(default=0.50, gt=0)`
      - `activation: Literal["after_t1", "after_profit_pct", "immediate"] = "after_t1"`
      - `activation_profit_pct: float = Field(default=0.005, ge=0)`
      - `min_trail_distance: float = Field(default=0.05, ge=0)`

   b. `EscalationPhase(BaseModel)` with `model_config = ConfigDict(extra="forbid")`:
      - `elapsed_pct: float = Field(gt=0, le=1.0)`
      - `stop_to: StopToLevel` (import from exit_math.py)

   c. `ExitEscalationConfig(BaseModel)` with `model_config = ConfigDict(extra="forbid")`:
      - `enabled: bool = False`
      - `phases: list[EscalationPhase] = []`
      - Validator: phases must be sorted by elapsed_pct ascending

   d. `ExitManagementConfig(BaseModel)` with `model_config = ConfigDict(extra="forbid")`:
      - `trailing_stop: TrailingStopConfig = TrailingStopConfig()`
      - `escalation: ExitEscalationConfig = ExitEscalationConfig()`

2. Add a `deep_update(base: dict, override: dict) -> dict` utility function (in config.py or a shared utils module) that recursively merges override into base at the field level. This implements AMD-1: a strategy's `trailing_stop.atr_multiplier: 3.0` overrides only that field; all other fields inherit from global.

3. In `argus/core/events.py`, add `atr_value: float | None = None` to:
   - `SignalEvent` dataclass
   - `SignalRejectedEvent` dataclass (if it doesn't already carry it via the signal reference)

4. Create `config/exit_management.yaml` with all default values matching the Pydantic model defaults. Include comments explaining each field.

## Constraints
- Do NOT modify `config/order_manager.yaml`
- Do NOT modify `argus/core/fill_model.py`
- Do NOT modify any strategy files (that's S3)
- `extra="forbid"` on all new models to catch unknown keys

## Config Validation
Write a test that loads `config/exit_management.yaml` and verifies all keys are recognized by the Pydantic models:
1. Load YAML, extract trailing_stop and escalation sections
2. Instantiate TrailingStopConfig and ExitEscalationConfig from the YAML data
3. Verify no ValidationError on valid config
4. Verify ValidationError on unknown key (e.g., `trailing_stop.bogus_field: 123`)

## Test Targets
- New test file: `tests/unit/core/test_exit_management_config.py`
- Minimum new test count: 12
- Tests to write:
  1. TrailingStopConfig valid defaults load correctly
  2. TrailingStopConfig rejects atr_multiplier ≤ 0
  3. TrailingStopConfig rejects percent > 0.2
  4. EscalationPhase rejects elapsed_pct > 1.0
  5. StopToLevel enum has all 4 AMD-5 values (breakeven, quarter_profit, half_profit, three_quarter_profit)
  6. ExitEscalationConfig validates phases sorted ascending
  7. ExitManagementConfig round-trip from YAML file
  8. Unknown YAML key raises ValidationError (extra="forbid")
  9. AMD-1: deep_update merges single field, inherits rest from global
  10. AMD-1: deep_update with full trailing_stop section override
  11. SignalEvent with atr_value=None (backward compat — existing constructor still works)
  12. SignalEvent with atr_value=1.5 (field set correctly)
- Test command: `python -m pytest tests/unit/core/test_exit_management_config.py tests/unit/core/test_exit_math.py -x -q -v`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| SignalEvent backward compatible | Existing tests that create SignalEvent still pass without atr_value |
| No existing config files modified | `git diff --name-only` excludes order_manager.yaml, risk_limits.yaml |
| extra="forbid" on all new models | grep ConfigDict in new model definitions |

## Definition of Done
- [ ] 4 Pydantic models created (TrailingStopConfig, EscalationPhase, ExitEscalationConfig, ExitManagementConfig)
- [ ] deep_update() utility implemented (AMD-1)
- [ ] atr_value field added to SignalEvent and SignalRejectedEvent
- [ ] config/exit_management.yaml created with documented defaults
- [ ] 12+ new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-28.5/session-S2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`. Write to: `docs/sprints/sprint-28.5/session-S2-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-28.5/review-context.md`
2. Close-out report: `docs/sprints/sprint-28.5/session-S2-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/unit/core/test_exit_management_config.py tests/unit/core/test_exit_math.py -x -q -v`
5. Files NOT to modify: fill_model.py, risk_manager.py, order_manager.yaml, any strategy files

## Post-Review Fix Documentation
If CONCERNS, update close-out and review files per template.

## Session-Specific Review Focus (for @reviewer)
1. Verify AMD-1: deep_update does recursive field-level merge, not top-level key replacement
2. Verify extra="forbid" on ALL new Pydantic models
3. Verify StopToLevel enum imported from exit_math.py (single source of truth)
4. Verify SignalEvent atr_value=None default doesn't break existing SignalEvent construction
5. Verify exit_management.yaml defaults match Pydantic model defaults exactly

## Sprint-Level Regression Checklist
[Same as S1 — see review-context.md]

## Sprint-Level Escalation Criteria
[Same as S1 — see review-context.md]
