---BEGIN-CLOSE-OUT---

**Session:** Impromptu 2026-04-20 — Lifespan Hang + API Health Observability
**Date:** 2026-04-20
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/api/server.py | modified | Background HQS init via asyncio.to_thread + create_task; cancel on shutdown |
| argus/main.py | modified | Added `_wait_for_port()` method; gated health signal on port bind |
| scripts/start_live.sh | modified | Post-startup health probe + orphaned Vite cleanup |
| tests/api/test_lifespan_startup.py | added | 4 regression tests for lifespan timing + port probe |
| tests/scripts/test_start_live_probe.py | added | 2 tests for start_live.sh probe behavior |
| CLAUDE.md | modified | DEF-155, DEF-156, DEF-157 logged |
| docs/sprint-history.md | modified | AS entry for this impromptu |
| dev-logs/2026-04-20_lifespan-hang.md | added | Dev log summary |
| docs/sprints/sprint-31.8/session-1-lifespan-hang-closeout.md | added | This file |

### Judgment Calls
- **Background task over timeout**: Chose `asyncio.create_task(asyncio.to_thread(...))` for the HQS init rather than `asyncio.wait_for(..., timeout=N)` because the HQS is useful when it eventually completes — killing it after 30s would make it permanently unavailable until next restart. Background fire-and-forget preserves eventual availability.
- **Port probe approach**: Used a simple TCP socket `connect()` probe in `_wait_for_port()` rather than an HTTP health check because the lifespan handler hasn't `yield`ed yet (no routes available). Once the port accepts TCP connections, uvicorn has completed startup.
- **`/api/v1/market/status` for start_live.sh probe**: This endpoint requires no auth (GET /api/v1/market/status is the only unauthenticated endpoint) and confirms the full request pipeline is working.
- **60s timeout in main.py vs 15s in start_live.sh**: main.py needs to tolerate the full lifespan (which could be slow if VIX/intelligence initialization is heavy). start_live.sh uses 15s because by the time it probes, the main.py port-wait has already passed.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Diagnose lifespan hang root cause | DONE | HistoricalQueryService scanning 983K Parquet files (12 min) blocking lifespan yield |
| Fix lifespan hang with regression test | DONE | server.py:466-506 background task; test_lifespan_startup.py |
| Eliminate premature api_server healthy signal | DONE | main.py:1288-1320 _wait_for_port; test_wait_for_port_* |
| Post-startup probe in start_live.sh | DONE | start_live.sh:130-161; test_start_live_probe.py |
| Investigate evaluation.db bloat | DONE | DEF-157 logged with full findings (no fix applied) |
| DEF entries logged | DONE | DEF-155 (resolved), DEF-156 (resolved), DEF-157 (open) |
| Sprint-history entry | DONE | AS entry in docs/sprint-history.md |
| Close-out + dev-log written | DONE | This file + dev-logs/2026-04-20_lifespan-hang.md |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Port 8000 listening after startup | PASS | test_lifespan_startup tests verify client can make requests |
| No regression to Databento streaming | PASS | DatabentoDataService tests pass; block_for_close untouched |
| No regression to strategy registration | PASS | Full suite passes; no strategy files modified |
| WebSocket endpoints still accept connections | PASS | No WS changes; existing WS tests pass |
| Lifespan respects config-gating | PASS | test_lifespan_proceeds_when_hqs_cache_missing verifies disabled path |
| No added imports of block_for_close | PASS | grep shows same 2 existing uses only |
| Sprint 31.75 files untouched | PASS | No changes to experiments/, historical_query_service.py, run_experiment.py, etc. |

### Test Results
- **Before:** 4,899 pytest + 846 Vitest = 5,745 total
- **After:** 4,905 pytest + 846 Vitest = 5,751 total
- **New:** 6 tests (4 lifespan + 2 start_live probe)
- **All passing:** Yes

### Deferred Items
- DEF-157 (evaluation.db VACUUM) — intentionally not fixed per prompt constraints
- No new DEC needed — the health signal gating doesn't change architecture, just fixes a timing bug

### Context State
GREEN — session completed well within context limits, single-pass implementation.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "Impromptu 2026-04-20",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5745,
    "after": 5751,
    "new": 6,
    "all_pass": true,
    "pytest_count": 4905,
    "vitest_count": 846
  },
  "files_created": [
    "tests/api/test_lifespan_startup.py",
    "tests/scripts/test_start_live_probe.py",
    "dev-logs/2026-04-20_lifespan-hang.md",
    "docs/sprints/sprint-31.8/session-1-lifespan-hang-closeout.md"
  ],
  "files_modified": [
    "argus/api/server.py",
    "argus/main.py",
    "scripts/start_live.sh",
    "CLAUDE.md",
    "docs/sprint-history.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "evaluation.db write volume (36K events/min) may need throttling or sampling if it causes I/O pressure during trading hours",
    "HistoricalQueryService could be made truly lazy (defer VIEW creation to first query) for even faster startup"
  ],
  "doc_impacts": [
    {
      "document": "CLAUDE.md",
      "change_description": "DEF-155, DEF-156, DEF-157 added to deferred items table"
    },
    {
      "document": "docs/sprint-history.md",
      "change_description": "AS entry added for this impromptu"
    }
  ],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "Root cause was NOT an infinite hang but a 12-minute blocking call in the lifespan handler. The py-spy block_for_close thread was a red herring (normal Databento behavior). Fix backgrounds the slow init without changing HistoricalQueryService itself (which is off-limits per Sprint 31.75 constraints)."
}
```
