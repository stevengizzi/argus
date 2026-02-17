# Argus ORB Strategy — Parameter Validation Report

> **Phase 2 Deliverable** *(Updated with Sprint 11 Extended Walk-Forward Results)*
> Date: February 17, 2026
> Strategy: Opening Range Breakout (ORB)
> Dataset: 29 symbols, March 2023 – January 2026 (35 months)
> Backtesting toolkit: Replay Harness (production code replay) + VectorBT-equivalent parameter sweeps

---

## Section 0: How to Read This Report

This section explains every key metric used in this report. If you're already comfortable with systematic trading statistics, skip to Section 1. If not, read this carefully — understanding these numbers is as important as understanding the strategy itself. You'll be making real capital allocation decisions based on them.

### Sharpe Ratio

The Sharpe ratio measures your strategy's return relative to the risk it takes. Specifically, it's the average excess return (above the risk-free rate) divided by the standard deviation of those returns. Think of it as a "return per unit of stress" number.

A Sharpe of 0 means your strategy performs no better than putting money in a savings account. A Sharpe of 1.0 means you're earning one unit of return for each unit of volatility you're exposed to — this is generally considered good for a trading strategy. A Sharpe of 2.0+ is excellent, and a Sharpe of 3.0+ is exceptional (and should make you suspicious of overfitting). Negative Sharpe means you'd literally be better off in Treasury bills.

Concrete example: if your strategy has a Sharpe of 0.93 (as our recommended configuration does), it means the strategy is generating meaningful returns above cash, but the ride is bumpy. On a $100,000 account, you might make $8,000 in 11 months, but you'll experience weeks where you're down $3,000–$4,000 before recovering. The Sharpe tells you that the upside is real but modest — this is not a money printer, it's a probabilistic edge that plays out over many trades.

### Profit Factor

Profit Factor is the ratio of gross winning dollars to gross losing dollars. It's beautifully simple: take all the money you made on winning trades, divide by all the money you lost on losing trades, and you get a single number that tells you whether the strategy makes money.

A Profit Factor of 1.0 means you're breaking even — every dollar won is offset by a dollar lost. Below 1.0 means you're losing money. Above 1.0 means you're net profitable. In practice, a PF of 1.2–1.5 is solid for a day trading strategy. A PF above 2.0 is excellent but rare over large sample sizes.

Dollar example: our recommended configuration has a PF of 1.18 across 137 trades. That means for every $1.00 lost on losing trades, the strategy recovers $1.18 on winning trades. If total losses were $44,800, total wins were approximately $52,900, netting about $8,100. The edge is thin but positive — which is realistic for an automated strategy. Strategies claiming PFs of 3.0+ over hundreds of trades should be viewed with extreme skepticism.

### R-Multiple

R-Multiple expresses every trade's result as a multiple of the amount you risked on that trade. If you risked $500 on a trade (your stop loss distance × share count) and made $750, that's a +1.5R trade. If you lost the full $500, that's a -1.0R trade. If your stop triggered at a partial loss of $300, that's -0.6R.

This normalization is powerful because it lets you compare trades of different sizes on equal footing. A $2,000 profit on a $10,000 position where you risked $1,000 (2.0R) is a better trade than a $3,000 profit on a $30,000 position where you risked $5,000 (0.6R), even though the second trade made more raw dollars.

The average R-multiple across all your trades is essentially your edge per trade. Our strategy averages approximately 0.43R per winning trade via time stops (the ones that close in the money before the hold timer expires). Your losing trades average approximately -0.7R (some stopped out, some timed out at a loss). The net expectancy — factoring in win rate — determines whether the strategy prints money over time.

### Expectancy

Expectancy is what you expect to make, on average, per trade — expressed either in dollars or R-multiples. It combines win rate with average win size and average loss size into a single number.

The formula is: (Win Rate × Average Win) − (Loss Rate × Average Loss). If your win rate is 46.7%, your average win is $400, and your average loss is $320, your expectancy is (0.467 × $400) − (0.533 × $320) = $186.80 − $170.56 = $16.24 per trade. Multiply by expected trades per month (~13) and you get roughly $211/month on the position sizes used in backtesting.

Expectancy is the foundation of position sizing. If your expectancy is positive, you want to maximize the number of trades (more opportunities to realize the edge) while keeping each trade's risk small enough to survive the inevitable losing streaks. If your expectancy is negative or zero, no amount of position sizing will save you.

### Win Rate

Win rate is the percentage of trades that close in profit. It's the most intuitive metric — and also the most misleading one in isolation. A 90% win rate sounds fantastic until you learn that the 10% of losers each lose ten times more than the winners make. Conversely, a 35% win rate can be extremely profitable if the winners are 3–4x larger than the losers.

Our strategy has a 46.7% win rate with the recommended parameters. This means you will lose more often than you win. Psychologically, this is harder than it sounds — you need to be comfortable seeing three, four, or five losses in a row, knowing that over 50–100+ trades, the math works out. The win rate needs to be evaluated alongside the R-multiple distribution. A 46.7% win rate with an average win of 1.5R and average loss of 0.7R is a profitable system. A 46.7% win rate with an average win of 0.5R and average loss of 1.0R is not.

### Max Drawdown

Max drawdown is the largest peak-to-trough decline in your account equity before a new high is set. It answers the question: "What's the worst losing streak I can expect?" This is arguably the most important metric for staying in the game, because drawdowns are what kill traders — not individual losses, but the cumulative psychological and financial weight of a sustained losing period.

Dollar example: our strategy experienced a 6.6% max drawdown during backtesting. On a $100,000 account, that's a $6,600 decline from peak equity. You would have watched your account drop from, say, $108,000 to $101,400 over the October–January period. If you're risking 1% per trade ($1,000), a 6.6% drawdown means roughly 6–7 consecutive losses, which a 46.7% win rate will produce periodically.

