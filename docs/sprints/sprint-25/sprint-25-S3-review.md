# Sprint 25, Session 3 — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-3-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/`

## Do Not Modify
Existing page components, existing hooks

## Review Focus
1. Verify keyboard hook only fires when Observatory page is focused
2. Verify Tab preventDefault doesn't break accessibility outside Observatory
3. Verify React.lazy used for code-splitting
4. Verify Framer Motion used for panel animation
5. Verify no new npm packages installed
6. Verify full-bleed layout (no Card wrappers, no grid)

## Output
Write to: `docs/sprints/sprint-25/session-3-review.md`
