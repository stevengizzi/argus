# Fix Session FIX-04-execution: argus/execution — broker adapters, order manager

> Generated from audit Phase 2 on 2026-04-21. Paste into a fresh Claude Code session. This prompt is **standalone** — do not read other FIX-NN prompts.

## Scope

**Findings addressed:** 19
**Files touched:** `argus/execution/broker_router.py`, `argus/execution/execution_record.py`, `argus/execution/ibkr_broker.py`, `argus/execution/order_manager.py`, `tests/execution/test_broker_router.py`, `tests/execution/test_order_manager.py`
**Safety tag:** `weekend-only`
**Theme:** Execution-layer findings: dead BrokerRouter class, Order Manager internal-state guards, IBKR reconnection edges, typing gaps.

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
marker (`audit(FIX-04): WIP — <reason>`) rather than leaving
uncommitted changes.

## Implementation Order

Findings below are ordered to minimize file churn (edits to the same file are adjacent). Apply in this order:

1. Tests first where new behavior is added.
2. Code edits in the order listed in the Findings section (grouped by file).
3. Docs / audit-report back-annotation last.

**Per-file finding counts (edit hotspots):**

- `argus/execution/order_manager.py`: 11 findings
- `argus/execution/ibkr_broker.py`: 4 findings
- `argus/execution/broker_router.py`: 1 finding
- `argus/execution/execution_record.py`: 1 finding
- `tests/execution/test_broker_router.py`: 1 finding
- `tests/execution/test_order_manager.py`: 1 finding

## Findings to Fix

### Finding 1: `P1-C1-C01` [CRITICAL]

