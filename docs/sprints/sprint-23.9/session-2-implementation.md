# Sprint 23.9, Session 2: Debrief 503 Fix (DEF-043)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-23.9/sprint-spec.md`
   - `docs/sprints/sprint-23.9/spec-by-contradiction.md`
   - The Session 1 close-out report — specifically the **"Debrief 503
     Investigation"** section, which confirmed the root cause.
   - `argus/api/dependencies.py` — lines 126-143 (`get_debrief_service()`)
   - `argus/api/dev_state.py` — around line 2154 (how DebriefService is
     initialized in dev mode — this is the pattern to replicate)
   - `argus/api/server.py` — lifespan function (where the wiring goes;
     note Session 1 already added `catalyst_pipeline` health registration here)
   - `argus/api/routes/briefings.py` — debrief route handler
   - `argus/ui/src/pages/Debrief/` — current Debrief page components
2. Run the test baseline (DEC-328 — Session 2 gets scoped tests):
   ```bash
   python -m pytest tests/api/ tests/ai/ -x -q
   ```
   Expected: all passing (full suite was confirmed by Session 1 close-out).
   ```bash
   cd argus/ui && npx vitest run
   ```
   Expected: 446 tests passing (Session 1 baseline).
3. Verify you are on the correct branch: `sprint-23.9`
4. Verify Session 1 changes are committed: `git log --oneline -5`

## Objective
Fix `GET /api/v1/debrief/briefings` so it returns 200 instead of 503. The root
cause is confirmed: `DebriefService` is initialized in dev mode
(`dev_state.py:~2154`) but never initialized in live mode (`server.py` lifespan).
The fix is wiring `DebriefService` into the `server.py` lifespan, following the
same pattern used in `dev_state.py`.

## Requirements

### Root Cause (Confirmed by Session 1 Investigation)
- `get_debrief_service()` in `argus/api/dependencies.py:126-143` checks
  `state.debrief_service is None` and raises HTTP 503 if true
- In dev mode, `dev_state.py:~2154` initializes `DebriefService(db)` and assigns
  it to `app_state.debrief_service`
- In live mode (`server.py` lifespan), `debrief_service` is NEVER set — remains
  `None`
- `DailySummaryGenerator` IS created (confirmed in AI services init log), but
  `DebriefService` is a separate service that's missing

### Backend Fix

1. In `argus/api/server.py` lifespan function, initialize `DebriefService` and
   assign it to `app_state.debrief_service`. Follow the initialization pattern
   from `dev_state.py:~2154`:
   - Read what constructor arguments `DebriefService` requires (likely a database
     connection)
   - Use the same database connection available in the lifespan context
   - Place the initialization near the existing AI services block (after
     `DailySummaryGenerator` is created, since they may be related)

2. Verify the endpoint behavior after wiring:
   - When `DebriefService` is initialized and has no data: returns 200 with
     empty result set
   - When `DebriefService` is initialized and has data: returns 200 with data
   - Confirm 503 only occurs if `DebriefService` genuinely fails to initialize
     (e.g., database unavailable)

3. If `DebriefService` returns 503 or errors when it has no summaries to show
   (e.g., zero trades in paper mode), also fix that condition. The endpoint
   should return 200 with an empty result, not 503, when there's simply no
   data yet. This may require checking the service's methods for overly strict
   "has data" guards.

### Frontend Empty State

4. Review the Debrief page components. If the page currently only handles
   "data present" (no empty state rendering), add an empty state:
   - Show a message like "No daily briefings available yet" or "Briefings
     will appear once trades are recorded"
   - No error indicators, no red banners, no loading spinners stuck forever
   - Match the visual style of other empty states in the app (e.g., how the
     Dashboard handles no active trades)

5. If the Debrief page already has an empty state handler, verify it works
   correctly with the now-200 response.

### Tests

6. Write pytest tests for the endpoint:
   - Test: Endpoint returns 200 when `DebriefService` is initialized but has
     no data (empty result)
   - Test: Endpoint returns 200 with data when summaries exist (mock data)
   - Test: Endpoint returns 503 only when `debrief_service` is None
     (genuinely uninitialized)

7. If frontend changes were made, write Vitest tests:
   - Test: Debrief page renders empty state when API returns empty result
   - Test: Debrief page renders data when API returns summaries