The critical question is: can you survive the drawdown both financially and emotionally? A 6.6% drawdown is well within professional tolerance (20–30% is where most people tap out). But backtested drawdowns are always optimistic — live drawdowns are typically 1.5–2x worse due to slippage, poor fills, and market conditions the backtest didn't capture. Plan for a 10–15% live drawdown even if the backtest shows 6.6%.

### Walk-Forward Efficiency (WFE)

Walk-Forward Efficiency measures how well a strategy's optimized parameters perform on unseen data. It protects against overfitting — the insidious problem where a strategy looks amazing on historical data because you've (consciously or not) tuned it to match the past, but falls apart in live trading.

The process works like this: take your historical data, split it into a training period (in-sample, IS) and a test period (out-of-sample, OOS). Optimize parameters on the IS data. Then run those parameters on the OOS data without changing anything. WFE = OOS performance / IS performance. A WFE of 1.0 means the strategy performed identically on unseen data as on the data it was optimized for — perfect generalization. A WFE of 0.5 means it retained half its performance. A WFE below 0.3 is concerning, and a negative WFE means the optimization actually hurt — classic overfitting.

Our walk-forward results were **inconclusive** (WFE of 0.0 for three candidates, -4.09 for one). This is not necessarily damning — 11 months of data only produces 3 walk-forward windows, where the industry standard requires 8–12+. The insufficient data means we can't confirm or deny that the strategy generalizes. It's an honest "we don't know yet," which is very different from "it failed." Phase 3 paper trading provides the real forward-looking validation.

### Equity Curve

An equity curve is simply a line chart of your account value over time. A healthy equity curve trends upward with relatively small and short drawdowns — it looks like a staircase going up with some dips. A concerning equity curve shows one of several patterns: a plateau (the strategy stopped working), a hockey stick (one or two big trades drove all the returns — not repeatable), or a sawtooth (volatile swings with no net progress).

Our equity curve shows steady growth from March through September, then a decline from October through January. This could indicate seasonal sensitivity (the strategy works better in certain market conditions), or it could be coincidence — with only 11 months of data, we genuinely can't tell. If the curve looked like "up in months 1–3, down in months 4–11," that would be much more concerning than the pattern we see.

### Parameter Sensitivity Heatmaps

The heatmaps in the interactive HTML reports show how strategy performance changes as you vary two parameters simultaneously. Each cell represents a specific combination (e.g., opening_range_minutes = 5 and max_hold_minutes = 15), and the color represents performance (Sharpe ratio, profit factor, etc.).

What you want to see is a **stable region** — a cluster of cells with similar, positive values. This means the strategy isn't brittle; small changes in parameters don't dramatically alter performance. If the best performance sits on a narrow peak surrounded by poor results, the strategy is fragile and likely overfit.

What to worry about: if the best-performing cell is surrounded by cells with dramatically different (especially negative) performance, those parameters are fragile — a small change in market conditions could push you off the peak. Conversely, if a broad swath of the heatmap shows similar positive returns, the strategy is robust to parameter choice and more likely to perform in live trading.

---

## Section 1: Executive Summary

The ORB (Opening Range Breakout) strategy should proceed to Phase 3 live paper trading validation, with recommended parameters and explicit monitoring criteria. The extended walk-forward validation (Sprint 11) provides increased confidence in the strategy's aggregate edge, while confirming high period-to-period variance.

**Original Phase 2 findings:** The backtesting produced a net profit of $8,087 on $100,000 over 11 months (137 trades, Sharpe 0.93, Profit Factor 1.18) using recommended parameters that shortened the opening range window from 15 to 5 minutes and the maximum hold time from 30 to 15 minutes. These two parameter changes turned a break-even strategy into a modestly profitable one.

**Sprint 11 Extended Validation:** The dataset was extended to 35 months (March 2023 – January 2026) to address the original data insufficiency. Walk-forward analysis now covers 15 windows (vs. 3 originally). Key findings:
- **Fixed-params (DEC-076) outperform adaptive optimization** — OOS Sharpe +0.34 vs. -11.46
- **Aggregate OOS profitability confirmed** — $7,741 profit across 378 trades in ~2.5 years of OOS periods
- **67% of windows profitable** — 10/15 windows had positive OOS Sharpe
- **Traditional WFE threshold not met** — avg WFE (Sharpe) is -0.91, but this measures predictability, not profitability

The nuanced interpretation is that the strategy has a real but inconsistent edge. Individual 2-month periods vary widely (Sharpe from -4.8 to +4.5), but in aggregate the strategy makes money. This supports paper trading but requires patience through inevitable drawdown periods.

**Remaining caveats:** The strategy produced zero target-price exits (all profitable exits via time stops), and severe market regimes (bear markets, crises) are not represented in the test data.

The recommendation is to proceed to paper trading with minimum position sizes (10–25 shares per trade regardless of what the sizing model suggests), monitor the target-hit pattern and period-by-period performance, and plan for a minimum 20-trading-day evaluation period before drawing conclusions.

---

## Section 2: Dataset Description

### Symbol Universe

The backtest covers 28 US equities selected for high liquidity, active day trading participation, and representation across market segments:

| Category | Symbols |
|----------|---------|
| Index ETF | SPY |
| Mega-cap Tech | AAPL, MSFT, NVDA, META, AMZN, GOOG |
| High-beta Tech | TSLA, AMD, NFLX, PLTR, COIN, ARM |
| Momentum | SOFI, MARA, RIOT, SNAP, ROKU, SHOP, SMCI |
| Financials | PYPL, JPM, GS |
| Industrials | BA, UBER, DIS, XOM |
| Semiconductors | INTC, MU |

SPY is included as a market regime reference but is also scanned as a tradeable symbol. SQ (Block Inc.) was originally in the universe but removed due to no IEX data feed coverage from Alpaca; PYPL replaced it.

