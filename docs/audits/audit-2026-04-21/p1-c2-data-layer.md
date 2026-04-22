# Audit: Data Layer
**Session:** P1-C2
**Date:** 2026-04-21
**Scope:** `argus/data/` — 18 files, ~7,444 lines. Databento/FMP/Alpaca data sources, scanners, Universe Manager, Indicator Engine, Historical Query Service, IntradayCandleStore, VIX.
**Files examined:** 6 deep-read / 12 skimmed (all 18 files inspected at some depth)

## Pre-flag Verdicts

### PF-06 — `argus/data/service.py` (unclear provenance)
**LIVE.** [service.py](argus/data/service.py) is the abstract `DataService` ABC — DEC-029 single streaming surface. Four concrete implementations inherit from it:
- `AlpacaDataService`, `DatabentoDataService`, `ReplayDataService` ([service.py:15](argus/data/service.py#L15))
- `BacktestDataService` ([backtest/backtest_data_service.py:22](argus/backtest/backtest_data_service.py#L22))

All 7 strategy modules import it under `TYPE_CHECKING` for type hints. **Not dead; do not remove.**

### PF-07 — Alpaca data/scanner code (DEC-086 demoted to incubator)
**REACHABLE BUT OFF THE LIVE PATH.** `system.yaml:9` still sets `data_source: "alpaca"` (incubator); `system_live.yaml:18` sets `databento`. `main.py:301-317` branches on `DataSource` — `ALPACA` branch instantiates `AlpacaDataService`; `AlpacaScanner` reachable via `scanner.yaml` `scanner_type: "alpaca"` (currently set to `"fmp"`). Test suites in [tests/data/test_alpaca_data_service.py](tests/data/test_alpaca_data_service.py) and [tests/data/test_alpaca_scanner.py](tests/data/test_alpaca_scanner.py) still exercise them. Safe to keep unless the incubator path is explicitly retired. **Finding #10 below.**

### Sprint 31.85 Parquet repoint verification
**PARTIAL / DRIFT DETECTED.** `config/historical_query.yaml:3` points at the consolidated cache (`data/databento_cache_consolidated`), but this file is **not loaded by the live runtime**. The authoritative runtime config is `system_live.yaml:203` / `system.yaml:194`, both of which still point at the **original** cache (`data/databento_cache`). See CRITICAL Finding #1 below.

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 1 | [config/system_live.yaml:203](config/system_live.yaml#L203) + [config/system.yaml:194](config/system.yaml#L194) vs [config/historical_query.yaml:3](config/historical_query.yaml#L3) | **RESOLVED FIX-06-data-layer** (via FIX-16 overlay wiring + cache_dir flip) — **Live HistoricalQueryService still reads the OLD cache despite Sprint 31.85 "repoint".** [core/config.py:1355-1372](argus/core/config.py#L1355-L1372) `load_config()` loads only `system.yaml`, `risk_limits.yaml`, `brokers.yaml`, `orchestrator.yaml`, `notifications.yaml`. `config/historical_query.yaml` is NEVER loaded at runtime — it is consumed only by `scripts/run_experiment.py`, `scripts/resolve_sweep_symbols.py`, and the CLI tool. The live service starts from `app_state.config.historical_query` at [api/server.py:477](argus/api/server.py#L477) — which is populated from the `historical_query:` block in `system_live.yaml` (still `data/databento_cache`). [docs/operations/parquet-cache-layout.md:101-105](docs/operations/parquet-cache-layout.md#L101-L105) instructs the operator to edit `config/historical_query.yaml` — this does NOT take effect for the live system. | VIEW queries against ~983K monthly Parquet files — "hours-long scans" per the operations doc — continue to be the runtime behavior. REST endpoints at [api/routes/historical.py](argus/api/routes/historical.py) and the ExperimentRunner in-process path [intelligence/experiments/runner.py](argus/intelligence/experiments/runner.py) share this. The operator's mental model ("I activated the consolidated cache") disagrees with runtime. DEF-164/165 (late-night activation incident) may have appeared resolved, but the runtime is still on the slow path. | Pick one: (a) add `historical_query.yaml` to `load_config()`'s `file_mapping` and have it override the SystemConfig section; (b) update `system_live.yaml:203` + `system.yaml:194` to `data/databento_cache_consolidated`; (c) delete `config/historical_query.yaml` and move the `cache_dir` note into `system_live.yaml`. Option (b) is the minimum-change fix and matches the pattern used by `vix_regime` (system yaml is authoritative). Update [docs/operations/parquet-cache-layout.md:101-105](docs/operations/parquet-cache-layout.md#L101-L105) to match the chosen file. | weekend-only |

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 2 | [config/vix_regime.yaml](config/vix_regime.yaml) (all lines) + [config/system_live.yaml:161](config/system_live.yaml#L161) | **Standalone `vix_regime.yaml` never loaded at runtime** (same drift class as Finding #1). Confirmed by [docs/sprint-history.md:2170](docs/sprint-history.md#L2170) — `load_config()` doesn't read it. `system_live.yaml` `vix_regime:` block only contains `enabled: true`; all thresholds come from `VixRegimeConfig` Pydantic defaults. Comment in `system_live.yaml:161` ("Detailed params in vix_regime.yaml") is misleading. | Operator editing `vix_regime.yaml` expects tuning; changes do nothing. | Option A: add `vix_regime.yaml` to `load_config()` and merge into `SystemConfig.vix_regime` (same approach as Finding #1). Option B: delete `vix_regime.yaml`, move the commented threshold docs inline into `system_live.yaml`. Option C: update `system_live.yaml:161` comment to note the file is documentation-only. | safe-during-trading |
| 3 | [argus/core/config.py:319-336](argus/core/config.py#L319-L336) | **RESOLVED FIX-06-data-layer** — **`UniverseFilterConfig` Sprint 29 fields lack validators.** `min_relative_volume: float \| None = None`, `min_gap_percent: float \| None = None`, `min_premarket_volume: int \| None = None` have no `ge=0` constraint. Pydantic accepts negative values silently. Also: these three fields are NOT enforced in [`_symbol_matches_filter()` at universe_manager.py:409-482](argus/data/universe_manager.py#L409-L482) — intentional per sprint-history (enforced at strategy detection level). That intent is undocumented in the config model. | Misconfiguration goes undetected; reader of config model cannot tell which fields UM enforces vs. which are strategy-level. | Add `ge=0` constraint to all three fields. Add one-line docstring noting "enforced at strategy detection layer, not routing". | weekend-only |
| 4 | [argus/data/intraday_candle_store.py:7-9](argus/data/intraday_candle_store.py#L7-L9) | **RESOLVED FIX-06-data-layer** — **Thread-safety docstring overclaims single-threaded access.** Docstring asserts "All access is single-threaded asyncio — no additional locking needed." But `get_bars`, `get_latest`, `has_bars`, `bar_count`, `symbols_with_bars` ([lines 90-172](argus/data/intraday_candle_store.py#L90-L172)) are synchronous functions. FastAPI runs sync `def` endpoints in a threadpool by default; if any REST endpoint consumes these synchronously, reads race the asyncio writer thread. In practice GIL + `deque.append` is atomic (safe), but `list(bars)` snapshot under concurrent append can see partial state. No known production issue, but the docstring is incorrect. | Future developer reads the comment, writes a helper that assumes exclusive access, introduces a race. | Update docstring to "reads are GIL-atomic against append-only writes; no additional locking needed on CPython". Or wrap reads in an asyncio lock if strict correctness is desired. | safe-during-trading |
| 5 | [argus/data/historical_query_service.py:6-7](argus/data/historical_query_service.py#L6-L7) + [line 197](argus/data/historical_query_service.py#L197) | **RESOLVED FIX-06-data-layer** — **Stale cache-layout docstring.** Documents `{cache_dir}/{SYMBOL}/{YYYY-MM}.parquet` as the "expected layout"; Sprint 31.85 added the consolidated `{SYMBOL}/{SYMBOL}.parquet` layout, and the `regexp_extract` regex works for both (extracts from grandparent dir in either case). No runtime bug, but misleading. | Future developer may assume monthly layout is still primary or miss that the service supports either. | Update lines 6-7 to document both supported layouts. Line 197 likewise. Cross-reference `docs/operations/parquet-cache-layout.md`. | safe-during-trading |
| 6 | [argus/data/historical_query_config.py:28](argus/data/historical_query_config.py#L28) | **RESOLVED FIX-06-data-layer** — **`HistoricalQueryConfig.cache_dir` default still points at old cache.** `default = "data/databento_cache"` — if operator ever removes the `historical_query:` block from `system_live.yaml`, the service silently falls back to the old (slow) cache. Related to Finding #1 — even after fixing the yaml drift, the Python default is stale. | Latent regression risk if yaml config drifts or is cleared. | Change default to `"data/databento_cache_consolidated"` (after Finding #1 is resolved, so default matches runtime). | weekend-only |
| 7 | [argus/data/historical_query_service.py:571-581](argus/data/historical_query_service.py#L571-L581) | **RESOLVED FIX-06-data-layer** (DEF-165 closed) — **`close()` does not `interrupt()` in-flight DDL** — matches DEF-165 description (connection teardown hangs when `CREATE VIEW` is mid-flight; observed during DEF-164 late-night activation incident). Current code path: `self._conn.close()` directly. | Already an open DEF. Reconfirmed by inspection. | Call `self._conn.interrupt()` before `.close()` in a try/except; document that `close()` is idempotent. Tracked by DEF-165. | deferred-to-defs |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 8 | [argus/data/intraday_candle_store.py:67-70](argus/data/intraday_candle_store.py#L67-L70) | **RESOLVED FIX-06-data-layer** (fail-fast on naive) — **Naive-timestamp handling treats naive as ET.** `if ts.tzinfo is None: ts_et = ts.replace(tzinfo=ET)`. Production path ([databento_data_service.py:641](argus/data/databento_data_service.py#L641)) always produces UTC-aware timestamps, so naive branch is unreachable in live operation. But replay / test fixtures that feed naive timestamps will be misinterpreted (treated as ET rather than UTC). | Silent time-bucketing bug in any consumer that constructs synthetic `CandleEvent`s without tzinfo. | Either raise on naive timestamps (fail-fast) or document that naive means UTC and `.astimezone(ET)` accordingly. | safe-during-trading |
| 9 | [argus/data/universe_manager.py:124](argus/data/universe_manager.py#L124) | **RESOLVED FIX-06-data-layer** — **Accesses private attribute `self._reference_client._cache.keys()`.** When no `initial_symbols` is passed and cache path has been chosen, the UM reaches into the client's private `_cache`. Violates the `reference_cache` property-based API (already exposed via FMPReferenceClient). | Tight coupling; refactor risk in FMP client. | Expose `known_symbols()` on `FMPReferenceClient` and call that. | safe-during-trading |
| 10 | [argus/data/alpaca_data_service.py](argus/data/alpaca_data_service.py) + [argus/data/alpaca_scanner.py](argus/data/alpaca_scanner.py) | **RESOLVED FIX-06-data-layer** (deferred via new DEF-183) — **Alpaca data/scanner still reachable via `system.yaml:9` (`data_source: "alpaca"`) and `scanner.yaml` (`scanner_type: "alpaca"`).** DEC-086 demoted Alpaca to incubator. Live production uses Databento + FMP. Dead-code in effect but not in code-reachability. No clear operator use case remaining for the incubator path. | Maintenance drag; tests still exercise these modules. | Track retirement as a new DEF. If incubator is truly dead, delete modules, tests, config branches, and simplify `main.py:301-317` / `main.py:339-346` to a single live path. | deferred-to-defs |
| 11 | [argus/data/databento_data_service.py:1200-1214](argus/data/databento_data_service.py#L1200-L1214) | **RESOLVED FIX-06-data-layer** (warning comment + paired DEF-037 redaction fix) — **`fetch_daily_bars()` passes `apikey` in URL params dict.** Error handlers at lines 1251-1256 do not log the URL/params — currently safe (DEF-037 prevention). Latent risk: if an error branch ever logs `response.url` or exception context, FMP API key leaks. | Regression risk. | Move key to a header (`Authorization`) if FMP permits; otherwise keep, and add a code comment warning future editors not to log response context. | safe-during-trading |
| 12 | [argus/data/databento_data_service.py:1105-1141](argus/data/databento_data_service.py#L1105-L1141) | **RESOLVED FIX-06-data-layer** (multi-month concat with fail-closed on missing month) — **`_check_parquet_cache()` only checks the month of `start` — multi-month queries silently return partial data.** Comment at [line 1122-1123](argus/data/databento_data_service.py#L1122-L1123) acknowledges this: "Full implementation would merge multiple monthly files." | For live ops this is typically single-month queries — fine. For tooling or ad-hoc lookups that span months, cache returns a subset and the caller doesn't know. | Either reject multi-month requests (fail-closed) or concat monthly files when start.month != end.month. | safe-during-trading |
| 13 | [argus/data/databento_data_service.py:113-117](argus/data/databento_data_service.py#L113-L117) | **RESOLVED FIX-06-data-layer** (init-ordering contract documented) — **Record-class references typed `type \| None = None`** at init and populated later in `_connect_live_session()`. Used in `_dispatch_record()` via `isinstance(record, self._OHLCVMsg)` — passing `None` to `isinstance` raises `TypeError`. Callback path is only registered after `start()` fully sets these, so in practice no runtime error, but the code pattern is fragile if the ordering is ever disturbed. | Fragile initialization order. | Lift the `import databento as db` to module top-level (already paid once per process) and assign the class references at construction. | safe-during-trading |
| 14 | [argus/data/fmp_scanner.py](argus/data/fmp_scanner.py) | **RESOLVED-VERIFIED FIX-06-data-layer** (DEF-032 pointer re-verified inline) — **`criteria_list` parameter on `scan()` is ignored** — documented by DEF-032. | Known. | Tracked. | deferred-to-defs |
| 15 | [argus/data/databento_data_service.py:741,743,747,751](argus/data/databento_data_service.py#L741) | **RESOLVED FIX-06-data-layer** (switched to self._loop.create_task) — **`asyncio.ensure_future()` without explicit loop** used inside `_schedule_*_publish` helpers. Invoked from the asyncio thread (via `call_soon_threadsafe`), so `get_event_loop()` resolves correctly — no bug. Python 3.12+ deprecates loop-less `get_event_loop()` from outside a running loop; here it is inside one. Fine today, at minor future-compat risk. | Potential DeprecationWarning on future Python. | Switch to `self._loop.create_task(...)`. | safe-during-trading |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 16 | [argus/data/intraday_candle_store.py:35](argus/data/intraday_candle_store.py#L35) | **RESOLVED-VERIFIED FIX-06-data-layer** — Magic number `_MAX_BARS_PER_SYMBOL = 720` — adequate inline comment at line 34 ("12 hours of 1-minute bars"). Leave as-is. | None. | None. | read-only-no-fix-needed |
| 17 | [argus/data/historical_query_service.py:201](argus/data/historical_query_service.py#L201) | **RESOLVED FIX-06-data-layer** (extracted as `_SYMBOL_FROM_FILENAME_REGEX` raw-string constant at module scope) — Regex literal `'.*/([^/]+)/[^/]+\\.parquet$'` — should use raw string (`r'...'`) for clarity. Currently works. | Minor readability. | Use raw string. | safe-during-trading |
| 18 | [argus/data/scanner.py](argus/data/scanner.py) | **RESOLVED-VERIFIED FIX-06-data-layer** — Contains `Scanner` ABC (base class) + `StaticScanner` (fallback implementation used in `main.py:350`). LIVE — keep. | None. | None. | read-only-no-fix-needed |
| 19 | [argus/data/databento_utils.py](argus/data/databento_utils.py) | **RESOLVED-VERIFIED FIX-06-data-layer** — 63 lines, `normalize_databento_df()` shared between DatabentoDataService and DataFetcher. Tight, focused, LIVE. | None. | None. | read-only-no-fix-needed |
| 20 | [argus/data/replay_data_service.py](argus/data/replay_data_service.py) | **RESOLVED-VERIFIED FIX-06-data-layer** — Backtest/replay-only path; used by `scripts/*.py` and tests. LIVE for backtesting, not live trading. | None. | None. | read-only-no-fix-needed |

---

## Scanner / DataService Liveness Matrix

Per `config/scanner.yaml:6` (`scanner_type: "fmp"`) and `config/system_live.yaml:18` (`data_source: "databento"`):

| File | Status | Reached via |
|------|--------|-------------|
| `service.py` (ABC) | **LIVE** | All 4 concrete implementations + strategy type hints |
| `databento_data_service.py` | **LIVE** (production) | `main.py:303` when `data_source == DATABENTO` |
| `alpaca_data_service.py` | **INCUBATOR** | `main.py:311` when `data_source == ALPACA` (only `system.yaml`) |
| `replay_data_service.py` | **LIVE** (backtest path) | Scripts + tests |
| `scanner.py` (ABC + StaticScanner) | **LIVE** | Base class + `main.py:350` fallback |
| `fmp_scanner.py` | **LIVE** (production) | `main.py:330` when `scanner_type == "fmp"` |
| `databento_scanner.py` | **DEAD-IN-EFFECT** | Reachable only via `scanner.yaml` `scanner_type: "databento"` (not set) |
| `alpaca_scanner.py` | **INCUBATOR** | Reachable only via `scanner.yaml` `scanner_type: "alpaca"` |
| `databento_utils.py` | **LIVE** | Shared normalizer |
| `indicator_engine.py` | **LIVE** | All 4 DataService impls delegate |
| `universe_manager.py` | **LIVE** | `main.py` when `universe_manager.enabled` |
| `fmp_reference.py` | **LIVE** | UM dependency; canary + batch fetch + cache persistence |
| `historical_query_service.py` | **LIVE (runtime) + LIVE (CLI)** — with cache drift per Finding #1 | `api/server.py:477`, ExperimentRunner, CLI scripts |
| `historical_query_config.py` | **LIVE** | Pydantic model |
| `intraday_candle_store.py` | **LIVE** | EventBus subscriber, market bars REST, Arena candle endpoint, CounterfactualTracker |
| `vix_data_service.py` | **LIVE** (when `vix_regime.enabled`) | Regime Intelligence pipeline |
| `vix_config.py` | **LIVE** | Pydantic model |

---

## Direct Answers to Audit Questions

**1.1 Alpaca liveness** — `alpaca_data_service.py` + `alpaca_scanner.py` reachable only via `system.yaml`/`scanner.yaml` config strings; DEC-086 demoted to incubator. Tests in `tests/data/` still exercise them. Not on live production path.

**1.2 Scanner live per DEC-258** — FMPScannerSource is live. DatabentoScanner/AlpacaScanner are code-reachable but not selected by current `scanner.yaml`.

**1.3 `scanner.py`** — Abstract `Scanner` class + `StaticScanner` fallback. Still used at `main.py:350`.

**2. `service.py`** — LIVE ABC, not legacy. Keep.

**3.1 Universe Manager coherence** — DEC-277/314/317/361/362 layers are coherent, not a quilt. `trust_cache` fast path at [universe_manager.py:92-113](argus/data/universe_manager.py#L92-L113) cleanly separates boot behavior from the incremental-fetch path.

**3.2 `UniverseFilterConfig` Sprint 29 fields** — fields exist (`min_relative_volume`, `min_gap_percent`, `min_premarket_volume`) but lack `ge=0` constraints. Not enforced at UM routing layer — strategy-level enforcement (documented in sprint-history, undocumented in the config model). See Finding #3.

**3.3 DEC-277 fail-closed on missing reference data** — preserved. [_apply_system_filters:243-245](argus/data/universe_manager.py#L243) fail-closed at system layer; [_symbol_matches_filter:429-431](argus/data/universe_manager.py#L429) fail-closed when `ref_data is None` at routing layer. Per-field None treated as PASS — intentional, documented at lines 358-361.

**3.4 `set_watchlist(symbols, source=...)` (DEC-343)** — lives on `BaseStrategy` at [base_strategy.py:283-299](argus/strategies/base_strategy.py#L283), not on `UniverseManager`. `source` parameter is passed through to a debug log; not validated. All callers use `"scanner"` or `"universe_manager"` as documented.

**4.1 DEC-088 thread→asyncio bridge** — consistent. [_on_ohlcv:666-669](argus/data/databento_data_service.py#L666), [_on_trade:723-724](argus/data/databento_data_service.py#L723), and the stale-monitor path all use `call_soon_threadsafe`. Reader thread never touches asyncio primitives directly.

**4.2 DEC-316 time-aware warm-up** — matches spec. [_warm_up_indicators:851-884](argus/data/databento_data_service.py#L851) skips pre-market, enables lazy mid-session backfill via `_symbols_needing_warmup` set guarded by `_warmup_lock` (threading lock — correct, reader thread writes it in `_on_ohlcv`).

**4.3 OHLCV-1m observability counters (Apr 3 hotfix)** — all wired:
- Unmapped ([line 589](argus/data/databento_data_service.py#L589)), filtered-universe ([line 604](argus/data/databento_data_service.py#L604)), filtered-active ([line 610](argus/data/databento_data_service.py#L610))
- First-event sentinels ([line 614](argus/data/databento_data_service.py#L614) OHLCV; [line 697](argus/data/databento_data_service.py#L697) trade; [line 590](argus/data/databento_data_service.py#L590) unmapped warning once-per-session)
- SymbolMappingMsg progress ([line 566-570](argus/data/databento_data_service.py#L566))
- Heartbeat reports drop counts and trades summary ([line 1056-1073](argus/data/databento_data_service.py#L1056))

**4.4 Zero-candle WARNING escalation with holiday suppression** — correct. [_data_heartbeat:1082-1097](argus/data/databento_data_service.py#L1082) calls `is_market_holiday()` and downgrades to INFO with holiday name.

**4.5 `fetch_daily_bars()` fallback on FMP outage** — returns `None` on timeout/HTTP-error/missing-key ([line 1251-1256](argus/data/databento_data_service.py#L1251)). Caller (Orchestrator regime reclassification) handles `None` by skipping the update. Graceful.

**5.1 IntradayCandleStore 4 AM ET pre-market filter** — correct ([line 31-35, 73](argus/data/intraday_candle_store.py#L31)). 720-bar cap matches 12-hour window.

**5.2 Query API consumer coverage** — `get_bars`, `get_latest`, `has_bars`, `bar_count` are used by market bars REST, PatternBasedStrategy backfill, CounterfactualTracker, and Arena candle endpoint (confirmed via grep in earlier pass).

**5.3 IntradayCandleStore thread safety** — overclaims single-threaded asyncio; see Finding #4.

**6.1 HistoricalQueryService config-gating** — consistent; [init:86-90](argus/data/historical_query_service.py#L86) short-circuits if `enabled=False`.

**6.2 Lazy init on first query** — all methods raise `ServiceUnavailableError` if `_available=False` or `_conn is None`; no lazy reconnect.

**6.3 VIEW over consolidated cache** — glob pattern is `{cache_dir}/**/*.parquet` ([line 194](argus/data/historical_query_service.py#L194)); `regexp_extract(filename, '.*/([^/]+)/[^/]+\.parquet$', 1)` pulls the parent directory name — works for both `{SYMBOL}/{YYYY-MM}.parquet` (old) and `{SYMBOL}/{SYMBOL}.parquet` (new consolidated). **But per Finding #1, the live cache_dir is still the OLD cache.**

**6.4 `validate_symbol_coverage()` bypass** — no bypass. Parameterized query ([line 485-492](argus/data/historical_query_service.py#L485)).

**6.5 `regexp_extract`** — still used; works for both layouts.

**6.6 Timestamp column** — uses `"timestamp"` ([line 202,280](argus/data/historical_query_service.py#L202)) aliased to `ts_event`. Code assumes the Parquet column is literally named `timestamp`. Consolidation script embeds `symbol` column (confirmed via sprint history) but does not rename the timestamp column. Validation query at [line 215](argus/data/historical_query_service.py#L215) would fail fast if schema differed.

**7.1 VIX trust-cache-on-startup** — yes (data persisted in SQLite; `_CREATE_TABLE_SQL IF NOT EXISTS`).

**7.2 `max_staleness_days: 3` self-disable** — defined in config; applied via business-day counting.

**7.3 `VixRegimeConfig` wiring** — wired under `SystemConfig.vix_regime` at [core/config.py:411](argus/core/config.py#L411). However, `config/vix_regime.yaml` is NOT loaded at runtime (same drift class as Finding #1). See Finding #2.

**7.4 yfinance graceful degradation** — `VIXDataUnavailable` exception type + staleness self-disable. yfinance is unofficial (DEF-103 tracks this).

**8.1 FMP news circuit breaker** — lives in `argus/intelligence/sources/fmp_news.py`, not in `argus/data/fmp_reference.py`. DEC-323 applies to news endpoints only; `fmp_reference.py` (profiles, share float, daily bars) is scoped to Starter-plan endpoints that work without 403. Reference client does not implement DEC-323 semantics — correct scope separation.

**8.2 FMP batch size** — 50 (configurable, default). FMP documentation caps batch-profile at 50.

**8.3 Rate-limit handling** — exponential backoff (2s, 4s, 8s) on 429/5xx at [line 547-557](argus/data/fmp_reference.py#L547); per-request `rate_limit_delay_seconds: 0.2`.

**9.1 IndicatorEngine purity** — stateful per-symbol (VWAP cumulative, ATR Wilder state, close history, RVOL baseline). Docstring explicitly states "NOT thread-safe" ([line 62](argus/data/indicator_engine.py#L62)) — ownership by DataService.

**9.2 Unused indicators** — all 6 (`vwap`, `atr_14`, `sma_9/20/50`, `rvol`) consumed by strategies: ATR used in exit_math.py/fill_model.py, VWAP in VwapReclaim / VwapBounce, SMAs + RVOL in multiple gates. None orphaned.

**9.3 ATR consistency** — engine returns Wilder's-smoothed ATR(14). `exit_math.compute_trail_stop_price()` and `fill_model.evaluate_bar_exit()` read the same value (not recomputed locally). Consistent.

---

## Positive Observations

1. **OHLCV-1m observability stack is exemplary.** Per-gate drop counters (unmapped / filtered-universe / filtered-active / trades-unmapped / trades-received), first-event sentinels (fire-once-per-session), SymbolMappingMsg progress logs, heartbeat with market-hours + holiday-suppressed escalation — together they turn a silent data-loss class of failure into a loud one. [databento_data_service.py:125-138,589-638,1021-1099](argus/data/databento_data_service.py#L125-L138) is the best-instrumented hot path in the codebase; replicate this pattern in any future streaming integration.

2. **DEC-088 thread→asyncio bridge is consistent.** Every single reader-thread callback path (OHLCV, trade, stale monitor) bridges via `call_soon_threadsafe` before touching the Event Bus. No latent primitives-on-reader-thread leaks.

3. **DEC-277 fail-closed-on-missing-reference-data is honored at both system-filter and routing-filter layers.** Different behavior for "symbol unknown" (fail closed) vs "some fields unknown" (fail open per-field) is documented and consistent.

4. **Time-aware warm-up (DEC-316)** — clean split between pre-market boot (skip) and mid-session lazy-load (one symbol at a time on first candle). The `_warmup_lock` is a threading lock, not an asyncio lock — correct choice because the reader thread is the writer.

5. **HistoricalQueryService schema auto-discovery.** Logs the Parquet column names at startup ([line 183-186](argus/data/historical_query_service.py#L183)) so any future schema drift is caught at boot. Operationally defensive.

6. **IndicatorEngine extraction** (DEF-013) leaves a single source of truth — all four DataServices delegate, so ATR/VWAP/SMA/RVOL math is identical across live, replay, backtest, and paper paths. No silent divergence risk.

7. **Canary test on FMP API schema.** [fmp_reference.py:211-249](argus/data/fmp_reference.py#L211) fetches an AAPL profile and verifies required keys (`symbol`, `companyName`, `marketCap`, `price`). If FMP changes their response shape, this fires a WARNING at boot rather than silently corrupting the reference cache.

8. **Trust-cache-on-startup (DEC-362)** — `build_viable_universe(trust_cache=True)` returns cached data without a single FMP round-trip. Paired with a background refresh task, this removes minutes from boot time and makes the startup deterministic under FMP outages.

9. **VixRegimeConfig `validate_window_ordering` model validator.** [vix_config.py:193-201](argus/data/vix_config.py#L193) enforces `vol_short_window < vol_long_window` — catches a misconfiguration that would produce silently wrong vol-of-vol ratios. More of this kind of cross-field validation would be welcome elsewhere.

10. **IntradayCandleStore is a clean 177-line utility.** Single responsibility, `deque(maxlen=N)` for bounded memory, no hidden state, comprehensive query API. Easy to reason about; easy to test.

---

## Statistics

- Files deep-read: 6 — `databento_data_service.py`, `universe_manager.py` (partial), `fmp_reference.py` (partial), `historical_query_service.py`, `intraday_candle_store.py`, `indicator_engine.py`
- Files skimmed: 12 — `service.py`, `scanner.py`, `databento_scanner.py`, `fmp_scanner.py`, `alpaca_scanner.py`, `alpaca_data_service.py`, `replay_data_service.py`, `databento_utils.py`, `vix_data_service.py`, `vix_config.py`, `historical_query_config.py`
- Total findings: 20 (1 critical, 6 medium, 8 low, 5 cosmetic)
- Safety distribution: 7 safe-during-trading / 4 weekend-only / 6 read-only-no-fix-needed / 3 deferred-to-defs
- Estimated Phase 3 fix effort: 2 sessions
  - **Session A (safe-during-trading batch):** Findings #2, #4, #5, #8, #11, #13, #15, #17 — docstring/comment fixes, defensive notes, Python-3.12-compat. Single session, ~1 hour.
  - **Session B (weekend-only batch):** Findings #1, #3, #6, #9 — the critical cache-dir drift + `UniverseFilterConfig` validators + `HistoricalQueryConfig` default + UM private-attr access. One session, ~2 hours. Must land with paper trading paused.
  - Findings #7 and #10 and #14 → tracked by existing / new DEF entries.
