# Session 6a Tier 2 Review

**Sprint:** 25 — The Observatory
**Session:** 6a — Three.js Funnel Scene Setup
**Reviewer:** Claude (Tier 2 automated)
**Date:** 2026-03-17

---BEGIN-REVIEW---

## Verdict: PASS_WITH_NOTES

The implementation is solid and well-structured. All tests pass (46 observatory, 569 full suite), TypeScript has only pre-existing errors (2 in ObservatoryLayout.tsx, not introduced here), and the code follows project conventions. Minor notes documented below.

## Review Focus Checklist

### 1. React.lazy code-splitting (Three.js not in main bundle)
**PASS.** `ObservatoryPage.tsx` uses `React.lazy()` with dynamic `import('./views/FunnelView')` and wraps the result in `<Suspense>`. The `.then((m) => ({ default: m.FunnelView }))` pattern correctly adapts the named export for React.lazy's default-export requirement. Three.js is only imported inside `FunnelView.tsx` and `FunnelScene.ts`, which are in the lazy chunk.

### 2. Proper disposal of all Three.js resources on unmount
**PASS.** `FunnelScene.dispose()` covers:
- `cancelAnimationFrame` for the RAF loop
- `controls.dispose()` for OrbitControls
- All geometries via `this.geometries` array (disc geometries, edge geometries, connecting line geometries)
- All materials via `this.materials` array (disc materials, edge materials, connecting line material)
- `scene.clear()` and `renderer.dispose()`
- DOM element removal from parent
- Guard via `this.disposed` flag prevents double-dispose

`FunnelView.tsx` cleanup effect calls `funnelScene.dispose()` and nulls the ref. Complete.

### 3. ResizeObserver cleanup
**PASS.** `FunnelView.tsx` creates a `ResizeObserver` in the setup effect and calls `resizeObserver.disconnect()` in the cleanup function. Correct pattern.

### 4. requestAnimationFrame loop cancelled on unmount
**PASS.** `FunnelScene.dispose()` calls `cancelAnimationFrame(this.animationId)` and sets it to null. The `animate` method also checks `this.disposed` at the top as a safety guard.

### 5. OrbitControls imported from examples/jsm (not a separate package)
**PASS.** `FunnelScene.ts` line 11: `import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';`. No additional Three.js addon packages in package.json.

### 6. No post-processing or PBR materials
**PASS.** Materials are `MeshStandardMaterial` with `roughness: 0.8, metalness: 0.1` — this is basic standard material usage, well below PBR complexity (no environment maps, no normal maps, no HDR). `LineBasicMaterial` for edges and connecting lines. No bloom, SSAO, or any post-processing imports.

## Definition of Done Checklist

| Item | Status | Notes |
|------|--------|-------|
| 3D funnel renders with 7 translucent tier discs in cone arrangement | DONE | 7 tiers with decreasing radius (5.0 to 0.4), vertical positions y=6 to y=0, transparent materials with opacity 0.2 |
| Orbit controls: rotate, zoom, pan with damping | DONE | damping=0.08, minDistance=3, maxDistance=30 |
| Camera reset (R) and fit (F) working | DONE | Changed to Shift+R / Shift+F (documented judgment call — bare R/F conflict with view-switch keys) |
| Tier highlighting on selection | DONE | highlightTier() sets 0.45 for selected, 0.1 for others, 0.2 for reset |
| Code-split: Three.js in separate lazy chunk | DONE | React.lazy + Suspense with fallback |
| Proper disposal on unmount | DONE | All geometries, materials, renderer, controls, RAF, DOM element |
| Responsive to container resize | DONE | ResizeObserver with proper cleanup |
| All existing tests pass, 3+ new tests | DONE | 4 new tests (569 total, 46 observatory) |
| Close-out report written | DONE | `docs/sprints/sprint-25/session-6a-closeout.md` |
| Tier 2 review written | This document | |

## Code Quality Observations

