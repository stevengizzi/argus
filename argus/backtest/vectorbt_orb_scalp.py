"""VectorBT ORB Scalp parameter sweep implementation.

Simplified variant of vectorbt_orb.py for the ORB Scalp strategy. Key differences:

1. **Parameter grid:** Only sweeps scalp_target_r and max_hold_bars
   - scalp_target_r_list: [0.2, 0.3, 0.4, 0.5]
   - max_hold_bars_list: [1, 2, 3, 5] (1m bars → 60s, 120s, 180s, 300s)
   - Fixed: or_minutes=5, min_gap_pct=2.0, stop_buffer_pct=0.0

2. **Single target exit:** Exit 100% at target. No T1/T2 split.

3. **Stop at OR midpoint:** (OR high + OR low) / 2

4. **Time stop in bars:** Exit at bar close if max_hold_bars reached.

Usage:
    python -m argus.backtest.vectorbt_orb_scalp \
        --data-dir data/historical/1m \
        --start 2023-03-01 --end 2026-01-31 \
        --output-dir data/backtest_runs/scalp_sweeps
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date
from itertools import product
from pathlib import Path
from typing import Any, TypedDict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

# Market hours constants (in minutes from midnight ET)
MARKET_OPEN_MINUTES = 9 * 60 + 30  # 9:30 AM ET = 570 minutes
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET = 945 minutes (minute 375 from open)


@dataclass
class ScalpSweepConfig:
    """Configuration for an ORB Scalp parameter sweep."""

    data_dir: Path
    symbols: list[str]  # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (only two parameters for scalp)
    scalp_target_r_list: list[float] = field(default_factory=lambda: [0.2, 0.3, 0.4, 0.5])
    max_hold_bars_list: list[int] = field(default_factory=lambda: [1, 2, 3, 5])

    # Fixed parameters (not swept)
    or_minutes: int = 5
    min_gap_pct: float = 2.0
    stop_buffer_pct: float = 0.0  # Stop at OR midpoint

    # Scanner filters
    min_price: float = 5.0
    max_price: float = 10000.0


@dataclass
class ScalpSweepResult:
    """Results from a single parameter combination on a single symbol."""

    symbol: str
    scalp_target_r: float
    max_hold_bars: int

    # Metrics
    total_trades: int
    win_rate: float  # 0.0-1.0
    total_return_pct: float  # Net return as % of initial capital
    avg_r_multiple: float  # Average R per trade
    max_drawdown_pct: float  # Peak-to-trough as % of equity
    sharpe_ratio: float  # Annualized
    profit_factor: float  # Gross profit / gross loss
    avg_hold_bars: float  # Average trade duration in bars
    qualifying_days: int  # Days that passed gap filter


class ScalpEntryInfo(TypedDict):
    """Pre-computed entry information for a single day."""

    entry_price: float
    entry_bar_idx: int  # Bar index of entry
    or_midpoint: float  # Stop price
    # NumPy arrays for post-entry bars
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    bar_indices: np.ndarray


def load_symbol_data(
    data_dir: Path,
    symbol: str,
    start_date: date,
    end_date: date,
) -> pd.DataFrame:
    """Load 1-minute Parquet files for a symbol.

    Adds derived columns:
    - trading_day: date
    - minutes_from_open: int (0 = 9:30 AM ET)
    - bar_number_in_day: int (0-indexed per day)

    Converts timestamps to ET.

    Args:
        data_dir: Directory containing Parquet files.
        symbol: Ticker symbol.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume,
        trading_day, minutes_from_open, bar_number_in_day.
        Empty DataFrame if no data found.
    """
    symbol_dir = data_dir / symbol.upper()
    if not symbol_dir.exists():
        logger.warning("No data directory for symbol %s", symbol)
        return pd.DataFrame()

    # Find all Parquet files for this symbol
    # Support both naming conventions:
    # - Legacy: {SYMBOL}_{YYYY-MM}.parquet (Alpaca-era data_fetcher)
    # - Current: {YYYY-MM}.parquet (HistoricalDataFeed / Databento cache)
    parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
    if not parquet_files:
        parquet_files = sorted(symbol_dir.glob("*.parquet"))
    if not parquet_files:
        logger.warning("No Parquet files found for symbol %s", symbol)
        return pd.DataFrame()

    # Load and concatenate all files
    dfs = []
    for f in parquet_files:
        try:
            df = pd.read_parquet(f)
            dfs.append(df)
        except Exception as e:
            logger.warning("Error reading %s: %s", f, e)

    if not dfs:
        return pd.DataFrame()

    df = pd.concat(dfs, ignore_index=True)

    # Ensure timestamp column exists and is datetime
    if "timestamp" not in df.columns:
        logger.warning("No timestamp column in data for %s", symbol)
        return pd.DataFrame()

    # Convert timestamps to ET
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    df["timestamp_et"] = df["timestamp"].dt.tz_convert(ET)

    # Filter by date range
    df["trading_day"] = df["timestamp_et"].dt.date
    df = df[(df["trading_day"] >= start_date) & (df["trading_day"] <= end_date)].copy()

    if df.empty:
        return pd.DataFrame()

    # Compute minutes from market open (9:30 AM ET)
    df["minutes_from_open"] = df["timestamp_et"].apply(
        lambda ts: (ts.hour * 60 + ts.minute) - MARKET_OPEN_MINUTES
    )

    # Filter to market hours only (9:30 AM - 4:00 PM ET, minutes 0-389)
    df = df[(df["minutes_from_open"] >= 0) & (df["minutes_from_open"] < 390)].copy()

    if df.empty:
        return pd.DataFrame()

    # Sort by timestamp
    df = df.sort_values("timestamp").reset_index(drop=True)

    # Compute bar number within each day
    df["bar_number_in_day"] = df.groupby("trading_day").cumcount()

    # Select and return columns
    result_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trading_day",
        "minutes_from_open",
        "bar_number_in_day",
    ]
    return df[result_cols].copy()


def compute_qualifying_days(
    df: pd.DataFrame,
    min_gap_pct: float,
    min_price: float = 5.0,
    max_price: float = 10000.0,
) -> set[date]:
    """Identify trading days that pass the gap and price filters.

    Args:
        df: DataFrame with trading_day, open, close columns.
        min_gap_pct: Minimum gap percentage (e.g., 2.0 for 2%).
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.

    Returns:
        Set of qualifying trading dates.
    """
    # Get daily open and close
    daily = (
        df.groupby("trading_day")
        .agg(
            {
                "open": "first",
                "close": "last",
            }
        )
        .reset_index()
    )

    if len(daily) < 2:
        return set()

    # Compute gap from previous day's close to current day's open
    daily["prev_close"] = daily["close"].shift(1)
    daily["gap_pct"] = ((daily["open"] - daily["prev_close"]) / daily["prev_close"]) * 100

    # Apply filters
    qualifying = daily[
        (daily["gap_pct"] >= min_gap_pct)
        & (daily["open"] >= min_price)
        & (daily["open"] <= max_price)
        & (~daily["prev_close"].isna())  # Must have previous close
    ]

    return set(qualifying["trading_day"].tolist())


def compute_opening_ranges(
    df: pd.DataFrame,
    or_minutes: int,
) -> pd.DataFrame:
    """Compute opening range (OR) for each trading day.

    Args:
        df: DataFrame with trading_day, minutes_from_open, high, low columns.
        or_minutes: Number of minutes for the opening range window.

    Returns:
        DataFrame with columns: trading_day, or_high, or_low, or_midpoint,
        or_complete_bar (bar index where OR window closes).
    """
    # Filter to opening range bars only
    or_bars = df[df["minutes_from_open"] < or_minutes].copy()

    if or_bars.empty:
        return pd.DataFrame(
            columns=["trading_day", "or_high", "or_low", "or_midpoint", "or_complete_bar"]
        )

    # Compute OR high/low per day
    or_agg = (
        or_bars.groupby("trading_day")
        .agg(
            or_high=("high", "max"),
            or_low=("low", "min"),
            or_complete_bar=("bar_number_in_day", "max"),
        )
        .reset_index()
    )

    # Scalp uses OR midpoint as stop
    or_agg["or_midpoint"] = (or_agg["or_high"] + or_agg["or_low"]) / 2

    return or_agg


def _find_scalp_exit_vectorized(
    post_entry_highs: np.ndarray,
    post_entry_lows: np.ndarray,
    post_entry_closes: np.ndarray,
    post_entry_bar_indices: np.ndarray,
    entry_price: float,
    entry_bar_idx: int,
    stop_price: float,
    target_price: float,
    max_hold_bars: int,
) -> dict[str, Any] | None:
    """Find exit using vectorized operations for scalp trades.

    Args:
        post_entry_highs: Array of high prices for bars after entry.
        post_entry_lows: Array of low prices for bars after entry.
        post_entry_closes: Array of close prices for bars after entry.
        post_entry_bar_indices: Array of bar indices for bars after entry.
        entry_price: The entry price.
        entry_bar_idx: The bar index of entry.
        stop_price: Stop loss price (OR midpoint).
        target_price: Target price.
        max_hold_bars: Maximum hold time in bars before time stop.

    Returns:
        Dict with trade details or None if no valid exit found.
    """
    n = len(post_entry_highs)
    if n == 0:
        return None

    # Compute bars held for each subsequent bar
    bars_held = post_entry_bar_indices - entry_bar_idx

    # Boolean masks for each exit condition
    stop_hit = post_entry_lows <= stop_price
    target_hit = post_entry_highs >= target_price
    hold_exceeded = bars_held >= max_hold_bars
    eod_hit = post_entry_bar_indices >= 375  # 3:45 PM ET (bar 375 from open)

    # Find first bar index for each condition (use n as "not found" sentinel)
    stop_idx = int(np.argmax(stop_hit)) if stop_hit.any() else n
    target_idx = int(np.argmax(target_hit)) if target_hit.any() else n
    hold_idx = int(np.argmax(hold_exceeded)) if hold_exceeded.any() else n
    eod_idx = int(np.argmax(eod_hit)) if eod_hit.any() else n

    # Earliest exit wins
    # Priority on same bar: stop > time_stop > target > eod (conservative for longs)
    exit_idx = min(stop_idx, target_idx, hold_idx, eod_idx)

    if exit_idx >= n:
        # Shouldn't happen with EOD check, but safety fallback
        exit_idx = n - 1
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == stop_idx and stop_hit[exit_idx]:
        # Stop takes priority on same bar
        reason = "stop"
        exit_price = stop_price
    elif exit_idx == hold_idx and hold_exceeded[exit_idx]:
        # Time stop - check if stop also hit on this bar
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "time_stop"
            exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == target_idx and target_hit[exit_idx]:
        # Check if stop also hit on same bar (stop wins)
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "target"
            exit_price = target_price
    elif exit_idx == eod_idx and eod_hit[exit_idx]:
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    else:
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])

    exit_bars = int(bars_held[exit_idx])
    risk = entry_price - stop_price
    pnl = exit_price - entry_price
    r_multiple = pnl / risk if risk > 0 else 0.0

    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "risk": risk,
        "pnl": pnl,
        "r_multiple": r_multiple,
        "hold_bars": exit_bars,
        "exit_reason": reason,
    }


def _precompute_scalp_entries_for_day(
    day_bars: pd.DataFrame,
    or_high: float,
    or_low: float,
    or_complete_bar: int,
    or_midpoint: float,
) -> ScalpEntryInfo | None:
    """Pre-compute entry information for a day.

    Entry: first bar that closes above OR high after OR completes.
    Stop: OR midpoint.

    Args:
        day_bars: DataFrame of bars for a single trading day.
        or_high: Opening range high.
        or_low: Opening range low.
        or_complete_bar: Bar index where OR completes.
        or_midpoint: OR midpoint (stop price).

    Returns:
        ScalpEntryInfo dict with entry details and NumPy arrays, or None if no entry.
    """
    # Bars after OR completes
    post_or_bars = day_bars[day_bars["bar_number_in_day"] > or_complete_bar]

    if post_or_bars.empty:
        return None

    # Look for breakout: first bar that closes above OR high
    breakout_mask = post_or_bars["close"] > or_high
    if not breakout_mask.any():
        return None

    # Entry on first breakout bar
    first_breakout_idx = breakout_mask.idxmax()
    entry_bar = post_or_bars.loc[first_breakout_idx]
    entry_price = float(entry_bar["close"])  # type: ignore[arg-type]
    entry_bar_idx = int(entry_bar["bar_number_in_day"])  # type: ignore[arg-type]

    # Verify risk is positive
    if entry_price <= or_midpoint:
        return None

    # Extract post-entry bars as NumPy arrays
    post_entry_bars = day_bars[day_bars["bar_number_in_day"] > entry_bar_idx]

    if post_entry_bars.empty:
        return None

    return ScalpEntryInfo(
        entry_price=entry_price,
        entry_bar_idx=entry_bar_idx,
        or_midpoint=or_midpoint,
        highs=post_entry_bars["high"].to_numpy(),
        lows=post_entry_bars["low"].to_numpy(),
        closes=post_entry_bars["close"].to_numpy(),
        bar_indices=post_entry_bars["bar_number_in_day"].to_numpy(),
    )


def run_single_symbol_sweep(
    df: pd.DataFrame,
    symbol: str,
    config: ScalpSweepConfig,
) -> list[ScalpSweepResult]:
    """Run parameter sweep for a single symbol.

    Args:
        df: DataFrame with all bar data for the symbol.
        symbol: Ticker symbol.
        config: Sweep configuration with parameter ranges.

    Returns:
        List of ScalpSweepResult objects (one per parameter combination).
    """
    results: list[ScalpSweepResult] = []

    # Pre-group bars by day
    day_groups: dict[date, pd.DataFrame] = {
        day: group for day, group in df.groupby("trading_day")  # type: ignore[misc]
    }

    # Compute qualifying days (gap filter)
    qualifying_days = compute_qualifying_days(
        df, config.min_gap_pct, config.min_price, config.max_price
    )

    # Compute opening ranges (fixed or_minutes)
    or_df = compute_opening_ranges(df, config.or_minutes)

    if or_df.empty:
        # No OR data - return empty results for all param combos
        for target_r, max_hold_bars in product(
            config.scalp_target_r_list, config.max_hold_bars_list
        ):
            results.append(_empty_scalp_result(symbol, target_r, max_hold_bars, 0))
        return results

    # Filter OR to gap-qualifying days
    valid_or = or_df[or_df["trading_day"].isin(qualifying_days)].copy()
    valid_days_count = len(valid_or)

    if valid_or.empty:
        # No qualifying days - return empty results
        for target_r, max_hold_bars in product(
            config.scalp_target_r_list, config.max_hold_bars_list
        ):
            results.append(_empty_scalp_result(symbol, target_r, max_hold_bars, 0))
        return results

    # Pre-compute entries for all qualifying days
    day_entries: dict[date, ScalpEntryInfo] = {}

    for _, row in valid_or.iterrows():
        day = row["trading_day"]
        or_high = row["or_high"]
        or_low = row["or_low"]
        or_midpoint = row["or_midpoint"]
        or_complete = int(row["or_complete_bar"])

        day_bars = day_groups.get(day)
        if day_bars is None or day_bars.empty:
            continue

        entry_info = _precompute_scalp_entries_for_day(
            day_bars, or_high, or_low, or_complete, or_midpoint
        )
        if entry_info is not None:
            day_entries[day] = entry_info

    # Sweep over parameter combinations
    total_combos = len(config.scalp_target_r_list) * len(config.max_hold_bars_list)
    combo_count = 0

    for target_r, max_hold_bars in product(config.scalp_target_r_list, config.max_hold_bars_list):
        combo_count += 1
        if combo_count % 4 == 0:
            logger.debug(
                "%s: processed %d/%d combinations",
                symbol,
                combo_count,
                total_combos,
            )

        if not day_entries:
            results.append(_empty_scalp_result(symbol, target_r, max_hold_bars, valid_days_count))
            continue

        # Vectorized exit detection for all days
        trades: list[dict[str, Any]] = []

        for _day, entry_info in day_entries.items():
            stop_price = entry_info["or_midpoint"]
            risk = entry_info["entry_price"] - stop_price
            if risk <= 0:
                continue
            target_price = entry_info["entry_price"] + target_r * risk

            trade = _find_scalp_exit_vectorized(
                entry_info["highs"],
                entry_info["lows"],
                entry_info["closes"],
                entry_info["bar_indices"],
                entry_info["entry_price"],
                entry_info["entry_bar_idx"],
                stop_price,
                target_price,
                max_hold_bars,
            )

            if trade is not None:
                trades.append(trade)

        # Compute metrics
        result = _compute_scalp_result(symbol, target_r, max_hold_bars, trades, valid_days_count)
        results.append(result)

    return results


def _empty_scalp_result(
    symbol: str,
    scalp_target_r: float,
    max_hold_bars: int,
    qualifying_days: int,
) -> ScalpSweepResult:
    """Create an empty result for parameter combinations with no trades."""
    return ScalpSweepResult(
        symbol=symbol,
        scalp_target_r=scalp_target_r,
        max_hold_bars=max_hold_bars,
        total_trades=0,
        win_rate=0.0,
        total_return_pct=0.0,
        avg_r_multiple=0.0,
        max_drawdown_pct=0.0,
        sharpe_ratio=0.0,
        profit_factor=0.0,
        avg_hold_bars=0.0,
        qualifying_days=qualifying_days,
    )


def _compute_scalp_result(
    symbol: str,
    scalp_target_r: float,
    max_hold_bars: int,
    trades: list[dict[str, Any]],
    qualifying_days: int,
) -> ScalpSweepResult:
    """Compute metrics from a list of trades."""
    if not trades:
        return _empty_scalp_result(symbol, scalp_target_r, max_hold_bars, qualifying_days)

    total_trades = len(trades)
    pnls = [t["pnl"] for t in trades]
    r_multiples = [t["r_multiple"] for t in trades]
    hold_bars_list = [t["hold_bars"] for t in trades]

    # Win rate
    winners = [t for t in trades if t["r_multiple"] > 0]
    win_rate = len(winners) / total_trades if total_trades > 0 else 0.0

    # Average R-multiple
    avg_r = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

    # Profit factor
    gross_wins = sum(p for p in pnls if p > 0)
    gross_losses = abs(sum(p for p in pnls if p < 0))
    profit_factor = (
        gross_wins / gross_losses if gross_losses > 0 else float("inf") if gross_wins > 0 else 0.0
    )

    # Total return (assuming $100 risk per trade for normalization)
    risk_per_trade = 100.0
    total_r = sum(r_multiples)
    total_return_pct = total_r * risk_per_trade / 10000.0 * 100

    # Average hold time in bars
    avg_hold = sum(hold_bars_list) / len(hold_bars_list) if hold_bars_list else 0.0

    # Equity curve for drawdown and Sharpe
    equity = [10000.0]
    for r in r_multiples:
        equity.append(equity[-1] + r * risk_per_trade)

    # Max drawdown
    max_dd_pct = _compute_max_drawdown_pct(equity)

    # Sharpe ratio (annualized from per-trade returns)
    sharpe = _compute_sharpe_from_r_multiples(r_multiples)

    return ScalpSweepResult(
        symbol=symbol,
        scalp_target_r=scalp_target_r,
        max_hold_bars=max_hold_bars,
        total_trades=total_trades,
        win_rate=win_rate,
        total_return_pct=total_return_pct,
        avg_r_multiple=avg_r,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
        avg_hold_bars=avg_hold,
        qualifying_days=qualifying_days,
    )


def _compute_max_drawdown_pct(equity: list[float]) -> float:
    """Compute maximum drawdown as percentage from equity curve."""
    if not equity:
        return 0.0

    peak = equity[0]
    max_dd = 0.0

    for value in equity:
        if value > peak:
            peak = value
        drawdown = (peak - value) / peak if peak > 0 else 0.0
        max_dd = max(max_dd, drawdown)

    return max_dd * 100


def _compute_sharpe_from_r_multiples(
    r_multiples: list[float],
    annualization_factor: float = 252.0,
) -> float:
    """Compute Sharpe ratio from R-multiples.

    Assumes approximately one trade per day for annualization.
    """
    if len(r_multiples) < 2:
        return 0.0

    mean_r = sum(r_multiples) / len(r_multiples)
    variance = sum((r - mean_r) ** 2 for r in r_multiples) / (len(r_multiples) - 1)
    std_r = variance**0.5

    if std_r < 1e-10:
        return 0.0

    return (mean_r / std_r) * (annualization_factor**0.5)


def run_sweep(config: ScalpSweepConfig) -> pd.DataFrame:
    """Run parameter sweep for all symbols.

    Args:
        config: Sweep configuration.

    Returns:
        DataFrame with all ScalpSweepResult data.
    """
    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Discover symbols
    if config.symbols:
        symbols = config.symbols
    else:
        # Scan data_dir for symbol directories
        symbols = [
            d.name for d in config.data_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        ]

    logger.info("Starting scalp sweep for %d symbols", len(symbols))

    all_results: list[ScalpSweepResult] = []

    for i, symbol in enumerate(symbols):
        logger.info("Processing %s (%d/%d)", symbol, i + 1, len(symbols))

        # Load data
        df = load_symbol_data(config.data_dir, symbol, config.start_date, config.end_date)

        if df.empty:
            logger.warning("No data for %s, skipping", symbol)
            continue

        # Run sweep
        symbol_results = run_single_symbol_sweep(df, symbol, config)

        if symbol_results:
            all_results.extend(symbol_results)

            # Save per-symbol results
            symbol_df = pd.DataFrame([vars(r) for r in symbol_results])
            symbol_path = config.output_dir / f"scalp_sweep_{symbol}.parquet"
            symbol_df.to_parquet(symbol_path, index=False)
            logger.debug("Saved %d results to %s", len(symbol_results), symbol_path)

    # Create summary DataFrame
    if not all_results:
        logger.warning("No results generated from sweep")
        return pd.DataFrame()

    results_df = pd.DataFrame([vars(r) for r in all_results])

    # Save cross-symbol summary
    summary_path = config.output_dir / "scalp_sweep_summary.parquet"
    results_df.to_parquet(summary_path, index=False)
    logger.info("Saved summary with %d results to %s", len(results_df), summary_path)

    return results_df


def generate_heatmap(
    results_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Generate 2D heatmap: scalp_target_r × max_hold_bars, color = Sharpe ratio.

    Args:
        results_df: DataFrame with sweep results.
        output_dir: Directory to save heatmap file.
    """
    if results_df.empty:
        logger.warning("No results to generate heatmap from")
        return

    import plotly.graph_objects as go

    output_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate across all symbols
    agg = (
        results_df.groupby(["scalp_target_r", "max_hold_bars"])
        .agg(
            sharpe_ratio=("sharpe_ratio", "mean"),
            total_trades=("total_trades", "sum"),
            win_rate=("win_rate", "mean"),
            profit_factor=("profit_factor", "mean"),
            avg_r_multiple=("avg_r_multiple", "mean"),
        )
        .reset_index()
    )

    # Pivot for heatmap
    pivot_sharpe = agg.pivot(index="max_hold_bars", columns="scalp_target_r", values="sharpe_ratio")
    pivot_trades = agg.pivot(index="max_hold_bars", columns="scalp_target_r", values="total_trades")
    pivot_win_rate = agg.pivot(index="max_hold_bars", columns="scalp_target_r", values="win_rate")
    pivot_profit_factor = agg.pivot(
        index="max_hold_bars", columns="scalp_target_r", values="profit_factor"
    )

    x_vals = pivot_sharpe.columns.tolist()
    y_vals = pivot_sharpe.index.tolist()

    fig = go.Figure()

    # Add traces for each metric (only Sharpe visible by default)
    fig.add_trace(
        go.Heatmap(
            z=pivot_sharpe.values,
            x=x_vals,
            y=y_vals,
            colorscale="RdYlGn",
            zmid=0,
            text=pivot_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>"
                "Max Hold Bars: %{y}<br>"
                "Sharpe: %{z:.2f}<br>"
                "Trades: %{text}<extra></extra>"
            ),
            visible=True,
            name="Sharpe Ratio",
        )
    )

    fig.add_trace(
        go.Heatmap(
            z=pivot_win_rate.values,
            x=x_vals,
            y=y_vals,
            colorscale="RdYlGn",
            zmid=0.5,
            text=pivot_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>"
                "Max Hold Bars: %{y}<br>"
                "Win Rate: %{z:.2%}<br>"
                "Trades: %{text}<extra></extra>"
            ),
            visible=False,
            name="Win Rate",
        )
    )

    fig.add_trace(
        go.Heatmap(
            z=pivot_profit_factor.values,
            x=x_vals,
            y=y_vals,
            colorscale="RdYlGn",
            zmid=1.0,
            text=pivot_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>"
                "Max Hold Bars: %{y}<br>"
                "Profit Factor: %{z:.2f}<br>"
                "Trades: %{text}<extra></extra>"
            ),
            visible=False,
            name="Profit Factor",
        )
    )

    fig.add_trace(
        go.Heatmap(
            z=pivot_trades.values,
            x=x_vals,
            y=y_vals,
            colorscale="Blues",
            text=pivot_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>Max Hold Bars: %{y}<br>Total Trades: %{z:,}<extra></extra>"
            ),
            visible=False,
            name="Total Trades",
        )
    )

    # Create dropdown menu
    fig.update_layout(
        title="ORB Scalp Parameter Sweep: Target R × Max Hold Bars",
        xaxis_title="Scalp Target R",
        yaxis_title="Max Hold Bars",
        updatemenus=[
            {
                "buttons": [
                    {
                        "label": "Sharpe Ratio",
                        "method": "update",
                        "args": [{"visible": [True, False, False, False]}],
                    },
                    {
                        "label": "Win Rate",
                        "method": "update",
                        "args": [{"visible": [False, True, False, False]}],
                    },
                    {
                        "label": "Profit Factor",
                        "method": "update",
                        "args": [{"visible": [False, False, True, False]}],
                    },
                    {
                        "label": "Total Trades",
                        "method": "update",
                        "args": [{"visible": [False, False, False, True]}],
                    },
                ],
                "direction": "down",
                "showactive": True,
                "x": 0.0,
                "xanchor": "left",
                "y": 1.15,
                "yanchor": "top",
            }
        ],
    )

    output_path = output_dir / "scalp_heatmap.html"
    fig.write_html(str(output_path))
    logger.info("Saved heatmap to %s", output_path)