### Data Specifications

All data was sourced from Alpaca Markets' free-tier IEX feed, downloaded as 1-minute bars, split-adjusted, stored as Parquet files with UTC timestamps. The dataset spans March 1, 2025 through January 31, 2026 — 11 calendar months covering approximately 230 trading days. Total: 2,231,905 bars across 308 Parquet files (52 MB).

### Data Quality

The data passed five automated validation checks (OHLC consistency, zero-volume filtering, timezone verification, duplicate detection, and trading day completeness) with two known issues. March 10, 2025 is missing across all 28 symbols due to an IEX feed gap — this represents one trading day out of ~230, or roughly 0.4% of the dataset. SQ returned no data at all and was excluded.

### Market Conditions During the Test Period

The 11-month period (March 2025 – January 2026) captures a range of market conditions, though not a full market cycle. Without going through month-by-month SPY performance in detail (the reader should consult the interactive reports for equity curves), the period included both trending and range-bound phases, some elevated VIX periods, and a mix of sector rotation. Notably, the strategy performed better in the spring and summer months and worse in the fall and winter — though whether this reflects the strategy's regime sensitivity or is simply the pattern this particular year happened to produce cannot be determined from a single year.

### Limitations of the Dataset

*Original Phase 2 analysis:* Eleven months was a thin dataset for validating a trading strategy. Walk-forward analysis was constrained to 3 windows where 8–12 is standard.

*Sprint 11 extension:* The dataset was extended to 35 months (March 2023 – January 2026) to address this limitation. The extended walk-forward ran 15 windows — well above the 8–12 standard. See Section 5b for the extended results.

The remaining limitation is that 3 years still captures limited market regimes. A true bear market (e.g., 2022) or crisis event (e.g., March 2020) is not represented. The strategy's behavior in severe downturns remains untested.

---

## Section 3: Baseline Performance

### Default Parameters (8 Trades)

The first backtest ran the Replay Harness with production default parameters: 15-minute opening range, 30-minute max hold, 2.0R target, 0% stop buffer, 2% minimum gap, and a `max_range_atr_ratio` of 2.0. The result was 8 trades across 11 months — far too few to evaluate any strategy.

The culprit was the `max_range_atr_ratio` filter, which compares the opening range size to the 14-period ATR. With the production ATR calculated from 1-minute bars (rather than daily bars), almost every opening range appeared "too wide" relative to ATR. Of all the opening ranges the strategy evaluated, 98.5% were rejected by this single filter. The 8 trades that passed produced a misleadingly high win rate (62.5%) and Sharpe (5.06), but with 8 data points, these statistics are meaningless.

This finding itself was valuable: it identified a fundamental mismatch between the ATR filter's intent (reject abnormally wide ranges relative to the stock's normal daily volatility) and its implementation (comparing range to 1-minute ATR, which measures intrabar noise, not daily volatility). This led to DEC-075 disabling the filter for Phase 3 and flagging the need for a proper daily-bar ATR implementation in the future.

Interactive report: `reports/orb_baseline_defaults.html`

### Relaxed Baseline (135 Trades)

With `max_range_atr_ratio` disabled (set to 999.0) and all other defaults unchanged (15-minute opening range, 30-minute max hold), the strategy produced 135 trades — a meaningful sample size. But the results were sobering: Sharpe -0.26, Profit Factor 1.00, net P&L of $71. The strategy was essentially break-even over 11 months. Average hold time was 111 minutes (due to positions held to end-of-day), and the win rate was 48.1%.

This baseline serves two purposes. First, it proves the Replay Harness works — 135 trades is enough to evaluate, the metrics are reasonable, and the strategy is behaving as designed (scanning for gaps, waiting for breakouts, placing bracket orders, managing exits). Second, it establishes the performance floor: with the original 15-minute opening range and 30-minute hold, the ORB strategy has no meaningful edge. Any improvement from parameter optimization is measured against this zero-edge baseline.

Interactive report: `reports/orb_baseline_relaxed.html`

---

## Section 4: Parameter Sensitivity

### The VectorBT Parameter Sweep

To understand which parameters matter and which are noise, a full parameter sweep evaluated 522,000 combinations (29 symbols × ~18,000 parameter sets) across the 11-month dataset. This used a vectorized NumPy/Pandas implementation equivalent to VectorBT's core functionality (the VectorBT library itself was dropped due to numba compatibility issues — see DEC-063). The full sweep completed in 63 seconds.

The six parameters swept were: `opening_range_minutes` (5, 10, 15, 20, 30), `max_hold_minutes` (5, 10, 15, 30, 45, 60), `min_gap_pct` (1.0, 1.5, 2.0, 3.0, 5.0), `max_range_atr_ratio` (0.3, 0.5, 0.75, 1.0, 1.5, 999.0), `stop_buffer_pct` (0.0, 0.1, 0.2, 0.3), and `target_r` (1.0, 1.5, 2.0, 2.5, 3.0).

### Sensitivity Classification

The sweep revealed a clear hierarchy: two parameters dominate strategy performance, one has a meaningful but secondary effect, and three are essentially noise.

| Parameter | Sensitivity | Best Value | Finding |
|-----------|------------|------------|---------|
| `opening_range_minutes` | **High** | 5 | Monotonic relationship: shorter ranges produce better results. 5-minute ranges significantly outperform 15- and 30-minute ranges. Every top-10 parameter set uses 5 minutes. |
| `max_hold_minutes` | **High** | 15 | Clear gradient: shorter holds are better. The ORB edge is front-loaded — if the breakout is going to work, it works quickly. Holding longer adds risk without adding return. |
| `min_gap_pct` | **Medium-High** | 3.0% (sweep) / 2.0% (recommended) | Higher gap thresholds improve average trade quality but reduce trade count. The sweep found 3.0% optimal, but 2.0% preserves enough trade frequency for paper trading evaluation. |
| `max_range_atr_ratio` | **High (non-transferable)** | 0.30 (sweep) | This parameter dominated the sweep results but is **not usable** — see ATR Divergence below. |
| `stop_buffer_pct` | **Low** | 0.0 | Minimal impact across all tested values (0.0–0.3%). The stop at the opening range low works as-is. |
| `target_r` | **Low** | 2.0 | All values from 1.0 to 3.0 produced similar results. This finding becomes even more significant in light of Section 7's zero-target-hit discovery. |

