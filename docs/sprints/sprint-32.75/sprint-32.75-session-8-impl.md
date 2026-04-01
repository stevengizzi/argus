# Sprint 32.75, Session 8: Arena Page Shell

## Pre-Flight Checks
1. Read: `docs/sprints/sprint-32.75/review-context.md`, `argus/ui/src/App.tsx` (router), `argus/ui/src/layouts/` (nav/sidebar), `argus/ui/src/features/observatory/ObservatoryPage.tsx` (similar full-page pattern)
2. Scoped tests: `cd argus/ui && npx vitest run src/pages/`
3. Branch: `sprint-32.75-session-8`
4. S1 merged (strategy identity)

## Objective
Create the Arena page shell — route, nav item, responsive grid skeleton, stats bar, controls, empty state.

## Requirements
1. **Create `ui/src/pages/ArenaPage.tsx`**: Full-page layout with minimal chrome. Top 48px: ArenaStatsBar. Below: ArenaControls bar (sort + filter). Remainder: CSS grid container for chart cards. Edge-to-edge layout (minimal padding).
2. **Create `ui/src/features/arena/ArenaStatsBar.tsx`**: Horizontal bar showing position_count, total_pnl (color-coded), net_r, entries_5m, exits_5m. Static placeholders initially (wired to live data in S11).
3. **Create `ui/src/features/arena/ArenaControls.tsx`**: Sort mode dropdown (Entry Time, Strategy, P&L, Urgency). Strategy filter dropdown (All + each of 12 strategies with their color dots).
4. **Create `ui/src/features/arena/index.ts`**: Barrel export.
5. **Register route** in App.tsx: `/arena` path. Add to sidebar nav with icon (e.g., lucide-react `LayoutGrid` or `Monitor`).
6. **Empty state**: When zero positions, show centered message "No open positions" with subtle icon.
7. **CSS grid**: `grid-template-columns: repeat(auto-fill, minmax(280px, 1fr))` for responsive card sizing. Gap: 12px.

## Constraints
- Do NOT create the MiniChart or ArenaCard components (those are S9)
- Do NOT wire any API calls (those are S10)
- The grid should render placeholder cards or empty state only
- Do NOT modify existing page files

## Test Targets
- ArenaPage renders without errors
- ArenaStatsBar renders all stat fields
- ArenaControls sort/filter dropdowns function
- Empty state shown when no positions prop
- Nav includes Arena item
- Minimum: 4 tests
- Command: `cd argus/ui && npx vitest run src/pages/ArenaPage.test.tsx src/features/arena/`

## Visual Review
1. Arena page accessible via nav, renders edge-to-edge dark layout
2. Stats bar visible at top with placeholder values
3. Sort and filter controls functional (UI only, no data)
4. Empty state displays when no data

## Definition of Done
- [ ] Page route and nav item registered
- [ ] Stats bar, controls, grid skeleton, empty state all render
- [ ] Close-out: `docs/sprints/sprint-32.75/session-8-closeout.md`
- [ ] Tier 2 review via @reviewer
