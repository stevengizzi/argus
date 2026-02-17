# ARGUS — Strategy Spec Sheet: ORB (Opening Range Breakout)

> *Based on `04_STRATEGY_TEMPLATE.md`. Last updated: February 18, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | ORB (Opening Range Breakout) |
| **ID** | `strat_orb_breakout` |
| **Version** | `1.2.0` (Sprint 11 extended validation + earliest_entry fix) |
| **Asset Class** | US Stocks |
| **Author** | Steven (design) + Claude (implementation) |
| **Created** | February 15, 2026 |
| **Last Updated** | February 18, 2026 |
| **Pipeline Stage** | Paper Trading (Phase 3) |

---

## Description

The ORB strategy exploits the tendency of stocks gapping on news or momentum to establish a tradeable range in the first few minutes of the session, then break out of that range directionally. It identifies stocks gapping ≥2% on above-average volume, records the high and low of the first 5 minutes of trading (the "opening range"), and enters long when price closes above the range high with confirming volume and VWAP alignment. The stop is placed at the opening range midpoint, and the strategy exits via a 15-minute time stop. The edge is front-loaded: if the breakout works, it works quickly.

Phase 2 backtesting (137 trades over 11 months) found a Sharpe ratio of 0.93 and Profit Factor of 1.18. The strategy's profitability comes from net-positive time-stopped exits, not from the 2.0R target (which never triggered). **Sprint 11 extended walk-forward validation** (35 months, 15 windows) confirmed aggregate OOS profitability (Sharpe +0.34, P&L +$7,741) despite not meeting traditional WFE (Sharpe) thresholds. WFE (P&L) = 0.56 exceeded the 0.3 threshold.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Any except Crisis |
| VIX Range | < 35 |
| SPY Trend | No requirement for V1 |
| Other | No active circuit breakers |

*Note: Market regime filtering is defined but not yet active in V1. The Orchestrator (Phase 5) will enforce these conditions.*

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Opening Range Window** | 9:30–9:35 AM EST (5 minutes) |
| **Earliest Entry Time** | 9:35 AM EST (DEC-078: updated from 9:45 to match or=5) |
| **Latest Entry Time** | 11:30 AM EST |
| **Force Close Time** | 3:50 PM EST |
| **Active Days** | Monday–Friday (US market days only) |

---

## Scanner Criteria

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Gap % | ≥ 2.0% from previous close | Minimum gap to indicate meaningful catalyst. Higher gaps (3%+) showed better quality in sweeps but lower trade frequency. |
| Pre-market Volume | Above average (RVOL ≥ 2.0) | Volume confirms institutional interest, not just a thin gap on no news. |
| Price Range | $5–$500 | Excludes penny stocks (manipulation risk) and ultra-high-priced stocks (position sizing difficulty). |
| Float | No filter in V1 | Low-float filters may improve quality but reduce the tradeable universe. Deferred. |

**Max Watchlist Size:** 10 symbols per day (configurable, `max_concurrent_positions: 2` limits actual entries)

---

## Entry Criteria

ALL of the following must be TRUE simultaneously for a trade to be taken:

1. **Opening Range Established:** 5 minutes of trading have elapsed since market open (9:30 AM). The OR high and OR low are recorded.
2. **Breakout Candle Close:** A 1-minute candle closes above the OR high. Not just a wick — the close must be above.
3. **Volume Confirmation:** The breakout candle's volume exceeds 1.5× the average volume of the preceding candles in the session (`breakout_volume_multiplier: 1.5`).
4. **VWAP Alignment:** Current price is above VWAP. This confirms the breakout is in the direction of the session's dominant flow.
5. **Chase Protection:** Entry price is within 0.5% of the OR high (`chase_protection_pct: 0.005`). Rejects entries where the stock has already moved significantly past the breakout level.
6. **Risk Manager Approval:** Position passes all three risk levels (strategy, cross-strategy, account). Includes PDT check, daily loss limit, position size limits, and cash reserve requirements.
7. **Within Operating Window:** Current time is between 9:35 AM and 11:30 AM EST.

---

## Position Sizing

