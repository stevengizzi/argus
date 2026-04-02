# Sprint 32.8: Arena Latency + UI Polish Sweep

## Goal
Fix Arena chart latency by bypassing the 1-second Order Manager throttle with a direct TickEvent subscription, add pre-market candle context, and polish the Arena/Dashboard/Trades pages for daily operational use as the primary monitoring interface.

## Scope

### Deliverables
1. **Arena real-time chart updates via direct TickEvent subscription** — charts update at Databento trade stream rate, not 1 Hz
2. **Pre-market candle data on Arena charts** — IntradayCandleStore accepts bars from 4:00 AM ET onward
3. **Arena UI polish** — no card borders, entry triangle markers, auto-zoom to entry, label cleanup, progress bar label, filtered stats
4. **Dashboard layout refactor** — 4-row no-scroll layout with vitals strip, 70/30 positions+timeline, consolidated secondary cards
5. **Trades page visual unification** — both tabs share Shadow Trades density + styling, `l`/`s` hotkeys
6. **Trades page feature additions** — Outcome toggle on Shadow, time presets, infinite scroll, sortable columns, Reason tooltip

### Acceptance Criteria
1. Arena TickEvent subscription:
   - Arena WS subscribes to TickEvent, filtered to symbols with open managed positions
   - Forming candle updates at actual tick rate (not throttled to 1 Hz)
   - PositionUpdatedEvent subscription retained for P&L/R-multiple overlay only
   - No measurable CPU regression on backend
2. Pre-market candles:
   - IntradayCandleStore accepts CandleEvents with timestamps >= 4:00 AM ET
   - `GET /api/v1/arena/candles/{symbol}` returns pre-market bars when available
   - Arena charts show pre-market context before 9:30 AM bars
3. Arena UI polish:
   - ArenaCard has no colored border (strategy identified by badge only)
   - Entry candle has upward triangle marker at entry timestamp
   - Chart auto-zooms to entry point with ~5 bars before and post-entry action visible
   - Only Stop and T1 have `axisLabelVisible: true` (Entry and Trail use line only)
   - Progress bar has "Stop ← → T1" label or tooltip
   - ArenaStatsBar shows filtered totals when strategy filter is active
4. Dashboard layout:
   - Row 1: VitalsStrip with Equity, Daily P&L, Today's Stats, VIX/Regime
   - Row 2: Strategy allocation bar
   - Row 3: Positions table (70%) + Session Timeline / Signal Quality stacked (30%)
   - Row 4: AI Insight (50%) + Learning Loop (50%) with matched height
   - All/Open/Closed toggle positioned left, next to "POSITIONS" header
   - Monthly Goal and Universe cards removed from Dashboard
   - No scroll required to see Rows 1–3 on 1080p display
5. Trades visual unification:
   - Both tabs have identical row height, background colors, and text styling
   - Shadow tab uses Live tab's darker, higher-contrast look
   - `l` hotkey switches to Live Trades tab, `s` to Shadow Trades tab
6. Trades feature additions:
   - Outcome toggle (All/Wins/Losses/BE) on Shadow Trades, filtering by theo P&L sign
   - Today/Week/Month/All time presets on Shadow Trades
   - Infinite scroll replacing pagination on Shadow Trades
   - Sortable columns on Shadow Trades
   - Reason column: wider min-width + tooltip showing full text on hover

### Performance Benchmarks
| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Arena chart update rate | ≥5 updates/sec for active symbols | Visual observation during market hours |
| Dashboard initial render | No scroll to see Rows 1–3 | Visual check on 1080p display |
| Shadow Trades infinite scroll | Smooth scrolling through 10K+ rows | Visual observation with 14K+ shadow trades |

### Config Changes
No config changes in this sprint.

## Dependencies
- Sprint 32.75 complete (test baseline: ~4,530 pytest + ~805 Vitest)
- ARGUS running on port 8000 with live market data
- Vite dev server for hot-reload visual review

## Relevant Decisions
- DEC-368: IntradayCandleStore architecture (being extended for pre-market)
- DEC-342: Strategy evaluation telemetry (Arena WS builds on this event pattern)
- DEC-104/215: Chart library choices (Lightweight Charts used in Arena)
- DEC-199: Navigation + keyboard shortcuts (extending with `l`/`s`)

## Relevant Risks
- RSK-018: Frontend complexity growth (mitigated by consolidation, not addition)

## Session Count Estimate
5 implementation sessions + 1 contingency visual fix session. S1/S2/S3/S4 run in parallel; S5 sequential after S4. Frontend sessions have visual review via live Vite dev server throughout.
