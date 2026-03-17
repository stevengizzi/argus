# Sprint 25, Session 5a — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-5a-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Review Focus
1. Verify cell color mapping: green=pass, red=fail, gray=inactive (NOT gray=fail)
2. Verify sort order descending by conditions_passed
3. Verify strategy grouping when multiple strategies evaluate same tier
4. Verify row component simple enough for S5b virtualization

## Output
Write to: `docs/sprints/sprint-25/session-5a-review.md`
