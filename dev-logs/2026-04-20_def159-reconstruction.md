# DEF-159: Reconstruction Trade Logging Fix

**Date:** 2026-04-20
**Type:** Impromptu bug fix
**Relates to:** DEF-158 (duplicate SELL fix from earlier today)

## Problem

After the hung-API restart this morning, ARGUS reconstructed 10 broker
positions with `avg_entry_price=0.0` (broker didn't have entry context
from the prior session). When these positions were flattened via time-stop,
the Trade model calculated `outcome=WIN` because `exit_price > 0.0`.

Result: 10 bogus "wins" totalling ~$34K fake P&L polluting all analytics.

## Fix

Added `entry_price_known` boolean column to the trades table:
- Default: `1` (true) — normal trades unaffected
- Set to `0` when `entry_price == 0.0` at trade logging time
- Analytics consumers filter these out of P&L/win-rate calculations
- Trades preserved in DB for audit (not deleted)

## Files Changed

- `argus/db/schema.sql` — column definition
- `argus/db/manager.py` — ALTER TABLE migration
- `argus/models/trading.py` — `entry_price_known: bool = True` field
- `argus/analytics/trade_logger.py` — INSERT, read-back, 3 query filters
- `argus/analytics/performance.py` — compute_metrics filter
- `argus/execution/order_manager.py` — detection in `_close_position()`
- `scripts/migrate_def159_bogus_trades.py` — one-shot backfill

## Migration Result

```
Found 10 trades with unrecoverable entry price
Updated 10 rows: entry_price_known = 0
```

## Tests

4 new tests covering: marking, read-back, analytics exclusion, P&L exclusion.
Full suite: 4,919 passed.
