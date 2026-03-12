# Sprint 23.8: Intelligence Pipeline Live QA Fixes

## Goal
Fix all bugs discovered during the March 12, 2026 live QA session that prevent the NLP Catalyst Pipeline (Sprint 23.5/23.6) from operating correctly end-to-end, plus fix the related Databento lazy warm-up regression. These are the first-ever live runs of the intelligence pipeline — every bug here was invisible to the test suite because it manifested only under real operational conditions (live data, real API responses, actual startup sequencing).

## Scope

### Deliverables
1. **Pipeline resilience:** Polling task has health monitoring via `done_callback`, task reference stored on `app_state`, and `asyncio.wait_for()` safety timeout on the source gather.
2. **Symbol scope fix:** `get_symbols()` returns scanner watchlist (not full 6,342-symbol viable universe), with fallback to viable universe capped at `max_batch_size`.
3. **Cost ceiling enforcement:** UsageTracker wired into classification path, `daily_cost_ceiling_usd` checked before each Claude API call, cost logged per classification cycle.
4. **Classifier safety guards:** `usage_tracker is not None` checks prevent `AttributeError` when AI layer is disabled.
5. **Source-level timeouts:** All three source HTTP clients use explicit `sock_connect` and `sock_read` timeouts in addition to `total`.
6. **FMP news circuit breaker:** After the first 403 response, FMP news source disables itself for the remainder of the poll cycle instead of hammering the endpoint for every symbol.
7. **Databento lazy warm-up fix:** `end` timestamp clamped to `now - 10min` to avoid Databento 422 rejections when historical data hasn't caught up to live.

### Acceptance Criteria
1. **Pipeline resilience:**
   - `done_callback` logs CRITICAL if the polling task crashes
   - Task reference stored on `app_state.intelligence_poll_task`
   - `asyncio.wait_for()` with 120s timeout wraps the gather; timeout logs CRITICAL and continues to next cycle
   - Polling loop survives a simulated source timeout (test)
2. **Symbol scope:**
   - `get_symbols()` returns scanner watchlist when available
   - Falls back to viable universe capped at `max_batch_size` (config value) when watchlist is empty
   - Returns `[]` only when both sources are unavailable
   - Log line shows symbol count and first 5 symbols each cycle
3. **Cost ceiling:**
   - Each Claude classification call records cost via UsageTracker
   - Before each call, daily cumulative cost is checked against `daily_cost_ceiling_usd`
   - When ceiling is reached, remaining items fall through to rule-based classifier
   - Log line at INFO when ceiling is reached, including cost and item count
4. **Classifier guards:**
   - `usage_tracker is None` does not crash; classification proceeds without cost tracking
   - Test covers classifier instantiation with `usage_tracker=None`
5. **Source timeouts:**
   - All three sources: `ClientTimeout(total=30, sock_connect=10, sock_read=20)`
   - Test validates timeout configuration on session creation
6. **FMP circuit breaker:**
   - First 403 logs ERROR and sets a flag
   - Subsequent symbols in the same cycle are skipped with a single WARNING log
   - Flag resets at start of next cycle
   - Test simulates 403 and verifies skip behavior
7. **Databento warm-up:**
   - `end` parameter clamped to `now - 10min` (600s buffer)
   - Pre-market boot path (skip warm-up) is unaffected
   - Test verifies clamping logic

### Performance Benchmarks
| Metric | Target | Measurement Method |
|--------|--------|--------------------|
| Poll cycle for 15 symbols | < 120s | Log timestamp delta (fetch start → store complete) |
| Classification throughput | 336 items in < 5 min | Log timestamp delta |

### Config Changes
No new config fields. Existing `catalyst.max_batch_size` and `catalyst.daily_cost_ceiling_usd` are already defined in the Pydantic model and YAML — this sprint wires them into code paths that weren't using them.

**Pre-existing config issue:** `system_live.yaml` was modified during this QA session (catalyst section added, fmp_news disabled). A config alignment test may fail until the test fixture is updated to match. This is tracked as a known pre-existing failure — Session 1 should update the test fixture as part of its pre-flight.

