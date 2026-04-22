# Audit: Execution
**Session:** P1-C1
**Date:** 2026-04-21
**Scope:** `argus/execution/` — order manager, IBKR/Alpaca/simulated brokers, bracket lifecycle, flatten coordination
**Files examined:** 4 deep / 5 skimmed

Deep-read (full file):
- `argus/execution/order_manager.py` (3,036L)
- `argus/execution/ibkr_broker.py` (1,287L)
- `argus/execution/broker.py` (162L)
- `argus/execution/broker_router.py` (66L)

Skimmed (interface + dead-code scan):
- `argus/execution/alpaca_broker.py` (885L)
- `argus/execution/simulated_broker.py` (796L)
- `argus/execution/execution_record.py` (156L)
- `argus/execution/ibkr_contracts.py` (105L)
- `argus/execution/ibkr_errors.py` (317L)

---

## Q1. Per-Symbol State Dict Inventory (OrderManager)

Enumerated every mutable, per-key container on `OrderManager` with its writer/reader/cleanup story:

| # | Attribute | Key shape | Writers | Readers | Cleanup |
|---|-----------|-----------|---------|---------|---------|
| 1 | `_managed_positions` | `dict[str, list[ManagedPosition]]` | `_handle_entry_fill`, `_reconstruct_known_position`, `_create_reco_position` | `on_tick`, `on_cancel`, `on_fill`, poll loop, reconcile, API | `_close_position` removes entry; `reset_daily_state` clears all |
| 2 | `_pending_orders` | `dict[str, PendingManagedOrder]` keyed by `order_id` | `on_approved`, `_submit_stop_order`, `_submit_t1_order`, `_submit_t2_order`, `_reconstruct_known_position`, `_flatten_position`, `_trail_flatten`, `_flatten_unknown_position`, `_check_flatten_pending_timeouts` | `on_fill`, `on_cancel`, `_handle_flatten_fill` (stale scan), `_amend_bracket_on_slippage` | Popped in `on_fill`/`on_cancel`/cancel paths; `reset_daily_state` clears |
| 3 | `_flatten_pending` | `dict[str, tuple[order_id, monotonic_t, retry_count]]` | `_flatten_position`, `_trail_flatten`, `_check_flatten_pending_timeouts` | `on_cancel`, `_handle_stop_fill`, `on_tick` suppress, poll loop, `_flatten_position` guard, `_trail_flatten` guard | `_close_position`, `on_cancel` (flatten), timeout path, `reset_daily_state` |
| 4 | `_broker_confirmed` | `dict[str, bool]` | `_handle_entry_fill` | `reconcile_positions` | `_close_position` pops when last position closes; `reset_daily_state` clears |
| 5 | `_reconciliation_miss_count` | `dict[str, int]` | `reconcile_positions` | `reconcile_positions` | `_close_position` pops; `reset_daily_state` clears |
| 6 | `_stop_retry_count` | `dict[str, int]` | `_resubmit_stop_with_retry` | `_resubmit_stop_with_retry` | `_close_position` pops; `reset_daily_state` clears |
| 7 | `_amended_prices` | `dict[str, tuple[stop, t1, t2]]` | `_amend_bracket_on_slippage` | `_handle_revision_rejected` | `_close_position` pops; `reset_daily_state` clears |
| 8 | `_flatten_cycle_count` | `dict[str, int]` | `_check_flatten_pending_timeouts` | `_check_flatten_pending_timeouts` | `eod_flatten` clears; **NOT** cleared in `reset_daily_state` (intentional: EOD is canonical reset point) |
| 9 | `_flatten_abandoned` | `set[str]` | `_check_flatten_pending_timeouts` | `_flatten_position`, poll loop, `eod_flatten` | `eod_flatten` clears; **NOT** cleared in `reset_daily_state` |
| 10 | `_startup_flatten_queue` | `list[tuple[symbol, qty]]` | `_flatten_unknown_position` | `_drain_startup_flatten_queue` | `_drain_startup_flatten_queue` clears all; **NOT** cleared in `reset_daily_state` |
| 11 | `_last_fill_state` | `dict[order_id, cumulative_qty]` | `on_fill` (dedup) | `on_fill` | `_close_position` via reverse index; `reset_daily_state` clears |
| 12 | `_fill_order_ids_by_symbol` | `dict[symbol, set[order_id]]` | `on_fill` | `_close_position` | `_close_position` pops; `reset_daily_state` clears |
| 13 | `_pnl_last_published` | `dict[symbol, monotonic_t]` | `_publish_position_pnl` | `_publish_position_pnl` | `_flatten_position` pops; **NOT** cleared in `reset_daily_state` (harmless — keys are symbols; stale monotonic timestamps cause max one extra suppression) |
| 14 | `_fingerprint_registry` | `dict[strategy_id, fingerprint]` | `register_strategy_fingerprint` | `_close_position` (trade logging) | **NEVER** cleared — intentional (session-persistent after boot) |
| 15 | `_eod_flatten_events` | `dict[symbol, asyncio.Event]` | `eod_flatten` | `_close_position`, `on_cancel` signal | Reassigned to `{}` at end of `eod_flatten`; **NOT** cleared in `reset_daily_state` |
| 16 | `_exit_config_cache` | `dict[strategy_id, ExitManagementConfig]` | `_get_exit_config` | `_get_exit_config` | **NEVER** cleared — intentional (config is session-immutable) |
| 17 | `_margin_rejection_count` / `_margin_circuit_open` | scalars | `on_cancel` (rejection path) | `on_approved`, poll loop | `reset_daily_state` resets both; poll loop auto-resets on position count < threshold |

### 1.2 Concurrent-mutation risk
All handlers run on a single asyncio loop; no shared-state race is possible across handlers without an `await`. Within handlers, the `_flatten_pending` dict is the most heavily contested and is consistently guarded by monotonic-timestamp tuples. No lock primitives used, and none appear necessary given the single-loop discipline.

