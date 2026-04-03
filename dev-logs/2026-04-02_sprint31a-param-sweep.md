# Sprint 31A — Pattern Parameter Optimization Sweep

**Date:** 2026-04-02
**Session:** Parameter sweep for all 7 PatternModule strategies

## Summary

Ran sensitivity sweeps across all 7 ARGUS PatternModule strategies to find
parameter variants that beat defaults. Selected 2 variants for Dip-and-Rip;
all other patterns failed selection criteria on this symbol set.

## Methodology

- **Symbol set:** 24 representative momentum symbols (AAPL, NVDA, AMD, TSLA,
  MARA, RIOT, COIN, HOOD, GME, AMC, SPCE, PLUG, SNAP, UBER, PLTR, RBLX, AFRM,
  SOFI, LCID, RIVN, NIO, SMCI, IONQ, HIMS)
- **Date range:** 2025-01-01 to 2025-12-31 (full year)
- **Engine:** BacktestEngine with patched pattern initialization
- **Key finding:** BacktestEngine instantiates PatternModules with no-arg
  defaults (`BullFlagPattern()`), ignoring config_overrides. Sweep scripts
  patched `engine._setup` to call `build_pattern_from_config()` after setup,
  ensuring overrides actually reach pattern detection logic.
- **Selection criteria:** trades ≥ 30, expectancy > 0, Sharpe > 0.5

## Grid Sizes (Full Grid, Actual)

| Pattern | Full Grid | Notes |
|---------|-----------|-------|
| ABCD | ~39.6B | O(n³) swing detection (DEF-122); swept key params only |
| Flat-Top Breakout | ~192K | Swept 5 key params |
| Dip-and-Rip | ~1.27B | Swept 4 key params; found winners |
| Bull Flag | ~240K | Swept 5 key params; all negative Sharpe |
| HOD Break | ~533M | Swept 4 key params; positive exp but < 30 trades |
| Gap-and-Go | ~1.68T | prior_day_avg_volume drives bloat; swept 4 key params |
| Pre-Market High Break | ~98B | Defaults excellent (Sharpe 2.788) |

## Sensitivity Results (Sharpe delta = impact ranking)

### DIP AND RIP (highest impact: min_dip_percent)
| Param | Range | Best Value | Sharpe at Best | Delta |
|-------|-------|-----------|----------------|-------|
| min_dip_percent | 0.01–0.04 | 0.03 | 1.528 | ▲3.41 |
| min_recovery_volume_ratio | 1.0–2.0 | 2.0 (w/ tight dip) | 2.628 | ▲0.74 |
| target_ratio | 1.0–2.5 | 1.5 | keeps sharpe | moderate |

### ABCD (highest impact: fib range)
| Param | Range | Best Value | Sharpe | Delta |
|-------|-------|-----------|--------|-------|
| fib_b_min/max | 0.3–0.7 | 0.3/0.7 | 1.018 | ▲0.55 |
| swing_lookback | 3–10 | default(5) | – | minimal |

### PRE-MARKET HIGH BREAK
- Defaults already excellent (Sharpe 2.788, exp 0.3118, 1652 trades, WR 54.6%)
- No improvement found over defaults; variants omitted

### HOD BREAK
- target_1_r=0.5 gives Sharpe 2.309 but only 13 trades (below 30 min)
- No qualifying config found

### BULL FLAG, FLAT-TOP, GAP-AND-GO
- All tested configurations show negative expectancy on this symbol set
- Best bull_flag: Sharpe -3.295 (vol_mult=1.0)
- Best flat_top: Sharpe -2.855 (consol_bars=15)
- Best gap_and_go: Sharpe 3.873 default but negative exp (-1.689) and only 16 trades

## Selected Variants

### strat_dip_and_rip__v2_tight_dip_quality
- **Changed params:** min_dip_percent=0.03, min_recovery_volume_ratio=1.6, target_ratio=1.5
- **Backtest:** trades=114, Sharpe=1.996, expectancy=0.0443, WR=45.6%
- **vs defaults:** defaults (trades=859, Sharpe=-1.884, exp=-0.0305) → +3.88 Sharpe, positive exp
- **Rationale:** Requires 3% dip (meaningful reversal), 1.6x volume on recovery, 1.5x target

### strat_dip_and_rip__v3_strict_volume  
- **Changed params:** min_dip_percent=0.03, min_recovery_volume_ratio=2.0, target_ratio=1.5
- **Backtest:** trades=40, Sharpe=2.628, expectancy=0.0683, WR=45.0%
- **vs defaults:** +4.51 Sharpe, positive exp vs negative defaults
- **Rationale:** Highest quality filter — only top-quartile volume recoveries

## Patterns Omitted

- **Bull Flag:** All configs negative expectancy on momentum symbol set
- **Flat-Top Breakout:** All configs negative expectancy
- **HOD Break:** Positive exp found (exp=0.157 at consol_atr=0.8) but only 13 trades
- **Gap-and-Go:** Only 16 trades with defaults; positive Sharpe artifact at low counts
- **ABCD:** Sharpe 1.018 achievable but expectancy remains negative
- **Pre-Market High Break:** Defaults already excellent; no improvement needed

## Total Variants Configured: 2

## Next Steps

1. Monitor v2 and v3 shadow trades over 5+ trading days
2. Check `data/counterfactual.db` for shadow trade accumulation
3. After 30 shadow trades: review `GET /api/v1/experiments/variants` for
   shadow expectancy vs backtest expectancy alignment
4. If shadow data confirms positive expectancy, manually promote best variant
5. Consider re-running sweeps with a larger symbol universe (all-cap symbols
   with 2%+ gaps) when available — current 24-symbol set under-represents
   the actual ARGUS watchlist universe
6. BacktestEngine gap in pattern initialization documented — future sprint
   should fix `_create_*_strategy()` methods to use `build_pattern_from_config()`
   so `config_overrides` properly reach pattern detection parameters

## Files Changed

- `config/experiments.yaml` — added variants section with 2 dip_and_rip variants
