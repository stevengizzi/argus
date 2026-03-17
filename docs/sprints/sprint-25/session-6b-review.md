# Sprint 25, Session 6b — Tier 2 Review Report

---BEGIN-REVIEW---

## Summary

Session 6b added symbol particles to the Funnel 3D scene using Three.js
InstancedMesh. The implementation covers: FunnelSymbolManager (instanced
rendering for up to 5,000 particles), tier transition animation (0.5s lerp),
raycasting for hover/click, LOD ticker labels via CSS2DObject (capped at 50),
selected symbol highlighting (amber/gold, 2x scale), and ObservatoryPage
integration with selectedSymbol/onSelectSymbol prop drilling.

## Verification Results

| Check | Result |
|-------|--------|
| Observatory Vitest tests | 49/49 PASS (5 files) |
| Full Vitest suite | 572/572 PASS (86 files) |
| TypeScript strict (`tsc --noEmit`) | PASS, 0 errors |
| No backend files modified | PASS (changes limited to `argus/ui/`) |
| No trading pipeline files modified | PASS |

## Review Focus Findings

### 1. CRITICAL: fps >= 30 with 3,000+ instances

**Finding: CANNOT VERIFY (acknowledged by implementer)**

The architecture is sound for this target: InstancedMesh with a single draw call
for up to 5,000 particles, reusable temp objects (Matrix4, Color, Vector3) to
avoid per-frame allocation, and dirty-flag updates (`instanceMatrix.needsUpdate`
only when changed). The SphereGeometry uses 8 segments, which is appropriately
low-poly for particles. This is an architecturally correct approach.

However, runtime fps verification requires a visual test with populated data,
which the jsdom environment cannot provide. The close-out report correctly flags
this as a deferred item requiring manual verification. This matches escalation
criterion #10 (visual checkpoint after S6b).

**Verdict on this item: No architectural concern, but runtime verification
pending. Does NOT trigger escalation criterion #1 since the architecture uses
the correct instancing approach.**

### 2. InstancedMesh used (not individual Mesh per symbol)

**PASS.** `FunnelSymbolManager.ts` line 117 creates a single
`THREE.InstancedMesh(geometry, material, MAX_INSTANCES)` with `MAX_INSTANCES =
5000`. All symbols share this single draw call. Instance transforms and colors
are updated via `setMatrixAt` / `setColorAt`.

### 3. CSS2D label count capped at 50

**PASS.** `MAX_VISIBLE_LABELS = 50` (line 64). The `updateLabels()` method
(line 400) sorts symbols by distance to camera and takes `slice(0,
MAX_VISIBLE_LABELS)`. Labels outside the visible set have `visible = false`.

### 4. Proper disposal of all Three.js resources in dispose()

**PASS.** `FunnelSymbolManager.dispose()` (line 356) removes all labels from
the label group, disposes geometry and material, and clears both maps.
`FunnelScene.dispose()` (line 200) cancels the animation frame, disposes
controls, symbol manager, all tracked geometries and materials, clears the
scene, disposes the renderer, and removes both DOM elements (WebGL canvas and
CSS2D overlay).

### 5. Raycaster only checks on mouse move, not every frame

**PASS.** The raycaster is invoked in `FunnelScene.raycastSymbols()` (line 179),
which is called from the `handleMouseMove` event listener in `FunnelView.tsx`
(line 81-83). It is NOT called in the animation loop (`animate()` at line 346).

### 6. Tier transition uses lerp in animation loop, not CSS/Framer animation

**PASS.** The `update(deltaTime)` method (line 235) performs `position.lerp()`
each frame with a progress value `t = transitionElapsed / TRANSITION_DURATION`.
This is pure Three.js in the requestAnimationFrame loop.

## Additional Findings

### CONCERN-1: Dead code in WebSocket handler (Medium)

`FunnelView.tsx` lines 147-163: The `onmessage` handler parses `tier_transition`
events and creates a `singleUpdate` Map, but never calls
`sceneRef.current.updateSymbolTiers(singleUpdate)` or any equivalent method.
The Map is constructed then discarded. The comment at line 161 says "Re-fetch
full pipeline to stay in sync" but no refetch is triggered either. The WS
connection is established and authenticated but effectively does nothing.

The implementation relies entirely on the 10-second TanStack Query refetch
interval. This works but is misleading: the WS handler creates the appearance
of incremental updates without actually applying them. This dead code should
either be completed (call `updateSymbolTiers` with the single update) or
removed, and the WS connection should not be established if it serves no
purpose.

### CONCERN-2: Instance slot exhaustion without reclamation (Low)

`nextInstanceIndex` increments monotonically and never decreases. When symbols
are removed via `updateSymbolTiers()`, their instance slots are not reclaimed.
If symbol churn is high enough, the 5,000 limit could be reached even with
fewer than 5,000 active symbols. The close-out report acknowledges this and
defers it. For a single trading session this is unlikely to be a problem, but
it should be tracked.

### CONCERN-3: TIER_DEFS duplicated between FunnelScene.ts and FunnelSymbolManager.ts (Low)

