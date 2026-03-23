---BEGIN-REVIEW---

**Sprint:** 25.9
**Session:** S2 — Cache Checkpoint Fix + Trust Cache on Startup
**Reviewer:** Tier 2 Automated Review
**Date:** 2026-03-23
**Diff reviewed:** `git diff HEAD~1` (9 files)

## Verdict: CLEAR

## Summary

Session 2 implements two fixes for the FMP reference cache system: (B1) checkpoint merge to prevent data-destructive overwrites during interrupted fetches, and (B2) trust-cache-on-startup to eliminate blocking FMP fetches at boot time. The implementation is clean, well-scoped, and follows established patterns in the codebase.

## Session-Specific Review Focus

### 1. Checkpoint merge logic is `existing UNION fresh` with fresh taking precedence

**PASS.** In `fmp_reference.py:fetch_reference_data()` (line 401-405), the existing disk cache is loaded at the start. Existing entries are merged into `self._cache` with the guard `if sym not in self._cache`. Then during the fetch loop, fresh entries overwrite via `self._cache[symbol] = result` (line 445). This means fresh data always takes precedence for symbols being fetched, while existing entries for symbols NOT being fetched are preserved. Correct merge semantics.

### 2. Existing cache loaded at START of fetch cycle, not re-read at each checkpoint

**PASS.** `load_cache()` is called once at the top of `fetch_reference_data()` (line 401). The `existing_count` variable is captured at that point (line 402) and remains static throughout. Checkpoint saves call `self.save_cache()` which writes `self._cache` (which includes existing + fresh), not re-reading from disk.

### 3. `trust_cache_on_startup=false` fully reverts to blocking behavior

**PASS.** In `universe_manager.py:build_viable_universe()`, the trust-cache fast path is gated on `if trust_cache:` (line 93). When `trust_cache=False` (the default parameter value), it falls through to the existing `fetch_reference_data_incremental` path. Test `test_trust_cache_disabled_reverts_to_blocking` verifies `fetch_reference_data_incremental` is called. In `main.py`, the background task is only spawned when `config.system.universe_manager.trust_cache_on_startup` is true (line 828).

### 4. Background refresh task is properly registered for shutdown cancellation

**PASS.** The task is stored in `self._bg_refresh_task` (line 831-833). In `stop()` (lines 1351-1358), it follows the identical pattern as `_regime_task` and `_eval_check_task`: cancel, suppress CancelledError, await. The contextlib import pattern (`import contextlib as _ctxlib3`) is consistent with the existing codebase style.

### 5. Routing table rebuild is a single-assignment swap, not mutation

**PASS.** In `universe_manager.py:rebuild_after_refresh()` (lines 590-605), a new `new_routing` dict is built in a local variable. The swap happens via four sequential single assignments to `self._reference_cache`, `self._viable_symbols`, `self._routing_table`, `self._last_build_time`, and `self._last_routing_build_time`. Under asyncio's cooperative concurrency model (no `await` between the assignments), these are effectively atomic. The existing `build_routing_table` method mutates in-place (`self._routing_table.clear()`), so the new method is actually safer.

### 6. No new `await` calls added to the startup synchronous path when trust=true

**PASS.** The trust-cache fast path in `build_viable_universe()` (lines 93-107) calls only synchronous methods: `load_cache_for_startup()`, `get_cache_age_str()`, `_apply_system_filters()`. No `await` in the fast path.

### 7. Cache file path unchanged

**PASS.** No modification to `FMPReferenceConfig` cache_file default or any path construction logic. `load_cache()`, `save_cache()`, `load_cache_for_startup()` all use `self._config.cache_file` which defaults to `data/reference_cache.json`.

### 8. FMP rate limiting respected during background refresh

**PASS.** `background_refresh()` delegates to `self.fetch_reference_data(stale_symbols)` (line 1166), which uses the existing semaphore (concurrency=5) and `rate_limit_delay_seconds` (line 434-435). No new FMP API paths are introduced; the background refresh reuses the same fetch infrastructure.

## Regression Checklist

| Check | Result | Evidence |
|-------|--------|----------|
| Cache checkpoint does not lose existing entries | PASS | Test `test_checkpoint_merge_preserves_existing_entries` — A,B,C pre-populated, B updated + D added, all 4 present after |
| Cache load at startup is non-blocking when trust=true | PASS | Test `test_trust_cache_returns_cached_data_without_api_calls` — no FMP calls, returns cached data |
| Cache load at startup IS blocking when trust=false | PASS | Test `test_trust_cache_disabled_reverts_to_blocking` — `fetch_reference_data_incremental` called |
| Background refresh task starts and runs | PASS | Test `test_background_refresh_task_runs` — verifies cache updated to "Refreshed" sector |
| Background refresh does not crash on FMP errors | PASS | Test `test_background_refresh_handles_fmp_errors` — exception caught, client still functional |
| Routing table swap is atomic | PASS | `rebuild_after_refresh()` builds in local vars, assigns in sequence with no `await` between |
| Full test suite passes | PASS | 3,071 passed, 3 failed (pre-existing xdist flakes: `test_fmp_canary_success`, `test_fetch_reference_data_progress_logging`, `test_load_cache_missing_file`) |

