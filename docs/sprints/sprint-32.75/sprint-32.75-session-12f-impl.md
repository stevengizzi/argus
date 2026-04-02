# Sprint 32.75, Session 12f: Visual Review Fixes + Cleanup

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`
2. Scoped tests: `cd argus/ui && npx vitest run` (full Vitest) + `python -m pytest tests/api/test_arena.py tests/api/test_orchestrator_extended.py tests/api/test_arena_ws.py -x -q`
3. Verify branch: `main`
4. S1–S12 merged

## Objective
Fix the strategy filter bug, reorder keyboard shortcuts to place Arena at position 4, and apply 5 mechanical cleanup fixes from review findings.

---

## Fix 1 (BUG): Strategy filter returns empty for all selections

**Symptom:** On the Arena page, selecting any specific strategy from the filter dropdown causes all position cards to disappear. "All" works correctly.

**Root cause:** The `filterPositions` function in `argus/ui/src/hooks/useArenaData.ts` does a direct `===` comparison between `p.strategy_id` (from the REST API / WS) and the `strategyFilter` value (from `ArenaControls.tsx` dropdown, which uses `Object.keys(STRATEGY_DISPLAY)` as option values).

**Diagnosis step:** Before fixing, add a temporary `console.log` in `ArenaPage.tsx` at the top of the component body to log the actual `strategy_id` values from positions:
```typescript
console.log('Arena positions strategy_ids:', positions.map(p => p.strategy_id));
console.log('STRATEGY_DISPLAY keys:', Object.keys(STRATEGY_DISPLAY));
```
Compare the two lists to identify the exact mismatch. Then remove the console.log and apply the appropriate fix.

**Likely fixes (pick the one that matches the diagnosis):**
- If the API returns IDs without `strat_` prefix but dropdown uses `strat_` prefix: normalize in `filterPositions` using the same logic as `getStrategyDisplay()` (try both with and without prefix).
- If the API returns IDs with `strat_` prefix and dropdown matches: the issue is elsewhere (possibly WS `buildPositionFromOpenedMsg` transforming the ID, or a React state timing issue).
- If the format matches perfectly in the log: the bug is a state/timing issue — check whether `positions` is being cleared during the filter state change (look for `wsConnectedRef` race conditions).

**Test:** Add at least 1 test to `useArenaData.test.tsx` that verifies `filterPositions` works with the actual format returned by the API (whatever the diagnosis reveals).

---

## Fix 2 (ENHANCEMENT): Keyboard shortcuts — Arena at position 4

**Current state:**
- `NAV_ROUTES` in `argus/ui/src/layouts/AppShell.tsx` has `/arena` at index 9 (unreachable via numeric key)
- A separate `if (e.key === 'a')` handler on line 94 navigates to `/arena`

**Required changes in `AppShell.tsx`:**

1. **Reorder `NAV_ROUTES`** to match the Sidebar order (Arena after Performance):
```typescript
const NAV_ROUTES = [
  '/',           // 1 = Dashboard
  '/trades',     // 2 = Trades
  '/performance',// 3 = Performance
  '/arena',      // 4 = The Arena
  '/orchestrator',// 5 = Orchestrator
  '/observatory',// 6 = Observatory
  '/patterns',   // 7 = Pattern Library
  '/debrief',    // 8 = The Debrief
  '/system',     // 9 = System
  '/experiments',// 0 = Experiments
];
```

2. **Remove the `if (e.key === 'a')` block** (lines 94–96).

3. **Update the numeric key handler** to support key `0` mapping to index 9:
```typescript
const keyNum = parseInt(e.key, 10);
if (!isNaN(keyNum) && keyNum >= 0 && keyNum <= 9) {
  const routeIndex = keyNum === 0 ? 9 : keyNum - 1;
  if (routeIndex < NAV_ROUTES.length) {
    navigate(NAV_ROUTES[routeIndex]);
  }
  return;
}
```

**Test:** Update any existing AppShell keyboard shortcut tests. If none exist, add 2 tests:
- Key `4` navigates to `/arena`
- Key `0` navigates to `/experiments`

---

## Fix 3 (CLEANUP): Add `timestamp` to `ArenaCandlesResponse`

**File:** `argus/api/routes/arena.py`

Per Sprint 14 API convention, all responses include a `timestamp` field. `ArenaPositionsResponse` has it; `ArenaCandlesResponse` does not.

- Add `timestamp: str` to the `ArenaCandlesResponse` model (line ~72)
- Add `timestamp=datetime.now(UTC).isoformat()` to both return statements (the early return on line 185 and the normal return on line 201)

**Test:** Update `tests/api/test_arena.py` — assert `"timestamp"` key exists in candles response JSON.

---

## Fix 4 (CLEANUP): Type annotation in `orchestrator.py`

**File:** `argus/api/routes/orchestrator.py`, line 250

Change:
```python
trades_by_strategy: dict[str, list] = {}
```
To:
```python
trades_by_strategy: dict[str, list[Trade]] = {}
```

Add `Trade` to the imports from `argus.analytics.trade_logger` (or wherever `Trade` is imported in that file — check existing imports).

No test changes needed.

---

## Fix 5 (CLEANUP): Simplify redundant `except` in `arena_ws.py`

**File:** `argus/api/websocket/arena_ws.py`

Line 269: Change `except (JWTError, Exception):` → `except Exception:`
Line 384: Change `except (WebSocketDisconnect, Exception):` → `except Exception:`

`Exception` subsumes both `JWTError` and `WebSocketDisconnect`, making the tuples redundant.

No test changes needed (behavior is identical).

---

## Fix 6 (CLEANUP): `netR === 0` should show neutral color

**File:** `argus/ui/src/features/arena/ArenaStatsBar.tsx`

Line 52: Change `const rPositive = netR >= 0;` to:
```typescript
const rPositive = netR > 0;
const rNeutral = netR === 0;
```

Line 53: Change `const rClass = rPositive ? 'text-argus-profit' : 'text-argus-loss';` to:
```typescript
const rClass = rNeutral ? 'text-argus-text-dim' : rPositive ? 'text-argus-profit' : 'text-argus-loss';
```

Line 56: Change `const rSign = rPositive ? '+' : '';` to:
```typescript
const rSign = rNeutral ? '' : rPositive ? '+' : '';
```

**Test:** Update ArenaStatsBar tests — add a test that `netR={0}` renders with `text-argus-text-dim` class and no sign prefix.

---

## Fix 7 (CLEANUP): Import ArenaCard from barrel

**File:** `argus/ui/src/pages/ArenaPage.tsx`

Change:
```typescript
import { ArenaCard } from '../features/arena/ArenaCard';
```
To:
```typescript
import { ArenaCard } from '../features/arena';
```

Verify the barrel export in `argus/ui/src/features/arena/index.ts` includes `ArenaCard`. No test changes needed.

---

## Constraints
- Do NOT modify strategy detection logic, Risk Manager, Order Manager, Event Bus
- Do NOT modify MiniChart.tsx or useArenaWebSocket.ts (except if Fix 1 diagnosis requires it)
- Do NOT modify arena_ws.py message schemas (only the except clauses in Fix 5)
- All fixes are surgical — minimal diff per fix

## Test Targets
- Strategy filter works for at least 2 different strategies (manual verification + unit test)
- Key `4` → Arena, Key `0` → Experiments
- Candles endpoint returns `timestamp` field
- ArenaStatsBar `netR=0` renders neutral
- Minimum: 5 new/updated tests
- Commands:
  - `cd argus/ui && npx vitest run`
  - `python -m pytest tests/api/test_arena.py tests/api/test_arena_ws.py tests/api/test_orchestrator_extended.py -x -q`

## Definition of Done
- [ ] Strategy filter works correctly
- [ ] Keyboard shortcuts reordered (Arena=4, Experiments=0)
- [ ] 5 cleanup fixes applied
- [ ] Close-out: `docs/sprints/sprint-32.75/session-12f-closeout.md`
- [ ] Tier 2 review via @reviewer
