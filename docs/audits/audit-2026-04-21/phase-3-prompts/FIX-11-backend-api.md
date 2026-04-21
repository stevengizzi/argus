# Fix Session FIX-11-backend-api: argus/api — REST routes, WebSocket, auth

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 23
**Files touched:** `argus/api/auth.py`, `argus/api/dev_state.py`, `argus/api/routes/__init__.py`, `argus/api/routes/auth.py`, `argus/api/routes/historical.py`, `argus/api/routes/market.py`, `argus/api/routes/strategies.py`, `argus/api/routes/trades.py`, `argus/api/server.py`, `argus/api/setup_password.py`, `argus/api/websocket/live.py`, `argus/api/websocket/observatory_ws.py`, `argus/ui/src/features/dashboard/VitalsStrip.test.ts`, `docs/architecture.md`
**Safety tag:** `weekend-only`
**Theme:** REST route, WebSocket endpoint, and auth findings across the FastAPI Command Center backend.

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
marker (`audit(FIX-11): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/api/server.py`: 4 findings
- `argus/api/dev_state.py`: 3 findings
- `argus/api/websocket/live.py`: 3 findings
- `argus/api/routes/__init__.py`: 2 findings
- `argus/api/routes/market.py`: 2 findings
- `argus/api/auth.py`: 1 finding
- `argus/api/routes/auth.py`: 1 finding
- `argus/api/routes/historical.py`: 1 finding
- `argus/api/routes/strategies.py`: 1 finding
- `argus/api/routes/trades.py`: 1 finding
- `argus/api/setup_password.py`: 1 finding
- `argus/api/websocket/observatory_ws.py`: 1 finding
- `argus/ui/src/features/dashboard/VitalsStrip.test.ts`: 1 finding
- `docs/architecture.md`: 1 finding

## Findings to Fix

### Finding 1: `P1-F1-3` [MEDIUM]

**File/line:** [argus/api/server.py:90](argus/api/server.py#L90), [server.py:129](argus/api/server.py#L129), [server.py:233](argus/api/server.py#L233)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`app_state.trade_logger._db` private attribute access (×3).** DEC-034 says TradeLogger is the sole persistence interface. Reaching into `_db` to hand the `DatabaseManager` to ConversationManager / DebriefService / quality components bypasses that abstraction and couples API startup to TradeLogger internals.

**Impact:**

> Tight coupling; any TradeLogger refactor that renames/removes the private field silently breaks three startup paths.

**Suggested fix:**

> Add a `db_manager` property on TradeLogger (or pass the DatabaseManager in via AppState explicitly at construction in `main.py` instead of reaching in via server.py).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 2: `P1-F1-4` [MEDIUM]

**File/line:** [argus/api/server.py:326](argus/api/server.py#L326), [server.py:333](argus/api/server.py#L333), [server.py:559](argus/api/server.py#L559), [routes/vix.py:51-69](argus/api/routes/vix.py#L51-L69)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **Orchestrator / RegimeClassifierV2 / VIXDataService private-attribute mutations and reads** — `orchestrator._vix_data_service`, `regime_v2._vix_data_service`, `vix_data_service._update_task`, and vix.py reaches `_regime_classifier_v2._vol_phase_calc / _vol_momentum_calc / _term_structure_calc / _vrp_calc`. Same pattern as DEF-091.

**Impact:**

> Any rename of these private fields breaks API startup AND `/vix/current`. The VIX wiring in particular happens lazily after orchestrator init, so the side-effect is non-obvious.

**Suggested fix:**

> Replace each with a public setter (e.g., `orchestrator.attach_vix_service(service)`) or add read-only accessors as DEF-091 recommends. Add to DEF-091's scope.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 3: `P1-F1-15` [LOW]

**File/line:** [argus/api/server.py:48-596](argus/api/server.py#L48-L596)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`lifespan()` handler is ~550 lines of nested `try/except` covering 9 initialization phases.** (AI services, DebriefService, Intelligence Pipeline, Quality Engine, EvaluationEventStore, ObservatoryService, VIXDataService, Learning Loop, Experiment Pipeline, Historical Query Service.) Each phase has similar try/except + enabled-check pattern. No single responsibility, tough to reason about ordering (VIX wires into orchestrator post-init, learning registers auto-trigger post-init).

**Impact:**

> Hard to audit initialization-order invariants; adding a new optional service requires replicating the 30-line block.

**Suggested fix:**

> Extract each phase to a separate `async def _init_<name>(app_state)` helper; lifespan becomes a list of coroutine calls wrapped in an ordered execution loop with per-phase error reporting.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 4: `P1-F1-17` [LOW]

**File/line:** [argus/api/server.py:606-616](argus/api/server.py#L606-L616)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **CORS default is `["http://localhost:5173"]`** — Vite dev. Tauri desktop and PWA mobile (per project knowledge) use different origins. Configurable via `api.cors_origins`, but the default is dev-only.

**Impact:**

> Minor. Live deployments override.

**Suggested fix:**

> Document this in the ApiConfig docstring. No code change.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 5: `P1-F1-2` [CRITICAL]

**File/line:** [argus/api/dev_state.py:2296-2328](argus/api/dev_state.py#L2296-L2328) + [dev_state.py:52](argus/api/dev_state.py#L52)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`dev_state.py` badly outdated — only 7 of 15 live+shadow strategies seeded; V1 regime, no V2; no HQS/CFT/Experiments/VIX/Learning services.** Mock strategies: ORB Breakout, ORB Scalp, VWAP Reclaim, Afternoon Momentum, R2G (marked `is_active=False, pipeline_stage="exploration"` despite being live), Bull Flag (same), Flat-Top (same). Missing: HOD Break, Gap-and-Go, Dip-and-Rip, PMH, Micro Pullback, VWAP Bounce, Narrow Range, ABCD. [Line 52](argus/api/dev_state.py#L52) imports legacy `MarketRegime, RegimeIndicators` from V1; RegimeVector / RegimeClassifierV2 never referenced. `create_dev_state()` populates neither `counterfactual_store`, `vix_data_service`, `experiment_store`, `historical_query_service`, nor `learning_service` on AppState.

**Impact:**

> Frontend developers using `python -m argus.api --dev` see a snapshot from ~Sprint 27 of what the system is. Any new-feature UI work (Experiments page, VIX card, Learning Loop proposals) can't be exercised without a live backend, forcing devs to boot the full engine. Mock trades seeded for strategies that still exist use correct `strategy_id`s, but any page filtered by active-strategy set shows only 3 "active" strategies.

**Suggested fix:**

> Decide: (a) rebuild `dev_state.py` to current state (add missing strategies, populate all service stubs, upgrade regime V1→V2); or (b) retire `--dev` mode and require full-engine boot for UI dev (delete `__main__.py --dev` branch, `dev_state.py`, 2 test files). Option (b) is cleaner given the cost of keeping (a) in sync. If kept, add a CI check that enumerates registered strategies and fails if dev_state is missing any.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 6: `P1-F1-11` [MEDIUM]

**File/line:** [argus/api/dev_state.py:2336](argus/api/dev_state.py#L2336) → [trades.py:612](argus/api/routes/trades.py#L612)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`app_state._mock_watchlist` monkey-patched onto AppState; `trades.py:612` uses `hasattr(state, "_mock_watchlist")` as a dev-mode sentinel.** The dataclass has no `_mock_watchlist` field — `# type: ignore[attr-defined]` at the assignment. The route file infers dev-mode by attribute existence.

**Impact:**

> Fragile coupling. Any future AppState cleanup ("prune unused fields") might remove the monkey-patch. Non-obvious test-data flow.

**Suggested fix:**

> Add an explicit `is_dev_mode: bool = False` field on AppState, set True in `create_dev_state()`. Replace hasattr check.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 7: `P1-F1-22` [COSMETIC]

**File/line:** [argus/api/dev_state.py](argus/api/dev_state.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> File docstring says "Real ORB strategy" (line 1887) but dev_state actually seeds a MockStrategy dataclass, not the production OrbBreakoutStrategy.

**Impact:**

> None.

**Suggested fix:**

> Update docstring.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 8: `P1-F1-13` [LOW]

**File/line:** [argus/api/websocket/live.py:354-356](argus/api/websocket/live.py#L354-L356), [arena_ws.py:291-299](argus/api/websocket/arena_ws.py#L291-L299)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **QueueFull drops messages silently to the client.** Both WS dispatch paths: `put_nowait` in try/except, log WARNING, then discard. Slow clients silently fall behind.

**Impact:**

> Client chart drifts from server state with no signal to reconnect/refresh.

**Suggested fix:**

> Emit a `{"type": "state_desync"}` message before dropping, or close the socket with a specific code (e.g., 4003) forcing the client to reconnect with a fresh snapshot.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 9: `P1-F1-14` [LOW]

**File/line:** [argus/api/websocket/live.py:395](argus/api/websocket/live.py#L395)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`hasattr(self._broker, "get_account")` defensive duck-typing.** `Broker` ABC in [execution/broker.py](argus/execution/broker.py) should declare `get_account()`; if it does, the hasattr is dead code. If it doesn't, account polling is type-unsafe.

**Impact:**

> Minor fragility.

**Suggested fix:**

> Confirm `get_account()` is on the Broker ABC; remove the hasattr.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 10: `P1-F1-23` [COSMETIC]

**File/line:** [argus/api/websocket/live.py:455-462](argus/api/websocket/live.py#L455-L462)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `from jose import jwt` is imported inside `websocket_endpoint()` despite `from jose import JWTError` already at module top (line 18).

**Impact:**

> None.

**Suggested fix:**

> Lift `jwt` import to module level.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 11: `P1-F1-19` [LOW]

**File/line:** [argus/api/routes/__init__.py:9-36](argus/api/routes/__init__.py#L9-L36)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Route-import order is mostly alphabetical but not strictly** — `historical` appears before `ai` at lines 11-12 (should be `ai < arena < historical`). Other positions: `intelligence` (line 22) between `health` (21) and `experiments` (23) — `experiments` alphabetizes before both.

**Impact:**

> None functional.

**Suggested fix:**

> Sort imports strictly alphabetically.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 12: `P1-F1-25` [COSMETIC]

**File/line:** [argus/api/routes/__init__.py](argus/api/routes/__init__.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `observatory_router` is imported separately in `server.py:630` but NOT aggregated in `routes/__init__.py`. Conditional mount is intentional, but non-obvious to readers scanning the routes index.

**Impact:**

> None.

**Suggested fix:**

> Add a comment in `routes/__init__.py` noting observatory is conditionally mounted in `server.py` when `observatory.enabled`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 13: `P1-F1-1` [CRITICAL]

**File/line:** [argus/api/routes/market.py:151-293](argus/api/routes/market.py#L151-L293)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`GET /market/{symbol}/bars` silently returns synthetic bars when real data unavailable.** 3-tier fallback: IntradayCandleStore → DataService → `_generate_synthetic_bars()` at line 287. Response shape (`BarsResponse`) has NO flag indicating synthetic data. Frontend charts render fake prices indistinguishably from real ones.

**Impact:**

> In production (Databento flake or pre-market gap with no candle store): user sees plausible but fabricated OHLCV on the dashboard chart. No telemetry logs this event at WARNING+.

**Suggested fix:**

> Add `source: Literal["live", "historical", "synthetic"]` field to `BarsResponse`. Log WARNING when falling through to synthetic. Frontend must gate display behind real-data source.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 14: `P1-F1-18` [LOW]

**File/line:** [argus/api/routes/market.py:287](argus/api/routes/market.py#L287)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`_generate_synthetic_bars(limit=min(limit, 390))`** caps synthetic at 390 but `limit` param supports up to 1000 ([line 155](argus/api/routes/market.py#L155)). Real-data paths return up to `limit`; synthetic path silently truncates.

**Impact:**

> Asymmetric behavior between real/synthetic paths. Related to CRITICAL #1.

**Suggested fix:**

> Either lift the 390 cap or enforce it as the hard parameter max.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 15: `P1-F1-21` [COSMETIC]

**File/line:** [argus/api/auth.py:105](argus/api/auth.py#L105)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `create_access_token(jwt_secret, expires_hours: int = 24)` — docstring says "Default 24" but every call site passes `api_config.jwt_expiry_hours`. The default is unreachable.

**Impact:**

> None.

**Suggested fix:**

> Drop the default, make `expires_hours` required.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 16: `P1-F1-24` [COSMETIC]

**File/line:** [argus/api/routes/auth.py:132-149](argus/api/routes/auth.py#L132-L149)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `/auth/me` lacks `response_model=` (tiny helper returning `{"user": str, "timestamp": str}`) — easy to add for OpenAPI coverage.

**Impact:**

> None (functional).

**Suggested fix:**

> Define `UserInfoResponse` Pydantic model. Part of MEDIUM #5's batch.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 17: `P1-F1-9` [MEDIUM]

**File/line:** [argus/api/routes/historical.py:201](argus/api/routes/historical.py#L201)
**Safety:** `safe-during-trading` _(tag inferred from finding context; original CSV column was garbled by embedded newlines — operator may override)_
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`POST /historical/validate-coverage` accepts `body: dict = Body(...)` — untyped request body.** No Pydantic validation.

**Impact:**

> Invalid payloads surface as runtime `KeyError` instead of a 422 validation error. Breaks the pattern every other POST in the codebase follows.

**Suggested fix:**

> Define `ValidateCoverageRequest` with `symbols: list[str]`, `min_bars: int

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 18: `P1-F1-12` [LOW]

**File/line:** [argus/api/routes/strategies.py:389](argus/api/routes/strategies.py#L389)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Auth parameter named `_user` — every other route uses `_auth`.** Single outlier across 96 dependencies.

**Impact:**

> None functional. Cosmetic-but-trips-greps.

**Suggested fix:**

> Rename `_user` → `_auth`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 19: `P1-F1-10` [MEDIUM]

**File/line:** [argus/api/routes/trades.py:614-623](argus/api/routes/trades.py#L614-L623)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`GET /trades/{trade_id}/replay` is a STUB in non-dev mode** — returns `bars=[]`, `entry_bar_index=0`, `exit_bar_index=None`, `vwap=None`. Dev mode generates synthetic bars. Architecture.md documents a different path (see Finding #8) and implies it works. Related to DEF-029 (persist candle data).

**Impact:**

> Operator clicking "Replay" on Performance page in production sees empty chart; error not obvious.

**Suggested fix:**

> Either (a) remove the endpoint for now and return 501 Not Implemented until DEF-029 lands, or (b) wire it to `IntradayCandleStore` for same-session replay when the store has bars.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 20: `P1-F1-20` [LOW]

**File/line:** [argus/api/setup_password.py:85](argus/api/setup_password.py#L85)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **Setup CLI prints a generated JWT secret to stdout.** If captured by shell history, screen-sharing, or terminal multiplexer logs, the secret leaks.

**Impact:**

> User-operator foot-gun.

**Suggested fix:**

> Write secret to a `.env.example` file with 0600 permissions, or prompt the user to paste it into `.env` without printing.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 21: `P1-F1-16` [LOW]

**File/line:** [argus/api/websocket/observatory_ws.py:133-143](argus/api/websocket/observatory_ws.py#L133-L143)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **When Observatory query exceeds push interval, tracked state (`previous_tiers`, `previous_eval_count`) is advanced without emitting a push.** Prevents diff corruption on the next interval, but means tier transitions during the slow interval are never signalled to the client.

**Impact:**

> Slow-query windows silently drop transition events.

**Suggested fix:**

> Emit a `type: "interval_skipped"` marker instead of updating state; clients can re-fetch on demand.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-11-backend-api**`.

### Finding 22: `P1-F2-M09` [MEDIUM]

**File/line:** [features/dashboard/VitalsStrip.test.tsx:59](argus/ui/src/features/dashboard/VitalsStrip.test.tsx#L59), [features/orchestrator/StrategyDecisionStream.test.tsx:30](argus/ui/src/features/orchestrator/StrategyDecisionStream.test.tsx#L30), [hooks/__tests__/useQuality.test.tsx:48](argus/ui/src/hooks/__tests__/useQuality.test.tsx#L48), [features/arena/useArenaWebSocket.test.ts:72](argus/ui/src/features/arena/useArenaWebSocket.test.ts#L72)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> Hardcoded absolute dates in test fixtures: `'2026-04-02T09:30:00Z'`, `'2026-03-16T10:30:00-04:00'`, `'2026-03-14T10:00:00Z'`, `'2024-01-15T09:30:00Z'`. Same root-cause class as pytest DEF-137/DEF-163 (date decay). `TradeStatsBar.test.tsx:20` uses `new Date().toISOString()` — the correct pattern.

**Impact:**

> Tests may start failing as real time advances past the fixture dates, especially tests that render relative-time strings ("3 days ago" etc.).

**Suggested fix:**

> Replace with `new Date()` or `new Date(Date.now() - N*DAY)` for relative-date assertions. Add Vitest equivalent of DEF-163 to the deferred list.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 23: `P1-F1-8` [MEDIUM]

**File/line:** [docs/architecture.md:1717-1781](docs/architecture.md#L1717-L1781) vs [argus/api/routes/](argus/api/routes/)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> **Architecture.md API catalog is substantially drifted (≥10 mismatches).** (a) Line 1717-1719: `/api/v1/catalysts*` — code mounts them under `/api/v1/intelligence/catalysts/*`; `/catalysts/refresh` does not exist. (b) Line 1720-1722: "intelligence briefings" paths wrong; code has `/debrief/briefings` and `/intelligence/premarket/briefing*`. (c) Line 1743-1745: AI briefing/report/analyze POSTs do not exist in [ai.py](argus/api/routes/ai.py). (d) Line 1770: `GET /api/v1/performance/replay/{id}` — code has `/trades/{id}/replay`. (e) Line 1774: market/bars described "Synthetic OHLCV for dev mode" — actually serves real data first (see CRITICAL #1). (f) Line 1777: "/arena/positions ... no JWT required for polling" — code DOES require JWT. (g) Entire Experiments section (7 endpoints), Watchlist, Controls (5 endpoints), Trades stats/batch/export/csv, `/historical/symbols,coverage,bars,validate-coverage` — undocumented.

**Impact:**

> Frontend devs and operators consult wrong docs; AI assistants read stale contract; onboarding friction.

**Suggested fix:**

> Flag for **P1-H1a** (primary context compression session). Architecture.md needs a mechanically-regenerated endpoint catalog (introspect FastAPI routes).

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

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

### Vitest (frontend paths touched)

```bash
cd argus/ui && npx vitest run --reporter=verbose 2>&1 | tail -10
# Record PASS count: __________
# Net delta: __________ (MUST be >= 0)
```

### Audit report back-annotation

For each resolved finding, update the row in the originating audit
report file (in `docs/audits/audit-2026-04-21/`) from:

```
| ... | description | ... |
```

to:

```
| ... | ~~description~~ **RESOLVED FIX-11-backend-api** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-11-backend-api**` instead.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-11): backend API cleanup

Addresses audit findings:
- P1-F1-3 [MEDIUM]: 'app_state
- P1-F1-4 [MEDIUM]: Orchestrator / RegimeClassifierV2 / VIXDataService private-attribute mutations and reads — 'orchestrator
- P1-F1-15 [LOW]: 'lifespan()' handler is ~550 lines of nested 'try/except' covering 9 initialization phases
- P1-F1-17 [LOW]: CORS default is '["http://localhost:5173"]' — Vite dev
- P1-F1-2 [CRITICAL]: 'dev_state
- P1-F1-11 [MEDIUM]: 'app_state
- P1-F1-22 [COSMETIC]: File docstring says "Real ORB strategy" (line 1887) but dev_state actually seeds a MockStrategy dataclass, not the produ
- P1-F1-13 [LOW]: QueueFull drops messages silently to the client
- P1-F1-14 [LOW]: 'hasattr(self
- P1-F1-23 [COSMETIC]: 'from jose import jwt' is imported inside 'websocket_endpoint()' despite 'from jose import JWTError' already at module t
- P1-F1-19 [LOW]: Route-import order is mostly alphabetical but not strictly — 'historical' appears before 'ai' at lines 11-12 (should be 
- P1-F1-25 [COSMETIC]: 'observatory_router' is imported separately in 'server
- P1-F1-1 [CRITICAL]: 'GET /market/{symbol}/bars' silently returns synthetic bars when real data unavailable
- P1-F1-18 [LOW]: '_generate_synthetic_bars(limit=min(limit, 390))' caps synthetic at 390 but 'limit' param supports up to 1000 ([line 155
- P1-F1-21 [COSMETIC]: 'create_access_token(jwt_secret, expires_hours: int = 24)' — docstring says "Default 24" but every call site passes 'api
- P1-F1-24 [COSMETIC]: '/auth/me' lacks 'response_model=' (tiny helper returning '{"user": str, "timestamp": str}') — easy to add for OpenAPI c
- P1-F1-9 [MEDIUM]: 'POST /historical/validate-coverage' accepts 'body: dict = Body(
- P1-F1-12 [LOW]: Auth parameter named '_user' — every other route uses '_auth'
- P1-F1-10 [MEDIUM]: 'GET /trades/{trade_id}/replay' is a STUB in non-dev mode — returns 'bars=[]', 'entry_bar_index=0', 'exit_bar_index=None
- P1-F1-20 [LOW]: Setup CLI prints a generated JWT secret to stdout
- P1-F1-16 [LOW]: When Observatory query exceeds push interval, tracked state ('previous_tiers', 'previous_eval_count') is advanced withou
- P1-F2-M09 [MEDIUM]: Hardcoded absolute dates in test fixtures: ''2026-04-02T09:30:00Z'', ''2026-03-16T10:30:00-04:00'', ''2026-03-14T10:00:0
- P1-F1-8 [MEDIUM]: Architecture

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
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-11-backend-api**`
- [ ] Vitest suite net delta >= 0
