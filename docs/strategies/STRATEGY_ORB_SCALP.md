# ARGUS — Strategy Spec Sheet: ORB Scalp

> *Based on `04_STRATEGY_TEMPLATE.md`. Last updated: February 25, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | ORB Scalp |
| **ID** | `strat_orb_scalp` |
| **Version** | `1.0.0` |
| **Asset Class** | US Stocks |
| **Author** | Steven (design) + Claude (implementation) |
| **Created** | February 25, 2026 |
| **Last Updated** | February 25, 2026 |
| **Pipeline Stage** | Exploration (Sprint 18) |

---

## Description

The ORB Scalp strategy is a fast-paced variant of the Opening Range Breakout strategy, designed for quick momentum captures with tight targets and short hold times. It exploits the same market behavior as ORB Breakout—stocks gapping on news or momentum establishing a tradeable range—but targets smaller, faster moves with a single exit at 0.3R and a maximum hold time of 120 seconds.

The thesis is that breakout momentum is front-loaded: if a breakout is going to work, it moves quickly. Instead of waiting for a 1.0R or 2.0R target that may never trigger, ORB Scalp captures a smaller profit quickly and moves on. This allows higher trade frequency (12/day vs 6/day for ORB Breakout) with a higher expected win rate (55% target vs 45%).

Key differences from ORB Breakout:
- **Single target at 0.3R** (instead of T1/T2 at 1R/2R)
- **Maximum hold time of 120 seconds** (instead of 15 minutes)
- **Higher trade frequency** (12/day vs 6/day)
- **Higher win rate target** (55% vs 45%)

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Range Bound, or High Volatility |
| VIX Range | < 35 |
| SPY Trend | No requirement for V1 |
| Other | No active circuit breakers |

*Note: Same regimes as ORB Breakout. The strategy works well in trending and volatile conditions where momentum is present. Market regime filtering will be enforced by the Orchestrator.*

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Opening Range Window** | 9:30–9:35 AM EST (5 minutes) |
| **Earliest Entry Time** | 9:45 AM EST (10 minutes after OR completes) |
| **Latest Entry Time** | 11:30 AM EST |
| **Force Close Time** | 3:50 PM EST |
| **Active Days** | Monday–Friday (US market days only) |

*Note: The 10-minute gap between OR completion (9:35) and earliest entry (9:45) allows the initial volatility to settle while still capturing morning momentum.*

---

## Scanner Criteria

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Gap % | ≥ 2.0% from previous close | Minimum gap to indicate meaningful catalyst |
| Pre-market Volume | Above average (RVOL ≥ 2.0) | Volume confirms institutional interest |
| Price Range | $10–$200 | Excludes penny stocks and ultra-high-priced stocks |
| Max Results | 20 symbols | Focus on highest-quality candidates |

**Max Watchlist Size:** 20 symbols per day (configurable, `max_concurrent_positions: 3` limits actual entries)

---

## Entry Criteria

ALL of the following must be TRUE simultaneously for a trade to be taken:

1. **Opening Range Established:** 5 minutes of trading have elapsed since market open (9:30 AM). The OR high and OR low are recorded.
2. **Breakout Candle Close:** A 1-minute candle closes above the OR high. Not just a wick—the close must be above.
3. **Volume Confirmation:** The breakout candle's volume exceeds 1.5× the average volume of the OR candles (`breakout_volume_multiplier: 1.5`).
4. **VWAP Alignment:** Current price is above VWAP. Confirms the breakout is in the direction of the session's dominant flow.
5. **Chase Protection:** Entry price is within 0.5% of the OR high (`chase_protection_pct: 0.005`). Rejects entries where the stock has already moved significantly past the breakout level.
6. **Risk Manager Approval:** Position passes all three risk levels (strategy, cross-strategy, account). Includes daily loss limit, position size limits, cash reserve requirements, and cross-strategy duplicate stock policy.
7. **Within Operating Window:** Current time is between 9:45 AM and 11:30 AM EST.

**Chase Protection:** `chase_protection_pct: 0.005` (0.5%) — entry price must be within 0.5% of the OR high.

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Midpoint of opening range (`stop_placement: "midpoint"`) |
| **Type** | Hard stop (stop-market) |
| **Initial Distance** | Entry price − OR midpoint |

