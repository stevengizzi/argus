# Sprint 27.9, Session 4: Dashboard VIX Widget (Frontend)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DashboardPage.tsx` (existing Dashboard layout and widget patterns)
   - `argus/ui/src/api/endpoints.ts` (existing API endpoint definitions)
   - `argus/ui/src/hooks/` (existing TanStack Query hook patterns — pick one as reference)
   - `argus/ui/src/components/dashboard/` (existing Dashboard widget patterns)
2. Run scoped test baseline:
   ```bash
   cd argus/ui && npx vitest run --reporter=verbose
   ```
   Expected: ~638 tests, all passing
3. Run full backend suite (final session of sprint):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -x -q
   ```
   Expected: ~3,542 + new tests, all passing

## Objective
Create VixRegimeCard component for Dashboard page showing VIX close, VRP tier, regime phase, and momentum arrow. TanStack Query hook for VIX data. Hidden when disabled.

## Requirements

1. **Create `argus/ui/src/hooks/useVixData.ts`** (~30 lines):
   - TanStack Query hook wrapping `GET /api/v1/vix/current`
   - 60s polling interval (refetchInterval)
   - `enabled` flag from system config (or a simple `/api/v1/health` check for VIX status)
   - Return typed response: `{ status, data_date, vix_close, regime, is_stale, ... }`
   - Handle loading, error, and disabled states

2. **Create `argus/ui/src/components/dashboard/VixRegimeCard.tsx`** (~100 lines):
   - Card component matching existing Dashboard widget styling (dark card, consistent sizing)
   - **Content:**
     - Header: "VIX Regime" with small status indicator (green=ok, yellow=stale, gray=unavailable)
     - VIX Close: Large number with date label (e.g., "VIX 18.45 (Mar 25)")
     - VRP Tier: Badge component (color-coded: green=COMPRESSED, blue=NORMAL, orange=ELEVATED, red=EXTREME)
     - Vol Regime Phase: Text label (CALM/TRANSITION/VOL_EXPANSION/CRISIS) with matching color
     - Momentum: Arrow icon (↑=STABILIZING green, →=NEUTRAL gray, ↓=DETERIORATING red)
   - **States:**
     - Loading: Skeleton placeholder
     - Data available: Full card content
     - Data stale: Card with "Stale" badge and muted colors
     - VIX disabled/unavailable: Do NOT render (return null)
   - Use Tailwind CSS for styling, matching existing widget patterns
   - No Canvas, no animations, no particle effects

3. **Modify `argus/ui/src/pages/DashboardPage.tsx`**:
   - Import VixRegimeCard
   - Add to Dashboard layout in appropriate position (suggest: top row alongside existing summary widgets)
   - Conditionally render based on VIX data availability (hook returns enabled=false → don't render)

4. **Modify `argus/ui/src/api/endpoints.ts`**:
   - Add VIX endpoint constants: `VIX_CURRENT = '/api/v1/vix/current'`, `VIX_HISTORY = '/api/v1/vix/history'`

5. **Create `argus/ui/src/test/VixRegimeCard.test.tsx`** (6 Vitest tests):
   - `test_renders_with_data`: Mock hook returning data → card renders VIX close, regime, VRP
   - `test_renders_loading_state`: Mock hook returning loading → skeleton rendered
   - `test_renders_stale_state`: Mock hook returning stale data → stale badge visible
   - `test_hidden_when_disabled`: Mock hook returning disabled → component returns null
   - `test_hidden_when_unavailable`: Mock hook returning status=unavailable → component returns null
   - `test_momentum_arrow_correct`: Mock each momentum value → correct arrow rendered

## Visual Review
The developer should visually verify the following after this session:
1. **Dashboard with VIX data:** VixRegimeCard appears in the widget grid showing VIX close, VRP badge, regime label, and momentum arrow
2. **Dashboard with VIX stale:** Card shows "Stale" indicator with muted styling
3. **Dashboard with VIX disabled:** No VixRegimeCard visible, no layout shift
4. **Color coding:** VRP badge colors match spec (green/blue/orange/red). Regime phase colors are readable.
5. **Responsive behavior:** Card doesn't break on narrow viewport

Verification conditions:
- Run ARGUS with `vix_regime.enabled: true` and mock/real VIX data loaded
- Run ARGUS with `vix_regime.enabled: false` to verify hidden state

## Constraints
- Do NOT create a new page or navigation entry
- Do NOT use Canvas 2D, Three.js, or any animation library
- Do NOT create WebSocket connections for VIX data
- Do NOT modify existing Dashboard widgets or their layout logic
- Do NOT modify ObservatoryPage.tsx or any other page
- Match existing Dashboard component patterns (card size, typography, spacing)

## Test Targets
- Existing Vitest: all must still pass
- New tests: 6 in `argus/ui/src/test/VixRegimeCard.test.tsx`
- Test command: `cd argus/ui && npx vitest run --reporter=verbose`
- **Also run full backend suite (final session):** `python -m pytest --ignore=tests/test_main.py -n auto -x -q`

## Definition of Done
- [ ] useVixData hook implemented with 60s polling
- [ ] VixRegimeCard renders correctly in all states
- [ ] Dashboard shows VixRegimeCard when VIX enabled and data available
- [ ] Dashboard hides VixRegimeCard when VIX disabled or unavailable
- [ ] 6 Vitest tests passing
- [ ] All existing Vitest tests passing
- [ ] All backend pytest tests passing (full suite — final session)
- [ ] Visual review items verified
- [ ] Close-out written to `docs/sprints/sprint-27.9/session-4-closeout.md`
- [ ] Tier 2 review via @reviewer (full suite)

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| R14: Dashboard loads when VIX disabled | Vitest: test_hidden_when_disabled |
| Existing Dashboard widgets unchanged | Visual check + existing Vitest suite |
| No other pages modified | `git diff argus/ui/src/pages/` → only DashboardPage.tsx |

## Close-Out
Write to: `docs/sprints/sprint-27.9/session-4-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-27.9/review-context.md`
2. Close-out: `docs/sprints/sprint-27.9/session-4-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test (FINAL SESSION — full suite):
   ```bash
   python -m pytest --ignore=tests/test_main.py -n auto -x -q
   cd argus/ui && npx vitest run --reporter=verbose
   ```
5. Do-not-modify: `argus/ui/src/pages/ObservatoryPage.tsx`, `argus/ui/src/pages/PatternLibraryPage.tsx`, all other pages except DashboardPage.tsx, all backend code

## Post-Review Fix Documentation
If @reviewer reports CONCERNS, fix and update both close-out and review report files.

## Session-Specific Review Focus (for @reviewer)
1. Verify no Canvas 2D or Three.js usage (must be simple React + Tailwind)
2. Verify VixRegimeCard returns null (not empty div) when disabled
3. Verify TanStack Query polling interval is 60s (not shorter)
4. Verify no WebSocket connections added
5. Verify existing Dashboard widgets are visually unchanged (no layout shifts)
6. Verify TypeScript types match the REST endpoint response format

## Sprint-Level Regression Checklist (for @reviewer)
R1–R15 as in review-context.md. R14 primary. Full suite run for final review.

## Sprint-Level Escalation Criteria (for @reviewer)
1–7 as in review-context.md.
