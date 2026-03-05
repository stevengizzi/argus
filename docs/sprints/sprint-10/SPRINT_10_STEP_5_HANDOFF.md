# Sprint 10 Step 5 — Write the Parameter Validation Report

> **Handoff document for a fresh Claude conversation.**
> Use this alongside the Argus Claude Project (which has project instructions and all docs synced via GitHub).

---

## Context

You are helping write the **Parameter Validation Report** for Argus, an automated day trading system. This report is the formal Phase 2 deliverable — it documents everything learned from backtesting the ORB (Opening Range Breakout) strategy and recommends parameters for Phase 3 (live paper trading validation).

Phase 2 built a full backtesting toolkit across Sprints 6–9 (Replay Harness, VectorBT parameter sweeps, walk-forward analysis, HTML report generator) and Sprint 10 used those tools to analyze the ORB strategy. Steps 1–4 are complete. Step 5 is writing the report.

---

## What Was Done (Sprint 10, Steps 1–4 Summary)

### Step 1: Baseline Backtest

Three Replay Harness runs across 28 symbols, March 2025 – January 2026, $100K starting capital:

| Run | Config | Trades | Win Rate | Sharpe | PF | Net P&L | Avg Hold |
|-----|--------|--------|----------|--------|----|---------|----------|
| Default | or=15, hold=30, atr=2.0 | 8 | 62.5% | 5.06 | 2.23 | $1,065 | 31 min |
| Relaxed | or=15, hold=30, atr=999 | 135 | 48.1% | -0.26 | 1.00 | $71 | 111 min |
| **Recommended** | **or=5, hold=15, atr=999** | **137** | **46.7%** | **0.93** | **1.18** | **$8,087** | **49 min** |

- Default was too restrictive (8 trades in 11 months) because `max_range_atr_ratio=2.0` rejected 98.5% of opening ranges
- Relaxed baseline was break-even — no edge with original OR window and hold time
- Recommended params turned a break-even strategy into a profitable one ($8K on $100K over 11 months)

### Step 2: Parameter Sensitivity (VectorBT Sweep)

522,000 combinations (29 symbols × 18,000 param combos) in 63 seconds.

**Sensitivity Classification:**

| Parameter | Sensitivity | Best Value | Notes |
|-----------|------------|------------|-------|
| `opening_range_minutes` | **HIGH** | 5 | Monotonic: shorter = better. 15–30 all negative. |
| `max_hold_minutes` | **HIGH** | 15 | Very clear: shorter = better |
| `min_gap_pct` | **MEDIUM-HIGH** | 3.0% | Higher = better quality, fewer trades |
| `max_range_atr_ratio` | **HIGH** | 0.30 | Non-transferable to production (see ATR divergence below) |
| `stop_buffer_pct` | **LOW** | 0.0 | Minimal impact |
| `target_r` | **LOW** | 2.0 | All values (1.0–3.0) similar |

**Top 5 Sets (all share or=5, hold=15, atr=0.5, gap=2.0):**

| Rank | or | target_r | stop_buf | hold | gap | atr | Sharpe | Trades | PF |
|------|-----|----------|----------|------|-----|------|--------|--------|----|
| 1 | 5 | 1.0 | 0.0 | 15 | 2.0 | 0.5 | 3.87 | 179 | 2.07 |
| 2 | 5 | 2.5 | 0.0 | 15 | 2.0 | 0.5 | 3.76 | 179 | 2.07 |
| 3 | 5 | 2.0 | 0.0 | 15 | 2.0 | 0.5 | 3.72 | 179 | 2.04 |
| 4 | 5 | 2.0 | 0.1 | 15 | 2.0 | 0.5 | 3.65 | 179 | 2.04 |
| 5 | 5 | 3.0 | 0.0 | 15 | 2.0 | 0.5 | 3.64 | 179 | 2.04 |

### Step 3: Walk-Forward Validation

4 candidates tested, 3 walk-forward windows each (4-month IS / 2-month OOS / 2-month step).

| Candidate | or | hold | atr | gap | target_r | stop_buf | OOS Trades | OOS Sharpe | Mean WFE |
|-----------|-----|------|------|-----|----------|----------|------------|------------|----------|
| A (tight) | 5 | 15 | 0.5 | 2.0 | 2.0 | 0.0 | 2 | 0.00 | 0.00 |
| B | 5 | 15 | 1.0 | 2.0 | 2.0 | 0.0 | 2 | 0.00 | 0.00 |
| C | 5 | 30 | 0.75 | 2.0 | 2.0 | 0.1 | 2 | 0.00 | 0.00 |
| D (relaxed) | 5 | 30 | 999 | 2.0 | 2.0 | 0.0 | 81 | -4.19 | -4.09 |

**Result: Scenario C (Inconclusive).** No candidate achieved WFE ≥ 0.3 (DEC-047 threshold). Tight candidates had too few OOS trades to evaluate. Relaxed candidate showed classic overfitting. Contributing factors: only 11 months of data yielding 3 windows (industry needs 8–12+), and ATR calculation divergence affecting tight-filter candidates.

