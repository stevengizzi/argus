# Sprint 27.6, Session 10: Observatory Regime Visualization

## Pre-Flight Checks
1. Read these files to load context:
   - `argus/ui/src/pages/Observatory/` (existing Observatory components)
   - `argus/ui/src/hooks/` (existing hooks, especially useObservatory or similar)
   - `argus/api/routes/` (Observatory API endpoints for regime data)
   - `argus/core/regime.py` (RegimeVector.to_dict() output format)
2. Run frontend test baseline:
   ```
   cd argus/ui && npx vitest run --reporter=verbose
   ```
   Expected: ~620 tests, all passing
3. Run full backend suite (DEC-328 — final session):
   ```
   python -m pytest --ignore=tests/test_main.py -x -q -n auto
   ```
   Expected: all passing
4. Verify branch

## Objective
Extend Observatory session vitals bar to display RegimeVector dimensions — trend, volatility, breadth, correlation, sector rotation, intraday character. Handle None/missing data gracefully.

## Requirements

1. Extend the Observatory session vitals bar component to show regime dimensions:
   - **Trend**: score indicator (-1 to +1 with color gradient red→neutral→green) + conviction badge
   - **Volatility**: level (numeric) + direction arrow (↑/↓/→)
   - **Breadth**: universe_breadth_score bar (-1 to +1) + thrust indicator (highlight when active). Show "Warming up..." when None.
   - **Correlation**: average value + regime badge (dispersed/normal/concentrated with color)
   - **Sector**: rotation phase badge + leading sectors as small tags
   - **Intraday**: character badge (trending/choppy/reversal/breakout with distinct colors). Show "Pre-market" when None.
   - **Confidence**: regime_confidence as a thin progress bar with numeric value

2. Data source: The regime_vector_summary is available from the Observatory WebSocket or health endpoint. Use the same data flow pattern as existing session vitals.

3. Graceful handling:
   - RegimeVector data unavailable → show placeholder/skeleton state, no JS errors
   - Individual dimensions None → show appropriate placeholder (e.g., "N/A", "—", or loading state)
   - regime_intelligence disabled → hide the regime dimensions section entirely

## Constraints
- Do NOT modify backend files in this session
- Follow existing Observatory component patterns and Tailwind styling
- Keep the vitals bar compact — regime dimensions should not dominate the layout

## Visual Review
The developer should visually verify the following after this session:
1. **Session vitals bar with regime data**: All 6 dimensions displayed with appropriate indicators
2. **Pre-market state**: Intraday and breadth show "Pre-market" / "Warming up..." placeholders
3. **Missing data state**: When regime_vector_summary is null, regime section gracefully hidden or shows skeleton
4. **Responsive**: Dimensions wrap gracefully on smaller viewports
5. **Dark/light mode**: Color indicators readable in both themes (if applicable)

Verification conditions:
- Observatory page loaded with paper trading system running
- If no live data: use browser dev tools to inject mock regime_vector_summary into the WebSocket message

## Test Targets
- New Vitest tests (~6) in appropriate test file:
  - Regime vitals component renders with full RegimeVector data
  - Handles None intraday fields (pre-market state) → placeholder
  - Handles missing/disabled dimensions
  - Displays all 6 dimension indicators
  - Updates on regime change
  - No JS errors when regime_vector_summary is null
- Minimum: 6
- Test command: `cd argus/ui && npx vitest run --reporter=verbose`

## Definition of Done
- [ ] Session vitals bar displays all 6 regime dimensions
- [ ] Graceful handling of None/missing data
- [ ] 6+ Vitest tests passing
- [ ] Visual review items verified
- [ ] Close-out: `docs/sprints/sprint-27.6/session-10-closeout.md`
- [ ] Tier 2 review via @reviewer

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end, fenced with ```json:structured-closeout. See the close-out skill for the full schema.

Write the close-out report to: `docs/sprints/sprint-27.6/session-10-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
After close-out, invoke @reviewer with:
1. Review context: `docs/sprints/sprint-27.6/review-context.md`
2. Close-out: `docs/sprints/sprint-27.6/session-10-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (FINAL SESSION — full suites):
   - Backend: `python -m pytest --ignore=tests/test_main.py -x -q -n auto`
   - Frontend: `cd argus/ui && npx vitest run --reporter=verbose`
5. Files NOT to modify: all backend Python files

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-27.6/session-10-review.md`

## Session-Specific Review Focus
1. Verify no backend modifications
2. Verify graceful None handling (no JS errors in any state)
3. Verify existing Observatory views unaffected (Funnel, Radar, Matrix, Timeline)
4. Verify regime section hidden when regime_intelligence disabled
5. Verify compact layout (vitals bar not excessively expanded)
