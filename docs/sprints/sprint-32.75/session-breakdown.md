# Sprint 32.75: Session Breakdown

## Parallelization Map

```
Wave 1 (parallel):  S1 ──┐   S5 ──┐   S6 ──┐   S9 ──┐
                          │        │        │        │
Wave 2 (parallel):  S2 ──┤  S3 ──┤  S4 ──┤  S7 ──┤  S8 ──┐
                     │    │   │   │   │   │        │       │
                     └────┴───┴───┴───┘   │        │       │
Wave 3:                   S10 ◄───────────┴────────┴───────┘
                           │
Wave 4:                   S11 ◄── S7
                           │
Wave 5:                   S12 → S12f
```

Dependency arrows:
- S2, S3, S4 depend on S1 (strategy identity constants)
- S8 depends on S1 (nav colors)
- S10 depends on S6 (REST API) + S8 (page shell) + S9 (MiniChart component)
- S11 depends on S7 (WebSocket) + S10 (card integration)
- S12 depends on S11

---

## Session 1: Strategy Identity System
**Objective:** Add 5 new PatternModule strategies to all identity maps. Every strategy gets unique color, badge, display name.

**New strategy identity:**

| Strategy | Display Name | Badge | Letter | Color | Tailwind |
|----------|-------------|-------|--------|-------|----------|
| strat_dip_and_rip | Dip-and-Rip | DIP | D | #fb7185 | rose-400 |
| strat_hod_break | HOD Break | HOD | H | #34d399 | emerald-400 |
| strat_gap_and_go | Gap-and-Go | GAP | G | #38bdf8 | sky-400 |
| strat_abcd | ABCD | ABCD | X | #f472b6 | pink-400 |
| strat_premarket_high_break | PM High Break | PMH | P | #a3e635 | lime-400 |

**Creates:** None
**Modifies:** `ui/src/utils/strategyConfig.ts`, `ui/src/components/Badge.tsx`, `ui/src/components/AllocationDonut.tsx`, `ui/src/features/dashboard/SessionTimeline.tsx`
**Integrates:** N/A (foundation session)
**Parallelizable:** true (zero overlap with S5, S6, S9)

| Factor | Count | Points |
|--------|-------|--------|
| New files created | 0 | 0 |
| Files modified | 4 | 4 |
| Context reads | 2 | 2 |
| Tests to update | 8 | 4 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large files | — | 0 |
| **Total** | | **10 (Medium)** |

---

## Session 2: Dashboard Overhaul
**Objective:** Remove low-value cards, reposition remaining cards, redesign VIX card, fix inline toggle.

**Changes:**
- Remove `<RecentTrades />` and `<HealthMini />` from all 3 responsive layouts in DashboardPage.tsx
- Swap Signal Quality into the 3-card row with Today's Stats and Session Timeline; move AI Insight to where Signal Quality was
- Move All/Open/Closed toggle into Positions card header row (OpenPositions.tsx)
- Redesign VixRegimeCard: condense to compact single-row showing VIX close, VRP tier, vol phase, momentum direction — or add sparkline + 5-day history to justify the space

**Creates:** None
**Modifies:** `ui/src/pages/DashboardPage.tsx` (3 layouts), `ui/src/features/dashboard/VixRegimeCard.tsx`, `ui/src/features/dashboard/OpenPositions.tsx`, `ui/src/features/dashboard/index.ts`
**Integrates:** S1 (strategy colors now visible in timeline, donut)
**Parallelizable:** true within Wave 2 (different page from S3, S4)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0 | 0 |
| Files modified | 5 | 5 |
| Context reads | 3 | 3 |
| Tests | 5 | 2.5 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large files | — | 0 |
| **Total** | | **10.5 (Medium)** |

---

## Session 3: Orchestrator Page Fixes
**Objective:** Fix P&L/trades display, capital allocation legend, catalyst links.

**P&L fix approach:** Modify `argus/api/routes/orchestrator.py` to query `trade_logger.get_trades()` filtered by today's ET date and aggregate per-strategy P&L + count, replacing the broken `getattr(strategy, '_trade_count_today', 0)` / `getattr(strategy, '_daily_pnl', 0.0)` pattern.

**Other fixes:**
- Capital Allocation legend: ensure `getStrategyDisplayName()` uses centralized identity (may already work after S1 — verify)
- Catalyst headlines: add `<a href={url} target="_blank" rel="noopener noreferrer">` wrapper around headline text in CatalystAlertPanel

