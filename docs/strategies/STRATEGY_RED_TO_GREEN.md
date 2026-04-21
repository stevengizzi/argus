# ARGUS — Strategy Spec Sheet: Red-to-Green

> *Created: Mar 22, 2026. Last Updated: Mar 22, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | Red-to-Green |
| **ID** | `strat_red_to_green` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven + Claude |
| **Created** | 2026-03-21 |
| **Last Updated** | 2026-03-22 |
| **Pipeline Stage** | Exploration (Sprint 26) |
| **Family** | Reversal |

---

## Description

Gap-down reversal strategy that enters long when price tests and holds a key support level (VWAP, premarket low, prior close) after a gap down. The thesis is that moderate gap-downs on liquid stocks often find support at predictable levels; when price holds and reclaims the level on volume, the reversal is likely. This is ARGUS's first gap-down reversal strategy, complementing the existing gap-up breakout (ORB) and mean-reversion (VWAP Reclaim) strategies.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Bearish Trending, Range-Bound |
| VIX Range | < 35 |
| SPY Trend | Not in Crisis mode |
| Other | None |

Rationale: Gap-down reversals work best in stable or bullish markets where institutional buyers step in at support. In crisis regimes, gap-downs tend to cascade rather than reverse.

**DEC-360 alignment (2026-04-21):** Red-to-Green hardcodes `allowed_regimes = ["bullish_trending", "bearish_trending", "range_bound"]` in the strategy class itself. This table now matches the code.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | 9:45 AM ET |
| **Latest Entry Time** | 11:00 AM ET |
| **Force Close Time** | 3:50 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: The 9:45–11:00 window gives the opening 15 minutes for the gap to confirm, then catches the first reversal attempt before midday chop sets in.

---

## Scanner Criteria

R2G uses the gap scanner, filtering for gap-down stocks (negative gap).

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Pre-market gap | -2% to -10% | Identifies moderate gap-down (not catastrophic) |
| Price range | $5–$200 | Sufficient liquidity, avoids penny stocks |
| Average daily volume | ≥ 500,000 | Ensures tradeable liquidity |

**Max Watchlist Size:** 20

---

## Entry Criteria

ALL of the following must be TRUE simultaneously:

1. **Gap down confirmed:** Stock gapped down between `min_gap_down_pct` (2%) and `max_gap_down_pct` (10%)
2. **Key level identified:** Price approaches VWAP, premarket low, or prior close within `level_proximity_pct` (0.3%)
3. **Level test confirmed:** Price tests the level for at least `min_level_test_bars` (2) bars
4. **Close above level:** Current candle closes above the key level
5. **Volume confirmation:** Candle volume ≥ `volume_confirmation_multiplier` (1.2×) × average bar volume
6. **Chase protection:** Close not more than `max_chase_pct` (0.3%) above the key level
7. **Within operating window:** Current time ≥ 9:45 AM ET and < 11:00 AM ET

**State Machine:** WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED/EXHAUSTED

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below the key support level minus `stop_buffer_pct` (0.1%) |
| **Type** | Hard stop (stop-market) |
| **Initial Distance** | level_price × (1 - stop_buffer_pct) |

### Profit Targets
| Target | Trigger | Action | Position Affected |
|--------|---------|--------|-------------------|
| T1 | Entry + 1.0R | Sell 50% | First half of position |
| T2 | Entry + 2.0R | Sell remaining 50% | Second half of position |

### Stop Adjustments
| Trigger | New Stop Level |
|---------|---------------|
| T1 hit | Move stop to breakeven (entry price + small buffer) |
| T2 hit | Position fully closed |

### Time Stop
| Parameter | Value |
|-----------|-------|
| **Max Time in Trade** | 20 minutes (1200 seconds) |
| **Action if Hit** | Close entire remaining position at market |

### End of Day
All positions closed at market by 3:50 PM ET.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1.0% of allocated capital |
| **Share Calculation** | Delegated to Quality Engine / Dynamic Position Sizer |
| **Max Concurrent Positions** | 2 |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |

---

## Strategy-Level Risk Limits

| Parameter | Value |
|-----------|-------|
| **Max Loss Per Trade** | 1% of allocated capital |
| **Max Daily Loss (this strategy)** | 3% of allocated capital |
| **Max Trades Per Day** | 6 |
| **Max Level Attempts** | 2 per symbol per day |

---

## Performance Benchmarks

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | 40% | 50% |
| Profit Factor | 1.1 | 1.4 |
| Sharpe Ratio (20-day rolling) | 0.3 | 0.8 |
| Max Drawdown (from peak) | 12% | 8% |

---

## Backtest Results

*VectorBT module ready (`argus.backtest.vectorbt_red_to_green`). Awaiting full sweep on historical data.*

### VectorBT Parameter Exploration
| Parameter Set | Win Rate | Avg R | Profit Factor | Max DD | Sharpe | Notes |
|---------------|----------|-------|---------------|--------|--------|-------|
| TBD | | | | | | |

**Parameter Grid:** 108 combinations (4 gap × 3 proximity × 3 volume × 3 time_stop)

### Walk-Forward Analysis
| Window | IS Period | OOS Period | IS Return | OOS Return | WF Efficiency |
|--------|-----------|------------|-----------|------------|---------------|
| TBD | | | | | |

**Walk-Forward Assessment:** TBD. All pre-Databento results are provisional (DEC-132).

---

## Cross-Strategy Interaction

| Aspect | Behavior |
|--------|----------|
| **Duplicate stock policy** | ALLOW_ALL (DEC-121) |
| **Intended flow** | R2G trades gap-down reversals; ORB/VWAP Reclaim trade gap-up breakouts/reclaims |
| **Shared watchlist** | Uses gap scanner (different direction filter than ORB) |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |
| **Time overlap** | R2G: 9:45–11:00, ORB: 9:35–11:30 — overlapping windows |

---

## Universe Filter (Sprint 26)

Declared in `config/strategies/red_to_green.yaml` under `universe_filter:`.

| Filter | Value |
|--------|-------|
| min_price | 5.0 |
| max_price | 200.0 |
| min_avg_volume | 500,000 |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-03-21 | Initial implementation (skeleton + state machine + entry/exit) | Sprint 26 S2/S3 |
| 1.0.1 | 2026-03-22 | Integration wiring into main.py + spec sheet | Sprint 26 S9 |

---

## Notes

- State machine: WATCHING → GAP_DOWN_CONFIRMED → TESTING_LEVEL → ENTERED/EXHAUSTED
- Key level priority: VWAP (35pts), PRIOR_CLOSE (30pts), PREMARKET_LOW (25pts) in pattern strength scoring
- Max 2 level attempts per symbol per day before EXHAUSTED
- VWAP queried from DataService via `get_indicator_sync()` — graceful fallback if unavailable
- All backtest results are provisional until re-validated with Databento exchange-direct data (DEC-132)

---

*End of Strategy Spec Sheet*
