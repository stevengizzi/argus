# Sprint 32.8 Work Journal Handoff

## Sprint Goal
Fix Arena chart latency (bypass 1s Order Manager throttle via direct TickEvent subscription), add pre-market candle context, and polish Arena/Dashboard/Trades UI for daily operational use.

## Session Breakdown

| Session | Scope | Creates | Modifies | Score | Parallel |
|---------|-------|---------|----------|-------|----------|
| S1 | Arena Pipeline Backend — TickEvent subscription + pre-market candles | — | `arena_ws.py`, `intraday_candle_store.py`, `useArenaWebSocket.ts` | 13 | Yes (S1∥S2∥S3∥S4) |
| S2 | Dashboard Layout Refactor — VitalsStrip, 70/30 layout, secondary cards | `VitalsStrip.tsx` | `DashboardPage.tsx` | 12.5 | Yes |
| S3 | Arena UI Polish — no borders, entry markers, auto-zoom, labels, filtered stats | — | `ArenaCard.tsx`, `MiniChart.tsx`, `ArenaPage.tsx`, `ArenaStatsBar.tsx` | 11 | Yes |
| S4 | Trades Visual Unification — match Shadow density, hotkeys | — | `TradesPage.tsx`, `ShadowTradesTab.tsx`, `TradeTable.tsx`, `TradeStatsBar.tsx` | 10 | Yes |
| S5 | Trades Feature Additions — Outcome toggle, time presets, infinite scroll, sort, tooltip | `SharedTradeFilters.tsx` (optional) | `ShadowTradesTab.tsx`, `TradeFilters.tsx`, `useShadowTrades.ts` | 13 | No (after S4) |
| S6f | Visual Review Contingency | — | Per findings | ≤8 | After S2–S5 |

## Session Dependency Chain
```
S1 ──┐
S2 ──┤── Round 1 (parallel)
S3 ──┤
S4 ──┘
      └── S5 (after S4) ── S6f (contingency)
```

## Do Not Modify
- Any Python files except `arena_ws.py` and `intraday_candle_store.py`
- `argus/core/events.py`
- `argus/execution/order_manager.py`
- Any strategy files
- Any config YAML files
- Any database schemas

## Issue Category Definitions
- **BLOCKER**: Prevents session completion. Halt and escalate.
- **CONCERN**: Quality/correctness issue. Fix in-session if possible, log if not.
- **OBSERVATION**: Minor item. Log for future sprint.
- **QUESTION**: Clarification needed. Check spec first, escalate if ambiguous.

## Escalation Triggers
- Any modification to trading engine code (strategies, risk, order management)
- Any change to event definitions
- Any API contract change
- Test baseline regression beyond known DEF-137/DEF-138

## Reserved Numbers
- No new DEC numbers reserved (no architectural decisions anticipated)
- DEF-139: Startup zombie flatten queue not draining (logged, NOT in scope)
- DEF-140: EOD flatten state/broker disconnect (logged, NOT in scope)
- DEF-141+: Available for this sprint if needed

## Test Baseline
- pytest: ~4,530 (DEF-137 may fail — pre-existing)
- Vitest: ~805 (DEF-138 may fail — pre-existing)

## Development Mode
Human-in-the-loop with Vite dev server for live visual review.
Run `cd argus/ui && npm run dev` for hot-reload on port 5175.
ARGUS running on port 8000 for live data.