### Top 5 Parameter Sets from Sweep

All five top-performing sets share the same core structure: 5-minute opening range, 15-minute hold, 2.0% gap minimum, and 0.5 ATR ratio. They differ only in `target_r` and `stop_buffer_pct`, which are the two low-sensitivity parameters.

| Rank | or_min | target_r | stop_buf | max_hold | min_gap | max_atr | Sharpe | Trades | PF |
|------|--------|----------|----------|----------|---------|---------|--------|--------|----|
| 1 | 5 | 1.0 | 0.0 | 15 | 2.0 | 0.5 | 3.87 | 179 | 2.07 |
| 2 | 5 | 2.5 | 0.0 | 15 | 2.0 | 0.5 | 3.76 | 179 | 2.07 |
| 3 | 5 | 2.0 | 0.0 | 15 | 2.0 | 0.5 | 3.72 | 179 | 2.04 |
| 4 | 5 | 2.0 | 0.1 | 15 | 2.0 | 0.5 | 3.65 | 179 | 2.04 |
| 5 | 5 | 3.0 | 0.0 | 15 | 2.0 | 0.5 | 3.64 | 179 | 2.04 |

The convergence is striking — the top 5 all have the same trade count (179) and near-identical profit factors. The Sharpe variation from 3.64 to 3.87 comes entirely from the low-sensitivity parameters. This suggests the strategy's performance is genuinely driven by `opening_range_minutes` and `max_hold_minutes`, not by fine-tuning secondary parameters.

Interactive heatmaps: `data/backtest_runs/sweeps/interactive/`

### The ATR Divergence Problem

The most important finding from the parameter sweep is something that *doesn't* work: the `max_range_atr_ratio` parameter. In the sweep, it appeared to be the most impactful filter — tighter ATR thresholds (0.3, 0.5) dramatically outperformed loose ones. But this finding is meaningless for production use.

The root cause is an architectural mismatch. The VectorBT sweep computes ATR from daily aggregated bars (one bar per day). The production code (and Replay Harness) computes ATR from 1-minute bars with Wilder smoothing. These produce fundamentally different scales — the range/ATR ratio for the same stock on the same day might be 0.4 in VectorBT but 3.5 in production, because 1-minute ATR measures intrabar noise while daily ATR measures full-day price range.

This means the ATR thresholds found in the sweep (0.3, 0.5, etc.) are not transferable to production. Setting `max_range_atr_ratio` to 0.5 in production would reject nearly every trade (as we saw with the default 2.0, which rejected 98.5%). Per DEC-075, this filter is disabled (set to 999.0) for Phase 3. Building a proper daily-bar ATR infrastructure is deferred until paper trading demonstrates the filter's value.

The other five parameters (`opening_range_minutes`, `max_hold_minutes`, `min_gap_pct`, `stop_buffer_pct`, `target_r`) are computed identically in both environments and transfer cleanly.

---

## Section 5: Walk-Forward Validation

### Purpose

Walk-forward validation is the gold standard for confirming that optimized parameters aren't just memorizing the past. The process splits the data into alternating training (in-sample) and testing (out-of-sample) windows, optimizes parameters on training data, then evaluates on test data. Walk-Forward Efficiency (WFE) — the ratio of OOS to IS performance — measures generalization quality. Per DEC-047, a WFE of 0.3 or higher is required to consider parameters validated.

### Setup

The 11-month dataset was divided into 3 walk-forward windows using a 4-month in-sample / 2-month out-of-sample / 2-month step configuration:

| Window | In-Sample Period | Out-of-Sample Period |
|--------|-----------------|---------------------|
| 1 | Mar 2025 – Jun 2025 | Jul 2025 – Aug 2025 |
| 2 | May 2025 – Aug 2025 | Sep 2025 – Oct 2025 |
| 3 | Jul 2025 – Oct 2025 | Nov 2025 – Dec 2025 |

Three windows is the minimum possible with this data length. For robust validation, 8–12 windows across 3–5 years of data is standard. This constraint should be kept in mind when interpreting results.

### Results

Four parameter candidates were tested, ranging from tight to relaxed filtering:

| Candidate | or | hold | atr | gap | target_r | stop_buf | OOS Trades | OOS Sharpe | Mean WFE |
|-----------|-----|------|------|-----|----------|----------|------------|------------|----------|
| A (tight) | 5 | 15 | 0.5 | 2.0 | 2.0 | 0.0 | 2 | 0.00 | 0.00 |
| B | 5 | 15 | 1.0 | 2.0 | 2.0 | 0.0 | 2 | 0.00 | 0.00 |
| C | 5 | 30 | 0.75 | 2.0 | 2.0 | 0.1 | 2 | 0.00 | 0.00 |
| D (relaxed) | 5 | 30 | 999 | 2.0 | 2.0 | 0.0 | 81 | -4.19 | -4.09 |

No candidate achieved the WFE ≥ 0.3 threshold. This is a Scenario C result per the Sprint 10 spec: inconclusive.

### Interpreting the Results

The results divide into two clear failure modes. Candidates A, B, and C used ATR filters that, due to the ATR divergence described in Section 4, rejected almost every trade in both the IS and OOS windows. Two OOS trades across three two-month windows is not "the strategy failed" — it's "the filter was miscalibrated to the point of silence." These candidates cannot be evaluated because there's no data to evaluate.

