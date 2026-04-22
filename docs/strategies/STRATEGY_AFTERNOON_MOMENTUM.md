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

Consolidation breakout strategy that identifies stocks from the morning gap watchlist that traded in a tight range during the midday lull (12:00–2:00 PM), then enters on breakout above the consolidation range during the afternoon session (2:00–3:30 PM). Thesis: institutional rebalancing and mutual fund flows during "power hour" drive strong moves in stocks that have consolidated after strong mornings. The midday consolidation filters out stocks that faded (not coming back) and stocks that never paused (already ran without you). This strategy is complementary to ORB and VWAP Reclaim — it catches the afternoon continuation on the same universe of gap stocks during the period when earlier strategies have completed their operating windows.

---

## Market Conditions Filter

| Condition | Required Value |
|-----------|---------------|
| Market Regime | Bullish Trending, Bearish Trending, Range-Bound, High Volatility |
| VIX Range | < 30 |
| SPY Trend | Not in Crisis mode |
| Other | None |

Rationale: Momentum breakouts thrive in trending conditions and moderate-to-high volatility where afternoon moves have follow-through. Excluded during Crisis regime where afternoon reversals are common and institutional flows are unpredictable.

**DEC-360 alignment (2026-04-21):** `bearish_trending` is present in this strategy's `allowed_regimes` list in code (`argus/strategies/afternoon_momentum.py:1160`) and was added to the regime table above so this doc no longer contradicts the source.

---

## Operating Window

| Parameter | Value |
|-----------|-------|
| **Consolidation Tracking Start** | 12:00 PM ET |
| **Earliest Entry Time** | 2:00 PM ET |
| **Latest Entry Time** | 3:30 PM ET |
| **Force Close Time** | 3:45 PM ET |
| **Active Days** | Mon–Fri, excluding FOMC days and half-days |

Rationale: The 12:00–2:00 PM window is the "lunch lull" when volume typically dries up and stocks consolidate. The 2:00–3:30 PM entry window captures the afternoon momentum phase when institutional rebalancing and mutual fund flows accelerate. Force close at 3:45 PM provides 15 minutes of buffer before market close.

---

## Scanner Criteria

Afternoon Momentum reuses the same gap scanner as the ORB strategy family (DEC-154). Stocks that gapped up strongly are the natural candidates for midday consolidation and afternoon breakout patterns.

| Filter | Criteria | Rationale |
|--------|----------|-----------|
| Pre-market gap | ≥ 2.0% | Identifies institutional interest / catalyst |
| Price range | $10–$200 | Sufficient liquidity, avoids penny stocks |
| Average daily volume | ≥ 1,000,000 | Ensures tradeable liquidity |
| Relative volume (RVOL) | ≥ 2.0× | Today is an unusual day for this stock |

**Max Watchlist Size:** 20 (shared with ORB family)

---

## Entry Criteria

ALL of the following must be TRUE simultaneously for a trade to be taken. No exceptions (DEC-156).

1. **State is CONSOLIDATED:** Symbol has completed the consolidation phase (midday range confirmed tight)
2. **Within entry window:** Current time ≥ 2:00 PM ET and < 3:30 PM ET
3. **Breakout confirmation:** Candle CLOSES above the consolidation high (not just wicks above)
4. **Volume confirmation:** Breakout candle volume ≥ `volume_multiplier` × average bar volume (default 1.2×)
5. **Chase protection:** Candle close ≤ consolidation_high × (1 + `max_chase_pct`) (default 0.5%)
6. **Valid risk:** Risk per share > 0 (entry price > stop price)
7. **Internal risk limits:** Daily loss, trade count, and position count limits not exceeded
8. **Position count:** Current positions < `max_concurrent_positions` (default 3)

**Chase Protection:** If the breakout candle closes more than `max_chase_pct` (default 0.5%) above the consolidation high, skip the entry — the move has already happened.

---

