# Sprint 23.9 — Scoping Note (Fast-Follow to 23.8)

> Captured during March 12, 2026 live QA session. This note preserves diagnostic
> context so Sprint 23.9 can be planned immediately after Sprint 23.8 completes
> without re-investigating these issues.

**Type:** Impromptu triage (fast-follow)
**Urgency:** DISCOVERED — found during live QA (March 12) + Sprint 23.8 reviews
**Predecessor:** Sprint 23.8 (must complete first — pipeline must be operational) ✅ COMPLETE
**Estimated sessions:** 2
**Items:** DEF-041 (catalyst short-circuit), DEF-043 (debrief 503), DEF-045 (SEC Edgar test rewrite), DEF-046 (test_main.py xdist failures)

---

## Issue 1: Frontend Catalyst Endpoint Short-Circuit (DEF-041)

### What Happens
When `catalyst.enabled: false` (or the pipeline is disabled), the frontend
fires 15+ individual `GET /api/v1/catalysts/{symbol}` requests on Dashboard
page load — one per watchlist symbol. All return 503. On component remount
or navigation, it fires them again. Observed: ~30–60 wasted 503 responses
per page load cycle.

When `catalyst.enabled: true`, the same pattern fires but returns 200 with
data. The request volume is still excessive (one per symbol) but at least
produces useful results.

### Root Cause
The TanStack Query hooks (`useCatalysts` or similar, likely in
`argus/ui/src/hooks/` or co-located with Dashboard components) fire
unconditionally for each watchlist symbol. There's no check of pipeline
status before issuing requests.

### Proposed Fix
**Option A (recommended):** Add a pipeline status check to the catalyst hooks.
The `/api/v1/health` endpoint already returns component status. Add a
`usePipelineStatus()` hook (or extract from existing `useHealth()`) that
returns whether the intelligence pipeline is active. In `useCatalysts()`,
set `enabled: pipelineActive` on the TanStack Query options. When pipeline
is inactive, the query never fires.

**Option B:** Add a dedicated `GET /api/v1/catalysts/status` lightweight
endpoint that returns `{ enabled: bool, source_count: int }`. Frontend
checks this once on mount and gates all catalyst queries.

**Option A is preferred** because it uses existing infrastructure (health
endpoint) and requires no backend changes.

### Files Likely Involved
- `argus/ui/src/hooks/useCatalysts.ts` (or wherever catalyst hooks live)
- `argus/ui/src/hooks/useHealth.ts` (or wherever health data is consumed)
- `argus/ui/src/pages/Dashboard/` (watchlist component that renders badges)
- Possibly `argus/ui/src/hooks/useIntelligenceBriefings.ts` (same pattern)

### Test Strategy
- Vitest: mock health response with pipeline disabled, verify catalyst queries
  have `enabled: false`
- Vitest: mock health response with pipeline enabled, verify catalyst queries fire
- Visual: load Dashboard with `catalyst.enabled: false`, verify no 503s in
  network tab

---

## Issue 2: `/debrief/briefings` Returns 503 (DEF-043)

### What Happens
`GET /api/v1/debrief/briefings` returns HTTP 503 Service Unavailable.
This is the DailySummaryGenerator endpoint on The Debrief page, separate
from the intelligence briefings (`/api/v1/premarket/briefing/*`) which
work correctly.

### Observed Log Lines
```
INFO:     127.0.0.1:53537 - "GET /api/v1/debrief/briefings HTTP/1.1" 503 Service Unavailable
INFO:     127.0.0.1:53541 - "GET /api/v1/debrief/briefings HTTP/1.1" 503 Service Unavailable
```

No error log, no traceback — just a 503 response. This means the route
handler exists and is deliberately returning 503, likely because a required
service dependency is None/uninitialized.

### Probable Root Cause (Needs Verification)
The Debrief page was built in Sprint 21c. The DailySummaryGenerator was
likely designed to generate end-of-day AI summaries. The 503 pattern
matches what we saw with the intelligence pipeline before enabling it —
a service dependency check returning "not available."

**Investigation steps for Sprint 23.9:**
1. Find the route handler: `grep -rn "debrief/briefings" argus/api/`
2. Find what service it checks: likely `if app_state.daily_summary_generator is None: return 503`
3. Find where DailySummaryGenerator is initialized: `grep -rn "DailySummaryGenerator" argus/api/server.py`
4. Determine if it needs a config gate (like `catalyst.enabled`) or if
   it should always be active when the AI layer is configured

