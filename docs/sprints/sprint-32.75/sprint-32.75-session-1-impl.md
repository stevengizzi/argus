# Sprint 32.75, Session 1: Strategy Identity System

## Pre-Flight Checks
1. Read context:
   - `docs/sprints/sprint-32.75/review-context.md`
   - `argus/ui/src/utils/strategyConfig.ts`
   - `argus/ui/src/components/Badge.tsx`
   - `argus/ui/src/components/AllocationDonut.tsx`
   - `argus/ui/src/features/dashboard/SessionTimeline.tsx`
2. Run full test suite (first session): `cd argus && python -m pytest -x -q -n auto && cd argus/ui && npx vitest run`
3. Verify branch: `sprint-32.75-session-1`

## Objective
Add all 5 new PatternModule strategies to every strategy identity map in the frontend so they display unique colors, badges, and names instead of grey "STRA" fallbacks.

## Requirements

1. In `ui/src/utils/strategyConfig.ts`, add entries to `STRATEGY_DISPLAY` for:
   | strategy_id | name | shortName | letter | color | tailwindColor | badgeId |
   |------------|------|-----------|--------|-------|---------------|---------|
   | strat_dip_and_rip | Dip-and-Rip | DIP | D | #fb7185 | rose-400 | strat_dip_and_rip |
   | strat_hod_break | HOD Break | HOD | H | #34d399 | emerald-400 | strat_hod_break |
   | strat_gap_and_go | Gap-and-Go | GAP | G | #38bdf8 | sky-400 | strat_gap_and_go |
   | strat_abcd | ABCD | ABCD | X | #f472b6 | pink-400 | strat_abcd |
   | strat_premarket_high_break | PM High Break | PMH | P | #a3e635 | lime-400 | strat_premarket_high_break |

   Also add corresponding entries to `STRATEGY_BORDER_CLASSES` and `STRATEGY_BAR_CLASSES` with matching Tailwind color classes.

2. In `ui/src/components/Badge.tsx`, add the 5 new strategies to `StrategyId` type union, `strategyColors`, `strategyLabels`, and `strategyLetters` maps with matching colors and labels.

3. In `ui/src/components/AllocationDonut.tsx`, add the 5 new strategies to `STRATEGY_COLORS` and `STRATEGY_DISPLAY_NAMES` maps.

4. In `ui/src/features/dashboard/SessionTimeline.tsx`, add the 5 new strategies to `ALL_STRATEGY_WINDOWS` with correct operating windows:
   | Strategy | Start | End | Row |
   |----------|-------|-----|-----|
   | strat_dip_and_rip | 9:45 AM | 11:30 AM | 6 |
   | strat_hod_break | 10:00 AM | 3:30 PM | 7 |
   | strat_gap_and_go | 9:35 AM | 10:30 AM | 8 |
   | strat_abcd | 10:00 AM | 3:00 PM | 9 |
   | strat_premarket_high_break | 9:35 AM | 10:30 AM | 10 |

## Constraints
- Do NOT refactor Badge.tsx, AllocationDonut.tsx, or SessionTimeline.tsx to import from strategyConfig.ts — just add the missing entries to each file's existing maps
- Do NOT modify any backend Python files
- Do NOT change the fallback logic in `getStrategyDisplay()` — it should remain as-is for future unknown strategies
- Do NOT modify strategy detection logic or operating window enforcement

## Test Targets
- Update existing tests that assert strategy color/badge maps to include new entries
- New tests: verify `getStrategyDisplay()` returns correct config for all 12 strategy IDs (with and without `strat_` prefix)
- Verify `StrategyBadge` component renders correct label for each new strategy
- Minimum new/updated tests: 8
- Commands: `cd argus/ui && npx vitest run`

## Visual Review
1. **Badge component**: Each of the 12 strategies should show its unique colored badge abbreviation — no grey "STRA" badges anywhere
2. **AllocationDonut**: All strategies in the donut chart should have unique colors — no grey segments
3. **SessionTimeline**: All 12 strategies visible in the timeline with unique colors and correct time windows
4. **StrategyCoverageTimeline** (Orchestrator): All 12 strategies visible with display names (not "Strat Xxx")
5. **StrategyOperationsCard** (Orchestrator): Each strategy card header shows correct display name

Verification conditions: App running with paper trading active showing multiple strategies

## Definition of Done
- [ ] All 12 strategies have unique colors, badges, and names in strategyConfig.ts
- [ ] Badge.tsx, AllocationDonut.tsx, SessionTimeline.tsx updated with matching entries
- [ ] All existing tests pass
- [ ] New/updated tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-32.75/session-1-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Existing 7 strategies unchanged | `getStrategyDisplay('strat_orb_breakout').color === '#60a5fa'` |
| Fallback still works for unknown IDs | `getStrategyDisplay('unknown_strategy').color === '#6b7280'` |
| Badge normalization handles all prefix variants | Test with 'orb_breakout', 'strat_orb_breakout', 'ORB_BREAKOUT' |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.
Write the close-out report to: `docs/sprints/sprint-32.75/session-1-closeout.md`
Include structured JSON appendix per close-out skill.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-32.75/review-context.md`
2. Close-out: `docs/sprints/sprint-32.75/session-1-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `cd argus/ui && npx vitest run src/components/Badge.test.tsx src/utils/ src/features/dashboard/SessionTimeline.test.tsx`
5. Files NOT to modify: any Python files, any page files, any non-identity-related components

## Session-Specific Review Focus
1. Verify all 5 new strategies have entries in ALL FOUR files (strategyConfig.ts, Badge.tsx, AllocationDonut.tsx, SessionTimeline.tsx) — missing from any one causes inconsistent display
2. Verify Tailwind color classes are full static strings (not dynamic construction) — required for purge
3. Verify SessionTimeline operating windows match the strategy specs (e.g., ABCD is 10:00-15:00, not 9:30-15:00)
4. Verify no existing strategy colors/badges were accidentally changed

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-32.75/review-context.md` for the complete checklist.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-32.75/review-context.md` for escalation triggers.