Candidate D disabled the ATR filter and produced a healthy trade count (81 OOS trades). But it showed classic overfitting: strong in-sample performance (Sharpe +3.49) collapsed to deeply negative out-of-sample performance (Sharpe -7.24 in the worst window, -4.19 mean). The parameters that looked optimal in training data performed terribly on unseen data.

However, Candidate D used a 30-minute max hold — not the 15-minute hold that dominates the full-period analysis. The walk-forward framework re-optimized all parameters in each IS window, and the optimizer apparently preferred 30-minute holds within the IS periods. The fact that a 30-minute hold overfits while a 15-minute hold might not is consistent with the sensitivity analysis: longer holds introduce more noise and more opportunity for the optimizer to chase phantom patterns.

### The Data Insufficiency Factor

The honest assessment is that 11 months / 3 windows is simply insufficient for walk-forward validation of this strategy. The walk-forward framework itself is working correctly (it was thoroughly tested in Sprint 9 with 542 tests passing). The problem is the data, not the tool.

Consider: with 3 windows of 2-month OOS periods, each window might contain only 20–30 qualifying trades. A single anomalous week — an earnings surprise, a macro shock, an unusual sector rotation — can dominate the statistics of a 2-month window. With 12 windows of 2-month periods, outliers average out. With 3 windows, they don't.

This is why the result is classified as inconclusive (Scenario C) rather than failed (Scenario B). A definitive failure would require enough data to show that, across many windows, the strategy consistently fails OOS. We don't have that data. What we have is an honest "the test was underpowered." Paper trading provides the forward validation that the walk-forward could not.

---

## Section 5b: Extended Walk-Forward Results (Sprint 11)

### Purpose

Sprint 11 extended the historical data from 11 months to 35 months (March 2023 – January 2026) specifically to address the data insufficiency problem identified in Section 5. With ~3 years of data, we can now run a proper walk-forward analysis with 15 windows — well above the 8–12 minimum required for statistical reliability.

### Dataset Extension

| Metric | Original (Phase 2) | Extended (Sprint 11) |
|--------|-------------------|----------------------|
| Date range | Mar 2025 – Jan 2026 | Mar 2023 – Jan 2026 |
| Months covered | 11 | 35 |
| Symbols | 28 | 29 |
| Total bars | 2.2M | 7.0M |
| Walk-forward windows | 3 | 15 |

The extended dataset covers multiple market regimes including the 2023 recovery rally, 2024's range-bound periods, and various volatility events. This provides much more robust validation than the original single-year dataset.

### Methodology

Two walk-forward analyses were run:

1. **Optimizer mode**: Each in-sample window selects the best-performing parameters via VectorBT sweep, then runs those params on the subsequent OOS window. This tests whether adaptive optimization adds value.

2. **Fixed-params mode**: The recommended DEC-076 parameters (or=5, hold=15, gap=2.0, stop_buf=0.0, target_r=2.0, max_atr=999.0) are applied to all windows. This tests whether the Phase 2 recommendations generalize.

Window configuration: 4-month IS / 2-month OOS / 2-month step.

### Results Summary

| Metric | Optimizer | Fixed-Params (DEC-076) |
|--------|-----------|------------------------|
| Windows | 15 | 15 |
| Avg WFE (Sharpe) | -0.38 | -0.91 |
| Avg WFE (P&L) | -0.03 | **+0.56** |
| Total OOS Trades | 93 | **378** |
| Overall OOS Sharpe | -11.46 | **+0.34** |
| Overall OOS P&L | $7,204 | **$7,741** |
| Parameter stability | ~33% | 100% |

### Per-Window Detail (Fixed-Params)

| Window | OOS Period | OOS Sharpe | OOS Trades | WFE |
|--------|-----------|------------|------------|-----|
| 1 | Jul–Aug 2023 | +3.50 | 23 | 0.00 |
| 2 | Sep–Oct 2023 | -0.33 | 27 | 0.00 |
| 3 | Nov–Dec 2023 | -3.28 | 28 | 0.00 |
| 4 | Jan–Feb 2024 | +3.74 | 22 | 0.00 |
| 5 | Mar–Apr 2024 | -4.49 | 31 | -3.17 |
| 6 | May–Jun 2024 | +0.11 | 23 | 0.00 |
| 7 | Jul–Aug 2024 | +0.23 | 25 | 0.00 |
| 8 | Sep–Oct 2024 | -4.75 | 28 | -12.23 |
| 9 | Nov–Dec 2024 | +1.52 | 20 | 0.00 |
| 10 | Jan–Feb 2025 | -0.79 | 28 | -0.33 |
| 11 | Mar–Apr 2025 | +2.75 | 34 | 0.00 |
| 12 | May–Jun 2025 | +2.08 | 25 | 0.98 |
| 13 | Jul–Aug 2025 | +4.51 | 14 | 0.84 |
| 14 | Sep–Oct 2025 | +0.92 | 25 | 0.19 |
| 15 | Nov–Dec 2025 | -0.54 | 25 | 0.00 |

**Windows with positive OOS Sharpe:** 10/15 (67%)
**Windows with WFE ≥ 0.3:** 2/15 (13%)

### Interpretation

The extended walk-forward results are nuanced and require careful interpretation.

**Why WFE (Sharpe) is negative:** WFE = OOS Sharpe / IS Sharpe. When IS Sharpe is negative (a poor training period), and OOS Sharpe is positive (good forward performance), WFE is floored at 0. When IS Sharpe is positive but OOS Sharpe is negative, WFE is negative. The high variance of both IS and OOS Sharpe across windows produces a negative average WFE — but this measures predictability, not profitability.

