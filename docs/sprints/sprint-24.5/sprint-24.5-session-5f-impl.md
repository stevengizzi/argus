# Sprint 24.5, Session S5f: Visual Review Fixes + Decision Stream 404

## Context
This is the contingency session for visual review fixes identified during live QA of
the Orchestrator page after Session 5. It addresses four issues: one integration bug
(404 on decision stream), one CSS alignment issue in the 3-column section, one CSS
consistency issue in the strategy cards, and one minor padding fix on the decision
stream dropdown.

**Execution mode:** Human-in-the-loop
**Blocks:** S6 (independent, not blocked — but this should complete first for clean
git history)

## Pre-Flight Checks
Before making any changes:
1. Run the frontend test suite:
   ```bash
   cd argus/ui && npx vitest run
   ```
   Expected: 520 tests, all passing
2. Verify git is clean: `git status`
3. Read the affected files:
   - `argus/ui/src/pages/OrchestratorPage.tsx`
   - `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx`
   - `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx`
   - `argus/ui/src/hooks/useStrategyDecisions.ts`
   - `argus/api/routes/strategies.py` (read only — to understand the strategy ID
     format the backend expects)

## Fix 1: Decision Stream 404 — Strategy ID Mismatch (MEDIUM)

**Symptom:** Clicking "View Decisions" on a strategy card opens the slide-out panel,
which shows "Failed to load decisions: Not Found" with a 404 error. The panel title
shows `VWAP_RECLAIM`.

**Diagnosis step (do this first):**
1. Check what strategy IDs the Orchestrator page passes to `onViewDecisions`. These
   likely come from the strategy operations data (e.g., `strategy.id` or
   `strategy.strategy_id`).
2. Check what IDs the backend strategy registry uses. Look at how
   `GET /api/v1/strategies/{strategy_id}/decisions` resolves the strategy — it
   calls `app_state.strategies.get(strategy_id)` or similar.
3. Identify the mismatch. Common possibilities:
   - Frontend passes `VWAP_RECLAIM` but backend expects `vwap_reclaim`
   - Frontend passes a display name but backend expects the strategy class ID
   - Frontend passes an enum value but backend expects a different key format

