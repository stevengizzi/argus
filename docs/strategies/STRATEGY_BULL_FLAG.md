# ARGUS — Strategy Spec Sheet: Bull Flag

> *Created: Mar 22, 2026. Last Updated: Mar 22, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | Bull Flag |
| **ID** | `strat_bull_flag` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven + Claude |
| **Created** | 2026-03-21 |
| **Last Updated** | 2026-03-22 |
| **Pipeline Stage** | Exploration (Sprint 26) |
| **Family** | Continuation |

---

## Description

Bull flag continuation pattern strategy that identifies strong upward moves (poles) followed by tight consolidation periods (flags), then enters on the breakout above the flag's upper boundary with volume confirmation. This is a classic continuation pattern — the consolidation after a strong move represents a pause, not a reversal, and the breakout resumes the prior trend. Implemented as a PatternBasedStrategy wrapping the BullFlagPattern module.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Bearish Trending, Range-Bound |
| VIX Range | < 35 |
| SPY Trend | Not in Crisis mode |

Rationale: Continuation patterns work best in markets with established trends. In crisis regimes, breakouts frequently fail.

**DEC-360 alignment (2026-04-21):** `bearish_trending` is present in `allowed_regimes` for every PatternBasedStrategy via `config/strategies/bull_flag.yaml`. This table now matches the config.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | 10:00 AM ET |
| **Latest Entry Time** | 3:00 PM ET |
| **Force Close Time** | 3:50 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: The wider 10:00–3:00 window captures bull flags that form throughout the trading day, not just the morning session. The 10:00 start avoids opening volatility noise.

---

## Scanner Criteria

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Price range | $10–$200 | Sufficient liquidity, avoids penny stocks |
| Average daily volume | ≥ 1,000,000 | Ensures tradeable liquidity |

**Max Watchlist Size:** 20

---

## Entry Criteria

ALL of the following must be TRUE (detected by BullFlagPattern module):

1. **Strong pole:** At least `pole_min_bars` (5) bars with cumulative move ≥ `pole_min_move_pct` (3%)
2. **Tight flag:** Consolidation of ≤ `flag_max_bars` (20) bars retracing ≤ `flag_max_retrace_pct` (50%) of the pole
3. **Breakout:** Price breaks above the flag's upper boundary (highest high during flag)
4. **Volume confirmation:** Breakout bar volume ≥ `breakout_volume_multiplier` (1.3×) × average bar volume
5. **Within operating window:** 10:00 AM–3:00 PM ET

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below the flag low (pattern-defined) |
| **Type** | Hard stop (stop-market) |

### Profit Targets
| Target | Trigger | Action | Position Affected |
|--------|---------|--------|-------------------|
| T1 | Entry + 1.0R | Sell 50% | First half |
| T2 | Entry + 2.0R | Sell remaining 50% | Second half |

### Time Stop
| Parameter | Value |
|-----------|-------|
| **Max Time in Trade** | 30 minutes |
| **Action if Hit** | Close entire remaining position at market |

### End of Day
All positions closed at market by 3:50 PM ET.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1.0% of allocated capital |
| **Share Calculation** | Delegated to Quality Engine / Dynamic Position Sizer |
| **Max Concurrent Positions** | 3 |

---

## Strategy-Level Risk Limits

| Parameter | Value |
|-----------|-------|
| **Max Loss Per Trade** | 1% of allocated capital |
| **Max Daily Loss** | 3% of allocated capital |
| **Max Trades Per Day** | 6 |

---

## Performance Benchmarks

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | 45% | 55% |
| Profit Factor | 1.1 | 1.5 |
| Sharpe Ratio | 0.3 | 1.0 |
| Max Drawdown | 12% | 8% |

---

## Backtest Results

*Generic PatternBacktester infrastructure ready. Awaiting historical data for full sweep + walk-forward validation.*

### Walk-Forward Analysis
TBD. All pre-Databento results are provisional (DEC-132).

---

## Cross-Strategy Interaction

| Aspect | Behavior |
|--------|----------|
| **Duplicate stock policy** | ALLOW_ALL (DEC-121) |
| **Shared watchlist** | Uses gap scanner results |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |

---

## Universe Filter (Sprint 26)

Declared in `config/strategies/bull_flag.yaml` under `universe_filter:`.

| Filter | Value |
|--------|-------|
| min_price | 10.0 |
| max_price | 200.0 |
| min_avg_volume | 1,000,000 |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-03-21 | Initial BullFlagPattern module | Sprint 26 S5 |
| 1.0.1 | 2026-03-22 | Integration wiring + spec sheet | Sprint 26 S9 |

---

## Notes

- Implemented via PatternBasedStrategy wrapper around BullFlagPattern module
- Pattern detection is pure — no strategy concerns in the pattern module
- Lookback window: `pole_min_bars + flag_max_bars` = 25 bars by default
- All backtest results are provisional until re-validated with Databento data (DEC-132)

---

*End of Strategy Spec Sheet*
