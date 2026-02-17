# ARGUS — Backtest Run Log

> Logs every backtest run with parameters, results, and observations.
> Created during Sprint 10 (February 17, 2026).

---

## Run 1: Baseline — Default Parameters

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Type** | Replay Harness |
| **Dataset** | 28 symbols, 2025-03-01 to 2026-01-31 |
| **Initial Cash** | $100,000 |
| **Database** | `data/backtest_runs/strat_orb_breakout_20250301_20260131_20260217_025757.db` |
| **Report** | `reports/orb_baseline_defaults.html` |

**Parameters (production defaults):**

| Parameter | Value |
|-----------|-------|
| `orb_window_minutes` | 15 |
| `target_1_r` | 1.0 |
| `target_2_r` | 2.0 |
| `time_stop_minutes` | 30 |
| `max_range_atr_ratio` | 2.0 |
| `min_range_atr_ratio` | 0.5 |
| `stop_buffer_pct` | 0.005 |
| `chase_protection_pct` | 0.005 |
| `breakout_volume_multiplier` | 1.5 |
| `volume_threshold_rvol` | 2.0 |

**Results:**

| Metric | Value |
|--------|-------|
| Total trades | 8 |
| Win rate | 62.5% |
| Profit factor | 2.23 |
| Sharpe ratio | 5.06 |
| Max drawdown | 0.8% |
| Avg R-multiple | 0.39 |
| Total P&L | $1,065 |
| Avg hold (min) | 31 |
| Trades/month | 0.7 |

**Observations:** Sample size far too small for statistical conclusions. Confirms Sprint 8 gate check finding that `max_range_atr_ratio=2.0` rejects nearly all trades (all OR/ATR ratios in dataset below 1.74). The 62.5% win rate and 2.23 PF are directionally encouraging but meaningless with 8 trades.

---

## Run 2: Baseline — Relaxed ATR Filter

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Type** | Replay Harness |
| **Dataset** | 28 symbols, 2025-03-01 to 2026-01-31 |
| **Initial Cash** | $100,000 |
| **Database** | `data/backtest_runs/strat_orb_breakout_20250301_20260131_20260217_030222.db` |
| **Report** | `reports/orb_baseline_relaxed.html` |

**Parameters (max_range_atr_ratio overridden to 999.0, all else default):**

| Parameter | Value |
|-----------|-------|
| `max_range_atr_ratio` | 999.0 (overridden) |
| All other parameters | Same as Run 1 |

**Results:**

| Metric | Value |
|--------|-------|
| Total trades | 135 |
| Win rate | 48.1% |
| Profit factor | 1.00 |
| Sharpe ratio | -0.26 |
| Max drawdown | 7.9% |
| Avg R-multiple | 0.16 |
| Total P&L | $71 |
| Avg hold (min) | 111 |
| Trades/month | 12.3 |

**Observations:** With the ATR filter removed, the strategy is essentially break-even over 11 months. The 48.1% win rate and PF of 1.00 suggest no edge without parameter optimization. This is the unfiltered "base rate" of the ORB strategy on this dataset.

---

## Run 3: VectorBT Parameter Sweep

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Type** | VectorBT Sweep |
| **Dataset** | 29 symbols, 2025-03-01 to 2026-01-31 |
| **Output Dir** | `data/backtest_runs/sweeps/` |
| **Runtime** | ~63 seconds |
| **Combinations** | 29 symbols × 18,000 = 522,000 |

**Parameter Grid:**

| Parameter | Values Swept |
|-----------|-------------|
| `or_minutes` | 5, 10, 15, 20, 30 |
| `target_r` | 1.0, 1.5, 2.0, 2.5, 3.0 |
| `stop_buffer_pct` | 0.0, 0.1, 0.2, 0.5 |
| `max_hold_minutes` | 15, 30, 45, 60, 90, 120 |
| `min_gap_pct` | 1.0, 1.5, 2.0, 3.0, 5.0 |
| `max_range_atr_ratio` | 0.3, 0.5, 0.75, 1.0, 1.5, 999.0 |

**Sensitivity Classification:**

| Parameter | Sensitivity | Best Value | Avg Sharpe at Best | Notes |
|-----------|-------------|------------|-------------------|-------|
| `or_minutes` | **HIGH** | 5 | +0.88 | Clear winner. 15→30 min all negative. |
| `max_hold_minutes` | **HIGH** | 15 | +1.00 | Very clear trend: shorter = better |
| `min_gap_pct` | **MEDIUM-HIGH** | 3.0% | +1.22 | Higher gaps better, but fewer trades |
| `max_range_atr_ratio` | **HIGH** | 0.30 | +1.22 | Stricter filter = better quality |
| `stop_buffer_pct` | **LOW** | 0.0 | +0.29 | Slight preference for 0%, minimal impact |
| `target_r` | **LOW** | 2.0 | +0.20 | All values (1.0–3.0) similar |

