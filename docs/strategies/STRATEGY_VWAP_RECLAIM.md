# ARGUS — Strategy Spec Sheet: VWAP Reclaim

> *Created: Feb 25, 2026. Last Updated: Feb 25, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | VWAP Reclaim |
| **ID** | `strat_vwap_reclaim` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven + Claude |
| **Created** | 2026-02-25 |
| **Last Updated** | 2026-02-25 |
| **Pipeline Stage** | Concept → Exploration (Sprint 19) |

---

## Description

Mean-reversion strategy that identifies stocks which gapped up strongly at the open, ran during the opening range period, then pulled back below VWAP on declining interest. When these stocks cross back above VWAP on increasing volume, the pullback is likely over and the stock resumes its intraday trend. This strategy is complementary to the ORB family — it catches a second-wave entry on the same universe of gap stocks during the mid-morning period when initial breakout momentum has faded.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Range-Bound, High Volatility |
| VIX Range | < 35 |
| SPY Trend | Not in Crisis mode |
| Other | None |

Rationale: Mean-reversion strategies thrive in range-bound and moderate volatility environments where pullbacks resolve. Excluded during Crisis regime where pullbacks can become cascading sell-offs.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | 10:00 AM ET |
| **Latest Entry Time** | 12:00 PM ET |
| **Force Close Time** | 3:50 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: The 10:00–12:00 window captures the period after initial ORB momentum fades. VWAP pullbacks need the opening range to establish, the stock to run, and then to pull back — this naturally takes 30–90 minutes from market open.

---

## Scanner Criteria

VWAP Reclaim reuses the same gap scanner as the ORB strategy family. Stocks that gapped up strongly are the natural candidates for VWAP pullback-and-reclaim patterns.

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Pre-market gap | ≥ 2.0% | Identifies institutional interest / catalyst |
| Price range | $10–$200 | Sufficient liquidity, avoids penny stocks |
| Average daily volume | ≥ 1,000,000 | Ensures tradeable liquidity |
| Relative volume (RVOL) | ≥ 2.0× | Today is an unusual day for this stock |

**Max Watchlist Size:** 20 (shared with ORB family)

---

## Entry Criteria

ALL of the following must be TRUE simultaneously for a trade to be taken. No exceptions.

1. **Stock gapped up:** Stock is on the scanner watchlist (gap ≥ 2% confirmed pre-market)
2. **Previously above VWAP:** Stock must have traded above VWAP at some point after market open (confirms the gap-up thesis)
3. **Pulled back below VWAP:** Stock closed below VWAP for at least `min_pullback_bars` (default 3) consecutive 1-minute bars
4. **Minimum pullback depth:** Distance from VWAP to pullback low ≥ `min_pullback_pct` (default 0.2%) — filters noise from bars barely touching VWAP
5. **Maximum pullback depth:** Distance from VWAP to pullback low ≤ `max_pullback_pct` (default 2.0%) — if exceeded, the sell-off is real, not a healthy pullback
6. **VWAP reclaim:** Current candle CLOSES above VWAP (not just wicks above)
7. **Volume confirmation:** Reclaim candle volume ≥ `volume_confirmation_multiplier` × average bar volume (default 1.2×)
8. **Within operating window:** Current time ≥ 10:00 AM ET and < 12:00 PM ET

**Chase Protection:** If the reclaim candle closes more than `max_chase_above_vwap_pct` (default 0.3%) above VWAP, skip the entry — the move has already happened.

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below the pullback swing low (lowest low during the below-VWAP period) |
| **Type** | Hard stop (stop-market) |
| **Initial Distance** | pullback_low − (pullback_low × stop_buffer_pct), buffer default 0.1% |

Rationale: The pullback low is the natural support level. If the stock breaks below its pullback low after reclaiming VWAP, the mean-reversion thesis has failed. Using the pullback low (a fixed point) rather than VWAP (a moving line) provides a stable reference.

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
| **Max Time in Trade** | 30 minutes (1800 seconds) |
| **Action if Hit** | Close entire remaining position at market |

### End of Day
All positions closed at market by 3:50 PM ET.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1.0% of allocated capital |
| **Max Risk in Dollars** | allocated_capital × 0.01 |
| **Share Calculation** | risk_dollars / (entry_price − stop_price) |
| **Max Concurrent Positions** | 3 |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |
| **Minimum Risk Floor** | max(risk_per_share, entry_price × 0.003) — prevents oversizing on very shallow pullbacks |

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Expected Minimum** | 5 minutes |
| **Expected Maximum** | 30 minutes (time stop) |
| **Average (from backtest)** | TBD after VectorBT sweep |

---

## Strategy-Level Risk Limits

| Parameter | Value |
|-----------|-------|
| **Max Loss Per Trade** | 1% of allocated capital |
| **Max Daily Loss (this strategy)** | 3% of allocated capital |
| **Max Consecutive Losses Before Pause** | 5 (handled by Orchestrator PerformanceThrottler) |
| **Max Trades Per Day** | 8 |

---

## Performance Benchmarks

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | 45% | 55% |
| Average R-Multiple | 0.3R | 0.8R |
| Profit Factor | 1.1 | 1.5 |
| Sharpe Ratio (20-day rolling) | 0.3 | 1.0 |
| Max Drawdown (from peak) | 12% | 8% |

---

## Backtest Results

*To be filled after Sprint 19 VectorBT sweep and walk-forward analysis.*

### VectorBT Parameter Exploration
| Parameter Set | Win Rate | Avg R | Profit Factor | Max DD | Sharpe | Notes |
|---------------|----------|-------|---------------|--------|--------|-------|
| TBD | | | | | | |

**Parameter Sensitivity:** TBD
**Selected Parameters:** TBD

### Replay Harness Validation
| Metric | Value |
|--------|-------|
| Period Tested | TBD |
| Total Trades | TBD |

### Walk-Forward Analysis
| Window | IS Period | OOS Period | IS Return | OOS Return | WF Efficiency |
|--------|-----------|------------|-----------|------------|---------------|
| TBD | | | | | |

**Walk-Forward Assessment:** TBD. Note: All pre-Databento results are provisional (DEC-132).

---

## Paper Trading Results

*To be filled during Validation Track.*

---

## Live Trading Results

*To be filled after promotion to live.*

---

## Cross-Strategy Interaction

| Aspect | Behavior |
|--------|----------|
| **Duplicate stock policy** | ALLOW_ALL (DEC-121) — same symbol can be held by ORB and VWAP Reclaim simultaneously |
| **Intended flow** | ORB trades breakout → exits → stock pulls back → VWAP Reclaim enters pullback recovery |
| **Shared watchlist** | Uses same scanner results as ORB family |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |
| **Time overlap** | ORB: 9:35–11:30, VWAP Reclaim: 10:00–12:00 — 90-minute overlap window |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-25 | Initial specification | Sprint 19 design |

---

## Notes

- VWAP is already computed by IndicatorEngine (Sprint 12.5, DEC-092). No new indicator infrastructure needed.
- This is ARGUS's first mean-reversion strategy. ORB and ORB Scalp are both momentum/breakout.
- 1-minute bar resolution is adequate for this strategy's 5–30 minute hold duration (unlike ORB Scalp, DEC-127).
- All backtest results are provisional until re-validated with Databento exchange-direct data (DEC-132).
- Minimum risk floor in position sizing prevents enormous positions from very shallow pullbacks where the pullback low is close to VWAP.

---

*End of Strategy Spec Sheet*