### 1.3 `_last_fill_state` dedup correctness
Dedup at [order_manager.py:586-595](argus/execution/order_manager.py#L586-L595) compares cumulative filled qty. This is correct for:
- IBKR partial fills (each reports cumulative qty; dedup catches redundant callbacks with same cumulative).
- SimulatedBroker synchronous fill (first call sets; no second call would normally occur).

Subtle case: if a stop order fires twice at IBKR (cancel race), the second cumulative qty equals first → dedup correctly drops it. Contract holds.

---

## Q2. Flatten Path Coordination Map

Every site that can submit a SELL order to close a position, and its coordination posture:

| # | Path | Function | Guards `_flatten_pending`? | Queries broker qty before SELL? | Cancels concurrent orders? |
|---|------|----------|---------------------------|------------------------------|---------------------------|
| 1 | Normal exit via `_flatten_position` | [L2538-L2631](argus/execution/order_manager.py#L2538-L2631) | **Yes** (L2556) | No | Cancels stop/T1/T2 before SELL |
| 2 | Trail stop | `_trail_flatten` [L2369-L2468](argus/execution/order_manager.py#L2369-L2468) | **Yes** (L2389) | No | SELL first, then cancel stop/T1/T2 (AMD-2 order) |
| 3 | Time stop (poll loop) | calls `_flatten_position` [L1524,1547](argus/execution/order_manager.py#L1524) | Inherits guard | No | Inherits |
| 4 | Bracket-exhaustion on cancel | `on_cancel → _flatten_position` [L702](argus/execution/order_manager.py#L702) | Inherits guard | No | Inherits |
| 5 | Stop retry exhausted | `_flatten_position` [L805](argus/execution/order_manager.py#L805) | Inherits guard | No | Inherits |
| 6 | Stop submission failure | `_flatten_position` [L2159](argus/execution/order_manager.py#L2159) | Inherits guard | No | Inherits |
| 7 | Escalation failure | `_flatten_position` [L2536](argus/execution/order_manager.py#L2536) | Inherits guard | No | Inherits |
| 8 | Bracket-amendment safety | `_flatten_position` [L1115](argus/execution/order_manager.py#L1115) | Inherits guard | No | Inherits |
| 9 | API close | `close_position → _flatten_position` [L1740-L1759](argus/execution/order_manager.py#L1740-L1759) | Inherits guard | No | Inherits |
| 10 | Circuit breaker | `emergency_flatten → eod_flatten → _flatten_position` | Cleared before flatten (L1615) | No | Inherits |
| 11 | EOD flatten Pass 1 | `eod_flatten → _flatten_position` [L1619-L1625](argus/execution/order_manager.py#L1619-L1625) | Abandoned set cleared L1615 | No | Inherits |
| 12 | EOD Pass 2 (broker-only) | `_flatten_unknown_position(force_execute=True)` [L1693](argus/execution/order_manager.py#L1693) | **No guard** | No (broker qty is input) | **Yes** — cancels open orders for symbol (L1911-L1931) |
| 13 | EOD timeout retry | `_flatten_unknown_position(force_execute=True)` [L1668](argus/execution/order_manager.py#L1668) | No guard | Yes — uses retried broker qty map | Inherits |
| 14 | Flatten-pending timeout resubmit | `_check_flatten_pending_timeouts` [L2333-L2367](argus/execution/order_manager.py#L2333-L2367) | Re-populates itself | **Yes** (DEF-158, L2301-L2324) | Cancels stale order |
| 15 | Startup zombie (live market) | `_flatten_unknown_position(force_execute=False)` [L1933-L1953](argus/execution/order_manager.py#L1933-L1953) | No guard | No | **Yes** — cancels open orders for symbol |
| 16 | Startup zombie (queued) | `_drain_startup_flatten_queue` [L1955-L1989](argus/execution/order_manager.py#L1955-L1989) | No guard | No | **No** — ⚠ **see finding M-02** |
| 17 | Reconciliation cleanup | `_close_position(RECONCILIATION)` [L2988,L3014](argus/execution/order_manager.py#L2988) | No SELL — zero-out bookkeeping | N/A | N/A |

### 2.2 Stop-fill cancels concurrent flatten (Sprint 31.8 S3 lesson)
`_handle_stop_fill` [L1329-L1344](argus/execution/order_manager.py#L1329-L1344) cancels the `_flatten_pending` order for the symbol before closing. `_handle_flatten_fill` [L1407-L1424](argus/execution/order_manager.py#L1407-L1424) scans `_pending_orders` for any other `flatten` order on the symbol and cancels it. **Both DEF-158 guards present and correct.**

### 2.3 Startup cleanup cancels bracket before flatten
`_flatten_unknown_position` with `force_execute` or live-market path cancels residual bracket orders before placing SELL (L1911-L1931). **Present and correct for the direct path.** Gap in the queued/drain path — see M-02.

---

## Q3. `getattr(pos, "qty")` / `.qty` Regression Scan

Grep across `argus/execution/`:

| Call site | Object | Attribute | Verdict |
|-----------|--------|-----------|---------|
| `order_manager.py:1657` | Position (broker return) | `shares` | ✅ Correct |
| `order_manager.py:1684` | Position (broker return) | `shares` | ✅ Correct |
| `order_manager.py:1830` | Position (broker return) | `shares` | ✅ Correct |
| `order_manager.py:2038` | Position (broker return) | `shares` | ✅ Correct |
| `order_manager.py:2004` | Position (broker return) | `avg_entry_price` | ❌ **C-01** — `Position` model uses `entry_price` |
| `order_manager.py:2039` | Position (broker return) | `avg_entry_price` | ❌ **C-01** — same |
| `order_manager.py:2061` | Order (broker return) | `qty` | ❌ **C-02** — `Order` model uses `quantity` |
| `order_manager.py:2306` | Position (broker return) | `shares` | ✅ Correct |
| `alpaca_broker.py:211,608,609,748` | Alpaca-native objects | `qty` | ✅ Correct (alpaca-py SDK contract) |

**Summary:** Two new latent instances of the DEF-139/140-class bug in the reconstruction path. Details in finding C-01 and C-02. Attribute-level mismatches in the reconstruction functions mean reconstructed positions are created with `entry_price=0.0` and `t1_shares=0`, producing severely wrong live P&L and breaking T1 partial-exit logic after a mid-session restart.

---

## Q4. IBKR Broker — Error Handling

- **Error codes documented:** `ibkr_errors.py` has a 30-entry `IBKR_ERROR_MAP` with severity (CRITICAL/WARNING/INFO), category, and recommended action. 201 (margin rejection) is classified WARNING with action `reject_order`; 404 (qty hold on SELL) is WARNING with action `verify_state`.
- **Reconnection logic (Sprint 32.75):** `_reconnect` [L425-L511](argus/execution/ibkr_broker.py#L425-L511) implements exponential backoff, 3s post-connect settle sleep, and the "re-query positions after 2s if first returned 0" retry-once pattern. **Present and correct.**
- **`reqGlobalCancel()`:** Called from `cancel_all_orders` [L1047](argus/execution/ibkr_broker.py#L1047) and `flatten_all` [L1072](argus/execution/ibkr_broker.py#L1072). `cancel_all_orders` wired into shutdown at [main.py:2325](argus/main.py#L2325) before order manager stop.
- **`except Exception`:** Swept the file — all blanket handlers in `_handle_order_status`/`_on_error` are leaf handlers that log and continue; no IBKR-specific exceptions are swallowed silently. `_on_error` classifies by code, not by exception type, which is appropriate for ib_async's signal-style error delivery.

---

## Q5. Alpaca & Simulated Broker Liveness (PF-07)

### 5.1 `AlpacaBroker` reachability — **DEFINITIVE ANSWER**

**Status:** Reachable in code, **unreachable in current configuration**.

Call chain:
1. `argus/main.py:94` — `from argus.execution.alpaca_broker import AlpacaBroker` (**unconditional module-level import**).
2. `argus/main.py:252-257` — instantiated only when `config.system.broker_source == BrokerSource.ALPACA`.
3. `BrokerSource.ALPACA` still exists in `argus/core/config.py:370`.
4. **No YAML config currently sets `broker_source: alpaca`:**
   - `config/system.yaml` → `simulated`
   - `config/system_live.yaml` → `ibkr`
5. DEC-086 demoted Alpaca to incubator-only; architecture docs still reference it as "paper testing only".

**Verdict:** Code path is dormant. Dead in practice but reachable via a YAML edit. **Not runtime-dead.** See findings M-03 (lazy-import inconsistency) and L-01 (dead Alpaca tests still run on every CI cycle).

### 5.2 `SimulatedBroker` usage
Used in 5 locations:
- `argus/main.py` (`BrokerSource.SIMULATED`)
- `argus/backtest/engine.py` (production BacktestEngine)
- `argus/backtest/replay_harness.py`
- `argus/backtest/config.py`
- `argus/api/dev_state.py` (`--dev` mode)

Broader than just backtest — correctly scoped to `argus/execution/`. **No relocation warranted.**

### 5.3 `broker_router.py` — **DEAD CODE**
`BrokerRouter` class has no production caller. Grep of `argus/` finds only the class definition in `broker_router.py` itself. A test file exists (`tests/execution/test_broker_router.py`). `main.py` selects broker directly via `if/elif` on `broker_source`; no routing abstraction is used. This is unused Sprint 2 scaffolding. See finding M-04.

---

## Q6. Config-Gating Patterns

- **`reconciliation.auto_cleanup_unconfirmed`** — [L2970](argus/execution/order_manager.py#L2970) default False; requires `consecutive_miss_threshold` streak before any close. Legacy `auto_cleanup_orphans` also honored [L3001](argus/execution/order_manager.py#L3001) for backwards compat. **Pattern consistent.**
- **`overflow.enabled`/`broker_capacity`** — not read in `order_manager.py` directly. Overflow routing lives upstream in `_process_signal` (main.py). Out of scope for this audit; P1-A1 owns it.
- **`max_concurrent_positions`** — not read in `order_manager.py`. Same — upstream in Risk Manager.
- **`startup.flatten_unknown_positions`** — [L1839](argus/execution/order_manager.py#L1839) respected. When False, creates RECO entry instead of flatten. Correct.
- **`eod_flatten_retry_rejected`** — [L1653](argus/execution/order_manager.py#L1653) gates the timeout-retry Pass 1b. Default True.
- **`margin_rejection_threshold`/`margin_circuit_reset_positions`** — [L662,L1472](argus/execution/order_manager.py#L662) wired. Gated reasonably.
- **`auto_shutdown_after_eod`** — [L1719](argus/execution/order_manager.py#L1719) respected. Moved post-verification in Sprint 32.9.

---

## Q7. Logging & Throttling

`ThrottledLogger` used at 7 sites across the module:

| File:Line | Message | Interval | Justification |
|-----------|---------|----------|---------------|
| `ibkr_broker.py:321` | IBKR error 399 per-symbol | 60s | Paper-trading repricing storm (DEF-100) |
| `ibkr_broker.py:329` | IBKR error 202 per-orderId | 86400s | One-per-order cap |
| `ibkr_broker.py:337` | IBKR error 10148 per-orderId | 86400s | Same |
| `order_manager.py:1509` | Time stop (flatten pending) | 60s | Per-symbol log-spam defense |
| `order_manager.py:1531` | Time stop global (flatten pending) | 60s | Same |
| `order_manager.py:2558` | "Flatten already pending" | 60s | Sprint 28.75 (DEF-113) |
| `order_manager.py:2960` | "IBKR snapshot missing confirmed" | 600s | Sprint 28.75 (DEF-114) |

Intervals are reasonable. No obvious unthrottled high-volume path — poll loop at `fallback_poll_interval_seconds` (default 5s) produces per-symbol INFO log at each time-stop-checked branch only when `_suppress_log` is False (i.e., not yet pending), bounding volume. P&L publishes are throttled to 1/sec/symbol.

**One sub-optimal pattern:** `logger.debug("Could not cancel ...")` is scattered in `_flatten_position`/`_trail_flatten`/`_handle_*_fill` paths where cancel exceptions are routinely swallowed. DEBUG level is fine; no throttling needed.

---

## Q8. `_fingerprint_registry` (Sprint 32)

- **Registration site:** `register_strategy_fingerprint()` [L317-L330](argus/execution/order_manager.py#L317-L330). Called from main.py startup after pattern strategies are constructed. Non-pattern strategies are intentionally absent (trades get `None` fingerprint).
- **Read site:** `_close_position` [L2696](argus/execution/order_manager.py#L2696) — `self._fingerprint_registry.get(position.strategy_id)`. Safe default to None.
- **Persistence:** Written to `Trade.config_fingerprint` [L2716](argus/execution/order_manager.py#L2716) and flows to the trades DB column.
- **Race window:** Registration happens in startup Phase 9.5 (before strategy wiring). First trade close cannot occur before Phase 9.5 completes because Phase 3 (broker) + Phase 8 (order manager) finish before strategies can emit signals. **No race observable.**

---

## Q9. PF-07 (Pre-flagged)
Answered in Q5.1. **Alpaca code is reachable via YAML but not active in any shipped config.** Recommend keeping enum + broker for incubator-testing optionality, but tightening the import pattern (M-03) and confirming via a config-level guard in `main.py` that Alpaca cannot be selected in a "live" run.

---

## CRITICAL Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| C-01 | [order_manager.py:2004](argus/execution/order_manager.py#L2004), [order_manager.py:2039](argus/execution/order_manager.py#L2039) | `_create_reco_position` and `_reconstruct_known_position` read `getattr(pos, "avg_entry_price", 0.0)` but `argus.models.trading.Position` uses field name `entry_price`. The getattr silently returns `0.0`. | After any mid-day restart with open positions, reconstructed `ManagedPosition` objects carry `entry_price=0.0`. This corrupts: (a) live P&L in `_publish_position_pnl` — `(price − 0) × shares` = massively inflated unrealized P&L broadcast to UI; (b) `_handle_t1_fill` realized P&L — `(t1_price − 0) × qty` writes a huge fake "win" to trades DB; (c) MFE/MAE R-multiples divided by a risk computed against `entry_price=0`. DEF-159's `entry_price_known` guard saves the trade record but does **not** protect runtime telemetry or partial-exit accumulation. Same regression class as DEF-139/140 (`qty` vs `shares`). | Change both sites to `getattr(pos, "entry_price", 0.0)`. Add a regression test that drives `reconstruct_from_broker` through `SimulatedBroker` with a pre-seeded position and asserts `managed.entry_price == broker_entry`. Consider deleting `getattr` and directly accessing `pos.entry_price` now that the Broker ABC contractually returns `Position`. | **weekend-only** |
| C-02 | [order_manager.py:2061](argus/execution/order_manager.py#L2061) | `_reconstruct_known_position` reads `getattr(order, "qty", 0)` but `argus.models.trading.Order` uses field name `quantity`. The getattr silently returns `0`. | Reconstructed positions set `t1_shares = 0`. Combined with `t1_filled = (t1_order_id is None and t1_shares == 0)` at L2077, a live T1 bracket order is paired with `t1_shares=0` and `t1_filled=False` — inconsistent state. On T1 fill, `position.t1_shares=0` breaks downstream calculations in `_handle_t1_fill` (the check `if t1_shares == 0 and share_count > 0: t1_shares = 1` does not apply post-reconstruction). | Change to `getattr(order, "quantity", 0)` — or delete the `getattr` and use `order.quantity` directly, since the Broker ABC contractually returns `Order`. Add same-shape regression test. | **weekend-only** |

## MEDIUM Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| M-01 | [ibkr_broker.py:638-770](argus/execution/ibkr_broker.py#L638-L770) | `place_bracket_order` docstring claims "atomic submission" but implementation is sequential `_ib.placeOrder()` calls (parent, stop, each target). If an exception raises between the parent and stop submission (e.g., Pydantic validation, network blip), the parent is left at IBKR in `PendingSubmit` with `transmit=False` — an orphan that will never transmit but occupies an order slot. No rollback path. | Low probability in practice (ib_async calls don't await between these points) but the safety claim in the docstring is misleading. A crash between parent submit and stop submit during a live run would leave an untransmitted parent order. | (a) Wrap the body in try/except and call `_ib.cancelOrder(parent)` on failure before re-raising. (b) Soften the docstring to reflect actual behavior. Fix (a) is the real hardening; (b) alone is insufficient. | **weekend-only** |
| M-02 | [order_manager.py:1955-1989](argus/execution/order_manager.py#L1955-L1989) | `_drain_startup_flatten_queue` submits market-sell orders at 9:30 ET market-open **without** cancelling pre-existing bracket orders for the symbol. By contrast, the direct path `_flatten_unknown_position(force_execute=True)` and EOD Pass 2 cancel bracket orders first (DEF-158 fix at L1911-L1931). If zombie positions carry residual stop/T1 orders from a prior session, those orders can fire between market-open and the drain call, producing a double-SELL (short-selling risk). | Same class as DEF-158 but in the queued-zombie path. Probability is a function of how often ARGUS boots pre-market with both zombie positions **and** orphan bracket orders at IBKR; currently rare (EOD flatten usually clears brackets), but the risk mode is identical to the three DEF-158 root causes resolved in Sprint 31.8 S3. | Move the bracket-cancel loop (currently at L1911-L1931) into a shared helper and call it from `_drain_startup_flatten_queue` before each `place_order`. Add a test that seeds open orders for a queued zombie and asserts they're cancelled before the queued SELL fires. | **weekend-only** |
| M-03 | [main.py:94](argus/main.py#L94) | `from argus.execution.alpaca_broker import AlpacaBroker` is an **unconditional module-top import**, while `IBKRBroker` and `SimulatedBroker` are lazy-imported inside the `broker_source` branches at L245 and L260. Inconsistent pattern, and forces `alpaca-py>=0.30` to be installed on every deployment even when the broker is IBKR. | Deployment weight (minor). Also an undocumented dependency contract — if alpaca-py ever has a breaking release, IBKR-only deploys will crash at startup even though they don't use Alpaca. | Move the Alpaca import inside its `elif` branch matching the pattern of IBKR/Simulated. Optional follow-on: add a `main.py` assertion that `BrokerSource.ALPACA` cannot be combined with `config/system_live.yaml` (reinforces DEC-086's "incubator only"). | **safe-during-trading** (import-site change, no runtime path affected) |
| M-04 | [broker_router.py](argus/execution/broker_router.py) | `BrokerRouter` class is **dead code in production.** No file in `argus/` imports it (verified by grep); only `tests/execution/test_broker_router.py` references it. `main.py` selects a broker via `if/elif` on `broker_source` without any routing abstraction. This is legacy Sprint 2 scaffolding. | Maintenance cost: every future broker-selection change must remember this file doesn't need updating. Test suite runs tests for an unused class. Architecture doc [architecture.md:315](docs/architecture.md#L315) still describes the pattern as active. | Either (a) delete `broker_router.py` + its test file + the architecture.md section, or (b) wire it into `main.py` and delete the `if/elif` block. (a) is the right call — multi-broker routing is not on the near roadmap and the if/elif is simpler. | **safe-during-trading** (no runtime change) |
| M-05 | [ibkr_broker.py:344-355](argus/execution/ibkr_broker.py#L344-L355) | `_on_error` handles IBKR error 404 with an **early return** before the `is_order_rejection` check below. 404 adds the symbol to `error_404_symbols` but does **not** publish `OrderCancelledEvent`. Relies entirely on IBKR subsequently firing an `orderStatusEvent(status="Cancelled")` to wake up OrderManager. | If IBKR's cancel status message is delayed or dropped, the `PendingManagedOrder` entry stays in `_pending_orders` indefinitely, eventually producing a phantom pending-entry exposure counted by `get_pending_entry_exposure()`. A robust contract should not depend on two separate IBKR messages (error + status) both arriving. | Remove the early return on L355; let 404 fall through to the shared `is_order_rejection` branch which publishes `OrderCancelledEvent(reason="IBKR 404: ...")`. The Order Manager's `on_cancel` path already handles flatten-pending cleanup correctly. | **weekend-only** |
| M-06 | [order_manager.py:2068](argus/execution/order_manager.py#L2068) | `_reconstruct_known_position` sets `entry_time=self._clock.now()` on reconstructed positions. Time-stop arithmetic in the poll loop computes `elapsed_seconds = (now - position.entry_time)` — which always starts at zero post-restart. | Per-position `time_stop_seconds` on reconstructed positions is `None` (not set by reconstruction), so DEC-122 path is skipped. But the fallback `max_position_duration_minutes` (default 240min) is measured from **restart time**, not from actual entry time. On a mid-day restart 15 minutes before the original time-stop would have fired, the position now has a fresh 240-minute lease. Bounded by EOD flatten but degrades time-stop semantics after any reconnect. | (a) Persist `entry_time` in the trades DB live-positions sidecar and restore it on reconstruction, or (b) conservatively set `entry_time = self._clock.now() - timedelta(minutes=config.max_position_duration_minutes // 2)` to bias toward earlier time-stop firing. (a) is the correct fix; (b) is a stopgap. | **weekend-only** |

## LOW Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| L-01 | `tests/execution/test_broker_router.py` (exists but not audited in full — referenced from M-04) | Tests for dead `BrokerRouter` class run on every CI cycle. Also the Alpaca broker has a full test suite (`tests/execution/test_alpaca_broker.py`, ~30 tests per earlier sprint history) exercising a code path not active in any shipped config. | CI seconds spent, maintenance pinning on alpaca-py SDK changes. Not user-facing. | Deferred to DEF triage (P1-H4). If M-04 removes `broker_router.py`, the test file goes with it. | **deferred-to-defs** |
| L-02 | [ibkr_broker.py:1231-1246](argus/execution/ibkr_broker.py#L1231-L1246) | `_find_trade_by_order_id` does an O(n) scan of all trades in `_ib.trades()` on every `cancel_order` / `modify_order` / `get_order_status` call. For a session with hundreds of bracket legs, this is small but unbounded. | Not performance-critical at current volumes (<100 active brackets). Scales linearly with session length. | Maintain a parallel `dict[int, Trade]` indexed by `orderId`, populated in `_on_order_status`. Drop stale entries on Cancelled/Filled. | **weekend-only** |
| L-03 | [ibkr_broker.py:598-602,L633-L636,L695-L697](argus/execution/ibkr_broker.py#L598-L602) (multiple sites) | `OrderResult` constructed with string literal `status="submitted"` / `"rejected"` instead of `OrderStatus.SUBMITTED` / `OrderStatus.REJECTED` enum values. Pydantic coerces but the pattern is inconsistent with the rest of the codebase which uses enum access. | Cosmetic; readers/linters cannot verify the valid status set. | Replace with enum references. | **safe-during-trading** |
| L-04 | [execution_record.py:10-15](argus/execution/execution_record.py#L10-L15) | Imports `from datetime import ..., timezone` and separately uses `timezone.utc` at L113 instead of the project-standard `datetime.UTC` (Python 3.11+) used elsewhere. Also `_ET = ZoneInfo(...)` is defined between imports — violates CLAUDE.md "all imports at top" rule. | Style inconsistency. No functional impact. | Use `datetime.UTC` throughout; move `_ET` below all imports. | **safe-during-trading** |
| L-05 | [order_manager.py:1441-1452](argus/execution/order_manager.py#L1441-L1452) | `_flattened_today` set to True inside `eod_flatten()` [L1605](argus/execution/order_manager.py#L1605) **and** by the poll loop after the call [L1451](argus/execution/order_manager.py#L1451). Redundant — the second write is unreachable because `eod_flatten` already set it. | Harmless double-write. | Delete the redundant poll-loop assignment. | **safe-during-trading** |
| L-06 | [order_manager.py:1454-1465](argus/execution/order_manager.py#L1454-L1465) | `_poll_loop` computes `et_tz2 = ZoneInfo("America/New_York")` and `now_et2` inline inside the startup-queue drain block because `et_tz`/`now_et` from the EOD-flatten block above may not be in scope. The "2" suffix is a workaround for a structural issue — both blocks convert `now` to ET independently. | Duplicate work per poll tick. | Lift ET conversion to a single helper `_now_et()` and call once at the top of the loop body. | **safe-during-trading** |
| L-07 | [order_manager.py:2741-L2748](argus/execution/order_manager.py#L2741-L2748) | `_close_position` pops `_reconciliation_miss_count[symbol]`, `_stop_retry_count[symbol]`, `_amended_prices[symbol]` — which are also cleared wholesale in `reset_daily_state`. Double cleanup; harmless but signals intent confusion. | None. | Leave as-is (defense in depth) or document as intentional. | **safe-during-trading** |
| L-08 | [order_manager.py:1376-L1389](argus/execution/order_manager.py#L1376-L1389) | `_handle_flatten_fill` has a strategy_id match path and a "fall back to first open position" path with a WARNING log. The fallback exists for backward-compat with positions that were opened before strategy_id was tracked on `PendingManagedOrder`. With 89 sprints shipped, this legacy shape likely no longer exists. | Dead fallback path; could be promoted to a hard error to catch bugs earlier. | Replace the `if position is None` fallback with `logger.error(...)` and return, tightening the invariant. Run full suite afterward to confirm. | **weekend-only** |
| L-09 | [order_manager.py:112-116](argus/execution/order_manager.py#L112-L116) | `ManagedPosition.mfe_time` / `mae_time` defaulted to `None`, then set inside `on_tick` at L725 / L731. However the MFE/MAE R-multiples are only computed when price changes — the first tick after fill where `event.price == entry_price` leaves `mfe_time=None`. On an instant-reversal position, `mfe_time` may stay None forever. | Cosmetic — downstream handling of None is not audited here but may show as "null" in analytics. | Initialize `mfe_time = entry_time` in `_handle_entry_fill` (mirroring `mfe_price = entry_price`). | **safe-during-trading** |
| L-10 | [order_manager.py:188](argus/execution/order_manager.py#L188) | Constructor parameter `auto_cleanup_orphans` is documented "Deprecated — use reconciliation_config.auto_cleanup_orphans instead" but still accepted and still honored [L3001](argus/execution/order_manager.py#L3001). | Compatibility shim; no users identified. | Grep all callers; if none pass the deprecated arg, remove the parameter. | **weekend-only** |

## COSMETIC Findings

| # | File:Line | Finding | Impact | Suggested Fix | Safety |
|---|-----------|---------|--------|---------------|--------|
| X-01 | [order_manager.py:56](argus/execution/order_manager.py#L56) | Two imports from `argus.models.trading`: one on L58 importing `Order`, `OrderSide`, `OrderStatus`, another on L60 importing `OrderType as TradingOrderType`. Split into two statements; should be combined. | Minor style. | Single import block. | **safe-during-trading** |
| X-02 | [order_manager.py:1500-L1503](argus/execution/order_manager.py#L1500-L1503) | Variable `_suppress_log` uses leading underscore but is a local, not a private attribute. Convention mismatch. | Minor style. | Rename to `suppress_log`. | **safe-during-trading** |
| X-03 | [order_manager.py:996-L997](argus/execution/order_manager.py#L996-L997) | Comment "NOTE: No `_submit_stop_order`, `_submit_t1_order`, `_submit_t2_order` calls." — CLAUDE.md guidance: don't explain what the code does not do. | Minor style. | Delete. | **safe-during-trading** |
| X-04 | [ibkr_broker.py:861-L867](argus/execution/ibkr_broker.py#L861-L867) | `get_positions` contains local `from ... import` statements — deferred imports inside a frequently-called method. All are already imported at module top via other paths (`Position`) or are cheap (`AssetClass`, `PositionStatus`). | Overhead is negligible but the pattern is inconsistent — module-top imports would match the rest of the file. | Move to module top. | **safe-during-trading** |

---

## Positive Observations

1. **DEF-158 coverage is genuinely thorough.** The three root-cause fixes from Sprint 31.8 S3 (concurrent flatten cancel in `_handle_stop_fill`, stale flatten cancel in `_handle_flatten_fill`, broker-qty re-query in timeout resubmit) are all present, well-commented, and consistently reference the defect. The extension to `_flatten_unknown_position` (cancel pre-existing orders before flatten) shows the team learned the general pattern, not just the specific cases. M-02 is the remaining gap, but 4/5 paths are hardened.

2. **Atomic bracket order via IBKR transmit-flag pattern** (`place_bracket_order` L650-L770) correctly uses `transmit=False` until the last child — this is the IBKR-native way to get server-side atomic submission. The implementation detail is nuanced and matches ib_async best practices. (The caveat in M-01 is about exception handling between calls, not the transmit pattern itself.)

3. **`_fingerprint_registry` design is clean.** Registration is explicit (no hidden auto-discovery), non-PatternModule strategies naturally produce `None`, and the read path in `_close_position` is a single `.get()` with correct default. Session-persistent (correctly not cleared in `reset_daily_state`). A minimal, well-scoped addition to a complex class.

4. **Margin circuit breaker is well-sequenced.** Open condition [L661](argus/execution/order_manager.py#L661) (rejection count ≥ threshold), reset condition [L1472](argus/execution/order_manager.py#L1472) (position count < reset threshold), and integration at the entry gate [L475-L492](argus/execution/order_manager.py#L475-L492) all hang together. Publishes `SignalRejectedEvent` into the counterfactual tracker so blocked signals are still visible.

5. **`ThrottledLogger` is applied only where demonstrably needed** — IBKR 399 repricing storm, "flatten pending" spam, "portfolio snapshot missing" — with justifications tied to specific past incidents (DEF-100, DEF-113, DEF-114). Intervals (60s per symbol for operational log, 600s for recon, 86400s for one-per-order ids) are well-chosen.

6. **Broker ABC contract is cleanly minimal.** 11 abstract methods in `broker.py`, all async, all returning Pydantic models. Clear separation of lifecycle (`connect`/`disconnect`), order ops (place/cancel/modify), queries (`get_positions`/`get_account`/`get_open_orders`), and emergency (`flatten_all`/`cancel_all_orders`). Three adapters implement the same surface cleanly.

7. **EOD verification tier** (post-flatten `get_positions()` check at [L1706-L1716](argus/execution/order_manager.py#L1706-L1716) logging CRITICAL on any residual) is a strong safety belt — catches the "both passes ran but positions still exist" failure mode. Added in Sprint 32.9 in response to zombie positions going undetected.

8. **`eod_flatten_events` fill-verification pattern** using per-symbol `asyncio.Event` + `asyncio.gather` + `asyncio.wait_for` (L1629-L1650) is the correct asyncio idiom. Previously fire-and-forget; now the EOD barrier actually waits for confirmations before moving to Pass 2. This is the pattern to replicate for any future "submit N orders and wait for all to resolve" surface.

---

## Statistics

- Files deep-read: 4 (order_manager.py, ibkr_broker.py, broker.py, broker_router.py)
- Files skimmed: 5 (alpaca_broker.py, simulated_broker.py, execution_record.py, ibkr_contracts.py, ibkr_errors.py)
- Total lines examined: 4,654 deep / 2,159 skimmed = 6,813 LOC
- Total findings: 22 (2 critical, 6 medium, 10 low, 4 cosmetic)
- Safety distribution: 11 safe-during-trading / 10 weekend-only / 0 read-only-no-fix-needed / 1 deferred-to-defs
- Estimated Phase 3 fix effort: 3-4 sessions
  - **Session 1 (weekend-only, CRITICAL):** C-01 + C-02 bundled — both are attribute-name fixes in the same reconstruction path (`_reconstruct_known_position` / `_create_reco_position`). Single focused session with a dedicated regression test. +3-5 pytest.
  - **Session 2 (weekend-only, MEDIUM):** M-02 (drain bracket cancel) + M-05 (IBKR 404 publish OrderCancelledEvent) + M-01 (bracket rollback). Three related safety-net tightenings; all touch the flatten/order-lifecycle surface. +5-8 pytest.
  - **Session 3 (safe-during-trading):** M-03 (lazy Alpaca import) + M-04 (delete BrokerRouter) + L-03/L-04/L-05/L-06/L-07/L-09 and cosmetic cleanup. Zero-risk stylistic pass. Drops 1 dead test file, net pytest count preserved.
  - **Session 4 (weekend-only, MEDIUM):** M-06 (reconstruction entry_time) — needs a small DB schema addition (live positions sidecar). Large enough to warrant its own session. +4-6 pytest.

### Cleanup Tracker Cross-Reference
No items from the Sprint 31.75 cleanup tracker fall in this scope (items 1-3 are in backtest/engine.py and scripts/; item 4 is in tests/).

---

## FIX-03 Resolution (2026-04-21)

- **M-03** ~~`from argus.execution.alpaca_broker import AlpacaBroker` unconditional at module top~~ → **RESOLVED FIX-03-main-py**. Import moved inside the `elif config.system.broker_source == BrokerSource.ALPACA` branch in `argus/main.py`, matching the lazy-import pattern used for IBKR and Simulated. 15 `patch("argus.main.AlpacaBroker", ...)` sites in `tests/test_main.py` repointed to `patch("argus.execution.alpaca_broker.AlpacaBroker", ...)`. See the full FIX-03 resolution section in `p1-a1-main-py.md` for context.

Remaining P1-C1 findings (M-04 BrokerRouter delete, M-05 IBKR 404, M-06 reconstruction entry_time, M-01 bracket rollback, L-01..L-09, etc.) unchanged — those live in `argus/execution/` and are FIX-04's scope.

---

## FIX-04 Resolution (2026-04-22)

All P1-C1 findings addressed. Also resolves cross-domain P1-D1-M03 (deferred — DEF-177) and P1-G2-M04 (test wall-clock).

| # | Status | Summary |
|---|--------|---------|
| C-01 | **RESOLVED** | `avg_entry_price` → `entry_price` at `order_manager.py:2004` + `:2039`. Both reconstruction paths (`_create_reco_position`, `_reconstruct_known_position`) now read the correct `Position.entry_price` field. +2 regression tests using real `Position` models (not `MagicMock`) to prevent the field-name drift from recurring; tests verified to FAIL when the fix is reverted (gold-standard proof). |
| C-02 | **RESOLVED** | `qty` → `quantity` at `order_manager.py:2061`. `t1_shares` on a reconstructed position now carries the live T1 order's quantity instead of silently defaulting to 0. +1 regression test using real `Order` model. |
| M-01 | **RESOLVED** | `place_bracket_order` body wrapped in try/except; on any child-leg failure the parent is cancelled via `_ib.cancelOrder(parent_trade.order)` before the exception propagates, preventing a `PendingSubmit`/`transmit=False` orphan at IBKR. Docstring softened from "atomic" to "rollback-protected, sequential submission with transmit-flag activation". |
| M-02 | **RESOLVED** | Bracket-cancel loop extracted into `_cancel_open_orders_for_symbol(symbol)` helper; called from both `_flatten_unknown_position` and `_drain_startup_flatten_queue` before each SELL. +1 regression test asserts `cancel_order` fires before `place_order` when draining a queued zombie with residual orders. Same-class protection as DEF-158 for the 9:30-ET queue-drain path. |
| M-04 | **RESOLVED** | `argus/execution/broker_router.py` + `tests/execution/test_broker_router.py` deleted. No `argus/*` importers — only the (now-deleted) test referenced the class. `docs/architecture.md` BrokerRouter prose kept as a deferred observation (tracked under DEF-168 API-catalog drift) to minimize scope expansion. |
| M-05 | **RESOLVED** | 404 early return in `ibkr_broker._on_error` removed; 404 added to `_ORDER_REJECTION_CODES`. 404 now falls through to the shared `is_order_rejection` branch, which publishes `OrderCancelledEvent(reason=...)` without depending on a later `orderStatusEvent(Cancelled)` message from IBKR. |
| M-06 | **PARTIAL** | Stopgap fix (b) applied: reconstructed `entry_time` biased earlier by `max_position_duration_minutes // 2` so post-restart time-stop semantics degrade gracefully instead of granting a fresh full-duration lease. Durable fix (a) (persist entry_time in trades-DB live-positions sidecar) requires schema addition and was deferred. +1 regression test. |
| M-03 (cross-domain, P1-D1-M03) | **DEFERRED → DEF-177** | `RejectionStage.MARGIN_CIRCUIT` requires editing `argus/intelligence/counterfactual.py` + `counterfactual_positions` schema + `argus/main.py:1833` consumer, which exceeds FIX-04's execution-only declared scope (halt-rule-4). Tracked as DEF-177; MEDIUM priority (masks margin-incident signal in `FilterAccuracy.by_stage` today). |
| L-01 | **RESOLVED** via M-04 | Test file deleted with `broker_router.py`. |
| L-02 | **RESOLVED** | `_trades_by_order_id: dict[int, Trade]` index added; populated in `_handle_order_status` for any non-terminal status; pruned on Filled/Cancelled/Inactive. `_find_trade_by_order_id` is O(1) with an O(n) `_ib.trades()` fallback for the brief window after submission but before the first orderStatusEvent. |
| L-03 | **RESOLVED** | 10 `OrderResult(status="submitted")` / `status="rejected"` literals in `ibkr_broker.py` replaced with `OrderStatus.SUBMITTED` / `OrderStatus.REJECTED` enum references. |
| L-04 | **RESOLVED** | `execution_record.py`: `from datetime import UTC, datetime` (no `timezone`); `datetime.now(UTC)` replaces `datetime.now(timezone.utc)`; `_ET = ZoneInfo(...)` module-level constant moved below all imports per CLAUDE.md. |
| L-05 | **RESOLVED** | Redundant `self._flattened_today = True` at poll-loop L1451 deleted. `eod_flatten()` owns that write at L1605. |
| L-06 | **RESOLVED** | `_now_et(now)` helper extracted; reads `self._config.eod_flatten_timezone` (preserving config-aware behavior from the EOD path, extending it to the startup-drain path that previously hard-coded `"America/New_York"`). Poll loop computes ET once at the top. |
| L-07 | **RESOLVED-VERIFIED** | `_close_position` per-symbol cleanup of reconciliation-miss / stop-retry / amended-prices dicts documented as intentional defense-in-depth; carries per-close cleanup even though `reset_daily_state()` clears these wholesale. Honors ALLOW_ALL duplicate-stock policy (DEC-121/160) where a symbol may close and reopen intraday. |
| L-08 | **RESOLVED** | `_handle_flatten_fill` legacy "fall back to first open position" path tightened to `logger.error + return`. Pre-strategy_id `PendingManagedOrder` shape no longer exists after 89 sprints; the silent fallback was letting stale fills accrue to the wrong position's P&L. Existing `test_flatten_fill_fallback_when_strategy_id_not_found` renamed to `test_flatten_fill_strategy_id_mismatch_hard_errors` and rewritten to assert no position closes. |
| L-09 | **RESOLVED** | `_handle_entry_fill` now initializes `mfe_time = mae_time = entry_fill_time` in the new `ManagedPosition`, mirroring the pre-existing `mfe_price = mae_price = entry_price` initialization. Three existing tests (`test_mfe_mae_initialized_at_entry`, `test_mfe_updated_on_price_increase`, `test_mae_updated_on_price_decrease`) updated from `is None` to `== entry_time`. |
| L-10 | **PARTIAL → DEF-176** | `DeprecationWarning` emitted when the legacy `auto_cleanup_orphans` kwarg is used without `reconciliation_config=`. Production (`argus/main.py`) confirmed to pass `reconciliation_config=` directly; full parameter removal deferred because three reconciliation test modules (`test_order_manager_reconciliation.py`, `test_order_manager_reconciliation_redesign.py`, `test_order_manager_sprint2875.py`) still pass the kwarg and were outside FIX-04's declared scope. |
| P1-G2-M04 | **RESOLVED** | Shared `config` fixture in `tests/execution/test_order_manager.py` overrides `eod_flatten_timeout_seconds=1` (Pydantic `ge=1` minimum) — matches the pattern from `test_order_manager_sprint329.py`. Full `test_order_manager.py` wall-clock run dropped from ~151s to ~34s. |

**Test delta:** 4,984 → 4,985 (net +1). Added 5 new execution regression tests (`test_reconstruct_reads_position_entry_price_field`, `test_reconstruct_reco_path_reads_position_entry_price_field`, `test_reconstruct_reads_order_quantity_field`, `test_drain_startup_flatten_queue_cancels_brackets_first`, `test_reconstruct_biases_entry_time_earlier`); removed 4 tests via `test_broker_router.py` deletion.

**New DEFs:** DEF-176 (legacy kwarg removal — LOW), DEF-177 (cross-domain MARGIN_CIRCUIT — MEDIUM).

**Scope expansions (in-scope but outside kickoff's Expected Files list):**
- `argus/execution/ibkr_errors.py` — added 404 to `_ORDER_REJECTION_CODES` so M-05's fall-through publishes `OrderCancelledEvent`. File is in `argus/execution/` per the kickoff's broader scope; just not on the narrow Expected Files list.
- `tests/execution/test_ibkr_broker.py` — one test (`test_ibkr_error_404_logged_at_warning`) updated to expect 2 warning calls after the 404 fall-through. Without this, the suite would regress.
