# Sprint 26, Session 10: UI — Pattern Library Cards

## Pre-Flight Checks
1. Read:
   - `argus/ui/src/pages/PatternLibraryPage.tsx`
   - `argus/ui/src/features/patterns/PatternCard.tsx`
   - `argus/ui/src/features/patterns/PatternCardGrid.tsx`
   - `argus/ui/src/features/patterns/PatternDetail.tsx`
   - `argus/ui/src/api/types.ts` (StrategiesResponse type)
   - `argus/ui/src/hooks/useStrategies.ts`
   - `argus/ui/src/api/client.ts` (getStrategies)
2. Run full test baseline (DEC-328 — final session):
   ```
   python -m pytest --ignore=tests/test_main.py -n auto -q
   cd argus/ui && npx vitest run --reporter=verbose
   ```
   Expected: ~2,891+ pytest, ~611+ Vitest, all passing
3. Verify branch
4. Start the dev server to verify existing Pattern Library renders correctly:
   ```
   cd argus/ui && npm run dev
   ```

## Objective
Ensure the Pattern Library page correctly displays 3 new strategy/pattern cards (Red-to-Green, Bull Flag, Flat-Top Breakout) using existing component infrastructure. The API already returns all 7 strategies from S9 wiring — this session verifies the frontend handles them correctly and adds any needed family color/icon mappings.

## Requirements

1. **Verify `argus/ui/src/api/types.ts`:**
   - Check that `StrategyInfo` type (or whatever type `StrategiesResponse.strategies` uses) is generic enough to handle new families ("reversal", "continuation", "breakout")
   - If the type uses a union/enum for `family`, add the new values
   - If the type uses `string`, no changes needed

2. **Update `argus/ui/src/features/patterns/PatternCard.tsx`:**
   - Check family-to-color mapping. If there's a color map (e.g., momentum=blue, mean_reversion=green):
     - Add: `reversal` → purple/violet
     - Add: `continuation` → teal/cyan
     - Add: `breakout` → amber/orange
   - If no color map exists and colors are derived dynamically, verify new families render correctly
   - Check family-to-icon mapping if present — add icons for new families

3. **Update `argus/ui/src/features/patterns/PatternDetail.tsx`:**
   - Verify detail panel tabs work for new strategies (overview, performance, backtest, trades, intelligence)
   - The existing implementation should handle new strategies automatically since it reads from API data
   - If there are hardcoded strategy_id checks anywhere, add the new IDs

4. **Verify `argus/ui/src/features/patterns/PatternCardGrid.tsx`:**
   - Verify grid layout handles 7 cards without breaking
   - Check sort logic handles new families

5. **Verify `argus/ui/src/features/patterns/IncubatorPipeline.tsx`:**
   - Verify pipeline visualization counts include new strategies
   - New strategies at "exploration" stage should appear in the correct pipeline bucket

6. **Write Vitest tests:**
   - Use mock strategy data that includes all 7 strategies

## Constraints
- Do NOT modify PatternLibraryPage.tsx layout structure
- Do NOT add new pages, routes, or navigation items
- Do NOT modify API endpoints or hooks (data comes from existing /strategies endpoint)
- MINIMAL changes — the existing component infrastructure should handle new strategies. Only add family color/icon mappings if needed.

## Visual Review
The developer should visually verify the following after this session:
1. **Pattern Library page:** Shows 7 strategy cards (4 existing + 3 new)
2. **New card appearance:** Each new card has correct name, family badge, pipeline stage ("exploration"), operating window display
3. **Card grid layout:** 7 cards render in a clean grid without overflow or broken spacing
4. **Family colors:** New families (reversal, continuation, breakout) have distinct colors from existing families
5. **Detail panel:** Clicking any new card opens detail panel with all 5 tabs
6. **Pipeline visualization:** "exploration" bucket shows new strategies, counts are correct
7. **Search/filter:** Searching by name or filtering by stage includes new strategies

Verification conditions:
- App must be running with API serving 7 strategies (dev mode with mock data or live with S9 wiring)
- If using mock data, seed 7 strategies with correct metadata

## Test Targets
New Vitest tests in `argus/ui/src/features/patterns/__tests__/PatternCard.test.tsx` (or adjacent):
1. `test_renders_reversal_family_badge` — R2G card shows "reversal" family
2. `test_renders_continuation_family_badge` — Bull Flag shows "continuation"
3. `test_renders_breakout_family_badge` — Flat-Top shows "breakout"
4. `test_seven_cards_in_grid` — PatternCardGrid with 7-strategy mock data renders 7 cards
5. `test_pipeline_counts_include_new_strategies` — IncubatorPipeline counts exploration=3 (new strategies)
6. `test_detail_panel_opens_for_new_strategy` — clicking new card sets selectedStrategyId
7. `test_family_color_distinct` — each family has a different color class
8. `test_card_displays_operating_window` — new card shows time_window_display
- Minimum new test count: 8
- Test: `cd argus/ui && npx vitest run --reporter=verbose`

## Definition of Done
- [ ] All 7 strategies visible on Pattern Library page
- [ ] Family color/icon mappings for new families
- [ ] Detail panel works for new strategies
- [ ] Pipeline visualization counts are correct
- [ ] Visual review items checked (document results in close-out)
- [ ] All existing tests pass, 8+ new Vitest tests passing
- [ ] Close-out: `docs/sprints/sprint-26/session-10-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
Write to: `docs/sprints/sprint-26/session-10-closeout.md`

## Tier 2 Review (FINAL SESSION — full suite)
Review context: `docs/sprints/sprint-26/review-context.md`
Close-out: `docs/sprints/sprint-26/session-10-closeout.md`
Test (full suite — final session per DEC-328):
```
python -m pytest --ignore=tests/test_main.py -n auto -q
cd argus/ui && npx vitest run --reporter=verbose
```
Do-not-modify: PatternLibraryPage.tsx layout, API endpoints/hooks, existing PatternCard test files (extend, don't replace)

## Session-Specific Review Focus
1. Only family color/icon additions — no structural component changes
2. New Vitest tests use realistic mock data matching actual API response shape
3. No hardcoded strategy_id checks that would break when more strategies are added later
4. Responsive layout handles 7+ cards (test at various viewport sizes if feasible)
5. Pipeline visualization correctly categorizes new strategies by pipeline_stage

## Sprint-Level Regression Checklist
See `docs/sprints/sprint-26/review-context.md` — Regression Checklist section.

## Sprint-Level Escalation Criteria
See `docs/sprints/sprint-26/review-context.md` — Escalation Criteria section.
