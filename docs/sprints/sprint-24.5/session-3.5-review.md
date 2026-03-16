---BEGIN-REVIEW---

# Sprint 24.5, Session 3.5 — Tier 2 Review Report

**Reviewer:** Automated Tier 2 (@reviewer subagent)
**Date:** 2026-03-16
**Commit range:** Uncommitted working tree changes on branch `sprint-24.5`
**Close-out self-assessment:** CLEAN

---

## 1. Spec Compliance

| Spec Requirement | Status | Notes |
|-----------------|--------|-------|
| Create telemetry_store.py with EvaluationEventStore | DONE | Correct location, all methods present |
| __init__ with db_path and RETENTION_DAYS=7 | DONE | Class constant, value 7 |
| initialize() creates table + indexes (IF NOT EXISTS) | DONE | All three DDL use IF NOT EXISTS |
| write_event() with try/except, never raises | DONE | Full body wrapped, logs warning on failure |
| query_events() with filters, default today ET | DONE | Uses _ET ZoneInfo for default date |
| cleanup_old_events() with ET dates | DONE | datetime.now(_ET) for cutoff |
| Buffer set_store() and record() forwarding | DONE | Fire-and-forget via loop.create_task |
| REST ?date= parameter routes to store | DONE | Non-today dates route to store |
| AppState.telemetry_store field | DONE | Optional field with None default |
| Server lifespan wiring + cleanup | DONE | Init, cleanup, strategy wiring, close() |
| >=10 new tests | DONE | 17 new tests |
| close() method (scope addition) | DONE | Justified resource cleanup |

All spec requirements are met. One scope addition (close() method) is justified.

---

## 2. Review Focus Items

### F1: Table creation idempotent (IF NOT EXISTS)
**PASS.** `_CREATE_TABLE`, `_CREATE_IDX_DATE_STRATEGY`, and `_CREATE_IDX_DATE_SYMBOL` all use `IF NOT EXISTS`. Safe to call `initialize()` multiple times.

### F2: write_event() has try/except -- never raises
**PASS.** Lines 95-115 of telemetry_store.py: entire method body is in try/except. The except clause logs `warning` with `exc_info=True` and returns silently. Additionally, uninitialised connection is handled with early return (line 96-98).

### F3: buffer.record() still works when store is None (graceful degradation)
**PASS.** The `if self._store is not None` guard at line 102 of telemetry.py ensures the store path is only entered when a store is attached. The `_store` is initialized to `None` in `__init__`. Test `test_buffer_record_works_without_store` verifies this.

### F4: loop.create_task usage is correct for fire-and-forget async
**PASS.** `asyncio.get_running_loop()` is called to get the current loop, then `loop.create_task()` schedules the coroutine. The broad `except Exception: pass` catches `RuntimeError` (no running loop) and any other unexpected errors. This matches the spec's fire-and-forget pattern. The test `test_buffer_record_forwards_to_store` verifies the task completes with a small `asyncio.sleep(0.05)`.

### F5: Cleanup uses ET dates (not UTC) for retention boundary
**PASS.** Line 180: `datetime.now(_ET)` where `_ET = ZoneInfo("America/New_York")`. The cutoff is computed in ET and formatted as YYYY-MM-DD for string comparison against `trading_date`.

### F6: AppState.telemetry_store field added correctly
**PASS.** Added as `telemetry_store: EvaluationEventStore | None = None` at the end of the optional fields. TYPE_CHECKING import added for the type annotation. Follows existing pattern for optional components.

### F7: Server lifespan wires store into all strategy buffers
**PASS.** Lines 271-272 of server.py iterate `app_state.strategies.values()` and call `strategy.eval_buffer.set_store(telemetry_store)` on each. Cleanup section closes the store and sets `app_state.telemetry_store = None`.

---

## 3. Regression Checklist

