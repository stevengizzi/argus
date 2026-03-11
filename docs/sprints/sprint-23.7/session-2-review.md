# Tier 2 Review: Sprint 23.7, Session 2

## Instructions
You are conducting a Tier 2 code review. This is a READ-ONLY session.
Do NOT modify any files.

Follow the review skill in .claude/skills/review.md.

Your review report MUST include a structured JSON verdict at the end,
fenced with ```json:structured-verdict. See the review skill for the
full schema and requirements.

## Review Context
Read the following file for the Sprint Spec, Specification by Contradiction,
Sprint-Level Regression Checklist, and Sprint-Level Escalation Criteria:

`sprint-23.7/review-context.md`

## Tier 1 Close-Out Report
---BEGIN-CLOSE-OUT---

**Session:** Sprint 23.7, Session 2 — Reference Cache Resilience + API Double-Bind Fix
**Date:** 2026-03-11
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/data/fmp_reference.py | modified | Added periodic checkpoint saves every 1,000 symbols, shutdown signal handling, and shutdown flag |
| argus/api/server.py | modified | Added port-availability guard (`check_port_available`, `PortInUseError`), removed duplicate WebSocket bridge start from lifespan |
| argus/main.py | modified | Added PortInUseError handling with headless mode fallback, added Universe Manager shutdown (saves reference cache) |
| tests/data/test_fmp_reference.py | modified | Added 8 tests for periodic checkpoints and shutdown handling |
| tests/api/test_server.py | modified | Added 4 tests for port-availability guard |

### Judgment Calls
Decisions made during implementation that were NOT specified in the prompt:
- **Pre-populate internal cache before incremental fetch**: When `fetch_reference_data_incremental()` calls `fetch_reference_data()`, I pre-populate `self._cache` with valid (non-stale) entries so checkpoint saves include both old and new data.
- **Reset `_shutdown_requested` flag in `start()`**: Added reset to ensure clean state when reusing a client instance.
- **Removed duplicate WebSocket bridge start from lifespan**: The lifespan handler was starting the WebSocket bridge, but main.py already does this. Removed the duplicate to simplify the startup flow.
- **Headless mode on port conflict**: When `PortInUseError` is raised, the system continues without the API server rather than crashing completely.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| Cache saves every 1,000 symbols during fetch | DONE | fmp_reference.py:fetch_reference_data, lines 376-385 |
| Use atomic writes (temp file + rename) | DONE | Already implemented in save_cache(), verified |
| Log each periodic save | DONE | fmp_reference.py:fetch_reference_data, lines 381-385 |
| Shutdown signal handling triggers cache save | DONE | fmp_reference.py:stop(), lines 267-279 |
| Partial cache used on next startup | DONE | Already working via get_stale_symbols(), enhanced pre-population in fetch_reference_data_incremental() |
| Investigate API double-bind root cause | DONE | Documented: duplicate WS bridge start in lifespan + no port guard |
| Fix double-bind root cause | DONE | Removed duplicate WS bridge start from server.py lifespan |
| Add port-availability guard | DONE | server.py:check_port_available + PortInUseError + main.py handling |
| 7+ new tests | DONE | 14 new tests added |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Cache format unchanged | PASS | Existing cache tests still pass |
| Full fetch still works end-to-end | PASS | Existing FMPReferenceClient tests pass |
| API server starts normally on clean boot | PASS | Startup tests pass |
| Startup sequence ordering unchanged | PASS | Steps 1-12 unchanged |
| No new dependencies introduced | PASS | No changes to requirements.txt/pyproject.toml |

### Test Results
- Tests run: 2511
- Tests passed: 2511
- Tests failed: 0
- New tests added: 14
- Command used: `python -m pytest tests/ -x -q`

### Unfinished Work
None

### Notes for Reviewer
- **Root cause analysis**: The API double-bind issue appears to be caused by (1) duplicate WebSocket bridge start in both main.py and lifespan handler, and (2) no guard against port already in use. The "different PID" symptom may have been from a previous ARGUS instance that didn't fully shut down.
- **Defense in depth**: The port-availability guard checks before uvicorn starts. If the port is occupied, the system continues in "headless mode" without the API server rather than crashing.
- **Checkpoint save concurrency**: The checkpoint save happens inside the counter_lock, which is safe but could cause brief pauses during high-frequency fetching. In practice, 1,000 symbols takes several minutes to accumulate, so this is not a concern.

---END-CLOSE-OUT---

## Review Scope
- Diff to review: `git diff HEAD~1`
- Test command: `python -m pytest tests/ -x -q`
- Files that should NOT have been modified: strategy files, orchestrator,
  risk manager, order manager, frontend code, AI layer, intelligence pipeline,
  databento_data_service.py (Session 1 scope)

## Session-Specific Review Focus
1. Verify periodic cache saves use atomic writes (temp file + rename), not
   direct writes that could corrupt on kill
2. Verify the 1,000-symbol checkpoint interval is based on successful fetches,
   not total attempts (failed symbols should not inflate the counter)
3. Verify the incremental fetch logic respects partially cached data — a
   cache with 15,000 symbols should result in ~22,000 incremental fetches,
   not 37,000
4. Verify the shutdown signal handler actually triggers during an active
   fetch (not just during idle)
5. Verify the API server double-bind root cause is documented in the
   close-out report
6. Verify the port-availability guard uses a proper socket check, not just
   a try/except around uvicorn.run()
7. Verify the port guard does not introduce a TOCTOU race (time-of-check
   vs time-of-use) — acceptable as defense-in-depth since the root cause
   is also fixed, but note if present
8. Verify the cache JSON schema is unchanged (backward compatible with
   existing cache files)

## Additional Context
This session addresses two independent bugs. Part A (cache saves) prevents
data loss on interrupted cold-starts (previously required re-doing a 2-hour
fetch). Part B (API double-bind) prevents a boot crash observed when
restarting ARGUS rapidly. The reviewer should treat these as independent
changes that happen to be in the same session for efficiency.