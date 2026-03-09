# Sprint 23.3, Session 1: Universe Manager Wide Pipe + Warm-Up Fix

## Pre-Flight Checks
Before making any changes:
1. Read these files to load context:
   - `argus/data/fmp_reference.py` (FMP reference client — already migrated to stable endpoints)
   - `argus/data/fmp_scanner.py` (FMP scanner — reference for stable endpoint patterns and async HTTP usage)
   - `argus/data/universe_manager.py` (Universe Manager — understand `build_viable_universe()` interface)
   - `argus/data/databento_data_service.py` (Data service — find the indicator warm-up call)
   - `argus/main.py` (Startup wiring — Phase 11 warm-up, Universe Manager initialization)
   - `config/system_live.yaml` (Live config with universe_manager section)
   - `CLAUDE.md`
2. Run the test suite: `python -m pytest tests/ -x -q`
   Expected: ~2,289 tests, all passing
3. Verify you are on the correct branch: `main`
4. Confirm `config/system_live.yaml` has `universe_manager.enabled: true` committed

## Objective
Complete the Universe Manager's full-universe architecture (DEC-263, DEC-299) by
feeding it the complete FMP stock-list (~8,000 symbols) instead of the scanner's
15-symbol watchlist, and fix the warm-up bug where indicator warm-up runs for
excluded symbols when the Universe Manager is active.

## Background
During live deployment testing on March 9, 2026:
- The Universe Manager infrastructure works correctly (system filters, routing table,
  fast-path discard) but receives only 15 scanner symbols instead of the full universe.
- FMP's `/stable/stock-list` endpoint returns ~8,000 symbols (confirmed via curl on
  Starter tier). Each symbol then needs a per-symbol `/stable/profile` call for
  reference data (FMP Starter does not support batch).
- At 300 calls/min rate limit with async concurrency, ~8,000 symbols takes ~27 minutes.
  This is acceptable — the system starts early enough to accommodate.
- The FMP stable API migration hotfix has already been committed to `main` (DEC-298).

## Requirements

### Requirement 1: Add `fetch_stock_list()` to FMPReferenceClient
In `argus/data/fmp_reference.py`:

1. Add an async method `fetch_stock_list() -> list[str]` that:
   - Calls `GET /stable/stock-list?apikey={key}` (same base URL pattern as existing methods)
   - Parses the JSON response — an array of objects with at minimum `symbol` and `companyName` fields
   - Returns a list of symbol strings (just the `symbol` field from each object)
   - Logs the total count: `INFO  Fetched {N} symbols from FMP stock-list`
   - On failure (network error, non-200 status, JSON parse error): logs `ERROR`, returns empty list
   - Does NOT do any filtering — returns the raw complete list

### Requirement 2: Async Concurrent Profile Fetching with Rate Limiting
In `argus/data/fmp_reference.py`:

The existing `fetch_reference_data(symbols)` method fetches profiles per-symbol (after
the stable API migration, batch is not available). Update it to handle ~8,000 symbols
efficiently:

1. Use an `asyncio.Semaphore(5)` to limit concurrent requests (5 in-flight at once)
2. Add a per-call minimum spacing of 0.2 seconds (to stay well under 300/min)
3. Add retry logic: 3 retries per symbol with exponential backoff (2s, 4s, 8s)
   on transient failures (HTTP 429, 5xx, network timeout). Non-retryable errors
   (4xx other than 429) fail immediately for that symbol.
4. Failed symbols after all retries are logged at WARNING and excluded (fail-closed
   per DEC-277 — a symbol with no reference data is not promoted to viable)
5. Add progress logging every 500 symbols:
   ```
   INFO  Fetching reference data: 500/8000 (6%) — 487 succeeded, 13 failed [2m 14s elapsed]
   INFO  Fetching reference data: 1000/8000 (12%) — 981 succeeded, 19 failed [4m 28s elapsed]
   ...
   INFO  Reference data fetch complete: 7850/8000 succeeded in 26m 42s (150 failed)
   ```
6. Return the reference data dict as before — the interface to `build_viable_universe()`
   does not change.

**Important:** Review how the existing `fetch_reference_data()` is structured. If it
already loops per-symbol, you're adding concurrency + retries + progress to the
existing loop. If it does something else, adapt accordingly. Do not change the
method signature or return type.

### Requirement 3: Update `main.py` Startup Wiring
In `argus/main.py`:

1. **When Universe Manager is ENABLED:**
   a. Fetch the full stock list: `all_symbols = await fmp_reference.fetch_stock_list()`
   b. If `all_symbols` is empty (stock-list endpoint failed), fall back to scanner
      symbols with a loud warning:
      ```
      WARNING  FMP stock-list fetch failed — falling back to scanner symbols ({N} symbols).
               Universe Manager will operate with reduced universe.
      ```
   c. Pass the symbol list (full or fallback) to `universe_manager.build_viable_universe()`
   d. Use the viable symbols (from `build_viable_universe()`) for indicator warm-up —
      NOT the scanner symbols or the full stock list
   e. If the viable set is empty (all symbols filtered out — possible if FMP is returning
      garbage data), log `ERROR` and fall back to scanner symbols for warm-up

2. **When Universe Manager is DISABLED:**
   a. Behavior unchanged — use scanner symbols for warm-up (existing code path)
   b. Do NOT call `fetch_stock_list()` — no FMP calls beyond what the scanner already does

3. The FMP Scanner continues to run regardless of Universe Manager state — it provides
   the pre-market watchlist display. The Universe Manager input is independent of the scanner.

