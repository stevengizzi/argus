# Sprint 8 — VectorBT Parameter Sweeps — Implementation Spec

> **Version:** 1.0 | **Date:** February 16, 2026
> **Pre-requisites:** Sprint 7 complete (473 tests), DEF-008 resolved (timezone fix + trade logging fix, 488 tests)
> **Starting test count:** 488 | **Target test count:** ~505–510

---

## Goal

Build fast parameter exploration tooling using vectorized operations. This is an approximation of the production ORB strategy — intentionally simplified — to test thousands of parameter combinations in minutes and identify which parameters are sensitive vs stable.

This is the VectorBT layer of the two-layer backtest toolkit. It does NOT replace the Replay Harness; it complements it. VectorBT answers "which parameters matter most?" while the Replay Harness answers "how does the actual system perform with those parameters?"

---

## Context from Gate Check

The 7-month Replay Harness run (June–December 2025) with default parameters produced only 5 trades. Root cause: `max_range_atr_ratio=2.0` rejects 98.5% of opening ranges (1,099 "Range too wide" out of ~1,116 attempts). Relaxing to 5.0 produced 59 trades.

This confirms `max_range_atr_ratio` is the single most impactful parameter and MUST be included in the sweep. The original sprint plan had 5 parameters; we now have 6.

---

## Micro-Decisions (Locked)

| ID | Decision | Rationale |
|----|----------|-----------|
| MD-8-1 | Open-source `vectorbt` from PyPI. NumPy/Pandas fallback if compatibility issues. (DEC-057) | VectorBT Pro unnecessary. ORB logic simple enough for pure NumPy if needed. |
| MD-8-2 | Pre-compute qualifying days via gap scan (prev close → day open). `min_gap_pct` is a swept parameter. (DEC-058) | Mirrors ScannerSimulator. Avoids evaluating combos on non-qualifying days. |
| MD-8-3 | Per-symbol sweeps, then aggregate. (DEC-059) | Isolates strategy logic from portfolio construction. |
| MD-8-4 | Dual visualization: matplotlib+seaborn (PNG) and plotly (interactive HTML). (DEC-060) | Static for docs/git, interactive for exploration and Sprint 9 reuse. |

---

## Parameter Grid

| Parameter | Config Key | Values | Count | Notes |
|-----------|-----------|--------|-------|-------|
| Opening range duration | `opening_range_minutes` | 5, 10, 15, 20, 30 | 5 | How many minutes to accumulate for the opening range |
| Profit target | `profit_target_r` | 1.0, 1.5, 2.0, 2.5, 3.0 | 5 | Take-profit as multiple of risk (R) |
| Stop buffer | `stop_buffer_pct` | 0.0, 0.1, 0.2, 0.5 | 4 | Additional % buffer below OR low for stop placement |
| Max hold time | `max_hold_minutes` | 15, 30, 45, 60, 90, 120 | 6 | Time stop — max minutes before forced exit |
| Min gap filter | `min_gap_pct` | 1.0, 1.5, 2.0, 3.0, 5.0 | 5 | Scanner pre-filter: minimum overnight gap % |
| Max OR range / ATR | `max_range_atr_ratio` | 2.0, 3.0, 4.0, 5.0, 8.0, 999.0 | 6 | Max opening range width as ATR(14) multiple. 999.0 = disabled. |

**Total combinations: 5 × 5 × 4 × 6 × 5 × 6 = 18,000 per symbol**

With 28 symbols: 504,000 total evaluations. Vectorized operations handle this in seconds to minutes per symbol.

---

## Simplified ORB Logic for VectorBT

The VectorBT implementation is intentionally simplified compared to production. The goal is parameter sensitivity, not exact replication.

**Included (affects parameter sensitivity):**
- Opening range high/low over configurable window
- Breakout detection: close > OR high
- Entry at breakout bar's close price
- Stop at OR low minus stop_buffer_pct
- Target at entry + profit_target_r × risk (where risk = entry - stop)
- Time stop at max_hold_minutes after entry
- EOD flatten at 15:45 ET
- Gap filter (pre-filter qualifying days)
- OR range / ATR filter (pre-filter qualifying opening ranges)
- ATR(14) computation (needed for OR range filter)
- One trade per symbol per day maximum

