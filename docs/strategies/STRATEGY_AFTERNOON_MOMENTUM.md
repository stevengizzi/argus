# ARGUS — Strategy Spec Sheet: Afternoon Momentum

> *Created: Feb 26, 2026. Last Updated: Feb 26, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | Afternoon Momentum |
| **ID** | `strat_afternoon_momentum` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven + Claude |
| **Created** | 2026-02-26 |
| **Last Updated** | 2026-02-26 |
| **Pipeline Stage** | Concept → Exploration (Sprint 20) |

---

## Description

Consolidation breakout strategy that identifies stocks consolidating during midday (12:00–2:00 PM) and enters on breakouts after 2:00 PM ET. This strategy capitalizes on the common intraday pattern where stocks that gapped up and ran in the morning often consolidate during the lunch lull, then resume their trend in the afternoon session. The tight midday consolidation provides a clear risk reference (the consolidation low) and the afternoon breakout confirms renewed institutional interest.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, High Volatility |
| VIX Range | < 30 |
| SPY Trend | Not in Crisis mode |
| Other | None |

Rationale: Momentum strategies thrive in trending markets where directional moves follow through. Afternoon breakouts work best when there's enough volatility for continuation but not so much that stocks reverse sharply.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | 2:00 PM ET |
| **Latest Entry Time** | 3:30 PM ET |
| **Force Close Time** | 3:45 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: The 2:00–3:30 PM window captures afternoon momentum after the midday consolidation period (12:00–2:00 PM). This gives stocks 2–3 hours to establish a clear consolidation range before we look for breakouts. Force close at 3:45 PM ensures positions are flattened before the final 15 minutes when liquidity can thin.

---

## Scanner Criteria

Afternoon Momentum reuses the same gap scanner as the ORB strategy family. Stocks that gapped up strongly are the natural candidates for midday consolidation and afternoon breakout patterns.

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

1. **CONSOLIDATED state:** Stock has confirmed tight consolidation during midday window (range/ATR < `consolidation_atr_ratio`, default 0.75)
2. **Within entry window:** Current time is 2:00 PM ET – 3:30 PM ET
3. **Breakout confirmation:** Current candle CLOSES above the consolidation high (using the high value BEFORE the current bar)
4. **Volume confirmation:** Breakout candle volume ≥ `volume_multiplier` × average bar volume (default 1.2×)
5. **Chase protection:** Close is not more than `max_chase_pct` (default 0.5%) above consolidation high
6. **Valid risk:** Entry price > stop price (ensures positive risk per share)
7. **Internal risk limits pass:** Daily loss and trade count limits not exceeded
8. **Position count limit:** Current concurrent positions < `max_concurrent_positions` (default 3)

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below consolidation_low (lowest low seen from noon through breakout) |
| **Type** | Hard stop (stop-market) |
| **Initial Distance** | consolidation_low × (1 − stop_buffer_pct), buffer default 0.1% |

Rationale: The consolidation low is the natural support level. If price breaks below it after the breakout, the consolidation thesis has failed.

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
| **Max Time in Trade** | min(60 minutes, seconds until 3:45 PM ET) |
| **Action if Hit** | Close entire remaining position at market |

### End of Day
All positions closed at market by 3:45 PM ET.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1.0% of allocated capital |
| **Max Risk in Dollars** | allocated_capital × 0.01 |
| **Share Calculation** | risk_dollars / effective_risk_per_share |
| **Max Concurrent Positions** | 3 |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |
| **Minimum Risk Floor** | max(risk_per_share, entry_price × 0.003) — prevents oversizing on very tight consolidation ranges |

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Expected Minimum** | 5 minutes |
| **Expected Maximum** | 60 minutes (time stop) |
| **Average (from backtest)** | TBD after VectorBT sweep |

---

## Strategy-Level Risk Limits

| Parameter | Value |
|-----------|-------|
| **Max Loss Per Trade** | 1% of allocated capital |
| **Max Daily Loss (this strategy)** | 3% of allocated capital |
| **Max Consecutive Losses Before Pause** | 5 (handled by Orchestrator PerformanceThrottler) |
| **Max Trades Per Day** | 6 |

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

*TBD after Sprint 20 VectorBT sweep and walk-forward analysis.*

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

*TBD during Validation Track.*

---

## Live Trading Results

*TBD after promotion to live.*

---

## Cross-Strategy Interaction

| Aspect | Behavior |
|--------|----------|
| **Duplicate stock policy** | ALLOW_ALL (DEC-121) — same symbol can be held by ORB and Afternoon Momentum simultaneously |
| **Intended flow** | ORB trades morning breakout → consolidation during midday → Afternoon Momentum enters PM breakout |
| **Shared watchlist** | Uses same scanner results as ORB family |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |
| **Time separation** | ORB: 9:35–11:30 entry window, Afternoon Momentum: 2:00–3:30 PM entry window — no overlap |

---

## Known Divergences

Differences between VectorBT backtest and production implementation:

1. **ATR calculation method:** VectorBT uses SMA(14) of intraday true ranges; production uses Wilder's EMA. Consolidation ratio thresholds may not transfer exactly. Same class as DEC-074.

2. **Entry attempts per day:** VectorBT captures single entry per day for simplicity; live strategy could theoretically retry if first breakout fails and stock re-consolidates (conservative direction for VectorBT — produces fewer trades than live might).

3. **Volume average denominator:** Includes all bars from 9:30 AM (not just consolidation window). Consistent between live and VectorBT.

4. **Provisional results:** All backtest results are provisional until re-validated with Databento exchange-direct data (DEC-132).

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-26 | Initial specification | Sprint 20 design |

---

## Notes

- Uses existing IndicatorEngine VWAP and ATR-14 indicators (Sprint 12.5, DEC-092). No new indicator infrastructure needed.
- State machine has 5 states: WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED (terminal) or REJECTED (terminal).
- Consolidation range updates continuously through CONSOLIDATED state — if range widens beyond `max_consolidation_atr_ratio` (default 2.0), transitions to REJECTED.
- 1-minute bar resolution is adequate for this strategy's 5–60 minute hold duration.
- Time stop is dynamically compressed near EOD — entry at 3:25 PM gets a 20-minute time stop (until 3:45 PM), not the full 60 minutes.
- Minimum risk floor (0.3% of entry price) prevents enormous positions from very tight consolidation where the stop is extremely close to entry.

---

*End of Strategy Spec Sheet*
