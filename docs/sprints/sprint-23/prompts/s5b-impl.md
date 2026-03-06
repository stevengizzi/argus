# Sprint 23, Session 5b: Frontend — Dashboard Universe Panel

## Pre-Flight Checks
1. Read: `argus/ui/src/features/dashboard/` (existing Dashboard components — understand layout, card patterns, data fetching), `argus/ui/src/hooks/` or `argus/ui/src/api/` (TanStack Query patterns, API hooks), `argus/api/routes/universe.py` (Session 5a — API response shape)
2. Run: `cd argus/ui && npx vitest run` — all passing
3. Branch: `sprint-23`

## Objective
Add a Universe Status panel to the Dashboard page showing universe monitoring stats.

## Requirements

1. Create an API hook for universe data:
   - `useUniverseStatus()` — fetches from `/api/v1/universe/status`
   - Polling interval: 60 seconds (universe data changes at most once per day, but freshness indicator is useful)
   - Handle loading, error, and disabled states

2. Create `UniverseStatusCard` component (or similar name following existing patterns):
   - **Enabled state:** Shows:
     - Total viable symbols count (large number, prominent)
     - Per-strategy match counts (small list or compact display with strategy names)
     - Reference data age ("Updated 45 min ago" or similar)
   - **Disabled state:** Shows "Universe Manager not enabled" with muted styling
   - **Loading state:** Skeleton consistent with existing Dashboard cards
   - **Error state:** Error message with retry

3. Integrate into Dashboard page layout:
   - Position: above or beside the existing watchlist panel (natural grouping — universe stats relate to watchlist context)
   - Follow existing Dashboard card patterns (same border radius, shadow, padding, etc.)
   - Must not break existing Dashboard layout or other panels

4. Styling:
   - Tailwind CSS v4 (existing stack)
   - Framer Motion for entrance animation (if other cards use it)
   - Responsive: works on desktop and mobile (PWA)
   - Follow "Bloomberg Terminal meets modern fintech" design north star (DEC-109)

## Constraints
- Do NOT modify other Dashboard panels or their data fetching
- Do NOT modify any backend files
- Do NOT add new npm dependencies
- Follow existing component patterns exactly (imports, hooks, Tailwind classes)

## Visual Review
The developer should visually verify the following after this session:

1. **Universe panel renders on Dashboard**: correct position, no overlap with other panels, consistent card styling
2. **Per-strategy counts display clearly**: strategy names readable, counts visible
3. **Disabled state renders cleanly**: "Universe Manager not enabled" message, muted/dimmed appearance
4. **Mobile responsive**: panel stacks correctly on narrow viewport (iPhone width)
5. **No visual regressions**: other Dashboard panels (watchlist, AI insight card, goal tracking) unchanged

Verification conditions:
- Run dev server: `cd argus/ui && npm run dev`
- View Dashboard at `http://localhost:5173`
- For enabled state: may need to mock API response (or use dev mode if it provides mock data)
- For disabled state: API returns `{"enabled": false}` — this is the default
- Test mobile: resize browser to 375px width

## Test Targets
- New Vitest tests:
  1. `test_universe_status_card_renders_enabled`: mock API, verify counts displayed
  2. `test_universe_status_card_renders_disabled`: mock disabled response
  3. `test_universe_status_card_loading_state`: verify skeleton/loading indicator
  4. `test_universe_status_card_error_state`: mock API error
  5. `test_universe_status_card_strategy_counts`: verify per-strategy display
  6. `test_universe_status_card_age_display`: reference data age formatting
  7. `test_dashboard_includes_universe_card`: Dashboard renders with universe card
  8. `test_universe_api_hook`: useUniverseStatus hook returns correct shape
- Minimum: 8 tests
- Command: `cd argus/ui && npx vitest run --reporter=verbose`

## Definition of Done
- [ ] UniverseStatusCard component created
- [ ] Integrated into Dashboard page
- [ ] Enabled, disabled, loading, and error states all render correctly
- [ ] Visual review items verified
- [ ] All existing Vitest tests pass
- [ ] 8+ new tests passing
- [ ] Mobile responsive

## Close-Out
Follow `.claude/skills/close-out.md`. Include visual review findings in "Notes for Reviewer" section.

## Sprint-Level Regression Checklist
R2 (Vitest 377+), R20 (Dashboard loads, UM enabled), R21 (Dashboard loads, UM disabled), R22 (other pages unaffected), R23 (AI Copilot functional).

## Sprint-Level Escalation Criteria
E11: AI Copilot affected → ESCALATE. E12: Modifying "Do not modify" files → ESCALATE.
