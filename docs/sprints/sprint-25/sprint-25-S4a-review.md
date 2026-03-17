# Sprint 25, Session 4a — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-4a-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/detail/`

## Do Not Modify
Existing detail panel components (TradeDetailPanel, SignalDetailPanel)

## Review Focus
1. Verify panel does not close on canvas click (only Escape or close button)
2. Verify content swap animation (no close/reopen on symbol change)
3. Verify condition grid: green=pass, red=fail, gray=inactive
4. Verify strategy history uses Sprint 24.5 color palette
5. Verify no existing components modified

## Output
Write to: `docs/sprints/sprint-25/session-4a-review.md`
