# Sprint 25.6, Session 3: Trades Page Fixes (DEF-067/068/069/073)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/TradesPage.tsx`
   - Search for trade-related hooks: `grep -rn "useTrades\|useTradeFilter\|tradeStore" argus/ui/src/`
   - `argus/ui/src/api/types.ts` (trade-related types)
2. Run scoped test baseline (DEC-328 — Session 2+):
   ```
   cd argus/ui && npx vitest run src/pages/TradesPage
   ```
   Expected: all passing
3. Verify Sessions 1–2 are committed.

## Objective
Fix four UX issues on the Trades page: replace pagination with scrollable table, compute summary metrics from full dataset, fix time filter state persistence on page re-entry, and enable sortable column headers.

## Requirements

### 1. Replace pagination with scrollable table (DEF-067)
- Remove any pagination controls (page buttons, page size selector)
- Set the table container to a fixed visible height (~20 rows) with `overflow-y: auto`
- Fetch all trades matching the active filter in a single query (no `limit`/`offset` pagination)
- If TanStack Table is being used, switch from paginated to unpaginated mode

### 2. Compute metrics from full dataset (DEF-068)
- Win Rate and Net P&L at the top of the page must be computed from the full trade list for the active time filter
- These values must NOT change when the user scrolls
- If metrics were previously derived from a paginated slice: change the source to the complete query result
- Verify metrics recalculate correctly when the time filter changes

### 3. Fix time filter persistence (DEF-069)
- The time filter toggle (Today / Week / Month / All) must drive BOTH:
  a. The visual toggle button state
  b. The query parameters (`date_from` / `date_to`) sent to the API
- On page re-entry (navigate away, return): both toggle state AND query params must be restored from the persisted state
- Root cause is likely: toggle state in Zustand persists across navigation, but the TanStack Query key or fetch params reset to defaults on component mount
- Fix: ensure the query uses the Zustand store value as the source of truth for filter params, and that the initial fetch on mount reads from the store (not a hardcoded default)

### 4. Enable sortable columns (DEF-073)
- Column headers for at least: Symbol, Strategy, P&L, R-multiple, Time should be clickable
- First click: sort ascending. Second click: sort descending. Third click: clear sort (or cycle)
- Show a sort indicator (arrow/chevron) on the active sort column
- Client-side sorting is fine (all data is loaded, no server-side sort needed after DEF-067 removes pagination)

## Constraints
- Do NOT modify backend API endpoints or response schemas
- Do NOT modify: `risk_manager.py`, `order_manager.py`, any strategy file
- Do NOT add virtualization (deferred — current trade volume is <100/day)
- Keep existing table column layout and styling (just add scroll + sort)

## Test Targets
After implementation:
- Existing Vitest tests: all must still pass
- New tests:
  1. Test that table renders without pagination controls
  2. Test that summary metrics are derived from full trade array, not a slice
  3. Test that time filter state drives query params on mount
  4. Test that clicking a column header triggers sort (check rendered order changes)
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run`

## Visual Review
The developer should visually verify:
1. **Scroll:** Trades table scrolls vertically (no pagination buttons visible)
2. **Metrics:** Win Rate + Net P&L stay constant while scrolling through rows
3. **Filter persistence:** Set filter to "Today", navigate to Dashboard, return to Trades — both toggle and data show "Today"
4. **Sort:** Click "P&L" column header — rows reorder by P&L, arrow indicator appears

Verification conditions: App running with existing trade data from March 19 session.

## Definition of Done
- [ ] Pagination replaced with scrollable table
- [ ] Summary metrics computed from full dataset
- [ ] Time filter persists correctly on page re-entry
- [ ] Column headers sortable with sort indicator
- [ ] All existing tests pass
- [ ] 4+ new Vitest tests written and passing
- [ ] `npx tsc --noEmit` clean
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All trades visible | Row count matches expected trade count for filter |
| Trade detail panel still works | Click a row — detail panel opens with correct data |
| Time filter buttons all functional | Click each (Today/Week/Month/All) — data updates |
| TypeScript clean | `npx tsc --noEmit` |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.
**Write to:** `docs/sprints/sprint-25.6/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-25.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-25.6/session-3-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (scoped): `cd argus/ui && npx vitest run src/pages/TradesPage`
5. Files that should NOT have been modified: any backend Python file

## Session-Specific Review Focus (for @reviewer)
1. Verify no pagination component or controls remain in the rendered output
2. Verify metrics source is the complete trade array, not a paginated slice
3. Verify the Zustand store (or equivalent) drives both toggle UI and query params
4. Verify sort is client-side only (no API changes)

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
