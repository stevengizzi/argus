# Sprint 23.9: Frontend + Test Cleanup (Post-23.8 Fast-Follow)

## Goal
Fix frontend intelligence hook request spam (DEF-041), resolve the Debrief page
503 error (DEF-043), rewrite the tautological SEC Edgar timeout test (DEF-045),
and fix pre-existing xdist test failures (DEF-046). These are all issues
discovered during live QA and Sprint 23.8 Tier 2 reviews — clearing the deck
before Sprint 24 (Setup Quality Engine + Dynamic Sizer).

## Scope

### Deliverables
1. **Frontend catalyst/intelligence hook gating (DEF-041):** TanStack Query
   hooks for catalyst and intelligence briefing data only fire when the
   intelligence pipeline is active, as reported by the health endpoint.
   When pipeline is inactive, zero catalyst/intelligence HTTP requests are made.
2. **Debrief 503 fix (DEF-043):** `GET /api/v1/debrief/briefings` returns a
   valid response (200 with data, or 200 with empty result set) instead of 503.
3. **SEC Edgar timeout test rewrite (DEF-045):** The SEC Edgar timeout test
   calls `await client.start()` and inspects `client._session.timeout`,
   matching the pattern used by Finnhub and FMP timeout tests.
4. **xdist test isolation fix (DEF-046):** `test_orchestrator_in_app_state` and
   `test_multiple_strategies_registered_with_orchestrator` in `test_main.py`
   pass under `pytest -n auto`.

### Acceptance Criteria
1. **DEF-041 (Hook gating):**
   - With `catalyst.enabled: false`: Dashboard page load produces zero
     `/api/v1/catalysts/*` requests and zero `/api/v1/premarket/briefing/*`
     requests in the browser network tab
   - With `catalyst.enabled: true`: Catalyst and briefing requests fire normally
     and return 200 with data
   - Vitest tests confirm both paths
2. **DEF-043 (Debrief 503):**
   - `GET /api/v1/debrief/briefings` returns 200 (with data if available, or
     empty list/object if no summaries exist yet)
   - Debrief page renders without console errors or red UI states
   - pytest tests confirm endpoint behavior for both data-present and no-data cases
3. **DEF-045 (SEC Edgar test):**
   - Test calls `client.start()` (with CIK refresh mocked)
   - Test inspects `client._session.timeout` values
   - Test fails if someone changes timeout values in `sec_edgar.py:start()`
     without updating the test
4. **DEF-046 (xdist fix):**
   - `pytest tests/test_main.py -n auto -x -q` passes all tests in that file
   - Full suite `pytest -n auto` passes with consistent test count

### Performance Benchmarks
N/A — this sprint fixes correctness issues, not performance.

### Config Changes
No config changes in this sprint.

## Dependencies
- Sprint 23.8 merged to main ✅
- `catalyst.enabled` togglable in `system_live.yaml` for testing both paths
- `ANTHROPIC_API_KEY` set (DailySummaryGenerator may require Claude API)
- IBKR Gateway running is NOT required for any item in this sprint

## Relevant Decisions
- DEC-305 (TanStack Query hooks for catalyst data): Sprint 23.5 introduced these
  hooks — this sprint adds conditional enablement
- DEC-313 (FMP canary test): Health endpoint includes pipeline component status —
  Session 1 leverages this for frontend gating
- DEC-328 (Test suite tiering): Governs pre-flight and review test commands

## Relevant Risks
- RSK-022 (IBKR Gateway reconnection): Not relevant — no IBKR interaction
- No new risks introduced. All changes are low-regression fixes.

## Session Count Estimate
2 sessions estimated. Session 1 bundles three independent small items (hook
gating, test rewrite, xdist fix) plus a read-only investigation. Session 2
handles the debrief fix using Session 1's findings. Both sessions score Low
on compaction risk (7 and 4 respectively).