**Creates:** None
**Modifies:** `argus/api/routes/orchestrator.py`, `ui/src/features/orchestrator/StrategyOperationsCard.tsx` (legend), CatalystAlertPanel component (~4 files)
**Integrates:** S1 (auto-propagated via getStrategyDisplay)
**Parallelizable:** true within Wave 2 (Orchestrator page, no overlap with S2/S4)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0 | 0 |
| Files modified | 4 | 4 |
| Context reads | 4 | 4 |
| Tests | 5 | 2.5 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large files | — | 0 |
| **Total** | | **10.5 (Medium)** |

---

## Session 4: Bug Fixes + AI Context
**Objective:** Fix duplicate price labels, enhance AI Insight portfolio context.

**TradeChart fix:** In the `useEffect` that creates price lines (line 213), track created lines in a `useRef<ISeriesApi<'Candlestick'>['createPriceLine'][]>()`, call `candleSeries.removePriceLine()` for each tracked line at the start of the effect, then create new lines and track them.

**AI context fix:** In `argus/ai/system_context.py` (SystemContextBuilder), expand position data injection from top-5 to all open positions. Include summary stats (total count, total P&L, strategy distribution) plus individual position details for up to 30 positions.

**Creates:** None
**Modifies:** `ui/src/components/TradeChart.tsx`, `argus/ai/system_context.py`
**Integrates:** N/A
**Parallelizable:** true within Wave 2 (no file overlap with S2/S3)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0 | 0 |
| Files modified | 2 | 2 |
| Context reads | 3 | 3 |
| Tests | 4 | 2 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large files | — | 0 |
| **Total** | | **7 (Low)** |

---

## Session 5: Operational Fixes + IBC Guide
**Objective:** Raise overflow capacity, improve reconnect resilience, add operational logging, create IBC documentation.

**Changes:**
- `config/overflow.yaml`: `broker_capacity: 60`
- `argus/execution/ibkr_broker.py`: After successful reconnection in `_reconnect()`, add `await asyncio.sleep(3)` before first portfolio query, then verify position count is reasonable (>0 if `_managed_positions` is non-empty)
- `argus/strategies/base_strategy.py`: Add `_log_window_summary()` called from operating window close logic — logs count of symbols evaluated, signals generated, rejections by category
- Stop retry analysis: examine April 1 logs for pattern (same symbols repeatedly, specific order types, timing), document findings in close-out
- `docs/ibc-setup.md`: Complete guide covering IBC install, config, credentials, launchd, verification
- `scripts/ibc/com.argus.ibgateway.plist`: Template launchd plist

**Creates:** `docs/ibc-setup.md`, `scripts/ibc/com.argus.ibgateway.plist`
**Modifies:** `config/overflow.yaml`, `argus/execution/ibkr_broker.py`, `argus/strategies/base_strategy.py`
**Integrates:** N/A
**Parallelizable:** true (zero overlap with S1, S6, S9)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 2 | 4 |
| Files modified | 3 | 3 |
| Context reads | 4 | 4 |
| Tests | 5 | 2.5 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large files | — | 0 |
| **Total** | | **13.5 (Medium)** |

---

## Session 6: Arena REST API
**Objective:** Backend endpoints for Arena initial data load.

**Endpoints:**
- `GET /api/v1/arena/positions` — Returns all open managed positions with: symbol, strategy_id, side, entry_price, current_price, stop_price, target_prices[], trailing_stop_price, unrealized_pnl, r_multiple, hold_duration_seconds, shares, quality_grade. JWT-protected.
- `GET /api/v1/arena/candles/{symbol}?minutes=30` — Returns last N minutes of 1-min OHLC bars from IntradayCandleStore. JWT-protected.

**Creates:** `argus/api/routes/arena.py`
**Modifies:** `argus/api/routes/__init__.py` (import + router registration)
**Integrates:** N/A (consumed by S10)
**Parallelizable:** true (zero overlap with S1, S5, S9)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads | 4 | 4 |
| Tests | 8 | 4 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large file | — | 0 |
| **Total** | | **11 (Medium)** |

---

## Session 7: Arena WebSocket
**Objective:** Real-time streaming channel for Arena live updates.

**Channel:** `/ws/v1/arena` (JWT-authenticated, same pattern as observatory_ws.py)

