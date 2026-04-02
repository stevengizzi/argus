# Sprint 32.8, Session 3: Arena UI Polish

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/arena/ArenaCard.tsx`
   - `argus/ui/src/features/arena/MiniChart.tsx`
   - `argus/ui/src/pages/ArenaPage.tsx`
   - `argus/ui/src/features/arena/ArenaStatsBar.tsx`
2. Run scoped test baseline:
   Vitest: `cd argus/ui && npx vitest run src/features/arena/ src/pages/ArenaPage`
   Expected: all passing (DEF-138 `ArenaPage.test.tsx` WS mock may fail — known pre-existing)
3. Verify you are on the correct branch: `sprint-32.8`

## Objective
Polish Arena card visuals: remove colored borders, add entry candle markers, auto-zoom to entry point, reduce label clutter, label the progress bar, and make stats reflect active filters.

## Requirements

### 1. Remove card borders (`ArenaCard.tsx`)
Remove the `style={{ border: \`1px solid ${strategyConfig.color}\` }}` from the card container div. The strategy badge in the header row is sufficient for identification. Keep the `rounded-lg bg-argus-surface-2` classes.

### 2. Entry candle triangle marker (`MiniChart.tsx`)
Add an entry marker using the Lightweight Charts markers API. After setting candle data in the `useEffect` that handles `candles` prop:

```typescript
if (entryPrice && candles.length > 0) {
    // Find the candle closest to entry time
    const entryTimestamp = /* derive from props or find nearest candle */;
    series.setMarkers([{
        time: entryTimestamp,
        position: 'belowBar',
        color: '#3b82f6',
        shape: 'arrowUp',
        text: '',
    }]);
}
```

Add an `entryTime` prop to MiniChartProps (type: `UTCTimestamp | undefined`). Pass it from ArenaCard, which has access to the position's `entry_time` string. Convert entry_time to UTCTimestamp in ArenaCard before passing down.

The marker should appear at the candle whose time is closest to (but not after) the entry time.

### 3. Auto-zoom to entry point (`MiniChart.tsx`)
After `chart.timeScale().fitContent()`, if `entryTime` is provided, compute a visible range:
- Start: `entryTime - (5 * 60)` (5 bars before entry)
- End: latest candle time + 60s (or current time if no candles after entry)

Use `chart.timeScale().setVisibleRange({ from, to })`. This centers the view on the entry with context.

If there are fewer than 5 bars before entry (e.g., trade entered near market open), start from the first available bar.

### 4. Reduce price axis labels (`MiniChart.tsx`)
Change the `createPriceLine()` calls:
- **Entry line**: set `axisLabelVisible: false` (keep the blue dashed line itself)
- **Stop line**: keep `axisLabelVisible: true` (red, important to read exact price)
- **T1 line**: keep `axisLabelVisible: true` (green, important to read exact price)
- **Trail line**: set `axisLabelVisible: false` (keep the yellow dashed line itself)

This reduces the right-axis label count from 4 to 2, preventing overlap.

### 5. Progress bar label (`ArenaCard.tsx`)
Add a tiny label or tooltip to the stop-to-T1 progress bar. Two options (implement whichever is cleaner):

**Option A (inline labels):** Add small text at each end of the bar:
```
Stop ─────────●───────── T1
```
Use `text-[10px] text-argus-text-dim` at left ("Stop") and right ("T1").

**Option B (tooltip):** Wrap the progress bar in a container with `title="Price position between Stop and T1"`.

Prefer Option A if space allows within the card width.

### 6. Filtered stats in ArenaStatsBar (`ArenaStatsBar.tsx` + `ArenaPage.tsx`)
Currently, ArenaStatsBar always shows totals from the WebSocket stats message, which covers ALL positions regardless of the strategy filter.

When `strategyFilter !== 'all'`, compute filtered stats from the displayed positions instead:
- `position_count`: `displayPositions.length`
- `total_pnl`: sum of `(overlay?.unrealized_pnl ?? pos.unrealized_pnl)` across displayed positions
- `net_r`: sum of `(overlay?.r_multiple ?? pos.r_multiple)` across displayed positions
- `entries_5m` and `exits_5m`: keep from WS stats (these are global and fine as-is)

Pass filtered vs unfiltered stats to ArenaStatsBar based on whether a filter is active.

## Constraints
- Do NOT modify: any Python backend files, any non-Arena frontend files
- Do NOT change: the Arena grid layout, card sizing, or sort/filter logic
- Do NOT change: the WebSocket hook message handling (that's S1's domain)
- Do NOT add: new API calls or data fetching

## Visual Review
The developer should visually verify the following after this session:
1. **No borders**: Arena cards have no colored outline, just the dark surface background
2. **Entry markers**: Blue upward triangle visible at the entry candle on each chart
3. **Auto-zoom**: Charts are zoomed to show the entry point with ~5 bars of context before
4. **Label cleanup**: Only Stop (red) and T1 (green) labels on the right price axis; Entry and Trail are lines only
5. **Progress bar**: "Stop" and "T1" text visible at the ends of the progress bar
6. **Filtered stats**: When filtering by a strategy (e.g., VWAP Reclaim), the stats bar shows position count and P&L for only that strategy's positions

Verification conditions:
- ARGUS running with open positions
- Vite dev server on port 5175
- Test with both "All" filter and a specific strategy filter

## Test Targets
- New tests:
  1. `test_arena_card_no_border` — ArenaCard container has no `border` style
  2. `test_mini_chart_entry_marker` — MiniChart creates a marker when entryTime provided
  3. `test_mini_chart_no_marker_without_entry_time` — no marker when entryTime undefined
  4. `test_mini_chart_reduced_axis_labels` — Entry and Trail price lines have axisLabelVisible: false
  5. `test_progress_bar_labels` — "Stop" and "T1" text present in progress bar area
  6. `test_filtered_stats_with_strategy_filter` — stats reflect filtered positions when filter active
- Minimum new test count: 6
- Test command: `cd argus/ui && npx vitest run src/features/arena/ src/pages/ArenaPage`

## Definition of Done
- [ ] Card borders removed
- [ ] Entry triangle markers rendered at entry candle
- [ ] Charts auto-zoom to entry point
- [ ] Only Stop + T1 have axis labels
- [ ] Progress bar has Stop/T1 labels
- [ ] Stats bar reflects active strategy filter
- [ ] All existing tests pass
- [ ] 6+ new tests passing
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-3-closeout.md
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Arena cards still render with strategy badge | Visual check: colored badge in top-left of each card |
| Charts still show price level lines (entry blue, stop red, T1 green, trail yellow) | Visual check: lines visible on charts |
| Progress bar still functional | White pip moves with price between stop and T1 |
| Stats bar still updates from WebSocket | Stats bar shows live position count and P&L when filter is "All" |

## Close-Out
**Write the close-out report to a file:**
docs/sprints/sprint-32.8/session-3-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-3-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `cd argus/ui && npx vitest run src/features/arena/ src/pages/ArenaPage`
5. Files that should NOT have been modified: any Python files, any non-Arena UI files

## Session-Specific Review Focus (for @reviewer)
1. Verify border removal is complete (no inline style or className with border)
2. Verify entry marker uses Lightweight Charts `setMarkers()` API (not a custom overlay)
3. Verify auto-zoom uses `setVisibleRange()` with sensible from/to calculation
4. Verify `axisLabelVisible: false` is set on Entry and Trail price lines
5. Verify filtered stats computation only activates when `strategyFilter !== 'all'`

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-32.8/review-context.md`