### Cross-Validation Fix (DEC-074)

During Step 3, the cross-validation sanity check failed (VectorBT 21 vs Replay 135 trades for TSLA). Investigation found three bugs:

1. CLI hardcoded 4 of 6 parameters
2. VectorBT used `.get()` with silent defaults
3. Replay Harness loaded all 29 symbols instead of filtering to target

All fixed. Walk-forward pipeline parameter handoff was already correct. 542 tests passing.

**ATR Calculation Divergence (architectural, not a bug):**
- VectorBT: ATR(14) from daily aggregated bars
- Production/Replay: ATR(14) from 1-minute bars with Wilder smoothing
- Result: range/ATR ratios 5–10x higher in production, making VectorBT ATR thresholds meaningless in production
- Resolution: `max_range_atr_ratio` disabled (999.0) for Phase 3 per DEC-075. Other 5 params transfer cleanly.

### Step 4: Parameter Recommendations (DEC-076 pending)

| Parameter | Old Default | Recommended | Sensitivity | Justification |
|-----------|-------------|-------------|-------------|---------------|
| `opening_range_minutes` | 15 | **5** | High | Monotonic trend, all top-10 sets agree, aligns with ORB thesis |
| `max_hold_minutes` | 30 | **15** | High | Clear shorter=better gradient, ORB edge is front-loaded |
| `min_gap_pct` | 2.0 | **2.0** (no change) | Med-High | Top-5 all use 2.0%, preserves trade frequency for paper validation |
| `stop_buffer_pct` | 0.0 | **0.0** (no change) | Low | Minimal impact, stop at OR low |
| `target_r` | 2.0 | **2.0** (no change) | Low | All values similar |
| `max_range_atr_ratio` | 2.0 | **999.0** (disabled) | N/A | DEC-075, ATR calc divergence |

### Final Validation Run (Recommended Params)

137 trades, Sharpe 0.93, PF 1.18, net P&L +$8,087 on $100K.

**Monthly P&L:**

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

**Exit Distribution:**

| Exit Type | Count | % |
|-----------|-------|---|
| Stop loss | 95 | 69.3% |
| Time stop | 38 | 27.7% |
| EOD flatten | 4 | 2.9% |
| Target hit | 0 | 0% |

**Key Observations:**
1. Zero target hits — all profitable exits via time stop or EOD. The 2.0R target never triggers within 15 min. Strategy profits from net-positive time-stopped exits, not from R:R framework working as designed.
2. Strong Mar–Sep, weak Oct–Jan. Possible seasonality/regime sensitivity, but only 1 year of data — could be coincidence.
3. 6.6% max drawdown is well within risk limits (account daily limit 3–5%, weekly 5–8%).

---

## Report Structure

The report is `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`. It should have 10 sections:

### Section 0: How to Read This Report (NEW — not in original spec)

Plain-language explanations of every key metric used in the report. The reader is building this system for his family's financial future and wants to deeply understand what he's looking at, not just see numbers. Cover:

- **Sharpe Ratio** — what it measures, what values are good/bad/concerning, with a concrete dollar example
- **Profit Factor** — what it means, how to interpret values above/below 1.0, dollar example
- **R-Multiple** — the concept of measuring trades in units of risk, why it matters, examples
- **Expectancy** — what it means, how to use it for position sizing planning
- **Win Rate** — why it's less important than people think, relationship with R:R
- **Max Drawdown** — what it measures, why it's arguably the most important metric for staying in the game, dollar example
- **Walk-Forward Efficiency (WFE)** — what it protects against (overfitting), how to interpret values, what "inconclusive" means
- **Equity Curve** — how to read it, what a healthy vs concerning curve looks like
- **Heatmaps** — how to read parameter sensitivity heatmaps, what stable vs fragile regions mean

Each explanation should be 2–4 paragraphs, written for someone intelligent but new to systematic trading. Use concrete examples with dollar amounts where possible (e.g., "If you risk $500 per trade and your average R-multiple is 0.43, your average trade makes $215").

### Section 1: Executive Summary

One-paragraph verdict: should this strategy proceed to live paper trading?
Key numbers, caveats in plain language. The answer is yes with caveats — the strategy shows a modest edge in backtesting but walk-forward validation was inconclusive due to insufficient data, and the zero-target-hit pattern needs monitoring.

### Section 2: Dataset Description

- 28 symbols (list them), March 2025 – January 2026, source Alpaca, 2.2M+ bars
- Data quality notes
- Market conditions during the period (SPY performance, VIX range, notable events)
- Limitations: only 11 months, single market regime

### Section 3: Baseline Performance

- Default results (8 trades) — document why so few
- Relaxed results (135 trades) — break-even baseline
- Reference the HTML reports: `reports/orb_baseline_defaults.html`, `reports/orb_baseline_relaxed.html`

