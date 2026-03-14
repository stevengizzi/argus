# Sprint 24.5, Session 4: Frontend — Strategy Decision Stream Component

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/orchestrator/RecentSignals.tsx` (list display pattern)
   - `argus/ui/src/features/orchestrator/SignalDetailPanel.tsx` (slide-out panel pattern)
   - `argus/ui/src/hooks/useQualityData.ts` (TanStack Query hook pattern)
   - `argus/ui/src/features/orchestrator/index.ts` (barrel exports)
   - `argus/ui/src/services/` (API service layer — check existing patterns)
   - `argus/ui/src/components/QualityBadge.tsx` (GRADE_COLORS reference)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -10
   ```
   Expected: all passing
3. Verify branch: `sprint-24.5`

## Objective
Build the Strategy Decision Stream component and its TanStack Query hook as
self-contained units. The component shows a live-scrolling log of evaluation
events with color coding and symbol filtering.

## Requirements

1. **Create `argus/ui/src/hooks/useStrategyDecisions.ts`**:

   a. Define TypeScript types:
      ```typescript
      interface EvaluationEvent {
        timestamp: string;
        symbol: string;
        strategy_id: string;
        event_type: string;
        result: 'PASS' | 'FAIL' | 'INFO';
        reason: string;
        metadata: Record<string, unknown>;
      }
      ```

   b. TanStack Query hook:
      ```typescript
      export function useStrategyDecisions(
        strategyId: string | null,
        options?: { symbol?: string; limit?: number; enabled?: boolean }
      )
      ```
      - Polls `GET /api/v1/strategies/${strategyId}/decisions` every 3 seconds
      - Passes `symbol` and `limit` as query params
      - Returns `{ data, isLoading, error }` standard TanStack pattern
      - `enabled` defaults to `!!strategyId` (disabled when no strategy selected)
      - Use existing API service patterns (check `services/api.ts` or similar)

2. **Create `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx`**:

   a. Props: `{ strategyId: string; onClose: () => void }`

   b. **Header bar**: Strategy name/ID, close button (X icon from lucide-react)

   c. **Symbol filter**: Dropdown/select at top. Options populated from unique
      symbols in current event data. "All symbols" as default option.

   d. **Summary stats bar**: Compact row showing:
      - "Symbols: {n}" (unique symbols in events)
      - "Signals: {n}" (events with type SIGNAL_GENERATED)
      - "Rejected: {n}" (events with type SIGNAL_REJECTED)

   e. **Event list**: Scrolling list of events, newest at top. Each event row:
      - Timestamp (HH:MM:SS format, ET)
      - Symbol badge
      - Event type label
      - Result indicator with color:
        - PASS: green (`text-emerald-400`)
        - FAIL: red (`text-red-400`)
        - INFO: amber (`text-amber-400`)
        - SIGNAL_GENERATED: blue (`text-blue-400`)
        - QUALITY_SCORED: blue (`text-blue-400`)
      - Reason text (truncated with tooltip for long reasons)
      - Expandable metadata section (click to expand JSON details)

   f. **Empty state**: "Awaiting market data — evaluation events will appear
      when strategies begin processing candles."

   g. **Loading state**: Skeleton loader (follow existing patterns)

   h. **Styling**: Tailwind CSS v4. Dark theme consistent with existing UI.
      Use `Card` component wrapper. Framer Motion for list animations
      (stagger entrance).

3. **Modify `argus/ui/src/features/orchestrator/index.ts`**:
   - Export `StrategyDecisionStream`

## Constraints
- Do NOT modify any existing orchestrator components
- Do NOT modify OrchestratorPage.tsx (that's Session 5)
- Do NOT add WebSocket subscription — REST polling only
- Follow existing component patterns (Card wrapper, Tailwind utilities, lucide icons)
- Use standard TanStack Query patterns — no custom caching logic
- No localStorage or sessionStorage usage

## Test Targets
New tests in `argus/ui/src/features/orchestrator/StrategyDecisionStream.test.tsx`:
1. `renders event list with mock data` — verify events appear
2. `color codes PASS events as green` — verify CSS class
3. `color codes FAIL events as red`
4. `symbol filter filters displayed events` — select symbol, verify filtered
5. `empty state shows awaiting message` — empty data → message shown
6. `loading state shows skeleton` — isLoading → skeleton rendered
7. `summary stats show correct counts` — verify signal/rejected counts
8. `close button calls onClose`
- Minimum new test count: 8
- Test command: `cd argus/ui && npx vitest run src/features/orchestrator/StrategyDecisionStream.test.tsx`

## Visual Review
The developer should visually verify the following after this session:
1. **Decision Stream component** (render in isolation or storybook): Events
   display in a scrollable list with correct color coding
2. **Symbol filter**: Dropdown populates with unique symbols from event data
3. **Empty state**: Shows appropriate message when no events
4. **Dark theme**: Colors match existing Command Center aesthetic

Verification conditions:
- Component can be tested in isolation with mock data (no live backend needed)

## Definition of Done
- [ ] `useStrategyDecisions` hook created with polling
- [ ] `StrategyDecisionStream` component created with all features
- [ ] Exported from orchestrator barrel
- [ ] ≥8 Vitest tests written and passing
- [ ] No TypeScript build errors
- [ ] ruff/eslint passes
- [ ] Close-out report written to docs/sprints/sprint-24.5/session-4-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No new TS build errors | `cd argus/ui && npx tsc --noEmit` |
| Existing orchestrator components unaffected | `cd argus/ui && npx vitest run src/features/orchestrator/` |
| No console errors | Manual check in browser dev tools |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-4-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `cd argus/ui && npx vitest run src/features/orchestrator/`
5. Files NOT to modify: `OrchestratorPage.tsx`, `StrategyOperationsCard.tsx`, any backend files

## Session-Specific Review Focus (for @reviewer)
1. Verify hook polls at 3-second intervals (refetchInterval config)
2. Verify component handles API errors gracefully (error state, not crash)
3. Verify no localStorage/sessionStorage usage
4. Verify color coding matches spec (PASS=green, FAIL=red, INFO=amber, signals=blue)
5. Verify TypeScript types match backend EvaluationEvent structure
6. Verify no hardcoded API URLs — use existing service patterns

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