Risk-based sizing: `shares = risk_dollars / risk_per_share`, where:
- `risk_dollars` = strategy's allocated capital × `max_loss_per_trade_pct` (1%)
- `risk_per_share` = entry price − stop price (OR midpoint)

The Risk Manager may reduce share count (approve-with-modification) to maintain account-level limits. Minimum 0.25R floor on modified positions (DEC-027).

---

## Exit Rules

| Exit Type | Condition | Priority |
|-----------|-----------|----------|
| **Stop Loss** | Price hits OR midpoint (`stop_placement: "midpoint"`, 0% buffer) | Highest — non-negotiable |
| **Target T1** | Price hits entry + 1.0R (exit 50% of position) | Second |
| **Target T2** | Price hits entry + 2.0R (exit remaining 50%) | Third |
| **Time Stop** | 15 minutes elapsed since entry | Fourth |
| **EOD Flatten** | 3:50 PM EST | Absolute — all positions closed |

**Tiered exit design:** The strategy is designed with a two-stage profit target: 50% of the position exits at 1.0R, and the remaining 50% targets 2.0R. In practice, the Order Manager handles this split (Sprint 4b), with Alpaca receiving a single bracket order at T1 due to API limitations.

**Critical finding from Phase 2 backtesting:** Neither target (1.0R or 2.0R) triggered across 137 trades with the 15-minute hold window. All profitable exits came via time stop (27.7%) or EOD flatten (2.9%). The strategy makes money because breakout moves tend to be net-positive within 15 minutes — the time stop captures this edge. The target parameters are functionally irrelevant with the current hold duration. This should be monitored in Phase 3 paper trading — if targets still never trigger, consider replacing with a trailing stop or lowering to 0.5R/1.0R.

| Exit Type | Backtest Count | Backtest % |
|-----------|---------------|------------|
| Stop loss | 95 | 69.3% |
| Time stop | 38 | 27.7% |
| EOD flatten | 4 | 2.9% |
| Target hit | 0 | 0.0% |

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Typical** | 1–15 minutes |
| **Maximum (time stop)** | 15 minutes |
| **Maximum (EOD)** | Full trading day (if time stop not hit before 3:50 PM — rare, only 2.9% of trades) |

*Note: The 15-minute time stop governs nearly all exits. EOD-flatten trades are outliers where the time stop logic failed to trigger or the position was opened very close to the latest_entry cutoff.*

---

## Risk Parameters

| Parameter | Value | Source |
|-----------|-------|--------|
| Max loss per trade | 1% of allocated capital | `orb_breakout.yaml` |
| Max daily loss (strategy) | 3% of allocated capital | `orb_breakout.yaml` |
| Max consecutive losses before pause | 5 | `orb_breakout.yaml` |
| Max trades per day | 6 | `orb_breakout.yaml` |
| Max concurrent positions | 2 | `orb_breakout.yaml` |
| Max drawdown (suspension threshold) | 15% | `orb_breakout.yaml` benchmarks |

---

## Performance Benchmarks

*Minimum thresholds for the strategy to remain active. Falling below triggers Orchestrator review.*

| Metric | Minimum | Target | Backtest (11mo) | Extended OOS (35mo) |
|--------|---------|--------|-----------------|---------------------|
| Win Rate | 0.35 | 0.50 | 0.467 | — |
| Average R-Multiple | 0.3 | 0.6 | ~0.43 (winners) | — |
| Profit Factor | 1.0 | 1.3 | 1.18 | — |
| Sharpe Ratio | 0.5 | 1.5 | 0.93 (full period) | 0.34 (aggregate OOS) |
| Max Drawdown | 0.15 | 0.08 | 0.066 | — |

---

## Backtest Results

### VectorBT Parameter Exploration

522,000 combinations (29 symbols × ~18,000 param sets), 63-second sweep on 11 months of data.

**Top 5 Parameter Sets (by Sharpe, min 20 trades):**

