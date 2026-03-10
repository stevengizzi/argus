# Sprint 23.6: Tier 3 Review Remediation + Pipeline Integration + Warm-Up Optimization

## Goal
Address all findings from the Tier 3 architectural review of Sprints 23–23.5: fix storage/query defects, wire the NLP Catalyst Pipeline into the running application with scheduled polling, optimize the 27-minute pre-market warm-up via reference data caching, add semantic deduplication and safe publish ordering, and improve runner maintainability. Clears the path for Sprint 24 (Setup Quality Engine + Dynamic Sizer) with zero known issues.

## Scope

### Deliverables

1. **Storage schema & query fixes** — `fetched_at` column persisted and round-tripped; `SELECT COUNT(*)` for total count endpoint; `store_catalysts_batch()` for transactional batch inserts; `since` datetime filter pushed to SQL WHERE clause.

2. **CatalystEvent timezone alignment** — Default factories changed from `datetime.now(UTC)` to `datetime.now(_ET)` to match DEC-276 intelligence layer convention.

3. **SEC EDGAR email validation** — `SECEdgarClient.start()` raises `ValueError` if `user_agent_email` is empty when source is enabled.

4. **FMP canary test** — `FMPReferenceClient.start()` fetches one known symbol (AAPL) and validates expected response keys. Logs WARNING and continues if canary fails (non-blocking).

5. **Post-classification semantic dedup** — Pipeline deduplicates classified catalysts by `(symbol, category, dedup_window_minutes)` before storage. Highest `quality_score` wins.

6. **Batch-then-publish ordering** — Pipeline stores all classified catalysts in a single transaction, then publishes CatalystEvents in a second pass with per-item error handling.

7. **Intelligence startup factory** — `create_intelligence_components()` in `argus/intelligence/startup.py` builds all pipeline components from config, returns structured result or None if disabled.

8. **App lifecycle wiring** — Intelligence components initialized in FastAPI lifespan handler when `catalyst.enabled: true`. AppState fields populated. Graceful shutdown calls `pipeline.stop()`.

9. **Polling loop** — Scheduled `asyncio` task calls `pipeline.run_poll()` at configurable intervals (premarket vs session hours). Symbols sourced from Universe Manager viable_symbols or cached watchlist.

10. **Reference data file cache** — JSON file cache for FMPReferenceClient reference data with per-symbol `cached_at` timestamps, configurable max age, atomic writes, and corrupt-file fallback.

11. **Incremental warm-up** — On startup: load cache → diff against stock list → fetch only missing/stale symbols → merge → save. Reduces ~27-minute warm-up to ~2-5 minutes on subsequent runs.

12. **Runner CLI extraction** — Print helpers and argument parsing moved from `main.py` (2,187 lines) to `cli.py` (~200 lines).

13. **Conformance fallback monitoring** — `conformance_fallback_count` in RunState; WARNING logged if >2 per run.

### Acceptance Criteria

1. Storage schema & query fixes:
   - `fetched_at` column exists in `catalyst_events` table (new DBs); `ALTER TABLE` adds it for existing DBs
   - `get_total_count()` returns integer via `SELECT COUNT(*)`; `get_recent_catalysts` endpoint uses it instead of 10K fetch
   - `store_catalysts_batch()` inserts N catalysts in a single transaction
   - `GET /catalysts/{symbol}?since=<ISO>` filters via SQL WHERE, not Python
   - All existing storage tests pass unchanged

2. CatalystEvent timezone alignment:
   - `CatalystEvent()` with no arguments produces `published_at` and `classified_at` in ET
   - Existing CatalystEvent usage unchanged (explicit timestamps still override defaults)

3. SEC EDGAR email validation:
   - `SECEdgarClient.start()` raises `ValueError` with descriptive message when `user_agent_email == ""`
   - `SECEdgarClient.start()` succeeds when `user_agent_email` is non-empty

4. FMP canary test:
   - `FMPReferenceClient.start()` fetches AAPL profile and checks for keys: `symbol`, `companyName`, `marketCap`, `price`
   - Canary failure logs WARNING but does not raise (non-blocking)
   - Canary skipped when API key is not set

5. Post-classification semantic dedup:
   - Given two catalysts with same `(symbol, category)` within `dedup_window_minutes`, only the one with higher `quality_score` is stored
   - Catalysts with different symbols, different categories, or outside the window are all preserved
   - `dedup_window_minutes` config field exists with default 30

