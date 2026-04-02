---BEGIN-REVIEW---

# Sprint 32.75, Session 11 — Tier 2 Review

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-01
**Scope:** Arena Live Data (useArenaWebSocket hook, ArenaCard/ArenaPage modifications)
**Diff:** Uncommitted changes against commit 0535d89

---

## 1. Test Results

| Suite | Result |
|-------|--------|
| Arena tests (3 files, 40 tests) | 40/40 PASS |
| Full Vitest suite (111 files) | 798/798 PASS |

No regressions detected.

---

## 2. Spec Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| `useArenaWebSocket` hook connecting to `/ws/v1/arena` | PASS | Connects, sends auth, handles auth_success |
| All 5 WS message types handled | PASS | arena_tick, arena_candle, arena_position_opened, arena_position_closed, arena_stats |
| rAF batching present | PASS | Boolean `rafScheduledRef` guard, `flushRaf` callback, `cancelAnimationFrame` on cleanup |
| Live candle formation (open/high/low/close accumulation) | PASS | Minute-boundary bucketing, correct max/min logic |
| Stats bar wired (entries_5m / exits_5m) | PASS | ArenaStatsBar receives entries5m/exits5m from WS stats |
| Position add/remove functional | PASS | arena_position_opened adds (with dedup), arena_position_closed removes + cleans overlay |
| `registerChartRef` wired via `onChartMount` | PASS | ArenaCard useEffect calls onChartMount with handle on mount, null on unmount |
| S9 carry-forward: targetPrices useMemo | PASS | `useMemo` with `join(',')` key stabilizes reference |
| `wsConnectedRef` guard prevents REST clobbering WS state | PASS | Set true on auth_success, false on close; initialPositions sync gated |

---

## 3. Scope Verification

Only Arena feature files and ArenaPage were modified. No backend files, Risk Manager, Order Manager, Event Bus, or other invariant systems were touched. The only non-Arena file changed is the sprint spec itself (docs update). PASS.

---

## 4. Findings

### F2-1: `makeOnChartMount` is not actually stable across renders (SHOULD-FIX, severity: F2)

**File:** `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/pages/ArenaPage.tsx`, line 41-46 and line 104.

The `makeOnChartMount` factory is wrapped in `useCallback`, but calling `makeOnChartMount(pos.symbol)` during render (line 104) creates a **new closure** every render. The `useCallback` memoizes the factory function, not its return values. This means `onChartMount` is a new reference on every ArenaPage render, causing ArenaCard's registration `useEffect` (line 85-89) to re-fire each render cycle: cleanup (null) then re-register (handle).

The operations are cheap (Map set/delete), and React's synchronous batching makes the window negligible. No functional breakage will occur. However, this does not achieve the stated design goal (close-out judgment call #3). At 30-chart scale with frequent WS ticks, ArenaPage re-renders frequently, and each re-render triggers 30 effect cleanup+re-register cycles unnecessarily.

**Recommended fix:** Use a `useRef<Map<string, (handle: MiniChartHandle | null) => void>>` to cache per-symbol callbacks, or pass `registerChartRef` directly and have ArenaCard call it with the symbol prop.

### F3-1: `liveOverlays` keyed by symbol only -- multi-strategy same-symbol overlap (MINOR, severity: F3)

**File:** `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/features/arena/useArenaWebSocket.ts`, lines 180-189, 229, 274.

`liveOverlays` uses `symbol` as the map key. Under the ALLOW_ALL cross-strategy policy (DEC-121/160), two strategies can hold the same symbol. The backend `arena_tick` message also lacks `strategy_id`, so the frontend has no way to disambiguate. The last tick for a symbol wins, and both ArenaCards for that symbol would display the same P&L/R overlay.

This is a design limitation inherited from the backend message schema (which the spec says not to modify). Documenting for awareness. Not blocking.

