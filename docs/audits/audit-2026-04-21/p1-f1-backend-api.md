# Audit: Backend API
**Session:** P1-F1
**Date:** 2026-04-21
**Scope:** `argus/api/` — 42 files, 14,192 lines. `dev_state.py` (2,338L) + 29 route files + 4 websocket files + infrastructure (auth, dependencies, server, serializers, __main__, setup_password).
**Files examined:** 7 deep-read / 31 skimmed (all 42 files inspected)

## Pre-Read Note / Audit-Prompt Corrections
- Audit prompt said "30 routes" — actual count is **29** route files in [argus/api/routes/](argus/api/routes/). (`account, ai, arena, auth, briefings, config, controls, counterfactual, dashboard, debrief_search, documents, experiments, health, historical, intelligence, journal, learning, market, observatory, orchestrator, performance, positions, quality, session, strategies, trades, universe, vix, watchlist`.)
- Audit prompt said `serializers.py` is "919 lines approx" — actual is **84 lines** ([serializers.py](argus/api/serializers.py)). It handles only WS event serialization; route responses use Pydantic models directly.
- Audit prompt said "Arena polling endpoint is intentionally no-auth" — **incorrect**. [arena.py:87](argus/api/routes/arena.py#L87) and [arena.py:169](argus/api/routes/arena.py#L169) both use `_auth: dict = Depends(require_auth)`. The only intentionally no-auth endpoints are `/market/status` (line 32) and `/auth/login` + `/auth/refresh`.

---

## dev_state.py Verdict — STALE LIVE CODE (keep, but decay is bad)

### Import graph (repo-wide)
```
argus/api/__main__.py:61            → from argus.api.dev_state import create_dev_state
tests/api/test_dev_state_dashboard.py:19
tests/api/test_dev_state_patterns.py:14
docs/sprints/sprint-14/SPRINT_14_SPEC.md:419     (doc only)
docs/sprints/sprint-14/sprint_14_revised_prompts.md:911  (doc only)
```
`argus/main.py` does NOT import dev_state. The single live import path is `python -m argus.api --dev` (frontend dev mode with mock data, password: `argus`).

**Verdict: LIVE.** Code runs during every `--dev` invocation. Two pytest files exercise it. **Do not delete** — but it has rotted significantly. See CRITICAL #2.

---

## 29-Route Consistency Summary

| Aspect | Status | Notes |
|--------|--------|-------|
| **Auth coverage** | ✅ consistent | 97 `_auth` dependencies across 29 files. 3 intentional no-auth: `/market/status`, `/auth/login`, `/auth/refresh`. All others authed. |
| **`HTTPBearer(auto_error=False)` pattern** | ✅ consistent | Single `security` instance in [auth.py:34](argus/api/auth.py#L34); all routes use `Depends(require_auth)`. DEC-351 compliance: 100%. |
| **JWT algorithm** | ✅ consistent | `HS256` everywhere. |
| **`response_model=` coverage** | ⚠️ **~78% (~77 of 99 endpoints)** | Newer routes (learning×8, experiments×5, historical×4, counterfactual×1, vix×2, /ai/context×1, /strategies/decisions×1, /auth/me×1) return untyped `dict`. See MEDIUM #5. |
| **Timestamp TZ** | ⚠️ drift | 60+ routes use `datetime.now(UTC).isoformat()`. [counterfactual.py:94,124](argus/api/routes/counterfactual.py#L94) uses `datetime.now(_ET).isoformat()`. See MEDIUM #6. |
| **Error response shape** | ✅ consistent | All use `raise HTTPException(status_code=..., detail=...)`. |
| **Auth-dependency naming** | ⚠️ 1 outlier | 96 routes use `_auth: dict = Depends(require_auth)`; [strategies.py:389](argus/api/routes/strategies.py#L389) uses `_user:`. LOW #12. |
| **Request body typing** | ⚠️ 1 outlier | [historical.py:201](argus/api/routes/historical.py#L201) uses `body: dict = Body(...)`; all other POSTs use Pydantic request models. MEDIUM #9. |
| **Route-function naming** | ✅ consistent | Verb form (`get_...`, `list_...`, `post_...`) uniformly. |
| **Path naming** | ✅ mostly consistent | Plural nouns (`/positions`, `/trades`, `/experiments`); `/orchestrator` is intentionally singular (single component). |
| **Query param naming** | ✅ consistent | `snake_case` everywhere (`start_date`, `date_from`, `strategy_id`). One alias: [learning.py:222](argus/api/routes/learning.py#L222) `status_filter: str | None = Query(default=None, alias="status")` — alias required to avoid shadowing `status` module. |

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 1 | [argus/api/routes/market.py:151-293](argus/api/routes/market.py#L151-L293) | **RESOLVED FIX-11-backend-api** — **`GET /market/{symbol}/bars` silently returns synthetic bars when real data unavailable.** 3-tier fallback: IntradayCandleStore → DataService → `_generate_synthetic_bars()` at line 287. Response shape (`BarsResponse`) has NO flag indicating synthetic data. Frontend charts render fake prices indistinguishably from real ones. | In production (Databento flake or pre-market gap with no candle store): user sees plausible but fabricated OHLCV on the dashboard chart. No telemetry logs this event at WARNING+. | Add `source: Literal["live", "historical", "synthetic"]` field to `BarsResponse`. Log WARNING when falling through to synthetic. Frontend must gate display behind real-data source. | weekend-only |
| 2 | [argus/api/dev_state.py:2296-2328](argus/api/dev_state.py#L2296-L2328) + [dev_state.py:52](argus/api/dev_state.py#L52) | **RESOLVED FIX-11-backend-api** (Option B — retired; DEF-169) — **`dev_state.py` badly outdated — only 7 of 15 live+shadow strategies seeded; V1 regime, no V2; no HQS/CFT/Experiments/VIX/Learning services.** Mock strategies: ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, R2G (marked `is_active=False, pipeline_stage="exploration"` despite being live), Bull Flag (same), Flat-Top (same). Missing: HOD Break, Gap-and-Go, Dip-and-Rip, PMH, Micro Pullback, VWAP Bounce, Narrow Range, ABCD. [Line 52](argus/api/dev_state.py#L52) imports legacy `MarketRegime, RegimeIndicators` from V1; RegimeVector / RegimeClassifierV2 never referenced. `create_dev_state()` populates neither `counterfactual_store`, `vix_data_service`, `experiment_store`, `historical_query_service`, nor `learning_service` on AppState. | Frontend developers using `python -m argus.api --dev` see a snapshot from ~Sprint 27 of what the system is. Any new-feature UI work (Experiments page, VIX card, Learning Loop proposals) can't be exercised without a live backend, forcing devs to boot the full engine. Mock trades seeded for strategies that still exist use correct `strategy_id`s, but any page filtered by active-strategy set shows only 3 "active" strategies. | Decide: (a) rebuild `dev_state.py` to current state (add missing strategies, populate all service stubs, upgrade regime V1→V2); or (b) retire `--dev` mode and require full-engine boot for UI dev (delete `__main__.py --dev` branch, `dev_state.py`, 2 test files). Option (b) is cleaner given the cost of keeping (a) in sync. If kept, add a CI check that enumerates registered strategies and fails if dev_state is missing any. | weekend-only |

---

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 3 | [argus/api/server.py:90](argus/api/server.py#L90), [server.py:129](argus/api/server.py#L129), [server.py:233](argus/api/server.py#L233) | **RESOLVED FIX-11-backend-api** — **`app_state.trade_logger._db` private attribute access (×3).** DEC-034 says TradeLogger is the sole persistence interface. Reaching into `_db` to hand the `DatabaseManager` to ConversationManager / DebriefService / quality components bypasses that abstraction and couples API startup to TradeLogger internals. | Tight coupling; any TradeLogger refactor that renames/removes the private field silently breaks three startup paths. | Add a `db_manager` property on TradeLogger (or pass the DatabaseManager in via AppState explicitly at construction in `main.py` instead of reaching in via server.py). | weekend-only |
| 4 | [argus/api/server.py:326](argus/api/server.py#L326), [server.py:333](argus/api/server.py#L333), [server.py:559](argus/api/server.py#L559), [routes/vix.py:51-69](argus/api/routes/vix.py#L51-L69) | **RESOLVED FIX-11-backend-api** (API-side of DEF-091 — see DEF-091 update in CLAUDE.md). **Orchestrator / RegimeClassifierV2 / VIXDataService private-attribute mutations and reads** — `orchestrator._vix_data_service`, `regime_v2._vix_data_service`, `vix_data_service._update_task`, and vix.py reaches `_regime_classifier_v2._vol_phase_calc / _vol_momentum_calc / _term_structure_calc / _vrp_calc`. Same pattern as DEF-091. | Any rename of these private fields breaks API startup AND `/vix/current`. The VIX wiring in particular happens lazily after orchestrator init, so the side-effect is non-obvious. | Replace each with a public setter (e.g., `orchestrator.attach_vix_service(service)`) or add read-only accessors as DEF-091 recommends. Add to DEF-091's scope. | deferred-to-defs |
| 5 | [argus/api/routes/learning.py](argus/api/routes/learning.py) (8 endpoints), [experiments.py](argus/api/routes/experiments.py) (5), [historical.py](argus/api/routes/historical.py) (4), [counterfactual.py:60](argus/api/routes/counterfactual.py#L60), [vix.py](argus/api/routes/vix.py) (2), [ai.py:521](argus/api/routes/ai.py#L521), [strategies.py:382](argus/api/routes/strategies.py#L382), [auth.py:132](argus/api/routes/auth.py#L132) | ~~**~22 of ~99 endpoints lack `response_model=`** and return bare `dict`. All newer routes (Sprint 27.7+) skip response_model; older routes (Sprint 14-25) use it consistently.~~ **RESOLVED FIX-07-intelligence-catalyst-quality** (21 endpoints wired across 7 files; auth.py already compliant — the `:132` reference was stale) | (1) OpenAPI docs show untyped responses — harder for frontend to generate types. (2) No server-side response validation. (3) Breaks the pattern new contributors see; encourages drift. | For each bare-`dict` endpoint, define a matching `*Response` Pydantic model in the same file and wire `response_model=...`. Many already build inline TypedDicts-in-spirit — extraction is mechanical. | weekend-only |
| 6 | [argus/api/routes/counterfactual.py:94](argus/api/routes/counterfactual.py#L94), [counterfactual.py:124](argus/api/routes/counterfactual.py#L124) | ~~**`/counterfactual/positions` returns `timestamp` in ET**; every other route file returns UTC (60+ occurrences audited). `/counterfactual/accuracy` correctly uses UTC-derived ISO strings. Drift is within a single file.~~ **RESOLVED FIX-07-intelligence-catalyst-quality** (regression test `test_counterfactual_positions_timestamp_utc` pins UTC) | Frontend code that uniformly parses `timestamp` as UTC will mis-display by 4-5 hours. Probably already accounted for client-side, but the inconsistency is a foot-gun. | Change the two `datetime.now(_ET).isoformat()` calls to `datetime.now(UTC).isoformat()`. | weekend-only |
| 7 | [argus/api/routes/counterfactual.py:201-213](argus/api/routes/counterfactual.py#L201-L213) | ~~**`assert isinstance(b, FilterAccuracyBreakdown)` in production deserialization.** Same anti-pattern flagged in DEF-106 (S6cf-1 review), now recurring. Python `-O` optimization strips asserts — the isinstance check disappears.~~ **RESOLVED FIX-07-intelligence-catalyst-quality** (batch closure of DEF-106 — 8 sites in `intelligence/learning/models.py` + this 1 site) | Production-disabled guard; future `-O` runs silently accept any object into `BreakdownResponse(...)`. | Replace with `if not isinstance(b, FilterAccuracyBreakdown): raise TypeError(...)`. Extend DEF-106 scope or close-out with a batch fix. | safe-during-trading |
| 8 | [docs/architecture.md:1717-1781](docs/architecture.md#L1717-L1781) vs [argus/api/routes/](argus/api/routes/) | **RESOLVED FIX-11-backend-api** (banner added in place; DEF-168 logs regeneration backlog) — **Architecture.md API catalog is substantially drifted (≥10 mismatches).** (a) Line 1717-1719: `/api/v1/catalysts*` — code mounts them under `/api/v1/intelligence/catalysts/*`; `/catalysts/refresh` does not exist. (b) Line 1720-1722: "intelligence briefings" paths wrong; code has `/debrief/briefings` and `/intelligence/premarket/briefing*`. (c) Line 1743-1745: AI briefing/report/analyze POSTs do not exist in [ai.py](argus/api/routes/ai.py). (d) Line 1770: `GET /api/v1/performance/replay/{id}` — code has `/trades/{id}/replay`. (e) Line 1774: market/bars described "Synthetic OHLCV for dev mode" — actually serves real data first (see CRITICAL #1). (f) Line 1777: "/arena/positions ... no JWT required for polling" — code DOES require JWT. (g) Entire Experiments section (7 endpoints), Watchlist, Controls (5 endpoints), Trades stats/batch/export/csv, `/historical/symbols,coverage,bars,validate-coverage` — undocumented. | Frontend devs and operators consult wrong docs; AI assistants read stale contract; onboarding friction. | Flag for **P1-H1a** (primary context compression session). Architecture.md needs a mechanically-regenerated endpoint catalog (introspect FastAPI routes). | deferred-to-defs |
| 9 | [argus/api/routes/historical.py:201](argus/api/routes/historical.py#L201) | **RESOLVED FIX-11-backend-api** — **`POST /historical/validate-coverage` accepts `body: dict = Body(...)` — untyped request body.** No Pydantic validation. | Invalid payloads surface as runtime `KeyError` instead of a 422 validation error. Breaks the pattern every other POST in the codebase follows. | Define `ValidateCoverageRequest` with `symbols: list[str]`, `min_bars: int | None`, etc. Wire as `body: ValidateCoverageRequest`. | weekend-only |
| 10 | [argus/api/routes/trades.py:614-623](argus/api/routes/trades.py#L614-L623) | **RESOLVED FIX-11-backend-api** (Option a — returns 501 until DEF-029 lands) — **`GET /trades/{trade_id}/replay` is a STUB in non-dev mode** — returns `bars=[]`, `entry_bar_index=0`, `exit_bar_index=None`, `vwap=None`. Dev mode generates synthetic bars. Architecture.md documents a different path (see Finding #8) and implies it works. Related to DEF-029 (persist candle data). | Operator clicking "Replay" on Performance page in production sees empty chart; error not obvious. | Either (a) remove the endpoint for now and return 501 Not Implemented until DEF-029 lands, or (b) wire it to `IntradayCandleStore` for same-session replay when the store has bars. | weekend-only |
| 11 | [argus/api/dev_state.py:2336](argus/api/dev_state.py#L2336) → [trades.py:612](argus/api/routes/trades.py#L612) | **RESOLVED FIX-11-backend-api** (subsumed by dev-mode retirement — trades.py is_dev_mode branch removed, DEF-169) — **`app_state._mock_watchlist` monkey-patched onto AppState; `trades.py:612` uses `hasattr(state, "_mock_watchlist")` as a dev-mode sentinel.** The dataclass has no `_mock_watchlist` field — `# type: ignore[attr-defined]` at the assignment. The route file infers dev-mode by attribute existence. | Fragile coupling. Any future AppState cleanup ("prune unused fields") might remove the monkey-patch. Non-obvious test-data flow. | Add an explicit `is_dev_mode: bool = False` field on AppState, set True in `create_dev_state()`. Replace hasattr check. | safe-during-trading |

---

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 12 | [argus/api/routes/strategies.py:389](argus/api/routes/strategies.py#L389) | **RESOLVED FIX-11-backend-api** — **Auth parameter named `_user` — every other route uses `_auth`.** Single outlier across 96 dependencies. | None functional. Cosmetic-but-trips-greps. | Rename `_user` → `_auth`. | safe-during-trading |
| 13 | [argus/api/websocket/live.py:354-356](argus/api/websocket/live.py#L354-L356), [arena_ws.py:291-299](argus/api/websocket/arena_ws.py#L291-L299) | **RESOLVED FIX-11-backend-api** — **QueueFull drops messages silently to the client.** Both WS dispatch paths: `put_nowait` in try/except, log WARNING, then discard. Slow clients silently fall behind. | Client chart drifts from server state with no signal to reconnect/refresh. | Emit a `{"type": "state_desync"}` message before dropping, or close the socket with a specific code (e.g., 4003) forcing the client to reconnect with a fresh snapshot. | weekend-only |
| 14 | [argus/api/websocket/live.py:395](argus/api/websocket/live.py#L395) | **RESOLVED FIX-11-backend-api** — **`hasattr(self._broker, "get_account")` defensive duck-typing.** `Broker` ABC in [execution/broker.py](argus/execution/broker.py) should declare `get_account()`; if it does, the hasattr is dead code. If it doesn't, account polling is type-unsafe. | Minor fragility. | Confirm `get_account()` is on the Broker ABC; remove the hasattr. | safe-during-trading |
| 15 | [argus/api/server.py:48-596](argus/api/server.py#L48-L596) | **RESOLVED FIX-11-backend-api** — **`lifespan()` handler is ~550 lines of nested `try/except` covering 9 initialization phases.** (AI services, DebriefService, Intelligence Pipeline, Quality Engine, EvaluationEventStore, ObservatoryService, VIXDataService, Learning Loop, Experiment Pipeline, Historical Query Service.) Each phase has similar try/except + enabled-check pattern. No single responsibility, tough to reason about ordering (VIX wires into orchestrator post-init, learning registers auto-trigger post-init). | Hard to audit initialization-order invariants; adding a new optional service requires replicating the 30-line block. | Extract each phase to a separate `async def _init_<name>(app_state)` helper; lifespan becomes a list of coroutine calls wrapped in an ordered execution loop with per-phase error reporting. | weekend-only |
| 16 | [argus/api/websocket/observatory_ws.py:133-143](argus/api/websocket/observatory_ws.py#L133-L143) | **RESOLVED FIX-11-backend-api** — **When Observatory query exceeds push interval, tracked state (`previous_tiers`, `previous_eval_count`) is advanced without emitting a push.** Prevents diff corruption on the next interval, but means tier transitions during the slow interval are never signalled to the client. | Slow-query windows silently drop transition events. | Emit a `type: "interval_skipped"` marker instead of updating state; clients can re-fetch on demand. | weekend-only |
| 17 | [argus/api/server.py:606-616](argus/api/server.py#L606-L616) | **RESOLVED FIX-11-backend-api** — **CORS default is `["http://localhost:5173"]`** — Vite dev. Tauri desktop and PWA mobile (per project knowledge) use different origins. Configurable via `api.cors_origins`, but the default is dev-only. | Minor. Live deployments override. | Document this in the ApiConfig docstring. No code change. | safe-during-trading |
| 18 | [argus/api/routes/market.py:287](argus/api/routes/market.py#L287) | **RESOLVED FIX-11-backend-api** (synthetic path retains the 390 cap; source=synthetic flag signals asymmetry — see finding #1) — **`_generate_synthetic_bars(limit=min(limit, 390))`** caps synthetic at 390 but `limit` param supports up to 1000 ([line 155](argus/api/routes/market.py#L155)). Real-data paths return up to `limit`; synthetic path silently truncates. | Asymmetric behavior between real/synthetic paths. Related to CRITICAL #1. | Either lift the 390 cap or enforce it as the hard parameter max. | safe-during-trading |
| 19 | [argus/api/routes/__init__.py:9-36](argus/api/routes/__init__.py#L9-L36) | **RESOLVED FIX-11-backend-api** — **Route-import order is mostly alphabetical but not strictly** — `historical` appears before `ai` at lines 11-12 (should be `ai < arena < historical`). Other positions: `intelligence` (line 22) between `health` (21) and `experiments` (23) — `experiments` alphabetizes before both. | None functional. | Sort imports strictly alphabetically. | safe-during-trading |
| 20 | [argus/api/setup_password.py:85](argus/api/setup_password.py#L85) | **RESOLVED FIX-11-backend-api** — **Setup CLI prints a generated JWT secret to stdout.** If captured by shell history, screen-sharing, or terminal multiplexer logs, the secret leaks. | User-operator foot-gun. | Write secret to a `.env.example` file with 0600 permissions, or prompt the user to paste it into `.env` without printing. | safe-during-trading |

---

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| 21 | [argus/api/auth.py:105](argus/api/auth.py#L105) | **RESOLVED FIX-11-backend-api** — `create_access_token(jwt_secret, expires_hours: int = 24)` — docstring says "Default 24" but every call site passes `api_config.jwt_expiry_hours`. The default is unreachable. | None. | Drop the default, make `expires_hours` required. | safe-during-trading |
| 22 | [argus/api/dev_state.py](argus/api/dev_state.py) | **RESOLVED FIX-11-backend-api** (dev_state.py deleted — finding moot) — File docstring says "Real ORB strategy" (line 1887) but dev_state actually seeds a MockStrategy dataclass, not the production OrbBreakoutStrategy. | None. | Update docstring. | safe-during-trading |
| 23 | [argus/api/websocket/live.py:455-462](argus/api/websocket/live.py#L455-L462) | **RESOLVED FIX-11-backend-api** — `from jose import jwt` is imported inside `websocket_endpoint()` despite `from jose import JWTError` already at module top (line 18). | None. | Lift `jwt` import to module level. | safe-during-trading |
| 24 | [argus/api/routes/auth.py:132-149](argus/api/routes/auth.py#L132-L149) | **RESOLVED FIX-11-backend-api** — `/auth/me` lacks `response_model=` (tiny helper returning `{"user": str, "timestamp": str}`) — easy to add for OpenAPI coverage. | None (functional). | Define `UserInfoResponse` Pydantic model. Part of MEDIUM #5's batch. | safe-during-trading |
| 25 | [argus/api/routes/__init__.py](argus/api/routes/__init__.py) | **RESOLVED FIX-11-backend-api** — `observatory_router` is imported separately in `server.py:630` but NOT aggregated in `routes/__init__.py`. Conditional mount is intentional, but non-obvious to readers scanning the routes index. | None. | Add a comment in `routes/__init__.py` noting observatory is conditionally mounted in `server.py` when `observatory.enabled`. | safe-during-trading |

---

## Positive Observations

- **Auth layer is excellent** — [auth.py](argus/api/auth.py) (195 lines) is small, tightly scoped, uses `HTTPBearer(auto_error=False)` + explicit 401 (DEC-351), bcrypt for passwords, env-sourced JWT secret. No JWT algorithm drift across 29 route files. This is the tidiest module in the API layer.
- **Route aggregation in [routes/__init__.py](argus/api/routes/__init__.py)** is centralized, declarative, and easy to scan — 28 mounts in a flat list.
- **`HTTPBearer(auto_error=False)` compliance is 100%.** No route defines its own security scheme; all 97 `Depends(require_auth)` references share the same singleton — zero drift from DEC-351.
- **WebSocket lifecycle pattern is consistent** across [arena_ws.py](argus/api/websocket/arena_ws.py) and [observatory_ws.py](argus/api/websocket/observatory_ws.py): accept → JWT handshake (30s timeout) → close-with-4001 on failure → background tasks (sender, stats/push loop) → `try/finally` cleanup with explicit `unsubscribe` BEFORE task cancellation (prevents queue-after-cleanup races — [arena_ws.py:403-408](argus/api/websocket/arena_ws.py#L403-L408)).
- **Pydantic response models (where used)** produce clean OpenAPI output. Dashboard, Performance, Trades, Strategies, Controls, Account, Arena, Briefings, Documents, Journal, Market all use consistent `*Response` naming and `count`/`timestamp`/`total_count`/`limit`/`offset` pagination fields per Sprint 14 contract.
- **Port availability check** ([server.py:669-691](argus/api/server.py#L669-L691)) + `PortInUseError` custom exception + disabled uvicorn signal handlers ([server.py:728](argus/api/server.py#L728)) is a defensible hardening pattern (DEC-318). Nice.
- **AppState dataclass** ([dependencies.py:56-130](argus/api/dependencies.py#L56-L130)) uses `TYPE_CHECKING` imports to avoid circular imports; `get_app_state(request)` is the single-source dependency injection entry. All 34 declared fields have explicit `Optional`/default handling. Tidy.
- **Tick throttling and position-filtered broadcast** in WebSocketBridge ([live.py:284-325](argus/api/websocket/live.py#L284-L325)) is efficient: only symbols with open positions forward; per-symbol 1Hz throttle. Mirrored (with a bypass path for Arena's `arena_tick_price`) in the Arena WS.
- **Per-connection state in Arena WS** (tracked_symbols, position_cache, unrealized_pnl_map, r_multiple_map, trail_stop_cache, ring buffers) is initialized from current broker state at connect time ([arena_ws.py:282-289](argus/api/websocket/arena_ws.py#L282-L289)), so mid-session clients receive a correct snapshot without a separate REST round-trip.
- **HistoricalQueryService is initialized in a background `asyncio.to_thread` task** ([server.py:479-505](argus/api/server.py#L479-L505)), avoiding the minutes-long blocking Parquet scan that would otherwise stall the lifespan handler (Sprint 31.8 S1 fix, DEF-155 resolved).
- **`DELETE` endpoints consistently use `status_code=204 + response_model=None`** across briefings/documents/journal — one small pattern done correctly everywhere.
- **Serializers.py is properly scoped** — 84 lines doing one thing (dataclass → JSON for WS events). Doesn't leak into REST response construction.

---

## Statistics
- Files deep-read: **7** (`dev_state.py`, `server.py`, `auth.py`, `dependencies.py`, `routes/__init__.py`, `websocket/live.py`, `websocket/arena_ws.py`)
- Files skimmed: **31** (all 29 route files + observatory_ws + ai_chat + serializers + __main__ + setup_password)
- Total findings: **25** (2 critical, 9 medium, 9 low, 5 cosmetic)
- Safety distribution: **9 safe-during-trading / 12 weekend-only / 0 read-only-no-fix-needed / 4 deferred-to-defs**
- Estimated Phase 3 fix effort: **4-5 sessions**
  - 1 session: `dev_state.py` decision (rebuild vs retire) — blocks UI dev work
  - 1 session: `response_model` uplift (~22 endpoints; mechanical)
  - 1 session: Private-attribute accessor cleanup (server.py × 6, vix.py × 4) — extend DEF-091
  - 1 session: market/bars synthetic signalling + trade replay stub hardening (CRITICAL #1 + MEDIUM #10)
  - 1 session (optional): lifespan extraction (LOW #15)

---

## Appendix — New DEF candidates

| Candidate | Source | Suggested scope |
|-----------|--------|-----------------|
| DEF-NEW-A | CRITICAL #1 | Mark market/bars synthetic-fallback responses explicitly; add WARNING log + frontend gate. |
| DEF-NEW-B | CRITICAL #2 | Decide dev_state.py lifecycle: rebuild to current system state OR retire `--dev` mode entirely. |
| DEF-NEW-C | MEDIUM #5 | Systematic `response_model=` coverage for ~22 Sprint 27.7+ endpoints. |
| DEF-NEW-D | MEDIUM #10 + DEF-029 | Production implementation of `/trades/{id}/replay` (requires DEF-029 candle persistence). |
| DEF-NEW-E | MEDIUM #8 | Generate architecture.md endpoint catalog from FastAPI introspection (feeds P1-H1a). |
| DEF-091 extension | MEDIUM #4 | Add VIX/Orchestrator/RegimeV2/VIXUpdateTask accessors to DEF-091's scope. |
| DEF-106 extension | MEDIUM #7 | Add `counterfactual.py:204` assert to DEF-106's replacement batch. |
