# Sprint 32.75, Session 12 — Tier 2 Review

---BEGIN-REVIEW---

## Review Summary

Session 12 adds entry/exit animations via Framer Motion AnimatePresence, attention-weighted priority sizing with 2-second recomputation, a WebSocket disconnection overlay, and an `'a'` keyboard shortcut for the Arena page. The implementation is clean, focused, and matches the spec precisely.

## Findings

### F1: AnimatePresence wrapping — PASS

AnimatePresence wraps the grid item list correctly at `ArenaPage.tsx:167`. Mode is `popLayout` which removes exiting items from layout flow immediately, allowing smooth grid reflow. Keys use the stable composite `${strategy_id}-${symbol}-${entry_time}` pattern (line 172), which is unique per-position and stable across renders.

### F2: Priority recomputation interval — PASS

The `setInterval(recomputeSpans, 2000)` at line 106 runs every 2 seconds as specified. The `useEffect` has an empty dependency array and reads mutable state via refs (`positionsRef`, `liveOverlaysRef`, `candlesBySymbolRef`), which is the correct pattern to avoid stale closures without causing interval re-registration on every state change.

### F3: Mobile single-column — PASS

The `window.innerWidth < 640` guard at line 84 forces `span 1` for all positions on mobile, correctly preventing priority-based `span 2` from breaking the single-column mobile layout.

### F4: Exit flash correctness — PASS

The flash overlay is a nested `motion.div` (lines 190-201) with `initial={{ opacity: 0 }}`, `animate={{ opacity: 0 }}` (invisible at rest), and `exit={{ opacity: [0, 0.15, 0] }}` with keyframe times `[0, 0.375, 1]` over 0.8s duration. The flash peaks at ~300ms (0.375 * 800ms = 300ms) then fades. The `pnlPositive` flag at line 171 is computed from `overlay?.unrealized_pnl ?? pos.unrealized_pnl`, which correctly uses the latest WS overlay when available. AnimatePresence preserves the last-rendered element during exit, so the color computed at the final render before removal is correct.

The outer `motion.div` exit has `delay: 0.3` and `duration: 0.5`, meaning the card stays visible for 300ms (flash window) then fades over 500ms. This aligns with the spec's "flash for 300ms then fade out."

### F5: wsStatus tracking — PASS

`WsStatus` type is `'connecting' | 'connected' | 'disconnected' | 'error'` (useArenaWebSocket.ts:37). Initial state is `'connecting'` (line 103). Transitions: `auth_success` -> `'connected'` (line 229), `onerror` -> `'error'` (line 304-305), `onclose` -> `'disconnected'` (line 309-310). The lifecycle is correct and complete.

### F6: Keyboard shortcut placement — PASS

In AppShell.tsx, the `'a'` shortcut (lines 93-97) is placed after the modifier check (line 88-91, `if (hasModifier) return`) and before the numeric shortcuts (line 100). This means `'a'` is ignored when any modifier key is held, which is correct behavior.

### F7: Tests — PASS

13 new tests in `arenaAnimations.test.tsx`:
- 9 tests for `computePriorityScore` correctness (near stop, near T1, at entry, degenerate ranges, clamping, span threshold mapping)
- 3 tests for disconnection overlay (connected hides it, disconnected shows it, error shows it)
- 1 test for AnimatePresence wrapper (renders `arena-card-wrapper` motion divs)

This exceeds the minimum of 3 tests and covers the three required areas.

### F8: Existing test compatibility — PASS

The `useArenaWebSocket.test.ts` test at line 312 ("clears live overlay on arena_position_closed") continues to pass. The hook diff only adds the `wsStatus` state variable and its transitions -- the `liveOverlays` clear logic in `arena_position_closed` handler is unchanged. All 11 existing useArenaWebSocket tests pass.

### F9: Constraints — PASS

- MiniChart.tsx: zero diff, confirmed unmodified.
- rAF tick dispatch in useArenaWebSocket: zero diff on `flushRaf`, `scheduleRaf`, `requestAnimationFrame`, or `cancelAnimationFrame` references.
- Chart rendering and data flow are untouched.

### F10: Minor observation (non-blocking)

The `layout` boolean prop on `motion.div` produces a React console warning in tests: "Received `true` for a non-boolean attribute `layout`." This is a known Framer Motion + testing-library interaction (Framer Motion uses `layout` as a special prop that doesn't map to a DOM attribute). It does not affect functionality or production behavior -- it only appears in test stderr. No action required.

## Test Results

Arena test suite: **53 tests passing** (4 files), 0 failures. Delta: +13 tests from session 12.

| Suite | Count | Status |
|-------|-------|--------|
| MiniChart.test.tsx | 10 | PASS |
| useArenaWebSocket.test.ts | 11 | PASS |
| ArenaCard.test.tsx | 19 | PASS |
| arenaAnimations.test.tsx | 13 | PASS |

## Regression Checklist (Session-Relevant Items)

- [x] Existing arena tests pass (53/53)
- [x] MiniChart.tsx unmodified
- [x] rAF tick dispatch unmodified
- [x] liveOverlays clear on position_closed preserved
- [x] No new files outside declared manifest
- [x] No backend changes

## Escalation Criteria Check

None triggered. No performance concerns (priority recomputation is 2s interval, not per-frame). No WS interference (only added state tracking, no message protocol changes). No chart rendering modifications.

## Verdict

All 9 review focus items pass. Implementation matches spec precisely. Tests are thorough. No regressions detected.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "confidence": 0.97,
  "findings_count": {
    "pass": 9,
    "concern": 0,
    "escalation": 0
  },
  "tests": {
    "arena_suite": "53 passed, 0 failed",
    "new_tests": 13,
    "existing_tests_preserved": true
  },
  "files_reviewed": [
    "argus/ui/src/pages/ArenaPage.tsx",
    "argus/ui/src/features/arena/useArenaWebSocket.ts",
    "argus/ui/src/layouts/AppShell.tsx",
    "argus/ui/src/features/arena/arenaAnimations.test.tsx"
  ],
  "constraints_verified": [
    "MiniChart.tsx unmodified",
    "rAF tick dispatch unmodified",
    "liveOverlays clear preserved",
    "Priority recompute at 2s interval not per-frame",
    "Mobile span override functional"
  ],
  "session_self_assessment_agreement": true,
  "recommendation": "APPROVED"
}
```