**File/line:** [order_manager.py:2004](argus/execution/order_manager.py#L2004), [order_manager.py:2039](argus/execution/order_manager.py#L2039)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_create_reco_position` and `_reconstruct_known_position` read `getattr(pos, "avg_entry_price", 0.0)` but `argus.models.trading.Position` uses field name `entry_price`. The getattr silently returns `0.0`.

**Impact:**

> After any mid-day restart with open positions, reconstructed `ManagedPosition` objects carry `entry_price=0.0`. This corrupts: (a) live P&L in `_publish_position_pnl` — `(price − 0) × shares` = massively inflated unrealized P&L broadcast to UI; (b) `_handle_t1_fill` realized P&L — `(t1_price − 0) × qty` writes a huge fake "win" to trades DB; (c) MFE/MAE R-multiples divided by a risk computed against `entry_price=0`. DEF-159's `entry_price_known` guard saves the trade record but does **not** protect runtime telemetry or partial-exit accumulation. Same regression class as DEF-139/140 (`qty` vs `shares`).

**Suggested fix:**

> Change both sites to `getattr(pos, "entry_price", 0.0)`. Add a regression test that drives `reconstruct_from_broker` through `SimulatedBroker` with a pre-seeded position and asserts `managed.entry_price == broker_entry`. Consider deleting `getattr` and directly accessing `pos.entry_price` now that the Broker ABC contractually returns `Position`.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 2: `P1-C1-C02` [CRITICAL]

**File/line:** [order_manager.py:2061](argus/execution/order_manager.py#L2061)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_reconstruct_known_position` reads `getattr(order, "qty", 0)` but `argus.models.trading.Order` uses field name `quantity`. The getattr silently returns `0`.

**Impact:**

> Reconstructed positions set `t1_shares = 0`. Combined with `t1_filled = (t1_order_id is None and t1_shares == 0)` at L2077, a live T1 bracket order is paired with `t1_shares=0` and `t1_filled=False` — inconsistent state. On T1 fill, `position.t1_shares=0` breaks downstream calculations in `_handle_t1_fill` (the check `if t1_shares == 0 and share_count > 0: t1_shares = 1` does not apply post-reconstruction).

**Suggested fix:**

> Change to `getattr(order, "quantity", 0)` — or delete the `getattr` and use `order.quantity` directly, since the Broker ABC contractually returns `Order`. Add same-shape regression test.

**Audit notes:** CRITICAL — auto-approve

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 3: `P1-C1-M02` [MEDIUM]

**File/line:** [order_manager.py:1955-1989](argus/execution/order_manager.py#L1955-L1989)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_drain_startup_flatten_queue` submits market-sell orders at 9:30 ET market-open **without** cancelling pre-existing bracket orders for the symbol. By contrast, the direct path `_flatten_unknown_position(force_execute=True)` and EOD Pass 2 cancel bracket orders first (DEF-158 fix at L1911-L1931). If zombie positions carry residual stop/T1 orders from a prior session, those orders can fire between market-open and the drain call, producing a double-SELL (short-selling risk).

**Impact:**

> Same class as DEF-158 but in the queued-zombie path. Probability is a function of how often ARGUS boots pre-market with both zombie positions **and** orphan bracket orders at IBKR; currently rare (EOD flatten usually clears brackets), but the risk mode is identical to the three DEF-158 root causes resolved in Sprint 31.8 S3.

**Suggested fix:**

> Move the bracket-cancel loop (currently at L1911-L1931) into a shared helper and call it from `_drain_startup_flatten_queue` before each `place_order`. Add a test that seeds open orders for a queued zombie and asserts they're cancelled before the queued SELL fires.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 4: `P1-C1-M06` [MEDIUM]

**File/line:** [order_manager.py:2068](argus/execution/order_manager.py#L2068)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_reconstruct_known_position` sets `entry_time=self._clock.now()` on reconstructed positions. Time-stop arithmetic in the poll loop computes `elapsed_seconds = (now - position.entry_time)` — which always starts at zero post-restart.

**Impact:**

> Per-position `time_stop_seconds` on reconstructed positions is `None` (not set by reconstruction), so DEC-122 path is skipped. But the fallback `max_position_duration_minutes` (default 240min) is measured from **restart time**, not from actual entry time. On a mid-day restart 15 minutes before the original time-stop would have fired, the position now has a fresh 240-minute lease. Bounded by EOD flatten but degrades time-stop semantics after any reconnect.

**Suggested fix:**

> (a) Persist `entry_time` in the trades DB live-positions sidecar and restore it on reconstruction, or (b) conservatively set `entry_time = self._clock.now() - timedelta(minutes=config.max_position_duration_minutes // 2)` to bias toward earlier time-stop firing. (a) is the correct fix; (b) is a stopgap.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 5: `P1-C1-L05` [LOW]

**File/line:** [order_manager.py:1441-1452](argus/execution/order_manager.py#L1441-L1452)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_flattened_today` set to True inside `eod_flatten()` [L1605](argus/execution/order_manager.py#L1605) **and** by the poll loop after the call [L1451](argus/execution/order_manager.py#L1451). Redundant — the second write is unreachable because `eod_flatten` already set it.

**Impact:**

> Harmless double-write.

**Suggested fix:**

> Delete the redundant poll-loop assignment.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 6: `P1-C1-L06` [LOW]

**File/line:** [order_manager.py:1454-1465](argus/execution/order_manager.py#L1454-L1465)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_poll_loop` computes `et_tz2 = ZoneInfo("America/New_York")` and `now_et2` inline inside the startup-queue drain block because `et_tz`/`now_et` from the EOD-flatten block above may not be in scope. The "2" suffix is a workaround for a structural issue — both blocks convert `now` to ET independently.

**Impact:**

> Duplicate work per poll tick.

**Suggested fix:**

> Lift ET conversion to a single helper `_now_et()` and call once at the top of the loop body.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 7: `P1-C1-L07` [LOW]

**File/line:** [order_manager.py:2741-L2748](argus/execution/order_manager.py#L2741-L2748)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `_close_position` pops `_reconciliation_miss_count[symbol]`, `_stop_retry_count[symbol]`, `_amended_prices[symbol]` — which are also cleared wholesale in `reset_daily_state`. Double cleanup; harmless but signals intent confusion.

**Impact:**

> None.

**Suggested fix:**

> Leave as-is (defense in depth) or document as intentional.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 8: `P1-C1-L08` [LOW]

**File/line:** [order_manager.py:1376-L1389](argus/execution/order_manager.py#L1376-L1389)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_handle_flatten_fill` has a strategy_id match path and a "fall back to first open position" path with a WARNING log. The fallback exists for backward-compat with positions that were opened before strategy_id was tracked on `PendingManagedOrder`. With 89 sprints shipped, this legacy shape likely no longer exists.

**Impact:**

> Dead fallback path; could be promoted to a hard error to catch bugs earlier.

**Suggested fix:**

> Replace the `if position is None` fallback with `logger.error(...)` and return, tightening the invariant. Run full suite afterward to confirm.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 9: `P1-C1-L09` [LOW]

**File/line:** [order_manager.py:112-116](argus/execution/order_manager.py#L112-L116)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `ManagedPosition.mfe_time` / `mae_time` defaulted to `None`, then set inside `on_tick` at L725 / L731. However the MFE/MAE R-multiples are only computed when price changes — the first tick after fill where `event.price == entry_price` leaves `mfe_time=None`. On an instant-reversal position, `mfe_time` may stay None forever.

**Impact:**

> Cosmetic — downstream handling of None is not audited here but may show as "null" in analytics.

**Suggested fix:**

> Initialize `mfe_time = entry_time` in `_handle_entry_fill` (mirroring `mfe_price = entry_price`).

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 10: `P1-C1-L10` [LOW]

**File/line:** [order_manager.py:188](argus/execution/order_manager.py#L188)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> Constructor parameter `auto_cleanup_orphans` is documented "Deprecated — use reconciliation_config.auto_cleanup_orphans instead" but still accepted and still honored [L3001](argus/execution/order_manager.py#L3001).

**Impact:**

> Compatibility shim; no users identified.

**Suggested fix:**

> Grep all callers; if none pass the deprecated arg, remove the parameter.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 11: `P1-D1-M03` [MEDIUM]

**File/line:** [execution/order_manager.py:482-491](argus/execution/order_manager.py#L482-L491)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> **`SignalRejectedEvent` from margin circuit breaker tags itself `rejection_stage="risk_manager"`** but the reason is margin-specific ("Margin circuit breaker open…"). `RejectionStage` enum has no MARGIN_CIRCUIT value, so the filter-accuracy breakdown `by_stage` groups margin rejections together with ordinary risk-manager rejections.

**Impact:**

> `FilterAccuracy` analyses conflate two different rejection classes. `by_reason` can distinguish them via string match, but `by_stage` (the principal cut used by the Experiments + Learning surfaces) cannot. Masks a potentially material operational signal during margin incidents.

**Suggested fix:**

> Extend `RejectionStage` with `MARGIN_CIRCUIT = "margin_circuit"` (and update `counterfactual_positions.rejection_stage` values to accept it). Bump emitted stage in `order_manager.py:485`.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 12: `P1-C1-M01` [MEDIUM]

**File/line:** [ibkr_broker.py:638-770](argus/execution/ibkr_broker.py#L638-L770)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `place_bracket_order` docstring claims "atomic submission" but implementation is sequential `_ib.placeOrder()` calls (parent, stop, each target). If an exception raises between the parent and stop submission (e.g., Pydantic validation, network blip), the parent is left at IBKR in `PendingSubmit` with `transmit=False` — an orphan that will never transmit but occupies an order slot. No rollback path.

**Impact:**

> Low probability in practice (ib_async calls don't await between these points) but the safety claim in the docstring is misleading. A crash between parent submit and stop submit during a live run would leave an untransmitted parent order.

**Suggested fix:**

> (a) Wrap the body in try/except and call `_ib.cancelOrder(parent)` on failure before re-raising. (b) Soften the docstring to reflect actual behavior. Fix (a) is the real hardening; (b) alone is insufficient.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 13: `P1-C1-M05` [MEDIUM]

**File/line:** [ibkr_broker.py:344-355](argus/execution/ibkr_broker.py#L344-L355)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_on_error` handles IBKR error 404 with an **early return** before the `is_order_rejection` check below. 404 adds the symbol to `error_404_symbols` but does **not** publish `OrderCancelledEvent`. Relies entirely on IBKR subsequently firing an `orderStatusEvent(status="Cancelled")` to wake up OrderManager.

**Impact:**

> If IBKR's cancel status message is delayed or dropped, the `PendingManagedOrder` entry stays in `_pending_orders` indefinitely, eventually producing a phantom pending-entry exposure counted by `get_pending_entry_exposure()`. A robust contract should not depend on two separate IBKR messages (error + status) both arriving.

**Suggested fix:**

> Remove the early return on L355; let 404 fall through to the shared `is_order_rejection` branch which publishes `OrderCancelledEvent(reason="IBKR 404: ...")`. The Order Manager's `on_cancel` path already handles flatten-pending cleanup correctly.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 14: `P1-C1-L02` [LOW]

**File/line:** [ibkr_broker.py:1231-1246](argus/execution/ibkr_broker.py#L1231-L1246)
**Safety:** `weekend-only`
**Action type:** Code change (`weekend-only`)

**Original finding:**

> `_find_trade_by_order_id` does an O(n) scan of all trades in `_ib.trades()` on every `cancel_order` / `modify_order` / `get_order_status` call. For a session with hundreds of bracket legs, this is small but unbounded.

**Impact:**

> Not performance-critical at current volumes (<100 active brackets). Scales linearly with session length.

**Suggested fix:**

> Maintain a parallel `dict[int, Trade]` indexed by `orderId`, populated in `_on_order_status`. Drop stale entries on Cancelled/Filled.

**Audit notes:** bundle with same-file MEDIUM/CRITICAL fixes

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 15: `P1-C1-L03` [LOW]

**File/line:** [ibkr_broker.py:598-602,L633-L636,L695-L697](argus/execution/ibkr_broker.py#L598-L602) (multiple sites)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `OrderResult` constructed with string literal `status="submitted"` / `"rejected"` instead of `OrderStatus.SUBMITTED` / `OrderStatus.REJECTED` enum values. Pydantic coerces but the pattern is inconsistent with the rest of the codebase which uses enum access.

**Impact:**

> Cosmetic; readers/linters cannot verify the valid status set.

**Suggested fix:**

> Replace with enum references.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 16: `P1-C1-M04` [MEDIUM]

**File/line:** [broker_router.py](argus/execution/broker_router.py)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> `BrokerRouter` class is **dead code in production.** No file in `argus/` imports it (verified by grep); only `tests/execution/test_broker_router.py` references it. `main.py` selects a broker via `if/elif` on `broker_source` without any routing abstraction. This is legacy Sprint 2 scaffolding.

**Impact:**

> Maintenance cost: every future broker-selection change must remember this file doesn't need updating. Test suite runs tests for an unused class. Architecture doc [architecture.md:315](docs/architecture.md#L315) still describes the pattern as active.

**Suggested fix:**

> Either (a) delete `broker_router.py` + its test file + the architecture.md section, or (b) wire it into `main.py` and delete the `if/elif` block. (a) is the right call — multi-broker routing is not on the near roadmap and the if/elif is simpler.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 17: `P1-C1-L04` [LOW]

**File/line:** [execution_record.py:10-15](argus/execution/execution_record.py#L10-L15)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> Imports `from datetime import ..., timezone` and separately uses `timezone.utc` at L113 instead of the project-standard `datetime.UTC` (Python 3.11+) used elsewhere. Also `_ET = ZoneInfo(...)` is defined between imports — violates CLAUDE.md "all imports at top" rule.

**Impact:**

> Style inconsistency. No functional impact.

**Suggested fix:**

> Use `datetime.UTC` throughout; move `_ET` below all imports.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

### Finding 18: `P1-C1-L01` [LOW]

**File/line:** `tests/execution/test_broker_router.py` (exists but not audited in full — referenced from M-04)
**Safety:** `deferred-to-defs`
**Action type:** Code fix + DEF log

**Original finding:**

> Tests for dead `BrokerRouter` class run on every CI cycle. Also the Alpaca broker has a full test suite (`tests/execution/test_alpaca_broker.py`, ~30 tests per earlier sprint history) exercising a code path not active in any shipped config.

**Impact:**

> CI seconds spent, maintenance pinning on alpaca-py SDK changes. Not user-facing.

**Suggested fix:**

> Deferred to DEF triage (P1-H4). If M-04 removes `broker_router.py`, the test file goes with it.

**Required steps for this finding:**
1. Apply the suggested fix (code change) as specified.
2. Add a DEF-NNN entry to CLAUDE.md under the appropriate section.
   Use the next available DEF number (grep CLAUDE.md for the highest
   existing DEF-NNN and increment). The DEF entry documents the
   decision + resolution trail so future sessions can find it.
3. Reference the DEF ID in the commit message bullet.

### Finding 19: `P1-G2-M04` [MEDIUM]

**File/line:** [tests/execution/test_order_manager.py:700-752](tests/execution/test_order_manager.py#L700-L752)
**Safety:** `safe-during-trading`
**Action type:** Code change (`safe-during-trading`)

**Original finding:**

> **`test_emergency_flatten_*` fixtures lack a fill-event publisher — 30s wait comes from `OrderManagerConfig()` default `eod_flatten_timeout_seconds=30`.** Confirms and explains G1 M4. The test calls `order_manager.emergency_flatten()` which calls `eod_flatten()` which creates `asyncio.Event`s per symbol and does `await asyncio.wait_for(gather(...), timeout=30.0)`. The mock broker `place_order` returns `OrderStatus.PENDING` but **no test code ever sets the corresponding `_eod_flatten_events[symbol].set()` via a synthetic `OrderFilledEvent`** — so each of 6 tests waits the full 30s timeout. 180s of wall-clock is wasted per full suite run.

**Impact:**

> Confirms G1 M4 diagnosis. Adds specificity: the fix is either (a) publish a synthetic `OrderFilledEvent` after `emergency_flatten()` kicks off, or (b) override the config fixture with `eod_flatten_timeout_seconds=0.1`.

**Suggested fix:**

> Override the shared `config` fixture for these specific tests with `OrderManagerConfig(eod_flatten_timeout_seconds=0.1)`. Alternatively, subscribe to `OrderSubmittedEvent` in the test, and publish a matching `OrderFilledEvent` synchronously. Pattern to follow: [test_order_manager_sprint329.py:320-340](tests/execution/test_order_manager_sprint329.py#L320-L340) already overrides `eod_flatten_timeout_seconds=1` or `=5` for its tests — replicate that for the `test_order_manager.py` tests.

**Required steps for this finding:**
1. Re-read the file at the cited line range before editing.
2. Apply the suggested fix. If the suggested fix is ambiguous or
   requires a judgment call, lay out the options in a comment and
   pick the one most consistent with existing patterns.
3. If the fix adds new behavior, add a test that would fail without
   the fix. If it removes code, grep-verify no other call sites remain.
4. Update the audit report row with `**RESOLVED FIX-04-execution**`.

## Post-Session Verification (before commit)

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
| ... | ~~description~~ **RESOLVED FIX-04-execution** | ... |
```

For `read-only-no-fix-needed` findings that were verified, use
`**RESOLVED-VERIFIED FIX-04-execution**` instead.

## Close-Out Report (REQUIRED — follows `workflow/claude/skills/close-out.md`)

Run the close-out skill now to produce the Tier 1 self-review report. Use
the EXACT procedure in `workflow/claude/skills/close-out.md`. Key fields
for this FIX session:

- **Sprint:** `audit-2026-04-21-phase-3`
- **Session:** `FIX-04` (full ID: `FIX-04-execution`)
- **Date:** today's ISO date

### Session-specific regression checks

Populate the close-out's `### Regression Checks` table with the following
campaign-level checks (all must PASS for a CLEAN self-assessment):

| Check | Result | Notes |
|-------|--------|-------|
| pytest net delta >= 0 against baseline 4,933 passed | | |
| DEF-150 flake remains the only pre-existing failure (no new regressions) | | |
| No file outside this session's declared Scope was modified | | |
| Every resolved finding back-annotated in audit report with `**RESOLVED FIX-04-execution**` | | |
| Every DEF closure recorded in CLAUDE.md | | |
| Every new DEF/DEC referenced in commit message bullets | | |
| `read-only-no-fix-needed` findings: verification output recorded OR DEF promoted | | |
| `deferred-to-defs` findings: fix applied AND DEF-NNN added to CLAUDE.md | | |

### Output format

Render the close-out inside a fenced markdown code block (triple backticks
with `markdown` language hint) bracketed by `---BEGIN-CLOSE-OUT---` /
`---END-CLOSE-OUT---` markers, followed by the `json:structured-closeout`
JSON appendix. Exact format per the close-out.md skill.

The operator will copy this block into the Work Journal conversation on
Claude.ai. Do NOT summarize or modify the format — the conversation parses
these blocks by structure.

### Self-assessment gate

Per close-out.md:
- **CLEAN:** all findings resolved, no unexpected decisions, all tests pass, all regression checks pass
- **MINOR_DEVIATIONS:** all findings addressed but minor judgment calls needed
- **FLAGGED:** any partial finding, test failures, regression check failures, scope exceeded, architectural concerns

**Proceed to the Commit section below UNLESS self-assessment is FLAGGED.**
If FLAGGED, pause. Surface the flag to the operator with a clear
description. Do not push. Wait for operator direction.

## Commit

```bash
git add <paths>
git commit -m "$(cat <<'COMMIT_EOF'
audit(FIX-04): execution layer cleanup

Addresses audit findings:
- P1-C1-C01 [CRITICAL]: '_create_reco_position' and '_reconstruct_known_position' read 'getattr(pos, "avg_entry_price", 0
- P1-C1-C02 [CRITICAL]: '_reconstruct_known_position' reads 'getattr(order, "qty", 0)' but 'argus
- P1-C1-M02 [MEDIUM]: '_drain_startup_flatten_queue' submits market-sell orders at 9:30 ET market-open without cancelling pre-existing bracket
- P1-C1-M06 [MEDIUM]: '_reconstruct_known_position' sets 'entry_time=self
- P1-C1-L05 [LOW]: '_flattened_today' set to True inside 'eod_flatten()' [L1605](argus/execution/order_manager
- P1-C1-L06 [LOW]: '_poll_loop' computes 'et_tz2 = ZoneInfo("America/New_York")' and 'now_et2' inline inside the startup-queue drain block 
- P1-C1-L07 [LOW]: '_close_position' pops '_reconciliation_miss_count[symbol]', '_stop_retry_count[symbol]', '_amended_prices[symbol]' — wh
- P1-C1-L08 [LOW]: '_handle_flatten_fill' has a strategy_id match path and a "fall back to first open position" path with a WARNING log
- P1-C1-L09 [LOW]: 'ManagedPosition
- P1-C1-L10 [LOW]: Constructor parameter 'auto_cleanup_orphans' is documented "Deprecated — use reconciliation_config
- P1-D1-M03 [MEDIUM]: 'SignalRejectedEvent' from margin circuit breaker tags itself 'rejection_stage="risk_manager"' but the reason is margin-
- P1-C1-M01 [MEDIUM]: 'place_bracket_order' docstring claims "atomic submission" but implementation is sequential '_ib
- P1-C1-M05 [MEDIUM]: '_on_error' handles IBKR error 404 with an early return before the 'is_order_rejection' check below
- P1-C1-L02 [LOW]: '_find_trade_by_order_id' does an O(n) scan of all trades in '_ib
- P1-C1-L03 [LOW]: 'OrderResult' constructed with string literal 'status="submitted"' / '"rejected"' instead of 'OrderStatus
- P1-C1-M04 [MEDIUM]: 'BrokerRouter' class is dead code in production
- P1-C1-L04 [LOW]: Imports 'from datetime import
- P1-C1-L01 [LOW]: Tests for dead 'BrokerRouter' class run on every CI cycle
- P1-G2-M04 [MEDIUM]: 'test_emergency_flatten_*' fixtures lack a fill-event publisher — 30s wait comes from 'OrderManagerConfig()' default 'eo

Part of Phase 3 audit remediation. Audit commit: <paste-audit-commit-ref-here>.
Test delta: <baseline> -> <new> (net +N / 0).
COMMIT_EOF
)"
git push origin main
```

## Tier 2 Review (REQUIRED after commit — follows `workflow/claude/skills/review.md`)

After the commit above is pushed, invoke the Tier 2 reviewer in this same
session:

```
@reviewer

Please follow workflow/claude/skills/review.md to review the changes from
this session.

Inputs:
- **Session spec:** the Findings to Fix section of this FIX-NN prompt (FIX-04-execution)
- **Close-out report:** the ---BEGIN-CLOSE-OUT--- block produced before commit
- **Regression checklist:** the 8 campaign-level checks embedded in the close-out
- **Escalation criteria:** trigger ESCALATE verdict if ANY of:
  - any CRITICAL severity finding
  - pytest net delta < 0
  - scope boundary violation (file outside declared Scope modified)
  - different test failure surfaces (not the expected DEF-150 flake)
  - Rule-4 sensitive file touched without authorization
  - audit-report back-annotation missing or incorrect
  - (FIX-01 only) Step 1G fingerprint checkpoint failed before pipeline edits proceeded

Produce the ---BEGIN-REVIEW--- block with verdict CLEAR / CONCERNS /
ESCALATE, followed by the json:structured-verdict JSON appendix. Do NOT
modify any code.
```

The reviewer produces its report in the format specified by review.md
(fenced markdown block, `---BEGIN-REVIEW---` markers, structured JSON
verdict). The operator copies this block into the Work Journal conversation
alongside the close-out.

## Operator Handoff

After both close-out and review reports are produced, display to the operator:

1. **The close-out markdown block** (for Work Journal paste)
2. **The review markdown block** (for Work Journal paste)
3. **A one-line summary:** `Session FIX-04 complete. Close-out: {verdict}. Review: {verdict}. Commits: {SHAs}. Test delta: {baseline} -> {post} (net {±N}).`

The operator pastes (1) and (2) into the Work Journal Claude.ai
conversation. The summary line is for terminal visibility only.

## Definition of Done

- [ ] Every listed finding has been addressed (resolved, verified, or DEF-logged)
- [ ] Full pytest suite net delta >= 0
- [ ] No new pre-existing-failure regressions (DEF-150 flake is the only expected failure)
- [ ] Close-out report produced per `workflow/claude/skills/close-out.md` (`---BEGIN-CLOSE-OUT---` block + `json:structured-closeout` appendix)
- [ ] Self-assessment CLEAN or MINOR_DEVIATIONS (FLAGGED → pause and escalate before commit)
- [ ] Commit pushed to `main` with the exact message format above (unless FLAGGED)
- [ ] Tier 2 `@reviewer` subagent invoked per `workflow/claude/skills/review.md`; `---BEGIN-REVIEW---` block produced
- [ ] Close-out block + review block displayed to operator for Work Journal paste
- [ ] Audit report rows back-annotated with `**RESOLVED FIX-04-execution**`
