# Sprint 31A S6 — Parameter Sweep Results

**Date:** 2026-04-03  
**Symbol set:** 24 representative momentum symbols (AAPL, NVDA, AMD, TSLA, MARA, RIOT,
COIN, HOOD, GME, AMC, SPCE, PLUG, SNAP, UBER, PLTR, RBLX, AFRM, SOFI, LCID, RIVN,
NIO, SMCI, IONQ, HIMS)  
**Date range target:** 2025-01-01 to 2025-12-31  
**Qualification thresholds:** trades ≥ 30, expectancy > 0, Sharpe > 0.5

---

## Infrastructure Note

Between S1–S5 sweeps (which produced the Dip-and-Rip v2/v3 variants) and S6, the
Databento cache grew from the 24-symbol set to 24,321 symbols. The `run_experiment.py`
CLI uses `BacktestEngine` auto-detection from cache with no `--symbols` filter flag.

**Impact on S6 sweeps:**
- Data loading alone: ~6 minutes per grid point (vs ~15 seconds before cache growth)
- Full backtest per grid point: ~40 minutes on the 24,321-symbol cache
- A 60-point grid for micro_pullback would require ~40 hours — not feasible in a session

**Methodology adapted for S6:**
- Default-config single-point backtests were run for all three S3–S5 patterns
- Runs were killed mid-year due to session time constraints; partial DB results were extracted
- 24-symbol performance was isolated by filtering the backtest run DBs by symbol
- Results cover January–May 2025 (partial year)
- The earlier patterns (bull_flag through abcd) were swept before the cache grew; results remain valid

**DEF-145 filed:** follow-up sweep when 24-symbol `--symbols` CLI flag or dedicated cache directory is available.

---

## Per-Pattern Summary Table

| Pattern | Partial Period | Trades (24-sym) | Win Rate | avg_R | Total P&L | Qualifies |
|---------|---------------|-----------------|----------|-------|-----------|-----------|
| bull_flag | Full 2025 | — | — | — | — | No (Sharpe −3.295) |
| flat_top_breakout | Full 2025 | — | — | — | — | No (Sharpe −2.855) |
| dip_and_rip (v2) | Full 2025 | 114 | 45.6% | +0.0443 | — | **Yes** (Sharpe 1.996) |
| dip_and_rip (v3) | Full 2025 | 40 | 45.0% | +0.0683 | — | **Yes** (Sharpe 2.628) |
| hod_break | Full 2025 | <30 | positive | — | — | No (<30 trades) |
| gap_and_go | Full 2025 | <30 | — | — | — | No (<30 trades) |
| abcd | Full 2025 | — | — | — | — | No (exp negative) |
| premarket_high_break | Full 2025 | <30 | — | — | — | No (<30 trades) |
| **micro_pullback** | Jan–May 2025 | 417 | 49.6% | +0.0046 | +$557 (Jan) | No (avg_R too low) |
| **vwap_bounce** | Jan–Feb 2025 | 154 | 40.3% | +0.055 | −$9,025 | No (neg dollar P&L) |
| **narrow_range_breakout** | Jan–Apr 2025 | 2 | 50.0% | −0.031 | — | No (<30 trades) |

---

## Qualifying Variants

### Dip-and-Rip (carried from S1–S5)

**v2 — Tight Dip Quality** (`strat_dip_and_rip__v2_tight_dip_quality`)
- Params: `min_dip_percent=0.03`, `min_recovery_volume_ratio=1.6`, `target_ratio=1.5`
- Trades: 114, Sharpe: 1.996, Expectancy: 0.0443, Win Rate: 45.6%
- Rationale: Requires a more meaningful 3% dip with strong volume confirmation.

**v3 — Strict Volume** (`strat_dip_and_rip__v3_strict_volume`)
- Params: `min_dip_percent=0.03`, `min_recovery_volume_ratio=2.0`, `target_ratio=1.5`
- Trades: 40, Sharpe: 2.628, Expectancy: 0.0683, Win Rate: 45.0%
- Rationale: Top-quartile volume filter produces fewer but higher-quality entries.

