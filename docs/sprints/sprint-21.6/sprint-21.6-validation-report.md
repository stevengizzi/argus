# Sprint 21.6 Human Step — Validation Report

**Date:** 2026-03-23
**Date Range:** 2023-04-01 to 2025-03-01 (23 months)
**Data Source:** Databento EQUS.MINI OHLCV-1m
**Symbols:** 28/29 (ARM unavailable pre-IPO)
**Cache:** 672 Parquet files in `data/databento_cache/`

## Results Summary

| Strategy | Status | OOS Trades | Walk-Forward |
|---|---|---|---|
| ORB Breakout | ZERO_TRADES | 0 | Yes (9 windows) |
| ORB Scalp | ZERO_TRADES | 0 | Yes (9 windows) |
| VWAP Reclaim | ZERO_TRADES | 0 | Yes (9 windows) |
| Afternoon Momentum | ZERO_TRADES | 0 | Yes (9 windows) |
| Red-to-Green | ZERO_TRADES | 0 | No (BacktestEngine-only) |
| Bull Flag | ZERO_TRADES | 0 | No (BacktestEngine-only) |
| Flat-Top Breakout | ZERO_TRADES | 0 | No (BacktestEngine-only) |

## Escalation Triggers

- **TRIGGERED:** 7/7 strategies ZERO_TRADES (threshold: >3)
- **TRIGGERED:** All WFE = 0.0 (threshold: WFE < 0.1)
- **N/A:** 0/7 DIVERGENT (threshold: >3)

## Root Cause

**BacktestEngine OOS path lacks position sizing.**

Since Sprint 24, all strategies emit `share_count=0`, expecting `main.py:_process_signal()` quality pipeline to fill it. The BacktestEngine's `_on_candle_event()` passes signals directly to the Risk Manager without sizing, resulting in immediate rejection.

VectorBT IS sweeps work correctly:
- ORB: 322 trades across 26 symbols (confirms data quality)
- Other strategies: 0 IS trades (strategy-specific filter thresholds)

## Issues for Session 4

1. **BacktestEngine position sizing gap** — `engine.py:_on_candle_event()` needs position sizing before Risk Manager evaluation. Either inline legacy sizing (`allocated_capital * max_loss / risk`) or wire the quality pipeline into BacktestEngine.

2. **VectorBT file naming mismatch** — VectorBT expects `{SYMBOL}/{SYMBOL}_{YYYY-MM}.parquet`, HistoricalDataFeed writes `{SYMBOL}/{YYYY-MM}.parquet`. Worked around with symlinks; needs permanent fix.

3. **WalkForwardConfig.symbols=None** — BacktestEngine OOS gets no symbols when auto-detect is used. VectorBT handles this (scans dirs), BacktestEngine doesn't.

4. **EQUS.MINI start date** — Dataset available from 2023-03-28, not 2023-03-01. Adjusted start to 2023-04-01.

5. **ARM unavailable** in EQUS.MINI for pre-IPO months. 28/29 symbols cached successfully.

## Data Infrastructure (Working)

- 28 symbols x 24 months = 672 Parquet files cached
- Download time: ~68 minutes (zero-cost via DEC-353 validation)
- Symlinks created for VectorBT compatibility
- HistoricalDataFeed + `normalize_databento_df()` verified
- JSON result files stored locally at `data/backtest_runs/validation/*.json` (7 files, gitignored)