## Dependencies
- Sprint 23.5 (NLP Catalyst Pipeline) — provides the pipeline, sources, classifier, storage
- Sprint 23.6 (Pipeline Integration) — provides startup factory, polling loop, catalyst.db
- Sprint 23.7 (Startup Scaling Fixes) — provides lazy warm-up, cache saves
- Live QA session March 12 — provides the bug evidence and live debug patches to revert/replace

## Relevant Decisions
- DEC-300 (config-gated feature): Pipeline must remain config-gated; fixes must not change default-disabled behavior
- DEC-301 (rule-based fallback classifier): Fallback path must work when Claude API is unavailable or budget exhausted
- DEC-302 (headline hash dedup): Dedup stage must remain unchanged
- DEC-303 (daily cost ceiling): $5/day ceiling — this sprint enforces what DEC-303 specified but wasn't wired
- DEC-308 (deferred initialization): Startup factory pattern must be preserved
- DEC-311 (semantic dedup): Semantic dedup stage must remain unchanged
- DEC-312 (batch-then-publish): Ordering guarantee must be preserved
- DEC-315 (polling loop): Market-hours-aware interval logic must be preserved

## Relevant Risks
- RSK-022 (IBKR Gateway nightly resets): Not directly related but system must remain stable through restarts during which these fixes are active

## Session Count Estimate
3 sessions estimated. Each session addresses a distinct concern domain (pipeline infrastructure, cost/classification, source networking + data service). No frontend changes, so no visual-review contingency session needed.

---

# Sprint 23.8: What This Sprint Does NOT Do

## Out of Scope
1. **Pipeline architecture refactor to firehose model:** The current per-symbol polling design is architecturally wrong for scale, but fixing it requires a design phase. Deferred to Sprint 24 planning (DEC-327).
2. **Frontend catalyst 503 short-circuit:** Deferred to Sprint 23.9 (DEF-041). Frontend change, not backend.
3. **`/debrief/briefings` 503:** Deferred to Sprint 23.9 (DEF-043). DailySummaryGenerator endpoint — separate from intelligence briefings. Needs investigation.
4. **SPY regime detection after market open:** The regime check only runs during pre-market routine. Making it re-evaluate intra-day is a feature, not a bug fix (DEF-044).
5. **Frontend polling frequency:** Dashboard polling every 5-10 seconds is aggressive but not harmful. Optimization is a UX sprint item.

## Edge Cases to Reject
1. **Watchlist empty AND viable universe empty:** Return `[]`, log WARNING, skip cycle. Do not crash.
2. **All sources fail in a single cycle:** Log CRITICAL with per-source error summary, continue to next cycle. Do not halt the polling loop.
3. **Cost ceiling reached mid-batch:** Switch remaining items to rule-based fallback. Do not discard unclassified items.
4. **Databento historical API returns different lag than 10 minutes:** Use a fixed 600s buffer. Do not dynamically probe Databento for its lag. If 600s is insufficient, the warm-up logs a WARNING and skips that symbol (existing behavior).

## Scope Boundaries
- Do NOT modify: Trading engine (`core/`), strategies (`strategies/`), order execution (`execution/`), frontend (`ui/`), AI Copilot layer (`ai/` except classifier.py), backtesting (`backtest/`)
- Do NOT optimize: Classification throughput, dedup performance, polling interval tuning
- Do NOT refactor: Pipeline architecture, source abstraction layer, storage schema
- Do NOT add: New catalyst sources, new classification categories, new API endpoints

## Interaction Boundaries
- This sprint does NOT change the behavior of: REST API endpoints, WebSocket streaming, Event Bus publishing contract, `catalyst.db` schema, config schema (Pydantic models)
- This sprint does NOT affect: Dashboard, Trade Log, Performance, Orchestrator, Pattern Library, The Debrief, System pages, AI Copilot chat, trading execution

## Deferred to Future Sprints
| Item | Target Sprint | Reference |
|------|--------------|-----------|
| Firehose pipeline architecture | Sprint 24 design | DEC-327 |
| Frontend catalyst endpoint short-circuit | Sprint 23.9 (fast-follow) | DEF-041 |
| `/debrief/briefings` 503 fix | Sprint 23.9 (fast-follow) | DEF-043 |
| SPY intra-day regime re-evaluation | Regime-aware strategy behavior or paper trading evidence | DEF-044 |
