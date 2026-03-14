# Tier 2 Review: Sprint 24.1, Session 4a

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any source code files.

Follow the review skill in `.claude/skills/review.md`.

Your review report MUST include a structured JSON verdict at the end,
fenced with ` ```json:structured-verdict `. See the review skill for the
full schema and requirements.

**Write the review report to a file:**
`docs/sprints/sprint-24.1/session-4a-review.md`

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`docs/sprints/sprint-24.1/review-context.md`

## Tier 1 Close-Out Report
Read the close-out report from:
`docs/sprints/sprint-24.1/session-4a-closeout.md`

## Review Scope
- Diff to review: `git diff HEAD~1` (or the commit range for Session 4a)
- Test command (scoped — non-final session):
  ```
  cd argus/ui && npm test -- --run
  ```
- Files that should NOT have been modified:
  - Any Python files
  - Dashboard components (those are Session 4b)
  - `src/api/types.ts` (should have been fixed in Session 3)

## Session-Specific Review Focus
1. **Orchestrator 3-column grid:** Verify the grid uses responsive breakpoints (e.g., `lg:grid-cols-3`) so mobile still stacks vertically.
2. **All three panels in grid:** Verify Decision Log, Catalyst Alerts, AND Recent Signals are all children of the grid container. Not just two of three.
3. **Debrief tab removal complete:** Verify the Quality tab definition is removed, the 'q' shortcut is removed, and exactly 5 sections remain. No orphaned imports of QualityOutcomeScatter in Debrief files.
4. **Scatter plot moved correctly:** Verify QualityOutcomeScatter renders in Performance Distribution tab with correct props and data hooks.
5. **No functionality regression:** Verify the scatter plot's data fetching, interactions, and rendering are preserved (same props, same hooks).
6. **Tab index integrity:** After removing the Quality tab, verify remaining tab indices and keyboard shortcuts are sequential and correct.

## Visual Review
The developer should visually verify:
1. **Orchestrator desktop:** 3-column layout, equal widths, no overflow
2. **Orchestrator mobile:** Vertical stack, full width
3. **Debrief:** 5 sections only, no Quality tab visible
4. **Performance Distribution:** Scatter plot present and rendering

Verification conditions:
- Run `npm run dev` in `argus/ui/`
- Check desktop (>1024px) and mobile (<768px)

## Additional Context
Two independent layout changes in one session. The Orchestrator grid is purely CSS/Tailwind. The scatter relocation is a component move between pages — watch for stale imports.
