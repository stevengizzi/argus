# Sprint 25, Session 7: Frontend — Radar View (Camera Animation)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/observatory/views/three/FunnelScene.ts` (S6a+S6b output)
   - `argus/ui/src/features/observatory/views/FunnelView.tsx` (S6a+S6b output)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (S3 — view key `4`)
   - `argus/ui/src/features/observatory/ObservatoryPage.tsx` (view switching logic)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the Radar view — which is the Funnel viewed from directly below, with the camera smoothly animating from its current position to a bottom-up perspective. The concentric tier rings get labeled and a center "TRIGGER" indicator appears. Switching back to Funnel animates the camera back. This is NOT a separate Three.js scene — it's a camera preset on the existing Funnel scene.

## Requirements

1. **Create `argus/ui/src/features/observatory/views/RadarView.tsx`:**
   - Thin wrapper that reuses FunnelView's Three.js scene but triggers a camera transition
   - When this view activates (key `4`), calls `FunnelScene.transitionToRadar()`
   - When leaving this view (switching to `1`), calls `FunnelScene.transitionToFunnel()`
   - Renders the same canvas as FunnelView — shared scene, different camera state
   - Implementation approach: RadarView and FunnelView could share the same underlying canvas ref, with the view switch triggering only camera animation. Alternatively, RadarView could be a FunnelView with a `mode` prop. Choose whichever is cleaner.

2. **Create `argus/ui/src/features/observatory/views/three/useCameraTransition.ts`:**
   - Hook or utility that smoothly interpolates camera position and orientation
   - Uses requestAnimationFrame-driven lerp (not CSS animation)
   - Duration: ~800ms with ease-out curve
   - Interpolates both camera.position and camera lookAt target
   - Must work with OrbitControls (temporarily disable during transition, re-enable after)

   Camera presets:
   - **Funnel preset:** position ~(0, 5, 10), looking at ~(0, 3, 0) — angled perspective
   - **Radar preset:** position ~(0, -2, 0), looking at ~(0, 3, 0) — directly below, looking up
   
   Note: "looking up from below" means the tier discs appear as concentric rings. The widest ring (Universe) is outermost, the smallest (Traded) is innermost = center.

3. **Modify `FunnelScene.ts`:**
   - Add radar-mode visual elements (only visible when camera is in radar position):
     a. **Concentric ring labels:** Text labels around each tier ring showing tier name + count. Use CSS2DObjects positioned at the outer edge of each disc. Fade in during transition to radar, fade out during transition to funnel.
     b. **Center "TRIGGER" label:** CSS2DObject at the center (y=0, origin point) showing "TRIGGER" in green. Only visible in radar mode.
     c. **Distance-from-center encoding:** In radar mode, particles' visual distance from center directly represents how close they are to triggering. Particles on the Traded tier are at center; Universe tier particles are at the outer edge. This is automatic from the disc layout — just verify it reads correctly from below.
   - Add methods: `transitionToRadar()`, `transitionToFunnel()` — called by view switch
   - Disable orbit controls during transition, re-enable after
   - In radar mode, orbit controls should be constrained: allow rotation around vertical axis only (no flipping back to funnel via drag — use key `1` for that)

4. **Modify `ObservatoryPage.tsx`:**
   - Register RadarView for view key `4`
   - Handle the shared-scene pattern: when switching between `1` (Funnel) and `4` (Radar), animate camera rather than mounting/unmounting components

## Constraints
- Do NOT create a second Three.js scene for radar — reuse the funnel scene
- Camera transition must not cause frame drops (lerp in animation loop, not requestAnimationFrame spam)
- OrbitControls must be disabled during transition (prevents user dragging mid-animation)
- Radar mode orbit should be constrained to vertical axis rotation only

## Visual Review
1. Press `4` — camera smoothly rotates to bottom-up view over ~800ms
2. Tier rings visible as concentric circles with labels
3. Center shows "TRIGGER" label in green
4. Symbols visible as dots at correct radial distances
5. Press `1` — camera smoothly returns to funnel perspective
6. In radar mode, drag rotates around vertical axis only (no flip to funnel)
7. Transition is smooth (no frame drops, no jumps)
8. Ring labels fade in during transition, fade out when leaving

Verification: `npm run dev`, navigate to Observatory, switch between Funnel and Radar.

## Test Targets
- New tests (~4 Vitest):
  - `test_radar_view_triggers_camera_transition`
  - `test_camera_transition_completes_in_time` — verify transition callback fires
  - `test_radar_labels_visibility` — labels visible in radar mode, hidden in funnel
  - `test_orbit_controls_constrained_in_radar` — vertical axis only
- Minimum: 4
- Test command: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Definition of Done
- [ ] Press `4` smoothly transitions camera to bottom-up (radar) perspective
- [ ] Press `1` smoothly transitions back to angled (funnel) perspective
- [ ] Concentric ring labels visible in radar mode
- [ ] Center TRIGGER label visible in radar mode
- [ ] Labels fade in/out during transitions
- [ ] Orbit constrained to vertical axis in radar mode
- [ ] No frame drops during transition
- [ ] All existing tests pass, 4+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-7-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-7-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify shared scene (no duplicate Three.js scene created)
2. Verify OrbitControls disabled during transition
3. Verify orbit constrained in radar mode
4. Verify CSS2DObject labels used (not Three.js TextGeometry)
5. Verify transition lerp runs in animation loop (not setTimeout chain)

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