### Profit Targets
| Target | Trigger | Action | Position Affected |
|--------|---------|--------|-------------------|
| T1 | Entry + 0.3R | Exit market | 100% |

*Single target design: Unlike ORB Breakout's T1/T2 split, ORB Scalp exits 100% of the position at a single 0.3R target.*

### Stop Adjustments
No stop adjustments. The position exits at target, stop, time stop, or EOD.

### Time Stop
| Parameter | Value |
|-----------|-------|
| **Max Time in Trade** | 120 seconds (`max_hold_seconds: 120`) |
| **Action if Hit** | Close at market |

*Note: The 120-second time stop is per-position, tracked via `time_stop_seconds` on the SignalEvent. Order Manager enforces this via the poll loop.*

### End of Day
All positions closed at market by 3:50 PM EST.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1% of allocated capital |
| **Max Risk in Dollars** | allocated_capital × 0.01 |
| **Share Calculation** | risk_dollars / (entry_price − stop_price) |
| **Max Concurrent Positions** | 3 |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |

Position size formula: `shares = (allocated_capital × 0.01) / (entry_price − OR_midpoint)`

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Expected Minimum** | 10 seconds |
| **Expected Maximum** | 120 seconds (time stop) |
| **Typical** | 30–90 seconds |

*Note: Unlike ORB Breakout where most exits are time stops at 15 minutes, ORB Scalp targets quick exits at the 0.3R target within seconds to 2 minutes.*

---

## Strategy-Level Risk Limits

| Parameter | Value | Source |
|-----------|-------|--------|
| Max loss per trade | 1% of allocated capital | `orb_scalp.yaml` |
| Max daily loss (this strategy) | 3% of allocated capital | `orb_scalp.yaml` |
| Max consecutive losses before pause | 5 | `orb_scalp.yaml` |
| Max trades per day | 12 | `orb_scalp.yaml` |
| Max concurrent positions | 3 | `orb_scalp.yaml` |
| Max drawdown (suspension threshold) | 15% | `orb_scalp.yaml` benchmarks |

---

## Performance Benchmarks

*Minimum thresholds for the strategy to remain active. Falling below triggers Orchestrator review.*

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | 0.55 | 0.65 |
| Average R-Multiple | 0.25 | 0.35 |
| Profit Factor | 1.2 | 1.5 |
| Sharpe Ratio (20-day rolling) | 0.3 | 1.0 |
| Max Drawdown (from peak) | 0.15 | 0.08 |

---

## Backtest Results

### VectorBT Parameter Exploration

16 combinations per symbol (4 target_r × 4 max_hold_bars), 29 symbols, ~2.9 years of data.

**Parameter Grid:**
- `scalp_target_r`: [0.2, 0.3, 0.4, 0.5]
- `max_hold_bars`: [1, 2, 3, 5] (60s, 120s, 180s, 300s)
- Fixed: `or_minutes=5`, `min_gap_pct=2.0`, `stop_buffer_pct=0.0`

**Aggregate Results (Default Params: target_r=0.3, max_hold_bars=2):**

| Metric | Value |
|--------|-------|
| Total Trades | 1,305 |
| Mean Win Rate | 53.0% |
| Mean Avg R-Multiple | -0.04 |
| Mean Profit Factor | 0.87 |
| Mean Sharpe Ratio | -1.20 |

**Best Parameter Set (by Sharpe, trades > 50):**

| Symbol | target_r | max_hold_bars | Trades | Win Rate | Sharpe | PF |
|--------|----------|---------------|--------|----------|--------|-----|
| SMCI | 0.5 | 5 | 100 | 65.0% | 4.20 | 1.11 |

**Parameter Sensitivity:**

| Parameter | Sensitivity | Notes |
|-----------|------------|-------|
| `scalp_target_r` | Medium | 0.3–0.5 range performs similarly; 0.2 too tight |
| `max_hold_bars` | Medium-High | Longer holds (3–5 bars) generally outperform 1–2 bars |

