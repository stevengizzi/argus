# Sprint 27.95, Session 3a: Overflow Infrastructure

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/core/events.py` — RejectionStage enum, SignalRejectedEvent
   - `argus/config/counterfactual.yaml` — reference pattern for config file structure
   - Config Pydantic models — find where CounterfactualConfig is defined, follow same pattern
2. Run scoped test baseline:
   ```bash
   python -m pytest tests/core/ tests/test_config* -x -q
   ```
   Expected: all passing (full suite confirmed by Session 4 close-out)
3. Verify Sessions 1a, 1b, 2, and 4 changes are committed

## Objective
Add overflow infrastructure: OverflowConfig Pydantic model, `config/overflow.yaml`, and `RejectionStage.BROKER_OVERFLOW` enum value. This is the foundation for the routing logic in Session 3b.

## Requirements

1. **In `argus/core/events.py`**, add enum value:
   - Add `BROKER_OVERFLOW = "broker_overflow"` to the `RejectionStage` enum
   - Place it after the existing values (QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW)

2. **Create `argus/config/overflow.yaml`:**
   ```yaml
   overflow:
     enabled: true
     broker_capacity: 30
   ```

3. **Add OverflowConfig Pydantic model:**
   - Find where other config models are defined (likely `argus/config/` or similar)
   - Create `OverflowConfig(BaseModel)`:
     - `enabled: bool = True`
     - `broker_capacity: int = 30` with validator `ge=0`
   - Wire into SystemConfig (follow the pattern used by CounterfactualConfig)
   - Ensure `overflow.yaml` is loaded during config initialization

4. **Add overflow config to `config/system.yaml` and `config/system_live.yaml`:**
   - Add the overflow section referencing the overflow.yaml file, or inline it (follow existing pattern for how counterfactual config is included)

## Constraints
- Do NOT modify: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/ai/`, `argus/data/`, `argus/intelligence/`, `argus/execution/`
- Do NOT add: routing logic (that's Session 3b), API endpoints, frontend components
- This is infrastructure only — no behavioral changes to the signal pipeline

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write (~6):
  1. `RejectionStage.BROKER_OVERFLOW` enum value exists and has correct string value
  2. OverflowConfig loads with defaults (enabled=True, broker_capacity=30)
  3. OverflowConfig validates broker_capacity >= 0
  4. OverflowConfig rejects negative broker_capacity
  5. overflow.yaml loads successfully
  6. Config fields recognized by Pydantic model (no silently ignored keys)
- Minimum new test count: 6
- Test command: `python -m pytest tests/core/ tests/test_config* -x -q`

## Config Validation
Write a test verifying overflow config keys are recognized:
| YAML Key | Model Field |
|----------|-------------|
| `enabled` | `enabled` |
| `broker_capacity` | `broker_capacity` |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 6+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to `docs/sprints/sprint-27.95/session-3a-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing RejectionStage values unchanged | Verify QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW still exist |
| No behavioral changes to signal pipeline | Verify no imports of OverflowConfig outside config layer |
| Config loading for existing sections unaffected | Run existing config tests |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.
**Write the close-out report to:** `docs/sprints/sprint-27.95/session-3a-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-27.95/review-context.md`
2. Close-out report: `docs/sprints/sprint-27.95/session-3a-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest tests/core/ tests/test_config* -x -q`
5. Files NOT modified: `argus/strategies/`, `argus/backtest/`, `argus/ui/`, `argus/intelligence/`, `argus/execution/`, `argus/data/`

Review report: `docs/sprints/sprint-27.95/session-3a-review.md`

## Post-Review Fix Documentation
If CONCERNS reported and fixed, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify BROKER_OVERFLOW enum value won't break existing RejectionStage consumers (CounterfactualTracker, FilterAccuracy)
2. Verify OverflowConfig follows existing config patterns (Pydantic BaseModel, YAML loading)
3. Verify no behavioral changes — only infrastructure additions

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Existing RejectionStage enum values intact
- [ ] Config loading unchanged for existing sections
- [ ] Full test suite passes, no hangs

## Sprint-Level Escalation Criteria (for @reviewer)
1. New enum value breaks existing consumers → halt, investigate
2. Pre-flight test failures → investigate
