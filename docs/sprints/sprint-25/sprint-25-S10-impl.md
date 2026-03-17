# Sprint 25, Session 10: Integration Polish

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-25/sprint-25-spec.md`
   - `docs/sprints/sprint-25/review-context.md`
   - `CLAUDE.md`
2. Run the full test baseline (DEC-328 — final session of sprint):
   ```
   python -m pytest tests/ --ignore=tests/test_main.py -n auto -q
   ```
   Expected: ~2,765 pytest tests, all passing
   ```
   cd argus/ui && npx vitest run
   ```
   Expected: ~597 Vitest tests, all passing
3. Verify you are on the correct branch: `main` or `sprint-25`
4. Run TypeScript check: `cd argus/ui && npx tsc --noEmit`
   Note: There are 2 pre-existing errors in ObservatoryLayout.tsx (unused
   `VIEW_LABELS` and `currentView`). These are addressed in Requirement 15 below.

## Objective
Address all review findings accumulated across Sessions 1–9 of Sprint 25. This
is a polish-only session: no new features, no new endpoints, no new components.
Every change either fixes a code quality issue, removes dead code, resolves a
behavioral concern, or tightens type safety.

## Requirements

Work through these in priority order. Each is independent — if one proves
unexpectedly complex, skip it and note the skip in the close-out.

### Priority 1: Behavioral Fix (MEDIUM finding)

**1. Unify Tab handler in Matrix view (S5b-F1)**

In `argus/ui/src/features/observatory/views/MatrixView.tsx`:
The page-level `useObservatoryKeyboard` and MatrixView both register `window`
keydown handlers for Tab, updating separate state (`selectedSymbol` vs
`highlightedSymbol`). These can drift out of sync.

Fix: When the Matrix view is active and its own Tab handler fires, it should
ALSO call `onSelectSymbol(nextSymbol)` so the detail panel stays in sync with
the visual highlight. This way Tab in Matrix simultaneously highlights the row
AND opens/updates the detail panel. Remove or guard the page-level Tab handler
so it doesn't double-fire when Matrix is active — the cleanest approach is to
have `useObservatoryKeyboard` accept an `isMatrixActive` flag and skip its own
Tab handling when true.

Verify: Tab in Matrix view should highlight a row AND show that symbol in the
detail panel. Shift+Tab should do the same in reverse.

### Priority 2: Backend Code Quality (S1 findings)

**2. Add public query method on EvaluationEventStore (S1 F-001)**

In `argus/analytics/observatory_service.py`:
`ObservatoryService` accesses `self._store._conn` directly (private attribute).

Fix: Add a public `async def execute_query(self, sql: str, params: tuple) -> list`
method (or similar) on `EvaluationEventStore` (in `argus/strategies/base.py` or
wherever the store class lives). Then update `ObservatoryService` to use the
public method instead of reaching into `_conn`.

Read the `EvaluationEventStore` class first to understand its interface before
deciding on the exact method signature.

**3. Replace `datetime.utcnow()` (S1 F-002)**

In `argus/api/routes/observatory.py` (line ~151):
Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` (or
`datetime.now(UTC)` with the appropriate import). This aligns with the project
standard and avoids the Python 3.12 deprecation.

**4. Narrow ConditionDetail typing (S1 F-003)**

In `argus/api/routes/observatory.py` (lines ~50-51):
Change `ConditionDetail.actual_value` and `required_value` from `object | None`
to `float | str | bool | None`.

**5. Remove unused `reason` column from journey SQL (S1 F-005)**

In `argus/analytics/observatory_service.py`, `get_symbol_journey()`:
The SQL SELECT includes `reason` but it's not included in the response dict.
Either drop `reason` from the SELECT, or add it to the response. Dropping is
cleaner since `JourneyEvent` has no `reason` field.

### Priority 3: Frontend Dead Code & Style (S5a, S5b, S8)

**6. Fix inline import in client.ts (S5a F-1)**