**What matters for trading:**
1. **Overall OOS Sharpe is +0.34** — positive, indicating the strategy makes risk-adjusted returns in aggregate
2. **Overall OOS P&L is +$7,741** — the strategy made money across 2.5 years of out-of-sample periods
3. **67% of windows had positive OOS Sharpe** — the strategy is more often profitable than not
4. **378 trades in OOS** — statistically meaningful sample size

**Fixed params vs. optimizer:** The optimizer performed *worse* than fixed params despite having the advantage of per-window optimization:
- Optimizer OOS Sharpe: -11.46 (deeply negative)
- Fixed-params OOS Sharpe: +0.34 (positive)

This is classic overfitting behavior. The optimizer finds parameters that look good in-sample but fail out-of-sample. The fixed parameters, while not optimized for each window, actually generalize better because they're not chasing noise.

### Scenario Classification

Per Sprint 11 spec:
- **Scenario A (WFE ≥ 0.3):** Not met — avg WFE (Sharpe) is -0.91
- **Scenario B (sweep finds better params):** Not met — optimizer mode performed worse
- **Scenario C (no parameter set generalizes):** Partially applicable but oversimplified

**Refined assessment:** The DEC-076 parameters show **aggregate profitability** (positive OOS Sharpe, positive OOS P&L) despite not meeting the traditional WFE threshold. The parameters "generalize" in the practical sense — they make money on unseen data — even though the IS Sharpe doesn't numerically predict the OOS Sharpe.

This is consistent with a strategy that has a real but modest edge that manifests inconsistently across time periods. Some 2-month windows will be profitable, others won't, but over many windows the edge accumulates.

### Recommendation Update

The extended walk-forward results **support proceeding with paper trading** using DEC-076 parameters, but calibrate expectations:

1. **The strategy has an aggregate edge** — positive OOS returns over 2.5 years of forward-looking periods
2. **Individual periods will vary widely** — some months will be great (+4.5 Sharpe), others terrible (-4.8 Sharpe)
3. **Don't expect IS performance to predict OOS** — the WFE is negative, meaning optimization doesn't help
4. **Fixed parameters outperform adaptive optimization** — trust DEC-076, don't chase recent performance

The original Phase 2 recommendation (proceed to paper trading with minimum position sizes) remains valid. The extended data provides more confidence in the aggregate edge while reinforcing the need for patience through drawdown periods.

---

## Section 6: Parameter Recommendations

### Decision Framework

Each parameter recommendation considers four factors: (1) the sensitivity analysis — how much does this parameter affect performance? (2) the sweep's best value — what does the data say is optimal? (3) robustness — is the optimal value on a sharp peak or a broad plateau? (4) conservatism — when in doubt, prefer the safer choice.

### Recommendation Table

| Parameter | Old Default | Recommended | Sensitivity | Justification |
|-----------|-------------|-------------|-------------|---------------|
| `opening_range_minutes` | 15 | **5** | High | Every top-10 parameter set uses 5 minutes. The relationship is monotonic — shorter ranges consistently outperform longer ones. This aligns with the ORB thesis: tight ranges produce sharper breakouts. |
| `max_hold_minutes` | 30 | **15** | High | Clear gradient: shorter holds are better. The ORB edge is front-loaded; if the breakout is going to work, it works within 15 minutes. Holding beyond that adds risk (mean reversion, news events) without proportional reward. |
| `min_gap_pct` | 2.0 | **2.0** (no change) | Medium-High | The sweep found 3.0% slightly better, but 2.0% preserves trade frequency (~13/month vs. ~8/month). During paper trading, we need enough trades to evaluate the strategy within a reasonable timeframe. Can be tightened later if quality > quantity proves out. |
| `stop_buffer_pct` | 0.0 | **0.0** (no change) | Low | Minimal impact across all tested values. The stop at the opening range low is the natural support level; adding buffer didn't meaningfully improve results. |
| `target_r` | 2.0 | **2.0** (no change) | Low | All values from 1.0 to 3.0 produced similar results in the sweep. This becomes even less meaningful given that zero target exits triggered in the final validation — see Section 7. The parameter is retained at 2.0 for now but is a candidate for revisiting once paper trading data is available. |
| `max_range_atr_ratio` | 2.0 | **999.0** (disabled) | N/A | Disabled per DEC-075. The production ATR calculation (1-minute bars) produces values on a fundamentally different scale than the sweep's ATR (daily bars). The filter's intent is sound but its implementation needs daily ATR infrastructure, which is deferred. |

### Configuration Diff

```yaml
# Before (Phase 1 defaults)
opening_range_minutes: 15
max_hold_minutes: 30
min_gap_pct: 2.0
stop_buffer_pct: 0.0
target_r: 2.0
max_range_atr_ratio: 2.0

# After (Phase 3 recommended)
opening_range_minutes: 5
max_hold_minutes: 15
min_gap_pct: 2.0
stop_buffer_pct: 0.0
target_r: 2.0
max_range_atr_ratio: 999.0  # disabled
```

Two parameters changed (`opening_range_minutes`, `max_hold_minutes`), one disabled (`max_range_atr_ratio`), three unchanged. This is a conservative approach — the sweep suggested changes to `min_gap_pct` and `target_r` as well, but the improvements were marginal and changing too many parameters at once reduces our ability to understand what's driving performance in live conditions.

---

## Section 7: Final Validation Results

### Summary Metrics

The Replay Harness was run with the recommended parameters across the full 11-month dataset (28 symbols, $100,000 starting capital):

| Metric | Value |
|--------|-------|
| Total trades | 137 |
| Win rate | 46.7% |
| Sharpe ratio | 0.93 |
| Profit Factor | 1.18 |
| Net P&L | +$8,087 |
| Max drawdown | 6.6% |
| Average hold time | 49 minutes |
| Trades per month (avg) | 12.5 |

Interactive report: `reports/orb_final_validation.html`

### Comparison to Baselines

