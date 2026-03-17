# Sprint 25, Session 8 — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-8-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Review Focus
1. Verify event density handling — no thousands of DOM elements
2. Verify active window time ranges match actual strategy configs
3. Verify debrief mode disables polling
4. Verify no charting library used (pure SVG/div)
5. Verify click handler correctly maps event to symbol

## Output
Write to: `docs/sprints/sprint-25/session-8-review.md`