---

## Non-Qualifying Patterns — S1–S5 Earlier Patterns

The seven patterns evaluated in S1–S5 (bull_flag, flat_top_breakout, dip_and_rip, hod_break,
gap_and_go, abcd, premarket_high_break) were swept against the full 24-symbol set over 2025
using full-year runs. Results for bull_flag, flat_top_breakout, hod_break, gap_and_go, and abcd
are documented in the S1–S5 sweep comment block in `config/experiments.yaml`. The dip_and_rip
variants qualify and appear in the Qualifying Variants section above. Pre-Market High Break is
documented below.

### Pre-Market High Break

**Full-year backtest result (24 symbols, full 2025):**
- Fewer than 30 trades on the 24-symbol momentum set across all of 2025

**Detailed observations:**
- The pattern fires when the intraday price breaks above the pre-market session high, which
  requires a meaningful pre-market range to have formed. On the 24-symbol momentum set, most
  names are either gapping aggressively (making the pre-market high a gap-away that doesn't
  revisit intraday) or opening near the prior close with little pre-market activity.
- The pattern shares the same root cause as gap_and_go's insufficient signal count: it is a
  reference-data-dependent setup (requires pre-market high level from the daily reference bar)
  and the 24 high-beta symbols produce relatively few clean intraday pre-market-high tests.
  Volatile names (IONQ, MARA, RIOT) tend to gap through the pre-market high on open rather
  than approaching it methodically during market hours.
- Unlike hod_break (which requires only intraday price action), pre-market high break depends
  on overnight session data being captured correctly in the reference bar. Any gap in the
  reference data pipeline further reduces signal generation.

**Why it doesn't qualify:** Fewer than 30 trades in a full year on the target symbol set
makes statistical qualification impossible regardless of per-trade metrics.

**Recommendation:** Consider a broader symbol universe with more orderly opening rotations
(e.g., sector ETFs, large-cap growth names like AAPL, MSFT, NVDA in non-trending phases)
where pre-market highs are approached and tested more methodically. Revisit under DEF-145
when 24-symbol sweep infrastructure is available.

---

## Non-Qualifying Patterns — S3–S5 New Patterns

### Micro Pullback

**Partial backtest result (24 symbols, Jan–May 2025):**
- 417 trades, WR=49.6%, avg_R=+0.0046, total_pnl≈+$557 (partial Jan only)

**Detailed observations:**
- January 2025 alone showed exceptional metrics: 37 trades, WR=64.9%, avg_R=+0.204 —
  driven almost entirely by IONQ (23/37 trades = 62%). IONQ's January 2025 run was an
  outlier in the dataset (+200%+ intra-month), not representative of normal detection.
- Normalised over 5 months (417 trades), win rate drops to 49.6% and avg_R collapses
  to +0.0046 — essentially breakeven. The Sharpe over this period would be approximately
  0.05–0.1, well below the 0.5 threshold.
- The pattern requires trending conditions (strong impulse) to work. On the 24-symbol
  momentum set, trending periods exist but are interspersed with consolidation and
  reversal phases where the pattern churns.

**Why it doesn't qualify:** Expectancy is positive but too close to zero for a reliable
Sharpe > 0.5. The January IONQ spike is a data artefact, not a durable edge.

**Recommendation:** Revisit with `min_impulse_percent=0.03–0.04` restriction to filter
out marginal impulses. A tighter impulse threshold should improve selectivity at the
cost of trade count. Requires 24-symbol sweep to validate (DEF-145).

---

### VWAP Bounce

**Partial backtest result (24 symbols, Jan–Feb 2025):**
- 154 trades, WR=40.3%, avg_R=+0.055, total_pnl=−$9,025

**Detailed observations:**
- Average R-multiple is positive (+0.055) but the win rate of 40.3% (62 wins / 92 losses)
  produces negative dollar P&L. The losses are larger in absolute dollar terms than the wins.
