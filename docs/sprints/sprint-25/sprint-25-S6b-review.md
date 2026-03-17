# Sprint 25, Session 6b — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-6b-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Review Focus
1. **CRITICAL:** Verify fps ≥ 30 with 3,000+ instances (escalation trigger if not)
2. Verify InstancedMesh used (not individual Mesh per symbol)
3. Verify CSS2D label count capped at 50
4. Verify disposal of all Three.js resources
5. Verify raycaster only on mouse move, not every frame
6. Verify tier transition uses lerp in animation loop

## Output
Write to: `docs/sprints/sprint-25/session-6b-review.md`
