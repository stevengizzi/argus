# Sprint 25.6, Session 4: Orchestrator Timeline Fixes (DEF-070/071)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/orchestrator/StrategyCoverageTimeline.tsx`
   - `argus/ui/src/utils/strategyConfig.ts` (check `getStrategyDisplay` — `name`, `shortName`, `letter`)
   - `argus/api/routes/orchestrator.py` (check how `is_throttled` and `is_active` are populated in allocation response)
2. Run scoped test baseline:
   ```
   cd argus/ui && npx vitest run src/features/orchestrator/StrategyCoverageTimeline
   ```
   Expected: all passing
3. Verify Sessions 1–3 are committed.

## Objective
Fix two display issues on the Orchestrator Strategy Coverage timeline: (1) "Afternoon Momentum" label truncated to "on Momentum" due to narrow label column, and (2) VWAP Reclaim incorrectly shown with throttled/hatched styling during its operating window.

## Requirements

### 1. Fix label truncation (DEF-070)
In `StrategyCoverageTimeline.tsx`:
- The `labelWidth` is hardcoded to 100px on desktop (~line 89). This is too narrow for "Afternoon Momentum".
- Option A (recommended): Increase `labelWidth` to 140px on desktop. Check that the timeline bars still have adequate width.
- Option B: Use `shortName` from `getStrategyDisplay()` instead of `name` on desktop. Verify what shortName is for Afternoon Momentum (likely "AfMo" or "Afternoon Mom").
- Choose whichever produces the better result. If widening to 140px causes the timeline to feel cramped, use shortName.

### 2. Fix throttled status display (DEF-071)
The hatched/striped bar is rendered when `alloc.is_throttled || !alloc.is_active` (~line 180).

First, investigate the data:
- Check `argus/api/routes/orchestrator.py` to see how `is_active` is determined in the allocation response
- Check if VWAP Reclaim being reported as `is_active: false` after suspension (it was suspended mid-session on March 19 after 5 consecutive losses)
- The circuit breaker suspension is correct behavior — but the bar should distinguish between:
  a. **Throttled by orchestrator** (hatched) — e.g., regime exclusion, performance throttle
  b. **Suspended by circuit breaker** (different visual?) — e.g., 5 consecutive losses
  c. **Outside operating window** (should show normal bar, just greyed if past)

For this sprint: ensure that during a strategy's operating window, the bar shows solid unless the strategy is actually throttled or suspended. If suspended mid-session, the hatched display is arguably correct — but the label should indicate "Suspended" not just appear throttled. If this distinction requires adding a `suspension_reason` field, that's in scope.

## Constraints
- Do NOT modify strategy files or strategy evaluation logic
- Do NOT modify `risk_manager.py`, `order_manager.py`
- Do NOT change the throttled pattern SVG definition (just fix when it's applied)

## Test Targets
- Existing tests: all must still pass
- New tests:
  1. Test that label renders full strategy name on desktop viewport (or shortName without truncation)
  2. Test that active, non-throttled strategy renders solid bar (no hatched pattern)
- Minimum new test count: 2
- Test command: `cd argus/ui && npx vitest run src/features/orchestrator/StrategyCoverageTimeline`

## Visual Review
1. "Afternoon Momentum" fully readable on desktop (no "on Momentum")
2. Active strategies show solid bars during their operating windows
3. Actually suspended strategies show hatched bars (if VWAP was suspended, hatched is correct)

Verification conditions: App running, Orchestrator page loaded during simulated or live market hours.

## Definition of Done
- [ ] Afternoon Momentum label fully visible on desktop
- [ ] Throttled/hatched bars accurately reflect strategy state
- [ ] All existing tests pass
- [ ] 2+ new Vitest tests
- [ ] `npx tsc --noEmit` clean
- [ ] Close-out report written to `docs/sprints/sprint-25.6/session-4-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide: review-context.md, session-4-closeout.md, `git diff HEAD~1`, scoped test command: `cd argus/ui && npx vitest run src/features/orchestrator/StrategyCoverageTimeline`, files NOT to modify: any backend Python file except possibly `orchestrator.py` routes.

## Session-Specific Review Focus (for @reviewer)
1. Verify label is not truncated at any standard desktop width (1024px+)
2. Verify hatched pattern condition correctly maps to strategy state
3. Verify no strategy file was modified

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