## State Machine

Afternoon Momentum uses a 5-state machine to track each symbol's progression through the trading day (DEC-155):

```
                    ┌──────────────────────────────────────────────────────┐
                    │                                                      │
                    ▼                                                      │
┌─────────┐     ┌───────────────┐     ┌──────────────┐     ┌─────────┐    │
│WATCHING │────▶│ ACCUMULATING  │────▶│ CONSOLIDATED │────▶│ ENTERED │    │
│         │     │               │     │              │     │         │    │
│(before  │     │(tracking      │     │(range        │     │(terminal│    │
│ 12:00)  │     │ midday range) │     │ confirmed)   │     │ state)  │    │
└─────────┘     └───────┬───────┘     └──────┬───────┘     └─────────┘    │
                        │                    │                            │
                        │   range too wide   │   range widens             │
                        │                    │                            │
                        ▼                    ▼                            │
                   ┌─────────┐          ┌─────────┐                       │
                   │REJECTED │          │REJECTED │───────────────────────┘
                   │         │          │         │
                   │(terminal│          │(terminal│
                   │ state)  │          │ state)  │
                   └─────────┘          └─────────┘
```

| State | Description | Transitions |
|-------|-------------|-------------|
| **WATCHING** | Before 12:00 PM. Ignore all candles, no range tracking. | → ACCUMULATING at 12:00 PM |
| **ACCUMULATING** | 12:00 PM onward. Track midday_high/midday_low. Check consolidation criteria each bar. | → CONSOLIDATED if range/ATR < threshold AND bars ≥ min_consolidation_bars. → REJECTED if range/ATR > max threshold. |
| **CONSOLIDATED** | Range confirmed tight. Continue updating range (can still reject if widens). Watch for breakout after 2:00 PM. | → ENTERED on valid breakout. → REJECTED if range widens past max threshold. |
| **ENTERED** | Position taken. Terminal state for the day. | None (terminal) |
| **REJECTED** | Midday range too wide. Terminal state for the day. | None (terminal) |

**Consolidation Criteria (DEC-153):**
- Range = midday_high - midday_low
- Consolidation confirmed when: `range / ATR-14 < consolidation_atr_ratio` (default 0.75) AND `consolidation_bars >= min_consolidation_bars` (default 30)
- Rejected when: `range / ATR-14 > max_consolidation_atr_ratio` (default 2.0)

---

## Exit Rules

### Stop Loss
| Parameter | Value |
|-----------|-------|
| **Placement** | Below the consolidation low (lowest low during 12:00–2:00 PM period) |
| **Type** | Hard stop (stop-market) |
| **Initial Distance** | consolidation_low × (1 - stop_buffer_pct), buffer default 0.1% |

Rationale: The consolidation low is the natural support level established during the midday lull. If the stock breaks below this level after the breakout, the thesis has failed.

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

### Time Stop (DEC-157)
| Parameter | Value |
|-----------|-------|
| **Max Time in Trade** | min(60 minutes, seconds until 3:45 PM) |
| **Action if Hit** | Close entire remaining position at market |

Rationale: Dynamic time stop calculation ensures late entries (e.g., 3:25 PM) get appropriately short time stops (20 minutes) rather than the full 60 minutes. Earliest-exit-wins logic in Order Manager handles overlap between time stop and T1/T2.

### End of Day (DEC-159)
All positions closed at market by 3:45 PM ET. Order Manager EOD flatten is the safety net.

---

## Position Sizing

| Parameter | Value |
|-----------|-------|
| **Risk Per Trade** | 1.0% of allocated capital |
| **Max Risk in Dollars** | allocated_capital × 0.01 |
| **Share Calculation** | risk_dollars / effective_risk_per_share |
| **Max Concurrent Positions** | 3 |
| **Buying Power Check** | shares × entry_price ≤ available_buying_power |
| **Minimum Risk Floor** | max(risk_per_share, entry_price × 0.003) — prevents oversizing on very tight consolidations |