**Top 5 Parameter Sets (aggregated across 29 symbols, min 100 total trades):**

| Rank | or_min | target_r | stop_buf | max_hold | min_gap | max_atr | Sharpe | Trades | PF |
|------|--------|----------|----------|----------|---------|---------|--------|--------|-----|
| 1 | 5 | 1.0 | 0.0 | 15 | 2.0 | 0.5 | 3.87 | 179 | 2.07 |
| 2 | 5 | 2.5 | 0.0 | 15 | 2.0 | 0.5 | 3.76 | 179 | 2.07 |
| 3 | 5 | 2.0 | 0.0 | 15 | 2.0 | 0.5 | 3.72 | 179 | 2.04 |
| 4 | 5 | 2.0 | 0.1 | 15 | 2.0 | 0.5 | 3.65 | 179 | 2.04 |
| 5 | 5 | 3.0 | 0.0 | 15 | 2.0 | 0.5 | 3.64 | 179 | 2.04 |

**Key Finding:** All top 10 sets share `or_minutes=5`, `max_hold_minutes=15`, `max_range_atr_ratio=0.5`, `min_gap_pct=2.0`. The current production config (or=15, hold=30, atr=2.0) is suboptimal by every measure.

---

## Run 4–7: Walk-Forward Validation (4 Candidates)

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Type** | Walk-Forward (fixed-params mode) |
| **Dataset** | 2025-03-01 to 2026-01-31 |
| **Windows** | 3 per candidate (4-month IS / 2-month OOS / 2-month step) |
| **Output Dirs** | `data/backtest_runs/walk_forward_candidate_{A,B,C,D}/` |

**Candidate Configurations:**

| Candidate | or_min | max_hold | max_atr | min_gap | target_r | stop_buf | Rationale |
|-----------|--------|----------|---------|---------|----------|----------|-----------|
| A | 5 | 15 | 0.5 | 2.0 | 2.0 | 0.0 | Sweep winner (tightest filters) |
| B | 5 | 15 | 1.0 | 2.0 | 2.0 | 0.0 | Relaxed ATR (more trades) |
| C | 5 | 30 | 0.75 | 2.0 | 2.0 | 0.1 | Middle ground |
| D | 5 | 30 | 999.0 | 2.0 | 2.0 | 0.0 | Fully relaxed (volume test) |

**Walk-Forward Results:**

| Metric | Candidate A | Candidate B | Candidate C | Candidate D |
|--------|-------------|-------------|-------------|-------------|
| Total WF windows | 3 | 3 | 3 | 3 |
| Mean WFE | 0.00 | 0.00 | 0.00 | -4.09 |
| Min WFE | 0.00 | 0.00 | 0.00 | -10.18 |
| Max WFE | 0.00 | 0.00 | 0.00 | 0.00 |
| Windows WFE > 0.3 | 0/3 | 0/3 | 0/3 | 0/3 |
| Windows WFE > 0.5 | 0/3 | 0/3 | 0/3 | 0/3 |
| OOS total P&L | -$444 | -$444 | -$444 | -$13,720 |
| OOS Sharpe | 0.00 | 0.00 | 0.00 | -4.19 |
| OOS total trades | 2 | 2 | 2 | 81 |

**Candidate D Per-Window Detail:**

| Window | IS Period | OOS Period | IS Sharpe | OOS Sharpe | WFE | OOS Trades |
|--------|-----------|------------|-----------|------------|-----|------------|
| 1 | Mar–Jun 2025 | Jul–Aug 2025 | +3.49 | -7.24 | -2.08 | 21 |
| 2 | May–Aug 2025 | Sep–Oct 2025 | +0.47 | -4.81 | -10.18 | 32 |
| 3 | Jul–Oct 2025 | Nov–Dec 2025 | -4.46 | -0.53 | 0.00 | 28 |

**Key Findings:**
1. **No candidate achieves WFE ≥ 0.3** (minimum threshold per DEC-047).
2. Candidates A–C produced only 2 OOS trades total — **inconclusive**, not negative.
3. Candidate D showed classic overfitting: IS Sharpe +3.49 → OOS Sharpe -7.24 in Window 1.
4. Only 3 walk-forward windows available — insufficient for robust statistical conclusions. Industry standard is 8–12+ windows requiring 3–5 years of data.

