# Sprint 25, Session 6b: Frontend — Funnel Symbol Particles

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/observatory/views/three/FunnelScene.ts` (S6a output)
   - `argus/ui/src/features/observatory/views/FunnelView.tsx` (S6a output)
   - `argus/api/routes/observatory.py` (S1 — pipeline endpoint for tier populations)
   - `argus/api/websocket/observatory_ws.py` (S2 — WS messages for live updates)
   - `argus/ui/src/features/observatory/detail/SymbolDetailPanel.tsx` (S4a — selection callback)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Add symbol particles to the Funnel scene using instanced meshes for performance. Symbols are positioned on their current tier disc. Clicking a particle selects the symbol. Hover shows a tooltip. Symbols animate between tiers when their stage changes. LOD: ticker labels appear only when zoomed in.

## Requirements

1. **Create `argus/ui/src/features/observatory/views/three/FunnelSymbolManager.ts`:**

   a. **Instanced mesh setup:**
      - Use `InstancedMesh` with a small sphere geometry (SphereGeometry, radius ~0.03–0.05) for symbol particles
      - Pre-allocate for maximum expected count (e.g., 5,000 instances)
      - Set instance count to actual symbol count
      - Color per instance via `InstancedBufferAttribute` — encode tier membership as color (matching tier disc colors but more saturated/opaque)

   b. **Position management:**
      - Each symbol has a target position on its tier disc
      - Positions distributed evenly across the disc surface (polar coordinates: random angle, random radius 0 to disc_radius × 0.85)
      - Maintain a Map<symbol, {tierIndex, position, instanceIndex}>
      - Method: `updateSymbolTiers(tierData: Map<string, {tier: number, conditionsPassed: number}>)` — called when WS data arrives

   c. **Tier transition animation:**
      - When a symbol's tier changes, animate its position from the old tier disc to the new tier disc
      - Use linear interpolation over ~0.5s (update in the animation loop)
      - Symbols moving DOWN the funnel (closer to trigger) get a brief brightness pulse

   d. **Interaction — raycasting:**
      - On mouse move: raycast against instanced mesh to find hovered instance
      - Hovered instance: increase scale slightly (1.5×), show HTML tooltip overlay with ticker + tier name
      - On click: find clicked instance, call `onSelectSymbol(symbol)` callback
      - Selected instance: distinct color (amber/gold) and larger scale (2×)

   e. **LOD — ticker labels:**
      - When camera distance < threshold (e.g., 5 units), render CSS2DRenderer labels for nearby symbols
      - Use `CSS2DObject` from three/examples/jsm/renderers/CSS2DRenderer
      - Labels show ticker symbol text
      - Only render labels for symbols within the camera frustum AND within distance threshold (performance)
      - Maximum ~50 visible labels at a time (nearest to camera)

   f. **Methods:**
      - `updateSymbolTiers(data)` — set positions and colors based on tier assignments
      - `setSelectedSymbol(symbol: string | null)` — highlight/unhighlight
      - `update(deltaTime: number)` — called in animation loop, handles tier transition animations
      - `dispose()` — clean up geometry, materials, CSS2D objects

2. **Modify `FunnelScene.ts`:**
   - Integrate FunnelSymbolManager: create in constructor, add to scene
   - Forward data updates to symbol manager
   - Include CSS2DRenderer for labels (initialize alongside WebGLRenderer)
   - Pass raycaster events from FunnelView

3. **Modify `FunnelView.tsx`:**
   - Connect to Observatory WS data (via hook or direct subscription)
   - Forward tier population data to FunnelScene → FunnelSymbolManager
   - Mouse event handlers → raycaster
   - Click handler → onSelectSymbol (propagate to ObservatoryPage state)
   - HTML tooltip overlay (positioned via mouse coordinates)

## Constraints
- Do NOT use sprite-based particles — use InstancedMesh for consistent performance
- Maximum 50 CSS2D labels rendered at once (performance guard)
- Tooltip is HTML overlay, not Three.js text — easier to style and position
- Do NOT modify the detail panel components

## Visual Review
1. Funnel now populated with symbol dots on each tier disc
2. Hover on a dot — tooltip shows ticker name
3. Click a dot — detail panel opens with that symbol
4. Zoom in — ticker labels appear near camera
5. **Performance check:** With 3,000+ particles, fps stays ≥ 30 (check DevTools Performance tab)
6. Watch for tier transitions when WS data updates (dots move between discs)

Verification: `npm run dev` with dev data populating tier assignments.

## Test Targets
- New tests (~3 Vitest):
  - `test_symbol_manager_creates_instanced_mesh` — InstancedMesh in scene
  - `test_symbol_manager_update_tiers_sets_positions` — positions change on data update
  - `test_symbol_manager_selected_symbol_highlight` — selected instance gets distinct color
- Minimum: 3
- Test command: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Definition of Done
- [ ] Symbol particles rendered on tier discs via InstancedMesh
- [ ] Hover tooltip with ticker name
- [ ] Click selects symbol → detail panel
- [ ] Tier transition animation (0.5s lerp between discs)
- [ ] LOD labels appear on zoom (max 50)
- [ ] 30+ fps with 3,000+ particles
- [ ] Selected symbol visually distinct
- [ ] All existing tests pass, 3+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-6b-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-6b-review.md`

## Session-Specific Review Focus (for @reviewer)
1. **CRITICAL:** Verify fps ≥ 30 with 3,000+ instances (escalation trigger if not)
2. Verify InstancedMesh used (not individual Mesh per symbol)
3. Verify CSS2D label count capped at 50
4. Verify proper disposal of all Three.js resources in dispose()
5. Verify raycaster only checks on mouse move, not every frame
6. Verify tier transition uses lerp in animation loop, not CSS/Framer animation

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`

**ESCALATION NOTE:** If fps < 30 with 3,000+ particles, this triggers escalation criterion #1. Do NOT proceed to S7 until resolved.
