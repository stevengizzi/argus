# ARGUS - Historical Data Inventory

> *Auto-generated after running the data fetcher. Update by re-running.*
> *Last updated: February 16, 2026*

## Data Source

- **Provider:** Alpaca Markets (free tier)
- **Feed:** IEX
- **Adjustment:** Split-adjusted
- **Timeframe:** 1-minute bars
- **Storage format:** Parquet (one file per symbol per month)
- **Timezone:** UTC

## Symbol Universe

29 symbols from `config/backtest_universe.yaml`:

| Category | Symbols |
|----------|---------|
| Index ETF | SPY |
| Mega-cap Tech | AAPL, MSFT, NVDA, META, AMZN, GOOG |
| High-beta Tech | TSLA, AMD, NFLX, PLTR, COIN, ARM |
| Momentum | SOFI, MARA, RIOT, SNAP, ROKU, SHOP, SMCI |
| Financials | SQ*, JPM, GS |
| Industrials | BA, UBER, DIS, XOM |
| Semiconductors | INTC, MU |

*\*SQ has no IEX data coverage - consider replacement*

## Date Range

- **Start:** March 1, 2025
- **End:** January 31, 2026
- **Months covered:** 11 (2025-03 through 2026-01)

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total files | 308 |
| Total bars | 2,231,905 |
| Symbols with data | 28 (SQ excluded) |
| Disk usage | 52 MB |
| Avg bars per symbol-month | ~7,200 |

## Data Quality

### Known Issues

**1. Missing Trading Day: March 10, 2025**
- Affects: 28 symbols (all except SQ)
- Cause: IEX feed gap for this date
- Impact: Minor (~390 bars per symbol missing)

**2. No Data: SQ (Block Inc.)**
- Affects: All 11 months (2025-03 through 2026-01)
- Cause: IEX feed does not cover this ticker
- Impact: SQ cannot be backtested with current data
- Recommendation: Replace with PYPL or V in `config/backtest_universe.yaml`

### Validation Checks Performed

For each Parquet file, the validator checks:
1. File exists and is readable
2. Contains required columns (timestamp, open, high, low, close, volume)
3. Timestamps are UTC-aware
4. No duplicate timestamps
5. OHLC consistency (high >= open, high >= close, low <= open, low <= close)
6. No zero-volume bars during market hours (warning only)
7. Expected trading days present

## File Structure

```
data/historical/
├── manifest.json          # Download tracking and metadata
└── 1m/
    ├── AAPL/
    │   ├── AAPL_2025-03.parquet
    │   ├── AAPL_2025-04.parquet
    │   └── ...
    ├── AMD/
    │   └── ...
    └── [27 more symbol directories]
```

## Re-downloading Data

To re-download all data (e.g., after fixing issues):
```bash
python -m argus.backtest.data_fetcher --start 2025-03-01 --end 2026-02-01 --force
```

To download a specific symbol:
```bash
python -m argus.backtest.data_fetcher --symbols AAPL --start 2025-03-01 --end 2026-02-01
```
