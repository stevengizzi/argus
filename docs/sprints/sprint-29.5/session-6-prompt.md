# Sprint 29.5, Session 6: MFE/MAE Trade Lifecycle Tracking

## Pre-Flight Checks
1. Read: `argus/execution/order_manager.py` (ManagedPosition class, `_handle_position_tick` or equivalent tick handler, `_log_trade` or trade close path), `argus/analytics/trade_logger.py`, `argus/analytics/debrief_export.py`, `argus/db/manager.py` (trades table schema)
2. **Fix prior-session regression first:**
   - Find `test_trades_limit_bounds` (likely in `tests/api/test_trades.py` or similar).
   - This test asserts the old `le=250` API boundary. S3 changed the limit to `le=1000`.
   - Update the test to reflect the new boundary (1000, not 250). Verify it passes.
   - Commit this fix separately: `git commit -m "fix: update test_trades_limit_bounds for S3 le=1000 change"`
3. Run scoped baseline: `python -m pytest tests/execution/test_order_manager.py tests/analytics/ tests/api/test_trades.py -x -q`
   Expected: all passing (including the fixed limit bounds test)
4. Verify branch: `sprint-29.5`

## Objective
Track Maximum Favorable Excursion (MFE) and Maximum Adverse Excursion (MAE) on every managed position in real-time, persist to trade records on close, and include in debrief export for post-session "was the trade green before it went red" analysis.

## Requirements

1. **Add MFE/MAE fields to ManagedPosition** in `argus/execution/order_manager.py`:
   ```python
   # MFE/MAE tracking (Sprint 29.5)
   mfe_price: float = 0.0      # Highest price reached while position open
   mae_price: float = 0.0      # Lowest price reached while position open
   mfe_r: float = 0.0          # MFE in R-multiples
   mae_r: float = 0.0          # MAE in R-multiples (negative)
   mfe_time: datetime | None = None  # When MFE was reached
   mae_time: datetime | None = None  # When MAE was reached
   ```
   - Initialize `mfe_price = entry_price` and `mae_price = entry_price` when position opens (in the method that creates ManagedPosition after fill).

2. **Update MFE/MAE on each tick** in the position tick handler:
   - Find where unrealized P&L is computed per tick (look for `PositionUpdatedEvent` publishing)
   - After computing current_price for a position:
     ```python
     if current_price > position.mfe_price:
         position.mfe_price = current_price
         position.mfe_time = self._clock.now()
         risk = position.entry_price - position.original_stop_price
         if risk > 0:
             position.mfe_r = (current_price - position.entry_price) / risk
     if current_price < position.mae_price:
         position.mae_price = current_price
         position.mae_time = self._clock.now()
         risk = position.entry_price - position.original_stop_price
         if risk > 0:
             position.mae_r = -((position.entry_price - current_price) / risk)
     ```
   - This must be O(1) — simple comparisons, no loops or queries.

3. **Persist to trade record** in `argus/analytics/trade_logger.py`:
   - Add 4 columns to the trades table: `mfe_r REAL`, `mae_r REAL`, `mfe_price REAL`, `mae_price REAL`
   - In the trade logging method, pass MFE/MAE from the ManagedPosition to the DB insert
   - Handle migration: use `ALTER TABLE trades ADD COLUMN ... DEFAULT NULL` pattern (or whatever the existing migration approach is — check `argus/db/manager.py`)

4. **Include in debrief export** in `argus/analytics/debrief_export.py`:
   - Add `mfe_r`, `mae_r`, `mfe_price`, `mae_price` to the trade dict in the debrief JSON

5. **Pass MFE/MAE from OrderManager to TradeLogger**:
   - Find where the trade is logged on position close (look for `TradeLogger.log_trade` or similar call)
   - Pass the position's MFE/MAE values as additional kwargs

## Constraints
- Do NOT modify CounterfactualTracker MAE/MFE logic (it has its own)
- MFE/MAE computation must be O(1) per tick — no lookups
- Do NOT add new DB tables — columns on existing trades table
- Handle NULL gracefully for historical trades without MFE/MAE data

## Test Targets
- New tests:
  1. `test_mfe_mae_initialized_at_entry` — verify mfe/mae set to entry_price on position open
  2. `test_mfe_updated_on_price_increase` — tick with higher price updates mfe_price and mfe_r
  3. `test_mae_updated_on_price_decrease` — tick with lower price updates mae_price and mae_r
  4. `test_mfe_mae_r_calculation_correct` — verify R-multiple math (entry=100, stop=98, price=103 → mfe_r=1.5)
  5. `test_mfe_mae_preserved_on_neutral_tick` — tick at same price doesn't overwrite timestamps
  6. `test_mfe_mae_persisted_to_trade_log` — verify DB record contains mfe/mae after position close
  7. `test_mfe_mae_in_debrief_export` — verify debrief JSON includes fields
  8. `test_mfe_mae_null_for_legacy_trades` — query old trade, mfe/mae are NULL, no crash
- Minimum: 8 new tests
- Test command: `python -m pytest tests/execution/test_order_manager.py tests/analytics/ -x -q`

## Regression Checklist (Session-Specific)
| Check | How to Verify |
|-------|---------------|
| Trade logging still works | Existing trade logger tests pass |
| Position tick handler performance | MFE/MAE is pure comparison — no perf regression |
| Debrief export includes all prior fields | Existing debrief tests pass, new fields are additive |
| DB migration doesn't lose data | ALTER TABLE ADD COLUMN preserves existing rows |
| test_trades_limit_bounds passes | Pre-flight fix confirmed |

## Definition of Done
- [ ] test_trades_limit_bounds pre-flight fix committed
- [ ] All requirements implemented
- [ ] All existing tests pass (including fixed limit bounds)
- [ ] 8+ new tests
- [ ] Close-out report written to `docs/sprints/sprint-29.5/session-6-closeout.md`
- [ ] Tier 2 review completed via @reviewer subagent

## Close-Out
Write to: `docs/sprints/sprint-29.5/session-6-closeout.md`

## Tier 2 Review
Test command: `python -m pytest tests/execution/test_order_manager.py tests/analytics/ -x -q`
Files NOT modified: `argus/intelligence/`, `argus/backtest/`, `argus/strategies/`

## Session-Specific Review Focus
1. Verify MFE/MAE O(1) — no loops or DB queries in tick handler
2. Verify R-multiple calculation uses original_stop_price, not current trail stop
3. Verify zero-risk guard (entry == stop) doesn't cause division by zero
4. Verify DB migration is additive (ALTER TABLE ADD COLUMN), not destructive
5. Verify test_trades_limit_bounds fix is correct (boundary at 1000, not 250)