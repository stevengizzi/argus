# Sprint 25, Session 7 — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-7-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Review Focus
1. Verify shared scene (no duplicate Three.js scene)
2. Verify OrbitControls disabled during transition
3. Verify orbit constrained in radar mode (vertical axis only)
4. Verify CSS2DObject labels (not TextGeometry)
5. Verify transition lerp in animation loop (not setTimeout)

## Output
Write to: `docs/sprints/sprint-25/session-7-review.md`