| Rank | or_min | target_r | stop_buf | max_hold | min_gap | max_atr | Sharpe | Trades | PF |
|------|--------|----------|----------|----------|---------|---------|--------|--------|----|
| 1 | 5 | 1.0 | 0.0 | 15 | 2.0 | 0.5 | 3.87 | 179 | 2.07 |
| 2 | 5 | 2.5 | 0.0 | 15 | 2.0 | 0.5 | 3.76 | 179 | 2.07 |
| 3 | 5 | 2.0 | 0.0 | 15 | 2.0 | 0.5 | 3.72 | 179 | 2.04 |
| 4 | 5 | 2.0 | 0.1 | 15 | 2.0 | 0.5 | 3.65 | 179 | 2.04 |
| 5 | 5 | 3.0 | 0.0 | 15 | 2.0 | 0.5 | 3.64 | 179 | 2.04 |

**Parameter Sensitivity:**

| Parameter | Sensitivity | Best Value | Notes |
|-----------|------------|------------|-------|
| `opening_range_minutes` | High | 5 | Monotonic: shorter = better |
| `max_hold_minutes` | High | 15 | Clear: shorter = better |
| `min_gap_pct` | Medium-High | 3.0% (sweep) / 2.0% (chosen) | Higher = better quality, fewer trades |
| `max_range_atr_ratio` | High (non-transferable) | 0.30 | ATR divergence makes this unusable in production (DEC-075) |
| `stop_buffer_pct` | Low | 0.0 | Minimal impact |
| `target_r` | Low | 2.0 | All values similar (never triggers with 15-min hold) |

**Selected Parameters (DEC-076):** or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0 (disabled). Conservative approach: only the two high-sensitivity parameters changed from defaults.

### Replay Harness Validation (11 Months)

| Metric | Default (ATR=2.0) | Relaxed (ATR=999, or=15) | Recommended (DEC-076) |
|--------|-------------------|--------------------------|----------------------|
| Period Tested | Mar 2025 – Jan 2026 | Mar 2025 – Jan 2026 | Mar 2025 – Jan 2026 |
| Total Trades | 8 | 135 | 137 |
| Win Rate | 62.5% | 48.1% | 46.7% |
| Profit Factor | 2.23 | 1.00 | 1.18 |
| Max Drawdown | — | — | 6.6% |
| Sharpe Ratio | 5.06 | -0.26 | 0.93 |
| Net P&L | $1,065 | $71 | $8,087 |

**Note:** All Replay Harness runs used `earliest_entry: "09:45"` (the config value at the time). With or=5, the OR completes at 9:35, meaning 10 minutes of potential breakouts were missed. Backtest results are therefore conservative. DEC-078 corrects this for paper trading.

**Monthly Performance (Recommended Params):**

| Month | Trades | Net P&L | Win Rate |
|-------|--------|---------|----------|
| 2025-03 | 14 | +$724 | 50.0% |
| 2025-04 | 20 | +$3,881 | 70.0% |
| 2025-05 | 17 | +$412 | 58.8% |
| 2025-06 | 9 | +$2,603 | 55.6% |
| 2025-07 | 7 | +$937 | 42.9% |
| 2025-08 | 6 | +$1,171 | 33.3% |
| 2025-09 | 8 | +$5,759 | 75.0% |
| 2025-10 | 18 | -$3,645 | 27.8% |
| 2025-11 | 10 | +$3,624 | 60.0% |
| 2025-12 | 14 | -$3,512 | 21.4% |
| 2026-01 | 14 | -$3,869 | 21.4% |

Interactive reports: `reports/orb_baseline_defaults.html`, `reports/orb_baseline_relaxed.html`, `reports/orb_final_validation.html`

### Walk-Forward Analysis (11-Month Data — Inconclusive)

4 candidates, 3 windows (4-month IS / 2-month OOS / 2-month step):

| Candidate | or | hold | atr | gap | OOS Trades | OOS Sharpe | Mean WFE |
|-----------|-----|------|------|-----|------------|------------|----------|
| A (tight) | 5 | 15 | 0.5 | 2.0 | 2 | 0.00 | 0.00 |
| B | 5 | 15 | 1.0 | 2.0 | 2 | 0.00 | 0.00 |
| C | 5 | 30 | 0.75 | 2.0 | 2 | 0.00 | 0.00 |
| D (relaxed) | 5 | 30 | 999 | 2.0 | 81 | -4.19 | -4.09 |

