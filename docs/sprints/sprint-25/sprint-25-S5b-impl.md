# Sprint 25, Session 5b: Frontend — Matrix Virtual Scrolling + Live Sort + Interaction

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/features/observatory/views/MatrixView.tsx` (S5a output)
   - `argus/ui/src/features/observatory/views/MatrixRow.tsx` (S5a output)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (S3 — keyboard)
   - `argus/api/websocket/observatory_ws.py` (S2 — WS message shapes for live data)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Add virtualized scrolling for large row counts, live-updating sort order from WebSocket data, and keyboard navigation within the Matrix (Tab/Shift+Tab cycle through rows).

## Requirements

1. **Create `argus/ui/src/features/observatory/hooks/useMatrixData.ts`:**
   - TanStack Query hook fetching closest-miss data: `GET /api/v1/observatory/closest-misses?tier={tier}&limit={limit}`
   - Also subscribes to Observatory WebSocket for live evaluation updates
   - When WS pushes new evaluation data, merge into cached TanStack data and re-sort
   - Sort: conditions_passed descending, then alphabetical by symbol as tiebreaker
   - Expose: `{ rows, isLoading, error, highlightedIndex }`
   - In debrief mode: fetch once, no WS subscription

2. **Modify `MatrixView.tsx` — add virtualization:**
   - Use a simple virtual scroll implementation (calculate visible rows from scroll position and container height, render only those + buffer)
   - Do NOT install a new npm package for this — implement with a straightforward `overflow-y: auto` container, `onScroll` handler, and absolute-positioned rows. The `matrix_max_rows` config controls the maximum buffer.
   - Or, if `react-window` or similar is already in dependencies, use that.

3. **Modify `MatrixView.tsx` — add keyboard navigation:**
   - `Tab` moves highlight to next row, `Shift+Tab` to previous
   - Highlighted row auto-scrolls into view
   - `Enter` on highlighted row selects the symbol (opens detail panel)
   - Highlighted row state managed via `highlightedIndex` from useMatrixData or local state
   - Focus indicator: subtle left border accent on highlighted row

4. **Live sort behavior:**
   - When new data arrives from WS, rows re-sort smoothly
   - The currently highlighted row stays highlighted even if its position in the list changes (track by symbol, not index)
   - New symbols appearing in the tier animate in (fade), symbols leaving animate out

## Constraints
- Do NOT install new npm packages for virtualization — use native scroll + positioning or existing dependency
- Keep the sort stable (symbols with same conditions_passed don't jump on every update)

## Visual Review
1. Load Matrix with 100+ rows — scroll is smooth
2. Tab through rows — highlight moves, auto-scrolls
3. While watching, new data arrives and rows re-sort (symbol at position 3 moves to position 1)
4. Highlighted symbol stays highlighted after re-sort
5. Enter on highlighted row opens detail panel

Verification: `npm run dev` with dev data generating enough rows.

## Test Targets
- New tests (~4 Vitest):
  - `test_matrix_data_sorted_by_conditions`
  - `test_matrix_keyboard_tab_advances_highlight`
  - `test_matrix_highlight_tracks_symbol_across_resort`
  - `test_matrix_enter_selects_highlighted`
- Minimum: 4
- Test command: `cd argus/ui && npx vitest run src/features/observatory/`

## Definition of Done
- [ ] Virtual scrolling handles 500+ rows without jank
- [ ] Live sort on new data
- [ ] Tab/Shift+Tab navigation with auto-scroll
- [ ] Highlight persists across re-sort (tracked by symbol)
- [ ] Enter selects highlighted symbol
- [ ] All existing tests pass, 4+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-5b-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-5b-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify virtual scroll doesn't install new packages
2. Verify highlight tracks by symbol, not array index
3. Verify stable sort (same-score symbols don't jump)
4. Verify debrief mode disables WS subscription

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
