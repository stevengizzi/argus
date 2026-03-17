# Sprint 25, Session 9 — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-9-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/`

## Review Focus
1. Verify WS disconnect/reconnect on debrief toggle
2. Verify all data hooks accept and use date parameter
3. Verify date validation (retention window)
4. Verify no new npm packages for date picker
5. Verify "Reviewing [date]" indicator in debrief mode
6. Verify live metrics increment from WS data

## Output
Write to: `docs/sprints/sprint-25/session-9-review.md`
