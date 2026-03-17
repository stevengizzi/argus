# Sprint 25, Session 6a: Frontend — Three.js Funnel Scene Setup

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md` (Funnel view requirements + performance benchmarks)
   - `argus/ui/src/features/observatory/ObservatoryPage.tsx` (S3 — view registration)
   - `argus/ui/package.json` (confirm three.js version in dependencies)
   - Any existing Three.js usage in codebase (search for `three` imports)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (S3 — camera shortcuts)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the Three.js 3D scene for the Funnel view: camera, lighting, 7 translucent tier discs arranged as a cone/funnel, orbit controls, and keyboard-driven camera reset/fit. This is the scene foundation — symbol particles are added in S6b.

## Requirements

1. **Create `argus/ui/src/features/observatory/views/FunnelView.tsx`:**
   - React component wrapping a Three.js canvas
   - Lazy-loaded via `React.lazy()` — Three.js bundle must NOT be in the main chunk
   - Uses `useRef` for the container div, initializes Three.js scene in `useEffect`
   - Disposes all Three.js resources on unmount (renderer, scene, geometry, materials)
   - Responsive: re-renders on container resize (ResizeObserver)
   - Exposes camera ref for S7's radar animation
   - requestAnimationFrame loop for continuous rendering (orbit controls need it)

2. **Create `argus/ui/src/features/observatory/views/three/FunnelScene.ts`:**
   - Pure Three.js class (no React dependency) that sets up:

   a. **Camera:** PerspectiveCamera, positioned at a 30–40° angle looking down at the funnel. Default position: approximately (0, 5, 10) looking at origin.

   b. **Lighting:** Ambient light (soft, 0.6 intensity) + one directional light from above-right. Subtle — the translucent discs should glow softly, not cast harsh shadows.

   c. **7 Tier discs:** Circular disc geometries (CircleGeometry or RingGeometry) arranged vertically as an inverted cone (widest at top, narrowest at bottom):
      - Tier 0 (Universe): y=6, radius=5 — largest
      - Tier 1 (Viable): y=5, radius=4.2
      - Tier 2 (Routed): y=4, radius=3.4
      - Tier 3 (Evaluating): y=3, radius=2.6
      - Tier 4 (Near-trigger): y=2, radius=1.8
      - Tier 5 (Signal): y=1, radius=1.0
      - Tier 6 (Traded): y=0, radius=0.4 — smallest, at the tip
      Exact positions/radii can be tuned — the key is a clear funnel shape.
      
      Materials: MeshBasicMaterial or MeshStandardMaterial with `transparent: true`, `opacity: 0.15–0.25`, `side: DoubleSide`. Each tier a slightly different color from the design palette:
      - Universe/Viable: cool gray-blue
      - Routed: amber tint
      - Evaluating: purple tint
      - Near-trigger: warm amber
      - Signal/Traded: green
      
      Each disc has a thin edge ring (wireframe or LineLoop) for visibility.

   d. **Connecting lines:** Faint lines connecting the edges of adjacent discs to form the funnel wireframe shape. Very subtle — opacity 0.1–0.15.

   e. **Orbit controls:** OrbitControls from three/examples/jsm/controls/OrbitControls.
      - Enable rotate (drag), zoom (scroll), pan (right-drag or shift-drag)
      - Damping enabled for smooth feel
      - Min/max zoom to prevent going inside or too far out

   f. **Camera presets:**
      - `resetCamera()`: Animate camera back to default perspective position
      - `fitView()`: Adjust camera to fit entire funnel in view
      - These are called by keyboard shortcuts `R` and `F` via callbacks

   g. **Tier highlight:** Method `highlightTier(tierIndex: number)` that increases the opacity of the selected tier disc and dims others. Called when tier selector changes.

   h. **Background:** Transparent (inherits page background). No skybox, no environment map.

3. **Modify `ObservatoryPage.tsx`:**
   - Register FunnelView as the component for view key `1` (via React.lazy)
   - Pass tier selector state to FunnelView for tier highlighting

4. **Wire keyboard shortcuts:**
   - `R` key → calls `FunnelScene.resetCamera()`
   - `F` key → calls `FunnelScene.fitView()`
   - These should only fire when Funnel or Radar view is active

## Constraints
- Do NOT install additional Three.js addon packages — use only what's in three.js core + examples/jsm
- Do NOT add post-processing effects (bloom, SSAO, etc.) — clean flat rendering
- Keep material complexity low — no PBR materials, no environment maps
- Ensure code-splitting: the dynamic `import('three')` or `React.lazy` must keep Three.js out of the main bundle

## Visual Review
1. Press `1` to see Funnel view — 3D funnel renders with translucent discs
2. Drag to orbit — smooth rotation with damping
3. Scroll to zoom — respects min/max bounds
4. Press `R` — camera animates to default position
5. Press `F` — camera adjusts to fit funnel
6. Select different tier in tier selector — selected disc brightens, others dim
7. Verify Three.js is in a separate chunk: `npm run build`, check output chunk sizes

Verification: `npm run dev`, navigate to Observatory, switch to Funnel view.

## Test Targets
- New tests (~3 Vitest):
  - `test_funnel_view_lazy_loaded` — verify React.lazy wrapper
  - `test_funnel_scene_creates_7_tier_discs` — scene has 7 disc meshes
  - `test_funnel_scene_highlight_tier` — highlightTier changes opacity
- Minimum: 3 (Three.js rendering is hard to unit test — focus on data/structure)
- Test command: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Definition of Done
- [ ] 3D funnel renders with 7 translucent tier discs in cone arrangement
- [ ] Orbit controls: rotate, zoom, pan with damping
- [ ] Camera reset (R) and fit (F) working
- [ ] Tier highlighting on selection
- [ ] Code-split: Three.js in separate lazy chunk
- [ ] Proper disposal on unmount
- [ ] Responsive to container resize
- [ ] All existing tests pass, 3+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-6a-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-6a-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify React.lazy code-splitting (Three.js not in main bundle)
2. Verify proper disposal of all Three.js resources on unmount (renderer, scene, geometries, materials)
3. Verify ResizeObserver cleanup
4. Verify requestAnimationFrame loop is cancelled on unmount
5. Verify OrbitControls imported from examples/jsm (not a separate package)
6. Verify no post-processing or PBR materials

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