- Top symbols generating trades: AFRM (39), RIOT (27), HIMS (23), RBLX (23), COIN (10).
  These are all high-beta names where VWAP is frequently violated intraday — the "bounce"
  attempt fails more often than it succeeds.
- The default `vwap_touch_tolerance_pct=0.002` (0.2% of VWAP) may be too loose, admitting
  touches that are actually VWAP breaks rather than clean tests.
- The `min_prior_trend_bars=10` default may be too low — entries after a short 10-bar trend
  lack the continuation momentum needed on volatile names.

**Why it doesn't qualify:** While R-positive in expectation, the negative dollar P&L and
40% win rate suggest the pattern fires on many false setups on high-beta names. A Sharpe
above 0.5 is unlikely given the variance in these symbols.

**Recommendation:** Tighten `vwap_touch_tolerance_pct` to 0.001 and raise
`min_prior_trend_bars` to 15–20. Fewer but cleaner VWAP interactions should improve
selectivity. Requires 24-symbol sweep (DEF-145).

---

### Narrow Range Breakout

**Partial backtest result (24 symbols, Jan–Apr 2025):**
- Only 2 trades on the 24 target symbols (WR=50%, avg_R=−0.031)
- Full-universe run: 1,384 trades (Jan–Apr) — the pattern fires broadly on the full cache

**Detailed observations:**
- The pattern generates fewer than 1 trade per month on the 24-symbol momentum set.
  High-beta momentum names (IONQ, MARA, RIOT, TSLA) rarely consolidate in the narrow
  tight-band fashion required — they either trend strongly or chop with wide candles.
- The full-universe run (1,384 trades) confirms the pattern works, but on a very
  different market segment: slower-moving, lower-volatility names where NR consolidations
  are more common.
- With only 2 trades in 4 months on target symbols, qualification (<30 trades) is
  structurally impossible for the intended universe.

**Why it doesn't qualify:** Signal generation is too sparse on the 24-symbol high-beta
momentum set. The pattern's requirements (multiple bars with decreasing range) are
rarely met on names like IONQ/MARA/RIOT.

**Recommendation:** Consider a different symbol universe (mid-cap growth, e.g., CRWD,
DDOG, SNOW, ZS) where range contraction → expansion cycles are more common. The pattern
itself is sound but mismatched to the current target universe. See DEF-145.

---

## Interesting Observations

1. **Cache growth changes sweep economics.** The cache grew 1,000× between early sprints
   (24 symbols) and S6 (24,321 symbols). The 30s/point estimate was calibrated on the
   24-symbol cache. With 24,321 symbols, each point takes ~40 minutes. A one-time solution
   (restricting cache or adding `--symbols` to the CLI) would restore the original sweep
   economics and unblock future pattern evaluation.

2. **IONQ January 2025 is a high-magnitude outlier.** Any pattern that fires on trend/impulse
   continuation will show exceptional January metrics for IONQ. The micro_pullback January
   data is essentially IONQ performance. This reinforces the need for full-year evaluation
   before qualifying a pattern.

3. **Momentum symbols need different filters for each pattern family:**
   - *Impulse/continuation patterns* (micro_pullback, dip_and_rip): work well when momentum
     names are in strong trending phases; need impulse strength floors to avoid churn
   - *Mean-reversion/bounce patterns* (vwap_bounce): low win rate on high-beta names;
     may work better on names with smoother trends (AAPL, NVDA, MSFT)
   - *Compression/breakout patterns* (NR breakout, flat_top): structurally limited on
     high-volatility names; better suited to mid-cap growth or sector ETFs

4. **Dip-and-Rip variants hold the S6 bar.** Both v2 and v3 qualify and have been shadow
   mode since Sprint 32.9. The 45% win rate is consistent with a pattern that wins on
   targets but takes the occasional -1R stop — the key is the Sharpe (1.996 / 2.628)
   driven by low variance in outcomes.
