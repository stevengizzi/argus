# ARGUS — Strategy Spec Sheet: Flat-Top Breakout

> *Created: Mar 22, 2026. Last Updated: Mar 22, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | Flat-Top Breakout |
| **ID** | `strat_flat_top_breakout` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven + Claude |
| **Created** | 2026-03-21 |
| **Last Updated** | 2026-03-22 |
| **Pipeline Stage** | Shadow (demoted Sprint 32.9; awaits parameter optimization) |
| **Family** | Breakout |
| **Mode** | `shadow` |
| **Status** | PROVISIONAL — backtest results **pending** (section below is an explicit placeholder, not forgotten). Demoted to shadow per Sprint 32.9. CounterfactualTracker collecting data; no live capital deployed. |

---

## Description

Horizontal resistance breakout strategy that identifies stocks building a flat resistance level with multiple touches and tight consolidation beneath it, then enters on a decisive break above resistance with volume confirmation. The flat-top pattern indicates strong supply at a price level being absorbed by persistent demand — when supply is exhausted, the breakout tends to be explosive. Implemented as a PatternBasedStrategy wrapping the FlatTopBreakoutPattern module.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Range-Bound |
| VIX Range | < 35 |
| SPY Trend | Not in Crisis mode |

Rationale: Breakout patterns need directional follow-through. Crisis regimes produce false breakouts.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | 10:00 AM ET |
| **Latest Entry Time** | 3:00 PM ET |
| **Force Close Time** | 3:50 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: Flat-top patterns need time to form (multiple resistance touches), so the window starts at 10:00 after opening noise settles. The wide window through 3:00 captures afternoon breakouts.

---

## Scanner Criteria

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Price range | $10–$200 | Sufficient liquidity, avoids penny stocks |
| Average daily volume | ≥ 1,000,000 | Ensures tradeable liquidity |

**Max Watchlist Size:** 20

---

## Entry Criteria

ALL of the following must be TRUE (detected by FlatTopBreakoutPattern module):

1. **Resistance level:** At least `resistance_touches` (3) highs within `resistance_tolerance_pct` (0.2%) of each other
2. **Consolidation:** Minimum `consolidation_min_bars` (10) bars in the consolidation zone
3. **Breakout:** Price closes above the resistance level
4. **Volume confirmation:** Breakout bar volume ≥ `breakout_volume_multiplier` (1.3×) × average bar volume
5. **Within operating window:** 10:00 AM–3:00 PM ET

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below consolidation low (pattern-defined) |
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

## Backtest Results — PENDING

**Status:** Pending. Not forgotten. The placeholder is explicit to distinguish "we haven't done it yet" from "we did it and the results are unrecorded."

Generic PatternBacktester infrastructure is ready (Sprint 32 integration). Universe-aware sweep is blocked on the Sprint 31.85 consolidated Parquet cache being activated operationally (`config/historical_query.yaml` repoint). Once the consolidated cache is live, a representative-universe sweep + walk-forward is the prerequisite for promoting this strategy back to `live` mode.

### Walk-Forward Analysis
PENDING. All pre-Databento results are provisional (DEC-132). Post-consolidation sweep will be the first valid evidence for this strategy.

---

## Cross-Strategy Interaction

| Aspect | Behavior |
|--------|----------|
| **Duplicate stock policy** | ALLOW_ALL (DEC-121) |
| **Shared watchlist** | Uses gap scanner results |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |

---

## Universe Filter (Sprint 26)

Declared in `config/strategies/flat_top_breakout.yaml` under `universe_filter:`.

| Filter | Value |
|--------|-------|
| min_price | 10.0 |
| max_price | 200.0 |
| min_avg_volume | 1,000,000 |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-03-21 | Initial FlatTopBreakoutPattern module | Sprint 26 S6 |
| 1.0.1 | 2026-03-22 | Integration wiring + spec sheet | Sprint 26 S9 |

---

## Notes

- Implemented via PatternBasedStrategy wrapper around FlatTopBreakoutPattern module
- Pattern detection is pure — no strategy concerns in the pattern module
- Lookback window: `consolidation_min_bars` = 10 bars minimum (pattern adjusts)
- Resistance tolerance: 0.2% — highs within this range count as "flat"
- All backtest results are provisional until re-validated with Databento data (DEC-132)

---

*End of Strategy Spec Sheet*