**Fix:** Align the strategy ID used in the `useStrategyDecisions` hook query with
what the backend expects. The fix should be on the frontend side (map the card's
strategy identifier to the backend's expected format) unless the backend format is
clearly wrong. Document the ID format in a code comment.

**If the IDs genuinely match and the issue is something else** (e.g., the strategies
dict isn't populated in dev mode, or the endpoint path is wrong), fix whatever the
actual root cause is and document it in the close-out.

## Fix 2: 3-Column Section Container Alignment (LOW)

**Symptom:** In the 3-column grid below the strategy cards (Decision Log, Catalyst
Alerts, Recent Signals), the container body areas start at different y-values. The
Recent Signals container starts lower because it has a "10 scored" sub-header line
below the section title. The other two containers have no sub-header and start
immediately.

**Fix:** Ensure all three column containers have their content areas aligned at the
same vertical position regardless of whether they have sub-headers. Options:
- Give all three columns a consistent top structure (e.g., a fixed-height header
  area that accommodates sub-headers, with empty space if no sub-header)
- Use CSS `items-start` with a min-height on the header area
- Add an invisible spacer to columns without sub-headers

The key constraint: the section headers ("DECISION LOG", "CATALYST ALERTS",
"RECENT SIGNALS") must remain aligned on the same baseline (they already are).
The fix is only for the container content below the headers.

## Fix 3: Strategy Card Height Consistency (LOW)

**Symptom:** The 4 strategy operations cards render in a 2×2 grid, but the bottom
row is taller than the top row. This happens because ORB Scalp (bottom-left) has
throttle override information (the orange "reduce" banner, Sharpe, DD, and Override
button) that adds vertical content.

**Fix:** Standardize strategy card heights so all cards in the grid have consistent
proportions. Options:
- Set a `min-h` on the card container so all cards match the tallest card's height,
  with content aligned to the top
- Use CSS grid `grid-rows-subgrid` or explicit row heights
- Use `items-stretch` on the grid (may already be there) plus internal flex layout
  to push the footer (time window + status) to the bottom of each card

The goal is that cards without throttle info don't look squat compared to cards with
it. The time window and status indicator at the bottom of each card should sit at the
same y-position across all cards in a row, and ideally across all cards in the grid.

## Fix 4: Symbol Filter Dropdown Padding (LOW)

**Symptom:** In the Decision Stream slide-out panel, the "All symbols" dropdown
(`<select>`) has insufficient right padding between the dropdown arrow/chevron and
the right border of the element.

**Fix:** Add right padding to the select element. Something like `pr-8` or `pr-10`
(Tailwind) to give the browser's native dropdown arrow breathing room. If the
component uses a custom chevron, adjust the padding accordingly.

## Constraints
- Do NOT modify any backend Python files (diagnosis reads are fine)
- Do NOT modify: `argus/core/events.py`, `argus/main.py`,
  `argus/api/websocket/live.py`, `argus/core/orchestrator.py`,
  `argus/execution/order_manager.py`, `argus/core/risk_manager.py`
- Do NOT change the slide-out panel mechanics (AnimatePresence, backdrop, open/close)
- Do NOT restructure the 3-column grid into a different layout
- Do NOT remove or reorder strategy cards
- Keep the change surface minimal — these are CSS/wiring fixes, not redesigns

## Affected Files
| File | Expected Change |
|------|----------------|
| `argus/ui/src/pages/OrchestratorPage.tsx` | Fix 2 (column alignment), Fix 3 (card grid), possibly Fix 1 (ID mapping) |
| `argus/ui/src/features/orchestrator/StrategyOperationsCard.tsx` | Fix 3 (card internal layout) |
| `argus/ui/src/features/orchestrator/StrategyDecisionStream.tsx` | Fix 4 (dropdown padding) |
| `argus/ui/src/hooks/useStrategyDecisions.ts` | Possibly Fix 1 (ID transformation) |
| `argus/ui/src/api/client.ts` | Possibly Fix 1 (if the URL path needs adjustment) |

## Test Targets
After implementation:
- All existing Vitest tests must still pass (520+)
- Minimum 1 new test: verify strategy ID mapping produces the correct API path
  (if Fix 1 involved a transformation)
- Test command: `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Decision Stream loads events for at least one strategy (no more 404)
- [ ] 3-column section containers start at the same y-value
- [ ] Strategy cards have consistent heights across the grid
- [ ] Symbol filter dropdown has adequate right padding
- [ ] All existing tests pass
- [ ] `npx tsc --noEmit` clean
- [ ] No backend files modified

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Fix 1: Decision stream loads | Open panel for any strategy — events appear or empty state (no 404) |
| Fix 2: Columns aligned | Visual check — all 3 container bodies start at same y-value |
| Fix 3: Cards consistent | Visual check — all 4 cards same height, footer aligned |
| Fix 4: Dropdown spacing | Visual check — chevron has breathing room |
| 3-column layout preserved | Section 4 still has 3 columns at lg breakpoint |
| Slide-out mechanics unchanged | Panel still slides in/out with animation, backdrop closes |
| No backend changes | `git diff --name-only` shows only ui/ files |

## Sprint-Level Escalation Criteria
| Criterion | Action |
|-----------|--------|
| Frontend 3-column layout structurally broken | HALT |
| Existing orchestrator component tests break | HALT |
| TypeScript build errors outside scope | HALT |

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include the structured JSON appendix.

For Fix 1, include the diagnosis findings in the close-out notes — document what the
ID mismatch was and how it was resolved.

**Write the close-out report to a file:**
docs/sprints/sprint-24.5/session-5f-closeout.md

## Tier 2 Review (Mandatory — @reviewer Subagent)
1. Review context: `docs/sprints/sprint-24.5/review-context.md`
2. Close-out: `docs/sprints/sprint-24.5/session-5f-closeout.md`
3. Diff: `git diff HEAD~1`
4. Test command (scoped, non-final): `cd argus/ui && npx vitest run src/features/orchestrator/ src/pages/`
5. Files NOT to modify: `StrategyDecisionStream.tsx` (S4 output), backend files