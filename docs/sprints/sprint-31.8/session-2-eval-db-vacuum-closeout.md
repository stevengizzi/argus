---BEGIN-CLOSE-OUT---

**Session:** Impromptu 2026-04-20 (B) — evaluation.db VACUUM (DEF-157)
**Date:** 2026-04-20
**Self-Assessment:** CLEAN

### Change Manifest
| File | Change Type | Rationale |
|------|-------------|-----------|
| argus/strategies/telemetry_store.py | modified | VACUUM after retention DELETE + startup reclaim + observability |
| tests/strategies/test_telemetry_store_vacuum.py | added | 5 regression tests for VACUUM behavior |
| CLAUDE.md | modified | DEF-157 marked RESOLVED |
| docs/sprint-history.md | modified | AT entry + statistics update |
| dev-logs/2026-04-20_eval-db-vacuum.md | added | Dev log |
| docs/sprints/sprint-31.8/session-2-eval-db-vacuum-closeout.md | added | This file |

### Judgment Calls
- **Close-reopen pattern for VACUUM**: aiosqlite cannot execute VACUUM ("SQL statements in progress") and holds WAL locks preventing file truncation by external connections. Solution: close the aiosqlite connection, VACUUM via a synchronous `sqlite3.connect(isolation_level=None)` in `asyncio.to_thread()`, then reopen and re-configure (WAL, row_factory). This is a one-time expensive operation (seconds) that only runs after retention DELETE finds rows to delete.
- **Class-level constants instead of config YAML**: Used class attributes (`VACUUM_AFTER_CLEANUP`, `STARTUP_RECLAIM_FREELIST_RATIO`, etc.) rather than adding a new Pydantic config model and YAML section. The prompt said "guarded/skippable via config if a future operator wants to disable it" — class attributes are overridable at instantiation time and avoid config proliferation for a maintenance feature.
- **5 tests instead of 2 minimum**: Added tests for both positive (VACUUM shrinks, startup reclaim triggers) and negative (no VACUUM preserves size, startup skipped on healthy DB, startup skipped when below size threshold) paths for thorough coverage.

### Scope Verification
| Spec Requirement | Status | Implementation |
|-----------------|--------|----------------|
| VACUUM after retention DELETE | DONE | telemetry_store.py:279-294 — cleanup_old_events calls _vacuum() when deleted>0 and VACUUM_AFTER_CLEANUP |
| One-time startup reclaim path | DONE | telemetry_store.py:114-132 — initialize() checks size+freelist ratio, triggers _vacuum() if bloated |
| Observability logging | DONE | telemetry_store.py:103-142 — size/freelist at INFO on init, WARNING for bloat + post-VACUUM stats |
| 2+ new tests | DONE | test_telemetry_store_vacuum.py — 5 tests (2 retention, 3 startup) |
| Manual VACUUM validation | DONE | sqlite3 VACUUM on data/evaluation.db: 3.7 GB → 209 MB, freelist 0% |
| DEF-157 RESOLVED in CLAUDE.md | DONE | Strikethrough + RESOLVED annotation |
| Sprint-history entry AT | DONE | docs/sprint-history.md |

### Regression Checks
| Check | Result | Notes |
|-------|--------|-------|
| Retention still deletes correct rows | PASS | Existing cleanup test (test_telemetry_store.py) passes |
| VACUUM doesn't break concurrent reads | PASS | Connection reopened after VACUUM; execute_query() works post-VACUUM |
| Startup time not bloated on normal boot | PASS | test_startup_reclaim_skipped_on_healthy_db + _skipped_when_size_below_threshold |
| No regression to StrategyEvaluationBuffer | PASS | Ring buffer code untouched; tests pass |
| No regression to record_evaluation() | PASS | write_event signature unchanged; existing tests pass |
| No strategy files modified | PASS | Only telemetry_store.py in argus/strategies/ touched |
| No Sprint 31.75 files modified | PASS | experiments/, historical_query_service.py, etc. untouched |
| No morning session files modified | PASS | server.py, main.py, start_live.sh, health.py untouched |

### Test Results
- **Before:** 4,905 pytest + 846 Vitest = 5,751 total
- **After:** 4,910 pytest + 846 Vitest = 5,756 total
- **New:** 5 tests
- **All passing:** Yes
- **Command:** `python -m pytest --ignore=tests/test_main.py -n auto -q`

### Unfinished Work
None.

### Notes for Reviewer
- The `_vacuum()` method closes and reopens the aiosqlite connection. This is safe because VACUUM only runs (a) after retention DELETE in `cleanup_old_events()` and (b) during `initialize()` startup reclaim. Both are non-concurrent paths — retention runs once at boot, initialize runs once at startup.
- The 36K events/min write volume concern was NOT investigated per prompt constraints. Observability (SIZE_WARNING_THRESHOLD_MB=2000) will surface this if the DB grows again despite VACUUM.
- Manual validation confirmed: 3.7 GB → 209 MB (94.5% reduction), freelist 0%.

### Context State
GREEN — single-pass implementation, well within context limits.

---END-CLOSE-OUT---

```json:structured-closeout
{
  "schema_version": "1.0",
  "sprint": "Impromptu 2026-04-20 (B)",
  "session": "S1",
  "verdict": "COMPLETE",
  "tests": {
    "before": 5751,
    "after": 5756,
    "new": 5,
    "all_pass": true,
    "pytest_count": 4910,
    "vitest_count": 846
  },
  "files_created": [
    "tests/strategies/test_telemetry_store_vacuum.py",
    "dev-logs/2026-04-20_eval-db-vacuum.md",
    "docs/sprints/sprint-31.8/session-2-eval-db-vacuum-closeout.md"
  ],
  "files_modified": [
    "argus/strategies/telemetry_store.py",
    "CLAUDE.md",
    "docs/sprint-history.md"
  ],
  "files_should_not_have_modified": [],
  "scope_additions": [],
  "scope_gaps": [],
  "prior_session_bugs": [],
  "deferred_observations": [
    "36K events/min write volume (from morning investigation) not addressed — observability via SIZE_WARNING_THRESHOLD_MB=2000 will surface if DB grows despite VACUUM"
  ],
  "doc_impacts": [],
  "dec_entries_needed": [],
  "warnings": [],
  "implementation_notes": "aiosqlite cannot execute VACUUM due to internal cursor state ('SQL statements in progress') and holds WAL locks preventing file truncation. Solution: close aiosqlite connection, run VACUUM via synchronous sqlite3 with isolation_level=None in asyncio.to_thread(), then reopen. This close-reopen pattern is safe because VACUUM only runs during maintenance windows (retention cleanup or startup reclaim)."
}
```
