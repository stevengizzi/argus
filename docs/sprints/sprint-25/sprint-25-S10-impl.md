# Sprint 25, Session 10: Integration Polish + Keyboard Refinement

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-spec.md` (full keyboard shortcut spec, acceptance criteria)
   - `docs/sprints/sprint-25/spec-by-contradiction.md` (scope boundaries)
   - All Observatory components (full directory scan of `argus/ui/src/features/observatory/`)
2. Run FULL test suite (DEC-328 — this is the final session):
   `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
   Expected: ~2,793+ tests (baseline 2,768 + S1/S2 additions)
   `cd argus/ui && npx vitest run`
   Expected: ~590+ tests (baseline 523 + S3–S9 additions)
3. Verify you are on the correct branch

## Objective
End-to-end integration testing and polish of the entire Observatory page. Fix keyboard edge cases, ensure smooth transitions between all views, verify all loading/error/empty states render correctly, and confirm the complete keyboard-first workflow functions without mouse.

## Requirements

1. **Keyboard flow — complete walkthrough and fixes:**
   Test this exact sequence and fix any issues discovered:
   a. Navigate to Observatory via sidebar
   b. Press `2` → Matrix view loads
   c. Press `]` three times → tier selector advances through Viable → Routed → Evaluating
   d. Matrix shows symbols for Evaluating tier
   e. Press `Tab` × 3 → highlights 3rd row
   f. Press `Enter` → detail panel slides open with that symbol
   g. Press `Tab` → highlight moves to 4th row, detail panel updates (no close/reopen)
   h. Press `1` → switches to Funnel view, detail panel stays open with same symbol
   i. Press `4` → camera smoothly transitions to Radar view
   j. Press `Escape` → detail panel closes, symbol deselected
   k. Press `1` → camera smoothly transitions back to Funnel
   l. Press `3` → Timeline view
   m. Press `/` → search overlay opens
   n. Press `Escape` → search closes
   o. Press `?` → shortcut overlay opens
   p. Press `?` or `Escape` → shortcut overlay closes
   q. All above without touching the mouse

   Fix any issues: timing problems, focus management, state leaks between views, animation glitches.

2. **Loading states:**
   - When data is fetching: show skeleton loaders (not spinners) for Matrix rows, Timeline lanes, Vitals metrics
   - Funnel/Radar: show empty tier discs (no particles) while loading, then particles fade in
   - Detail panel: show section skeletons while data loads

3. **Error states:**
   - When API endpoints fail: show unobtrusive error message in the affected view (not a full-page error)
   - When WebSocket disconnects: Vitals bar shows "Disconnected" with reconnecting indicator
   - When a specific hook fails: other hooks still function (no cascading failure)

4. **Empty states:**
   - Zero symbols at selected tier: Matrix shows centered "No symbols at [tier name]" message
   - No evaluation data yet (pre-market): all views show appropriate "Awaiting market data" or "Market opens at 9:30 AM ET"
   - Debrief mode with no data for selected date: "No data for [date]"

5. **Transition smoothness:**
   - View switching (`1`–`4`): verify no flash of unstyled content between views
   - Detail panel open/close: Framer Motion animation smooth, no jank
   - Funnel ↔ Radar camera transition: verify smooth lerp, no position jumps
   - Matrix sort updates: rows reorder without visible flicker

6. **Accessibility basics:**
   - Tab trap prevention: ensure `Tab` in Observatory doesn't trap keyboard focus forever — `Escape` from Observatory should allow normal browser Tab behavior to resume
   - All interactive elements reachable via keyboard
   - Sufficient color contrast on condition cells (not just color — consider adding pass/fail icons or text for color-blind accessibility)

## Constraints
- Do NOT add new features — this session is exclusively for polish and fixes
- Do NOT modify backend endpoints
- Keep changes minimal and targeted — fix only what's broken or rough, don't refactor working code

## Visual Review
The developer should perform a full walkthrough of the keyboard sequence above, plus:
1. Verify all 4 views render correctly with dev data
2. Verify detail panel works in all 4 views
3. Verify debrief mode works with a past date
4. Verify return to live mode
5. Verify all loading/error/empty states look correct
6. Verify no visual glitches on rapid view switching
7. **Final performance check:** Funnel with 3,000+ particles at 30+ fps

Verification: Full walkthrough in `npm run dev` mode.

## Test Targets
- New tests (~6 Vitest — integration level):
  - `test_keyboard_full_flow_no_errors` — simulate the keyboard sequence above, no uncaught exceptions
  - `test_view_switch_preserves_selection` — selecting a symbol, switching views, symbol still selected
  - `test_detail_panel_persists_across_views` — panel stays open through 1→2→3→4 view switches
  - `test_escape_closes_overlays_then_panel` — Escape priority: search overlay > shortcut overlay > detail panel
  - `test_empty_state_renders` — render with no data, no crash
  - `test_error_state_renders` — mock API failure, error message shown, no crash
- Minimum: 6
- Test command (FINAL SESSION — full suite):
  `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
  `cd argus/ui && npx vitest run`

## Definition of Done
- [ ] Complete keyboard walkthrough works without mouse
- [ ] All loading states render skeletons
- [ ] All error states handled gracefully
- [ ] All empty states show appropriate messages
- [ ] View transitions smooth (no flicker, no jumps)
- [ ] Detail panel persists across view switches
- [ ] Escape priority chain correct (overlays > panel)
- [ ] Performance: 30+ fps in Funnel with 3,000+ particles
- [ ] ALL pytest pass (full suite)
- [ ] ALL Vitest pass (full suite)
- [ ] 6+ new integration tests
- [ ] Close-out: `docs/sprints/sprint-25/session-10-closeout.md`
- [ ] Tier 2 review via @reviewer → `docs/sprints/sprint-25/session-10-review.md`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| All 7 existing pages still work | Navigate to each in browser |
| AI Copilot still functional | Send test message |
| No trading pipeline files touched | `git diff --name-only` check |
| Test count increased (not decreased) | Compare final counts to baseline |

## Close-Out
Follow close-out skill. Write to: `docs/sprints/sprint-25/session-10-closeout.md`

**This is the final session.** The close-out should include:
- Sprint-level test count summary (before/after)
- Full list of new files created across all sessions
- All DEC entries logged during the sprint
- Any DEF items created
- Sprint verdict recommendation

## Tier 2 Review (Mandatory — @reviewer Subagent)
This is the final session — the @reviewer runs the FULL test suite:
1. Review context: `docs/sprints/sprint-25/review-context.md`
2. Close-out: `docs/sprints/sprint-25/session-10-closeout.md`
3. Diff: `git diff HEAD~1` (or full sprint diff if more useful)
4. Test command: FULL SUITE
   `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q`
   `cd argus/ui && npx vitest run`
5. Do not modify: all trading pipeline files per regression checklist

Write review to: `docs/sprints/sprint-25/session-10-review.md`

## Session-Specific Review Focus (for @reviewer)
1. Verify complete keyboard flow works (test the full sequence from requirements)
2. Verify no trading pipeline files were modified across the ENTIRE sprint
3. Verify Three.js code-split (not in main bundle)
4. Verify test count increased from baseline
5. Verify all 4 views render, all transitions smooth
6. Verify Observatory page does not affect other page performance

## Sprint-Level Regression Checklist (for @reviewer)
See `docs/sprints/sprint-25/regression-checklist.md` — **check ALL items for final session**

## Sprint-Level Escalation Criteria (for @reviewer)
See `docs/sprints/sprint-25/escalation-criteria.md`
