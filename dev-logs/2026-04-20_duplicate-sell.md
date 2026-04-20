# DEF-158: Duplicate SELL Orders — Root Cause and Fix

**Date:** 2026-04-20
**Severity:** Critical (real money impact — 28 positions flipped short)

## Incident

During the morning session (09:26-10:04 ET), ARGUS traded normally but
positions were exited via time-stop and trailing-stop flatten orders. After
a mid-session reboot at 11:45 ET, startup cleanup placed additional SELL
orders for "zombie" positions. The cumulative effect: 28 symbols ended the
day at approximately -2x their original long size at IBKR.

## Root Causes

### 1. Flatten-pending timeout resubmission (primary)

`_check_flatten_pending_timeouts()` cancels and resubmits flatten orders
after 120 seconds if no fill callback has arrived. IBKR paper trading can
delay fill callbacks beyond this threshold. The resubmission places a SECOND
MARKET SELL while the first order has already filled at IBKR.

**Evidence:** ARX SELL 103 at 09:55:29, SELL 103 again at 09:57:30
(exactly 120s later = timeout resubmission).

**Fix:** Before resubmitting, query broker position via `get_positions()`.
If the symbol's position is 0 at the broker, clear the pending state
without resubmitting — the original order already filled.

### 2. Startup cleanup doesn't cancel pre-existing bracket orders

`_flatten_unknown_position()` places a MARKET SELL but doesn't cancel any
open orders for the symbol. If residual bracket orders (stop, T1, T2) from
a prior session are still at the broker, they can trigger ADDITIONAL sells
after the startup flatten, creating a short.

**Fix:** Query open orders and cancel any matching the symbol before
placing the flatten SELL.

### 3. Stop fill doesn't cancel concurrent flatten orders

When a broker-side stop fills while a time-stop or trail flatten order is
pending, `_handle_stop_fill` closes the position but leaves the flatten
order live at the broker. That flatten then executes against a now-flat
position, going short.

**Fix:** After processing a stop fill, check `_flatten_pending` for the
symbol and cancel the pending flatten order at the broker.

### Bonus fix: Flatten fill cancels duplicate flatten orders

When a flatten fill arrives, scan `_pending_orders` for any OTHER flatten
orders for the same symbol and cancel them. This catches the case where
timeout resubmission placed a second order and both are in flight.

## Files Changed

- `argus/execution/order_manager.py` — 4 method changes
- `tests/execution/test_order_manager_def158.py` — 5 new regression tests
- `CLAUDE.md` — DEF-158 resolved, DEF-159 + DEF-160 logged
- `docs/sprint-history.md` — AU entry