In `argus/ui/src/api/client.ts`:
`getObservatoryClosestMisses()` uses inline `import('./types')` instead of a
top-level import. Move `ObservatoryClosestMissesResponse` to the top-level
import block where all other types are imported.

**7. Replace imperative loop in groupByStrategy (S5a F-2)**

In `argus/ui/src/features/observatory/views/MatrixView.tsx`:
Replace the `for...of` loop in `groupByStrategy()` with a functional
`reduce()` pattern, per the project's CLAUDE.md preference for
map/reduce/filter over imperative iteration.

**8. Remove dead `totalHeight` variable (S5b-F2)**

In `argus/ui/src/features/observatory/views/MatrixView.tsx` (line ~237):
`const totalHeight = items.length * ROW_HEIGHT` is computed but never referenced.
Delete it.

**9. Remove dead `bucketWidth` variable (S8-F1)**

In `argus/ui/src/features/observatory/views/TimelineLane.tsx` (line ~95):
`const bucketWidth = ...` is computed but never referenced. Delete it.

### Priority 4: Three.js Maintainability (S6a, S6b)

**10. Extract shared TIER_DEFS (S6b CONCERN-3)**

`TIER_DEFS` and `TierDef` are duplicated between `FunnelScene.ts` and
`FunnelSymbolManager.ts` with a "must match" comment.

Fix: Create a shared constants file at
`argus/ui/src/features/observatory/views/three/constants.ts` exporting
`TIER_DEFS` and `TierDef`. Import from both FunnelScene.ts and
FunnelSymbolManager.ts. Delete the duplicate definitions.

**11. Add ordering comment for Shift+R/Shift+F (S6b CONCERN-4)**

In `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts`:
The Shift+R/Shift+F camera shortcuts rely on implicit ordering: lowercase
view-switch check (`VIEW_KEYS`) precedes uppercase shift-combo check. Add a
comment block explaining why the ordering matters and that `e.key` is uppercase
when Shift is held, so lowercase VIEW_KEYS won't match.

**12. Add camera shortcut test (S6a-F2)**

In `argus/ui/src/features/observatory/ObservatoryPage.test.tsx`:
Add a test that fires Shift+R and Shift+F keydown events when the funnel view
is active, and verifies the mock FunnelView ref callbacks (`resetCamera`,
`fitView`) are invoked. This closes the test gap for camera controls.

### Priority 5: Minor Cleanup

**13. Remove unnecessary `currentView` from useEffect deps (S3-F2)**

