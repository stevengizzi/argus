# Sprint 25, Session 4b: Frontend — Candlestick Chart + Data Hooks

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/observatory/detail/SymbolDetailPanel.tsx` (S4a output)
   - Existing Lightweight Charts usage in codebase (search for `createChart` or `lightweight-charts`)
   - `argus/api/routes/observatory.py` (S1 — endpoint shapes for data hooks)
   - `argus/api/websocket/observatory_ws.py` (S2 — WS message shapes)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the live-updating candlestick chart component using Lightweight Charts and the TanStack Query data hooks that feed the detail panel with real-time symbol data.

## Requirements

1. **Create `argus/ui/src/features/observatory/detail/SymbolCandlestickChart.tsx`:**
   - Wrapper around Lightweight Charts `createChart()` with candlestick series
   - Props: `symbol: string`, `height?: number` (default 200px)
   - Data source: 1-minute candle bars from existing data API or Databento feed
   - Chart updates when new candles arrive (via the data hook's polling/WS)
   - Chart reinitializes when symbol changes (dispose old chart, create new)
   - Responsive width (fills panel width minus padding)
   - Clean up chart instance on unmount (dispose)
   - Minimal chrome: time axis, price axis, crosshair on hover. No toolbar, no drawing tools.
   - Dark mode support: chart background transparent, text/grid colors from CSS variables

2. **Create `argus/ui/src/features/observatory/hooks/useSymbolDetail.ts`:**
   - TanStack Query hook that fetches and combines data for the detail panel:
     a. Symbol journey: `GET /api/v1/observatory/symbol/{symbol}/journey?date={date}` — polling every 5s in live mode
     b. Quality score: `GET /api/v1/quality/{symbol}` — polling every 30s
     c. Catalysts: `GET /api/v1/catalysts/{symbol}` — polling every 60s
     d. Candle data: from appropriate existing endpoint or new endpoint if needed
   - Returns combined object: `{ journey, quality, catalysts, candles, isLoading, error }`
   - Queries keyed on symbol — automatic refetch when symbol changes
   - Queries disabled when symbol is null
   - In debrief mode (date prop provided), disable polling, fetch once

3. **Modify `SymbolDetailPanel.tsx`:**
   - Replace placeholder sections with data from `useSymbolDetail`
   - Wire SymbolCandlestickChart into the chart slot
   - Wire real quality score, catalyst data, and market data into their sections
   - Show loading skeletons while data fetches
   - Show "No data" messages for sections with no data

## Constraints
- Do NOT modify Lightweight Charts library or any shared chart utilities
- Do NOT create new backend endpoints for candle data — use existing data infrastructure if possible. If no existing endpoint serves 1-minute candles for a specific symbol, create a minimal proxy endpoint in observatory routes that reads from EvaluationEventStore metadata or Databento candle cache.
- Chart must not conflict with Three.js WebGL context (Lightweight Charts uses 2D canvas, not WebGL)

## Visual Review
1. Select a symbol — candlestick chart renders with candle data
2. Chart updates as new candles arrive (in dev mode, may need mock data)
3. Chart reinitializes cleanly when switching symbols (no ghost data)
4. Quality score badge renders correctly
5. Loading skeletons shown during fetch
6. Panel is fully functional with all sections populated

Verification: `npm run dev`, navigate to Observatory, select symbols.

## Test Targets
- New tests (~5 Vitest):
  - `test_candlestick_chart_renders_with_data`
  - `test_candlestick_chart_disposes_on_unmount`
  - `test_use_symbol_detail_fetches_on_symbol_change`
  - `test_use_symbol_detail_disabled_when_no_symbol`
  - `test_use_symbol_detail_stops_polling_in_debrief`
- Minimum: 5
- Test command: `cd argus/ui && npx vitest run src/features/observatory/`

## Definition of Done
- [ ] Candlestick chart renders with candle data
- [ ] Chart updates live, reinitializes on symbol change, disposes on unmount
- [ ] useSymbolDetail hook fetches and combines all detail data
- [ ] All detail panel sections populated with real/mock data
- [ ] Loading and empty states handled
- [ ] All existing tests pass, 5+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-4b-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-4b-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify chart disposal on unmount (no memory leaks)
2. Verify chart reinitializes (not just updates) on symbol change
3. Verify TanStack Query keys include symbol — automatic refetch on change
4. Verify polling disabled in debrief mode
5. Verify Lightweight Charts uses 2D canvas (no WebGL context conflict risk)

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
