# Sprint 25, Session 5b — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-5b-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/`

## Review Focus
1. Verify virtual scroll implementation doesn't install new packages
2. Verify highlight tracks by symbol, not array index
3. Verify stable sort (same-score symbols don't jump)
4. Verify debrief mode disables WS subscription

## Output
Write to: `docs/sprints/sprint-25/session-5b-review.md`
