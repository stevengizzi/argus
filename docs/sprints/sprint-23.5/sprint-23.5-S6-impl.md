# Sprint 23.5, Session 6: Frontend — Debrief Intelligence Brief View

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DebriefPage.tsx` (current Debrief layout — tabs/sections)
   - `argus/ui/src/components/MarkdownRenderer.tsx` (existing markdown rendering — reuse)
   - `argus/ui/src/hooks/useCatalysts.ts` (S5 output — hook patterns, type definitions)
   - `argus/api/intelligence_routes.py` (S4 output — briefing API response shapes)
2. Run the frontend test suite: `cd argus/ui && npx vitest run`
   Expected: 392+ tests + S5 tests, all passing
3. Verify S5 artifacts exist: `ls argus/ui/src/hooks/useCatalysts.ts argus/ui/src/components/CatalystBadge.tsx`

## Objective
Add an Intelligence Brief section to the Debrief page — rendered markdown view of pre-market intelligence briefs with date navigation, a generate button, and proper loading/empty states.

## Requirements

1. **Add briefing hooks to `useCatalysts.ts`** (or create separate `useBriefings.ts`):
   - **`useBriefing(date?: string)`**: Fetches `GET /api/v1/premarket/briefing?date={date}`. Returns `{ data, isLoading, error, isError }`. No auto-refetch (briefs are generated once).
   - **`useBriefingHistory(limit?: number)`**: Fetches `GET /api/v1/premarket/briefing/history?limit={limit}`. Returns list of past briefings with date and id.
   - **`useGenerateBriefing()`**: Mutation hook for `POST /api/v1/premarket/briefing/generate`. Returns `{ mutate, isLoading }`. On success, invalidates briefing query cache.
   - **Type definitions**:
     ```typescript
     interface IntelligenceBrief {
       id: string;
       date: string;
       brief_type: string;
       content: string;  // markdown
       symbols_covered: string[];
       catalyst_count: number;
       generated_at: string;
       generation_cost_usd: number;
     }
     ```

2. **Create `argus/ui/src/components/IntelligenceBriefView.tsx`**: Main brief viewing component.
   - **Date Navigation**: A date picker or prev/next arrows allowing the user to browse briefs by date. Default: today (ET).
   - **Brief Display**: When a brief exists for the selected date, render the `content` field as formatted markdown using the existing `MarkdownRenderer` component.
   - **Metadata Bar**: Show below the brief: "Generated at {time} | {catalyst_count} catalysts | {symbols_covered.length} symbols | Cost: ${generation_cost_usd.toFixed(4)}"
   - **Generate Button**: "Generate Brief" button that calls `useGenerateBriefing().mutate()`. Show loading spinner during generation. Disable button while generating.
   - **Empty State**: When no brief exists for selected date, show: "No intelligence brief for {date}" with the Generate Brief button.
   - **Loading State**: Skeleton/spinner while fetching brief.
   - **Error State**: "Failed to load briefing" with retry button.

3. **Create `argus/ui/src/components/BriefingCard.tsx`**: Compact card for briefing history.
   - Props: `brief: IntelligenceBrief`, `onClick: () => void`.
   - Shows: date, catalyst count, symbol count, truncated first line of content.
   - Used in a history sidebar/list within IntelligenceBriefView.

4. **Integrate into Debrief page**: Modify `DebriefPage.tsx`.
   - Add an "Intelligence Brief" section/tab alongside existing sections (Briefings, Documents, Journal).
   - If Debrief uses tabs: add a new tab. If it uses sections: add a new section at the top or in a logical position.
   - `<IntelligenceBriefView />` is the content of this section/tab.
   - Do NOT restructure existing Debrief layout. Do NOT remove or modify existing tabs/sections.

## Constraints
- Do NOT modify any backend files
- Do NOT modify pages other than DebriefPage.tsx
- Do NOT modify existing Debrief components (briefings, documents, journal)
- Use existing MarkdownRenderer component for brief content rendering
- Use only Tailwind utility classes for styling
- Do NOT use conditional rendering that creates different React element trees

## Visual Review
The developer should visually verify the following after this session:
1. **Debrief page**: Intelligence Brief section/tab is accessible and clearly labeled
2. **Brief content**: Markdown renders with proper formatting — headers, bold symbols, bullet points
3. **Date navigation**: Can browse to different dates; today loads by default
4. **Generate button**: Clicking triggers generation; loading spinner shows; brief appears after generation
5. **Empty state**: Shows appropriate message with Generate button when no brief exists
6. **Existing sections**: Briefings, Documents, Journal tabs/sections all still work correctly

Verification conditions:
- Backend running with at least one generated briefing (run `POST /api/v1/premarket/briefing/generate` first)
- Some dates should have no briefing (to test empty state)

## Test Targets
After implementation:
- Existing Vitest tests: all must still pass
- New tests:
  1. IntelligenceBriefView: renders brief content as markdown
  2. IntelligenceBriefView: shows empty state when no brief
  3. IntelligenceBriefView: date navigation changes displayed brief
  4. IntelligenceBriefView: generate button triggers mutation
  5. BriefingCard: renders date and catalyst count
  6. BriefingCard: truncates long content
- Minimum new test count: 6 Vitest
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing Vitest tests pass
- [ ] All existing pytest tests pass
- [ ] New Vitest tests written and passing (≥6)
- [ ] Visual review items ready for inspection
- [ ] Existing Debrief sections unchanged
- [ ] MarkdownRenderer reused for brief content

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| No backend files modified | `git diff --name-only` shows only UI files |
| Only DebriefPage modified | `git diff --name-only argus/ui/src/pages/` shows only DebriefPage.tsx |
| Existing Debrief tabs work | Navigate to each existing tab, verify content loads |
| MarkdownRenderer not modified | `git diff argus/ui/src/components/MarkdownRenderer.tsx` returns empty |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
R1–R25 from `docs/sprints/sprint-23.5/review-context.md`

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Items 1–15 from `docs/sprints/sprint-23.5/review-context.md`
