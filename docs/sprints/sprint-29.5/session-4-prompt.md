# Sprint 29.5, Session 4: Real-Time Position Updates via WebSocket

## Pre-Flight Checks
1. Read: `argus/ui/src/hooks/usePositions.ts`, `argus/ui/src/features/dashboard/OpenPositions.tsx`, `argus/api/websocket/live.py` (search for `PositionUpdatedEvent` and `position.updated`), `argus/core/events.py` (PositionUpdatedEvent fields)
2. Run scoped baseline: `cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -20`
3. Verify branch: `sprint-29.5`

## Objective
Make the Dashboard Open Positions table update P&L/R in near-real-time by consuming WebSocket `position.updated` events, with REST polling as a consistency backstop.

## Requirements

1. **New hook** `argus/ui/src/hooks/usePositionUpdates.ts`:
   - Subscribe to the existing WS connection (check how other hooks like the Observatory or AI chat subscribe — likely via a shared WS context or Zustand store)
   - Listen for `position.updated` messages on the WS channel
   - On each message, extract: `symbol`, `unrealized_pnl`, `r_multiple`, `current_price`
   - Merge into the `usePositions` query cache via `queryClient.setQueryData(['positions', ...], updater)` — update matching position's live fields without triggering a full refetch
   - Handle WS disconnection gracefully: fall back to REST polling (already active)

2. **Wire into OpenPositions** in `argus/ui/src/features/dashboard/OpenPositions.tsx`:
   - Import and call `usePositionUpdates()` — it's a side-effect hook that updates the query cache
   - The existing `usePositions()` data will automatically reflect WS updates via cache

3. **Reduce REST polling** in `argus/ui/src/hooks/usePositions.ts`:
   - Change `refetchInterval` from `5_000` to `15_000` — REST is now a consistency backstop, not the primary update path

4. **Verify WS message format**: Check `argus/api/websocket/live.py` to confirm the serialization format of `PositionUpdatedEvent`. The hook must parse the correct field names. If the WS sends the event as a JSON envelope like `{"type": "position.updated", "data": {...}}`, match that structure.

## Constraints
- Do NOT modify the WS bridge backend (`argus/api/websocket/live.py`) — frontend only
- Do NOT modify `PositionUpdatedEvent` in `argus/core/events.py`
- Do NOT remove REST polling entirely — it's the fallback
- Do NOT update closed-position transitions via WS — let REST handle open→closed list changes

## Test Targets
- New Vitest tests:
  1. `test_position_updates_hook_merges_cache` — mock WS message, verify query cache updated
  2. `test_position_updates_handles_unknown_symbol` — WS update for symbol not in positions list, ignored
  3. `test_rest_polling_still_active` — verify usePositions still has refetchInterval set
- Minimum: 3 new Vitest tests
- Test command: `cd argus/ui && npx vitest run`

## Visual Review
The developer should visually verify:
1. **Dashboard Open Positions P&L column**: Values update within 1-2 seconds of price change (vs previous 5s)
2. **No flickering**: Position rows don't flash or re-render entire table on each WS update
3. **WS disconnect recovery**: If WS drops (close browser DevTools Network tab WS), positions still update via REST at 15s interval

Verification conditions: Argus running in paper mode with open positions during market hours

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Positions still load on page load (REST) | Refresh Dashboard, positions appear |
| Closed positions still move to Recent Trades | Close a position, verify it appears in trades table |
| Other WS consumers unaffected | Observatory WS, AI chat still work |

## Definition of Done
- [ ] All requirements implemented
- [ ] All existing tests pass
- [ ] 3+ new Vitest tests
- [ ] Visual review verified
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-4-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-4-closeout.md`

## Tier 2 Review
Test command: `cd argus/ui && npx vitest run`
Files NOT modified: `argus/api/`, `argus/core/`, `argus/execution/`

## Session-Specific Review Focus
1. Verify WS hook properly handles reconnection/disconnection
2. Verify cache update is additive (merge), not destructive (replace)
3. Verify no race condition between WS update and REST refetch