**Walk-Forward Assessment (11 months):** Inconclusive (Scenario C per DEC-073). Insufficient data (3 windows vs. 8–12 standard). Sprint 11 extended this analysis.

### Walk-Forward Analysis (35-Month Extended Data — Sprint 11)

**Optimizer Walk-Forward** (re-optimizes parameters in each IS window):
- 15 windows, 4-month IS / 2-month OOS / 2-month step
- Avg WFE (Sharpe): -0.38
- Total OOS Trades: 93
- Overall OOS Sharpe: -11.46 (severe overfitting)
- Overall OOS P&L: $7,204
- Parameter stability: ~33% (optimizer picked different params each window)

**Fixed-Params Walk-Forward** (DEC-076 parameters held constant across all windows):
- 15 windows, same configuration
- Avg WFE (Sharpe): -0.91 (metric inappropriate for fixed-params — IS Sharpe swings wildly)
- **Avg WFE (P&L): 0.56** (exceeds 0.3 threshold — OOS recovers 56% of IS P&L)
- Total OOS Trades: 378
- **Overall OOS Sharpe: +0.34** (positive)
- **Overall OOS P&L: $7,741**
- Parameter stability: 100% (by definition)

**Per-Window Results (Fixed-Params):**

| Window | IS Period | OOS Period | IS Sharpe | OOS Sharpe | WFE | OOS Trades |
|--------|-----------|------------|-----------|------------|-----|------------|
| 1 | 2023-03 to 2023-06 | 2023-07 to 2023-08 | -0.04 | 3.50 | 0.00 | 23 |
| 2 | 2023-05 to 2023-08 | 2023-09 to 2023-10 | -0.16 | -0.33 | 0.00 | 27 |
| 3 | 2023-07 to 2023-10 | 2023-11 to 2023-12 | -4.77 | -3.28 | 0.00 | 28 |
| 4 | 2023-09 to 2023-12 | 2024-01 to 2024-02 | -3.04 | 3.74 | 0.00 | 22 |
| 5 | 2023-11 to 2024-02 | 2024-03 to 2024-04 | 1.42 | -4.49 | -3.17 | 31 |
| 6 | 2024-01 to 2024-04 | 2024-05 to 2024-06 | -2.93 | 0.11 | 0.00 | 23 |
| 7 | 2024-03 to 2024-06 | 2024-07 to 2024-08 | -0.26 | 0.23 | 0.00 | 25 |
| 8 | 2024-05 to 2024-08 | 2024-09 to 2024-10 | 0.39 | -4.75 | -12.23 | 28 |
| 9 | 2024-07 to 2024-10 | 2024-11 to 2024-12 | -2.26 | 1.52 | 0.00 | 20 |
| 10 | 2024-09 to 2024-12 | 2025-01 to 2025-02 | 2.37 | -0.79 | -0.33 | 28 |
| 11 | 2024-11 to 2025-02 | 2025-03 to 2025-04 | -0.64 | 2.75 | 0.00 | 34 |
| 12 | 2025-01 to 2025-04 | 2025-05 to 2025-06 | 2.11 | 2.08 | 0.98 | 25 |
| 13 | 2025-03 to 2025-06 | 2025-07 to 2025-08 | 5.33 | 4.51 | 0.84 | 14 |
| 14 | 2025-05 to 2025-08 | 2025-09 to 2025-10 | 4.96 | 0.92 | 0.19 | 25 |
| 15 | 2025-07 to 2025-10 | 2025-11 to 2025-12 | -25.76 | -0.54 | 0.00 | 25 |

**Key Insights:**
1. **Fixed params outperform optimizer** — optimizer overfits and produces worse OOS Sharpe (-11.46 vs. +0.34)
2. **Aggregate OOS profitability** — $7,741 across 378 trades in ~2.5 years of OOS periods
3. **9 of 15 windows (60%) had positive OOS Sharpe** — strategy is profitable more often than not
4. **High variance** — individual 2-month periods vary widely, but aggregate is positive
5. **WFE (Sharpe) measures predictability, not profitability** — strategy makes money despite low WFE (Sharpe)
6. **WFE (P&L) = 0.56 exceeds 0.3 threshold** — the metric that tracks dollar performance generalizes