### Requirement 4: Retroactive Tests for Stable API Migration
The DEC-298 hotfix was committed without tests. Add tests for the stable endpoint behavior:

1. Test `fetch_stock_list()`:
   - Successful response: returns list of symbol strings
   - Empty response: returns empty list
   - Network error: returns empty list, logs error
   - Non-200 status: returns empty list, logs error

2. Test `fetch_reference_data()` with concurrency:
   - Small batch (5 symbols): all succeed, returns complete reference data
   - Mixed results: some symbols fail, successful ones still returned (fail-closed)
   - All fail: returns empty dict
   - Retry behavior: transient 429 → succeeds on retry
   - Progress logging: verify log messages at expected intervals (mock time if needed)

3. Test `main.py` warm-up integration (may require mocking):
   - Universe Manager enabled + stock-list succeeds: warm-up uses viable symbols
   - Universe Manager enabled + stock-list fails: warm-up falls back to scanner symbols
   - Universe Manager enabled + viable set empty: warm-up falls back to scanner symbols
   - Universe Manager disabled: warm-up uses scanner symbols (existing behavior)

## Constraints
- Do NOT modify: `argus/data/universe_manager.py` (already correct — accepts any symbol list)
- Do NOT modify: Strategy files, AI layer, Orchestrator, Risk Manager, Event Bus
- Do NOT modify: `argus/data/databento_data_service.py` (the warm-up call originates from `main.py`)
- Do NOT change: The `build_viable_universe()` interface or return type
- Do NOT change: The FMP Scanner behavior or its endpoints
- Do NOT add: Any symbol-pattern pre-filtering or heuristic exclusions before profile fetching.
  All filtering happens inside `build_viable_universe()` using actual reference data.
- The existing FMP stable endpoint migration in `fmp_reference.py` is correct — do not
  revert or restructure it. Build on top of it.

## Test Targets
After implementation:
- Existing tests: all must still pass
- New tests to write:
  - `test_fetch_stock_list_success` — returns symbol list from valid response
  - `test_fetch_stock_list_empty_response` — returns empty list
  - `test_fetch_stock_list_network_error` — returns empty list, logs error
  - `test_fetch_stock_list_non_200` — returns empty list, logs error
  - `test_fetch_reference_data_concurrent_success` — small batch, all succeed
  - `test_fetch_reference_data_partial_failure` — some fail, rest returned
  - `test_fetch_reference_data_all_fail` — returns empty dict
  - `test_fetch_reference_data_retry_on_429` — retries transient, succeeds
  - `test_fetch_reference_data_progress_logging` — log messages at intervals
  - `test_warmup_uses_viable_symbols_when_um_enabled` — warm-up input is viable set
  - `test_warmup_fallback_on_stocklist_failure` — falls back to scanner symbols
  - `test_warmup_fallback_on_empty_viable` — falls back to scanner symbols
  - `test_warmup_uses_scanner_symbols_when_um_disabled` — existing behavior preserved
- Minimum new test count: 13
- Test command: `python -m pytest tests/ -x -q`

## Definition of Done
- [ ] `fetch_stock_list()` method added and working
- [ ] `fetch_reference_data()` updated with async concurrency, rate limiting, retries, progress logging
- [ ] `main.py` wiring updated: full stock-list → Universe Manager → viable symbols → warm-up
- [ ] Fallback behavior working: stock-list failure → scanner symbols; empty viable → scanner symbols
- [ ] All 13+ new tests written and passing
- [ ] All existing ~2,289 tests still passing
- [ ] No modifications to universe_manager.py, strategy files, AI layer, or other constrained files

## Regression Checklist (Session-Specific)
After implementation, verify each of these:
| Check | How to Verify |
|-------|---------------|
| Universe Manager disabled path unchanged | `python -m pytest tests/ -k "universe" -x -q` — all existing UM tests pass |
| FMP Scanner still works independently | `python -m pytest tests/ -k "fmp_scanner" -x -q` |
| Existing strategy tests unaffected | `python -m pytest tests/strategies/ -x -q` |
| No imports added to constrained files | `git diff --name-only` shows only `fmp_reference.py`, `main.py`, and test files |
| Config files not modified | `git diff config/` shows no changes (or only `system_live.yaml` if UM enabled flag wasn't committed) |

## Close-Out
After all work is complete, follow the close-out skill in .claude/skills/close-out.md.

The close-out report MUST include a structured JSON appendix at the end,
fenced with ```json:structured-closeout. See the close-out skill for the
full schema and requirements.

## Sprint-Level Regression Checklist (for Tier 2 reviewer)
| Check | How to Verify |
|-------|---------------|
| All existing tests pass | `python -m pytest tests/ -x -q` — 2,289+ passing |
| Universe Manager disabled path unchanged | Disable UM in config, run UM tests — same behavior |
| FMP Scanner independent operation | Scanner tests pass, scanner not called differently |
| No constrained files modified | `git diff --name-only` check |
| Warm-up only runs for viable symbols when UM enabled | New test + log inspection |
| Fallback to scanner symbols on stock-list failure | New test covers this |
| Fail-closed behavior preserved | Symbols with failed profile fetch excluded from viable set |

## Sprint-Level Escalation Criteria (for Tier 2 reviewer)
Escalate to Tier 3 if:
1. The `build_viable_universe()` interface was changed (should be untouched)
2. Any strategy files, AI layer, Orchestrator, or Risk Manager files were modified
3. The warm-up path for Universe Manager DISABLED does not match pre-session behavior
4. The FMP Scanner's behavior was altered
5. Rate limiting or retry logic could cause startup to exceed 45 minutes (review the math)
6. New dependencies were added beyond what's already in requirements.txt