Rationale: The minimum risk floor (0.3% of entry price) prevents enormous positions when the consolidation range is very tight and the stop is very close to entry. This is the same pattern used in VWAP Reclaim (DEC-140).

---

## Holding Duration

| Parameter | Value |
|-----------|-------|
| **Expected Minimum** | 5 minutes |
| **Expected Maximum** | 60 minutes (time stop) or until 3:45 PM |
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

*To be filled after Sprint 20 VectorBT sweep and walk-forward analysis.*

### VectorBT Parameter Exploration

**Parameter Grid (1,152 combinations):**

| Parameter | Values | Count |
|-----------|--------|-------|
| consolidation_atr_ratio | 0.5, 0.75, 1.0, 1.25 | 4 |
| min_consolidation_bars | 20, 30, 45, 60 | 4 |
| volume_multiplier | 1.0, 1.2, 1.5 | 3 |
| max_chase_pct | 0.003, 0.005, 0.01 | 3 |
| target_1_r | 0.75, 1.0, 1.5 | 3 |
| target_2_r | 1.5, 2.0, 2.5 | 3 values, 8 valid T1×T2 pairs after filter |

**Total combinations:** 4 × 4 × 3 × 3 × 8 (filtered T1/T2 pairs where T2 > T1 + 0.25) = 1,152

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
| **Duplicate stock policy** | ALLOW_ALL (DEC-141) — same symbol can be held by multiple strategies simultaneously |
| **Intended flow** | ORB trades morning breakout → VWAP Reclaim catches mid-morning pullback → Afternoon Momentum catches afternoon continuation |
| **Shared watchlist** | Uses same scanner results as ORB family (DEC-154) |
| **Cross-strategy risk** | max_single_stock_pct (5%) enforced across all strategies |
| **Time coverage** | ORB: 9:35–11:30, VWAP Reclaim: 10:00–12:00, Afternoon Momentum: 2:00–3:30 — fills the afternoon gap |

**Complementary Strategy Design:**

```
Market Hours:  9:30 ─────────────────────────────────────────────────── 4:00
                 │                                                      │
ORB Breakout:    ├─────────────────┤
                 9:35            11:30

VWAP Reclaim:        ├───────────────┤
                   10:00          12:00

Afternoon Momentum:                           ├─────────────────┤
                                            2:00              3:30

Coverage:        │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│░░░░░░░░░░│▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓│
                 │  Morning        │  Midday  │   Afternoon   │
                 │  (ORB + VWAP)   │  (lull)  │  (Momentum)   │
```

---

## Parameter Reference

| Parameter | Config Key | Default | Sweep Min | Sweep Max | Rationale |
|-----------|-----------|---------|-----------|-----------|-----------|
| Consolidation Start | `consolidation_start_time` | "12:00" | — | — | Start of midday tracking window |
| Consolidation ATR Ratio | `consolidation_atr_ratio` | 0.75 | 0.3 | 1.5 | Range/ATR threshold for "tight" consolidation |
| Max Consolidation ATR Ratio | `max_consolidation_atr_ratio` | 2.0 | 1.0 | 3.0 | Range/ATR rejection threshold |
| Min Consolidation Bars | `min_consolidation_bars` | 30 | 15 | 90 | Minimum bars to confirm consolidation |
| Volume Multiplier | `volume_multiplier` | 1.2 | 1.0 | 2.0 | Breakout volume confirmation threshold |
| Max Chase % | `max_chase_pct` | 0.005 | 0.002 | 0.02 | Chase protection threshold (0.5% default) |
| Target 1 R | `target_1_r` | 1.0 | 0.5 | 2.0 | First target R-multiple |
| Target 2 R | `target_2_r` | 2.0 | 1.0 | 3.0 | Second target R-multiple |
| Max Hold Minutes | `max_hold_minutes` | 60 | 15 | 120 | Time stop (dynamic with EOD) |
| Stop Buffer % | `stop_buffer_pct` | 0.001 | 0.0 | 0.01 | Buffer below consolidation_low (0.1% default) |
| Force Close Time | `force_close_time` | "15:45" | — | — | Hard EOD cutoff |
| Max Loss Per Trade | `risk_limits.max_loss_per_trade_pct` | 0.01 | 0.005 | 0.02 | 1% of allocated capital |
| Max Daily Loss | `risk_limits.max_daily_loss_pct` | 0.03 | 0.02 | 0.05 | 3% of allocated capital |
| Max Trades Per Day | `risk_limits.max_trades_per_day` | 6 | 3 | 12 | Daily trade limit |
| Max Concurrent Positions | `risk_limits.max_concurrent_positions` | 3 | 1 | 5 | Position count limit |