## Constraints
- Do NOT modify: `argus/intelligence/` (pipeline source code)
- Do NOT modify: `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/data/`
- Do NOT modify: `argus/config/system.yaml`, `argus/config/system_live.yaml`
- Do NOT modify: Session 1's changes (catalyst hooks, test fixes, health
  monitor registration in server.py — be careful not to disturb the
  `catalyst_pipeline` registration when editing the lifespan)
- Do NOT add: New config fields
- Do NOT change: Other API endpoint behaviors (health, catalyst, briefing, etc.)
- Do NOT add: Logic to trigger summary generation on demand — just fix the
  endpoint to return what it has (or empty)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New pytest tests: ~3-5 (debrief endpoint scenarios)
- New Vitest tests: ~2-3 if frontend changes made, 0 if not
- Minimum net new test count: 3
- Test commands:
  ```bash
  python -m pytest tests/api/ tests/ai/ -x -q    # Scoped to affected modules
  cd argus/ui && npx vitest run                    # Full Vitest if frontend changed
  ```

## Visual Review
The developer should visually verify the following after this session:

1. **Debrief page loads cleanly:** Navigate to The Debrief page. Page should
   load without errors, without stuck spinners, and without red error banners.
2. **Empty state shown when no data:** If no daily summaries exist (likely in
   paper trading with 0 completed trades), the page should show a friendly
   empty state message — not a 503 error.
3. **No console errors:** Open browser DevTools → Console. No errors related
   to `/api/v1/debrief/briefings`. The request should return 200.
4. **Other pages unaffected:** Navigate to Dashboard, Trade Log, Orchestrator
   page. All should work exactly as before.

Verification conditions:
- Backend running with `system_live.yaml` config
- `ANTHROPIC_API_KEY` set (DailySummaryGenerator likely needs it)
- No active trades needed — the empty state IS the primary test case

## Definition of Done
- [ ] `DebriefService` initialized in `server.py` lifespan
- [ ] `/api/v1/debrief/briefings` returns 200 (with data or empty result)
- [ ] Debrief page renders without errors
- [ ] Empty state UI shown when no summaries available
- [ ] pytest tests for endpoint scenarios
- [ ] Vitest tests for frontend empty state (if frontend modified)
- [ ] All existing tests pass
- [ ] Session 1's catalyst_pipeline health registration still works
- [ ] No ruff violations

## Regression Checklist (Session-Specific)
After implementation, verify each of these:
| Check | How to Verify |
|-------|---------------|
| Debrief endpoint returns 200 | `curl http://localhost:8000/api/v1/debrief/briefings` → 200 |
| Other debrief routes unchanged | Check that any other debrief routes still work as before |
| AI layer endpoints unaffected | `curl /api/v1/health` shows AI services initialized |
| Session 1 catalyst_pipeline registration intact | Health response includes `catalyst_pipeline` component |
| Session 1 hook gating intact | Dashboard with pipeline disabled: no 503 spam |
| Frontend builds | `cd argus/ui && npm run build` succeeds |
| No out-of-scope files modified | `git diff --name-only HEAD~1` shows only expected files |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Health endpoint unchanged | `curl http://localhost:8000/api/v1/health` returns same shape as before sprint |
| 2 | Catalyst endpoint still works when enabled | With `catalyst.enabled: true`, `curl http://localhost:8000/api/v1/catalysts/AAPL` returns 200 |
| 3 | Intelligence briefing endpoint still works | `curl http://localhost:8000/api/v1/premarket/briefing/latest` returns 200 or 404 (not 503) |
| 4 | Debrief briefings endpoint responds | `curl http://localhost:8000/api/v1/debrief/briefings` returns 200 |
| 5 | Frontend builds without errors | `cd argus/ui && npm run build` succeeds |
| 6 | All pytest tests pass | `python -m pytest -n auto -x -q` — count ≥ 2,529 |
| 7 | All Vitest tests pass | `cd argus/ui && npx vitest run` — count ≥ 446 |
| 8 | No ruff violations | `ruff check argus/ tests/` clean |
| 9 | No files outside scope modified | `git diff --name-only` shows only expected files |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
1. DebriefService architecture fundamentally incompatible with live-mode lifecycle
2. Health endpoint was modified (violates spec-by-contradiction)
3. Scope creep beyond DEF-043
4. Test count regression below baseline
5. Other API endpoints affected by changes
6. Session 1's catalyst_pipeline health registration broken by Session 2 changes