# Sprint 25.9, Session 2: Cache Checkpoint Fix + Trust Cache on Startup

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `docs/project-knowledge.md` (current state, data service architecture)
   - `docs/sprints/sprint-25.9/sprint-25.9-review-context.md` (sprint spec)
   - `argus/data/fmp_reference.py` (FMPReferenceClient — cache logic, checkpoint saves, build_viable_universe)
   - `argus/data/universe_manager.py` (UniverseManager — startup integration)
   - `argus/main.py` (startup phases, especially Phase 7.5 where universe build happens)
   - `config/system.yaml` and `config/system_live.yaml` (current config structure)
2. Run the test baseline (DEC-328 — Session 2, scoped):
   ```
   python -m pytest tests/data/ -x -q
   ```
   Expected: all passing (full suite was confirmed by Session 1 close-out)
3. Verify you are on branch `main`
4. Examine the current cache save logic in `fmp_reference.py` — specifically the periodic save (every 1,000 symbols, DEC-317) and the final save. Understand the data structure before modifying.

## Objective
Fix the data-destructive cache checkpoint bug (B1/DEC-361) and implement trust-cache-on-startup (B2/DEC-362/DEF-063 resolution) so that Monday boots and post-holiday boots don't trigger full reference data re-fetches that block market open.

## Requirements

### B1: Cache Checkpoint Merge Fix (DEC-361)

1. In `argus/data/fmp_reference.py`, find the checkpoint save logic (periodic save every 1,000 symbols during fetch, DEC-317, and the final save at end of fetch).

   **Current behavior (buggy):** The checkpoint writes only the freshly-fetched symbols to `data/reference_cache.json`, discarding all previously-cached entries.

   **Required behavior:** The checkpoint must write the UNION of:
   - All previously-cached entries that are NOT being re-fetched in this batch (preserved as-is)
   - All freshly-fetched entries so far (new data replaces old for the same symbol)

   Implementation approach:
   ```python
   # At the start of a fetch cycle, load the full existing cache into memory
   # (this should already happen — verify)
   existing_cache = self._load_cache()  # or however the cache is loaded
   
   # During fetch, new entries are accumulated (verify the data structure)
   # e.g., self._fetched_data[symbol] = new_data
   
   # At checkpoint time (every 1,000 symbols) and final save:
   merged = {**existing_cache, **self._fetched_data}  # new overwrites old for same symbol
   self._save_cache(merged)
   ```

   **Critical:** The merge must be `existing ∪ new` with new taking precedence for duplicate keys. The existing cache data must be loaded into memory at the START of the fetch cycle and held throughout, so that checkpoints can always produce the full merged set.

   **Edge cases to handle:**
   - First-ever fetch (no existing cache): should work fine (empty dict ∪ new = new)
   - Fetch interrupted after some checkpoints: each checkpoint saved the correct merged state, so the cache file is always valid
   - Fetch with 0 stale symbols: no-op fetch, cache unchanged

2. Add a log line at each checkpoint showing the merge statistics:
   ```python
   logger.info(
       "Cache checkpoint: %d existing + %d fresh = %d total (fetched %d/%d stale)",
       len(existing_entries), len(fresh_entries), len(merged),
       fetched_count, total_stale_count
   )
   ```

### B2: Trust Cache on Startup (DEC-362 / DEF-063 Resolution)

3. Add a config option `trust_cache_on_startup` (default: `true`) to the appropriate config section. This likely belongs in the `universe_manager` or `reference_data` section of `system.yaml`. Check the existing config model structure and add it where it fits naturally.

   Add the field to the corresponding Pydantic config model.

4. Modify the startup flow in `argus/data/fmp_reference.py` (specifically `build_viable_universe` or its caller) to implement two-phase startup:

   **Phase 1 (synchronous, fast):** Load the cache file from disk. If `trust_cache_on_startup` is true AND cache exists AND cache is non-empty, return the cached data immediately for routing table construction. Log clearly:
   ```python
   logger.info(
       "Using cached reference data (%d symbols, cache age: %s). "
       "Background refresh will update stale entries.",
       len(cached_symbols), cache_age_str
   )
   ```

   **Phase 2 (async background task):** After the system is live, spawn an asyncio task that:
   - Identifies stale entries (using the existing staleness logic / TTL)
   - Fetches fresh data for stale entries in batches, respecting FMP rate limits
   - After all stale entries are refreshed, rebuilds the routing table atomically
   - Logs progress periodically and completion

   The background refresh task design:
   ```python
   async def _background_cache_refresh(self):
       """Refresh stale cache entries without blocking startup."""
       try:
           stale_symbols = self.get_stale_symbols()
           if not stale_symbols:
               logger.info("Reference cache is fresh — no background refresh needed")
               return
           
           logger.info("Background refresh: %d stale symbols to update", len(stale_symbols))
           
           # Fetch in batches, respecting rate limits
           for i, batch in enumerate(batched(stale_symbols, batch_size)):
               fresh_data = await self._fetch_batch(batch)
               # Merge into cache (using the B1 merge pattern)
               self._merge_and_save(fresh_data)
               
               if (i + 1) % 10 == 0:  # Log every 10 batches
                   logger.info("Background refresh: %d/%d symbols updated", 
                              min((i + 1) * batch_size, len(stale_symbols)), 
                              len(stale_symbols))
           
           logger.info("Background refresh complete: %d symbols updated", len(stale_symbols))
           
           # Signal the Universe Manager to rebuild routing table
           # (see requirement 6 below)
       except Exception:
           logger.exception("Background cache refresh failed — trading on stale cache")
   ```