The DailySummaryGenerator is listed in the server.py AI services initialization
log line: `"AI services initialized (ClaudeClient, PromptManager, ...,
DailySummaryGenerator, ResponseCache)"` — so it IS being created. The 503
likely means either:
- A secondary dependency of DailySummaryGenerator is missing (e.g., it
  needs trade data that doesn't exist yet in paper trading with 0 trades)
- The route is checking for something beyond the generator's existence
- The generator has its own `is_ready()` or `is_available()` check that fails

### Proposed Approach
This needs a 10-minute investigation in Claude Code (read-only) before
the implementation prompt can be written. The fix could be:
- **Config wiring:** If the generator needs explicit enablement, add a gate
- **Dependency fix:** If it checks for data that doesn't exist, make it
  return an empty result set instead of 503
- **Backend + frontend:** The frontend may need to handle the empty state
  gracefully (no briefings yet, show empty state instead of error)

### Files Likely Involved
- `argus/api/routes/debrief.py` (or wherever the route lives)
- `argus/api/server.py` (DailySummaryGenerator initialization)
- `argus/ai/daily_summary.py` (or wherever the generator lives)
- `argus/ui/src/pages/Debrief/` (if frontend needs empty state handling)

---

## Session Plan (Preliminary)

**Session 1: Catalyst Short-Circuit + Debrief Investigation + Test Fixes**
- Implement the catalyst hook gating (DEF-041)
- Read-only investigation of the debrief 503 root cause
- Rewrite SEC Edgar timeout test (DEF-045) — match Finnhub/FMP pattern
- Investigate test_main.py xdist failures (DEF-046)
- Report debrief findings in close-out to inform Session 2

**Session 2: Debrief 503 Fix**
- Fix based on Session 1's investigation findings
- Backend wiring + frontend empty state if needed

---

## Dependencies
- Sprint 23.8 must be complete (pipeline operational, cost ceiling enforced) ✅
- `catalyst.enabled: true` in `system_live.yaml` (to test both enabled/disabled paths)
- ANTHROPIC_API_KEY set (DailySummaryGenerator likely needs Claude API)

## Additional Issues from Sprint 23.8 Close-Outs

### Issue 3: SEC Edgar Timeout Test is Tautological (DEF-045)

**Source:** Sprint 23.8, Session 3, Tier 2 Review — CONCERNS verdict.

The SEC Edgar timeout test (`test_sec_edgar.py:339-372`) does NOT call
`client.start()`. It manually constructs an `aiohttp.ClientSession` with
hardcoded timeout values inside the test body, then asserts those same
values. If someone changes the timeout in `sec_edgar.py:start()`, this
test still passes — it provides zero regression protection.

**Fix:** Rewrite to match the pattern used by Finnhub and FMP tests: call
`await client.start()`, then inspect `client._session.timeout`. The SEC
Edgar `start()` method includes a CIK map refresh that needs mocking
(likely why the implementer took the shortcut).

### Issue 4: test_main.py Failures Under xdist (DEF-046)

**Source:** Sprint 23.8, Session 3 close-out.

Two tests fail under `pytest-xdist -n auto`:
- `test_orchestrator_in_app_state`
- `test_multiple_strategies_registered_with_orchestrator`

Confirmed pre-existing — fail on clean HEAD with xdist. Pass without xdist.
Likely cause: shared state, port conflicts, or import-time side effects
under parallel worker isolation.

**Investigation:** Run these tests isolated (`-k "test_orchestrator_in_app"`)
with and without `-n auto`. Check if they depend on global state, database
files, or network ports. Fix may be test isolation (fixtures) or marking
as `@pytest.mark.no_xdist`.

### Issue 5: xdist Test Collection Discrepancy

**Source:** Sprint 23.8, Session 3 close-out.

Session 2 reported 2,521 tests without xdist. Session 3 added 8 tests
(expected: 2,529) but xdist collected only 2,519. The 10-test gap may
be worker collection issues, import failures under parallel execution,
or tests that depend on collection order. Low priority but worth
understanding.

## Context That Will Be Lost
- The exact log excerpts showing the 503 pattern (captured in this note)
- The server.py initialization log confirming DailySummaryGenerator IS created
- The behavioral observation that intelligence briefings work but debrief
  briefings don't — they use different endpoints and different generators
- The double-fire pattern on debrief/briefings (frontend requests it twice
  on page load — likely same React remount issue as catalyst requests)
- SEC Edgar timeout test location: `test_sec_edgar.py:339-372`
- Finnhub/FMP timeout test pattern (the correct approach) — in their respective test files
- test_main.py failure names: `test_orchestrator_in_app_state`, `test_multiple_strategies_registered_with_orchestrator`
