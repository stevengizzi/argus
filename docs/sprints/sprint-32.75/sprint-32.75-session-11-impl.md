# Sprint 32.75, Session 11: Arena Live Data

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/ui/src/features/arena/MiniChart.tsx` (imperative handle), `argus/api/websocket/arena_ws.py` (S7 — message types), `argus/ui/src/api/ws.ts` (existing WS client)
2. Scoped tests: `cd argus/ui && npx vitest run src/features/arena/`
3. Verify branch: `main`
4. S7, S10 merged

## Objective
Wire the Arena WebSocket to MiniChart instances for sub-second live candle formation, dynamic trailing stop updates, and live aggregate stats.

## Requirements
1. **Create `ui/src/features/arena/useArenaWebSocket.ts`**:
   - Connect to `/ws/v1/arena` using the existing WebSocketClient pattern
   - Maintain a map of `symbol → MiniChart ref` for dispatching updates
   - On `arena_tick`: call `chartRef.updateCandle()` to modify current candle's close/high/low. Update ArenaCard's P&L/R overlay. Update trailing stop line via `chartRef.updateTrailingStop(price)`.
   - On `arena_candle`: call `chartRef.appendCandle()` to lock the current candle and start a new one
   - On `arena_position_opened`: add new position to state (triggers new ArenaCard render)
   - On `arena_position_closed`: remove position from state (triggers card removal)
   - On `arena_stats`: update ArenaStatsBar values

2. **requestAnimationFrame batching**: Collect all tick updates that arrive within a frame into a batch. Apply all chart updates in a single rAF callback. This prevents 40 separate DOM repaints per second.

3. **Live candle formation in MiniChart**: The `updateCandle` method should:
   - If no forming candle exists for current minute, create one (open=high=low=close=price)
   - If forming candle exists, update close=price, high=max(high, price), low=min(low, price)
   - Call `candleSeries.update()` with the forming candle data (same timestamp)

4. **ArenaStatsBar live updates**: Wire `arena_stats` messages to update position count, total P&L, net R, entries/exits counters.

## Constraints
- Do NOT modify the Arena WS backend (S7)
- Do NOT add animations (S12)
- Chart update must use TradingView LC's `update()` method (not `setData()`)
- If rAF batching proves too complex within compaction budget, defer to S12 and use direct updates

## Review Carry-Forwards (from prior sessions)
1. **useMemo for targetPrices (S9 F2):** When building ArenaCard props from
   position data, stabilize `targetPrices` arrays with `useMemo` (or equivalent
   stable reference) before passing to MiniChart. Without this, every parent
   re-render creates a new array literal, triggering MiniChart's price-line
   useEffect to remove and recreate all lines — at 30-chart scale this is
   measurable. Apply the same treatment to any other array/object props passed
   to MiniChart from the parent.

2. **Strategy filter bug (S10 visual review):** The strategy filter in
   ArenaControls produces zero results for all selections. Root cause: the
   dropdown values (from `STRATEGY_DISPLAY` keys in `strategyConfig.ts`) don't
   match the `strategy_id` format returned by the Arena REST API. When wiring
   position state updates from WebSocket messages, ensure `strategy_id` values
   are consistent with whatever format the filter comparison uses. This fix
   belongs in S12f, but be aware of the format when handling
   `arena_position_opened` payloads — use the raw `strategy_id` from the
   backend, don't transform it.

## Test Targets
- useArenaWebSocket dispatches tick to correct chart ref
- Live candle formation: updateCandle creates/updates forming candle correctly
- appendCandle locks current candle and starts new
- Stats bar updates on arena_stats message
- Position add/remove on open/close messages
- Minimum: 5 tests
- Command: `cd argus/ui && npx vitest run src/features/arena/`

## Visual Review
1. Charts update sub-second — current candle body visibly moves with each tick
2. Trailing stop yellow line moves when position's trail tightens
3. P&L and R-multiple overlays update in real time
4. Stats bar updates every second
5. New positions appear as new cards; closed positions disappear

## Definition of Done
- [ ] WebSocket wired to all chart instances
- [ ] Live candle formation working
- [ ] Trailing stop updates dynamically
- [ ] Stats bar live
- [ ] Position add/remove functional
- [ ] Close-out: `docs/sprints/sprint-32.75/session-11-closeout.md`
- [ ] Tier 2 review via @reviewer