**Assessment:** The VectorBT exploration shows mixed results. The default parameters (0.3R, 120s) produce marginal returns. The strategy may require:
1. Symbol-specific parameter tuning (SMCI shows strong results)
2. Longer hold times than initially specified
3. Better filtering of entry conditions (RVOL, gap quality)

### Replay Harness Validation

*Not yet completed. Pending walk-forward analysis.*

### Walk-Forward Analysis

**WALK-FORWARD PENDING (2026-04-21).** Not yet completed for ORB Scalp. The VectorBT sweep is directional guidance; serious validation requires replay harness walk-forward similar to ORB Breakout (DEC-073). Placeholder is explicit so the gap is not confused with "completed and unrecorded." Track as part of the Phase 3 completion gate.

---

## Paper Trading Results

*To be filled during Phase 3 paper trading.*

| Metric | Expected (from backtest) | Actual | Deviation |
|--------|--------------------------|--------|-----------|
| Win Rate | 50–60% | | |
| Avg R-Multiple | ~0.0–0.1 | | |
| Profit Factor | 0.8–1.2 | | |
| Trades/Month | 30–60 | | |
| Avg Slippage | TBD | | |
| Target Hit Rate | TBD | | |
| Trading Days | Flexible | | |

---

## Live Trading Results

*To be filled during Phase 4 live trading.*

| Period | Trades | Win Rate | Net P&L | Avg R | Status |
|--------|--------|----------|---------|-------|--------|
| | | | | | |

---

## Known Limitations & Open Questions

1. **Marginal backtest performance:** The VectorBT sweep shows default parameters (0.3R, 120s) producing near-zero or negative returns. Consider:
   - Increasing target to 0.4–0.5R
   - Extending max_hold to 3–5 minutes
   - Adding stricter entry filters

2. **No walk-forward validation:** Unlike ORB Breakout (15 windows, 35 months), ORB Scalp lacks walk-forward analysis. Results are directional but not validated for parameter stability.

3. **Sub-bar resolution:** 1-minute bars provide ~15s synthetic tick granularity (DEC-053). For 120-second holds, time stops resolve at the nearest bar boundary—results are approximate.

4. **Symbol dependence:** Best results concentrated in high-volatility names (SMCI). May need dynamic symbol selection based on regime.

5. **Cross-strategy allocation:** When running alongside ORB Breakout, both strategies may fire on the same symbol. Depends on `duplicate_stock_policy` configuration.

6. **Long only:** Strategy only takes breakouts above the OR high. Short (breakdown below OR low) is deferred.

---

## Universe Filter (Sprint 23)

Declared in `config/strategies/orb_scalp.yaml` under `universe_filter:`. These filters are used by the Universe Manager for O(1) symbol routing.

| Filter | Value | Source |
|--------|-------|--------|
| min_price | 10.0 | Extracted from `get_scanner_criteria()` |
| max_price | 200.0 | Extracted from `get_scanner_criteria()` |
| min_avg_volume | 1,000,000 | Extracted from `get_scanner_criteria()` |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-25 | Initial implementation (Sprint 18) | DEC-123: Single target exit, 0.3R default, 120s hold, midpoint stop. Shared base class with OrbBreakoutStrategy (DEC-120). |
| 1.0.1 | 2026-03-08 | Added Universe Filter section | Sprint 23 Universe Manager integration |

---

## Notes

ORB Scalp is the second strategy through the Incubator Pipeline, sharing infrastructure with ORB Breakout via the `OrbBaseStrategy` base class. The design prioritizes quick profits over large R-multiples, accepting a lower profit factor in exchange for higher trade frequency and faster capital turnover.

The strategy's edge hypothesis is that breakout momentum is front-loaded—profitable breakouts show immediate follow-through. The 120-second time stop captures this: if momentum hasn't materialized within 2 minutes, exit flat rather than waiting.

**Tuning opportunities identified from backtesting:**
1. Increase `scalp_target_r` to 0.4–0.5 based on parameter sensitivity
2. Increase `max_hold_seconds` to 180–300 based on VectorBT results
3. Add symbol-tier filtering (high-volatility names like SMCI perform best)

---

*End of ORB Scalp Strategy Spec Sheet*
