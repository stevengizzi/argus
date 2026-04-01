# Sprint 29.5 Session 4 — Tier 2 Review

---BEGIN-REVIEW---

## Review Summary

**Session objective:** Make Dashboard Open Positions table update P&L/R in near-real-time via WebSocket `position.updated` events, with REST polling as a consistency backstop.

**Reviewer verdict:** CLEAR

## Spec Compliance

All four requirements satisfied:

| Requirement | Status | Evidence |
|-------------|--------|----------|
| R1: New `usePositionUpdates` hook | PASS | `argus/ui/src/hooks/usePositionUpdates.ts` created, subscribes to WS `position.updated`, merges into query cache |
| R2: Wired into `OpenPositions.tsx` | PASS | `usePositionUpdates()` called at top of `OpenPositions` component |
| R3: REST polling reduced 5s to 15s | PASS | `refetchInterval` changed from `5_000` to `15_000` in `usePositions.ts` |
| R4: WS message format verified | PASS | `PositionUpdatePayload` interface matches backend `PositionUpdatedEvent` fields; `r_multiple` correctly mapped to `r_multiple_current` |

## Constraint Verification

| Constraint | Status |
|------------|--------|
| No backend modifications | PASS — `git diff HEAD` shows zero changes in `argus/api/`, `argus/core/`, `argus/execution/` |
| REST polling retained | PASS — `refetchInterval: 15_000` still active |
| No closed-position transitions via WS | PASS — hook filters strictly for `type === 'position.updated'` |

## Review Focus Items

### F1: WS reconnection/disconnection handling
The hook subscribes via `getWebSocketClient().onMessage()`. On WS disconnect, the WebSocketClient automatically attempts reconnection with exponential backoff (up to 10 attempts). The hook's message handler remains registered in the `messageHandlers` Set across reconnections since the singleton client persists. On unmount, the cleanup function removes the handler. This is correct — the hook is passive and the reconnection logic lives in the WS client layer where it belongs.

### F2: Cache update is additive (merge), not destructive (replace)
Confirmed. The updater function in `setQueriesData` spreads `...old` at the response level and `...pos` at the position level, then overwrites only `current_price`, `unrealized_pnl`, and `r_multiple_current`. All other position fields (entry_price, stop_price, shares, t1/t2, etc.) are preserved.

### F3: Race condition between WS update and REST refetch
No race condition. Both `setQueriesData` (WS path) and the REST refetch write to the same React Query cache. React Query batches state updates within the same render cycle. If REST delivers slightly stale data, the next WS event (sub-second cadence in live) overwrites it. The worst case is a brief display of stale REST data until the next WS tick, which is acceptable.

### F4: No backend files modified
Confirmed via `git diff HEAD`. The `M argus/api/routes/trades.py` in git status is a staged change with no actual diff against HEAD — likely from a previous session.

### F5: Test quality and coverage
5 tests covering the key behaviors:
1. **Cache merge** — seeds cache, fires WS event, asserts 3 updated fields + 2 preserved fields
2. **Unknown symbol ignored** — fires WS for symbol not in cache, asserts no change
3. **Non-matching type ignored** — fires `position.opened` event, asserts no change
4. **Unmount unsubscribe** — verifies cleanup function called
5. **15s interval** — renders `usePositions`, inspects query cache options

Test quality is adequate. The tests use proper React Testing Library patterns (`renderHook`, `act`), properly mock the WS client, and verify both positive and negative cases.

## Findings

No findings. The implementation is clean, minimal, and correctly scoped.

## Test Results

- **Vitest:** 103 files, 700 tests passed (baseline: 102 files, 695 tests)
- **Delta:** +1 file, +5 tests — matches close-out report exactly

## Close-Out Report Accuracy

The close-out report is accurate in all respects: change manifest matches the actual diff, test counts match, constraints verified, self-assessment of CLEAN is justified.

---END-REVIEW---

```json:structured-verdict
{
  "verdict": "CLEAR",
  "findings": [],
  "test_results": {
    "vitest_files": 103,
    "vitest_tests": 700,
    "vitest_pass": true,
    "delta_files": 1,
    "delta_tests": 5
  },
  "spec_compliance": "FULL",
  "constraint_violations": [],
  "escalation_triggers": []
}
```
