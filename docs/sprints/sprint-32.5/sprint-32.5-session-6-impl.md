# Sprint 32.5, Session 6: DEF-131 Shadow Trades UI

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - The Trade Log page component (find under `argus/ui/src/pages/` — likely `trades/` directory)
   - Existing trade hooks (TanStack Query patterns — find under `argus/ui/src/hooks/`)
   - API type definitions (find trade-related types)
   - `argus/api/routes/counterfactual.py` (the positions endpoint from S5 — read response shape)
2. Run the scoped test baseline (DEC-328):
   ```
   cd /Users/stevengizzi/argus/argus/ui && npx vitest run --reporter=verbose 2>&1 | head -100
   ```
   Expected: ~700+ passing (1 pre-existing failure)
3. Verify you are on branch: `main` (S5 merged)
4. Create working branch: `git checkout -b sprint-32.5-session-6`

## Objective
Add a Shadow Trades tab to the existing Trade Log page that displays counterfactual/shadow positions from the CounterfactualTracker, showing rejection metadata, theoretical P&L, R-multiples, and MFE/MAE data.

## Requirements

1. **Create TanStack Query hook (`useShadowTrades.ts` or similar):**
   - Fetch from `GET /api/v1/counterfactual/positions`
   - Support query params: strategy_id, date_from, date_to, rejection_stage
   - Pagination via limit/offset
   - Follow existing hook patterns (staleTime, refetchInterval, error handling)
   - Return typed data (define ShadowTrade interface)

2. **Create ShadowTradesTab component:**
   - Table displaying shadow positions with columns: Symbol, Strategy, Variant (nullable), Entry Time, Entry Price, Exit Price, Theoretical P&L (colored green/red), R-Multiple, MFE (R), MAE (R), Rejection Stage, Rejection Reason, Quality Grade
   - Filter bar: strategy selector, date range picker, rejection stage selector
   - Summary stats row at top: total shadow trades, win rate, avg theoretical P&L, avg R-multiple (computed client-side from loaded data)
   - Empty state: "No shadow trades recorded yet. Shadow trades appear when signals are rejected by the quality filter, position sizer, or risk manager."
   - Pagination controls at bottom

3. **Integrate into Trade Log page:**
   - Add a tab bar/toggle at the top: "Live Trades" | "Shadow Trades"
   - Default to "Live Trades" tab (existing behavior unchanged)
   - Shadow Trades tab loads ShadowTradesTab component
   - Tab state managed locally (not in URL — keep it simple)

4. **Visual design:**
   - Shadow trades should be visually distinct from live trades — use a muted/ghost styling (lower opacity, different accent color, or subtle background tint)
   - Rejection stage badges: color-code by stage (QUALITY_FILTER, POSITION_SIZER, RISK_MANAGER, SHADOW, BROKER_OVERFLOW)
   - Quality grade badges: reuse existing GRADE_COLORS from shared constants
   - P&L coloring: green for positive, red for negative (existing pattern)

## Constraints
- Do NOT modify: existing Trade Log table/data/filtering logic for live trades
- Do NOT modify: any backend files
- Do NOT modify: existing trade hooks or trade type definitions (only ADD new types)
- Do NOT modify: navigation/routing config (Trade Log page already exists)
- Follow existing component patterns: Tailwind CSS v4, TanStack Query, functional components

## Test Targets
After implementation:
- Existing Vitest: all must still pass
- New tests to write:
  1. **ShadowTradesTab renders:** component mounts without error
  2. **Empty state:** no data → empty state message displayed
  3. **Data display:** mock data → table rows rendered with correct columns
  4. **Tab switching:** Live Trades ↔ Shadow Trades tabs work
- Minimum new test count: 4
- Test command: `cd argus/ui && npx vitest run`

## Visual Review
The developer should visually verify the following after this session:

1. **Tab bar:** Trade Log page shows "Live Trades" and "Shadow Trades" tabs. Default is "Live Trades". Clicking "Shadow Trades" switches content.
2. **Shadow table (with data):** If counterfactual data exists, rows display with muted/ghost styling distinct from live trades. All columns present and readable.
3. **Shadow table (empty):** If no counterfactual data, empty state message displays cleanly.
4. **Rejection badges:** Rejection stage shows as colored badge.
5. **Quality grades:** Grade badges use existing GRADE_COLORS.
6. **P&L coloring:** Green for positive, red for negative theoretical P&L.
7. **Live trades unchanged:** Switching back to "Live Trades" tab shows existing trades with no visual changes.

Verification conditions:
- App running with paper trading backend (IBKR paper or simulated)
- If no real shadow data, verify empty state. If shadow data exists from prior sessions, verify data display.

## Definition of Done
- [ ] useShadowTrades hook created with TanStack Query
- [ ] ShadowTradesTab component created with table, filters, summary stats
- [ ] Tab bar added to Trade Log page
- [ ] Empty state handled
- [ ] Shadow trades visually distinct from live trades
- [ ] Existing Trade Log unchanged
- [ ] All existing Vitest pass
- [ ] 4+ new Vitest written and passing
- [ ] Visual review items documented
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Trade Log live trades display unchanged | Visual inspection + existing tests |
| Trade filtering unchanged | Existing tests |
| Trade detail panel unchanged | Visual inspection |
| No new backend requests on "Live Trades" tab | Network tab in browser devtools |

## Close-Out
Follow .claude/skills/close-out.md.
**Write to:** docs/sprints/sprint-32.5/session-6-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide the @reviewer with:
1. Review context: `docs/sprints/sprint-32.5/review-context.md`
2. Close-out: `docs/sprints/sprint-32.5/session-6-closeout.md`
3. Diff: `git diff main...HEAD`
4. Test command: `cd argus/ui && npx vitest run`
5. Files NOT modified: any backend files, existing trade hooks, navigation/routing config

## Post-Review Fix Documentation
If CONCERNS, update both close-out and review files per protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify existing Trade Log component logic untouched (tab is purely additive)
2. Verify hook follows existing TanStack Query patterns (staleTime, error handling)
3. Verify ShadowTrade type matches the API response from S5's endpoint
4. Verify empty state message is user-friendly (not technical error)
5. Verify no shadow-related API calls fire when on "Live Trades" tab (lazy loading)

## Sprint-Level Regression Checklist (for @reviewer)

### Trade Log Functionality
- [ ] Existing trades display correctly
- [ ] Filtering works
- [ ] Detail panel works
- [ ] Loads without error when no shadow trades exist

### Navigation and Routing
- [ ] All 8 existing pages accessible
- [ ] Keyboard shortcuts unchanged

### Config Gating
- [ ] experiments.enabled=false → Shadow Trades tab still shows counterfactual data

### Test Suite Health
- [ ] All pre-existing Vitest pass (700 baseline, 1 known failure)
- [ ] All pre-existing pytest pass

## Sprint-Level Escalation Criteria (for @reviewer)

### Tier 3 Triggers
1. Trade Log tab breaks existing page architecture
2. 9th page navigation breaks keyboard shortcut scheme

### Scope Reduction Triggers
1. Frontend session exceeds 13 compaction after fixes → split
