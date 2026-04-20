---BEGIN-REVIEW---

# Tier 2 Review: Impromptu 2026-04-20 — Lifespan Hang + API Health Observability

**Reviewer:** Tier 2 Automated Review
**Date:** 2026-04-20
**Diff Range:** d3afff5..HEAD
**Test Result:** 4,905 pytest passed (176.53s), 0 failures

---

## 1. Root Cause Alignment (Focus Item 1)

The py-spy dump (`logs/argus_hang_2026-04-20.txt`) shows:
- MainThread idle in `select` (asyncio event loop waiting)
- AnyIO worker threads idle (waiting for work)
- `asyncio_0` thread blocked in `block_for_close` (Databento — normal behavior)

The dev log explains the root cause was NOT visible in the py-spy dump directly:
the `HistoricalQueryService.__init__()` was executing in the lifespan handler's
context (same asyncio event loop), blocking the lifespan from yielding. By the
time py-spy was invoked, the HQS init may have completed (session was 26 min old),
leaving only the waiting main loop visible.

The fix (backgrounding HQS init via `asyncio.create_task(asyncio.to_thread(...))`)
correctly addresses this: the blocking file-system glob is moved off the event loop
entirely, and the lifespan handler can yield immediately.

**Verdict:** Root cause is correctly identified and in the lifespan handler. Fix is
appropriate and minimal.

## 2. Network-Dependent Calls in Lifespan (Focus Item 2)

The lifespan handler (`server.py` create_app lifespan) initializes:
- AI client (local config only, no network call)
- Intelligence pipeline (startup factory — may call network for catalysts)
- VIXDataService (yfinance download)
- Learning Loop (local SQLite)
- ExperimentStore (local SQLite)
- HistoricalQueryService (filesystem + DuckDB — NOW BACKGROUNDED)

The VIXDataService and intelligence pipeline initialization within the lifespan
path were not addressed by this session. However, these are initialized in
`main.py`'s startup sequence (Phase 9+), not in the API lifespan handler. The
API lifespan only initializes VIX if running in standalone mode (without main.py).

Reviewed the lifespan code: all remaining init calls are either local SQLite ops
or config-gated services that were already background-safe. The HQS was the only
blocking filesystem operation in the lifespan.

**Verdict:** The specific hang is resolved. No other blocking network calls exist
in the lifespan critical path.

## 3. Health Signal Gating (Focus Item 3)

Code path:
1. `main.py:1288` — `run_server()` returns an asyncio Task
2. `main.py:1296` — `_wait_for_port()` polls TCP connect to `127.0.0.1:port`
3. Only on successful TCP connect does `update_component("api_server", HEALTHY)` fire
4. If port never binds within 60s, marks DEGRADED instead

TCP accept on the port means uvicorn has completed its bind (lifespan yielded,
socket listening). The `api_server -> healthy` signal cannot fire while the port
is unbound.

**Verdict:** Correct. Health signal is properly gated on actual port availability.

## 4. start_live.sh Non-Zero Exit (Focus Item 4)

The script:
1. Launches ARGUS, captures PID
2. Probes `curl -sf http://127.0.0.1:$API_PORT/api/v1/market/status` (15 retries x 1s)
3. On probe timeout: logs error, kills process, removes PID file, `exit 1`
4. Also checks if process died mid-probe: logs error, `exit 1`

The script exits non-zero both when the API fails to bind AND when the Python
process crashes. This is correct and well-tested (test_start_live_probe.py).

**Verdict:** Correct.

## 5. evaluation.db Investigation (Focus Item 5)

DEF-157 logged in CLAUDE.md with full root cause analysis (missing VACUUM after
DELETE, 94.3% freelist). No code fix was applied. The investigation is purely
observational and documented.

**Verdict:** Correctly handled as investigation-only with DEF logged.

## 6. Protected Files (Focus Items 6, 9)

Verified via `git diff` that ZERO changes exist in:
- `argus/strategies/`, `argus/strategies/patterns/`
- `config/system_live.yaml`, `config/system.yaml`, `config/experiments.yaml`
- `config/universe_filters/`
- `argus/intelligence/experiments/`
- `argus/data/historical_query_service.py`
- `scripts/run_experiment.py`, `scripts/resolve_sweep_symbols.py`, `scripts/run_sweep_batch.sh`
- `argus/backtest/engine.py`

No broker, order manager, risk manager, or universe manager files were touched.

**Verdict:** All file boundaries respected.

## 7. block_for_close Imports (Focus Item 7)

`grep` shows only 2 existing uses of `block_for_close`:
- `argus/data/databento_data_service.py`
- `tests/mocks/mock_databento.py`

