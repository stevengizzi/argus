# Sprint 25, Session 11 — Tier 2 Review Prompt (FINAL SESSION)

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-11-closeout.md`

## Diff & Test (FULL SUITE — final session)
Diff: `git diff HEAD~1` (or full sprint diff)
Test:
  `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
  `cd argus/ui && npx vitest run`

## Do Not Modify
ALL trading pipeline files per regression checklist

## Review Focus
1. Verify complete keyboard flow works (full sequence from requirements)
2. Verify no trading pipeline files modified across ENTIRE sprint
3. Verify Three.js code-split (not in main bundle)
4. Verify test count increased from baseline (2,768 pytest + 523 Vitest)
5. Verify all 4 views render, all transitions smooth
6. Verify Observatory does not affect other page performance
7. **Check ALL items in regression checklist** (final session)

## Output
Write to: `docs/sprints/sprint-25/session-11-review.md`
