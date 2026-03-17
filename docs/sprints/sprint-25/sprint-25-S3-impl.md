# Sprint 25, Session 3: Frontend — Page Shell, Routing, Keyboard System

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md`
   - `argus/ui/src/App.tsx` (or router config — routing pattern)
   - `argus/ui/src/features/` (existing page component patterns)
   - `argus/ui/src/components/layout/` (sidebar/navigation components)
   - `argus/ui/src/hooks/` (existing hook patterns)
2. Run scoped test baseline (DEC-328):
   `cd argus/ui && npx vitest run`
   Expected: ~523 tests, all passing
3. Verify you are on the correct branch

## Objective
Create the Observatory page shell with full-bleed canvas layout (no dashboard card grid), register it in navigation as page 8, implement the complete keyboard shortcut system, and create the ObservatoryLayout component with zones for canvas, tier selector, and detail panel.

## Requirements

1. **Create `argus/ui/src/features/observatory/ObservatoryPage.tsx`:**
   - Top-level page component registered at route `/observatory`
   - Full-bleed layout: no padding, no card wrappers — canvas fills entire content area minus sidebar
   - Manages current view state: `'funnel' | 'radar' | 'matrix' | 'timeline'` (default: 'funnel')
   - Manages selected tier state: one of the 7 pipeline tiers
   - Manages selected symbol state: `string | null`
   - Renders `ObservatoryLayout` with current state
   - For now, each view slot renders a placeholder `<div>` with the view name — actual views wired in later sessions

2. **Create `argus/ui/src/features/observatory/ObservatoryLayout.tsx`:**
   - Three-zone layout:
     a. **Canvas zone** (main area) — takes remaining space, renders the active view
     b. **Tier selector** (floating right edge of canvas) — vertical stack of tier pills with counts
     c. **Detail panel** (right slide-out, 320px wide) — slides in from right when symbol selected, pushes canvas narrower (not overlay). Animated with Framer Motion.
   - Session vitals bar slot at top (placeholder for S9)
   - Bottom shortcut reference strip with key hints
   - When detail panel is closed, canvas takes full width
   - When detail panel is open, canvas shrinks to accommodate

3. **Create `argus/ui/src/features/observatory/TierSelector.tsx`:**
   - Vertical stack of tier pills: Universe, Viable, Routed, Evaluating, Near-trigger, Signal, Traded
   - Each pill shows tier name + count (count from TanStack Query hook hitting `/api/v1/observatory/pipeline`)
   - Active tier highlighted with distinct style
   - Click to select tier
   - Keyboard `[`/`]` navigates up/down

4. **Create `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts`:**
   - Global keyboard handler (useEffect with keydown listener)
   - Shortcut map:
     - `1` → set view to 'funnel'
     - `2` → set view to 'matrix'
     - `3` → set view to 'timeline'
     - `4` → set view to 'radar'
     - `[` → select previous tier
     - `]` → select next tier
     - `Tab` → select next symbol in current tier (prevent default browser tab behavior)
     - `Shift+Tab` → select previous symbol
     - `Enter` → confirm selection (open detail panel if closed)
     - `Escape` → deselect symbol / close detail panel
     - `/` → open symbol search overlay (future — for now, just set a `searchOpen` state)
     - `?` → toggle shortcut help overlay
     - `r` / `R` → reset camera (Three.js views — no-op for now)
     - `f` / `F` → fit view (Three.js views — no-op for now)
   - Only active when Observatory page is focused (not when typing in Copilot or other inputs)
   - Expose state setters and current state via return value

5. **Modify navigation/routing:**
   - Add Observatory to sidebar navigation (icon + label "Observatory")
   - Position after Orchestrator in the nav order (Dashboard, Trades, Performance, Orchestrator, Observatory, Pattern Library, Debrief, System)
   - Route: `/observatory`
   - Lazy-load with `React.lazy()` to enable code-splitting in later sessions

6. **Create `argus/ui/src/features/observatory/ShortcutOverlay.tsx`:**
   - Modal overlay showing all keyboard shortcuts, grouped by category
   - Toggle with `?` key
   - Dismiss with `Escape` or `?` again or click outside

## Constraints
- Do NOT modify any existing page components
- Do NOT modify any existing hooks or stores
- Do NOT install new npm packages — use existing dependencies (Framer Motion, TanStack Query, Zustand)
- The keyboard hook must not interfere with Copilot text input or browser shortcuts when focus is elsewhere

## Visual Review
The developer should visually verify:
1. Observatory appears in sidebar navigation at correct position
2. Clicking Observatory navigates to the page
3. Full-bleed layout: no padding, placeholder view fills entire area
4. Pressing `1`–`4` switches the placeholder text (confirming view switching works)
5. Tier selector visible on right edge with pill layout
6. `?` opens shortcut overlay
7. `Escape` closes overlay
8. `[`/`]` changes highlighted tier in selector

Verification conditions: Run `npm run dev` and navigate to Observatory page.

## Test Targets
- New tests (~8 Vitest):
  - `test_observatory_route_registered` — route exists
  - `test_keyboard_view_switching` — pressing 1-4 changes view state
  - `test_keyboard_tier_navigation` — [ and ] change tier
  - `test_keyboard_escape_deselects` — Escape clears selection
  - `test_keyboard_inactive_when_input_focused` — shortcuts don't fire when typing
  - `test_tier_selector_renders_all_tiers` — 7 tier pills present
  - `test_detail_panel_opens_on_selection` — selecting symbol opens panel
  - `test_shortcut_overlay_toggles` — ? key toggles overlay
- Minimum: 8
- Test command: `cd argus/ui && npx vitest run src/features/observatory/`

## Definition of Done
- [ ] Observatory page renders at /observatory
- [ ] Full-bleed layout (no card grid)
- [ ] Keyboard shortcuts functional (1-4, [, ], Escape, ?)
- [ ] Tier selector with 7 pills
- [ ] Detail panel zone (placeholder) slides in/out
- [ ] Shortcut overlay toggles
- [ ] Navigation updated with Observatory
- [ ] Lazy-loaded via React.lazy
- [ ] All existing tests pass
- [ ] 8+ new tests written and passing
- [ ] Close-out report written to `docs/sprints/sprint-25/session-3-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All existing pages still accessible | Navigate to each page in browser |
| No existing components modified | `git diff --name-only` only shows new files + nav/router |
| Sidebar nav order correct | Visual check |

## Close-Out
Follow close-out skill. Write to: `docs/sprints/sprint-25/session-3-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide @reviewer with:
1. Review context: `docs/sprints/sprint-25/review-context.md`
2. Close-out: `docs/sprints/sprint-25/session-3-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command: `cd argus/ui && npx vitest run src/features/observatory/`
5. Do not modify: existing page components, existing hooks

Write review to: `docs/sprints/sprint-25/session-3-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify keyboard hook only fires when Observatory page is focused
2. Verify Tab preventDefault doesn't break accessibility outside Observatory
3. Verify React.lazy used for code-splitting
4. Verify Framer Motion used for panel animation (not CSS transitions)
5. Verify no new npm packages installed
6. Verify full-bleed layout (no Card wrappers, no grid)

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-25/regression-checklist.md`

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-25/escalation-criteria.md`