> **Note:** Sweep Min/Max are recommended operating ranges for VectorBT parameter exploration. Code validation bounds (Pydantic) may be wider — see `AfternoonMomentumConfig` in `argus/core/config.py` for enforced limits.

---

## Known Divergences

Differences between VectorBT backtest and production implementation:

1. **ATR calculation method:** VectorBT uses SMA(14) of intraday true ranges; production uses Wilder's EMA. Consolidation ratio thresholds may not transfer exactly. Same class as DEC-074.

2. **Entry attempts per day:** VectorBT captures single entry per day for simplicity; live strategy could theoretically retry if first breakout fails and stock re-consolidates (conservative direction for VectorBT — produces fewer trades than live might).

3. **Volume average denominator:** Includes all bars from 9:30 AM (not just consolidation window). Consistent between live and VectorBT.

4. **Provisional results:** All backtest results are provisional until re-validated with Databento exchange-direct data (DEC-132).

---

## Universe Filter (Sprint 23)

Declared in `config/strategies/afternoon_momentum.yaml` under `universe_filter:`. These filters are used by the Universe Manager for O(1) symbol routing.

| Filter | Value | Source |
|--------|-------|--------|
| min_price | 10.0 | Extracted from `get_scanner_criteria()` |
| max_price | 200.0 | Extracted from `get_scanner_criteria()` |
| min_avg_volume | 1,000,000 | Extracted from `get_scanner_criteria()` |

---

## Version History

| Version | Date | Changes | Rationale |
|---------|------|---------|-----------|
| 1.0.0 | 2026-02-26 | Initial specification | Sprint 20 design |
| 1.0.1 | 2026-03-08 | Added Universe Filter section | Sprint 23 Universe Manager integration |

---

## Notes

- Inherits directly from BaseStrategy (DEC-152), not from a shared consolidation base class. Extraction deferred (DEF-025) until a second consolidation-based strategy is designed.
- ATR-14 is already computed by IndicatorEngine (Sprint 12.5, DEC-092). No new indicator infrastructure needed.
- This is ARGUS's fourth strategy and the first targeting afternoon sessions exclusively.
- Dynamic time stop calculation (DEC-157) ensures late-session entries have appropriately short time stops.
- Trailing stop deferred to V2 (DEC-158, DEF-024) — T1/T2 fixed targets are proven across all four strategies.
- All backtest results are provisional until re-validated with Databento exchange-direct data (DEC-132).
- 1-minute bar resolution is adequate for this strategy's 5–60 minute hold duration.
- State machine has 5 states: WATCHING → ACCUMULATING → CONSOLIDATED → ENTERED (terminal) or REJECTED (terminal).
- Consolidation range updates continuously through CONSOLIDATED state — if range widens beyond `max_consolidation_atr_ratio` (default 2.0), transitions to REJECTED.
- Minimum risk floor (0.3% of entry price) prevents enormous positions from very tight consolidation where the stop is extremely close to entry.

---

*End of Strategy Spec Sheet*
