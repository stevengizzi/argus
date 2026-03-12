# Sprint 23.9, Session 2: Debrief 503 Fix (DEF-043)

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-23.9/sprint-spec.md`
   - `docs/sprints/sprint-23.9/spec-by-contradiction.md`
   - The Session 1 close-out report — specifically the **"Debrief 503
     Investigation"** section. This contains the root cause, exact file/line,
     and recommended fix approach. Your implementation MUST follow those findings.
   - `argus/api/routes/debrief.py` (or the file identified by Session 1)
   - `argus/ai/daily_summary.py` (or the file identified by Session 1)
   - `argus/api/server.py` — DailySummaryGenerator initialization
   - `argus/ui/src/pages/Debrief/` — current Debrief page components
2. Run the test baseline (DEC-328 — Session 2 gets scoped tests):
   ```bash
   python -m pytest tests/api/ tests/ai/ -x -q
   ```
   Expected: all passing (full suite was confirmed by Session 1 close-out).
   ```bash
   cd argus/ui && npx vitest run
   ```
   Expected: ≥ 439 tests passing (Session 1 added ~4).
3. Verify you are on the correct branch: `sprint-23.9`
4. Verify Session 1 changes are committed: `git log --oneline -5`

## Objective
Fix `GET /api/v1/debrief/briefings` so it returns 200 instead of 503. When
no summaries exist (e.g., no trades have occurred in paper trading), the endpoint
returns a 200 with an empty result set. The Debrief page handles this gracefully
with an empty state.

## Requirements

**NOTE:** The exact fix depends on Session 1's investigation findings. The
requirements below describe the intended *outcome*. Adapt the implementation
approach based on what Session 1 discovered about the root cause.

### Likely Scenario A: Generator dependency check is too strict
If the 503 is caused by the route handler checking a condition that fails
legitimately (e.g., "no trades exist" → "generator not ready" → 503):

1. In the route handler, change the dependency check so that "no data available"
   returns 200 with an empty result, not 503. Reserve 503 for actual service
   unavailability (generator object is None, API key missing, etc.).
2. If the generator has an `is_ready()` or `is_available()` method that
   conflates "no data" with "not initialized," split those conditions.

### Likely Scenario B: Generator initialization is incomplete
If the 503 is caused by the generator not being wired into `app_state` properly:

1. Fix the initialization wiring in `server.py` or the startup sequence.
2. Ensure the generator is available in `app_state` when the route is called.
3. Return empty result set if the generator has no data to summarize.

### Likely Scenario C: Generator needs a config gate
If the generator should only be active under certain conditions (like
`catalyst.enabled` gates the pipeline):

1. Add the appropriate condition check. When the condition is false, return
   200 with empty result and a status indicator (not 503).
2. The frontend should display "feature not active" or similar — not an error.

### Frontend Empty State (applies to all scenarios)

3. Review the Debrief page components. If the page currently only handles
   "data present" (no empty state rendering), add an empty state:
   - Show a message like "No daily briefings available yet" or "Briefings
     will appear once trades are recorded"
   - No error indicators, no red banners, no loading spinners stuck forever
   - Match the visual style of other empty states in the app (e.g., how the
     Dashboard handles no active trades)

4. If the Debrief page already has an empty state handler, verify it works
   correctly with the now-200 response.

### Tests

5. Write pytest tests for the endpoint:
   - Test: Endpoint returns 200 when generator is ready but has no data
     (empty result)
   - Test: Endpoint returns 200 with data when summaries exist
   - Test: Endpoint returns 503 only when generator is genuinely unavailable
     (None / uninitialized)

6. If frontend changes were made, write Vitest tests:
   - Test: Debrief page renders empty state when API returns empty result
   - Test: Debrief page renders data when API returns summaries

## Constraints
- Do NOT modify: `argus/intelligence/` (pipeline source code)
- Do NOT modify: `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/data/`
- Do NOT modify: `argus/config/system.yaml`, `argus/config/system_live.yaml`
- Do NOT modify: Session 1's changes (catalyst hooks, test fixes)
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
- [ ] `/api/v1/debrief/briefings` returns 200 (with data or empty result)
- [ ] Debrief page renders without errors
- [ ] Empty state UI shown when no summaries available
- [ ] pytest tests for endpoint scenarios
- [ ] Vitest tests for frontend empty state (if frontend modified)
- [ ] All existing tests pass
- [ ] No ruff violations

## Regression Checklist (Session-Specific)
After implementation, verify each of these:
| Check | How to Verify |
|-------|---------------|
| Debrief endpoint returns 200 | `curl http://localhost:8000/api/v1/debrief/briefings` → 200 |
| Other debrief routes unchanged | Check that any other debrief routes still work as before |
| AI layer endpoints unaffected | `curl /api/v1/health` shows AI services initialized |
| Session 1 changes intact | Catalyst hook gating still works (quick check: no 503 spam with pipeline disabled) |
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
| 7 | All Vitest tests pass | `cd argus/ui && npx vitest run` — count ≥ 439 |
| 8 | No ruff violations | `ruff check argus/ tests/` clean |
| 9 | No files outside scope modified | `git diff --name-only` shows only expected files |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
1. Architectural surprise in DailySummaryGenerator (design fundamentally incompatible)
2. Health endpoint was modified (violates spec-by-contradiction)
3. Scope creep beyond DEF-043
4. Test count regression below baseline
5. Other API endpoints affected by changes
