## Sprint Spec

### Goal
Fix three bugs that prevent ARGUS from booting and operating reliably with the
full-universe Universe Manager (Sprint 23) enabled. Without these fixes, no
further QA or Sprint 24 work is possible.

### Deliverables

1. **Time-aware indicator warm-up:** Replace the current blocking per-symbol
   warm-up with a time-aware approach: skip warm-up entirely when booting
   pre-market; perform lazy per-symbol backfill on first candle arrival when
   booting mid-session.

2. **Periodic reference cache saves:** Save the reference data cache
   incrementally during long fetches (every 1,000 symbols) and on shutdown
   signal, so interrupted cold-starts preserve progress.

3. **API server double-bind fix:** Identify and fix the root cause of uvicorn
   starting twice during boot, and add a port-availability guard as defense
   in depth.

### Acceptance Criteria

1. Time-aware warm-up:
   - Pre-market boot (before 9:30 ET): warm-up phase completes in <5 seconds
     regardless of universe size
   - Mid-session boot (after 9:30 ET): warm-up phase completes in <5 seconds;
     individual symbols are backfilled lazily on first candle arrival
   - Lazy backfill fetches historical data from market open to current time
     for the specific symbol before processing its first candle
   - Symbols that fail lazy backfill are logged and skipped (fail-open for
     warm-up, fail-closed for signal generation — indicators will be invalid,
     so no signals fire)
   - All existing DatabentoDataService tests pass
   - New tests cover both pre-market and mid-session paths

2. Periodic cache saves:
   - During reference data fetch, cache is saved to disk every 1,000 symbols
   - On SIGTERM/SIGINT during fetch, cache is saved before exit
   - Interrupted fetch followed by restart uses the partial cache (incremental
     fetch count should reflect saved progress)
   - All existing FMPReferenceClient tests pass

3. API server double-bind:
   - Root cause identified and fixed in main.py or api/server.py
   - Port-availability check added before uvicorn.run() — if port is occupied,
     log a clear error message and skip the second bind attempt
   - No regression in normal single-boot startup

### Config Changes
No config changes in this sprint.

---

## Specification by Contradiction

### Out of Scope
1. **Batch historical API approach:** We are NOT using a single ALL_SYMBOLS
   historical request for mid-session warm-up. We are using lazy per-symbol
   backfill. (Batch approach is architecturally cleaner but has unknown
   Databento API behavior for ALL_SYMBOLS historical.)
2. **Warm-up caching/persistence:** We are NOT caching warm-up results to disk.
   Warm-up is either skipped (pre-market) or done live (mid-session).
3. **Exchange pre-filtering for reference data:** We are NOT changing the
   reference data fetch scope (the ~37K symbol fetch). That optimization is
   deferred.
4. **Databento reconnection retry logic (Bug 4):** Not in this sprint.
5. **FMP rate limit handling (Bug 5):** Not in this sprint.

### Edge Cases to Reject
1. Boot exactly at 9:30:00 ET: treat as pre-market (no warm-up). The live
   stream will deliver the first candle within seconds and indicators begin
   building naturally.
2. Boot during extended hours (pre-market 4:00–9:30, after-hours 4:00–8:00):
   treat as pre-market (no warm-up). ARGUS strategies only operate during
   regular hours.
3. Partial cache with corrupted JSON: log error, discard cache, proceed with
   full fetch.

### Scope Boundaries
- Do NOT modify: strategy files, orchestrator, risk manager, order manager,
  any frontend code, AI layer, intelligence pipeline
- Do NOT optimize: reference data fetch scope or speed (beyond periodic saving)
- Do NOT refactor: IndicatorEngine internals, Event Bus, Broker abstraction
- Do NOT add: new config fields, new API endpoints, new dependencies

### Interaction Boundaries
- This sprint does NOT change the IndicatorEngine API or behavior
- This sprint does NOT change the DatabentoDataService streaming/subscription behavior
- This sprint does NOT change the Universe Manager filtering or routing logic
- This sprint does NOT change how strategies receive or process candles

---

## Sprint-Level Regression Checklist

| Check | How to Verify |
|-------|---------------|
| All existing pytest tests pass | `cd ~/Documents/Coding\ Projects/argus && python -m pytest tests/ -x -q` |
| DatabentoDataService can still warm up a small symbol set | Run existing warm-up tests — they should still work for the scanner-symbol path |
| FMPReferenceClient fetch + cache round-trip works | Run existing reference client tests |
| API server starts on port 8000 without error | Run the startup sequence test or manual boot |
| Universe Manager routing table builds correctly | Run existing Universe Manager tests |
| Strategies still receive candles via Event Bus | Run existing strategy integration tests |

## Sprint-Level Escalation Criteria

Escalate to Tier 3 if:
- The warm-up changes alter the IndicatorEngine interface or require changes
  to how strategies consume indicator data
- The lazy backfill introduces async concurrency patterns that could conflict
  with the Event Bus FIFO guarantee (DEC-025)
- The API server fix requires changes to the FastAPI app factory or middleware
  stack
- Any fix touches more than the files listed in the session scope