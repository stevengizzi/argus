# ARGUS - Historical Data Inventory

> *Auto-generated after running the data fetcher. Update by re-running.*
> *Last updated: February 17, 2026*

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
| Financials | PYPL, JPM, GS |
| Industrials | BA, UBER, DIS, XOM |
| Semiconductors | INTC, MU |

## Date Range

- **Start:** March 1, 2023
- **End:** January 31, 2026
- **Months covered:** 35 (2023-03 through 2026-01)

## Summary Statistics

| Metric | Value |
|--------|-------|
| Total files | 1,015 |
| Total bars | 6,993,222 |
| Symbols with data | 29 |
| Disk usage | ~175 MB |
| Avg bars per symbol-month | ~6,890 |

## Data Quality

### Known Issues

**1. Missing Trading Day: March 10, 2025**
- Affects: All 29 symbols
- Cause: IEX feed gap for this date
- Impact: Minor (~390 bars per symbol missing)

**2. Market Holidays Flagged as "Missing"**
- The data validator flags market holidays as missing days because it uses a simple weekday check without a holiday calendar.
- These are NOT actual data quality issues. Affected dates include:
  - Good Friday (2023-04-07, 2024-03-29)
  - Memorial Day (2023-05-29, 2024-05-27)
  - Juneteenth (2023-06-19, 2024-06-19)
  - Independence Day (2023-07-04, 2024-07-04)
  - Labor Day (2023-09-04, 2024-09-02)
  - Thanksgiving (2023-11-23, 2024-11-28)
  - Christmas (2023-12-25, 2024-12-25)
  - New Year's Day (2024-01-01)
  - MLK Day (2024-01-15)
  - Presidents Day (2024-02-19)
  - National Day of Mourning for President Carter (2025-01-09)

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
    │   ├── AAPL_2023-03.parquet
    │   ├── AAPL_2023-04.parquet
    │   └── ... (35 files)
    ├── AMD/
    │   └── ...
    └── [27 more symbol directories]
```

## Re-downloading Data

To re-download all data (e.g., after fixing issues):
```bash
python -m argus.backtest.data_fetcher --start 2023-03-01 --end 2026-02-01 --force
```

To download a specific symbol:
```bash
python -m argus.backtest.data_fetcher --symbols AAPL --start 2023-03-01 --end 2026-02-01
```