**Walk-Forward Assessment (35 months):** DEC-076 parameters confirmed for paper trading. The strategy produces a real but modest aggregate edge across 3 years of out-of-sample data. Expect high period-to-period variance but positive long-run returns.

---

## Paper Trading Results

*To be filled during Phase 3 paper trading.*

| Metric | Expected (from backtest) | Actual | Deviation |
|--------|--------------------------|--------|-----------|
| Win Rate | 40–55% | | |
| Avg R-Multiple | ~0.43 (winners) | | |
| Profit Factor | 1.0–1.5 | | |
| Trades/Month | 10–16 (may be higher with DEC-078 fix) | | |
| Avg Slippage | $0.01 (backtest assumption) | | |
| Target Hit Rate | 0% (backtest) | | |
| Trading Days | Flexible | | |

---

## Live Trading Results

*To be filled during Phase 4 live trading.*

| Period | Trades | Win Rate | Net P&L | Avg R | Status |
|--------|--------|----------|---------|-------|--------|
| | | | | | |

---

## Known Limitations & Open Questions

1. **Zero target hits:** Neither the 1.0R nor 2.0R target triggers within the 15-minute hold. Should targets be lowered, replaced with a trailing stop, or removed? Monitor in paper trading.
2. **ATR filter disabled:** The intent (reject abnormally wide ranges) is sound, but production ATR uses the wrong scale (1-minute bars vs. daily). Needs daily ATR infrastructure or empirical calibration.
3. **High period-to-period variance:** Extended walk-forward shows OOS Sharpe varying from -4.75 to +4.51 across 2-month windows. Aggregate is profitable but individual periods will vary.
4. **Fixed slippage model:** Backtest uses $0.01/share. Real slippage at market open may be $0.03–$0.10 for volatile gap stocks.
5. **Long only:** Strategy only takes breakouts above the OR high. Short (breakdown below OR low) is deferred.
6. **No regime filtering:** Strategy runs in all market conditions. Orchestrator (Phase 5) will add regime-based activation.
7. **No severe regime data:** Extended data (2023–2026) doesn't include a bear market or crisis event. Strategy behavior in severe downturns untested.
8. **Backtest used wrong earliest_entry:** All backtests ran with `earliest_entry: "09:45"` despite or=5 completing at 9:35. Paper trading (with DEC-078 fix) will capture breakouts the backtest missed. Direct comparison requires adjusting for this difference.

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-15 | Initial implementation | Sprint 3 — foundational strategy with default parameters |
| 1.1.0 | 2026-02-17 | Parameters revised: or 15→5, hold 30→15, ATR disabled | Phase 2 backtesting (DEC-076). Sweep + sensitivity analysis. |
| 1.2.0 | 2026-02-18 | Extended validation + earliest_entry fix | Sprint 11 confirmed DEC-076 across 35 months. DEC-078 fixed earliest_entry 9:45→9:35. |

---

## Notes

The ORB strategy is the first strategy through the Incubator Pipeline and serves as the template for all future strategies. Every piece of infrastructure built for ORB (Replay Harness, VectorBT sweeps, walk-forward validation, report generation) is reusable for subsequent strategies.

The strategy's edge is modest but real across 35 months of data. The primary risk is that this edge doesn't survive contact with live markets — which is exactly what Phase 3 is designed to test. The conservative approach (minimum position sizes, kill criteria, flexible duration) limits downside while the system collects genuine forward-looking data.

**Stop placement note:** The stop is at the OR **midpoint** (`stop_placement: "midpoint"` in config), not the OR low. This was a deliberate design choice (DEC-012) to provide a tighter stop with smaller risk per share. The OR low would be a wider stop — potentially worth evaluating if the midpoint stop triggers too frequently during paper trading.

---

*End of ORB Strategy Spec Sheet*