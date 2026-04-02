# Sprint 32.8, Session 6f: Visual Review Fixes

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DashboardPage.tsx`
   - `argus/ui/src/features/dashboard/VitalsStrip.tsx`
   - `argus/ui/src/features/dashboard/OpenPositions.tsx`
   - `argus/ui/src/features/trades/ShadowTradesTab.tsx`
   - `argus/ui/src/features/trades/TradeFilters.tsx`
   - `argus/ui/src/features/arena/ArenaCard.tsx`
2. Kill orphaned Vitest workers:
   `pkill -f "vitest/dist/workers" 2>/dev/null; echo "Cleaned"`
3. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/pages/DashboardPage src/features/dashboard/ src/features/trades/ src/features/arena/`
   Expected: all passing
4. Verify on branch: `main`

## Objective
Fix visual issues identified during Sprint 32.8 live review. All changes are frontend CSS/layout/display fixes — no data logic, no API changes, no Python changes.

## Requirements

### 1. Dashboard — Today's Stats trades count capped at 1000
The "Trades" field in VitalsStrip's Today's Stats section shows 1000 while the Daily P&L section shows "1069 trades today." Investigate VitalsStrip.tsx — there may be a hardcoded cap, a formatting function that truncates, or the data source for this field differs from the Daily P&L data source. Both should show the same number from the same source. Fix so they match.

### 2. Dashboard — Daily P&L section horizontal space
The Daily P&L section in VitalsStrip is cramped — the sparkline, percentage, and "trades today" text are squeezed. Widen this section's flex allocation relative to the other three sections. Consider `flex-[2]` or similar to give it more room, or reduce padding/font sizes in the other sections to rebalance.

### 3. Dashboard — AI Insight and Learning Loop height mismatch
Row 4 should have matched heights. Currently the AI Insight card (with its longer text content) is taller than the Learning Loop card. If using `grid grid-cols-2`, both children should stretch to match. Verify the grid container has `items-stretch` (or `align-items: stretch` which is the grid default). If one card has a fixed height or max-height, remove it. Both cards should grow to the height of the taller one.

### 4. Dashboard — Signal Quality "Signals today:" text overflowing
The "Signals today: 9351 passed / 0 filtered" text at the bottom of the Signal Quality card is floating off the bottom edge. The card's container likely needs `overflow-hidden` or the chart above it needs a constrained height so the text stays within the card bounds. Alternatively, give the Signal Quality section a fixed internal layout: chart area (flex-1) + footer text (fixed height).

### 5. Dashboard — Positions Timeline view height
When switching the Positions card from table view to timeline view, the entire card expands to fit the timeline content, pushing Row 4 (AI Insight + Learning Loop) far down the page. Instead, the Positions card should maintain a fixed height (matching its table-view height) and the timeline content should scroll internally with `overflow-y: auto`. Look in `OpenPositions.tsx` for the timeline rendering branch — wrap the timeline content in a container with `overflow-y-auto` and a max-height that matches the table view height.

### 6. Arena — Verify card borders removed
Check `git diff argus/ui/src/features/arena/ArenaCard.tsx` for the border removal from S3. If the `style={{ border: ... }}` is still present in the file, remove it. If it's already gone in the file but still showing in the browser, the Vite dev server may need a cache clear — add a comment or whitespace change to force a re-parse.

### 7. Live Trades — Filter bar not matching Shadow density
The Live Trades filter bar (TradeFilters.tsx) still looks vertically looser than Shadow Trades. Specifically:
- The Strategy dropdown appears taller than Shadow's dropdowns
- The overall filter area has more vertical padding
Compare the padding/height values between TradeFilters.tsx and ShadowTradesTab.tsx filter section. Ensure both use the same `py-1.5` on inputs/selects, same container padding (`px-4 py-3`), and remove any remaining `min-h-[44px]` if present. Also check if the Outcome toggle (`SegmentedTab`) has different sizing between the two tabs.

### 8. Shadow Trades — Remove counts from Outcome toggle labels
The Outcome toggle shows "All 50 | Wins 1 | Losses 0 | BE 49" where the counts reflect only the first loaded page (50 trades), not the full dataset. This is misleading. Remove the count badges from the Outcome toggle labels. Show just "All | Wins | Losses | BE" as plain text buttons. The server-level `total_count` in the SummaryStats bar above is the authoritative number.

### 9. Shadow Trades — Condense filters to one row
Currently the Shadow Trades filter area spans 3 visual rows:
- Row 1: Strategy | Rejection Stage | From | To
- Row 2: Outcome toggle
- Row 3: Time presets (Today | Week | Month | All)

Condense to a single flex-wrap row:
Strategy | Rejection Stage | Outcome toggle | Today | Week | Month | All | From | To

Use `flex flex-wrap gap-2 items-center` on the container. The Outcome toggle and time presets are small enough to sit inline. On narrow viewports, flex-wrap handles the overflow naturally.

## Constraints
- Do NOT modify any Python backend files
- Do NOT change data fetching hooks, API calls, or data logic
- Do NOT modify test assertions in existing tests (but you may add new tests)
- All changes are CSS, layout, and display text changes

## Visual Review
After all fixes, the developer should verify:
1. **VitalsStrip**: Trades count in Today's Stats matches Daily P&L trade count. Daily P&L section has adequate horizontal space.
2. **Row 4**: AI Insight and Learning Loop cards are exactly the same height (flush bottom edges).
3. **Signal Quality**: "Signals today:" text fully visible within the card, not clipped or floating.
4. **Positions Timeline**: Switching to timeline view does NOT expand the card height. Timeline scrolls internally.
5. **Arena**: No colored borders on any cards.
6. **Live Trades**: Filter bar density matches Shadow Trades — same input heights, same container padding.
7. **Shadow Trades**: Outcome toggle shows "All | Wins | Losses | BE" without count badges. All filters on one row.

Verification conditions:
- ARGUS running with live data
- Vite dev server on port 5175
- Multiple open positions for Arena and Positions table
- At least some closed trades for Trades page

## Test Targets
- All existing tests must pass
- New tests (if any): only for structural changes (e.g., test that Outcome toggle labels don't contain numbers)
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Today's Stats trade count matches Daily P&L count
- [ ] Daily P&L section has better horizontal space
- [ ] AI Insight and Learning Loop are flush height
- [ ] Signal Quality text fully visible within card
- [ ] Positions Timeline view scrolls internally, fixed card height
- [ ] Arena cards have no colored borders
- [ ] Live Trades filter bar matches Shadow density
- [ ] Shadow Trades Outcome toggle has no count badges
- [ ] Shadow Trades filters condensed to one row
- [ ] All existing tests pass
- [ ] Close-out report written to docs/sprints/sprint-32.8/session-6f-closeout.md
- [ ] Tier 2 review via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out MUST run the full test suite (final session):
`python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`

**Write the close-out report to:**
docs/sprints/sprint-32.8/session-6f-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context file: `docs/sprints/sprint-32.8/review-context.md`
2. Close-out report: `docs/sprints/sprint-32.8/session-6f-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command: `python -m pytest --ignore=tests/test_main.py -n auto -q && cd argus/ui && npx vitest run`
5. Files that should NOT have been modified: any Python files (except none should be touched at all)

## Session-Specific Review Focus (for @reviewer)
1. Verify trades count data source is consistent between VitalsStrip and Daily P&L
2. Verify AI Insight / Learning Loop grid uses `items-stretch` or equivalent
3. Verify Positions timeline view has `overflow-y-auto` with constrained height
4. Verify Outcome toggle labels are plain text with no count badges
5. Verify no Python files in diff
