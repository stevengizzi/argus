# Sprint 24.1, Session 4a: Frontend Layout Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/OrchestratorPage.tsx` — current layout structure
   - Find the Debrief page/tab component files — look for QualityOutcomeScatter import and Quality tab definition
   - Find the Performance page/tab component files — identify the Distribution tab
   - `argus/ui/src/features/debrief/` — directory structure for Debrief components
2. Run the scoped test baseline:
   ```
   cd argus/ui && npm test -- --run
   ```
   Expected: all passing
3. Verify you are on branch `sprint-24.1`
4. Confirm `tsc --noEmit` exits 0 (Session 3 must be complete)

## Objective
Two layout fixes: (1) Orchestrator page 3-column layout for Decision Log, Catalyst Alerts, and Recent Signals; (2) Move QualityOutcomeScatter from Debrief Quality tab to Performance Distribution tab.

## Requirements

### Item 5: Orchestrator 3-Column Layout (DEF-055)
In `src/pages/OrchestratorPage.tsx`:
- Find the section where Decision Log, Catalyst Alerts, and Recent Signals are rendered
- Currently, Recent Signals likely takes a full-width row
- Wrap all three components in a responsive grid:
  ```tsx
  <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
    <DecisionLog ... />
    <CatalystAlerts ... />
    <RecentSignals ... />
  </div>
  ```
- Each panel should fill its column equally on desktop
- On mobile (below `lg` breakpoint), stack vertically as single column

### Item 6: QualityOutcomeScatter Relocation (DEF-056)
1. **Find and move the scatter plot:**
   - Locate `QualityOutcomeScatter` component usage in the Debrief page/tabs
   - Remove it from the Debrief Quality tab
   - Add it to the Performance Distribution tab (find the correct file)
   - Update imports in both files

2. **Remove the Quality tab from Debrief:**
   - Remove the Quality tab definition from the Debrief tab list
   - Remove the 'q' keyboard shortcut mapping for the Quality tab
   - Debrief should have exactly 5 sections after removal
   - Update the DebriefPage component docstring to reflect 5 sections

3. **Verify tab indexing:** After removing the Quality tab, ensure remaining tabs render correctly and keyboard shortcuts still work for the remaining tabs.

## Constraints
- Do NOT modify: backend Python files, API routes, data fetching hooks
- Do NOT change: component logic, data transformations, or chart configurations
- Do NOT rearrange: other page layouts beyond the two specified items
- Preserve: all existing functionality of moved/rearranged components

## Visual Review
The developer should visually verify the following after this session:

1. **Orchestrator page (desktop):** Decision Log, Catalyst Alerts, and Recent Signals appear side-by-side in a 3-column row. Each column has equal width.
2. **Orchestrator page (mobile):** Same three components stack vertically, each taking full width.
3. **Debrief page:** Exactly 5 tab/section options visible. No "Quality" tab. Keyboard shortcuts for remaining tabs work.
4. **Performance page:** Distribution tab contains the QualityOutcomeScatter chart. Scatter chart renders correctly with data (or empty state if no data).

Verification conditions:
- Run the app with `npm run dev` in `argus/ui/`
- Load sample data via seed script (if needed for scatter chart data)
- Check both desktop (>1024px) and mobile (<768px) widths

## Test Targets
After implementation:
- Vitest: all existing tests pass
- New tests (if components have tests):
  1. OrchestratorPage renders all three panels in grid container
  2. DebriefPage renders exactly 5 sections
- Test command: `cd argus/ui && npm test -- --run`

## Definition of Done
- [ ] Orchestrator page has 3-column layout on desktop
- [ ] Mobile stacks vertically
- [ ] QualityOutcomeScatter on Performance Distribution tab
- [ ] No Quality tab on Debrief page (5 sections)
- [ ] No 'q' shortcut for Quality tab
- [ ] DebriefPage docstring updated
- [ ] All Vitest tests pass
- [ ] Visual review items verified
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Debrief page loads without error | Navigate to /debrief in browser — no console errors |
| Performance page loads without error | Navigate to /performance — Distribution tab shows scatter |
| Orchestrator page loads without error | Navigate to /orchestrator — 3-column layout visible |
| Remaining Debrief keyboard shortcuts work | Press each shortcut key — correct tab activates |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ` ```json:structured-closeout `.

**Write the close-out report to a file:**
`docs/sprints/sprint-24.1/session-4a-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-24.1/review-context.md`
2. The close-out report path: `docs/sprints/sprint-24.1/session-4a-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (scoped — non-final session):
   ```
   cd argus/ui && npm test -- --run
   ```
5. Files that should NOT have been modified:
   - Any Python files
   - Dashboard components (those are Session 4b)
   - `src/api/types.ts`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-24.1/session-4a-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **Orchestrator 3-column grid:** Verify responsive breakpoints (e.g., `lg:grid-cols-3`) so mobile stacks.
2. **All three panels in grid:** Verify Decision Log, Catalyst Alerts, AND Recent Signals are all grid children.
3. **Debrief tab removal complete:** Verify Quality tab removed, 'q' shortcut removed, exactly 5 sections. No orphaned imports.
4. **Scatter plot moved correctly:** Verify QualityOutcomeScatter renders in Performance Distribution tab with correct props.
5. **No functionality regression:** Verify scatter plot data fetching and interactions preserved.
6. **Tab index integrity:** Remaining tab indices and keyboard shortcuts are sequential and correct.

## Visual Review (for @reviewer)
The developer should visually verify:
1. **Orchestrator desktop:** 3-column layout, equal widths, no overflow
2. **Orchestrator mobile:** Vertical stack, full width
3. **Debrief:** 5 sections only, no Quality tab visible
4. **Performance Distribution:** Scatter plot present and rendering

## Sprint-Level Regression Checklist (for @reviewer)
- [ ] Order Manager position lifecycle unchanged
- [ ] TradeLogger handles quality-present and quality-absent trades
- [ ] Schema migration idempotent, no data loss
- [ ] Quality engine bypass path intact
- [ ] All pytest pass (full suite with `-n auto`)
- [ ] All Vitest pass
- [ ] TypeScript build clean (`tsc --noEmit` exits 0)
- [ ] API response shapes unchanged
- [ ] Frontend renders without console errors

## Sprint-Level Escalation Criteria (for @reviewer)
### Critical (Halt immediately)
1. Vitest tests fail after layout changes

### Warning (Proceed with caution, document)
2. Frontend layout breaks mobile/PWA rendering — defer mobile fixes, document
