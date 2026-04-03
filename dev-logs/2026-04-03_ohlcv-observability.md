# Dev Log — OHLCV-1m Silent Drop Observability

**Date:** 2026-04-03
**Session:** Diagnostic + Fix — data feed observability
**Status:** COMPLETE — reviewer verdict CLEAR

## Problem

April 3 session: ARGUS booted at 09:21 ET, Databento connected successfully
(EQUS.MINI, ALL_SYMBOLS, schemas=[ohlcv-1m, trades]), but after 6+ minutes
of market hours the heartbeat reported "0 candles received in last 5m" with
no WARNING or explanation. All 14 strategies received no data. The trades
schema appeared functional (stale detector was not tripping).

## Root Cause Confirmed

Three silent drop gates in `_on_ohlcv` run BEFORE the heartbeat counter:

1. `_resolve_symbol()` returns None — DEBUG log only (invisible at INFO)
2. `symbol not in self._viable_universe` — no log
3. `symbol not in self._active_symbols` — no log

Same pattern in `_on_trade` for unmapped records.

The most likely cause for the April 3 incident: OHLCV-1m instrument IDs were
not yet in Databento's `symbology_map` when the first bars arrived at 9:31 ET.
Trade instrument IDs resolved correctly (trades flow continuously from session
open, driving mapping completion). OHLCV bars arrive once per minute — by
9:31 ET, OHLCV mapping may not have completed for all symbols.

Git history confirmed: `databento_data_service.py` unchanged since Sprint 25.7.
Runtime/environment condition, not a regression.

## Changes

### `argus/data/databento_data_service.py`

**`__init__`** — 10 new instance variables:
- 5 drop counters: `_ohlcv_unmapped_since_heartbeat`,
  `_ohlcv_filtered_universe_since_heartbeat`,
  `_ohlcv_filtered_active_since_heartbeat`,
  `_trades_unmapped_since_heartbeat`,
  `_trades_received_since_heartbeat`
- 3 first-event flags: `_ohlcv_unmapped_warned`, `_first_ohlcv_resolved`,
  `_first_trade_resolved`
- `_symbol_mappings_received`
- `_market_hours_heartbeat_count`

**`_on_ohlcv`** — counter at each silent drop gate, one-time WARNING for
first unmapped, one-time INFO for first resolved symbol.

**`_on_trade`** — unmapped counter, received counter, one-time INFO for
first resolved trade.

**`_on_symbol_mapping`** — was `pass`; now counts arrivals, logs first
mapping at INFO, logs progress every 2000th.

**`_connect_live_session`** — schedules `_log_post_start_symbology_size()`
after `start()`.

**`_log_post_start_symbology_size`** — new method, 2s delay, logs
symbology_map size at INFO.

**`_data_heartbeat`** — enhanced log format:
```
Data heartbeat: 42 candles in last 5m (38 symbols active) | dropped: 1200 unmapped, 350 universe, 80 active | trades: 15000 received, 200 unmapped
```
Drops suffix omitted when all zero. Trades suffix omitted when all zero.
Escalates to WARNING when 0 candles in market hours after ≥2 market-hours
cycles (the April 3 failure mode was previously invisible at INFO).

### `tests/data/test_databento_data_service.py`

+23 tests in 5 new classes:
- `TestDropCounters` (6) — per-gate counter increment
- `TestHeartbeatObservability` (5) — drop/trades suffix presence/absence, reset
- `TestZeroCandleEscalation` (3) — WARNING vs INFO by market hours + cycle count
- `TestFirstEventSentinels` (4) — once-per-session firing
- `TestSymbolMappingObservability` (5) — counter and milestone logging

## Test Results

```
4610 passed, 0 failed (was 4582 before, +28 net including Sprint 32.95 additions)
```

## Reviewer Notes (CLEAR)

- N1: `_on_trade` lacks universe/active filter drop counters (spec-intentional)
- N2: `_market_hours_heartbeat_count` never resets — acceptable, service recreated per session
- N3: `asyncio.ensure_future` vs `create_task` — stylistic, no action needed
