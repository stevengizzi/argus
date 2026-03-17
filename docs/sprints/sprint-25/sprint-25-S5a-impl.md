# Sprint 25, Session 5a: Frontend — Matrix View Core

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md` (Matrix view acceptance criteria)
   - `argus/ui/src/features/observatory/ObservatoryPage.tsx` (S3 — view registration)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (S3 — keyboard integration)
   - `argus/api/routes/observatory.py` (S1 — closest-misses endpoint shape)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`

## Objective
Create the Matrix view — a full-screen condition heatmap where rows are symbols on the currently-selected tier, sorted by proximity to trigger, and columns are the strategy's entry conditions. This is the primary diagnostic view for answering "why aren't trades firing?"

## Requirements

1. **Create `argus/ui/src/features/observatory/views/MatrixView.tsx`:**
   - Full-canvas heatmap grid
   - Header row: condition names as column headers (from the strategy associated with the current tier's evaluations)
   - Data rows: one per symbol, each containing:
     a. Symbol ticker (fixed left column, always visible during horizontal scroll if needed)
     b. Conditions-passed count / total (e.g., "6/8")
     c. Condition cells: colored squares/rectangles
       - Green (#EAF3DE / #1D9E75): condition passed
       - Red (#FCEBEB / #E24B4A): condition failed
       - Gray (var(--color-background-secondary)): not applicable (strategy window inactive, or condition doesn't apply)
     d. Hover on cell: tooltip showing condition name, actual value, required value
   - Rows sorted by conditions_passed descending (most promising at top)
   - When multiple strategies are evaluating symbols at the current tier, group by strategy with a strategy header row
   - Receives `selectedTier` from ObservatoryPage to determine which data to show
   - Empty state: "No symbols at this tier" centered message

2. **Create `argus/ui/src/features/observatory/views/MatrixRow.tsx`:**
   - Single row component optimized for rendering performance
   - Click row → set selectedSymbol (populates detail panel)
   - Selected row gets highlight border/background
   - Keyboard-focused row gets subtle focus indicator

3. **Modify `ObservatoryPage.tsx`:**
   - Register MatrixView as the component for view key `2`
   - Pass selectedTier, selectedSymbol, and onSelectSymbol to MatrixView

## Constraints
- Do NOT implement virtual scrolling yet (S5b adds it)
- Do NOT implement live-updating sort yet (S5b adds it)
- Basic rendering with static data fetch is sufficient for this session
- Keep rows as simple as possible for S5b to add virtualization layer

## Visual Review
1. Press `2` to switch to Matrix view
2. Matrix renders with header row and symbol rows
3. Green/red/gray cells correctly colored
4. Hover on cell shows tooltip with values
5. Click row highlights it and opens detail panel
6. Empty tier shows appropriate message
7. Sorted by conditions-passed (most at top)

Verification: `npm run dev` with dev/mock data, navigate to Observatory, press `2`.

## Test Targets
- New tests (~6 Vitest):
  - `test_matrix_view_renders_header_row`
  - `test_matrix_row_correct_cell_colors`
  - `test_matrix_row_click_selects_symbol`
  - `test_matrix_sorted_by_conditions_passed`
  - `test_matrix_gray_cells_for_inactive`
  - `test_matrix_empty_tier_message`
- Minimum: 6
- Test command: `cd argus/ui && npx vitest run src/features/observatory/views/`

## Definition of Done
- [ ] Matrix view renders with header and data rows
- [ ] Correct green/red/gray cell coloring
- [ ] Tooltip on cell hover with values
- [ ] Sorted by conditions passed (descending)
- [ ] Click row selects symbol → detail panel
- [ ] Empty state handled
- [ ] All existing tests pass, 6+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-5a-closeout.md`
- [ ] Tier 2 review → `docs/sprints/sprint-25/session-5a-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify cell color mapping matches spec (green=pass, red=fail, gray=inactive — NOT gray=fail)
2. Verify sort order is descending by conditions_passed
3. Verify strategy grouping when multiple strategies evaluate symbols on same tier
4. Verify row component is simple enough for S5b virtualization (no complex internal state)

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
