# Sprint 23.7, Session 2: Reference Cache Resilience + API Double-Bind Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_reference.py` (reference client and cache logic)
   - `argus/main.py` (startup sequence, API server launch)
   - `argus/api/server.py` (FastAPI app creation)
   - `CLAUDE.md`
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ~2497+ tests (Session 1 added ~7), all passing
3. Verify you are on the correct branch: `sprint-23.7`
4. Verify Session 1 changes are committed

## Objective
Make the reference data cache resilient to interrupted fetches by saving
incrementally, and fix the API server double-bind bug that crashes the system
on certain restart timings.

## Requirements

### Part A: Periodic Reference Cache Saves

1. **In `argus/data/fmp_reference.py` — add periodic cache saves during fetch:**
   - During the reference data fetch loop (the one that iterates through
     batches of symbols), save the cache to disk every 1,000 successfully
     fetched symbols.
   - Use the same cache save mechanism that currently runs at the end of
     the fetch (write to `data/reference_cache.json`).
   - Use atomic writes (write to a temp file, then rename) to prevent
     corruption if the process is killed mid-write. If atomic writes are
     already used, confirm and note in close-out.
   - Log each periodic save: `"Reference cache checkpoint: {N} symbols
     saved to {path}"` at INFO level.

2. **In `argus/data/fmp_reference.py` — add shutdown signal handling:**
   - Register a callback or flag that triggers a cache save when the
     application is shutting down (SIGTERM/SIGINT).
   - This may already be partially handled by the existing shutdown sequence
     in main.py. Check if the FMPReferenceClient's shutdown/cleanup path
     includes a cache save. If not, add one.
   - If the fetch is still in progress when shutdown is requested, save
     whatever has been fetched so far.

3. **Ensure incremental fetch respects partial cache:**
   - On startup, if the cache contains, say, 15,000 symbols from an
     interrupted fetch, the incremental logic should recognize those 15,000
     as fresh and only fetch the remaining ~22,000.
   - Verify this is already the case by reading the incremental fetch logic.
     If it compares against the cache's symbol set, it should work. If it
     only checks a "last full fetch" timestamp, it may re-fetch everything —
     fix this.

### Part B: API Server Double-Bind Fix

4. **In `argus/main.py` (or wherever uvicorn is launched) — investigate the
   double-bind root cause:**
   - From the logs: the API server starts successfully at step [12/12],
     then a SECOND uvicorn process (different PID) attempts to bind the
     same port and crashes.
   - Look for: duplicate `uvicorn.run()` calls, FastAPI startup events that
     spawn a second server, or middleware/lifespan handlers that re-invoke
     the server.
   - The second instance logged `Started server process [31953]` with its
     own AI services initialization, suggesting a full second app startup.
   - Document the root cause in the close-out report.

5. **In `argus/main.py` — fix the root cause:**
   - Remove or guard the code path that causes the second uvicorn invocation.
   - The fix depends on what the investigation finds. Common causes:
     - uvicorn's `reload=True` in production config
     - A `multiprocessing` or `workers>1` setting
     - A startup lifespan event that accidentally re-invokes the server
     - A duplicate call to `uvicorn.run()` in an if/else branch

6. **In `argus/main.py` — add port-availability guard (defense in depth):**
   - Before calling `uvicorn.run()`, check if the target port is already
     in use (try binding a socket, then close it).
   - If the port is occupied, log a CRITICAL error:
     `"Port {port} already in use — cannot start API server. Is another
     ARGUS instance running?"` and either skip the API server startup
     (system runs headless) or raise a clear exception.
   - This guard catches the double-bind scenario even if the root cause
     fix misses an edge case, and also handles the case where a previous
     ARGUS instance wasn't cleanly shut down.

## Constraints
- Do NOT modify: strategy files, orchestrator, risk manager, order manager,
  any frontend code, AI layer, intelligence pipeline
- Do NOT modify: `argus/data/databento_data_service.py` (Session 1 scope)
- Do NOT change: the FMPReferenceClient's fetch logic, batching, or retry
  behavior (only add save checkpoints)
- Do NOT change: the FastAPI app's routes, middleware, or WebSocket endpoints
- Do NOT add: new config fields or dependencies
- PRESERVE: the existing cache format (JSON, same schema)
- PRESERVE: the existing startup sequence ordering (steps 1–12)

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  1. Test periodic cache save: mock a fetch of 2,500 symbols, verify cache
     is saved at 1,000 and 2,000 marks (2 intermediate saves + 1 final)
  2. Test cache save uses atomic writes: verify temp file + rename pattern
  3. Test interrupted fetch preserves partial cache: mock a fetch that fails
     at symbol 1,500, verify cache contains ~1,000 symbols from the
     checkpoint
  4. Test incremental fetch after partial cache: load a partial cache with
     1,000 symbols, start a fetch of 2,000 total, verify only ~1,000 new
     symbols are fetched
  5. Test port-availability guard: mock port 8000 as occupied, verify the
     guard prevents uvicorn.run() and logs CRITICAL
  6. Test port-availability guard (port free): mock port 8000 as available,
     verify uvicorn.run() proceeds normally
  7. Test shutdown during fetch triggers cache save: simulate SIGTERM during
     an active fetch, verify cache is saved with current progress
- Minimum new test count: 7
- Test command: `python -m pytest tests/ -x -q`

## Definition of Done
- [ ] Cache saves every 1,000 symbols during fetch
- [ ] Shutdown during fetch saves partial cache
- [ ] Partial cache is used on next startup (incremental fetch is smaller)
- [ ] API server double-bind root cause identified and documented
- [ ] Double-bind root cause fixed
- [ ] Port-availability guard added
- [ ] All existing tests pass
- [ ] 7+ new tests written and passing

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Cache format unchanged | Load a cache file from before this session, verify it still works |
| Full fetch still works end-to-end | Existing FMPReferenceClient tests pass |
| API server starts normally on clean boot | Existing startup tests or manual verification |
| Startup sequence ordering unchanged | Steps 1–12 execute in same order |
| No new dependencies introduced | Check requirements.txt / pyproject.toml diff |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)

| Check | How to Verify |
|-------|---------------|
| All existing pytest tests pass | `python -m pytest tests/ -x -q` |
| DatabentoDataService can still warm up a small symbol set | Existing warm-up tests pass |
| FMPReferenceClient fetch + cache round-trip works | Existing reference client tests pass |
| API server starts on port 8000 without error | Startup sequence test or manual boot |
| Universe Manager routing table builds correctly | Existing Universe Manager tests pass |
| Strategies still receive candles via Event Bus | Existing strategy integration tests pass |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)

Escalate to Tier 3 if:
- The warm-up changes alter the IndicatorEngine interface
- The lazy backfill introduces async concurrency patterns that could conflict
  with Event Bus FIFO (DEC-025)
- The API server fix requires changes to the FastAPI app factory or middleware
- Any fix touches more than the files listed in the session scope