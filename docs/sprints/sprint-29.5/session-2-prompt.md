# Sprint 29.5, Session 2: Paper Trading Data-Capture Mode

## Pre-Flight Checks
Before making any changes:
1. Read: `argus/core/config.py` (OrchestratorConfig), `argus/core/throttle.py`, `argus/core/orchestrator.py`, `config/risk_limits.yaml`, `config/orchestrator.yaml`
2. Run scoped baseline: `python -m pytest tests/core/test_orchestrator.py tests/core/test_throttle.py -x -q`
3. Verify branch: `sprint-29.5`

## Objective
Remove paper-trading data-capture blockers: disable weekly/daily loss limits (set to 100%), disable PerformanceThrottler suspension via config flag.

## Requirements

1. **Risk limit values** in `config/risk_limits.yaml`:
   - Change `daily_loss_limit_pct: 0.03` → `daily_loss_limit_pct: 1.0`
   - Change `weekly_loss_limit_pct: 0.05` → `weekly_loss_limit_pct: 1.0`
   - Add comment: `# PAPER TRADING: Set to 1.0 (100%) to maximize data capture. Restore to 0.03/0.05 before live trading.`

2. **Throttler suspend bypass** in `argus/core/config.py`:
   - Add `throttler_suspend_enabled: bool = True` to `OrchestratorConfig`

3. **Throttler suspend bypass** in `argus/core/throttle.py`:
   - Add `suspend_enabled: bool = True` parameter to `PerformanceThrottler.__init__()`
   - In `evaluate()`, if `not self._suspend_enabled`, return `ThrottleAction.NONE` immediately before any checks
   - Store as `self._suspend_enabled`

4. **Wire config** in `argus/core/orchestrator.py`:
   - Pass `suspend_enabled=config.throttler_suspend_enabled` when constructing `PerformanceThrottler`

5. **Config value** in `config/orchestrator.yaml`:
   - Add `throttler_suspend_enabled: false` with comment: `# PAPER TRADING: Disabled to allow all strategies to trade. Restore to true before live.`

6. **Update pre-live checklist** in `docs/pre-live-transition-checklist.md`:
   - Add entries for restoring `daily_loss_limit_pct`, `weekly_loss_limit_pct`, `throttler_suspend_enabled`

## Constraints
- Do NOT modify PerformanceThrottler internal logic (Sharpe/drawdown checks) — just add bypass
- Do NOT remove the risk limit checks in RiskManager — just make the limits permissive
- Preserve all existing config field defaults for non-paper configs

## Test Targets
- New tests:
  1. `test_throttler_suspend_disabled_returns_none` — when suspend_enabled=False, evaluate() returns NONE regardless of trade history
  2. `test_throttler_suspend_enabled_normal_behavior` — when suspend_enabled=True, existing behavior preserved
  3. `test_orchestrator_config_throttler_flag` — config loads with new field, default True
- Minimum new test count: 3
- Test command: `python -m pytest tests/core/test_orchestrator.py tests/core/test_throttle.py -x -q`

## Config Validation
| YAML Key | Model Field |
|----------|-------------|
| `throttler_suspend_enabled` | `OrchestratorConfig.throttler_suspend_enabled` |

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Risk Manager still checks limits | Existing risk manager tests pass (limits just more permissive) |
| Throttler still works when enabled | test_throttler_suspend_enabled_normal_behavior |
| Config backward compatible | Existing config tests pass without new field in YAML |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 3+ new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-2-closeout.md`

## Tier 2 Review
Invoke @reviewer with:
1. Review context: `docs/sprints/sprint-29.5/review-context.md`
2. Close-out: `docs/sprints/sprint-29.5/session-2-closeout.md`
3. Test command: `python -m pytest tests/core/test_orchestrator.py tests/core/test_throttle.py -x -q`
4. Files NOT modified: `argus/intelligence/`, `argus/execution/`, `argus/strategies/`

## Session-Specific Review Focus
1. Verify throttler bypass is config-gated, not hard-coded
2. Verify pre-live checklist updated with all changed values
3. Verify risk limit changes are value-only (no structural changes to RiskManager)