5. **Task lifecycle:** The background refresh task must be:
   - Created AFTER the system is fully started and the event loop is running
   - Registered with the application's shutdown handler so it's cancelled cleanly on shutdown
   - Fire-and-forget from the startup perspective — failure logs a warning but doesn't block trading
   - Guarded: if `trust_cache_on_startup` is false, revert to the existing blocking behavior (fetch all stale entries synchronously before returning). This preserves backward compatibility.

   Find the appropriate place in `main.py` to spawn this task. It should be AFTER Phase 9.5 (routing table built) but BEFORE Phase 12 (API server start), or as a post-startup hook. Look at how other asyncio background tasks are spawned (e.g., regime reclassification, polling loop) and follow the same pattern.

6. **Routing table atomic rebuild:** After the background refresh completes, the Universe Manager needs to rebuild its routing table with the fresh data. This must be an atomic swap:
   - Build the new routing table in a local variable
   - Swap it into place with a single assignment (Python's GIL makes this safe for asyncio)
   - Update strategy watchlists from the new routing table
   - Log the rebuild:
     ```python
     logger.info(
         "Routing table rebuilt with fresh reference data: %d viable symbols",
         len(new_routing_table)
     )
     ```

   Check how `build_routing_table` currently works in `UniverseManager` and whether it supports being called again after initial startup. If not, ensure re-invocation is safe (idempotent or properly replaces previous state).

7. **Backward compatibility:** When `trust_cache_on_startup` is `false`:
   - Startup blocks on reference data fetch (existing behavior)
   - No background task is spawned
   - This is the safe fallback if the new behavior causes issues

## Constraints
- Do NOT modify any strategy files
- Do NOT modify Risk Manager, Order Manager, Event Bus, or Broker
- Do NOT modify the Observatory, AI layer, or Intelligence pipeline
- Do NOT change the FMP API endpoints or authentication
- Do NOT modify the reference data staleness criteria (TTL) — that's the config's job
- Do NOT introduce new pip dependencies
- The cache file format (`data/reference_cache.json`) must remain backward-compatible — an existing cache file must load correctly with the new code
- The background refresh must use the same FMP API methods as the existing fetch logic — no new API integration

## Config Validation
Write a test that loads the YAML config file and verifies the new
`trust_cache_on_startup` key is recognized by the Pydantic model.

1. Load `config/system.yaml` and extract the relevant section
2. Compare against the Pydantic model's `model_fields.keys()`
3. Assert no keys are present in YAML that are absent from the model

Expected mapping:
| YAML Key | Model Field |
|----------|-------------|
| `trust_cache_on_startup` | `trust_cache_on_startup` |

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:

  1. **B1 — Checkpoint merge preserves existing entries:** Create a cache with symbols A, B, C. Start a fetch that updates B and adds D. After checkpoint, cache contains A, B (fresh), C, D.
  2. **B1 — Checkpoint merge with empty existing cache:** First-ever fetch. Checkpoint writes only new entries. No crash.
  3. **B1 — Checkpoint merge with zero stale symbols:** Cache is fresh. Fetch is a no-op. Cache file unchanged.
  4. **B2 — Trust cache startup path:** With `trust_cache_on_startup=True` and a non-empty cache file, `build_viable_universe` returns immediately with cached data. Verify no FMP API calls are made synchronously.
  5. **B2 — Trust cache disabled reverts to blocking:** With `trust_cache_on_startup=False`, `build_viable_universe` blocks on fetching stale entries (existing behavior).
  6. **B2 — Trust cache with empty/missing cache file:** If cache doesn't exist, fall back to synchronous fetch regardless of config (can't trust an empty cache).
  7. **B2 — Background refresh task starts:** Verify that after startup, the background refresh task is created and runs.
  8. **B2 — Background refresh handles FMP errors gracefully:** Simulate FMP 429 during background refresh. Task logs error but doesn't crash.
  9. **B2 — Routing table rebuild after refresh:** After background refresh completes, verify the routing table is rebuilt and strategy watchlists are updated.
  10. **B1 — Concurrent checkpoint safety:** Verify that two sequential checkpoints during the same fetch both produce valid merged caches (no entries lost between checkpoints).

