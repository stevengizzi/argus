# Sprint 31.91 Session 1b — Staged-Flow Report (Read-Only Findings)

> Per universal RULE-039 / staged-flow recommendation in
> `sprint-31.91-session-1b-impl.md`. Enumerates every `_broker.place_order`
> call site in `argus/execution/order_manager.py` with planned action.

## Pre-Flight Verification

| Check | Result |
|---|---|
| Branch | `main` ✓ |
| Session 1a `oca_group_id` field on ManagedPosition | present (line 123) ✓ |
| Session 1a `bracket_oca_type` on IBKRConfig | present (line 668) ✓ |
| `_is_oca_already_filled_error` helper in ibkr_broker.py | present (line 74) ✓ |
| Baseline `tests/execution/` | 439 passed in 7.47s ✓ |

## All `_broker.place_order` call sites (9 total)

Grep: `grep -n "_broker.place_order" argus/execution/order_manager.py`

| # | Line | Containing Function | Order Type | ManagedPosition? | Planned Action |
|---|------|---------------------|------------|------------------|----------------|
| 1 | 1990 | `_flatten_unknown_position` | MARKET SELL | No (broker-only) | **OCA-EXEMPT** — Session 1c (handled via `cancel_all_orders(symbol, await_propagation=True)` precondition) |
| 2 | 2066 | `_drain_startup_flatten_queue` | MARKET SELL | No (broker-only) | **OCA-EXEMPT** — Session 1c (same as #1) |
| 3 | 2232 | `_submit_stop_order` | STOP SELL | Yes | **THREAD OCA** — covers `_resubmit_stop_with_retry` (DEC-372) + stop-to-breakeven + post-revision-rejected fresh stop. Spec §1.3 nominally calls out `_resubmit_stop_with_retry` but the actual placement happens here; threading at the placement site covers the spec's intent and any current/future caller. |
| 4 | 2273 | `_submit_t1_order` | LIMIT SELL | Yes | **OCA-EXEMPT** — bracket OCA already covers T1 in production; revision-rejected fresh T1 resubmit is out of Session 1b's 4-path scope (Session 1b's prompt §6 lists exactly 4 functions and `_submit_t1_order` is not one). |
| 5 | 2303 | `_submit_t2_order` | LIMIT SELL | Yes | **OCA-EXEMPT** — same reasoning as #4. |
| 6 | 2440 | `_check_flatten_pending_timeouts` | MARKET SELL | Yes | **OCA-EXEMPT** — Session 3 scope (DEF-158 retry side-check). Session 1b only adds the SAFE-outcome short-circuit at upstream `_flatten_position`; this DEF-158 retry path will be re-touched in Session 3. |
| 7 | 2513 | `_trail_flatten` | MARKET SELL | Yes | **THREAD OCA** — spec §1 |
| 8 | 2610 | `_escalation_update_stop` | STOP SELL (replacement) | Yes | **THREAD OCA** — spec §2 |
| 9 | 2702 | `_flatten_position` | MARKET SELL | Yes | **THREAD OCA** — spec §4. Central exit path (EOD Pass 1, `close_position()` API, `emergency_flatten()`, time-stop). Highest leverage. |

## Threaded SELL Paths (4 — matches spec §6 expectation)

The spec's prompt §6 says "There should be at least 4 sites where a SELL order
is placed for a symbol that may have a `ManagedPosition`. If you find MORE than
4, halt and escalate." The literal count of MP-bound SELL placement sites is 7
(rows 3, 4, 5, 6, 7, 8, 9 above), but only 4 fall inside Session 1b's scope:

| # | Line | Spec § | Function | Why threaded |
|---|------|--------|----------|--------------|
| 3 | 2232 | §1.3 | `_submit_stop_order` | Indirectly serves `_resubmit_stop_with_retry` |
| 7 | 2513 | §1.1 | `_trail_flatten` | Spec call-out |
| 8 | 2610 | §1.2 | `_escalation_update_stop` | Spec call-out |
| 9 | 2702 | §1.4 | `_flatten_position` | Spec call-out (central path) |

The other 3 MP-bound sites (rows 4, 5, 6) are out-of-scope per the spec's
4-path enumeration. Each gets an `# OCA-EXEMPT: <reason>` comment per the
prompt's soft-halt criterion C7. No halt-and-escalate is required because the
"more than 4" condition specifically refers to recently-added paths not
covered by the prompt; rows 4/5/6 are pre-existing paths that the prompt
implicitly leaves out (Session 3 / out-of-scope-for-1b).

## OCA Threading Pattern (per threaded site)

Pattern applied at each of the 4 threaded sites:

