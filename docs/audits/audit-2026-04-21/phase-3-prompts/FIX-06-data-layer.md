# Fix Session FIX-06-data-layer: argus/data — Databento, Universe Manager, HistoricalQueryService

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 26
**Files touched:** `../../scripts/test_databento_scanner.py`, `argus/core/config.py`, `argus/data/alpaca_data_service.py`, `argus/data/databento_data_service.py`, `argus/data/databento_utils.py`, `argus/data/fmp_reference.py`, `argus/data/fmp_scanner.py`, `argus/data/historical_query_config.py`, `argus/data/historical_query_service.py`, `argus/data/intraday_candle_store.py`, `argus/data/replay_data_service.py`, `argus/data/scanner.py`, `argus/data/universe_manager.py`, `argus/intelligence/sources/fmp_news.py`, `config/system_live.yaml`, `vix_data_service.py`
**Safety tag:** `weekend-only`
**Theme:** Data-layer findings: Databento type imports, UniverseManager validation, HistoricalQueryService edge cases, IntradayCandleStore.

## Pre-Session Verification (REQUIRED — do not skip)

### 1. Environment check

```bash
# Paper trading MUST be paused. No open positions. No active alerts.
./scripts/launch_monitor.sh status 2>/dev/null || echo "monitor offline (expected for weekend-only)"

# If paper trading is running, STOP before proceeding:
#   ./scripts/stop_live.sh
# Confirm zero open positions at IBKR paper account U24619949 via Command Center.
# This session MAY touch production paths. Do NOT run during market hours.
```

