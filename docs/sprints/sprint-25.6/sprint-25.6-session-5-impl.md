# Sprint 25.6, Session 5: Dashboard Layout Restructure (DEF-072)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/ui/src/pages/DashboardPage.tsx`
   - Search for dashboard components: `grep -rn "import.*from.*components\|import.*from.*features" argus/ui/src/pages/DashboardPage.tsx`
   - Read the component files imported by DashboardPage to understand current card structure
   - `argus/ui/src/components/Card.tsx` (if exists — understand card wrapper)
2. Run scoped test baseline:
   ```
   cd argus/ui && npx vitest run src/pages/DashboardPage
   ```
   Expected: all passing
3. Verify Sessions 1–4 are committed.

## Objective
Restructure the Dashboard page layout to promote the Positions card above the fold on 1080p desktop displays. Currently, three full card rows push Positions below the visible viewport, requiring scrolling during active trading sessions.

## Requirements

### 1. Restructure card order
Current layout (top to bottom):
- Row 1: Account Equity | Daily P&L | Monthly Goal
- Row 2: Market Status | Today's Stats | Session Timeline
- Row 3: AI Insight | Universe | Signal Quality
- Positions (below fold)
- Recent Trades | System Status

New layout:
- Row 1: Account Equity | Daily P&L | Monthly Goal (unchanged)
- Row 2: Positions (promoted — full width or appropriate width for the table)
- Row 3: Today's Stats + Session Timeline (merge or compact) | AI Insight (condensed)
- Row 4: Recent Trades | System Status
- Below fold: Universe, Signal Quality (review-oriented, not real-time)

### 2. Eliminate or absorb Market Status card
The Market Status card shows: market open/closed status, time, regime badge, and "Regime data unavailable" text. This is largely redundant with the top status bar (which already shows regime badge). Options:
- Remove Market Status card entirely (status bar covers it)
- Merge the regime detail text into the Session Timeline card
- Choose whichever produces cleaner layout

### 3. Condense AI Insight card (optional if space allows)
If the AI Insight card's paragraph text makes Row 3 too tall:
- Make the card collapsible (show title + "Mid-Morning Range-Bound Assessment" only, click to expand)
- Or cap the height with overflow scroll
- If it fits naturally in the new layout, leave it as-is

### 4. Ensure Positions visibility
The key acceptance criterion: on a 1080p display (1920×1080), the Positions card must be fully visible without scrolling when the page first loads. The financial scoreboard (Row 1) and Positions (Row 2) should both be visible in the initial viewport.

## Constraints
- Do NOT modify card component internals (data sources, API calls, calculations)
- Do NOT modify backend API endpoints
- Do NOT change: any Python file
- Preserve all existing cards — reorder and optionally merge/condense, but don't remove data
- Mobile/tablet layout is out of scope (desktop only for this sprint)

## Test Targets
- Existing tests: all must still pass
- New tests:
  1. Test that DashboardPage renders Positions component before Universe/Signal Quality in DOM order
  2. Test that all expected cards are still rendered (no missing components)
- Minimum new test count: 2
- Test command: `cd argus/ui && npx vitest run src/pages/DashboardPage`

## Visual Review
The developer should visually verify:
1. **Positions visible without scrolling** on 1080p desktop viewport
2. **Financial scoreboard** (Account Equity / Daily P&L / Monthly Goal) still in Row 1
3. **All cards render** with correct data — no missing or broken cards
4. **No console errors** in browser dev tools
5. **Universe and Signal Quality** still accessible below fold

Verification conditions: App running with existing data from March 19 session, desktop browser at 1920×1080.

## Definition of Done
- [ ] Positions card visible without scrolling on 1080p
- [ ] All existing cards still render with correct data
- [ ] Market Status card eliminated or merged
- [ ] All existing tests pass
- [ ] 2+ new Vitest tests
- [ ] `npx tsc --noEmit` clean
- [ ] Close-out report written to `docs/sprints/sprint-25.6/session-5-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All dashboard cards render | Visual check — no blank spaces or errors |
| Positions data correct | Compare open/closed counts with Trades page |
| Account equity displays | Value matches status bar |
| System Status shows all components | All 15+ health components listed |
| TypeScript clean | `npx tsc --noEmit` |

## Close-Out
Follow the close-out skill in `.claude/skills/close-out.md`.
**Write to:** `docs/sprints/sprint-25.6/session-5-closeout.md`

## Tier 2 Review (Mandatory — @reviewer Subagent)
Provide:
1. Review context file: `docs/sprints/sprint-25.6/review-context.md`
2. Close-out report: `docs/sprints/sprint-25.6/session-5-closeout.md`
3. Diff range: `git diff HEAD~1`
4. Test command (FINAL session — full suite): `cd argus/ui && npx vitest run`
5. Files that should NOT have been modified: any backend Python file

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS, follow the fix documentation procedure.

## Session-Specific Review Focus (for @reviewer)
1. Verify Positions component is rendered above Universe and Signal Quality in DOM order
2. Verify no card was removed entirely (all data still accessible)
3. Verify no backend files were modified
4. Verify no console errors in test output

## Sprint-Level Regression Checklist
(See review-context.md)

## Sprint-Level Escalation Criteria
(See review-context.md)
