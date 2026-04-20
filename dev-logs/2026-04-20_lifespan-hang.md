# Dev Log — Lifespan Hang + API Health Observability

**Date:** 2026-04-20
**Session:** Impromptu Triage — startup reliability
**Status:** COMPLETE

## Problem

April 20 cold-start (first boot after 17 days): ARGUS appeared to start but
the UI could not connect — every `/api/v1/*` request returned `ECONNREFUSED`.
`lsof -p 64127 -iTCP -sTCP:LISTEN` confirmed zero TCP listeners despite the
log line `API server started on 0.0.0.0:8000` at 09:26:34 ET.

The log showed `Waiting for application startup.` (09:26:35) with
`Application startup complete.` not appearing until 09:38:34 — a **12-minute
gap** during which the lifespan handler was blocked.

## Root Cause Confirmed

**Primary**: `HistoricalQueryService.__init__()` (called synchronously in the
lifespan handler at `server.py:476`) performs:
1. `list(cache_path.glob("**/*.parquet"))` — enumerating 983,894 files
2. `SELECT * FROM historical LIMIT 1` — forcing DuckDB to scan the glob

This took 12 minutes on cold filesystem cache, blocking the lifespan from
`yield`ing and preventing uvicorn from completing startup.

**Secondary**: The `api_server → healthy` health signal in `main.py:1296` fired
immediately after `run_server()` created the asyncio.Task — before uvicorn's
lifespan even began executing. This is because `run_server()` just does
`asyncio.create_task(server.serve())` and returns the task reference; it
doesn't wait for the port to bind.

**Red herring**: The `block_for_close` thread in py-spy is the normal Databento
live client `_run_with_reconnection()` loop — unrelated to the hang.

## Changes

### `argus/api/server.py` — Background HQS initialization

The `HistoricalQueryService` constructor is now run inside an
`asyncio.create_task(asyncio.to_thread(...))` wrapper. The lifespan handler
proceeds immediately; the service becomes available asynchronously. Cleanup
on shutdown cancels the task if still running.

### `argus/main.py` — Port-probed health signal

Added `ArgusSystem._wait_for_port()` static method (TCP connect probe,
0.5s interval, configurable timeout). After `run_server()`, the startup
sequence now awaits a successful connection to the API port (60s timeout)
before marking `api_server → healthy` or printing the "RUNNING" banner.

### `scripts/start_live.sh` — Post-startup API probe

After process launch:
- Probes `http://127.0.0.1:8000/api/v1/market/status` (15 retries × 1s)
- On timeout: logs error, kills the backend process, exits non-zero
- Also detects and kills orphaned Vite processes on ports 5173–5175

## Investigation: `data/evaluation.db` (4 GB)

- 937,245 rows, all from 2026-04-20 (today's 26-minute session)
- `freelist_count = 923,947` / `page_count = 979,337` — **94.3% free pages**
- Retention DELETE ran correctly on boot (cleared 17 days of stale data)
- Root cause: no `VACUUM` follows the DELETE — SQLite never reclaims pages
- Logged as DEF-157 (fix: add VACUUM or enable auto_vacuum)

## Tests

- 6 new tests: 4 in `tests/api/test_lifespan_startup.py`, 2 in
  `tests/scripts/test_start_live_probe.py`
- Full suite: 4,905 pytest + 846 Vitest, all passing