### 2. Baseline test run

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record PASS count here: __________ (baseline)
```

**Expected baseline as of the audit commit:** 4,934 pytest + 846 Vitest
(3 pre-existing failures: 2 date-decay DEF-163 + 1 flaky DEF-150).
If your baseline diverges, pause and investigate before proceeding.

### 3. Branch & workspace

Work directly on `main`. No audit branch. Commit at session end with the
exact message format in the "Commit" section below. If you are midway
through the session and need to stop, commit partial progress with a WIP
marker (`audit(FIX-06): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/data/databento_data_service.py`: 5 findings
- `argus/data/historical_query_service.py`: 4 findings
- `argus/data/intraday_candle_store.py`: 3 findings
- `argus/intelligence/sources/fmp_news.py`: 2 findings
- `../../scripts/test_databento_scanner.py`: 1 finding
- `argus/core/config.py`: 1 finding
- `argus/data/alpaca_data_service.py`: 1 finding
- `argus/data/databento_utils.py`: 1 finding
- `argus/data/fmp_reference.py`: 1 finding
- `argus/data/fmp_scanner.py`: 1 finding
- `argus/data/historical_query_config.py`: 1 finding
- `argus/data/replay_data_service.py`: 1 finding
- `argus/data/scanner.py`: 1 finding
- `argus/data/universe_manager.py`: 1 finding
- `config/system_live.yaml`: 1 finding
- `vix_data_service.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-C2-11` [LOW]

**File/line:** [argus/data/databento_data_service.py:1200-1214](argus/data/databento_data_service.py#L1200-L1214)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`fetch_daily_bars()` passes `apikey` in URL params dict.** Error handlers at lines 1251-1256 do not log the URL/params — currently safe (DEF-037 prevention). Latent risk: if an error branch ever logs `response.url` or exception context, FMP API key leaks.

**Impact:**

> Regression risk.

**Suggested fix:**

> Move key to a header (`Authorization`) if FMP permits; otherwise keep, and add a code comment warning future editors not to log response context.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 2: `P1-C2-12` [LOW]

**File/line:** [argus/data/databento_data_service.py:1105-1141](argus/data/databento_data_service.py#L1105-L1141)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_check_parquet_cache()` only checks the month of `start` — multi-month queries silently return partial data.** Comment at [line 1122-1123](argus/data/databento_data_service.py#L1122-L1123) acknowledges this: "Full implementation would merge multiple monthly files."

**Impact:**

> For live ops this is typically single-month queries — fine. For tooling or ad-hoc lookups that span months, cache returns a subset and the caller doesn't know.

**Suggested fix:**

> Either reject multi-month requests (fail-closed) or concat monthly files when start.month != end.month.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 3: `P1-C2-13` [LOW]

**File/line:** [argus/data/databento_data_service.py:113-117](argus/data/databento_data_service.py#L113-L117)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Record-class references typed `type \

**Impact:**

> None = None`** at init and populated later in `_connect_live_session()`. Used in `_dispatch_record()` via `isinstance(record, self._OHLCVMsg)` — passing `None` to `isinstance` raises `TypeError`. Callback path is only registered after `start()` fully sets these, so in practice no runtime error, but the code pattern is fragile if the ordering is ever disturbed.

**Suggested fix:**

> Fragile initialization order.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 4: `P1-C2-15` [LOW]

**File/line:** [argus/data/databento_data_service.py:741,743,747,751](argus/data/databento_data_service.py#L741)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`asyncio.ensure_future()` without explicit loop** used inside `_schedule_*_publish` helpers. Invoked from the asyncio thread (via `call_soon_threadsafe`), so `get_event_loop()` resolves correctly — no bug. Python 3.12+ deprecates loop-less `get_event_loop()` from outside a running loop; here it is inside one. Fine today, at minor future-compat risk.

**Impact:**

> Potential DeprecationWarning on future Python.

**Suggested fix:**

> Switch to `self._loop.create_task(...)`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 5: `DEF-014` [MEDIUM]

**File/line:** argus/data/databento_data_service.py
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> SystemAlertEvent for dead data feed (reconnection exhaustion)

**Impact:**

> Health Monitor / Command Center cannot react to dead feed

**Suggested fix:**

> Fold into P1-A1 M9 health_monitor expansion; emit SystemAlertEvent on max-retries exceeded

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 6: `P1-C2-5` [MEDIUM]

**File/line:** [argus/data/historical_query_service.py:6-7](argus/data/historical_query_service.py#L6-L7) + [line 197](argus/data/historical_query_service.py#L197)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Stale cache-layout docstring.** Documents `{cache_dir}/{SYMBOL}/{YYYY-MM}.parquet` as the "expected layout"; Sprint 31.85 added the consolidated `{SYMBOL}/{SYMBOL}.parquet` layout, and the `regexp_extract` regex works for both (extracts from grandparent dir in either case). No runtime bug, but misleading.

**Impact:**

> Future developer may assume monthly layout is still primary or miss that the service supports either.

**Suggested fix:**

> Update lines 6-7 to document both supported layouts. Line 197 likewise. Cross-reference `docs/operations/parquet-cache-layout.md`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 7: `P1-C2-7` [MEDIUM]

**File/line:** [argus/data/historical_query_service.py:571-581](argus/data/historical_query_service.py#L571-L581)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **`close()` does not `interrupt()` in-flight DDL** — matches DEF-165 description (connection teardown hangs when `CREATE VIEW` is mid-flight; observed during DEF-164 late-night activation incident). Current code path: `self._conn.close()` directly.

**Impact:**

> Already an open DEF. Reconfirmed by inspection.

**Suggested fix:**

> Call `self._conn.interrupt()` before `.close()` in a try/except; document that `close()` is idempotent. Tracked by DEF-165.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 8: `P1-C2-17` [COSMETIC]

**File/line:** [argus/data/historical_query_service.py:201](argus/data/historical_query_service.py#L201)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Regex literal `'.*/([^/]+)/[^/]+\\.parquet$'` — should use raw string (`r'...'`) for clarity. Currently works.

**Impact:**

> Minor readability.

**Suggested fix:**

> Use raw string.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 9: `DEF-165` [LOW]

**File/line:** argus/data/historical_query_service.py
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> DuckDB connection close hangs when CREATE VIEW interrupted

**Impact:**

> Only manifests under DEF-164 conditions

**Suggested fix:**

> HistoricalQueryService.close() calls conn.interrupt() before conn.close()

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 10: `P1-C2-4` [MEDIUM]

**File/line:** [argus/data/intraday_candle_store.py:7-9](argus/data/intraday_candle_store.py#L7-L9)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Thread-safety docstring overclaims single-threaded access.** Docstring asserts "All access is single-threaded asyncio — no additional locking needed." But `get_bars`, `get_latest`, `has_bars`, `bar_count`, `symbols_with_bars` ([lines 90-172](argus/data/intraday_candle_store.py#L90-L172)) are synchronous functions. FastAPI runs sync `def` endpoints in a threadpool by default; if any REST endpoint consumes these synchronously, reads race the asyncio writer thread. In practice GIL + `deque.append` is atomic (safe), but `list(bars)` snapshot under concurrent append can see partial state. No known production issue, but the docstring is incorrect.

**Impact:**

> Future developer reads the comment, writes a helper that assumes exclusive access, introduces a race.

**Suggested fix:**

> Update docstring to "reads are GIL-atomic against append-only writes; no additional locking needed on CPython". Or wrap reads in an asyncio lock if strict correctness is desired.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 11: `P1-C2-8` [LOW]

**File/line:** [argus/data/intraday_candle_store.py:67-70](argus/data/intraday_candle_store.py#L67-L70)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Naive-timestamp handling treats naive as ET.** `if ts.tzinfo is None: ts_et = ts.replace(tzinfo=ET)`. Production path ([databento_data_service.py:641](argus/data/databento_data_service.py#L641)) always produces UTC-aware timestamps, so naive branch is unreachable in live operation. But replay / test fixtures that feed naive timestamps will be misinterpreted (treated as ET rather than UTC).

**Impact:**

> Silent time-bucketing bug in any consumer that constructs synthetic `CandleEvent`s without tzinfo.

**Suggested fix:**

> Either raise on naive timestamps (fail-fast) or document that naive means UTC and `.astimezone(ET)` accordingly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 12: `P1-C2-16` [COSMETIC]

**File/line:** [argus/data/intraday_candle_store.py:35](argus/data/intraday_candle_store.py#L35)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> Magic number `_MAX_BARS_PER_SYMBOL = 720` — adequate inline comment at line 34 ("12 hours of 1-minute bars"). Leave as-is.

**Impact:**

> None.

**Suggested fix:**

> None.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-06-data-layer**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-06-data-layer**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 13: `P1-D1-M04` [MEDIUM]

**File/line:** [intelligence/sources/fmp_news.py:129-131](argus/intelligence/sources/fmp_news.py#L129-L131)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **FMP "circuit breaker" (DEC-323) resets every poll cycle.** The `_disabled_for_cycle` flag is set `False` at the top of `fetch_catalysts()`, so once a 401/403 trips it, the *next* poll clears the flag, re-hits the API, re-logs the error, and re-trips. This is not a persistent circuit — it only suppresses spam *within* a single cycle.

**Impact:**

> On a Starter-plan 403 storm, every poll cycle produces a fresh ERROR log. Because `system_live.yaml` has `fmp_news.enabled: false` today, this is mostly dormant — but anyone flipping FMP news on without upgrading will get continuous ERROR-level noise, not the one-time-and-silent behaviour DEC-323's "circuit breaker" framing suggests.

**Suggested fix:**

> Change the semantics: keep the flag sticky across cycles, with a backoff of e.g. 1 hour before re-trying. Alternative: move the flag into `start()` and require an explicit manual reset.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 14: `P1-D1-M05` [MEDIUM]

**File/line:** [intelligence/sources/fmp_news.py:115-116](argus/intelligence/sources/fmp_news.py#L115-L116)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **FMP silently returns `[]` in firehose mode** — the polling loop's default is `firehose=True` (see `api/server.py:211`), so whenever the pipeline polls, FMP contributes nothing regardless of the `fmp_news.enabled` flag. The one-line docstring notes this, but there is no info-level log on the first firehose call, and `CatalystPipeline.run_poll()` reports `Source fmp_news returned 0 items` as if it had been consulted normally.

**Impact:**

> Inscrutable behaviour: an operator who toggles `fmp_news.enabled: true` will see "0 items" forever and will not realize FMP needs `firehose=False` to be used at all. Given FMP Starter disables news anyway, this is mostly academic — but directly contradicts the DEC-332 "firehose mode" architecture claim that all three sources participate.

**Suggested fix:**

> If the long-term plan is to replace per-symbol FMP polling with firehose (none exists), log this once per session and treat FMP as implicitly disabled in firehose mode. Alternatively mark FMP out of scope for firehose in the startup factory so `sources` list does not include it when the polling loop is firehose.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 15: `P1-I-C02` [COSMETIC]

**File/line:** [scripts/test_databento_scanner.py](../../../scripts/test_databento_scanner.py), `test_ibkr_bracket_lifecycle.py`, `test_ibkr_order_lifecycle.py`, `test_position_management_lifecycle.py`, `test_time_stop_eod.py`
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Five files in `scripts/` named `test_*.py` are manual diagnostic runners, NOT pytest tests. Not auto-discovered (testpaths is `tests/`) so no functional issue, but the naming is misleading.

**Impact:**

> Minor confusion. A new contributor might assume they run under pytest.

**Suggested fix:**

> Rename to `diagnose_*.py` (matches the pattern already established by `scripts/diagnose_databento.py`, `diagnose_feed.py`, `diagnose_live_streaming.py`) OR `verify_*.py`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 16: `P1-C2-3` [MEDIUM]

**File/line:** [argus/core/config.py:319-336](argus/core/config.py#L319-L336)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`UniverseFilterConfig` Sprint 29 fields lack validators.** `min_relative_volume: float \

**Impact:**

> None = None`, `min_gap_percent: float \

**Suggested fix:**

> None = None`, `min_premarket_volume: int \

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 17: `P1-C2-10` [LOW]

**File/line:** [argus/data/alpaca_data_service.py](argus/data/alpaca_data_service.py) + [argus/data/alpaca_scanner.py](argus/data/alpaca_scanner.py)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **Alpaca data/scanner still reachable via `system.yaml:9` (`data_source: "alpaca"`) and `scanner.yaml` (`scanner_type: "alpaca"`).** DEC-086 demoted Alpaca to incubator. Live production uses Databento + FMP. Dead-code in effect but not in code-reachability. No clear operator use case remaining for the incubator path.

**Impact:**

> Maintenance drag; tests still exercise these modules.

**Suggested fix:**

> Track retirement as a new DEF. If incubator is truly dead, delete modules, tests, config branches, and simplify `main.py:301-317` / `main.py:339-346` to a single live path.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 18: `P1-C2-19` [COSMETIC]

**File/line:** [argus/data/databento_utils.py](argus/data/databento_utils.py)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> 63 lines, `normalize_databento_df()` shared between DatabentoDataService and DataFetcher. Tight, focused, LIVE.

**Impact:**

> None.

**Suggested fix:**

> None.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-06-data-layer**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-06-data-layer**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 19: `DEF-037` [MEDIUM]

**File/line:** argus/data/fmp_reference.py
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> FMP API Key Redaction in Error Logs

**Impact:**

> FMP API URLs with apikey= appear in error logs

**Suggested fix:**

> Add .replace(api_key, "[REDACTED]") before logging in FMP error paths

**Audit notes:** Promoted from DEF via audit P1-H4

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 20: `P1-C2-14` [LOW]

**File/line:** [argus/data/fmp_scanner.py](argus/data/fmp_scanner.py)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **`criteria_list` parameter on `scan()` is ignored** — documented by DEF-032.

**Impact:**

> Known.

**Suggested fix:**

> Tracked.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 21: `P1-C2-6` [MEDIUM]

**File/line:** [argus/data/historical_query_config.py:28](argus/data/historical_query_config.py#L28)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`HistoricalQueryConfig.cache_dir` default still points at old cache.** `default = "data/databento_cache"` — if operator ever removes the `historical_query:` block from `system_live.yaml`, the service silently falls back to the old (slow) cache. Related to Finding #1 — even after fixing the yaml drift, the Python default is stale.

**Impact:**

> Latent regression risk if yaml config drifts or is cleared.

**Suggested fix:**

> Change default to `"data/databento_cache_consolidated"` (after Finding #1 is resolved, so default matches runtime).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 22: `P1-C2-20` [COSMETIC]

**File/line:** [argus/data/replay_data_service.py](argus/data/replay_data_service.py)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> Backtest/replay-only path; used by `scripts/*.py` and tests. LIVE for backtesting, not live trading.

**Impact:**

> None.

**Suggested fix:**

> None.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-06-data-layer**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-06-data-layer**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 23: `P1-C2-18` [COSMETIC]

**File/line:** [argus/data/scanner.py](argus/data/scanner.py)
**Safety:** `read-only-no-fix-needed`
**Action type:** Verify + audit-report annotation (no code change expected)

**Original finding:**

> Contains `Scanner` ABC (base class) + `StaticScanner` (fallback implementation used in `main.py:350`). LIVE — keep.

**Impact:**

> None.

**Suggested fix:**

> None.

**Required steps for this finding:**
1. Re-read the original audit finding in-context (file + line).
2. Run a quick verification (grep, test, or inspection) to confirm
   the observation still holds. Record the verification command and
   output below.
3. If verified AND the "Suggested fix" above is purely observational
   (e.g. "note", "document", "no action"): back-annotate the audit
   report row with `~~description~~ **RESOLVED-VERIFIED FIX-06-data-layer**`
   and move on. Make no code change.
4. If verified AND the "Suggested fix" explicitly asks for a DEF
   entry or a small code change (e.g. "Open a new DEF entry",
   "Add a comment", "Remove the stub"): treat this finding as if it
   were tagged `deferred-to-defs` — apply the suggested fix AND add
   a DEF-NNN entry to CLAUDE.md (grep for the highest existing
   DEF-NNN and increment). Back-annotate as
   `**RESOLVED FIX-06-data-layer**` (not -VERIFIED, since a change was
   made). Reference the DEF ID in the commit bullet.
5. If the verification *contradicts* the finding (i.e. it is now a
   real bug that requires a larger fix than the suggested_fix
   anticipates): **STOP**, log a note here, and escalate to the
   operator rather than silently applying an invented fix.

### Finding 24: `P1-C2-9` [LOW]

**File/line:** [argus/data/universe_manager.py:124](argus/data/universe_manager.py#L124)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Accesses private attribute `self._reference_client._cache.keys()`.** When no `initial_symbols` is passed and cache path has been chosen, the UM reaches into the client's private `_cache`. Violates the `reference_cache` property-based API (already exposed via FMPReferenceClient).

**Impact:**

> Tight coupling; refactor risk in FMP client.

**Suggested fix:**

> Expose `known_symbols()` on `FMPReferenceClient` and call that.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 25: `P1-C2-1` [CRITICAL]

**File/line:** [config/system_live.yaml:203](config/system_live.yaml#L203) + [config/system.yaml:194](config/system.yaml#L194) vs [config/historical_query.yaml:3](config/historical_query.yaml#L3)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **Live HistoricalQueryService still reads the OLD cache despite Sprint 31.85 "repoint".** [core/config.py:1355-1372](argus/core/config.py#L1355-L1372) `load_config()` loads only `system.yaml`, `risk_limits.yaml`, `brokers.yaml`, `orchestrator.yaml`, `notifications.yaml`. `config/historical_query.yaml` is NEVER loaded at runtime — it is consumed only by `scripts/run_experiment.py`, `scripts/resolve_sweep_symbols.py`, and the CLI tool. The live service starts from `app_state.config.historical_query` at [api/server.py:477](argus/api/server.py#L477) — which is populated from the `historical_query:` block in `system_live.yaml` (still `data/databento_cache`). [docs/operations/parquet-cache-layout.md:101-105](docs/operations/parquet-cache-layout.md#L101-L105) instructs the operator to edit `config/historical_query.yaml` — this does NOT take effect for the live system.

**Impact:**

> VIEW queries against ~983K monthly Parquet files — "hours-long scans" per the operations doc — continue to be the runtime behavior. REST endpoints at [api/routes/historical.py](argus/api/routes/historical.py) and the ExperimentRunner in-process path [intelligence/experiments/runner.py](argus/intelligence/experiments/runner.py) share this. The operator's mental model ("I activated the consolidated cache") disagrees with runtime. DEF-164/165 (late-night activation incident) may have appeared resolved, but the runtime is still on the slow path.

**Suggested fix:**

> Pick one: (a) add `historical_query.yaml` to `load_config()`'s `file_mapping` and have it override the SystemConfig section; (b) update `system_live.yaml:203` + `system.yaml:194` to `data/databento_cache_consolidated`; (c) delete `config/historical_query.yaml` and move the `cache_dir` note into `system_live.yaml`. Option (b) is the minimum-change fix and matches the pattern used by `vix_regime` (system yaml is authoritative). Update [docs/operations/parquet-cache-layout.md:101-105](docs/operations/parquet-cache-layout.md#L101-L105) to match the chosen file.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

### Finding 26: `P1-G1-L04` [LOW]

**File/line:** Data layer modules: `vix_data_service.py` (59%), `databento_data_service.py` (79%), `fmp_reference.py` (83%), `alpaca_data_service.py` (85%)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Data-service coverage is materially below the 90% target in `testing.md` §Core Logic. The `vix_data_service.py` gap in particular covers lines 556-685 — almost the entire `refresh()` / backfill code path.

**Impact:**

> VIX data is a RegimeClassifierV2 input; a silent regression in refresh would yield stale-but-plausible regime labels. Low severity because VIXDataService has explicit staleness self-disable guard per DEC-349.

**Suggested fix:**

> Add tests for `VIXDataService.refresh()` happy path + FMP fallback branch. Data-service tests are well-established pattern — follow `test_fmp_reference.py`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-06-data-layer**`.

## Post-Session Verification

### Full pytest suite

```bash
python -m pytest --ignore=tests/test_main.py -n auto -q 2>&1 | tail -3
# Record new PASS count here: __________
# Net delta: __________ (MUST be >= 0)
```

**Fail condition:** net delta < 0. If this happens:
1. DO NOT commit.
2. `git checkout .` to revert.
3. Re-triage: was the fix wrong, or did it collide with another finding?
4. If fix is correct but a test needed updating, apply test update as a
   SECOND commit after the fix — do not squash into the fix commit.

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-06-data-layer** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-06-data-layer**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-06): data layer cleanup

Addresses audit findings:
- P1-C2-11 [LOW]: 'fetch_daily_bars()' passes 'apikey' in URL params dict
- P1-C2-12 [LOW]: '_check_parquet_cache()' only checks the month of 'start' — multi-month queries silently return partial data
- P1-C2-13 [LOW]: Record-class references typed 'type \
- P1-C2-15 [LOW]: 'asyncio
- DEF-014 [MEDIUM]: SystemAlertEvent for dead data feed (reconnection exhaustion)
- P1-C2-5 [MEDIUM]: Stale cache-layout docstring
- P1-C2-7 [MEDIUM]: 'close()' does not 'interrupt()' in-flight DDL — matches DEF-165 description (connection teardown hangs when 'CREATE VIE
- P1-C2-17 [COSMETIC]: Regex literal ''
- DEF-165 [LOW]: DuckDB connection close hangs when CREATE VIEW interrupted
- P1-C2-4 [MEDIUM]: Thread-safety docstring overclaims single-threaded access
- P1-C2-8 [LOW]: Naive-timestamp handling treats naive as ET
- P1-C2-16 [COSMETIC]: Magic number '_MAX_BARS_PER_SYMBOL = 720' — adequate inline comment at line 34 ("12 hours of 1-minute bars")
- P1-D1-M04 [MEDIUM]: FMP "circuit breaker" (DEC-323) resets every poll cycle
- P1-D1-M05 [MEDIUM]: FMP silently returns '[]' in firehose mode — the polling loop's default is 'firehose=True' (see 'api/server
- P1-I-C02 [COSMETIC]: Five files in 'scripts/' named 'test_*
- P1-C2-3 [MEDIUM]: 'UniverseFilterConfig' Sprint 29 fields lack validators
- P1-C2-10 [LOW]: Alpaca data/scanner still reachable via 'system
- P1-C2-19 [COSMETIC]: 63 lines, 'normalize_databento_df()' shared between DatabentoDataService and DataFetcher
- DEF-037 [MEDIUM]: FMP API Key Redaction in Error Logs
- P1-C2-14 [LOW]: 'criteria_list' parameter on 'scan()' is ignored — documented by DEF-032
- P1-C2-6 [MEDIUM]: 'HistoricalQueryConfig
- P1-C2-20 [COSMETIC]: Backtest/replay-only path; used by 'scripts/*
- P1-C2-18 [COSMETIC]: Contains 'Scanner' ABC (base class) + 'StaticScanner' (fallback implementation used in 'main
- P1-C2-9 [LOW]: Accesses private attribute 'self
- P1-C2-1 [CRITICAL]: Live HistoricalQueryService still reads the OLD cache despite Sprint 31
- P1-G1-L04 [LOW]: Data-service coverage is materially below the 90% target in 'testing

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions
- [ ] Commit pushed to `main` with the exact message format above
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-06-data-layer**`
