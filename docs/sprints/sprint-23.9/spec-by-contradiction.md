# Sprint 23.9: What This Sprint Does NOT Do

## Out of Scope
These items are related to the sprint goal but are explicitly excluded:
1. **Request batching / bulk catalyst endpoint:** The current pattern of one
   request per watchlist symbol (when pipeline is active) is not optimized in
   this sprint. The fix only prevents requests when pipeline is *inactive*.
   Bulk endpoint consolidation is a future optimization (DEF-047).
2. **Backend catalyst endpoint changes:** The 503 → no-request fix is purely
   frontend. The backend still returns 503 when pipeline is disabled — the
   frontend just stops asking.
3. **DailySummaryGenerator content quality:** Session 2 fixes the 503 plumbing
   so the endpoint returns data. Whether the generated summaries are *useful*
   is a Sprint 24+ concern.
4. **Debrief page AI summary triggering logic:** If the DailySummaryGenerator
   has no summaries because no trades have occurred, the fix returns an empty
   result set. We do not add logic to generate summaries on demand or schedule
   generation.
5. **xdist collection discrepancy investigation:** The 10-test count gap between
   xdist and non-xdist runs (Issue 5 in scoping note) may resolve when DEF-046
   is fixed. If it doesn't, it is noted but not actively debugged in this sprint.
6. **Frontend double-fire / remount optimization:** The scoping note observes
   that some requests fire twice on page load (React remount). This is a general
   React lifecycle issue, not specific to catalyst hooks. Not addressed here.
7. **New backend API endpoints:** No new routes. DEC-329 uses the existing
   health endpoint for pipeline status.

## Edge Cases to Reject
The implementation should NOT handle these cases in this sprint:
1. **Health endpoint unavailable:** If `/api/v1/health` itself fails, catalyst
   hooks should default to `enabled: false` (fail-closed). Do not build retry
   logic for the health check.
2. **Partial pipeline status:** If some sources are up but others aren't, the
   hooks treat pipeline as either fully active or inactive (boolean). Per-source
   granularity is not needed.
3. **DailySummaryGenerator partial initialization:** If the generator exists but
   an internal dependency is missing, return empty result set (not 503). Do not
   add health-check probing of sub-dependencies.
4. **xdist failures in files other than test_main.py:** Only the two named tests
   are in scope. Other xdist issues discovered during investigation are logged
   but not fixed.

## Scope Boundaries
- Do NOT modify: `argus/intelligence/` (pipeline code), `argus/core/`,
  `argus/strategies/`, `argus/execution/`, `argus/data/`,
  `argus/api/routes/health.py` (health endpoint response shape),
  `argus/config/system.yaml`, `argus/config/system_live.yaml`
- Do NOT optimize: Catalyst request volume when pipeline IS active (one-per-symbol
  pattern stays)
- Do NOT refactor: TanStack Query hook architecture, DailySummaryGenerator
  internals beyond what's needed for the 503 fix
- Do NOT add: New API routes, new config fields, new database tables

## Interaction Boundaries
- This sprint does NOT change the behavior of: `/api/v1/health` response shape,
  `/api/v1/catalysts/{symbol}` response shape, `/api/v1/premarket/briefing/*`
  response shape, WebSocket endpoints, Event Bus, intelligence pipeline polling
  loop
- This sprint does NOT affect: Strategy execution, order management, risk manager,
  data service, universe manager, scanner, any backend pipeline logic

## Deferred to Future Sprints
| Item | Target Sprint | DEF Reference |
|------|--------------|---------------|
| Bulk catalyst endpoint (one request for all symbols) | Unscheduled | DEF-047 |
| xdist collection discrepancy (10-test gap) | Unscheduled | Observation only |
| React double-fire / remount optimization | Unscheduled | General UI concern |
