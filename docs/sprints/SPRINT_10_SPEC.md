# Sprint 10 — Analysis & Parameter Validation Report — Implementation Spec

> **Version:** 1.0 | **Date:** February 17, 2026
> **Pre-requisites:** Sprints 6–9 complete (541 tests), historical data available (28 symbols × 11 months), all analysis tooling functional
> **Starting test count:** 541 | **Target new tests:** 0 (this is analysis work, not code)
> **Mode:** Analysis mode. No new modules, no new tests. Structured workflow using existing tools.

---

## Goal

Use the backtesting toolkit built in Sprints 6–9 to actually run backtests, interpret results, tune parameters, and produce the formal **Parameter Validation Report** — the deliverable that determines whether the ORB strategy proceeds to live trading, and with what parameters.

This sprint answers three questions:
1. **Does the ORB strategy make money on historical data?** (Baseline backtest)
2. **Are the current parameters optimal, or is there a more robust set?** (Parameter sensitivity + walk-forward)
3. **Is the strategy robust enough to risk real capital?** (Walk-forward efficiency + honest assessment)

---

## Important Context

### The max_range_atr_ratio Problem

Sprint 8's gate check revealed a critical finding: with default parameters (`max_range_atr_ratio=2.0`), the strategy produced only **5 trades in 148 days** because the ATR filter rejected 98.5% of opening ranges. With relaxed params (`max_range_atr_ratio=5.0`), it found **59 trades**.

Additionally, DEC-065 found that all OR range/ATR ratios in the dataset are below 2.0 (max 1.74). The sweep threshold was updated from `[2.0, 3.0, 4.0, 5.0, 8.0, 999.0]` to `[0.3, 0.5, 0.75, 1.0, 1.5, 999.0]`, showing a meaningful trade count gradient: 25% → 65% → 84% → 89% → 92% → 100%.

This means the production config's `max_range_atr_ratio=2.0` is an extremely aggressive filter that eliminates the vast majority of potential trades. The baseline backtest will confirm this, and the parameter analysis will determine the right threshold.

### Current Production Parameters (from config/strategies/orb_breakout.yaml)

Document the exact parameter values here before running anything, so the baseline is reproducible:

```yaml
# The user or Claude Code should fill these in from the actual YAML before proceeding
opening_range_minutes: ???
target_1_r: ???
target_2_r: ???
stop_buffer_pct: ???
max_hold_minutes: ???
min_gap_pct: ???
max_range_atr_ratio: 2.0  # Known to be very restrictive
```

**Action item:** Before running Step 1, read and record all current parameter values from `config/strategies/orb_breakout.yaml` in this section.

---

## Step 1: Baseline Backtest

### Objective
Run the Replay Harness with current production parameters to establish the "how does the strategy perform as-built?" baseline.

### 1a. Run with Current Defaults

```bash
python -m argus.backtest.replay_harness \
    --start 2025-03-01 \
    --end 2026-01-31 \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs \
    --initial-cash 100000
```

Record the output database path: `data/backtest_runs/orb_breakout_20250301_20260131_XXXXXX.db`

### 1b. Generate Baseline Report

```bash
python -m argus.backtest.report_generator \
    --db data/backtest_runs/<baseline_db>.db \
    --output reports/orb_baseline_defaults.html
```

### 1c. Evaluate Default Baseline

If the default baseline produces **fewer than 20 trades** (which is expected given `max_range_atr_ratio=2.0`), the sample is too small for statistical conclusions. In that case, also run a relaxed baseline:

```bash
python -m argus.backtest.replay_harness \
    --start 2025-03-01 \
    --end 2026-01-31 \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs \
    --initial-cash 100000 \
    --config-override max_range_atr_ratio=999.0

python -m argus.backtest.report_generator \
    --db data/backtest_runs/<relaxed_db>.db \
    --output reports/orb_baseline_relaxed.html
```

This gives two data points: "strategy with maximum filter selectivity" vs "strategy with no ATR filter."

### 1d. Metrics to Record

For each baseline run, document:

| Metric | Default Params | Relaxed ATR |
|--------|---------------|-------------|
| Total trades | | |
| Win rate (%) | | |
| Profit factor | | |
| Sharpe ratio (annualized) | | |
| Max drawdown (%) | | |
| Max drawdown duration (days) | | |
| Average R-multiple | | |
| Total P&L ($) | | |
| Average trades per month | | |
| Best month (P&L) | | |
| Worst month (P&L) | | |