In `argus/ui/src/features/observatory/hooks/useObservatoryKeyboard.ts` (line ~190):
`currentView` is in the useEffect dependency array but the handler never reads
it directly — it only calls `setCurrentView`. Remove it from the deps array.
(If ESLint complains, suppress with a comment explaining the handler uses the
setter form which doesn't need the current value.)

**14. Add Suspense loading fallback (S3-F3)**

In `argus/ui/src/App.tsx` (line ~52):
Replace `<Suspense fallback={null}>` for the Observatory route with a minimal
loading indicator. A simple centered spinner or "Loading Observatory..." text
is sufficient. This is now relevant since the Three.js chunk is substantial.

**15. Fix pre-existing TS errors in ObservatoryLayout (S6a review note)**

In `argus/ui/src/features/observatory/ObservatoryLayout.tsx`:
Remove or use the unused `VIEW_LABELS` and `currentView` variables that cause
TypeScript errors. If they were intended for the vitals bar (which now handles
view display via SessionVitalsBar), they can be safely removed.

### Priority 6: Type Tightening

**16. Tighten `conn: object` type hint (S2 info)**

In `argus/analytics/observatory_service.py`:
Change `conn: object` parameter type on `_get_near_trigger_symbols()` and
`_count_near_triggers()` to `conn: aiosqlite.Connection` (with appropriate
import). This may be superseded by Requirement 2 if the public query method
eliminates direct connection passing.

## Constraints
- Do NOT modify any files in `argus/strategies/`, `argus/core/orchestrator.py`,
  `argus/core/risk_manager.py`, `argus/execution/`, `argus/data/`, `argus/ai/`,
  `argus/intelligence/` (except as needed for Requirement 2's EvaluationEventStore change)
- Do NOT add new features, new endpoints, or new UI components
- Do NOT change any existing test assertions (update tests only to match the
  fixes above)
- Do NOT add new npm dependencies
- Each requirement is independent — if one is unexpectedly complex, skip it and
  document the skip. Better to ship 14/16 clean fixes than 16/16 with a hack.

## Test Targets
After implementation:
- All existing tests must still pass
- New tests:
  - Requirement 1: Tab in Matrix selects symbol in detail panel (update existing test or add new)
  - Requirement 12: Shift+R/Shift+F camera shortcut test
- Minimum new/modified tests: 2
- Final test commands (full suite — last session of sprint):
  ```
  python -m pytest tests/ --ignore=tests/test_main.py -n auto -q
  cd argus/ui && npx vitest run
  ```

## Definition of Done
- [ ] All 16 requirements addressed (implemented or explicitly skipped with rationale)
- [ ] All existing tests pass
- [ ] New/modified tests pass
- [ ] TypeScript `tsc --noEmit` clean (0 errors, including pre-existing ones fixed)
- [ ] No new lint warnings introduced
- [ ] Close-out report written to file
- [ ] Tier 2 review completed via @reviewer subagent

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Matrix Tab now syncs highlight + selection | Manual test or new automated test |
| Observatory backend endpoints still work | `python -m pytest tests/api/test_observatory_routes.py tests/analytics/test_observatory_service.py -v` |
| All Observatory Vitest tests pass | `cd argus/ui && npx vitest run src/features/observatory/` |
| No trading pipeline files modified | `git diff --name-only` excludes strategies/core/execution/data/ai |
| TypeScript clean | `cd argus/ui && npx tsc --noEmit` returns 0 errors |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-25/session-10-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

The close-out MUST include a table showing which of the 16 requirements were
completed vs skipped, with rationale for any skips.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25/review-context.md`
2. The close-out report path: `docs/sprints/sprint-25/session-10-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (full suite — final session):
   ```
   python -m pytest tests/ --ignore=tests/test_main.py -n auto -q
   cd argus/ui && npx vitest run
   ```
5. Files that should NOT have been modified: anything in strategies/, core/orchestrator.py,
   core/risk_manager.py, execution/, data/, ai/, intelligence/catalyst/

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-25/session-10-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review files per the standard protocol.

## Session-Specific Review Focus (for @reviewer)
1. Verify Tab in Matrix view now syncs both `highlightedSymbol` and `selectedSymbol`
2. Verify `ObservatoryService` no longer accesses `_store._conn` directly
3. Verify all dead code variables removed (totalHeight, bucketWidth, unused imports)
4. Verify TIER_DEFS shared constants file exists and both consumers import from it
5. Verify TypeScript compiles with 0 errors (pre-existing errors resolved)
6. Verify no trading pipeline files in the diff
7. Verify each of the 16 requirements is either implemented or documented as skipped

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| No trading pipeline files modified | `git diff --name-only` |
| All pytest tests pass | `python -m pytest tests/ --ignore=tests/test_main.py -n auto -q` |
| All Vitest tests pass | `cd argus/ui && npx vitest run` |
| TypeScript strict mode clean | `cd argus/ui && npx tsc --noEmit` |
| No new npm dependencies | Check package.json diff |

## Sprint-Level Escalation Criteria (for @reviewer)
| Criterion | Threshold |
|-----------|-----------|
| Three.js < 30fps with 3,000+ particles | Cannot verify in CI — deferred to visual review |
| Bundle size increase > 500KB gzipped | Verify no new deps added |
| Observatory WS degrades Copilot WS | No WS changes in this session |
| Trading pipeline modification required | Must not happen |
| Non-Observatory page load > 100ms increase | Must not happen |