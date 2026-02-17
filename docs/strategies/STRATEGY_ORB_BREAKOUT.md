# ARGUS — Strategy Spec Sheet: ORB (Opening Range Breakout)

> *Based on `04_STRATEGY_TEMPLATE.md`. Last updated: February 17, 2026.*

---

## Strategy Identity

| Field | Value |
|-------|-------|
| **Name** | ORB (Opening Range Breakout) |
| **ID** | `strat_orb_breakout` |
| **Version** | `1.1.0` (parameters revised from Phase 2 backtesting) |
| **Asset Class** | US Stocks |
| **Author** | Steven (design) + Claude (implementation) |
| **Created** | February 15, 2026 |
| **Last Updated** | February 17, 2026 |
| **Pipeline Stage** | Paper Trading (Phase 3) |

---

## Description

The ORB strategy exploits the tendency of stocks gapping on news or momentum to establish a tradeable range in the first few minutes of the session, then break out of that range directionally. It identifies stocks gapping ≥2% on above-average volume, records the high and low of the first 5 minutes of trading (the "opening range"), and enters long when price closes above the range high with confirming volume and VWAP alignment. The stop is placed at the opening range low, and the strategy exits via a 15-minute time stop. The edge is front-loaded: if the breakout works, it works quickly.

Phase 2 backtesting (137 trades over 11 months) found a Sharpe ratio of 0.93 and Profit Factor of 1.18. The strategy's profitability comes from net-positive time-stopped exits, not from the 2.0R target (which never triggered). **Sprint 11 extended walk-forward validation** (35 months, 15 windows) confirmed aggregate OOS profitability (Sharpe +0.34, P&L +$7,741) despite not meeting traditional WFE thresholds.

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
| **Earliest Entry Time** | 9:45 AM EST |
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
7. **Within Operating Window:** Current time is between 9:45 AM and 11:30 AM EST.

---

## Position Sizing

Risk-based sizing: `shares = risk_dollars / risk_per_share`, where:
- `risk_dollars` = strategy's allocated capital × `max_loss_per_trade_pct` (1%)
- `risk_per_share` = entry price − stop price (OR low)

The Risk Manager may reduce share count (approve-with-modification) to maintain account-level limits. Minimum 0.25R floor on modified positions (DEC-027).

---

## Exit Rules

| Exit Type | Condition | Priority |
|-----------|-----------|----------|
| **Stop Loss** | Price hits OR low (0% buffer) | Highest — non-negotiable |
| **Target** | Price hits entry + 2.0R | Second — but see note below |
| **Time Stop** | 15 minutes elapsed since entry | Third |
| **EOD Flatten** | 3:50 PM EST | Absolute — all positions closed |

**Critical finding from Phase 2 backtesting:** The 2.0R target produced zero hits across 137 trades. All profitable exits came via time stop (27.7%) or EOD flatten (2.9%). The strategy makes money because breakout moves tend to be net-positive within 15 minutes — the time stop captures this edge. The target_r parameter is functionally irrelevant with the current 15-minute hold. This should be monitored in Phase 3 paper trading and potentially replaced with a trailing stop or lower target.

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
| **Typical** | 5–15 minutes |
| **Maximum (time stop)** | 15 minutes |
| **Maximum (EOD)** | Full trading day (if time stop and target both not hit before 3:50 PM) |
| **Backtest average** | 49 minutes (skewed by EOD-flatten outliers) |

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

| Metric | Minimum | Target | Backtest Actual |
|--------|---------|--------|-----------------|
| Win Rate | 0.35 | 0.50 | 0.467 |
| Average R-Multiple | 0.3 | 0.6 | ~0.43 (winning trades) |
| Profit Factor | 1.0 | 1.3 | 1.18 |
| Sharpe Ratio (20-day rolling) | 0.5 | 1.5 | 0.93 (full period) |
| Max Drawdown (from peak) | 0.15 | 0.08 | 0.066 |

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
| `max_range_atr_ratio` | High (non-transferable) | 0.30 | ATR divergence makes this unusable in production |
| `stop_buffer_pct` | Low | 0.0 | Minimal impact |
| `target_r` | Low | 2.0 | All values similar |

**Selected Parameters (DEC-076):** or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, atr=999.0 (disabled). Conservative approach: only the two high-sensitivity parameters changed from defaults.

### Replay Harness Validation