- Minimum new test count: 8
- Test command (close-out — final session, full suite):
  ```
  python -m pytest --ignore=tests/test_main.py -n auto -q
  ```

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Cache file format unchanged | Load existing cache with new code — no errors |
| Checkpoint save creates valid JSON | After checkpoint, `json.load(open(cache_path))` succeeds |
| Startup doesn't block when trust=true | Time startup with cache present — completes in seconds, not minutes |
| Startup blocks when trust=false | Time startup with trust=false — waits for fetch |
| Background refresh doesn't interfere with trading | Verify no strategy deactivation during refresh |
| Routing table rebuild doesn't drop symbols | Symbol count before/after rebuild is same or higher |
| Shutdown cancels background task cleanly | No "Task was destroyed" warnings in logs |
| Existing startup phases unchanged in order | Verify Phase 7–9.5 numbering/ordering in main.py |

## Definition of Done
- [ ] Cache checkpoint saves merge fresh + existing (B1 fix)
- [ ] Checkpoint merge logged with statistics
- [ ] `trust_cache_on_startup` config option added with Pydantic model
- [ ] Startup uses cached data immediately when trust=true
- [ ] Background refresh task spawned post-startup
- [ ] Background refresh handles errors gracefully (log, don't crash)
- [ ] Routing table rebuild after refresh is atomic
- [ ] Backward compatibility: trust=false reverts to blocking fetch
- [ ] All existing tests pass
- [ ] ≥8 new tests written and passing
- [ ] Config validation test passing
- [ ] Close-out report written to `docs/sprints/sprint-25.9/session-2-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
After all work is complete, follow the close-out skill in `.claude/skills/close-out.md`.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

**Write the close-out report to a file** (DEC-330):
`docs/sprints/sprint-25.9/session-2-closeout.md`

Do NOT just print the report in the terminal. Create the file, write the
full report (including the structured JSON appendix) to it, and commit it.

## Tier 2 Review (Mandatory — @reviewer Subagent)
After the close-out is written to file and committed, invoke the @reviewer
subagent to perform the Tier 2 review within this same session.

Provide the @reviewer with:
1. The review context file: `docs/sprints/sprint-25.9/sprint-25.9-review-context.md`
2. The close-out report path: `docs/sprints/sprint-25.9/session-2-closeout.md`
3. The diff range: `git diff HEAD~1`
4. The test command (final session, full suite): `python -m pytest --ignore=tests/test_main.py -n auto -q`
5. Files that should NOT have been modified: anything in `argus/strategies/`, `argus/execution/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`, `argus/backtest/`, `argus/core/orchestrator.py`

The @reviewer will produce its review report and write it to:
`docs/sprints/sprint-25.9/session-2-review.md`

## Post-Review Fix Documentation
If the @reviewer reports CONCERNS and you fix the findings within this same
session, update both the close-out and review report files per the standard
post-review fix protocol (see implementation-prompt template for full details).

## Session-Specific Review Focus (for @reviewer)
1. Verify checkpoint merge logic is `existing ∪ fresh` with fresh taking precedence — not the other way around, not additive without dedup
2. Verify the existing cache is loaded into memory at START of fetch cycle, not re-read at each checkpoint
3. Verify `trust_cache_on_startup=false` fully reverts to the pre-sprint blocking behavior
4. Verify background refresh task is properly registered for shutdown cancellation
5. Verify routing table rebuild is a single-assignment swap, not a mutation of the existing table
6. Verify no new `await` calls were added to the startup synchronous path when trust=true
7. Verify the cache file path hasn't changed (still `data/reference_cache.json`)
8. Verify the FMP rate limiting is respected during background refresh (batching, delays between batches)

## Sprint-Level Regression Checklist (for @reviewer)
| Check | How to Verify |
|-------|---------------|
| Cache checkpoint doesn't lose existing entries | Test: partial fetch + checkpoint → original entries still present |
| Cache load at startup is non-blocking when trust=true | Test: startup completes without waiting for FMP API |
| Cache load at startup IS blocking when trust=false | Test: backward-compatible behavior |
| Background refresh task starts and runs | Test: log output shows refresh task lifecycle |
| Background refresh doesn't crash on FMP errors | Test: simulate FMP 429/500 during refresh |
| Routing table swap is atomic | Test: no intermediate state where routing table is empty |
| Full test suite passes | `python -m pytest --ignore=tests/test_main.py -n auto -q` |

## Sprint-Level Escalation Criteria (for @reviewer)
Escalate to Tier 3 if:
1. Changes to startup sequence (main.py Phases 7–9.5) affect component initialization order
2. Background refresh introduces a new asyncio task lifecycle pattern not used elsewhere in the codebase
3. Cache merge logic requires file locking or cross-process synchronization
4. Any change to Risk Manager, Order Manager, or Event Bus behavior