| Check | Result |
|-------|--------|
| Ring buffer still works without store | PASS -- 17 tests in test_telemetry.py pass |
| Existing DB tables unaffected | PASS -- new table only, IF NOT EXISTS |
| REST endpoint without date param unchanged | PASS -- 4 tests in test_strategy_decisions.py pass |
| Strategy construction unaffected | PASS -- 303 strategy tests pass |
| Forbidden files unmodified | PASS -- git diff shows no changes to events.py, main.py, or strategy files |

---

## 4. Test Analysis

- **New tests:** 17 in `tests/test_telemetry_store.py`
- **Test coverage:** Store CRUD (6 tests), cleanup retention (2 tests), failure handling (1 test), default date (1 test), buffer-store forwarding (2 tests), REST date routing (2 tests), plus 3 additional filter/combined tests
- **All scoped tests pass:** 31/31 (telemetry_store + telemetry + strategy_decisions)
- **Existing strategy tests pass:** 316/316
- **Test quality:** Tests are well-structured with a helper factory, async fixtures with proper cleanup, and self-contained REST fixtures

---

## 5. Code Quality

### Positive
- Clean separation: store is its own module, buffer knows store only via optional reference
- WAL mode enabled for concurrent write safety (important since main DB may also be in use)
- Parameterized SQL throughout (no string interpolation)
- `json.dumps(event.metadata, default=str)` handles non-serializable metadata gracefully
- Shutdown cleanup closes the connection properly

### Minor Observations (non-blocking)
- `app_state.trade_logger._db._db_path` in server.py accesses two private attributes. This is a pre-existing pattern in the codebase (other server.py code also accesses `_db`), so it is consistent but worth noting.
- `getattr(state, "telemetry_store", None)` in strategies.py (line 418) is overly defensive since `telemetry_store` is a proper dataclass field. `state.telemetry_store is not None` would be equivalent and clearer. Not a bug.
- The store opens its own `aiosqlite` connection to the same DB file rather than reusing `DatabaseManager`. WAL mode makes this safe, and it keeps the store self-contained. Acceptable design choice.

---

## 6. Escalation Criteria Check

| Criterion | Triggered? | Evidence |
|-----------|-----------|----------|
| Strategy on_candle() behavior change | NO | No strategy files modified |
| Ring buffer blocks candle processing | NO | Fire-and-forget pattern, try/except/pass |
| BaseStrategy construction breaks | NO | 303 strategy tests pass |
| Existing REST endpoints break | NO | 4 existing API tests pass, only additive changes |
| SQLite write throughput insufficient | NO | Inline async writes, no throughput issue observed |
| Frontend 3-column layout disruption | N/A | No frontend changes in this session |
| Test count deviation >50% | NO | 17 new tests (spec said >=10) |

No escalation criteria triggered.

---

## 7. Verdict

**CLEAR**

The implementation precisely matches the spec. All 12 requirements are met, including the justified close() scope addition. The 7 review focus items all pass. No forbidden files were modified. 17 new tests cover store CRUD, retention cleanup, failure handling, buffer forwarding, and REST routing. All existing tests pass. Code quality is good with proper error handling, parameterized SQL, and clean shutdown.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "24.5",
  "session": "S3.5",
  "reviewer": "tier2-automated",
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "severity": "info",
      "category": "code-style",
      "description": "Private attribute chain access (trade_logger._db._db_path) in server.py for DB path resolution",
      "file": "argus/api/server.py",
      "line": 264,
      "recommendation": "Pre-existing pattern in codebase. No action needed now, but a public accessor on TradeLogger for db_path would be cleaner."
    },
    {
      "severity": "info",
      "category": "code-style",
      "description": "getattr(state, 'telemetry_store', None) is overly defensive for a dataclass field with a default",
      "file": "argus/api/routes/strategies.py",
      "line": 418,
      "recommendation": "Could simplify to state.telemetry_store is not None. Not a bug."
    }
  ],
  "tests_pass": true,
  "tests_total": 31,
  "tests_new": 17,
  "forbidden_files_clean": true,
  "escalation_triggers": [],
  "regression_checklist_pass": true
}
```
