# Sprint 24.5, Session 5: Frontend — Orchestrator Page Integration

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/OrchestratorPage.tsx` (target — 3-column layout)
   - `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx` (add button)
   - `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx` (S4 output)
   - `argus/ui/src/hooks/useStrategyDecisions.ts` (S4 output)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   cd argus/ui && npx vitest run src/features/orchestrator/ src/pages/ --reporter=verbose 2>&1 | tail -10
   ```
   Expected: all passing
3. Verify branch: `sprint-24.5`

## Objective
Wire the Strategy Decision Stream into the Orchestrator page as a slide-out
panel accessible from the strategy cards in StrategyOperationsGrid.

## Requirements

1. **Modify `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`**:

   a. Add a "View Decisions" button (or icon button) to each strategy card.
      Use a lucide-react icon (e.g., `ListChecks`, `Activity`, or `Eye`).

   b. The button calls an `onViewDecisions(strategyId: string)` callback prop.

   c. Styling: subtle button, consistent with existing card action patterns.
      Tooltip: "View strategy decisions"

2. **Modify `argus/ui/src/pages/OrchestratorPage.tsx`**:

   a. Add state for the slide-out panel:
      ```typescript
      const [decisionStrategyId, setDecisionStrategyId] = useState<string | null>(null);
      ```

   b. Pass `onViewDecisions={setDecisionStrategyId}` through to
      `StrategyOperationsGrid` → `StrategyOperationsCard`.

   c. Render the slide-out panel conditionally:
      ```tsx
      {decisionStrategyId && (
        <StrategyDecisionStream
          strategyId={decisionStrategyId}
          onClose={() => setDecisionStrategyId(null)}
        />
      )}
      ```

   d. The panel should render as a side panel or modal overlay — NOT inline
      in the page flow. It should slide in from the right (Framer Motion
      `AnimatePresence` + slide animation) and overlay the page content.
      Click outside or X button to close.

   e. **Critical:** Do NOT rearrange the existing page sections. The 3-column
      layout in Section 4 (DecisionTimeline + CatalystAlerts + RecentSignals)
      must remain unchanged.

3. **Modify `argus/ui/src/features/orchestrator/StrategyOperationsGrid.tsx`**
   (if needed to pass the callback through):
   - Accept and forward the `onViewDecisions` prop to each card.

## Constraints
- Do NOT rearrange or modify Section 4 (3-column layout)
- Do NOT modify the StrategyDecisionStream component itself (S4 output)
- Do NOT add new routes or pages — this is a panel/overlay, not a separate page
- Preserve existing navigation and keyboard shortcuts (DEC-199)
- Do NOT add any backend changes

## Test Targets
New tests in `argus/ui/src/features/orchestrator/StrategyDecisionStream.integration.test.tsx`
or extend existing files:
1. `clicking View Decisions opens slide-out panel`
2. `panel receives correct strategy ID`
3. `closing panel sets state to null`
4. `3-column layout preserved` — snapshot or structural assertion
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run src/features/orchestrator/ src/pages/`

## Visual Review
The developer should visually verify:
1. **Strategy cards**: "View Decisions" button/icon visible on each card
2. **Slide-out panel**: Opens from right side, overlays content
3. **Panel close**: X button and click-outside both close the panel
4. **3-column layout**: Section 4 unchanged after modifications
5. **Mobile responsive**: Panel doesn't break on smaller viewports

Verification conditions:
- App running with orchestrator data (live or mock)
- Test both opening and closing the panel multiple times

## Definition of Done
- [ ] "View Decisions" button on strategy cards
- [ ] Slide-out panel opens with correct strategy ID
- [ ] Panel closes via X button and click-outside
- [ ] 3-column layout preserved
- [ ] ≥4 Vitest tests written and passing
- [ ] No TypeScript build errors
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-5-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| 3-column layout preserved | Visual review + existing layout tests |
| Strategy cards still render | `cd argus/ui && npx vitest run src/features/orchestrator/StrategyOperationsCard.test.tsx` |
| No TS build errors | `cd argus/ui && npx tsc --noEmit` |
| Navigation shortcuts work | Manual check: keyboard shortcuts per DEC-199 |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-5-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-5-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `cd argus/ui && npx vitest run src/features/orchestrator/ src/pages/`
5. Files NOT to modify: `StrategyDecisionStream.tsx` (S4 output), backend files

## Session-Specific Review Focus (for @reviewer)
1. Verify 3-column layout in Section 4 is completely unchanged
2. Verify slide-out panel uses AnimatePresence for enter/exit animation
3. Verify panel is an overlay, not inserted into page flow
4. Verify onViewDecisions callback properly typed and passed through
5. Verify no new page routes added

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
