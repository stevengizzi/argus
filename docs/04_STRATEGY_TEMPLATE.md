# ARGUS — Strategy Spec Sheet Template

> *Copy this template for each new strategy. Fill in every field. Leave nothing as "TBD" before advancing past the Concept stage. File naming convention: `STRATEGY_[NAME].md`*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | |
| **ID** | `strat_` (e.g., `strat_orb_breakout`) |
| **Version** | `1.0.0` (semver: major.minor.patch) |
| **Asset Class** | US Stocks / Crypto / Forex / Futures |
| **Author** | |
| **Created** | |
| **Last Updated** | |
| **Pipeline Stage** | Concept / Exploration / Validation / Ecosystem Replay / Paper / Live Min / Live Full / Monitoring / Suspended / Retired |

---

## Description

*One paragraph explaining the core thesis of this strategy. What market behavior does it exploit? Why does it work?*

---

## Market Conditions Filter

*Under what market regime is this strategy eligible to run? The Orchestrator checks these conditions before activating the strategy each day.*

| Condition | Required Value |
|-----------|---------------|
| Market Regime | (e.g., Bullish Trending, any except Crisis) |
| VIX Range | (e.g., < 30) |
| SPY Trend | (e.g., Above 20-day MA) |
| Other | |

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Earliest Entry Time** | (e.g., 9:45 AM EST) |
| **Latest Entry Time** | (e.g., 11:30 AM EST) |
| **Force Close Time** | (e.g., 3:50 PM EST) |
| **Active Days** | (e.g., Mon–Fri, excluding FOMC days) |

---

## Scanner Criteria

*How does this strategy find trade candidates? All criteria must be met for a stock to be added to this strategy's watchlist.*

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| | | |
| | | |
| | | |
| | | |

**Max Watchlist Size:** ___

---

## Entry Criteria

*ALL of the following must be TRUE simultaneously for a trade to be taken. No exceptions.*

1. **[Criterion Name]:** [Precise description]
2. **[Criterion Name]:** [Precise description]
3. **[Criterion Name]:** [Precise description]
4. **[Criterion Name]:** [Precise description]
5. **[Criterion Name]:** [Precise description]

**Chase Protection:** [Rule for skipping entries that have already moved too far]

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | (e.g., Midpoint of opening range) |
| **Type** | Hard stop (stop-market) / Trailing / ATR-based |
| **Initial Distance** | (e.g., Entry - Stop = X, or ATR-based formula) |

### Profit Targets
| Target | Trigger | Action | Position Affected |
|--------|---------|--------|-------------------|
| T1 | | | |
| T2 | | | |
| T3 (if applicable) | | | |

### Stop Adjustments
| Trigger | New Stop Level |
|---------|---------------|
| T1 hit | (e.g., Move stop to breakeven) |
| T2 hit | (e.g., Trail by 1 ATR) |

### Time Stop
| Parameter | Value |
|-----------|-------|
| **Max Time in Trade (to T1)** | (e.g., 30 minutes) |
| **Action if Hit** | (e.g., Close at market) |

### End of Day
All positions closed at market by [time].

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | ___% of allocated capital |
| **Max Risk in Dollars** | Calculated: allocated_capital × risk_pct |
| **Share Calculation** | risk_dollars / (entry_price - stop_price) |
| **Max Concurrent Positions** | |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Expected Minimum** | (e.g., 10 seconds) |
| **Expected Maximum** | (e.g., 45 minutes) |
| **Average (from backtest)** | (fill in after backtesting) |

---

## Strategy-Level Risk Limits

| Parameter | Value |
|-----------|-------|
| **Max Loss Per Trade** | |
| **Max Daily Loss (this strategy)** | ___% of allocated capital |
| **Max Consecutive Losses Before Pause** | |
| **Max Trades Per Day** | |

---

## Performance Benchmarks

*Minimum thresholds to remain in active deployment. Falling below triggers Orchestrator review.*

| Metric | Minimum | Target |
|--------|---------|--------|
| Win Rate | | |
| Average R-Multiple | | |
| Profit Factor | | |
| Sharpe Ratio (20-day rolling) | | |
| Max Drawdown (from peak) | | |

---

## Backtest Results

*Filled in after Exploration and Validation phases.*

### VectorBT Exploration
| Parameter Set | Win Rate | Avg R | Profit Factor | Max DD | Sharpe | Notes |
|---------------|----------|-------|---------------|--------|--------|-------|
| | | | | | | |
| | | | | | | |
| | | | | | | |

**Selected Parameters:** [Which combination was chosen and why]

### Backtrader Validation
| Metric | Value |
|--------|-------|
| Period Tested | |
| Total Trades | |
| Win Rate | |
| Average Winner | |
| Average Loser | |
| Profit Factor | |
| Max Drawdown | |
| Sharpe Ratio | |

### Ecosystem Replay
| Metric | Value |
|--------|-------|
| Period Replayed | |
| Concurrent Strategies | |
| Conflicts with Other Strategies | |
| Capital Allocation Used | |
| Net Contribution to Portfolio | |

---

## Paper Trading Results

| Metric | Expected (from backtest) | Actual | Deviation |
|--------|--------------------------|--------|-----------|
| Win Rate | | | |
| Avg R-Multiple | | | |
| Profit Factor | | | |
| Avg Slippage | N/A | | |
| Trading Days | Min 20 | | |

---

## Live Trading Results

*Ongoing tracking after promotion to live.*

| Period | Trades | Win Rate | Net P&L | Avg R | Status |
|--------|--------|----------|---------|-------|--------|
| | | | | | |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | | Initial specification | |
| | | | |

---

## Notes

*Any additional observations, caveats, known limitations, or ideas for improvement.*

---

*End of Strategy Spec Sheet*