Both files define identical `TIER_DEFS` arrays and `TierDef` interfaces.
`FunnelSymbolManager.ts` line 17 has a comment "must match TIER_DEFS in
FunnelScene.ts" which is a maintenance hazard. A shared constants file would
prevent drift.

### CONCERN-4: Keyboard Shift+R/Shift+F unreachable (Low)

In `useObservatoryKeyboard.ts`, the `hasModifier` check at line 113-114 only
guards against meta/ctrl/alt, so Shift key combos pass through correctly.
However, `VIEW_KEYS` maps lowercase `'r'` and `'f'`. When Shift is held,
`e.key` is uppercase `'R'` and `'F'`, so they won't match `VIEW_KEYS` and will
correctly fall through to the Shift+R/Shift+F handlers at lines 181-188. This
logic is correct but fragile -- the ordering dependency between the lowercase
view-switch check and the uppercase shift-combo check is implicit. A comment
would help future maintainers.

## Scope Compliance

All specified deliverables are present:

- [x] FunnelSymbolManager.ts -- NEW, InstancedMesh-based, ~464 LOC
- [x] FunnelScene.ts -- Modified, integrated symbol manager + CSS2DRenderer
- [x] FunnelView.tsx -- Modified, WS subscription + mouse events + tooltip
- [x] ObservatoryPage.tsx -- Modified, selectedSymbol + onSelectSymbol props
- [x] FunnelView.test.tsx -- Extended with 3 new FunnelSymbolManager tests
- [x] ObservatoryPage.test.tsx -- Updated to mock FunnelView lazy import

No files outside the specified scope were modified (the keyboard hook change was
required to support camera reset/fit-view shortcuts).

## Regression Checklist

| Item | Status |
|------|--------|
| No backend files modified | PASS |
| All Vitest tests pass (572) | PASS |
| TypeScript compiles cleanly | PASS |
| Vitest count: 572 (was 523 baseline + prior sessions) | PASS |
| Three.js code-split via React.lazy | PASS |

## Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| #1: Three.js performance below 30fps | NOT TRIGGERED (architecture correct; runtime verification pending per #10) |
| #2: Bundle size increase >500KB | Not measured this session (no build produced) |
| #4: Modification to strategy/pipeline logic | NOT TRIGGERED |
| #10: Visual checkpoint after S6b | PENDING -- developer should verify |

## Test Delta

- Before: 46 observatory tests, 569 total Vitest
- After: 49 observatory tests (+3), 572 total Vitest (+3)
- New tests cover: InstancedMesh creation, updateSymbolTiers positioning, selected symbol color change

## Verdict

The implementation is architecturally sound and meets all testable deliverables.
The InstancedMesh approach is correct for performance, disposal is thorough,
raycasting is event-driven not per-frame, and label count is capped. The main
concern is the dead code in the WS handler that creates the appearance of
incremental updates without applying them.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "confidence": 0.90,
  "findings": [
    {
      "id": "CONCERN-1",
      "severity": "medium",
      "category": "dead-code",
      "description": "WebSocket onmessage handler in FunnelView.tsx creates a singleUpdate Map from tier_transition events but never applies it. The WS connection is established and authenticated but serves no functional purpose. Data freshness relies entirely on 10-second TanStack Query refetch.",
      "file": "argus/ui/src/features/observatory/views/FunnelView.tsx",
      "lines": "147-163"
    },
    {
      "id": "CONCERN-2",
      "severity": "low",
      "category": "resource-management",
      "description": "Instance slot allocation is monotonically increasing without reclamation. Removed symbols leave unused slots. Acknowledged in close-out as deferred.",
      "file": "argus/ui/src/features/observatory/views/three/FunnelSymbolManager.ts",
      "lines": "165-166"
    },
    {
      "id": "CONCERN-3",
      "severity": "low",
      "category": "maintainability",
      "description": "TIER_DEFS array and TierDef interface duplicated between FunnelScene.ts and FunnelSymbolManager.ts. Comment says 'must match' but no enforcement mechanism.",
      "file": "argus/ui/src/features/observatory/views/three/FunnelSymbolManager.ts",
      "lines": "17-33"
    },
    {
      "id": "CONCERN-4",
      "severity": "low",
      "category": "maintainability",
      "description": "Shift+R/Shift+F camera shortcuts rely on implicit ordering: lowercase view-switch check precedes uppercase shift-combo check. Correct but fragile without a comment.",
      "file": "argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts",
      "lines": "117-188"
    }
  ],
  "tests_pass": true,
  "test_count": {
    "vitest": 572,
    "observatory": 49,
    "new_tests": 3
  },
  "typescript_clean": true,
  "scope_compliance": "full",
  "escalation_triggers_checked": ["#1", "#2", "#4", "#10"],
  "escalation_triggered": false,
  "close_out_assessment_agrees": true,
  "reviewer_notes": "Close-out self-assessment of MINOR_DEVIATIONS is accurate. The fps verification gap is expected and covered by escalation criterion #10 (visual checkpoint). CONCERN-1 (dead WS handler) is the most actionable finding -- the code should either complete the incremental update or remove the WS connection."
}
```