### 1e. Manual Trade Spot-Check (20+ Trades)

Open TradingView (or similar charting tool) and manually verify at least 20 trades from the relaxed baseline against real charts. For each trade, check:

- Does the entry make sense? (breakout above OR high, with gap context)
- Does the stop placement look reasonable?
- Did the exit trigger correctly? (T1 hit, T2 hit, stop out, time stop, EOD flatten)
- Are there obvious trades the strategy missed that it should have taken?
- Are there trades that look like they should NOT have been taken?

Document any discrepancies. If you find systematic errors in the Replay Harness logic, **stop and fix them before proceeding** — all subsequent analysis depends on the harness being correct.

### Step 1 Gate Check

**Proceed to Step 2 if:**
- At least one baseline run produced ≥20 trades
- Manual spot-check found no systematic harness errors
- Results are directionally plausible (even if unprofitable — that's useful data)

**Stop and investigate if:**
- Both baselines produce <10 trades (something is wrong with the harness or data)
- Manual spot-check reveals entries/exits that don't match the chart data
- The harness crashes or produces corrupt output

---

## Step 2: Parameter Sensitivity

### Objective
Identify which parameters matter most and which are stable across a wide range of values.

### 2a. Run Full VectorBT Sweep

```bash
python -m argus.backtest.vectorbt_orb \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/sweeps \
    --start 2025-03-01 \
    --end 2026-01-31
```

This runs 28 symbols × 18,000 parameter combinations. Expected runtime: ~53 seconds based on Sprint 8 benchmarks.

### 2b. Examine Heatmaps

The sweep produces heatmaps (static PNG + interactive HTML) showing performance across parameter combinations. Look for:

- **Stable regions:** Large areas of the parameter space with similar (and positive) performance. These are robust parameters — small changes don't destroy profitability.
- **Fragile regions:** Narrow peaks where small parameter changes cause large performance swings. These are overfit-prone parameters.
- **Dominant parameters:** Which parameters have the biggest impact on results? (Sprint 8 already suggested `max_range_atr_ratio` is dominant — confirm this.)
- **Irrelevant parameters:** Parameters where changing the value barely affects performance. These can be set to reasonable defaults without stress.

### 2c. Parameter Sensitivity Summary

For each of the 6 swept parameters, classify:

| Parameter | Sensitivity | Stable Range | Notes |
|-----------|------------|-------------|-------|
| `opening_range_minutes` | High / Medium / Low | e.g., 10–20 | |
| `target_r` (T1 target) | High / Medium / Low | e.g., 1.0–2.0 | |
| `stop_buffer_pct` | High / Medium / Low | | |
| `max_hold_minutes` | High / Medium / Low | | |
| `min_gap_pct` | High / Medium / Low | | |
| `max_range_atr_ratio` | High / Medium / Low | | |

### 2d. Identify Top-N Parameter Sets

From the sweep results, identify the top 5–10 parameter combinations by Sharpe ratio (with minimum trade count filter). These become candidates for walk-forward validation.

**Record them here:**

| Rank | or_min | target_r | stop_buf | max_hold | min_gap | max_atr | Sharpe | Trades | PF |
|------|--------|----------|----------|----------|---------|---------|--------|--------|----|
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| ... | | | | | | | | | |

---

## Step 3: Walk-Forward Validation

### Objective
Test whether the "best" parameters from the sweep are genuinely robust or just overfit to historical data.

### 3a. Walk-Forward with Default Parameters

```bash
python -m argus.backtest.walk_forward \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/walk_forward_defaults \
    --start 2025-03-01 \
    --end 2026-01-31
```

This uses the default config parameters. Record the Walk-Forward Efficiency (WFE) for each window.

### 3b. Walk-Forward with Sweep "Best" Parameters

Run walk-forward analysis using the top parameter set(s) from Step 2:

```bash
python -m argus.backtest.walk_forward \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs/walk_forward_optimized \
    --start 2025-03-01 \
    --end 2026-01-31 \
    --config-override opening_range_minutes=<best> \
    --config-override target_r=<best> \
    --config-override max_range_atr_ratio=<best> \
    # ... etc for all 6 parameters
```

### 3c. Compare Walk-Forward Results

| Metric | Default Params | Optimized Params |
|--------|---------------|-----------------|
| Mean WFE across windows | | |
| Min WFE (worst window) | | |
| Max WFE (best window) | | |
| Windows with WFE > 0.3 | /total | /total |
| Windows with WFE > 0.5 | /total | /total |
| OOS total P&L | | |
| OOS Sharpe | | |
| Parameter stability (mode consistency) | | |

### 3d. Interpret the Results

Per DEC-047, WFE > 0.3 is the minimum threshold. WFE > 0.5 suggests good generalization.

**Scenario A — Optimized params have BETTER WFE than defaults:**
The sweep found genuinely better parameters. Use the optimized set as the starting point for Phase 3, but apply a conservative bias (e.g., if the sweep says `target_r=2.5` is optimal but `target_r=2.0` is nearly as good, prefer 2.0).

**Scenario B — Optimized params have WORSE WFE than defaults:**
The "optimization" was overfitting. The default parameters may actually be more robust. This is valuable information — it means the strategy's edge (if any) doesn't come from parameter tuning.

**Scenario C — Both show poor WFE (< 0.3):**
The ORB strategy may not have a durable edge in this dataset. This doesn't necessarily mean "abandon it" — 11 months is a limited sample, and the strategy may perform differently in different market regimes — but it's an honest signal that should be documented.

### 3e. Cross-Validation Sanity Check

If not already run during Sprint 9, run cross-validation on a few symbols to confirm VectorBT and Replay Harness agree:

```bash
python -m argus.backtest.walk_forward --cross-validate \
    --symbol TSLA --start 2025-03-01 --end 2026-01-31 \
    --or-minutes 15 --target-r 2.0
```

VectorBT should produce ≥ Replay Harness trade count for matching parameters (DEC-069).

---

## Step 4: Parameter Recommendations

### Objective
Based on Steps 1–3, recommend final parameter values for Phase 3 live trading. Prioritize **robustness over maximum backtest return**.

### 4a. Decision Framework

For each parameter, apply this logic:

1. **If low sensitivity (Step 2):** Keep current default or use the mode from walk-forward stability analysis. Don't overthink it.
2. **If high sensitivity + good WFE (Step 3):** Use the walk-forward optimized value, but bias conservatively.
3. **If high sensitivity + poor WFE (Step 3):** Use a middle-of-the-road value from the stable region identified in Step 2. The parameter matters, but optimization doesn't generalize.

### 4b. Parameter Recommendation Table

| Parameter | Current | Recommended | Justification |
|-----------|---------|-------------|---------------|
| `opening_range_minutes` | | | |
| `target_1_r` | | | |
| `target_2_r` | | | |
| `stop_buffer_pct` | | | |
| `max_hold_minutes` | | | |
| `min_gap_pct` | | | |
| `max_range_atr_ratio` | 2.0 | | |

### 4c. Special Consideration: max_range_atr_ratio

This parameter deserves specific attention because:
- The current default (2.0) eliminates 98.5% of trades
- All OR/ATR ratios in the dataset are below 1.74
- The sweep showed 0.3 → 25%, 0.5 → 65%, 0.75 → 84%, 1.0 → 89%, 1.5 → 92% trade count gradient

The recommendation should explicitly address what threshold balances trade quality (stricter filter) against sample size (more trades for statistical validity).

### 4d. Run Final Validation

Once parameter recommendations are locked, run one final Replay Harness pass with the recommended parameters to get the "expected live performance" baseline:

```bash
python -m argus.backtest.replay_harness \
    --start 2025-03-01 \
    --end 2026-01-31 \
    --data-dir data/historical/1m \
    --output-dir data/backtest_runs \
    --initial-cash 100000 \
    --config-override opening_range_minutes=<rec> \
    --config-override target_r=<rec> \
    --config-override max_range_atr_ratio=<rec> \
    # ... etc

python -m argus.backtest.report_generator \
    --db data/backtest_runs/<final_db>.db \
    --sweep-dir data/backtest_runs/sweeps \
    --walk-forward-dir data/backtest_runs/walk_forward_optimized \
    --output reports/orb_final_validation.html
```

This is the report you'll reference during Phase 3 live trading.

---

## Step 5: Write the Parameter Validation Report

### Objective
Produce `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` — the formal Phase 2 deliverable.

### 5a. Report Structure

The report should contain:

**Section 1: Executive Summary**
- One-paragraph verdict: should this strategy proceed to live trading?
- Key numbers: total trades, win rate, Sharpe, max drawdown, recommended starting capital
- Caveats in plain language

**Section 2: Dataset Description**
- 28 symbols, date range (March 2025 – January 2026), source (Alpaca), 2.2M+ bars
- Data quality notes (any gaps, holidays, early closes)
- Market conditions during the period (SPY performance, VIX range, any major events)

**Section 3: Baseline Performance**
- Default parameter results (even if only 5 trades — document why)
- Relaxed parameter results
- Monthly P&L table
- Equity curve with drawdown overlay
- Trade distribution charts (by time of day, by holding duration, by R-multiple)

**Section 4: Parameter Sensitivity**
- Heatmaps (reference the HTML files)
- Classification of each parameter (high/medium/low sensitivity)
- Identification of stable vs fragile regions
- Discussion of `max_range_atr_ratio` as dominant parameter

**Section 5: Walk-Forward Validation**
- WFE results per window
- Comparison of default vs optimized parameters
- Parameter stability analysis (do the "best" parameters change every window?)
- Honest assessment of overfitting risk

**Section 6: Recommended Parameters**
- Final parameter table with justification for each value
- Expected performance range based on walk-forward OOS results
- Comparison to baseline

**Section 7: Known Limitations & Caveats**
- 11-month sample is limited (< 1 full market cycle)
- Backtest doesn't account for: partial fills, true slippage, market impact, news events, pre-market volatility
- VectorBT approximation vs Replay Harness differences
- Strategy only tested long-only on US equities
- No regime-conditional analysis yet (would the strategy have been stopped during a downturn?)

**Section 8: Risk Assessment**
- What market conditions would this strategy struggle in? (Low-volatility / no-gap environments, sharp reversals, news-driven gaps that fade)
- Worst-case drawdown estimate
- How many consecutive losing days before the daily loss limit triggers?
- Expected number of trades per week/month for position sizing planning

**Section 9: Phase 3 Live Trading Recommendation**
- Recommended starting position size
- Recommended capital allocation
- Ramp-up schedule (e.g., 10 shares × 20 days → 25 shares × 20 days → model size)
- Kill criteria: what results during Phase 3 should trigger a pause or strategy review?
- Reference paper trading results (if available by this point)

### 5b. Supporting Files

In addition to the markdown report, the following artifacts should be referenced:
- `reports/orb_baseline_defaults.html` — Baseline report with default params
- `reports/orb_baseline_relaxed.html` — Baseline report with relaxed ATR filter
- `reports/orb_final_validation.html` — Full report with recommended params + sweep + walk-forward data
- `data/backtest_runs/sweeps/` — Raw sweep output (Parquet + heatmaps)
- `data/backtest_runs/walk_forward_*/` — Walk-forward output (JSON + CSV)

---

## Workflow Summary

```
Step 1: Baseline Backtest
    ├── 1a: Run with defaults → probably ~5 trades
    ├── 1b: Generate report
    ├── 1c: Run with relaxed ATR → ~59+ trades
    ├── 1d: Record metrics
    └── 1e: Spot-check 20+ trades on TradingView
         ↓ Gate check: ≥20 trades, no harness errors
Step 2: Parameter Sensitivity
    ├── 2a: Full VectorBT sweep (~53 seconds)
    ├── 2b: Examine heatmaps
    ├── 2c: Classify parameter sensitivity
    └── 2d: Identify top-N parameter sets
         ↓
Step 3: Walk-Forward Validation
    ├── 3a: Walk-forward with defaults
    ├── 3b: Walk-forward with sweep "best"
    ├── 3c: Compare WFE
    ├── 3d: Interpret results (Scenario A/B/C)
    └── 3e: Cross-validation sanity check
         ↓
Step 4: Parameter Recommendations
    ├── 4a: Apply decision framework
    ├── 4b: Fill recommendation table
    ├── 4c: Address max_range_atr_ratio specifically
    └── 4d: Final validation run with recommended params
         ↓
Step 5: Write the Report
    ├── 5a: PARAMETER_VALIDATION_REPORT.md (9 sections)
    └── 5b: Collect supporting HTML reports and data artifacts
         ↓
    Phase 2 COMPLETE
```

---

## What This Sprint Does NOT Include

- Writing new code or new tests (if harness bugs are found in Step 1e, fix them but that's a bug fix, not Sprint 10 scope)
- Multi-strategy analysis (ORB only)
- Regime-conditional backtesting (future enhancement)
- Automated parameter selection (this is human judgment, informed by data)
- PDF report generation (HTML only, per DEC-067)
- Live trading decisions (that's Phase 3 planning, which happens after this report)

---

## Claude Code Handoff Notes

Sprint 10 is collaborative between the user and Claude Code. Unlike Sprints 6–9, there is no single spec-to-implementation handoff. Instead:

- **Claude Code runs the tools** (Steps 1a, 1b, 1c, 2a, 3a, 3b, 3e, 4d)
- **The user interprets results** (Steps 1d, 1e, 2b, 2c, 2d, 3c, 3d, 4a, 4b, 4c)
- **Both collaborate on the report** (Step 5)

The recommended workflow is to run Steps 1 and 2 in a single Claude Code session (they're sequential and mechanical), bring the results back here for interpretation, then run Step 3 based on what was learned. Step 4 is primarily a conversation. Step 5 can be drafted in either environment.

### First Claude Code Task

```
Sprint 10, Step 1 — Baseline Backtest

1. Read and record ALL current parameter values from config/strategies/orb_breakout.yaml.
   Document them in the session output.

2. Run the Replay Harness with current defaults (no overrides):
   python -m argus.backtest.replay_harness \
       --start 2025-03-01 --end 2026-01-31 \
       --data-dir data/historical/1m --output-dir data/backtest_runs \
       --initial-cash 100000

3. Generate the baseline report from the output database.

4. Record total trade count. If < 20 trades, also run with --config-override max_range_atr_ratio=999.0
   and generate a second report.

5. Summarize key metrics (total trades, win rate, Sharpe, profit factor, max drawdown, monthly P&L)
   for each run.

6. Then proceed to Step 2: run the full VectorBT parameter sweep:
   python -m argus.backtest.vectorbt_orb \
       --data-dir data/historical/1m \
       --output-dir data/backtest_runs/sweeps \
       --start 2025-03-01 --end 2026-01-31

7. Summarize sweep findings: which parameters are most sensitive,
   what are the top 5 parameter sets by Sharpe (with min 20 trades).

Context: Sprint 8 gate check showed default max_range_atr_ratio=2.0 produced only 5 trades.
Expect the default baseline to have very few trades. This is expected, not a bug.
```

---

## Definition of Done

1. Baseline backtest complete with metrics recorded
2. At least 20 trades manually spot-checked against real charts
3. VectorBT parameter sweep complete with sensitivity classification
4. Walk-forward analysis complete for both default and optimized parameters
5. Parameter recommendations documented with justification
6. Final validation run with recommended parameters complete
7. `docs/backtesting/PARAMETER_VALIDATION_REPORT.md` written with all 9 sections
8. HTML reports generated and stored in `reports/`
9. `09_PHASE2_SPRINT_PLAN.md` updated: Sprint 10 marked ✅ COMPLETE
10. Phase 2 declared complete

---

## Documentation Updates Expected

After this sprint:
- **09_PHASE2_SPRINT_PLAN.md:** Mark Sprint 10 ✅ COMPLETE. Add summary of findings.
- **02_PROJECT_KNOWLEDGE.md (project instructions):** Update current state to "Phase 2 COMPLETE." Update test count. Add link to Parameter Validation Report.
- **CLAUDE.md:** Update current state to "Phase 2 complete. Phase 3 (Live Validation) next."
- **05_DECISION_LOG.md:** Add DEC-072+ for any parameter decisions made during analysis.
- **01_PROJECT_BIBLE.md:** Update ORB strategy parameters if recommendations change defaults.
- **config/strategies/orb_breakout.yaml:** Update with recommended parameters (after report is finalized).

---

*End of Sprint 10 Implementation Spec*
*This sprint completes Phase 2 (Backtesting Validation).*