**Message types:**
- `arena_position_opened`: symbol, strategy_id, entry_price, stop_price, target_prices, side, shares
- `arena_position_closed`: symbol, strategy_id, exit_price, pnl, r_multiple, exit_reason
- `arena_tick`: symbol, price, unrealized_pnl, r_multiple, trailing_stop_price
- `arena_candle`: symbol, timestamp, open, high, low, close, volume (completed 1-min candle)
- `arena_stats`: position_count, total_pnl, net_r, entries_5m, exits_5m (every 1 second)

**Implementation:** Subscribe to PositionUpdatedEvent (tick data), CandleEvent (completed candles), and position open/close events from event bus. Filter CandleEvents to only symbols with open positions. Aggregate stats computation on 1-second timer.

**Creates:** `argus/api/websocket/arena_ws.py`
**Modifies:** `argus/api/server.py` (WS route registration)
**Integrates:** N/A (consumed by S11)
**Parallelizable:** true within Wave 2 (backend WS, no overlap with S2/S3/S4/S8)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Files modified | 1 | 1 |
| Context reads | 4 | 4 |
| Tests | 8 | 4 |
| Integration wiring | +3 (event bus subscriptions) | 3 |
| External API | — | 0 |
| Large file | — | 0 |
| **Total** | | **14 (High — tight but manageable, established WS pattern)** |

---

## Session 8: Arena Page Shell
**Objective:** Create page structure, nav registration, grid layout, stats bar, controls.

**Components:**
- `ArenaPage.tsx` — page component with CSS grid, stats bar, controls bar, grid container
- `ArenaStatsBar.tsx` — aggregate stats display (position count, P&L, R, entry/exit rate)
- `ArenaControls.tsx` — sort mode selector + strategy filter dropdown
- Empty state when no positions
- Nav registration in App.tsx router + sidebar

**Creates:** `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaStatsBar.tsx`, `ui/src/features/arena/ArenaControls.tsx`, `ui/src/features/arena/index.ts`
**Modifies:** `ui/src/App.tsx`, sidebar/nav component (~2 files)
**Integrates:** S1 (strategy colors for filter dropdown, nav icon)
**Parallelizable:** true within Wave 2 (new files only, no overlap with S2/S3/S4/S7)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 4 | 8 |
| Files modified | 2 | 2 |
| Context reads | 2 | 2 |
| Tests | 4 | 2 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large file | — | 0 |
| **Total** | | **14 (High — tight, but files are small components)** |

---

## Session 9: MiniChart Component
**Objective:** Standalone TradingView Lightweight Charts wrapper for Arena cards.

**Components:**
- `MiniChart.tsx` — wraps TradingView LC createChart() + addCandlestickSeries(). Props: candle data, entry/stop/T1/trailing prices, chart dimensions. Manages chart lifecycle in useEffect with proper cleanup. Price level lines via createPriceLine() with tracked refs (same fix pattern as S4).
- `ArenaCard.tsx` — card frame wrapping MiniChart. Displays: strategy badge (top-left), P&L + R-multiple (top-right, color-coded), hold duration timer (bottom-left), stop-to-T1 progress bar (bottom).

**Creates:** `ui/src/features/arena/MiniChart.tsx`, `ui/src/features/arena/ArenaCard.tsx`
**Modifies:** None (standalone components)
**Integrates:** S1 (strategy colors for badge/progress bar)
**Parallelizable:** true (zero overlap with all Wave 1 sessions — creates new files only)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 2 | 4 |
| Files modified | 0 | 0 |
| Context reads | 3 | 3 |
| Tests | 6 | 3 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large file | 1 (MiniChart) | 2 |
| **Total** | | **12 (Medium)** |

---

## Session 10: Arena Card Integration
**Objective:** Wire MiniChart/ArenaCard with real data from REST API, implement sort and filter.

**Components:**
- `useArenaData.ts` — TanStack Query hook fetching from `/api/v1/arena/positions` and `/api/v1/arena/candles/{symbol}` per position. Manages candle data cache per symbol.
- Wire ArenaPage grid to render ArenaCard per position from useArenaData
- Sort logic: entry_time (default), strategy, pnl, urgency (computed from proximity to stop or target relative to entry)
- Filter: strategy dropdown filters positions array

**Creates:** `ui/src/hooks/useArenaData.ts`
**Modifies:** `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaCard.tsx`
**Integrates:** S6 (REST API) + S8 (page shell) + S9 (MiniChart component)
**Parallelizable:** false (depends on S6, S8, S9)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Files modified | 2 | 2 |
| Context reads | 4 | 4 |
| Tests | 5 | 2.5 |
| Integration wiring | +3 | 3 |
| External API | — | 0 |
| Large file | — | 0 |
| **Total** | | **13.5 (Medium)** |