### Section 4: Parameter Sensitivity

- Sensitivity classification table
- Key findings from heatmaps (reference HTML files in `data/backtest_runs/sweeps/interactive/`)
- Identification of dominant parameters (or_minutes, max_hold) vs insensitive ones (target_r, stop_buffer)
- ATR divergence explanation — why `max_range_atr_ratio` results don't transfer

### Section 5: Walk-Forward Validation

- Results per candidate per window
- Scenario C interpretation: inconclusive, not definitively negative
- Why 11 months / 3 windows is insufficient (industry standard 8–12+)
- How ATR divergence contributed to tight-filter candidates having near-zero OOS trades

### Section 6: Parameter Recommendations

- Full recommendation table with justifications
- Decision framework applied to each parameter
- Config diff (before/after)

### Section 7: Final Validation Results

- Full metrics from the recommended-params run
- Monthly P&L table
- Exit distribution analysis — the zero-target-hit finding and what it means
- Comparison table (default vs relaxed vs recommended)
- Reference: `reports/orb_final_validation.html`

### Section 8: Known Limitations & Open Questions

- Limited historical data (11 months)
- Walk-forward inconclusive
- ATR filter disabled (DEC-075) — needs daily ATR infrastructure or empirical calibration
- Zero target hits — is the 2.0R target too aggressive for a 15-min hold, or is the time stop doing the right thing?
- VectorBT vs Replay divergence (21 vs 39 trades with matched params, ATR disabled) — remaining gap is due to VectorBT not modeling VWAP, volume confirmation, and chase protection
- Possible seasonal pattern (strong spring/summer, weak fall/winter) — 1 year insufficient to confirm
- Slippage model is fixed $0.01/share — real slippage during market open may be higher

### Section 9: Phase 3 Live Trading Recommendation

- Recommended starting position size (minimum — e.g., 10–25 shares regardless of what sizing model says)
- Recommended capital allocation
- Ramp-up schedule (10 shares × 20 days → 25 shares × 20 days → model size)
- Kill criteria: what results should trigger a pause or strategy review
- Expected trade frequency (~12–14 trades/month based on backtest)
- What to monitor during paper trading (target hit rate, time stop profitability, seasonal patterns, slippage vs backtest assumption)

---

## Writing Guidelines

- **Audience:** The author of this system. Intelligent, can code in Python, has trading experience but is new to systematic/algorithmic trading. Building this for his family's financial future.
- **Tone:** Honest, thorough, not salesy. If the data is ambiguous, say so. Don't oversell a Sharpe of 0.93.
- **Length:** Comprehensive. This is the reference document for Phase 3 and beyond. Section 0 alone should be 2–3 pages. Total report probably 15–25 pages.
- **Format:** Markdown. Tables for data, prose for analysis. No bullet-point walls — write in paragraphs with clear topic sentences.
- **Charts:** Reference the existing HTML reports by filename. Don't try to embed charts in markdown.
- **Honesty:** The walk-forward was inconclusive. The zero-target-hit pattern is unusual. The strategy's edge is modest. Say all of this clearly. The user explicitly values being told hard truths.

---

## Key Decisions Referenced

| Decision | Summary |
|----------|---------|
| DEC-047 | Walk-forward WFE > 0.3 required. Not met (Scenario C). |
| DEC-073 | Walk-forward results classified as Scenario C (inconclusive). |
| DEC-074 | Cross-validation bugs fixed. ATR divergence documented. |
| DEC-075 | ATR filter disabled for Phase 3. Production ATR uses wrong scale. |
| DEC-076 | Parameter recommendations (pending — document in this report). |

---

## Files to Reference

- `reports/orb_baseline_defaults.html` — 8-trade default baseline
- `reports/orb_baseline_relaxed.html` — 135-trade relaxed baseline
- `reports/orb_final_validation.html` — 137-trade recommended params
- `data/backtest_runs/sweeps/` — Raw sweep Parquets + heatmaps
- `data/backtest_runs/walk_forward_candidate_{A,B,C,D}/` — Walk-forward outputs
- `docs/backtesting/BACKTEST_RUN_LOG.md` — All run details and metrics
- `config/strategies/orb_breakout.yaml` — Current (updated) config

---

## Deliverable

A single file: `docs/backtesting/PARAMETER_VALIDATION_REPORT.md`

This can be written collaboratively — draft sections in conversation, then assemble into the final file. Or draft the whole thing and iterate. The important thing is that every section is present, the data is accurate, and the tone is honest.

After the report is written:
1. Commit to git
2. Update `09_PHASE2_SPRINT_PLAN.md` — mark Sprint 10 ✅ COMPLETE
3. Update `02_PROJECT_KNOWLEDGE.md` — Phase 2 COMPLETE, test count, link to report
4. Update `CLAUDE.md` — Phase 2 complete, Phase 3 next
5. Phase 2 is done.
