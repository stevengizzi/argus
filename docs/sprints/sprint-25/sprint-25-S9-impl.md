# Sprint 25, Session 9: Frontend — Session Vitals + Debrief Mode

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/observatory/ObservatoryLayout.tsx` (vitals bar slot)
   - `argus/api/websocket/observatory_ws.py` (S2 — WS message shapes)
   - `argus/api/routes/observatory.py` (S1 — session-summary endpoint)
   - All existing observatory hooks (useMatrixData, useTimelineData, useSymbolDetail, useSessionVitals if partial)
   - `argus/ui/src/features/observatory/ObservatoryPage.tsx` (state management)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the session vitals bar showing real-time system health and trading metrics, and implement the debrief mode that switches all data hooks from live WebSocket to historical REST queries for a selected past date.

## Requirements

1. **Create `argus/ui/src/features/observatory/vitals/SessionVitalsBar.tsx`:**
   - Horizontal bar at top of Observatory page (below main nav, above canvas)
   - Left section — Mode toggle + View tabs:
     a. View selector tabs: Funnel / Matrix / Timeline / Radar (with keyboard hints `1` `2` `3` `4`)
     b. Live/Debrief toggle indicator
   - Center section — Session metrics:
     a. Symbols receiving data (count)
     b. Total evaluations this session (count, incrementing)
     c. Signals generated (count)
     d. Trades executed (count)
   - Right section — Diagnostics:
     a. Connection status dots: Databento (green/red), IBKR (green/red)
     b. Closest miss: "SMCI AfMo 6/8" (symbol + strategy + conditions)
     c. Top blocker: "volume_ratio (43%)" (most frequent rejection reason)
     d. Market time: "10:47 AM ET"
   - All metrics update live via WebSocket in live mode
   - In debrief mode, show "Reviewing [date]" instead of live connection status

2. **Create `argus/ui/src/features/observatory/hooks/useSessionVitals.ts`:**
   - Subscribes to Observatory WebSocket for live pipeline_update and evaluation_summary messages
   - Maintains running totals: evaluations, signals, trades
   - Extracts closest miss and top blocker from session-summary data
   - Connection status derived from WS connection state + health endpoint
   - Returns: `{ metrics, connectionStatus, closestMiss, topBlocker, marketTime, isLive }`

3. **Create `argus/ui/src/features/observatory/hooks/useDebriefMode.ts`:**
   - Manages debrief state: `{ isDebrief: boolean, selectedDate: string | null }`
   - When `isDebrief` is true:
     a. All TanStack Query hooks switch from polling/WS to one-time REST fetch with `date` param
     b. WebSocket connection is not established
     c. Vitals bar shows "Reviewing [date]" mode
   - When switching back to live:
     a. Clear date selection
     b. Reconnect WebSocket
     c. Hooks resume polling
   - Date validation: only allow dates within `debrief_retention_days` window (default 7 days)
   - Weekends/holidays: show "No market data for [date]" if selected date has no data

4. **Create date picker UI:**
   - Small calendar dropdown triggered by a button in the vitals bar
   - Shows last 7 days with market day indicators
   - Selecting a date enters debrief mode
   - "Live" button exits debrief mode
   - Keep it simple — a compact date list, not a full calendar widget

5. **Modify `ObservatoryLayout.tsx`:**
   - Wire SessionVitalsBar into the top slot
   - Pass debrief mode state to layout for visual mode indication

6. **Modify all existing Observatory data hooks** (useMatrixData, useTimelineData, useSymbolDetail):
   - Accept optional `date` parameter from useDebriefMode
   - When date is provided: add `?date={date}` to REST queries, disable polling/WS subscriptions
   - When date is null: use live mode (polling/WS)

## Constraints
- Do NOT install a date picker library — build a simple date list
- Do NOT modify backend endpoints — the date parameter is already supported from S1
- WebSocket should disconnect cleanly in debrief mode, reconnect on return to live

## Visual Review
1. Vitals bar visible at top with all sections populated
2. Connection dots green in dev mode
3. Metrics incrementing (evaluations count going up)
4. Closest miss and top blocker showing real data
5. Click date picker — shows last 7 days
6. Select a past date — all views switch to historical data, "Reviewing Mar 16" shown
7. Click "Live" — returns to real-time mode, WS reconnects
8. Select a weekend date — "No market data" message

Verification: `npm run dev`, verify vitals bar in live mode, then switch to debrief.

## Test Targets
- New tests (~8 Vitest):
  - `test_vitals_bar_renders_all_sections`
  - `test_vitals_connection_status_displayed`
  - `test_vitals_metrics_update_from_ws`
  - `test_debrief_mode_disables_ws`
  - `test_debrief_mode_adds_date_to_queries`
  - `test_debrief_date_validation_within_retention`
  - `test_debrief_exit_reconnects_live`
  - `test_date_picker_shows_last_7_days`
- Minimum: 8
- Test command: `cd argus/ui && npx vitest run src/features/observatory/`

## Definition of Done
- [ ] Session vitals bar with connection status, metrics, diagnostics
- [ ] Live updates via WebSocket
- [ ] Date picker for debrief mode
- [ ] Debrief mode switches all hooks to historical REST queries
- [ ] Return to live mode reconnects WS
- [ ] Date validation (retention window, market days)
- [ ] All existing observatory hooks accept date parameter
- [ ] All existing tests pass, 8+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-9-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-9-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify WS disconnect/reconnect on debrief mode toggle
2. Verify all data hooks accept and use date parameter
3. Verify date validation prevents selecting dates beyond retention window
4. Verify no new npm packages for date picker
5. Verify debrief mode shows appropriate "Reviewing [date]" indicator
6. Verify live mode metrics actually increment from WS data

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