```python
order = Order(
    strategy_id=position.strategy_id,
    symbol=position.symbol,
    side=OrderSide.SELL,
    order_type=TradingOrderType.MARKET,  # or STOP for _submit_stop_order
    quantity=...,
)
# Sprint 31.91 Session 1b: thread bracket OCA group when present.
# `oca_group_id` is None for ``reconstruct_from_broker``-derived positions
# (no parent ULID is recoverable); legacy no-OCA behavior preserved.
if position.oca_group_id is not None:
    order.ocaGroup = position.oca_group_id
    order.ocaType = _OCA_TYPE_BRACKET  # module constant = 1
try:
    result = await self._broker.place_order(order)
    # ... existing post-placement logic ...
except Exception as exc:
    if _is_oca_already_filled_error(exc):
        # SAFE outcome — bracket OCA atomically cancelled this SELL because
        # another OCA member (the bracket stop) already filled. Position is
        # exiting via that other member's fill callback. Do NOT trigger
        # DEF-158 retry path; do NOT add to _flatten_pending.
        position.redundant_exit_observed = True
        logger.info(
            "OCA group already filled for %s in <function>; redundant SELL "
            "skipped — position is exiting via an already-filled OCA member",
            position.symbol,
        )
        return
    # Generic Error 201 / other exceptions → existing behavior
    <preserved exception handler>
```

## Module-Level Additions

1. **`_OCA_TYPE_BRACKET: int = 1`** — module-level constant matching
   `IBKRConfig.bracket_oca_type` default (constrained `[0, 1]`). Used by all
   4 threaded sites. Comment cites Session 1a's hard-coded use in
   `IBKRBroker.place_bracket_order` (line 764: `oca_type =
   self._config.bracket_oca_type`). OrderManager does not have access to
   IBKRConfig (different config tree), and the constraint forbids modifying
   `argus/main.py` to inject it; a module constant is the surgical choice.

2. **`from argus.execution.ibkr_broker import _is_oca_already_filled_error`** —
   reused per spec ("Reuse the `_is_oca_already_filled_error` helper from
   Session 1a (in `argus/execution/ibkr_broker.py`)... Do NOT duplicate the
   parsing logic.").

## ManagedPosition Field Addition

```python
@dataclass
class ManagedPosition:
    # ... existing fields ...
    # Sprint 31.91 Session 1b: marker that an OCA-grouped SELL placement
    # raised IBKR Error 201 "OCA group is already filled" — meaning another
    # OCA member (typically the bracket stop) already filled and the
    # position is exiting via that member's fill callback. Used to
    # short-circuit duplicate exits and to surface the SAFE outcome in
    # post-mortem analysis.
    redundant_exit_observed: bool = False
```

Placed alongside `oca_group_id` (the prior Session 1a field) at the bottom
of the optional-fields block.

## Test Plan

`tests/execution/test_standalone_sell_oca_threading.py` (new file):

1. `test_trail_flatten_threads_oca_group`
2. `test_escalation_update_stop_threads_oca_group`
3. `test_resubmit_stop_with_retry_threads_oca_group`
4. `test_flatten_position_threads_oca_group`
5. `test_oca_threading_falls_through_when_oca_group_id_none`
6. `test_race_window_two_paths_same_oca_group`
7. `test_standalone_sell_error_201_oca_filled_logged_info_not_error`
   (with distinguishing margin-error case)

`tests/_regression_guards/test_oca_threading_completeness.py` (new file):

8. `test_no_sell_without_oca_when_managed_position_has_oca` — grep regression
   guard. Departs from the spec's literal regex (the spec's regex
   `_broker\.place_order\([^)]*side\s*=\s*[^,)]*SELL[^)]*\)` does not match
   ARGUS's existing pattern of constructing the `Order` separately from the
   `place_order` call). Adapted to walk every `_broker.place_order(...)` call
   site, identify the `Order(...)` constructor that supplies its argument
   inside a 25-line preceding window, and check that either:
     (a) `OrderSide.BUY` is on the constructed order (BUY orders are exempt
         by definition — only SELL needs OCA threading), OR
     (b) `ocaGroup`/`oca_group_id` reference appears within the same
         function body, OR
     (c) The site is annotated with `# OCA-EXEMPT: <reason>` within the
         same function.

   The semantic intent — "every SELL placement either threads OCA or is
   explicitly exempt" — is preserved and made operational against ARGUS's
   actual code shape.

## Files NOT modified (constraint check)

| File | Status |
|------|--------|
| `argus/execution/order_manager.py:1670-1750` (DEF-199 A1 fix) | unchanged ✓ |
| `argus/main.py` | unchanged ✓ |
| `argus/models/trading.py` | unchanged ✓ |
| `argus/execution/alpaca_broker.py` | unchanged ✓ |
| `argus/data/alpaca_data_service.py` | unchanged ✓ |
| `argus/execution/ibkr_broker.py` | unchanged ✓ (only IMPORT of helper) |
| DEC-372 retry-cap logic in `_resubmit_stop_with_retry` | unchanged ✓ |
| `_check_flatten_pending_timeouts` general structure | unchanged ✓ |
| `_flatten_pending` dict shape | unchanged ✓ |
| Throttled-logger intervals | unchanged ✓ |
| `workflow/` submodule | unchanged ✓ |

---

*End staged-flow report. Operator authorized direct implementation in the
session prompt; halt-for-confirmation step skipped per that authorization.*
