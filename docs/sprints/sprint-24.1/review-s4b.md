# Tier 2 Review: Sprint 24.1, Session 4b

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-24.1/session-4b-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-24.1/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-24.1/session-4b-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1` (or the commit range for Session 4b)
- Test command (scoped — non-final session):
  ```
  cd argus/ui && npm test -- --run
  ```
- Files that should NOT have been modified:
  - Any Python files
  - `src/api/types.ts` (should not need changes)
  - Orchestrator layout (that was Session 4a)
  - Debrief/Performance tabs (that was Session 4a)

## Session-Specific Review Focus
1. **Recharts Tooltip integration:** Verify tooltips use Recharts' `<Tooltip>` component (not custom hover handlers). Verify tooltip content is correctly formatted.
2. **Donut Legend:** Verify legend uses consistent grade colors from shared constants (GRADE_COLORS). Verify all grades are represented.
3. **QualityBadge reuse:** Verify Dashboard tables use the existing `QualityBadge` component, not a reimplementation.
4. **Null handling:** Verify positions/trades with null quality_grade show "—" (not a broken badge, empty string, or error).
5. **SignalDetailPanel data access:** Verify the detail panel reads from existing API data — no new fetch calls. If quality breakdown components aren't available in the signal data, verify graceful "—" rendering.
6. **Click behavior:** Verify only one detail panel opens at a time. Verify re-clicking the same row collapses it.
7. **TypeScript compliance:** Verify `tsc --noEmit` still exits 0 after these changes. New components should be properly typed.
8. **No new API calls:** Verify no new `useQuery` hooks or fetch calls were added. All data should come from existing queries.

## Visual Review
The developer should visually verify:
1. **Donut tooltips:** Hover over each segment — tooltip shows grade, count, percentage
2. **Donut legend:** All grade colors shown with labels below the chart
3. **Histogram tooltips:** Hover over bars — tooltip shows score range and count
4. **Dashboard Positions:** Quality column visible with badges
5. **Dashboard Recent Trades:** Quality column visible with badges
6. **Orchestrator signals:** Click a row — detail panel expands below
7. **Signal detail panel:** Shows grade, score, breakdown, prices
8. **Mobile:** All elements render without overflow

Verification conditions:
- Run `npm run dev` in `argus/ui/`
- Load sample/seed data
- Desktop and mobile widths

## Additional Context
This is the most visually complex session. The developer's visual review is critical — code review alone cannot verify tooltip positioning, chart interactions, or responsive layout behavior.
