# Sprint 28.5, Session S4a: Order Manager — Exit Config + Position Trail State

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/execution/order_manager.py` (ManagedPosition class, constructor, on_approved)
   - `argus/core/config.py` (ExitManagementConfig from S2)
   - `config/exit_management.yaml` (from S2)
   - `argus/core/exit_math.py` (from S1 — function signatures)
2. Run scoped test baseline:
   ```
   python -m pytest tests/unit/execution/test_order_manager*.py tests/unit/strategies/test_atr_emission.py -x -q
   ```
3. Verify branch: `sprint-28.5`

## Objective
Add ExitManagementConfig reference to OrderManager, implement per-strategy config lookup with field-level deep merge (AMD-1), and extend ManagedPosition with trail/escalation state fields.

## Requirements

1. **ManagedPosition new fields:** Add to the ManagedPosition dataclass:
   - `trail_active: bool = False` — whether trailing stop is currently active
   - `trail_stop_price: float = 0.0` — current computed trail stop price
   - `escalation_phase_index: int = -1` — index into phases list (-1 = no phase reached)
   - `exit_config: ExitManagementConfig | None = None` — per-strategy resolved config
   - `atr_value: float | None = None` — captured from signal at entry

2. **OrderManager constructor:** The `exit_config` parameter added in S3 is already stored. Now also store per-strategy exit configs if the strategy YAMLs have `exit_management:` overrides. Load strategy configs from the strategy YAML files.

3. **Per-strategy config lookup:** Add a method `_get_exit_config(strategy_id: str) -> ExitManagementConfig`:
   - Check if strategy has a per-strategy override (from strategy YAML `exit_management:` key)
   - If yes: deep_update(global_config_dict, strategy_override_dict), validate via Pydantic → return
   - If no: return global ExitManagementConfig
   - Cache the merged result per strategy_id (computed once at startup or first call)

4. **Wire into on_approved / entry fill:** When creating a ManagedPosition (in `_handle_entry_fill` or wherever the position is first created):
   - Set `exit_config = self._get_exit_config(signal.strategy_id)`
   - Set `atr_value = signal.atr_value` (from the SignalEvent)
   - Other trail fields stay at defaults (trail not active at entry by default)

## Constraints
- Do NOT implement trail logic or escalation logic yet (S4b)
- Do NOT modify on_tick() behavior
- Do NOT modify _handle_t1_fill() behavior
- Do NOT modify fill_model.py or risk_manager.py
- Changes to order_manager.py should be additive — existing behavior must be identical

## Test Targets
- Minimum new test count: 6
- Tests (add to existing OM test file or create new):
  1. OrderManager._get_exit_config returns global default when no strategy override
  2. _get_exit_config returns merged config with strategy-specific override (AMD-1 deep merge)
  3. ManagedPosition initializes with trail_active=False, trail_stop_price=0.0
  4. ManagedPosition captures atr_value from signal
  5. ManagedPosition captures exit_config from per-strategy lookup
  6. _get_exit_config caches result (same object returned on second call)
- Test command: `python -m pytest tests/unit/execution/test_order_manager*.py -x -q -v`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing OM tests pass | Full OM test suite green |
| No behavioral change in on_tick, on_fill handlers | Existing tests cover these paths |
| ManagedPosition backward compatible | Existing tests create positions without new fields |

## Definition of Done
- [ ] ManagedPosition extended with 5 new fields
- [ ] _get_exit_config() implements AMD-1 field-level deep merge
- [ ] Entry fill captures atr_value and exit_config on new positions
- [ ] 6+ new tests passing
- [ ] All existing OM tests passing
- [ ] Close-out written to `docs/sprints/sprint-28.5/session-S4a-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.
The close-out report MUST include a structured JSON appendix fenced with ```json:structured-closeout.
**Write to:** `docs/sprints/sprint-28.5/session-S4a-closeout.md`

## Tier 2 Review
1. Review context: `docs/sprints/sprint-28.5/review-context.md`
2. Close-out: `docs/sprints/sprint-28.5/session-S4a-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test: `python -m pytest tests/unit/execution/test_order_manager*.py -x -q -v`
5. Files NOT to modify: fill_model.py, risk_manager.py, on_tick logic, _handle_t1_fill logic

## Session-Specific Review Focus (for @reviewer)
1. Verify ManagedPosition new fields have safe defaults (trail_active=False, etc.)
2. Verify _get_exit_config uses deep_update from S2 (AMD-1), not top-level key replacement
3. Verify no on_tick or _handle_t1_fill behavioral changes
4. Verify atr_value captured from signal at entry time