### F3-2: `arena_position_closed` overlay cleanup by symbol deletes overlay for other strategies (MINOR, severity: F3)

**File:** `/Users/stevengizzi/Documents/Coding Projects/argus/argus/ui/src/features/arena/useArenaWebSocket.ts`, lines 274-276.

When a position closes, `liveOverlays` is cleaned up by symbol only (`delete next[symbol]`), but positions are filtered by both `symbol` AND `strategy_id`. If two strategies held the same symbol and one closes, the overlay for the remaining strategy's position is deleted. The remaining position's card would fall back to the REST data values until the next tick arrives.

Same root cause as F3-1 (symbol-only keying). Not blocking.

### F3-3: Close-out reports 798 Vitest tests; baseline was 711 (COSMETIC, severity: F3)

The close-out notes "+87 net" increase from 711 to 798 Vitest tests. The prior session (S10) close-out also reported test additions. The 798 count is the current verified state. No issue per se, just noting the substantial accumulation across S8-S11 Arena sessions.

---

## 5. Regression Checklist (Spot Checks)

- [x] No files outside Arena feature scope modified
- [x] Arena WS backend (arena_ws.py) NOT modified
- [x] All 798 Vitest tests pass
- [x] MiniChart imperative handle contract (updateCandle, appendCandle, updateTrailingStop) used correctly
- [x] No `any` types in new code
- [x] No direct broker/risk/order manager interaction from frontend

---

## 6. Escalation Criteria Check

| Criterion | Triggered? |
|-----------|-----------|
| Arena 30-chart >200ms/frame | Not measurable in automated review (no browser perf trace) |
| LC `update()` API inadequate | No -- used correctly via imperative handle |
| Arena WS degrades main trading pipeline | No -- backend not modified, separate WS channel |
| Post-reconnect delay causes corruption | Not applicable to this session |
| Systemic trade-to-strategy attribution gap | Not applicable |

No escalation criteria triggered.

---

## 7. Verdict

**CONCERNS**

The implementation is functionally complete and correct for single-strategy-per-symbol scenarios. All 5 WS message types are handled, rAF batching works, live candle formation logic is correct, and all tests pass with zero regressions. The S9 carry-forward (targetPrices stabilization) was applied as specified.

One F2 finding (makeOnChartMount instability) represents a performance concern at scale that does not match the stated design intent but causes no functional breakage. Two F3 findings (multi-strategy same-symbol overlay keying) are architectural limitations inherited from the backend message schema and not fixable without backend changes.

---END-REVIEW---

```json:structured-verdict
{
  "session": "sprint-32.75-session-11",
  "verdict": "CONCERNS",
  "findings": [
    {
      "id": "F2-1",
      "severity": "F2",
      "category": "performance",
      "summary": "makeOnChartMount factory creates new closure per render — does not achieve stated stability goal",
      "file": "argus/ui/src/pages/ArenaPage.tsx",
      "lines": "41-46, 104"
    },
    {
      "id": "F3-1",
      "severity": "F3",
      "category": "correctness",
      "summary": "liveOverlays keyed by symbol only — multi-strategy same-symbol positions show same overlay",
      "file": "argus/ui/src/features/arena/useArenaWebSocket.ts",
      "lines": "180-189, 229"
    },
    {
      "id": "F3-2",
      "severity": "F3",
      "category": "correctness",
      "summary": "arena_position_closed overlay cleanup by symbol deletes overlay for other strategies on same symbol",
      "file": "argus/ui/src/features/arena/useArenaWebSocket.ts",
      "lines": "274-276"
    },
    {
      "id": "F3-3",
      "severity": "F3",
      "category": "cosmetic",
      "summary": "Close-out test count jump from 711 to 798 is cumulative across S8-S11, not session-only"
    }
  ],
  "tests_pass": true,
  "test_count": {
    "arena": 40,
    "vitest_total": 798
  },
  "scope_violation": false,
  "escalation_triggered": false
}
```