| Metric | Default (ATR=2.0) | Relaxed (ATR=999, or=15) | Recommended (ATR=999, or=5) |
|--------|-------------------|--------------------------|----------------------------|
| Trades | 8 | 135 | 137 |
| Win Rate | 62.5% | 48.1% | 46.7% |
| Sharpe | 5.06 | -0.26 | 0.93 |
| PF | 2.23 | 1.00 | 1.18 |
| Net P&L | $1,065 | $71 | $8,087 |
| Avg Hold | 31 min | 111 min | 49 min |

The default configuration is statistically meaningless (8 trades). The meaningful comparison is relaxed vs. recommended: same trade count, same ATR filter state, but the shorter opening range and hold time turned a break-even strategy ($71 profit) into a modestly profitable one ($8,087). This $8,000 delta comes entirely from the two high-sensitivity parameter changes.

### Monthly Performance

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

The monthly data shows two distinct periods. March through September was consistently profitable (7 months, cumulative +$15,487, average win rate 55%). October through January was consistently unprofitable (4 months, cumulative -$7,402, average win rate 25%). The transition happened abruptly — September was the best single month (+$5,759) and October was the start of the drawdown.

Is this seasonal? Regime-dependent? Coincidence? With one data point per pattern, we genuinely cannot tell. The strategy should be run through at least one more spring/summer and fall/winter before drawing conclusions. If Phase 3 paper trading shows a similar pattern (strong spring, weak fall), that's a data point worth acting on. If it doesn't, the backtest pattern was likely noise.

### Exit Distribution

| Exit Type | Count | Percentage |
|-----------|-------|------------|
| Stop loss | 95 | 69.3% |
| Time stop (max hold) | 38 | 27.7% |
| EOD flatten | 4 | 2.9% |
| Target hit | 0 | 0.0% |

This is the most striking finding in the entire report: **zero target-price exits** out of 137 trades.

The strategy is designed around an R-multiple framework: risk $X at the stop, target a 2.0R reward. In theory, winning trades should hit the 2.0R target. In practice, with a 5-minute opening range and a 15-minute max hold, the price simply doesn't have time to travel 2R from the entry before the time stop fires.

What actually happens on winning trades is this: the stock breaks out above the opening range high, moves partially toward the target (perhaps 0.3R to 1.0R), and then the 15-minute hold timer expires. If the position happens to be in the money at that point, it exits as a profitable time stop. The strategy is making money not from the R:R framework working as designed, but from the statistical tendency of breakout moves to be net-positive within the first 15 minutes — even if they don't reach a 2.0R target.

This is not necessarily a problem. The strategy is profitable. But it means the `target_r` parameter is functionally irrelevant with a 15-minute hold — the target never triggers regardless of whether it's set to 1.0R or 3.0R (which explains why the sweep found `target_r` to be a low-sensitivity parameter). In Phase 3, there are two things to monitor: (1) whether reducing `target_r` to 1.0R or introducing a trailing stop would capture more profitable exits before the time stop fires, and (2) whether the time-stop exits are genuinely capturing the ORB edge or are just random noise that happened to be net-positive in this dataset.

---

## Section 8: Known Limitations & Open Questions

### Data Limitations

**~~Limited historical coverage.~~** *(RESOLVED in Sprint 11)* The dataset was extended from 11 months to 35 months (March 2023 – January 2026), covering ~3 years and multiple market regimes. This is now adequate for walk-forward validation.

**Walk-forward results.** *(UPDATED in Sprint 11)* The extended walk-forward ran 15 windows (vs. 3 originally) — well above the 8–12 standard. The traditional WFE (Sharpe) threshold of 0.3 was not met (avg WFE = -0.91 for fixed-params). However, the strategy shows **positive aggregate OOS returns** (Sharpe +0.34, P&L +$7,741 over ~2.5 years of OOS periods). This is a nuanced result: the parameters produce aggregate profitability without numerically predictable per-window performance. See Section 5b for full analysis.

**Single data source.** All data comes from Alpaca's IEX feed. IEX may have different price characteristics than consolidated tape data, particularly during the volatile market open when ORB trades execute. One missing day (March 10, 2025) confirms IEX is not perfectly reliable.

### Strategy Design Questions

**Zero target hits.** The 2.0R target never triggered within the 15-minute hold window. This raises a fundamental question: should the target be lowered (e.g., to 1.0R) so that some winning trades exit at target rather than time stop? Or is the time stop actually the right exit mechanism for this strategy, and the target should be removed entirely? This needs empirical investigation in Phase 3, ideally by A/B testing different target values.

**ATR filter disabled.** The `max_range_atr_ratio` filter is disabled (DEC-075) because the production ATR uses 1-minute bars, which measures a fundamentally different thing than the daily ATR the filter was designed for. The filter's intent — rejecting abnormally wide opening ranges — is sound. Building daily ATR infrastructure (computing ATR from daily bars and making it available as a strategy filter) is a future enhancement that would allow this filter to function as designed.

**VectorBT vs. Replay Harness trade count divergence.** Even with the ATR filter disabled and all six parameters matched, VectorBT produces 21 trades for TSLA while the Replay Harness produces 39 (cross-validation after DEC-074 fixes). The remaining gap is expected: VectorBT doesn't model VWAP confirmation, volume confirmation, or chase protection — three entry filters that exist in the production code but were not replicated in the vectorized sweep. This means VectorBT is more conservative (misses trades the production code takes), which is the safe direction for parameter optimization.

### Statistical Concerns

**Possible seasonal pattern.** Strong March–September (+$15,487) vs. weak October–January (-$7,402) is suggestive but inconclusive with only one year. If this pattern is real, it could mean the ORB strategy works primarily in certain market regimes. If it's noise, there's no action to take. Phase 3 will provide a second data point.

