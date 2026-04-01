# Sprint 32.75, Session 10: Arena Card Integration

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/ui/src/pages/ArenaPage.tsx` (S8), `argus/ui/src/features/arena/ArenaCard.tsx` (S9), `argus/api/routes/arena.py` (S6 — check response schema)
2. Scoped tests: `cd argus/ui && npx vitest run src/features/arena/ src/hooks/useArenaData*`
3. Branch: `sprint-32.75-session-10`
4. S6, S8, S9 merged

## Objective
Wire ArenaCard and MiniChart with real position/candle data from the Arena REST API.

## Requirements
1. **Create `ui/src/hooks/useArenaData.ts`**:
   - TanStack Query: fetch `/api/v1/arena/positions` on mount and every 5 seconds (positions list)
   - For each position, fetch `/api/v1/arena/candles/{symbol}?minutes=30` (candle history)
   - Cache candles per symbol — don't refetch if already loaded
   - Return: `{ positions, candlesBySymbol, isLoading, error, stats }`

2. **Wire ArenaPage**: Replace placeholder grid with actual ArenaCard instances from useArenaData. Map each position to an ArenaCard with its candle data.

3. **Sort logic**: Implement all 4 sort modes:
   - Entry time (default): newest first by `entry_time`
   - Strategy: group by `strategy_id`, then by entry time within group
   - P&L: highest unrealized P&L first
   - Urgency: sort by min(distance-to-stop, distance-to-T1) / entry-to-T1 range — nearest to any exit level first

4. **Filter logic**: Strategy filter dropdown filters the positions array. "All" shows everything.

## Constraints
- Do NOT wire WebSocket data yet (S11)
- Do NOT add animations yet (S12)
- Charts will show static candle history (will become live in S11)
- Do NOT modify the REST API endpoints

## Test Targets
- useArenaData fetches positions and candles
- Sort by each of 4 modes produces correct order
- Strategy filter narrows positions
- Grid renders correct number of cards
- Minimum: 5 tests
- Command: `cd argus/ui && npx vitest run src/hooks/useArenaData* src/features/arena/`

## Visual Review
1. Arena page shows one card per open position with real market data
2. Charts display candle history with price level lines
3. Sort modes reorder cards correctly
4. Strategy filter works — selecting one strategy shows only those positions

## Definition of Done
- [ ] Positions fetched and rendered as ArenaCards
- [ ] Candle history displayed in each MiniChart
- [ ] Sort and filter functional
- [ ] Close-out: `docs/sprints/sprint-32.75/session-10-closeout.md`
- [ ] Tier 2 review via @reviewer