| Metric | Default (ATR=2.0) | Relaxed (ATR=999, or=15) | Recommended (DEC-076) |
|--------|-------------------|--------------------------|----------------------|
| Period Tested | Mar 2025 – Jan 2026 | Mar 2025 – Jan 2026 | Mar 2025 – Jan 2026 |
| Total Trades | 8 | 135 | 137 |
| Win Rate | 62.5% | 48.1% | 46.7% |
| Profit Factor | 2.23 | 1.00 | 1.18 |
| Max Drawdown | — | — | 6.6% |
| Sharpe Ratio | 5.06 | -0.26 | 0.93 |
| Net P&L | $1,065 | $71 | $8,087 |
| Avg Hold Time | 31 min | 111 min | 49 min |

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

**Walk-Forward Assessment (11 months):** Inconclusive (Scenario C per DEC-073). No candidate achieved WFE ≥ 0.3. Root cause: insufficient data (3 windows vs. 8–12 standard).

### Walk-Forward Analysis (35-Month Extended Data — Sprint 11)

Dataset extended to March 2023 – January 2026 (35 months, 7M bars, 29 symbols). 15 walk-forward windows (4-month IS / 2-month OOS / 2-month step).

**Summary Results:**

| Mode | Windows | Avg WFE (Sharpe) | OOS Trades | OOS Sharpe | OOS P&L |
|------|---------|-----------------|------------|------------|---------|
| Optimizer | 15 | -0.38 | 93 | -11.46 | $7,204 |
| Fixed-params (DEC-076) | 15 | -0.91 | 378 | **+0.34** | **$7,741** |

**Per-Window Detail (Fixed-Params):**
- 10/15 windows (67%) had positive OOS Sharpe
- Best window: +4.51 Sharpe (Jul–Aug 2025)
- Worst window: -4.75 Sharpe (Sep–Oct 2024)

**Key Findings:**
1. **Fixed params outperform optimizer** — optimizer overfits and produces worse OOS Sharpe (-11.46 vs. +0.34)
2. **Aggregate OOS profitability** — $7,741 across 378 trades in ~2.5 years of OOS periods
3. **High variance** — individual 2-month periods vary widely, but aggregate is positive
4. **WFE measures predictability, not profitability** — the strategy makes money despite low WFE

**Walk-Forward Assessment (35 months):** Traditional WFE ≥ 0.3 threshold not met. However, aggregate OOS returns are positive. Decision: **Proceed with paper trading using DEC-076 parameters.** Expect high period-to-period variance but aggregate profitability.

---

## Paper Trading Results

*To be filled during Phase 3 paper trading.*

| Metric | Expected (from backtest) | Actual | Deviation |
|--------|--------------------------|--------|-----------|
| Win Rate | 40–55% | | |
| Avg R-Multiple | ~0.43 (winners) | | |
| Profit Factor | 1.0–1.5 | | |
| Trades/Month | 10–16 | | |
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

1. **Zero target hits:** The 2.0R target never triggers within the 15-minute hold. Should the target be lowered, replaced with a trailing stop, or removed? Monitor in paper trading.
2. **ATR filter disabled:** The intent (reject abnormally wide ranges) is sound, but production ATR uses the wrong scale. Needs daily ATR infrastructure or empirical calibration.
3. **High period-to-period variance:** Extended walk-forward shows OOS Sharpe varying from -4.75 to +4.51 across 2-month windows. Aggregate is profitable but individual periods will vary.
4. **Fixed slippage model:** Backtest uses $0.01/share. Real slippage at market open may be $0.03–$0.10 for volatile gap stocks.
5. **Long only:** Strategy only takes breakouts above the OR high. Short (breakdown below OR low) is deferred.
6. **No regime filtering:** Strategy runs in all market conditions. Orchestrator (Phase 5) will add regime-based activation.
7. **No severe regime data:** Extended data (2023–2026) doesn't include a bear market or crisis event. Strategy behavior in severe downturns untested.

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-15 | Initial implementation | Sprint 3 — foundational strategy with default parameters |
| 1.1.0 | 2026-02-17 | Parameters revised: or 15→5, hold 30→15, ATR disabled | Phase 2 backtesting (DEC-076). Sweep + sensitivity analysis. |

---

## Notes

The ORB strategy is the first strategy through the Incubator Pipeline and serves as the template for all future strategies. Every piece of infrastructure built for ORB (Replay Harness, VectorBT sweeps, walk-forward validation, report generation) is reusable for subsequent strategies.

The strategy's edge is modest (Sharpe 0.93, PF 1.18) but real in backtesting. The primary risk is that this edge doesn't survive contact with live markets — which is exactly what Phase 3 is designed to test. The conservative approach (minimum position sizes, kill criteria, flexible duration) limits downside while the system collects genuine forward-looking data.

---

*End of ORB Strategy Spec Sheet*
