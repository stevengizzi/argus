# Dev Log: evaluation.db VACUUM (DEF-157)

**Date:** 2026-04-20
**Type:** Impromptu (B) — DB maintenance fix
**DEF:** DEF-157 RESOLVED

## Problem

`data/evaluation.db` grew to 3.7 GB despite DEC-345's 7-day retention policy.
Root cause (identified in morning session): SQLite never reclaims freed pages
without an explicit VACUUM. The retention DELETE was running correctly but the
file never shrank.

## Solution

Three additions to `EvaluationEventStore` in `argus/strategies/telemetry_store.py`:

1. **VACUUM after retention** — `cleanup_old_events()` now calls `_vacuum()`
   after deleting rows (gated by `VACUUM_AFTER_CLEANUP` class attribute, default True).

2. **Startup reclaim** — `initialize()` checks freelist ratio and file size.
   If the file exceeds 500 MB AND freelist >50%, triggers VACUUM before normal
   operations begin. This handles the one-time reclaim case (like the 3.7 GB
   bloat from before this fix existed).

3. **Observability** — Logs DB size and freelist % at INFO on startup. Logs
   WARNING if DB exceeds 2 GB after maintenance (signals potential write volume
   issue).

## Technical Detail: aiosqlite VACUUM workaround

aiosqlite cannot execute VACUUM directly:
- `await conn.execute("VACUUM")` raises "cannot VACUUM - SQL statements in progress"
- Even if it could, the aiosqlite WAL lock prevents file truncation by other connections

Solution: close the aiosqlite connection, VACUUM via synchronous `sqlite3.connect(isolation_level=None)`
in `asyncio.to_thread()`, then reopen and reconfigure (WAL mode + row_factory).

## Validation

Manual VACUUM on production DB: 3.7 GB → 209 MB (94.5% reduction), freelist 0%.

## Tests

+5 pytest in `tests/strategies/test_telemetry_store_vacuum.py`:
- Retention + VACUUM shrinks DB
- Retention without VACUUM preserves file size
- Startup reclaim triggers on bloated DB
- Startup reclaim skipped on healthy DB
- Startup reclaim skipped when size below threshold