**Excluded (production features not relevant to parameter sensitivity):**
- VWAP confirmation (adds complexity, would need separate indicator computation)
- Volume > 1.5x filter (synthetic data doesn't have meaningful volume patterns for this)
- Multi-target exit (T1/T2 split) — single target only
- Stop-to-breakeven after T1
- Risk Manager gating (position sizing, daily loss limits)
- Slippage (VectorBT results are pre-slippage; Replay Harness adds slippage)

**Why these exclusions are acceptable:** VectorBT answers "is a 15-minute opening range better than 10 minutes?" — the relative ranking of parameters doesn't change much with VWAP or volume filters. The Replay Harness (which includes everything) is the validation layer for absolute performance numbers.

---

## Implementation

### File: `argus/backtest/vectorbt_orb.py`

```python
"""VectorBT ORB parameter sweep implementation.

Vectorized approximation of the ORB Breakout strategy for fast parameter
exploration. Intentionally simplified — see Sprint 8 spec for what's
included vs excluded and why.

Usage:
    python -m argus.backtest.vectorbt_orb \
        --data-dir data/historical/1m \
        --symbols TSLA,NVDA,AAPL \
        --start 2025-06-01 --end 2025-12-31 \
        --output-dir data/backtest_runs/sweeps
"""
```

### Data Structures

```python
from dataclasses import dataclass, field
from pathlib import Path
from datetime import date

@dataclass
class SweepConfig:
    """Configuration for a VectorBT parameter sweep."""
    data_dir: Path
    symbols: list[str]          # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (defaults match the grid above)
    or_minutes_list: list[int] = field(default_factory=lambda: [5, 10, 15, 20, 30])
    target_r_list: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 2.5, 3.0])
    stop_buffer_list: list[float] = field(default_factory=lambda: [0.0, 0.1, 0.2, 0.5])
    max_hold_list: list[int] = field(default_factory=lambda: [15, 30, 45, 60, 90, 120])
    min_gap_list: list[float] = field(default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 5.0])
    max_range_atr_list: list[float] = field(
        default_factory=lambda: [2.0, 3.0, 4.0, 5.0, 8.0, 999.0]
    )

@dataclass
class SweepResult:
    """Results from a single parameter combination on a single symbol."""
    symbol: str
    or_minutes: int
    target_r: float
    stop_buffer_pct: float
    max_hold_minutes: int
    min_gap_pct: float
    max_range_atr_ratio: float

    # Metrics
    total_trades: int
    win_rate: float             # 0.0-1.0
    total_return_pct: float     # Net return as % of initial capital
    avg_r_multiple: float       # Average R per trade
    max_drawdown_pct: float     # Peak-to-trough as % of equity
    sharpe_ratio: float         # Annualized
    profit_factor: float        # Gross profit / gross loss
    avg_hold_minutes: float     # Average trade duration
    qualifying_days: int        # Days that passed gap + range filter
```

### Core Functions

**1. `load_symbol_data(data_dir, symbol, start_date, end_date) -> pd.DataFrame`**

Load 1-minute Parquet files for a symbol. Add columns: `trading_day` (date), `minutes_from_open` (int, 0 = 9:30 AM ET), `bar_number_in_day` (int, 0-indexed per day). Convert timestamps to ET.

Return columns: `timestamp`, `open`, `high`, `low`, `close`, `volume`, `trading_day`, `minutes_from_open`, `bar_number_in_day`.

**2. `compute_atr(df, period=14) -> pd.Series`**

Standard ATR(14) computed on daily OHLC (aggregate 1m bars to daily first). Return a Series indexed by `trading_day`. Used by the OR range filter.

**3. `compute_qualifying_days(df, daily_atr, min_gap_pct, min_price=5.0, max_price=10000.0) -> set[date]`**

For each trading day:
- Compute gap_pct from previous day's close to current day's open
- Apply min_gap_pct filter
- Apply price range filter
- Return set of qualifying dates

Note: `min_gap_pct` is a swept parameter, so this function is called once per `min_gap_pct` value, not once per full parameter combination.

**4. `compute_opening_ranges(df, or_minutes) -> pd.DataFrame`**

For each trading day, compute:
- `or_high`: highest high in the first `or_minutes` minutes
- `or_low`: lowest low in the first `or_minutes` minutes
- `or_range`: `or_high - or_low`
- `or_complete_bar`: bar index where the OR window closes

Return one row per trading day. Like `min_gap_pct`, `or_minutes` produces a reusable intermediate result.

**5. `run_single_symbol_sweep(df, daily_atr, config) -> list[SweepResult]`**

The main sweep function. Strategy:

```
For each min_gap_pct:
    qualifying_days = compute_qualifying_days(df, daily_atr, min_gap_pct)
    
    For each or_minutes:
        opening_ranges = compute_opening_ranges(df_filtered, or_minutes)
        
        For each max_range_atr_ratio:
            Filter opening_ranges by range/ATR <= max_range_atr_ratio
            valid_days = qualifying_days ∩ range-filtered days
            
            For each (target_r, stop_buffer, max_hold):
                Vectorized entry/exit computation on valid_days:
                    entry = first bar after OR where close > or_high
                    stop = or_low * (1 - stop_buffer_pct)
                    target = entry + target_r * (entry - stop)
                    For each entry: scan forward bars for first of:
                        - low <= stop → exit at stop (loss)
                        - high >= target → exit at target (win)
                        - minutes_from_entry >= max_hold → exit at close (time stop)
                        - minutes_from_open >= 375 (15:45 ET) → exit at close (EOD)
                    Compute metrics from entry/exit arrays
                    Append SweepResult
```

**Optimization note:** The nested loop structure looks inefficient but the outer three loops (gap, OR minutes, range filter) produce reusable intermediates. The inner three loops (target, buffer, hold) are where vectorized operations evaluate all combinations at once for a given day's entry point. If using VectorBT, `Portfolio.from_orders()` can batch-evaluate these. If using pure NumPy, the inner loop is still fast because we're operating on pre-filtered day-level arrays.

**6. `run_sweep(config: SweepConfig) -> pd.DataFrame`**

Top-level orchestrator:
- Discover symbols (from config or by scanning data_dir)
- For each symbol: `load_symbol_data()` → `compute_atr()` → `run_single_symbol_sweep()`
- Collect all `SweepResult` objects into a DataFrame
- Save per-symbol results: `{output_dir}/{symbol}_sweep.parquet`
- Compute cross-symbol aggregation: `{output_dir}/sweep_summary.parquet`
- Return the summary DataFrame

**7. `generate_heatmaps(results_df, output_dir, symbol=None)`**

Generate 2D heatmaps for each pair of swept parameters, aggregating over remaining parameters.

Static (matplotlib + seaborn):
- `heatmap_{symbol}_{param1}_vs_{param2}.png` for per-symbol
- `heatmap_all_{param1}_vs_{param2}.png` for cross-symbol aggregate
- Primary metric: Sharpe ratio (color scale)
- Secondary metric: trade count (annotated in cells)

Interactive (plotly):
- `heatmap_{symbol}_{param1}_vs_{param2}.html`
- Hover shows all metrics for that cell
- Dropdown to switch between metrics (Sharpe, win rate, profit factor, trade count)

Default scope: Generate heatmaps for top-5 symbols by trade count plus the cross-symbol aggregate. CLI flag `--all-symbols` generates for all 28. This keeps default output manageable (6 × 15 pairs = 90 static + 90 interactive = 180 files) rather than 435 of each.

**8. CLI entry point**

```python
def main():
    parser = argparse.ArgumentParser(description="VectorBT ORB parameter sweep")
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--symbols", type=str, default="",
                        help="Comma-separated symbols. Empty = all in data-dir")
    parser.add_argument("--start", type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", type=str, required=True, help="YYYY-MM-DD")
    parser.add_argument("--output-dir", type=Path,
                        default=Path("data/backtest_runs/sweeps"))
    parser.add_argument("--all-symbols", action="store_true",
                        help="Generate heatmaps for all symbols (default: top 5)")
    # Optional overrides for parameter ranges (for testing or targeted sweeps)
    parser.add_argument("--or-minutes", type=str, default=None,
                        help="Override: comma-separated OR minute values")
    # ... similar for other parameters
    args = parser.parse_args()
    
    config = SweepConfig(
        data_dir=args.data_dir,
        symbols=args.symbols.split(",") if args.symbols else [],
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        output_dir=args.output_dir,
    )
    
    results = run_sweep(config)
    generate_heatmaps(results, config.output_dir, all_symbols=args.all_symbols)
    
    print(f"Sweep complete: {len(results)} combinations evaluated")
    print(f"Results saved to {config.output_dir}")

if __name__ == "__main__":
    main()
```

---

## VectorBT Integration Notes

**Primary approach:** Use `vectorbt` from PyPI.

The main VectorBT API we'd use is `vbt.Portfolio.from_signals()` or `vbt.Portfolio.from_orders()`, which take entry/exit arrays and compute returns and stats.

**Challenge:** VectorBT's `from_signals()` uses simple entry/exit boolean arrays. Our ORB logic needs conditional exits (stop vs target vs time stop vs EOD), which requires custom exit logic rather than a single exit signal. Two approaches:

**Approach A (preferred): Custom vectorized exit logic + VectorBT for stats only.**
Compute entry/exit prices and trade P&L ourselves using NumPy. Use VectorBT only for portfolio-level statistics, or just compute Sharpe/drawdown/profit factor from the P&L series directly. This gives us full control over the exit logic.

**Approach B: VectorBT's `from_order_func()` with custom callback.**
More VectorBT-idiomatic but requires learning VectorBT's callback API, which may have version-specific quirks.

**Recommendation: Approach A.** Compute entry/exit logic in pure NumPy, use VectorBT (or manual computation) only for portfolio-level statistics. This is more transparent, easier to test, and doesn't depend on VectorBT's internal mechanics. If VectorBT causes any installation or compatibility issues, we just compute Sharpe and drawdown ourselves (both are ~10 lines of NumPy each).

---

## Fallback: Pure NumPy/Pandas (No VectorBT)

If `vectorbt` fails to install or has compatibility issues:

```python
def compute_sharpe(daily_returns: pd.Series, risk_free_rate: float = 0.0) -> float:
    """Annualized Sharpe ratio from daily returns."""
    excess = daily_returns - risk_free_rate / 252
    if excess.std() == 0:
        return 0.0
    return float(excess.mean() / excess.std() * np.sqrt(252))

def compute_max_drawdown(equity_curve: pd.Series) -> float:
    """Maximum peak-to-trough drawdown as a fraction."""
    peak = equity_curve.cummax()
    drawdown = (equity_curve - peak) / peak
    return float(drawdown.min())

def compute_profit_factor(pnls: pd.Series) -> float:
    """Gross profit / gross loss. Infinity if no losses."""
    gross_profit = pnls[pnls > 0].sum()
    gross_loss = abs(pnls[pnls < 0].sum())
    if gross_loss == 0:
        return float('inf') if gross_profit > 0 else 0.0
    return float(gross_profit / gross_loss)
```

These already exist in `argus/backtest/metrics.py` (BacktestMetrics from Sprint 7). Reuse them directly if VectorBT is unavailable. Document the decision in the commit message.

---

## Tests

### File: `tests/backtest/test_vectorbt_orb.py`

Target: ~18-22 new tests.

**Data loading and preparation:**
```
test_load_symbol_data_correct_columns
    # Load test Parquet data, verify expected columns exist
    # Verify trading_day and minutes_from_open are computed correctly

test_load_symbol_data_et_conversion
    # Verify timestamps are converted to ET
    # First bar of each day should be 9:30 ET

test_load_symbol_data_date_range_filter
    # Load with start mid-month, verify no data before that date
```

**ATR computation:**
```
test_compute_atr_known_values
    # Create synthetic daily OHLC with known ATR
    # Verify computed ATR matches hand-calculated value

test_compute_atr_insufficient_data
    # Fewer than 14 trading days → ATR should handle gracefully
    # (NaN for first 13 days, valid from day 14+)
```

**Qualifying days:**
```
test_qualifying_days_gap_filter
    # Day with 3% gap, min_gap=2% → qualifies
    # Day with 1% gap, min_gap=2% → rejected

test_qualifying_days_price_filter
    # Stock at $3 with min_price=$5 → rejected
    # Stock at $50 with min_price=$5 → qualifies

test_qualifying_days_no_previous_close
    # First trading day has no prev close → excluded
```

**Opening range computation:**
```
test_opening_range_15min
    # Synthetic data with known high/low in first 15 minutes
    # Verify or_high, or_low, or_range match expected values

test_opening_range_5min_vs_30min
    # Same data, different OR windows → different ranges
    # 30-min range >= 5-min range (wider window captures more)
```

**Core sweep logic (single combination):**
```
test_breakout_entry_detection
    # Synthetic day: OR forms, next bar closes above OR high
    # Verify entry is detected at correct bar

test_stop_loss_exit
    # Entry at $100, stop at $98, next bar low hits $97.50
    # Verify exit at stop price, negative R-multiple

test_target_exit
    # Entry at $100, stop at $98, target at $104 (2R)
    # Subsequent bar high hits $104.50
    # Verify exit at target price, R-multiple ≈ 2.0

test_time_stop_exit
    # Entry at $100, max_hold=30 min, no stop/target hit
    # Verify exit at close of bar 30 minutes after entry

test_eod_flatten_exit
    # Entry at $100, no stop/target hit, position open at 15:45
    # Verify exit at 15:45 bar close

test_no_entry_when_no_breakout
    # OR forms, but no subsequent bar closes above OR high
    # Verify zero trades for the day

test_one_trade_per_day_max
    # Breakout detected, trade exits at stop, another breakout later
    # Verify only the first trade counts

test_or_range_atr_filter
    # OR range = 3.0 * ATR, max_range_atr_ratio = 2.0 → filtered out
    # OR range = 1.5 * ATR, max_range_atr_ratio = 2.0 → passes
```

**Full sweep integration:**
```
test_sweep_result_count
    # 1 symbol, small parameter grid (2×2×1×1×1×1 = 4 combos)
    # Verify 4 results total

test_sweep_output_columns
    # Run small sweep, verify SweepResult has all expected fields

test_sweep_results_deterministic
    # Run same sweep twice → identical results
```

**Heatmap generation:**
```
test_heatmap_png_created
    # Run sweep → call generate_heatmaps → PNG files exist in static/

test_heatmap_html_created
    # Run sweep → call generate_heatmaps → HTML files exist in interactive/

test_heatmap_no_trades_handles_gracefully
    # Parameter combo with zero trades → heatmap cell shows 0/NaN, no crash
```

**CLI:**
```
test_cli_runs_without_error
    # Call main() with small synthetic dataset and minimal params
    # Verify no exceptions, output files created
```

### Test Data

Create synthetic Parquet data in `tests/backtest/conftest.py` (extend existing fixtures). The synthetic data should include:
- At least 20 trading days (to have valid ATR after 14-day warmup)
- Known gap percentages (some qualifying, some not)
- Known opening range patterns (some with breakouts, some without)
- Known price paths that hit stops, targets, and time stops

This synthetic data is deterministic — the expected results for each test can be hand-computed.

---

## Output Structure

```
data/backtest_runs/sweeps/
├── AAPL_sweep.parquet          # Per-symbol: all 18,000 combinations
├── TSLA_sweep.parquet
├── ...
├── sweep_summary.parquet       # Cross-symbol aggregation
├── static/                     # matplotlib + seaborn PNGs
│   ├── heatmap_TSLA_or_minutes_vs_target_r.png
│   ├── heatmap_TSLA_or_minutes_vs_max_range_atr.png
│   ├── ...
│   ├── heatmap_ALL_or_minutes_vs_target_r.png
│   └── ...
└── interactive/                # plotly HTML files
    ├── heatmap_TSLA_or_minutes_vs_target_r.html
    ├── ...
    └── heatmap_ALL_or_minutes_vs_target_r.html
```

---

## Dependencies

**New packages to install:**

```
vectorbt          # Primary. pip install vectorbt --break-system-packages
matplotlib        # For static heatmaps (may already be installed)
seaborn           # For static heatmap styling
plotly            # For interactive HTML heatmaps
```

If `vectorbt` installation fails, proceed with pure NumPy/Pandas approach using metrics from `argus/backtest/metrics.py`. Document the fallback in the commit message.

---

## Definition of Done

1. `argus/backtest/vectorbt_orb.py` implements all 8 functions described above
2. CLI works: `python -m argus.backtest.vectorbt_orb --data-dir data/historical/1m --symbols TSLA --start 2025-06-01 --end 2025-12-31 --output-dir data/backtest_runs/sweeps`
3. Per-symbol Parquet results saved with all SweepResult fields
4. Cross-symbol summary Parquet saved
5. Static PNG heatmaps generated (at minimum: aggregate heatmaps for all 15 parameter pairs)
6. Interactive HTML heatmaps generated (same scope as static)
7. ~18-22 new tests passing
8. All existing tests still pass (488 + new ≈ 506-510 total)
9. No changes to production strategy code — this is a standalone analysis tool

---

## What NOT To Build

- **No changes to OrbBreakout strategy** — the vectorized version is separate
- **No VWAP or volume confirmation** — not needed for parameter sensitivity
- **No multi-target exits** — single target only
- **No risk manager integration** — unlimited capital for sweep purposes
- **No slippage** — Replay Harness handles slippage for validation
- **No walk-forward in this sprint** — that's Sprint 9
- **No report generation** — that's Sprint 9/10

---

*End of Sprint 8 Implementation Spec*
