# Sprint 23.9, Session 1: Catalyst Hook Gating + Test Fixes + Debrief Investigation

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/sprints/sprint-23.9/sprint-spec.md`
   - `docs/sprints/sprint-23.9/spec-by-contradiction.md`
   - `docs/sprints/sprint-23.9/design-summary.md`
   - `argus/ui/src/hooks/` — list all hook files to find catalyst/health hooks
   - `argus/api/routes/health.py` — understand health endpoint response shape
   - `argus/api/routes/debrief.py` (or `grep -rn "debrief/briefings" argus/api/`)
   - `tests/intelligence/test_sec_edgar.py` — lines 339-372 (the tautological test)
   - `tests/intelligence/test_finnhub.py` — find the timeout test (correct pattern to match)
   - `tests/intelligence/test_fmp_news.py` — find the timeout test (correct pattern to match)
   - `tests/test_main.py` — find `test_orchestrator_in_app_state` and
     `test_multiple_strategies_registered_with_orchestrator`
2. Run the test baseline (DEC-328 — Session 1 gets full suite):
   ```bash
   python -m pytest -n auto -x -q
   ```
   Expected: 2,529 tests passing (xdist may show ~2,519 due to DEF-046 — that's
   the known issue this session fixes). Record the actual count.
   ```bash
   cd argus/ui && npx vitest run
   ```
   Expected: 435 tests passing.
3. Verify you are on the correct branch:
   ```bash
   git checkout -b sprint-23.9 main
   ```
4. Confirm `catalyst.enabled` value in `argus/config/system_live.yaml` — need to
   know current state for testing both paths.

## Objective
Fix the frontend catalyst/intelligence hook request spam (DEF-041), rewrite the
tautological SEC Edgar timeout test (DEF-045), fix xdist test isolation failures
(DEF-046), and investigate the debrief 503 root cause (DEF-043 investigation only
— fix is Session 2).

## Requirements

### Part A: Frontend Catalyst Hook Gating (DEF-041, DEC-329)

1. Find the health endpoint response shape in `argus/api/routes/health.py`. Look
   for what fields indicate intelligence pipeline status. Expected: the component
   status section should include something like `intelligence_pipeline` or
   `catalyst_pipeline` with an active/inactive indicator.

2. Create or modify a hook (e.g., `usePipelineStatus`) that extracts the pipeline
   active status from the health endpoint response. If `useHealth()` already
   exists, consider extracting from it rather than creating a duplicate query.
   The hook should:
   - Return a boolean `isPipelineActive`
   - Default to `false` if health endpoint fails or is loading (fail-closed)
   - Use a reasonable stale time (30s–60s) since pipeline status rarely changes

3. In the catalyst data hooks (likely `useCatalysts.ts` or similar), add
   `enabled: isPipelineActive` to the TanStack Query options. This means:
   - When pipeline is inactive: query never fires, no HTTP request made
   - When pipeline is active: query fires normally

4. Apply the same pattern to intelligence briefing hooks (likely
   `useIntelligenceBriefings.ts` or similar). Both catalyst badges and
   intelligence briefings should be gated on the same pipeline status.

5. Write Vitest tests:
   - Test: When health reports pipeline inactive, catalyst query has `enabled: false`
   - Test: When health reports pipeline active, catalyst query has `enabled: true`
   - Test: When health endpoint fails/loading, catalyst query has `enabled: false`
   - Test: Briefing hooks follow the same gating pattern

### Part B: SEC Edgar Timeout Test Rewrite (DEF-045)

6. In `tests/intelligence/test_sec_edgar.py`, find the timeout test (~line 339-372).
   The current test manually constructs an `aiohttp.ClientSession` with hardcoded
   timeout values and asserts those same values — it's tautological.

7. Rewrite it to match the Finnhub/FMP pattern:
   - Mock the CIK map refresh (the SEC Edgar `start()` method fetches a CIK map,
     which is why the original implementer took the shortcut)
   - Call `await client.start()`
   - Inspect `client._session.timeout` values
   - Assert they match the values configured in `sec_edgar.py:start()`
   This ensures the test fails if someone changes the timeout configuration
   in the source without updating the test.

### Part C: xdist Test Isolation Fix (DEF-046)

8. Investigate the two failing tests in `tests/test_main.py`:
   - `test_orchestrator_in_app_state`
   - `test_multiple_strategies_registered_with_orchestrator`
   Run them in isolation:
   ```bash
   python -m pytest tests/test_main.py::test_orchestrator_in_app_state -x -v
   python -m pytest tests/test_main.py -n auto -x -v
   ```
   Diagnose why they fail under xdist. Common causes: shared state (global
   variables, singletons), port conflicts, database file contention, import-time
   side effects, fixture scope issues.

9. Fix the isolation issue. Options by preference:
   a. **Fix the root cause** — add proper fixtures, isolate shared state
   b. **Mark as serial** — if root cause is expensive to fix, mark with
      `@pytest.mark.no_xdist` or equivalent (document why in a comment)
   Note: Option (b) is acceptable for this sprint since these are pre-existing
   failures and deep refactoring of test infrastructure is out of scope.

### Part D: Debrief 503 Investigation (READ-ONLY — DEF-043)

10. Investigate the debrief 503 root cause. Do NOT fix it — just report findings.
    Steps:
    a. Find the route handler: `grep -rn "debrief/briefings" argus/api/`
    b. Read the handler — identify what service dependency check returns 503
    c. Find where DailySummaryGenerator is initialized in `argus/api/server.py`
    d. Determine why the dependency check fails. Likely candidates:
       - Generator needs trade data that doesn't exist yet (0 trades in paper mode)
       - Generator has its own `is_ready()` / `is_available()` check that fails
       - A secondary dependency (not the generator itself) is missing
    e. Check if the frontend (`argus/ui/src/pages/Debrief/`) handles empty
       states or always expects data

    Report your findings in the close-out under a dedicated "Debrief 503
    Investigation" section. Include:
    - The exact file and line causing the 503
    - The condition that fails
    - Your recommended fix approach (one of: config wiring, dependency fix,
      empty-result fallback, or combination)
    - Whether frontend changes are needed for empty state handling
    - Estimated scope of the Session 2 fix

## Constraints
- Do NOT modify: `argus/intelligence/` (any pipeline source code)
- Do NOT modify: `argus/core/`, `argus/strategies/`, `argus/execution/`, `argus/data/`
- Do NOT modify: `argus/api/routes/health.py` (health endpoint response shape)
- Do NOT modify: `argus/config/system.yaml`, `argus/config/system_live.yaml`
- Do NOT modify: `argus/api/routes/debrief.py` or any debrief-related code (investigation only)
- Do NOT add: New backend API routes or endpoints
- Do NOT change: Catalyst endpoint response shape, intelligence briefing response shape
- Do NOT optimize: Request volume when pipeline IS active (one-per-symbol stays)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New Vitest tests: ~4 (catalyst hook gating paths)
- Modified pytest tests: ~1 (SEC Edgar timeout rewrite)
- Fixed pytest tests: ~2 (xdist isolation)
- Minimum net new test count: 4
- Test commands:
  ```bash
  python -m pytest -n auto -x -q        # Full suite — should now include previously-failing xdist tests
  cd argus/ui && npx vitest run          # Full Vitest suite
  ```

## Visual Review
The developer should visually verify the following after this session:

1. **Dashboard with `catalyst.enabled: false`:** Open browser DevTools → Network
   tab. Load Dashboard page. Verify zero requests to `/api/v1/catalysts/*` and
   zero requests to `/api/v1/premarket/briefing/*`.
2. **Dashboard with `catalyst.enabled: true`:** Toggle config and restart. Load
   Dashboard page. Verify catalyst badge requests fire and return 200. Verify
   intelligence briefing requests fire normally.
3. **No visual regression on Dashboard:** Catalyst badges area shows gracefully
   empty state (no spinners, no error banners) when pipeline is disabled.

Verification conditions:
- Backend running with `system_live.yaml` config
- Test both `catalyst.enabled: true` and `catalyst.enabled: false` states
- Browser DevTools Network tab open during page load

## Definition of Done
- [ ] Catalyst hooks gated on pipeline status (zero requests when disabled)
- [ ] Intelligence briefing hooks follow same gating pattern
- [ ] Vitest tests for both enabled/disabled paths
- [ ] SEC Edgar timeout test rewritten (calls start(), inspects session timeout)
- [ ] xdist test failures resolved (both tests pass under -n auto)
- [ ] Debrief 503 investigation complete, findings in close-out
- [ ] All existing tests pass
- [ ] New tests written and passing
- [ ] No ruff violations

## Regression Checklist (Session-Specific)
After implementation, verify each of these:
| Check | How to Verify |
|-------|---------------|
| Health endpoint unchanged | `grep -c` response fields in health.py — same count as before |
| Catalyst endpoint still works when enabled | With pipeline active, `curl /api/v1/catalysts/AAPL` returns 200 |
| Frontend builds | `cd argus/ui && npm run build` succeeds |
| SEC Edgar test is non-tautological | New test calls `client.start()` — grep for `client.start()` in test body |
| xdist tests pass | `python -m pytest tests/test_main.py -n auto -x -q` passes |
| No out-of-scope files modified | `git diff --name-only` shows only expected files |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**IMPORTANT:** The close-out MUST include a "Debrief 503 Investigation" section
with the findings from Part D. This section informs the Session 2 implementation
prompt. Include: the exact file/line causing 503, the failing condition, your
recommended fix approach, whether frontend changes are needed, and estimated
scope.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| # | Check | How to Verify |
|---|-------|---------------|
| 1 | Health endpoint unchanged | `curl http://localhost:8000/api/v1/health` returns same shape as before sprint |
| 2 | Catalyst endpoint still works when enabled | With `catalyst.enabled: true`, `curl http://localhost:8000/api/v1/catalysts/AAPL` returns 200 |
| 3 | Intelligence briefing endpoint still works | `curl http://localhost:8000/api/v1/premarket/briefing/latest` returns 200 or 404 (not 503) |
| 4 | Frontend builds without errors | `cd argus/ui && npm run build` succeeds |
| 5 | All pytest tests pass | `python -m pytest -n auto -x -q` — count ≥ 2,529 |
| 6 | All Vitest tests pass | `cd argus/ui && npx vitest run` — count ≥ 435 |
| 7 | No ruff violations | `ruff check argus/ tests/` clean |
| 8 | No files outside scope modified | `git diff --name-only` shows only expected files |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
1. Architectural surprise in debrief 503 investigation findings
2. xdist failures trace to shared global state beyond test_main.py
3. Health endpoint modification was required (violates spec-by-contradiction)
4. Scope creep beyond the 4 defined items
5. Test count regression below 2,529 pytest or 435 Vitest