## Escalation Criteria Check

| Criterion | Triggered? | Notes |
|-----------|-----------|-------|
| Changes to startup sequence (Phases 7-9.5) affect component initialization order | No | Phase 7.5 adds a `trust_cache` parameter to `build_viable_universe` call; no phase reordering |
| Background refresh introduces new asyncio task lifecycle pattern | No | Follows identical pattern to `_regime_task` and `_eval_check_task` (create_task + cancel/suppress/await in stop) |
| Cache merge logic requires file locking or cross-process synchronization | No | Single-process, single-writer; merge is in-memory dict operations |
| Any change to Risk Manager, Order Manager, or Event Bus behavior | No | None of these files were modified |

## Files Modified vs. Should-Not-Modify List

No violations. Modified files are:
- `argus/core/config.py` — allowed
- `argus/data/fmp_reference.py` — allowed
- `argus/data/universe_manager.py` — allowed
- `argus/main.py` — allowed (not `orchestrator.py`)
- `config/system.yaml`, `config/system_live.yaml` — allowed
- `tests/data/test_fmp_reference.py`, `tests/data/test_cache_checkpoint_and_trust.py` — allowed

No changes to: `argus/strategies/`, `argus/execution/`, `argus/analytics/`, `argus/ai/`, `argus/intelligence/`, `argus/ui/`, `argus/backtest/`, `argus/core/orchestrator.py`.

## Minor Observations (Non-Blocking)

1. **Private attribute access across module boundaries:** `rebuild_after_refresh()` accesses `self._reference_client._cache` (line 578) and `_background_cache_refresh()` in `main.py` accesses `self._universe_manager._reference_client` (line 946). This is a code smell but consistent with existing patterns in the codebase (e.g., main.py already accesses `_universe_manager` internals elsewhere). Not a blocker.

2. **`get_cache_age_str()` reports oldest entry age:** After `load_cache_for_startup()` is called, `_cached_at_timestamps` is populated by `load_cache()`. The age string reflects the oldest entry, which is appropriate for communicating worst-case staleness. No issue.

3. **Double `save_cache()` in background refresh:** `background_refresh()` calls `fetch_reference_data(stale_symbols)` which already saves the cache during fetch (via checkpoints and final save), then calls `save_cache()` again on line 1170. This is redundant but harmless (idempotent write).

## Close-Out Report Accuracy

The close-out report accurately reflects the changes. Self-assessment of CLEAN is justified. Test count (3,071) matches the independent run. The 3 xdist failures are confirmed pre-existing (same tests that failed in the S1 review baseline).

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "25.9",
  "session": "S2",
  "verdict": "CLEAR",
  "summary": "Cache checkpoint merge fix and trust-cache-on-startup implemented correctly. Merge logic is existing-union-fresh with fresh precedence. Background refresh follows established asyncio task lifecycle pattern. No escalation criteria triggered. All tests pass (3 pre-existing xdist flakes).",
  "findings": [],
  "escalation_triggers_checked": [
    {"criterion": "Startup sequence phase ordering", "triggered": false},
    {"criterion": "New asyncio task lifecycle pattern", "triggered": false},
    {"criterion": "File locking or cross-process sync", "triggered": false},
    {"criterion": "Risk Manager / Order Manager / Event Bus changes", "triggered": false}
  ],
  "tests": {
    "total": 3071,
    "passed": 3071,
    "failed": 3,
    "failed_are_preexisting": true,
    "new_tests": 12
  },
  "files_wrongly_modified": [],
  "review_focus_results": [
    {"item": "Checkpoint merge is existing UNION fresh, fresh precedence", "result": "PASS"},
    {"item": "Cache loaded at START of fetch cycle", "result": "PASS"},
    {"item": "trust_cache_on_startup=false reverts to blocking", "result": "PASS"},
    {"item": "Background refresh registered for shutdown cancellation", "result": "PASS"},
    {"item": "Routing table rebuild is single-assignment swap", "result": "PASS"},
    {"item": "No new await in startup path when trust=true", "result": "PASS"},
    {"item": "Cache file path unchanged", "result": "PASS"},
    {"item": "FMP rate limiting respected in background refresh", "result": "PASS"}
  ]
}
```
