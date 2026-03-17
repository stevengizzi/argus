# Sprint 25, Session 8: Frontend — Timeline View

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md` (Timeline view requirements)
   - `argus/ui/src/features/observatory/ObservatoryPage.tsx` (view registration)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (keyboard — view `3`)
   - `argus/api/routes/observatory.py` (S1 — session summary and symbol journey endpoints)
   - `argus/ui/src/features/observatory/detail/SymbolDetailPanel.tsx` (S4a — selection integration)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the Timeline view — a horizontal session timeline spanning the full trading day (9:30 AM – 4:00 PM ET) with one lane per strategy. Events plotted as marks at severity levels. Click an event to populate the detail panel. Active strategy windows visually indicated.

## Requirements

1. **Create `argus/ui/src/features/observatory/views/TimelineView.tsx`:**
   - Full-canvas horizontal timeline
   - Time axis: 9:30 AM – 4:00 PM ET (390 minutes), with tick marks every 30 minutes
   - 4 strategy lanes stacked vertically, each labeled:
     a. ORB Breakout (window: 9:35–11:30)
     b. ORB Scalp (window: 9:45–11:30)
     c. VWAP Reclaim (window: 10:00–12:00)
     d. Afternoon Momentum (window: 2:00–3:30)
   - Active strategy window: subtle background highlight on the lane for the active time range
   - Current time indicator: vertical line at current market time (in live mode)
   - Scroll/zoom: horizontal scroll to navigate time, mouse wheel zoom to expand/compress time scale
   - Click event mark → `onSelectSymbol(event.symbol)` (populates detail panel)

2. **Create `argus/ui/src/features/observatory/views/TimelineLane.tsx`:**
   - Single strategy lane component
   - Renders event marks positioned along the time axis:
     - **Evaluation** (severity 0): tiny dot, low opacity (`var(--color-border-secondary)`, 3px, opacity 0.3)
     - **Near-miss** (severity 1): medium dot, purple (#7F77DD, 5px, opacity 0.7). Threshold: ≥ 50% conditions passed
     - **Signal** (severity 2): larger dot, amber (#EF9F27, 7px, opacity 0.9)
     - **Trade** (severity 3): largest dot, green (#1D9E75, 10px, opacity 1.0)
   - Evaluation dots may be very dense — bucket/aggregate when zoomed out (show count badge rather than individual dots when > 20 events per pixel)
   - Hover on event mark: tooltip with symbol, time, event type, condition summary
   - Strategy name label at left edge of lane
   - Lane height: ~60px each

3. **Create `argus/ui/src/features/observatory/hooks/useTimelineData.ts`:**
   - TanStack Query hook fetching timeline-appropriate data
   - Approach: fetch session summary + evaluation events, then bucket into time intervals
   - Use `ObservatoryConfig.timeline_bucket_seconds` (default 60s) for aggregation
   - Returns: `{ lanes: TimelineLane[], currentTime: string, isLoading }`
   - Each lane: `{ strategy, events: {time, symbol, severity, conditionsPassed?, conditionsTotal?}[] }`
   - In live mode: poll every 10s or subscribe to WS updates
   - In debrief mode: fetch once for the selected date

4. **Modify `ObservatoryPage.tsx`:**
   - Register TimelineView for view key `3`

## Constraints
- Do NOT use a charting library for the timeline — build with plain SVG or div-based layout
- Keep evaluation dot rendering performant — aggregate dense clusters rather than rendering thousands of individual DOM elements
- Do NOT modify any strategy code to add new event types

## Visual Review
1. Press `3` — Timeline view renders with 4 strategy lanes
2. Time axis shows 9:30–4:00 with 30-min ticks
3. Active strategy windows highlighted (ORB lanes highlighted 9:35–11:30, etc.)
4. Event marks visible at correct positions on time axis
5. Hover on event — tooltip with symbol and details
6. Click event — detail panel opens with that symbol
7. In live mode, vertical "now" line visible at current time
8. Zoom in/out on time axis works

Verification: `npm run dev` with dev data containing evaluation events at various times.

## Test Targets
- New tests (~8 Vitest):
  - `test_timeline_renders_4_lanes`
  - `test_timeline_lane_labels_correct`
  - `test_timeline_time_axis_range` — 9:30 to 4:00
  - `test_timeline_event_severity_colors` — correct color per severity level
  - `test_timeline_active_window_highlighted`
  - `test_timeline_click_event_selects_symbol`
  - `test_timeline_data_hook_buckets_events`
  - `test_timeline_debrief_mode_no_polling`
- Minimum: 8
- Test command: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Definition of Done
- [ ] 4 strategy lanes with correct labels
- [ ] Time axis 9:30–4:00 with ticks
- [ ] Active windows highlighted
- [ ] Event marks at 4 severity levels with correct colors/sizes
- [ ] Dense event aggregation when zoomed out
- [ ] Hover tooltips on events
- [ ] Click event → detail panel
- [ ] Live mode: current time indicator
- [ ] Debrief mode: static data, no polling
- [ ] All existing tests pass, 8+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-8-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-8-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify event density handling — no thousands of DOM elements
2. Verify active window time ranges match actual strategy configs
3. Verify debrief mode disables polling
4. Verify no charting library used (pure SVG/div)
5. Verify click handler correctly maps event position to symbol

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