---

## Session 11: Arena Live Data
**Objective:** Wire WebSocket for sub-second chart updates, live candle formation, trailing stop.

**Implementation:**
- `useArenaWebSocket.ts` — connects to `/ws/v1/arena`, dispatches tick/candle/stats messages to appropriate handlers
- On `arena_tick`: update current candle's close, high, low on the MiniChart's candlestick series via `update()`. Update trailing stop price line. Update P&L/R overlay.
- On `arena_candle`: append completed candle to series data, start new forming candle
- On `arena_stats`: update ArenaStatsBar
- On `arena_position_opened` / `arena_position_closed`: add/remove cards from grid
- `requestAnimationFrame` batching: collect all tick updates per frame, apply in single batch

**Creates:** `ui/src/features/arena/useArenaWebSocket.ts`
**Modifies:** `ui/src/features/arena/MiniChart.tsx` (imperative update methods), `ui/src/pages/ArenaPage.tsx` (WS integration), `ui/src/features/arena/ArenaStatsBar.tsx` (live stats)
**Integrates:** S7 (WebSocket channel) + S10 (card integration)
**Parallelizable:** false (depends on S7, S10)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 1 | 2 |
| Files modified | 3 | 3 |
| Context reads | 4 | 4 |
| Tests | 5 | 2.5 |
| Integration wiring | +3 | 3 |
| External API (WS) | +3 | 3 |
| Large file | — | 0 |
| **Total** | | **17.5 (High — complex but all established patterns)** |

> ⚠️ S11 scores 17.5 (High). Justified by: all WS patterns are established from Observatory, all chart APIs are from S9, the session is pure integration with no new abstractions. If compaction occurs, the `requestAnimationFrame` batching and stats bar can be deferred to S12.

---

## Session 12: Arena Animations + Polish
**Objective:** Entry/exit animations, attention-weighted priority sizing, grid reflow.

**Implementation:**
- Framer Motion `AnimatePresence` wrapping the grid items. New cards: `initial={{ opacity: 0, scale: 0.9 }}` → `animate={{ opacity: 1, scale: 1 }}`. Exiting cards: `exit={{ opacity: 0 }}` with brief green/red background tint flash.
- Priority sizing: compute priority score per card (0-1) based on proximity to stop/target + R velocity + recency. Map to CSS grid `fr` units (e.g., priority 1.0 → 1.3fr, priority 0.0 → 1.0fr). Recompute every 2 seconds. Smooth transitions via CSS `transition: all 500ms ease`.
- Disconnection indicator: overlay "Connection lost" when WS disconnected.

**Creates:** None
**Modifies:** `ui/src/pages/ArenaPage.tsx`, `ui/src/features/arena/ArenaCard.tsx`
**Integrates:** S11
**Parallelizable:** false (depends on S11)

| Factor | Count | Points |
|--------|-------|--------|
| New files | 0 | 0 |
| Files modified | 2 | 2 |
| Context reads | 2 | 2 |
| Tests | 3 | 1.5 |
| Integration wiring | — | 0 |
| External API | — | 0 |
| Large file | — | 0 |
| **Total** | | **5.5 (Low)** |

---

## Session 12f: Visual Review Fixes
**Objective:** Fix any visual issues discovered during S8-S12 reviews. Contingency, 0.5 session.

---

## Summary Table

| Session | Scope | Score | Wave | Parallel? |
|---------|-------|-------|------|-----------|
| S1 | Strategy Identity | 10 | 1 | ✅ |
| S5 | Operational Fixes + IBC | 13.5 | 1 | ✅ |
| S6 | Arena REST API | 11 | 1 | ✅ |
| S9 | MiniChart Component | 12 | 1 | ✅ |
| S2 | Dashboard Overhaul | 10.5 | 2 | ✅ |
| S3 | Orchestrator Fixes | 10.5 | 2 | ✅ |
| S4 | Bug Fixes + AI | 7 | 2 | ✅ |
| S7 | Arena WebSocket | 14 | 2 | ✅ |
| S8 | Arena Page Shell | 14 | 2 | ✅ |
| S10 | Arena Card Integration | 13.5 | 3 | ❌ |
| S11 | Arena Live Data | 17.5 | 4 | ❌ |
| S12 | Arena Animations | 5.5 | 5 | ❌ |
| S12f | Visual Review Fixes | — | 5 | ❌ |

**DEC range reserved:** 382–395 (14 slots)
**DEF range reserved:** 135–139