No new imports added by this session.

**Verdict:** Clean.

## 8. Timeout Audit (Focus Item 8)

This session's scope was the lifespan hang fix. Checking whether the session added
timeouts to the services listed:

- **yfinance (VIXDataService):** Not in lifespan path; initialized in main.py.
  Existing code uses yfinance defaults (no explicit timeout). NOT ADDRESSED by
  this session — but was not in scope.
- **FMP calls:** Scanner/reference/news all go through `FMPReferenceClient` with
  `aiohttp` session timeout. Pre-existing.
- **SEC EDGAR:** Has explicit `timeout` on ClientSession (added Sprint 23.9).
- **Finnhub:** Uses `aiohttp` session with timeout config.
- **Databento:** Has its own connection management with reconnection loop.

The yfinance library does not expose a clean timeout parameter (it uses
`requests.get()` internally). This is a pre-existing gap (DEF-103 already tracks
yfinance reliability concerns). Since this session's scope was specifically the
lifespan hang, and yfinance is not called in the lifespan path, this is not a
regression introduced by this session.

**Verdict:** No new timeout gaps introduced. Pre-existing yfinance timeout gap
exists but is out of scope and already tracked.

## 9. Existing Tests

No existing tests were modified or deleted. 6 new tests added; full suite passes
(4,905 tests, same count as close-out report claims).

**Verdict:** No escalation criteria triggered.

---

## Findings Summary

| # | Severity | Finding |
|---|----------|---------|
| F1 | INFO | `_wait_for_port()` uses blocking `socket.connect()` inside an async method. It does `await asyncio.sleep(0.5)` between attempts but each connect attempt itself is synchronous with a 1s socket timeout. This is acceptable for a startup probe (not a hot path) but technically blocks the event loop for up to 1s per attempt. |
| F2 | INFO | The `hqs_init_task` is a fire-and-forget background task. If it raises an unhandled exception after the lifespan yields, it would be silently swallowed by asyncio's default exception handler (logged as "Task exception was never retrieved"). The current code handles exceptions inside the task, so this is fine. |

No medium or high severity findings.

---

## Escalation Criteria Check

| Criterion | Triggered | Evidence |
|-----------|-----------|----------|
| Root cause NOT in lifespan handler | NO | Root cause confirmed: HQS `__init__()` called synchronously in lifespan handler blocked for 12 min |
| Fix requires async architecture change | NO | Fix is a targeted `create_task(to_thread(...))` wrapper; no architectural change |
| evaluation.db bloat from live-trading bug | NO | Caused by missing VACUUM after retention DELETE; write volume is high but expected |
| Existing test modified/deleted | NO | Zero existing test changes |
| Health check weakened | NO | Health check is strengthened (gated on actual port bind, not just task creation) |

---

## Verdict

**CLEAR**

The implementation correctly identifies and fixes the lifespan hang root cause,
properly gates the health signal on actual port availability, adds a shell-level
health probe with non-zero exit on failure, and logs the evaluation.db investigation
as a DEF without applying a fix. All protected files are untouched, no existing
tests were modified, and the full test suite passes. The changes are minimal,
well-scoped, and well-tested.

---END-REVIEW---

```json:structured-verdict
{
  "schema_version": "1.0",
  "sprint": "Impromptu 2026-04-20",
  "session": "S1",
  "reviewer": "tier-2-automated",
  "verdict": "CLEAR",
  "confidence": 0.95,
  "findings": [
    {
      "id": "F1",
      "severity": "info",
      "category": "implementation-detail",
      "description": "_wait_for_port() uses blocking socket.connect() with 1s timeout inside async method. Acceptable for startup probe but blocks event loop briefly per attempt.",
      "file": "argus/main.py",
      "line": 1420,
      "escalation_trigger": false
    },
    {
      "id": "F2",
      "severity": "info",
      "category": "error-handling",
      "description": "hqs_init_task handles exceptions internally; no risk of silent task exception. Correctly implemented.",
      "file": "argus/api/server.py",
      "line": 501,
      "escalation_trigger": false
    }
  ],
  "escalation_triggers_checked": [
    {"criterion": "Root cause NOT in lifespan handler", "triggered": false},
    {"criterion": "Fix requires async architecture change", "triggered": false},
    {"criterion": "evaluation.db bloat from live-trading bug", "triggered": false},
    {"criterion": "Existing test modified/deleted", "triggered": false},
    {"criterion": "Health check weakened", "triggered": false}
  ],
  "tests": {
    "suite_passed": true,
    "total": 4905,
    "new": 6,
    "modified": 0,
    "deleted": 0
  },
  "protected_files_violated": [],
  "scope_adherence": "full"
}
```
