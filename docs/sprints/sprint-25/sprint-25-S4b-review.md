# Sprint 25, Session 4b — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-4b-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/`

## Do Not Modify
Lightweight Charts library, shared chart utilities

## Review Focus
1. Verify chart disposal on unmount (no memory leaks)
2. Verify chart reinitializes on symbol change (not just updates)
3. Verify TanStack Query keys include symbol for auto-refetch
4. Verify polling disabled in debrief mode
5. Verify Lightweight Charts uses 2D canvas (no WebGL context conflict)

## Output
Write to: `docs/sprints/sprint-25/session-4b-review.md`
