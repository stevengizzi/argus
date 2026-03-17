# Sprint 25, Session 6a — Tier 2 Review Prompt

## Context
Read: `docs/sprints/sprint-25/review-context.md`
Close-out: `docs/sprints/sprint-25/session-6a-closeout.md`

## Diff & Test
Diff: `git diff HEAD~1`
Test: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Review Focus
1. Verify React.lazy code-splitting (Three.js not in main bundle)
2. Verify proper disposal of all Three.js resources on unmount
3. Verify ResizeObserver cleanup
4. Verify requestAnimationFrame loop cancelled on unmount
5. Verify OrbitControls from examples/jsm (not separate package)
6. Verify no post-processing or PBR materials

## Output
Write to: `docs/sprints/sprint-25/session-6a-review.md`