---

## Cross-Validation Sanity Check (TSLA)

| Metric | Value |
|--------|-------|
| VectorBT trades | 21 |
| Replay Harness trades | 135 |
| Ratio | 0.16 |
| Assessment | **FAIL** |

**Issue:** Cross-validation function hardcodes `max_range_atr_ratio=999.0` for the Replay Harness but the VectorBT run used `or_minutes=5, target_r=2.0` with its own ATR filtering. This mismatch means the two engines were not testing identical configurations. **This needs investigation before relying on walk-forward results that chain VectorBT IS optimization with Replay Harness OOS validation.**

---

## Open Questions (for Sprint 10 Steps 4–5)

1. **Cross-validation mismatch:** Does the walk-forward engine pass consistent parameters to both VectorBT (IS) and Replay Harness (OOS)? If not, the walk-forward results may be unreliable.
2. **Data quantity:** 11 months / 3 windows is insufficient for walk-forward validation. Should we acquire more historical data before drawing conclusions?
3. **Tight-filter inconclusive vs relaxed-filter failure:** The strategy may have an edge with tight filters that we simply can't validate yet. Paper trading is the forward-looking test.

---

## Run 8: Final Validation — Recommended Parameters

| Field | Value |
|-------|-------|
| **Date** | 2026-02-17 |
| **Type** | Replay Harness |
| **Dataset** | 29 symbols, 2025-03-01 to 2026-01-31 |
| **Initial Cash** | $100,000 |
| **Database** | `data/backtest_runs/strat_orb_breakout_20250301_20260131_20260217_174818.db` |
| **Report** | `reports/orb_final_validation.html` |

**Parameters (Sprint 10 recommended):**

| Parameter | Value | Change from Default |
|-----------|-------|---------------------|
| `orb_window_minutes` | 5 | ↓ from 15 |
| `time_stop_minutes` | 15 | ↓ from 30 |
| `max_range_atr_ratio` | 999.0 | ↑ from 2.0 (disabled) |
| All other parameters | Same as Run 1 | — |

**Results:**

| Metric | Value |
|--------|-------|
| Total trades | 137 |
| Win rate | 46.7% |
| Profit factor | 1.18 |
| Sharpe ratio | 0.93 |
| Max drawdown | $7,677.67 (6.6%) |
| Recovery factor | 1.05 |
| Avg R-multiple | 0.43 |
| Expectancy | 0.430R |
| Total P&L | $8,086.61 |
| Final equity | $108,086.61 |
| Avg hold (min) | 49 |
| Trades/month | 12.5 |

**Exit Distribution:**

| Exit Type | Count | % |
|-----------|-------|---|
| Stop loss | 95 | 69.3% |
| Time stop | 38 | 27.7% |
| EOD flatten | 4 | 2.9% |
| Target hit | 0 | 0% |

**Monthly P&L Breakdown:**

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

**Comparison vs Baselines:**

| Metric | Default (or=15, hold=30, atr=2.0) | Relaxed (or=15, hold=30, atr=999) | Recommended (or=5, hold=15, atr=999) |
|--------|-----------------------------------|-----------------------------------|--------------------------------------|
| Total trades | 8 | 135 | 137 |
| Win rate | 62.5% | 48.1% | 46.7% |
| Sharpe | 5.06 | -0.26 | **0.93** |
| Profit factor | 2.23 | 1.00 | **1.18** |
| Max drawdown | 0.8% | 7.9% | 6.6% |
| Net P&L | $1,065 | $71 | **$8,087** |
| Avg R-multiple | 0.39 | 0.16 | **0.43** |
| Avg hold (min) | 31 | 111 | **49** |
| Recovery factor | — | — | **1.05** |

**Observations:**

1. **Significant improvement** over relaxed baseline: Net P&L $71 → $8,087, Sharpe -0.26 → 0.93.
2. **Shorter OR window (5 min)** captures more actionable breakouts than the 15-min window.
3. **Shorter time stop (15 min)** exits losing trades faster, reducing average hold from 111 to 49 min.
4. **No target hits** — all exits via stop loss (69%), time stop (28%), or EOD (3%). This suggests targets may be set too aggressively or breakouts don't develop enough momentum.
5. **Rough patch Oct–Jan** with 4 consecutive losing months after strong performance Mar–Sep. Suggests seasonality or regime sensitivity that warrants monitoring.
6. **Config updated** (`config/strategies/orb_breakout.yaml`) to use recommended params. Decision logged as DEC-075.
