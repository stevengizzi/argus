---BEGIN-REVIEW---

# Sprint 27.6 Session 3 — Tier 2 Review

**Reviewer:** @reviewer subagent
**Date:** 2026-03-24
**Verdict:** PASS

## Spec Compliance

| Requirement | Status | Notes |
|---|---|---|
| `MarketCorrelationTracker` class with `CorrelationConfig` | PASS | Constructor accepts config + optional cache_path |
| `async compute(fetch_daily_bars_fn, get_top_symbols_fn)` | PASS | Dependency-injected callables, asyncio.gather for concurrency |
| `get_correlation_snapshot() -> dict` | PASS | Returns average_correlation, correlation_regime, symbols_used |
| Correlation regime classification (dispersed/normal/concentrated) | PASS | Threshold logic in `_classify_regime()` matches config semantics |
| File cache at `data/correlation_cache.json` with date key (ET) | PASS | Uses `datetime.now(_ET).strftime("%Y-%m-%d")` |
| Graceful degradation on missing data | PASS | Multiple fallback paths to `_set_neutral()` |
| Single symbol -> neutral defaults | PASS | `len(symbols) < 2` guard at line 90 |
| All identical returns -> correlation 1.0 | PASS | Tested and verified |
| Insufficient history -> exclude symbol | PASS | `len(df) < lookback` check at line 108 |
| No existing files modified | PASS | `git diff --name-only` empty |
| 10+ tests | PASS | 15 tests |

All spec requirements are met. The `cache_path` constructor parameter addition (not in spec) is a reasonable judgment call for test isolation.

## Code Quality

The implementation is clean and well-structured:

- Clear separation between public API (`compute`, `get_correlation_snapshot`) and internal helpers
- Proper type aliases for injected callables (`FetchDailyBarsFn`, `GetTopSymbolsFn`)
- Defensive coding throughout: NaN filtering on correlation values, OSError handling on cache I/O, insufficient-data guards
- NumPy upper-triangle extraction (`np.triu` with `k=1`) is the standard approach for pairwise correlation averaging
- The `lookback + 5` buffer for fetching extra days is a sensible defensive measure for gap handling
- Logging at appropriate levels (info for cache hits/computation results, warning for degradation, debug for symbol exclusion)

Minor observations (non-blocking):
- The `_fetch_bars_factory` helper in the test file (lines 40-48) is defined as an async function that returns a callable, but it is never actually used in any test. Each test defines its own inline `fetch` coroutine instead. This is dead code in the test file — harmless but slightly untidy.

## Test Coverage

15 tests organized into 4 clear classes:

- **TestConstruction (2):** Config wiring and default cache path
- **TestComputeKnownData (4):** Known correlation values for all 3 regime classifications plus normal
- **TestEdgeCases (4):** Single symbol, identical returns, insufficient history, all-None fetches
- **TestFileCache (3):** Write+read schema, same-day cache hit (no recompute), stale date recompute
- **TestSnapshot (2):** Before-compute neutral defaults, after-compute reflects actual values

Coverage is thorough for a standalone module. All spec-required test scenarios are present. The cache-hit test correctly verifies via a `fetch_called` flag that no data fetching occurs.

One gap worth noting: there is no test for a malformed cache file (e.g., invalid JSON or missing keys). The `_read_cache` method handles this gracefully (returns None on `JSONDecodeError` or missing "date" key), but a test would confirm the behavior. This is not a blocking concern — the code handles it defensively.

## Session-Specific Review Focus

### 1. Dependency injection pattern (no direct FMP/UM imports)

PASS. Grep for `fmp`, `universe_manager`, `UniverseManager`, `FmpReference` in `market_correlation.py` returns zero matches. The only import from argus is `CorrelationConfig` from `argus.core.config`. Data access is fully injected via callables.

### 2. Cache invalidation is date-keyed (ET, not UTC)

PASS. Line 77: `datetime.now(_ET).strftime("%Y-%m-%d")` where `_ET = ZoneInfo("America/New_York")`. This correctly uses Eastern Time for the cache key, which aligns with pre-market computation timing and the project's DEC-061 convention.

### 3. Graceful degradation (never raises on missing data)

PASS. Multiple degradation paths:
- `len(symbols) < 2` -> neutral (line 90)
- `df is None or len(df) < lookback` -> symbol excluded (line 108)
- `len(returns_map) < 2` after filtering -> neutral (line 122)
- `len(valid_values) == 0` after NaN filter -> neutral (line 140)
- Cache read errors -> returns None, triggers recompute (line 206)
- Cache write errors -> logged as warning, does not raise (line 230)

No code path raises an exception to the caller.

### 4. No naming collision with existing `core/correlation.py`

PASS. The existing `argus/core/correlation.py` is a "Strategy correlation tracking for the Orchestrator" module that "tracks daily P&L across strategies." The new `argus/core/market_correlation.py` computes market-wide pairwise price correlation across symbols. Different module names, different class names, different purposes. No collision.

## Regression Check

- `git diff --name-only`: empty (no existing files modified)
- Baseline tests (`test_regime.py` + `test_breadth.py`): 87 passed in 0.34s
- Session tests (`test_market_correlation.py`): 15 passed in 0.39s
- No do-not-modify files touched
- No circular import risk (only imports `CorrelationConfig` from `argus.core.config`)

## Issues Found

None.

## Recommendations

1. Consider adding a test for malformed cache file handling (invalid JSON, missing keys) in a future session. The code handles it correctly but lacks explicit test coverage for that path.
2. Remove the unused `_fetch_bars_factory` helper from the test file (dead code).

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "27.6",
  "session": "S3",
  "reviewer": "@reviewer subagent",
  "date": "2026-03-24",
  "verdict": "CLEAR",
  "summary": "MarketCorrelationTracker implementation meets all spec requirements. Clean dependency injection, ET-keyed cache, comprehensive graceful degradation, no naming collision. 15/15 tests pass. No existing files modified. No issues found.",
  "findings": [
    {
      "severity": "info",
      "category": "test-coverage",
      "description": "No test for malformed cache file (invalid JSON / missing keys). Code handles it correctly but path is untested.",
      "file": "tests/core/test_market_correlation.py"
    },
    {
      "severity": "info",
      "category": "dead-code",
      "description": "Unused _fetch_bars_factory helper function in test file (lines 40-48). Never called by any test.",
      "file": "tests/core/test_market_correlation.py"
    }
  ],
  "escalation_triggers_checked": {
    "regime_vector_breaks_mor_serialization": false,
    "breadth_latency_increase": false,
    "config_gate_bypass": false,
    "v2_different_market_regime_from_v1": false,
    "pre_market_startup_exceeds_60s": false,
    "circular_imports": false,
    "event_bus_subscriber_ordering": false
  },
  "tests_ran": true,
  "tests_passed": true,
  "test_count": 15,
  "baseline_tests_passed": true,
  "baseline_test_count": 87,
  "do_not_modify_files_checked": true,
  "do_not_modify_violations": []
}
```
