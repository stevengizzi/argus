# Sprint 25, Session 4a: Frontend — Detail Panel Shell + Condition Grid + Strategy History

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md`
   - `argus/ui/src/features/observatory/ObservatoryLayout.tsx` (S3 output — panel zone)
   - `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (S3 output)
   - `argus/api/routes/observatory.py` (S1 output — endpoint shapes)
   - Existing detail panel patterns in the codebase (e.g., TradeDetailPanel, SignalDetailPanel)
2. Run scoped test baseline:
   `cd argus/ui && npx vitest run src/features/observatory/`
   Expected: all S3 tests passing

## Objective
Create the slide-out detail panel that shows a selected symbol's full context: pipeline position, per-strategy condition checks (pass/fail grid with actual vs. required values), and chronological strategy evaluation history. Wire into the ObservatoryLayout.

## Requirements

1. **Create `argus/ui/src/features/observatory/detail/SymbolDetailPanel.tsx`:**
   - Slide-out panel (320px wide, right side) with Framer Motion AnimatePresence
   - Header: ticker symbol (large, bold) + company name + close button (×)
   - Sections (stacked vertically, scrollable):
     a. Pipeline position badge (e.g., "Evaluating — AfMo" with tier color)
     b. Condition grid (SymbolConditionGrid component)
     c. Quality score + grade badge (if available — read from `/api/v1/quality/{symbol}`)
     d. Market data snapshot (price, change %, volume, ATR, VWAP, relative volume) — placeholder data for now, real data hook in S4b
     e. Catalyst summary (if available — read from `/api/v1/catalysts/{symbol}`)
     f. Strategy history (SymbolStrategyHistory component)
     g. Candlestick chart slot (placeholder div, wired in S4b)
   - Panel receives `selectedSymbol: string | null` prop. When null, panel is hidden.
   - Panel does NOT close when clicking inside it. Only closes on Escape or explicit close button.
   - Panel content updates when selectedSymbol changes (no close/reopen animation — just content swap).

2. **Create `argus/ui/src/features/observatory/detail/SymbolConditionGrid.tsx`:**
   - Displays per-strategy condition results for the selected symbol
   - If symbol is being evaluated by multiple strategies, show sections for each
   - Each condition: name, pass/fail badge, actual value, required value/threshold
   - Color: green background for pass, red for fail, gray for "–" (not applicable)
   - Data from `/api/v1/observatory/symbol/{symbol}/journey` — extract latest ENTRY_EVALUATION events and parse condition details from metadata
   - Sort: passed conditions first, then failed, within each strategy section

3. **Create `argus/ui/src/features/observatory/detail/SymbolStrategyHistory.tsx`:**
   - Chronological list of evaluation events for this symbol today (all strategies)
   - Each event: timestamp (HH:MM:SS), strategy name, event type, result (PASS/FAIL/INFO), reason
   - Color-coded by result (same palette as Decision Stream from Sprint 24.5)
   - Scrollable list, newest at top
   - Data from `/api/v1/observatory/symbol/{symbol}/journey`

4. **Modify `ObservatoryLayout.tsx`:**
   - Wire SymbolDetailPanel into the detail panel zone
   - Pass selectedSymbol state from ObservatoryPage
   - Animate panel width changes (canvas area shrinks/expands)

## Constraints
- Do NOT modify any existing detail panel components (TradeDetailPanel, SignalDetailPanel)
- Do NOT modify backend endpoints — consume S1's API as-is
- Market data section uses placeholder values for now (S4b adds real data)
- Candlestick chart section is a placeholder div (S4b adds the chart)

## Visual Review
1. Select a symbol (mock/dev data) — panel slides in from right
2. Condition grid shows pass/fail cells with correct colors
3. Strategy history shows chronological events
4. Close button and Escape both close panel
5. Selecting different symbol swaps content without close/reopen animation
6. Panel scrolls when content exceeds viewport height

Verification: `npm run dev`, navigate to Observatory, trigger symbol selection via keyboard or click.

## Test Targets
- New tests (~7 Vitest):
  - `test_detail_panel_renders_when_symbol_selected`
  - `test_detail_panel_hidden_when_no_symbol`
  - `test_condition_grid_shows_pass_fail_colors`
  - `test_condition_grid_gray_for_inactive`
  - `test_strategy_history_chronological_order`
  - `test_panel_content_updates_on_symbol_change`
  - `test_close_button_clears_selection`
- Minimum: 7
- Test command: `cd argus/ui && npx vitest run src/features/observatory/detail/`

## Definition of Done
- [ ] SymbolDetailPanel slides in/out with animation
- [ ] SymbolConditionGrid renders pass/fail with colors and values
- [ ] SymbolStrategyHistory renders chronological events
- [ ] Panel persists across view switches
- [ ] Content swaps on symbol change without re-animation
- [ ] All existing tests pass
- [ ] 7+ new tests
- [ ] Close-out: `docs/sprints/sprint-25/session-4a-closeout.md`
- [ ] Tier 2 review via @reviewer → `docs/sprints/sprint-25/session-4a-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify panel does not close on canvas click (only Escape or close button)
2. Verify content swap animation (no close/reopen on symbol change)
3. Verify condition grid color mapping: green=pass, red=fail, gray=inactive
4. Verify strategy history uses existing Sprint 24.5 color palette for event types
5. Verify no existing components modified

## Sprint-Level Regression/Escalation
See `docs/sprints/sprint-25/regression-checklist.md` and `escalation-criteria.md`