def main() -> None:
    """CLI entry point for VectorBT ORB Scalp parameter sweep."""
    parser = argparse.ArgumentParser(
        description="VectorBT ORB Scalp parameter sweep",
        prog="python -m argus.backtest.vectorbt_orb_scalp",
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="Directory containing historical Parquet files",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated symbols. Empty = all in data-dir",
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/backtest_runs/scalp_sweeps"),
        help="Output directory for results",
    )
    # Optional parameter overrides for testing
    parser.add_argument(
        "--target-r",
        type=str,
        default=None,
        help="Override: comma-separated target R values",
    )
    parser.add_argument(
        "--max-hold-bars",
        type=str,
        default=None,
        help="Override: comma-separated max hold bars values",
    )
    parser.add_argument(
        "--or-minutes",
        type=int,
        default=None,
        help="Override: OR window minutes (default: 5)",
    )
    parser.add_argument(
        "--min-gap",
        type=float,
        default=None,
        help="Override: minimum gap percentage (default: 2.0)",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Build config
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    config = ScalpSweepConfig(
        data_dir=args.data_dir,
        symbols=symbols,
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        output_dir=args.output_dir,
    )

    # Apply parameter overrides
    if args.target_r:
        config.scalp_target_r_list = [float(x) for x in args.target_r.split(",")]
    if args.max_hold_bars:
        config.max_hold_bars_list = [int(x) for x in args.max_hold_bars.split(",")]
    if args.or_minutes:
        config.or_minutes = args.or_minutes
    if args.min_gap:
        config.min_gap_pct = args.min_gap

    # Run sweep
    results = run_sweep(config)

    if results.empty:
        logger.warning("No results generated. Check data availability.")
        return

    # Generate heatmap
    generate_heatmap(results, config.output_dir)

    print(f"\nSweep complete: {len(results)} combinations evaluated")
    print(f"Results saved to {config.output_dir}")

    # Print summary statistics
    total_trades = results["total_trades"].sum()
    results_with_trades = results[results["total_trades"] > 0]
    if not results_with_trades.empty:
        avg_sharpe = results_with_trades["sharpe_ratio"].mean()
        avg_win_rate = results_with_trades["win_rate"].mean()
        print(f"Total trades across all combinations: {total_trades:,}")
        print(f"Average Sharpe (where trades > 0): {avg_sharpe:.2f}")
        print(f"Average Win Rate (where trades > 0): {avg_win_rate:.1%}")

        # Best parameter combo
        best = results_with_trades.loc[results_with_trades["sharpe_ratio"].idxmax()]
        print(
            f"\nBest by Sharpe: target_r={best['scalp_target_r']}, "
            f"max_hold_bars={best['max_hold_bars']}, "
            f"sharpe={best['sharpe_ratio']:.2f}"
        )
    else:
        print("No trades generated across any parameter combination.")


if __name__ == "__main__":
    main()