1. **Shift+R/Shift+F instead of R/F (judgment call):** This is a reasonable deviation. Bare `r` and `f` are already bound to radar and funnel view switching. The close-out documents this clearly. The keyboard handler logic correctly handles this: `hasModifier` blocks meta/ctrl/alt but not shift, so shift-modified keys pass through, and uppercase `'R'`/`'F'` (produced by shift) won't match the lowercase view-switch keys in VIEW_KEYS. Clean implementation.

2. **MeshStandardMaterial choice:** The spec allowed either MeshBasicMaterial or MeshStandardMaterial. The choice of MeshStandardMaterial with low roughness/metalness is fine and within spec bounds. It does mean the directional light actually affects disc appearance (MeshBasicMaterial ignores lights), which arguably makes the lighting setup more justified.

3. **Connecting line material sharing:** All 12 connecting lines share a single `LineBasicMaterial` instance. This is efficient — only one material to dispose. The geometries are correctly tracked individually in the `geometries` array.

4. **Minor: `type-only` import for FunnelViewHandle.** `ObservatoryPage.tsx` uses `import type { FunnelViewHandle }` which is correct — the type is only used for the ref generic parameter and will be erased at compile time, avoiding pulling FunnelView into the main chunk.

5. **No test for camera reset/fit keyboard shortcuts.** The Shift+R and Shift+F keyboard handlers are not covered by any test. The ObservatoryPage tests mock FunnelView entirely. This is a minor gap — the keyboard hook is tested for other shortcuts in the existing test file, but the new camera callbacks are not exercised.

## Test Coverage Assessment

- **4 new tests** in FunnelView.test.tsx covering: tier disc count (7), highlight tier, dispose idempotency, and FunnelView named export shape.
- Tests appropriately mock Three.js classes since jsdom lacks WebGL. The mock classes are minimal but sufficient to verify structural behavior.
- The `highlightTier` test verifies the method runs without error but does not assert on actual opacity values of the mock materials. This is acceptable given the mock limitations, but a slightly stronger test could verify the material opacity property.
- **Missing:** No test for Shift+R/Shift+F keyboard shortcuts calling camera callbacks. Low risk since the wiring is straightforward optional-chaining delegation.

## Final Notes

Clean session. The code is well-organized with clear separation between the pure Three.js scene class (FunnelScene.ts) and the React wrapper (FunnelView.tsx). Resource management is thorough with tracked arrays for geometries and materials, a disposed flag, and proper cleanup in both the scene class and the React effect. The Shift+R/Shift+F deviation is pragmatic and well-documented.

Note: The session's changes are present in the working tree but not yet committed. This does not affect the review — the code, tests, and close-out report are all complete and consistent.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CONCERNS",
  "confidence": 0.92,
  "session": "S6a",
  "sprint": 25,
  "findings": [
    {
      "severity": "low",
      "category": "spec-deviation",
      "description": "Camera reset/fit keybindings changed from R/F to Shift+R/Shift+F due to conflict with view-switch keys. Well-documented judgment call, technically correct resolution.",
      "recommendation": "Accepted as-is. Update any user-facing documentation or shortcut overlay to reflect Shift+R/Shift+F."
    },
    {
      "severity": "low",
      "category": "test-coverage",
      "description": "No test coverage for Shift+R/Shift+F keyboard shortcuts invoking camera callbacks. The ObservatoryPage tests mock FunnelView entirely.",
      "recommendation": "Consider adding a test in ObservatoryPage.test.tsx that fires Shift+R/Shift+F and verifies the mock FunnelView ref callbacks are invoked."
    },
    {
      "severity": "low",
      "category": "test-quality",
      "description": "highlightTier test verifies no error but does not assert on opacity values of mock materials.",
      "recommendation": "Optional improvement: verify material.opacity after highlightTier calls."
    },
    {
      "severity": "info",
      "category": "process",
      "description": "Session changes are in working tree but not committed. Close-out report exists as untracked file.",
      "recommendation": "Commit session work before proceeding to next session."
    }
  ],
  "escalation_triggers": [],
  "tests_pass": true,
  "test_count": {
    "observatory": 46,
    "full_frontend": 569,
    "new_tests": 4
  },
  "typescript_errors": {
    "new": 0,
    "pre_existing": 2
  }
}
```
