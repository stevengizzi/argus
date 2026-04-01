# Sprint 32.5, Session 7: DEF-131 Experiments Dashboard

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - Router/navigation config (find the file that defines page routes and nav entries — likely `App.tsx` or a router config file)
   - An existing page component for structural reference (e.g., Observatory or Performance page)
   - Existing hooks patterns (one TanStack Query hook file for reference)
   - `argus/api/routes/experiments.py` (the variants and promotions endpoints from S5 — read response shapes)
   - Keyboard shortcut configuration (find where 1-8 shortcuts are defined)
2. Run the scoped test baseline (DEC-328):
   ```
   cd /Users/stevengizzi/argus/argus/ui && npx vitest run --reporter=verbose 2>&1 | head -100
   ```
   Expected: ~704+ passing (S6 additions included, 1 pre-existing failure)
3. Verify you are on branch: `main` (S6/S6f merged)
4. Create working branch: `git checkout -b sprint-32.5-session-7`

## Objective
Build the 9th Command Center page: Experiments Dashboard. Shows variant status table, promotion event log, and basic pattern-level variant comparison. This is the operational window into the experiment pipeline.

## Requirements

1. **Create TanStack Query hooks (`useExperiments.ts` or similar):**
   - `useExperimentVariants()` — fetches from `GET /api/v1/experiments/variants`
   - `usePromotionEvents()` — fetches from `GET /api/v1/experiments/promotions`
   - Follow existing hook patterns (staleTime, error handling, refetchInterval)
   - Define TypeScript interfaces: `ExperimentVariant`, `PromotionEvent`

2. **Create ExperimentsPage component:**
   - **Variant Status Table:** main section showing all variants
     - Columns: Pattern, Variant ID (abbreviated), Fingerprint (abbreviated), Mode (Live/Shadow badge), Trade Count, Shadow Trade Count, Win Rate, Expectancy, Sharpe
     - Mode badge: green for LIVE, gray/muted for SHADOW
     - Sortable by key metrics (click column header)
     - Group by pattern name (collapsible sections or visual separator)
   - **Promotion Event Log:** chronological list of promotion/demotion events
     - Each entry: timestamp, variant identifier, event type (↑ Promoted / ↓ Demoted badge), from_mode → to_mode, trigger reason
     - Most recent at top
     - Limit to last 50 events with "load more" or scroll
   - **Pattern Comparison:** when clicking a pattern group header (or a dedicated "Compare" action), show side-by-side metrics for all variants of that pattern
     - Highlight the variant with best Sharpe, best win rate (or use subtle indicators)
   - **Disabled State:** when `experiments.enabled=false`, show a clear disabled message: "Experiment pipeline is not enabled. Enable in config/experiments.yaml to start running parameter sweeps."
   - **Empty State:** when enabled but no experiments/variants exist: "No experiments have been run yet. Use `scripts/run_experiment.py` to run your first parameter sweep."

3. **Integrate into navigation:**
   - Add 9th page route
   - Add nav entry with appropriate icon (e.g., beaker/flask icon from lucide-react)
   - Assign keyboard shortcut: `9` (following 1-8 pattern for existing pages)
   - Page title: "Experiments"

4. **Visual design:**
   - Follow existing page layout patterns (consistent header, content area, spacing)
   - Lazy-load the page component (React.lazy, same as Observatory)
   - Use Recharts for any charts (e.g., small sparkline of variant performance if data available) — but charts are stretch, table is priority
   - Tailwind CSS v4

## Constraints
- Do NOT modify: any backend files
- Do NOT modify: existing 8 pages (only add new page)
- Do NOT modify: existing keyboard shortcuts for pages 1-8
- Do NOT add: parameter heatmap (deferred), experiment runner trigger (CLI only), variant promote/demote buttons (read-only)
- Lazy-load the page component to avoid impacting bundle size of other pages

## Test Targets
After implementation:
- Existing Vitest: all must still pass
- New tests to write:
  1. **ExperimentsPage renders:** component mounts without error
  2. **Empty state:** no data → empty state message
  3. **Disabled state:** experiments.enabled=false → disabled message
  4. **Navigation:** page accessible via route, nav entry present
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run`

## Visual Review
The developer should visually verify the following after this session:

1. **Navigation:** 9th page appears in nav bar with icon. Keyboard shortcut `9` navigates to it.
2. **Variant table (with data):** If variants exist, table displays with correct columns. Mode badges colored. Grouping by pattern visible.
3. **Variant table (empty):** Empty state message displays cleanly.
4. **Disabled state:** With experiments.enabled=false, disabled message shown.
5. **Promotion log:** If promotion events exist, chronological list with event type badges.
6. **Promotion log (empty):** Clean empty state.
7. **Pattern comparison:** Clicking a pattern group shows side-by-side variant metrics.
8. **Existing pages:** Navigate to all 8 existing pages — verify no regressions. Shortcuts 1-8 still work.

Verification conditions:
- App running with backend
- Test both with experiments.enabled=true (with/without data) and experiments.enabled=false

## Definition of Done
- [ ] useExperimentVariants and usePromotionEvents hooks created
- [ ] ExperimentsPage component with variant table, promotion log, comparison
- [ ] Empty state and disabled state handled
- [ ] Page added to router and navigation
- [ ] Keyboard shortcut `9` works
- [ ] Page lazy-loaded
- [ ] Existing 8 pages unaffected
- [ ] All existing Vitest pass
- [ ] 4+ new Vitest written and passing
- [ ] Visual review items documented
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 8 existing pages load | Navigate to each |
| Keyboard shortcuts 1-8 unchanged | Test each shortcut |
| Page transitions work | Navigate between pages |
| Bundle size not inflated | React.lazy confirmed on new page |

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-7-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-7-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command: `cd argus/ui && npx vitest run`
5. Files NOT modified: any backend files, existing 8 page components

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify no existing page components were modified
2. Verify keyboard shortcuts 1-8 unchanged, 9 added cleanly
3. Verify page is lazy-loaded (React.lazy + Suspense)
4. Verify hooks follow existing TanStack Query patterns
5. Verify TypeScript types match S5 API response shapes
6. Verify disabled state correctly detects experiments.enabled setting
7. Verify no promote/demote/trigger buttons added (read-only page)

## Sprint-Level Regression Checklist (for @reviewer)

### Navigation and Routing
- [ ] All 8 existing pages accessible
- [ ] Keyboard shortcuts for existing pages unchanged
- [ ] 9th page accessible via nav and shortcut
- [ ] Page transitions work
- [ ] Deep linking to existing pages unbroken

### Config Gating
- [ ] experiments.enabled=false → Experiments page shows disabled state

### Test Suite Health
- [ ] All pre-existing Vitest pass
- [ ] All pre-existing pytest pass

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. 9th page navigation breaks keyboard shortcut scheme

### Scope Reduction Triggers
1. Frontend session exceeds 13 compaction after fixes → split