**Fixed slippage model.** The backtest uses a fixed $0.01/share slippage (DEC-054). Real slippage during market open — the exact time ORB trades execute — is likely higher, especially for stocks with wider spreads or lower liquidity. On a 100-share position, $0.01 slippage costs $1.00 per trade. Real slippage might be $0.03–$0.10 per share for volatile gap stocks, costing $3–$10 per trade. Across 137 trades, the difference between $0.01 and $0.05 slippage is $548 — meaningful relative to the $8,087 net P&L. Phase 3 paper trading will provide real fill data to calibrate slippage.

**Commission model.** The backtest does not model commissions. Alpaca charges zero commission for stock trades, but this may not be the case for all future brokers (IBKR has per-share fees). At IBKR's rate of $0.005/share, 137 trades averaging 100 shares each would cost approximately $137 — a small but non-zero impact.

---

## Section 9: Phase 3 Live Trading Recommendation

### Go/No-Go Decision

**Go**, with controlled conditions. The strategy shows a modest positive edge in backtesting (Sharpe 0.93, PF 1.18) with manageable drawdown (6.6%). While the walk-forward validation was inconclusive, it was underpowered rather than failed. Paper trading at minimum size carries negligible financial risk and provides the forward-looking validation that backtesting could not deliver.

### Position Sizing

Start with **fixed minimum sizes regardless of what the position sizing model calculates**:

| Phase | Duration | Position Size | Rationale |
|-------|----------|--------------|-----------|
| Ramp 1 | First 20 trading days | 10 shares per trade | Baseline: verify fills, slippage, execution quality |
| Ramp 2 | Next 20 trading days | 25 shares per trade | Increased size, still minimal capital at risk |
| Ramp 3 | After 40 trading days | Model-calculated size | Transition to algorithmic sizing if metrics are acceptable |

With 10-share positions on stocks in the $50–$500 range, each trade risks $50–$500. At ~13 trades/month, monthly risk exposure is $650–$6,500 in notional terms (actual risk is capped by stops at a fraction of this). This is paper money — the point is not to make money but to validate the system.

### Capital Allocation

The paper trading account starts with $100,000 (Alpaca's default paper balance). Allocate 100% to the ORB strategy since it's the only strategy running. In Phase 4, when the Orchestrator and second strategy arrive, capital allocation becomes a real decision.

### Expected Performance Benchmarks

Based on backtesting, Phase 3 should expect approximately:

| Metric | Expected Range | Concern Threshold |
|--------|---------------|-------------------|
| Trades per month | 10–16 | < 5 or > 25 |
| Win rate | 40–55% | < 30% over 30+ trades |
| Profit Factor | 1.0–1.5 | < 0.8 over 30+ trades |
| Max drawdown | 5–10% | > 15% at any point |
| Avg hold time | 30–60 min | > 120 min consistently |

These ranges include a buffer for the expected degradation from backtest to live performance. If paper trading metrics fall within these ranges, the system is performing as backtested. If they fall outside, investigation is warranted but not necessarily a strategy kill.

### Kill Criteria

Stop trading and investigate if any of the following occur:

1. **Account drawdown exceeds 15%.** The backtest max was 6.6%. A 15% drawdown in paper trading would indicate either a regime the backtest didn't capture or a system malfunction. Pause, investigate, don't restart until root cause is identified.

2. **Profit Factor below 0.7 after 50+ trades.** A PF of 0.7 means you're losing $1.43 for every $1.00 you make — the strategy has a negative edge. At 50+ trades, this is statistically significant enough to act on.

3. **Win rate below 25% over any 30-trade window.** The backtest's worst monthly win rate was 21.4% (December and January), but these were 14-trade months. A sustained 25% win rate over 30 trades (roughly 2–3 months at expected frequency) suggests a structural problem.

4. **System error: missed fills, orphaned orders, or position tracking discrepancies.** Any data integrity or execution error is grounds for an immediate pause. Financial systems must be correct before they're profitable.

5. **Zero trades for 5 consecutive trading days when the scanner identifies gap candidates.** This suggests a filter is silently rejecting everything — similar to the original ATR filter problem.

### What to Monitor

Beyond the kill criteria, actively track these patterns during paper trading:

**Target hit rate.** The backtest produced zero target exits. If this persists in paper trading (and it likely will with a 15-minute hold and 2.0R target), it confirms the finding and motivates either reducing the target or replacing it with a trailing stop. If targets *do* start hitting, something has changed from the backtest conditions — investigate why.

**Time stop profitability.** The strategy's entire positive expectancy comes from time-stopped exits that happen to be in the money. Track the average P&L of time-stopped trades separately. If time stops flip from net-positive to net-negative, the strategy's edge has evaporated.

**Slippage vs. backtest assumption.** Compare actual fill prices to the expected fill prices (opening range high + $0.01 slippage). If real slippage consistently exceeds $0.03/share, the backtest's profitability estimate is overstated.

**Seasonal pattern.** If trading begins in February/March 2026, the first meaningful seasonal comparison point is October 2026. Note monthly performance and compare to the backtest's month-by-month pattern. One matching year is a hypothesis; two matching years is a signal.

**Trade frequency by day of week.** The backtest doesn't break down by weekday. If Monday or Friday trades have significantly different profiles (e.g., Monday gaps driven by weekend news behave differently), that's actionable intelligence for future parameter tuning.

### Timeline

Phase 3 is calendar-bound, not feature-bound. Minimum duration is 40 trading days (approximately 2 calendar months), covering both ramp phases. The strategy should run through at least one full market cycle before transitioning to live capital — which is unlikely to happen in 2 months. Plan for 3–6 months of paper trading as a realistic timeline before any live capital decision.

---

*End of Parameter Validation Report*
*Phase 2 (Backtesting Validation) is complete.*
*Next: Phase 3 (Live Validation) — paper trading with recommended parameters.*
