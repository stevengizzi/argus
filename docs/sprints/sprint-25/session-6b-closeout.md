# Sprint 25, Session 6b — Close-Out Report

## Objective
Add symbol particles to the Funnel scene using InstancedMesh for performance.
Symbols positioned on tier discs. Click selects, hover shows tooltip, tier
transition animation, LOD ticker labels on zoom.

## Change Manifest

| File | Change |
|------|--------|
| `argus/ui/src/features/observatory/views/three/FunnelSymbolManager.ts` | **NEW** — InstancedMesh-based symbol particle manager (350 LOC) |
| `argus/ui/src/features/observatory/views/three/FunnelScene.ts` | Integrated FunnelSymbolManager, CSS2DRenderer, raycaster, deltaTime in animation loop |
| `argus/ui/src/features/observatory/views/FunnelView.tsx` | Added WS subscription, pipeline data forwarding, mouse events, tooltip overlay, symbol selection props |
| `argus/ui/src/features/observatory/ObservatoryPage.tsx` | Pass `selectedSymbol` + `onSelectSymbol` to LazyFunnelView |
| `argus/ui/src/features/observatory/views/FunnelView.test.tsx` | Extended mocks for new Three.js classes, added 3 FunnelSymbolManager tests |

## Judgment Calls

1. **Tier data source:** Used the existing `getObservatoryPipeline()` REST endpoint
   (which returns `tiers: Record<string, {count, symbols[]}>`) as the primary data
   source for symbol positions. WS `tier_transition` events trigger refetch via
   TanStack Query's `refetchInterval: 10_000`. This avoids duplicating the full
   symbol→tier map on the client.

2. **Instance reuse:** The current implementation uses a monotonically increasing
   `nextInstanceIndex`. For a single trading session this is fine (symbols rarely
   exceed 3,000). If symbol churn becomes an issue, a free-list allocator can be
   added.

3. **CSS2DRenderer container:** Set `container.style.position = 'relative'` in
   FunnelScene constructor to allow the CSS2D overlay to position correctly. The
   container div already had no explicit positioning, so this is safe.

## Scope Verification

- [x] Symbol particles rendered on tier discs via InstancedMesh
- [x] Hover tooltip with ticker name
- [x] Click selects symbol → detail panel (via onSelectSymbol callback)
- [x] Tier transition animation (0.5s lerp between discs)
- [x] LOD labels appear on zoom (max 50)
- [x] Selected symbol visually distinct (amber/gold, 2× scale)
- [x] All existing tests pass, 3 new tests added
- [ ] 30+ fps with 3,000+ particles — **requires visual verification with dev server**

## Regression Checks

- Observatory tests: 49/49 passing (was 46, +3 new)
- Full Vitest suite: 572/572 passing
- No files outside scope modified
- Detail panel components untouched (per constraint)

## Test Results

```
Observatory: 49 passed (5 files)
Full Vitest: 572 passed (86 files)
```

## Deferred Items

- **Performance verification (fps ≥ 30 with 3,000+ particles):** Requires running
  dev server with populated pipeline data. Cannot verify in jsdom test environment.
  Must be checked during visual review.
- **Instance slot reclamation:** Current monotonic index allocation doesn't reuse
  slots from removed symbols. Fine for single-session use; revisit if symbol churn
  approaches MAX_INSTANCES (5,000).

## Post-Review Fix

Tier 2 review flagged dead code in FunnelView.tsx WS handler (CONCERN-1). Fixed
by replacing the unused `singleUpdate` Map construction with a proper
`queryClient.invalidateQueries()` call on `tier_transition` and `pipeline_update`
events. This triggers an immediate pipeline refetch, which flows through to the
symbol manager with tier transition animations.

## Self-Assessment

**MINOR_DEVIATIONS** — All code deliverables complete. The fps performance gate
cannot be verified in the test environment and requires manual visual confirmation
with dev data. Post-review fix addressed dead WS handler code.

## Context State

**GREEN** — Session completed well within context limits. All files read before
modification. No compaction occurred.