6. Batch-then-publish ordering:
   - All catalysts in a poll cycle are stored before any CatalystEvents are published
   - A failed `event_bus.publish()` does not prevent storage or subsequent publishes
   - Published event count matches stored count in normal operation

7. Intelligence startup factory:
   - `create_intelligence_components(config, ...)` returns populated `IntelligenceComponents` dataclass when `catalyst.enabled: true`
   - Returns `None` when `catalyst.enabled: false`
   - Only instantiates sources whose individual `enabled` flag is true
   - Classifier degrades to fallback-only when `ANTHROPIC_API_KEY` is unset

8. App lifecycle wiring:
   - With `catalyst.enabled: true` in config: `app_state.catalyst_storage` and `app_state.briefing_generator` are not None after startup
   - With `catalyst.enabled: false`: both remain None
   - On shutdown, `CatalystStorage.close()` and source `stop()` are called
   - `SystemConfig` has `catalyst: CatalystConfig` field that loads from `system.yaml`

9. Polling loop:
   - `asyncio` task runs `pipeline.run_poll()` at `polling_interval_premarket_seconds` outside market hours
   - Switches to `polling_interval_session_seconds` during market hours
   - Task is cancelled cleanly during shutdown
   - Symbols come from Universe Manager viable_symbols if available, else cached watchlist

10. Reference data file cache:
    - Cache saved to `data/reference_cache.json` after successful fetch
    - Cache loaded on startup if file exists and is valid JSON
    - Entries older than `cache_max_age_hours` treated as stale
    - Corrupt/missing file triggers full fetch (no crash)
    - Write is atomic (temp file + rename)

11. Incremental warm-up:
    - With valid cache: only stale/missing symbols fetched from FMP
    - Without cache: full fetch (existing behavior)
    - Warm-up time with cache < 5 minutes for typical delta (~100 changed symbols)
    - Merged cache includes both fresh fetches and valid cached entries

12. Runner CLI extraction:
    - `scripts/sprint_runner/cli.py` contains `Colors`, `print_*` helpers, `build_argument_parser()`
    - `main.py` imports from `cli.py`
    - All 188 existing runner tests pass unchanged
    - `main.py` line count reduced by ~200 lines

13. Conformance fallback monitoring:
    - `RunState.conformance_fallback_count` increments each time conformance defaults to CONFORMANT on failure
    - WARNING logged when count exceeds 2 in a single run
    - Field persists across resume (in state JSON)

### Performance Benchmarks

| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Warm-up time (cached) | < 5 minutes | Log timestamps: cache load → universe build complete |
| Warm-up time (no cache) | ~27 minutes (unchanged) | Existing behavior preserved |
| Total count query | < 10ms | No full table fetch; single COUNT(*) |
| Batch store (50 items) | Single transaction | Verify 1 commit per batch, not N |

### Config Changes

| YAML Path | Pydantic Model | Field Name | Default |
|-----------|---------------|------------|---------|
| `catalyst` (top-level section) | `SystemConfig` | `catalyst` | `CatalystConfig()` |
| `catalyst.dedup_window_minutes` | `CatalystConfig` | `dedup_window_minutes` | `30` |

Non-YAML config (dataclass defaults in `FMPReferenceConfig`):

| Field | Default | Description |
|-------|---------|-------------|
| `cache_file` | `"data/reference_cache.json"` | Path for reference data cache |
| `cache_max_age_hours` | `24` | Max age before cache entry is stale |

## Dependencies

- Sprint 23.5 branch merged or working branch checked out
- All 2,396 pytest + 435 Vitest passing
- `ANTHROPIC_API_KEY` environment variable (for AI client; tests can mock)
- `FMP_API_KEY` environment variable (for canary and integration; tests can mock)

## Relevant Decisions

- DEC-170: AI layer strict separation — intelligence layer reads/publishes, never modifies core trading
- DEC-276: ET timestamps for AI/intelligence layer
- DEC-277: Fail-closed on missing reference data
- DEC-300: Config-gated catalyst pipeline (enabled: false default)
- DEC-302: Daily cost ceiling for classification

## Relevant Risks

- RSK-031: FMP endpoint deprecation (canary test provides early warning)
- RSK-046: Claude API classification cost spike (daily ceiling mitigates)
- RSK-047: SEC EDGAR rate limiting (rate limiter mitigates)

## Session Count Estimate

9 sessions estimated. Comprehensive remediation sprint covering 13 deliverables across storage, events, pipeline integration, warm-up optimization, and runner maintenance. All sessions score ≤13 on compaction risk. No visual-review fix budget needed (no frontend changes).
