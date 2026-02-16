"""VectorBT ORB parameter sweep implementation.

Vectorized approximation of the ORB Breakout strategy for fast parameter
exploration. Intentionally simplified — see Sprint 8 spec for what's
included vs excluded and why.

Performance: Full sweep (29 symbols × 18K combos = 522K combinations)
completed in ~77 seconds on M1 MacBook Pro. Uses vectorized NumPy operations
for exit detection instead of iterrows().

Uses pure NumPy/Pandas for entry/exit logic (VectorBT had numba/coverage
compatibility issues at install time). Metrics computed using similar
approach to argus/backtest/metrics.py.

Usage:
    python -m argus.backtest.vectorbt_orb \
        --data-dir data/historical/1m \
        --symbols TSLA,NVDA,AAPL \
        --start 2025-06-01 --end 2025-12-31 \
        --output-dir data/backtest_runs/sweeps
"""

from __future__ import annotations

import argparse
import logging
from dataclasses import dataclass, field
from datetime import date
from itertools import product
from pathlib import Path
from typing import TypedDict
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

# Market hours constants (in minutes from midnight ET)
MARKET_OPEN_MINUTES = 9 * 60 + 30  # 9:30 AM ET = 570 minutes
MARKET_CLOSE_MINUTES = 16 * 60  # 4:00 PM ET = 960 minutes
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET = 945 minutes


@dataclass
class SweepConfig:
    """Configuration for a VectorBT parameter sweep."""

    data_dir: Path
    symbols: list[str]  # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (defaults match the grid in Sprint 8 spec)
    or_minutes_list: list[int] = field(default_factory=lambda: [5, 10, 15, 20, 30])
    target_r_list: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 2.5, 3.0]
    )
    stop_buffer_list: list[float] = field(
        default_factory=lambda: [0.0, 0.1, 0.2, 0.5]
    )
    max_hold_list: list[int] = field(
        default_factory=lambda: [15, 30, 45, 60, 90, 120]
    )
    min_gap_list: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 3.0, 5.0]
    )
    max_range_atr_list: list[float] = field(
        default_factory=lambda: [0.3, 0.5, 0.75, 1.0, 1.5, 999.0]
    )

    # Scanner filters (not swept, fixed thresholds)
    min_price: float = 5.0
    max_price: float = 10000.0


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
    win_rate: float  # 0.0-1.0
    total_return_pct: float  # Net return as % of initial capital
    avg_r_multiple: float  # Average R per trade
    max_drawdown_pct: float  # Peak-to-trough as % of equity
    sharpe_ratio: float  # Annualized
    profit_factor: float  # Gross profit / gross loss
    avg_hold_minutes: float  # Average trade duration
    qualifying_days: int  # Days that passed gap + range filter


class EntryInfo(TypedDict):
    """Pre-computed entry information for a single day."""

    entry_price: float
    entry_minutes: int
    or_low: float
    or_range: float  # OR high - OR low, for ATR ratio filtering
    atr: float | None  # Daily ATR, None if not available
    # NumPy arrays for post-entry bars
    highs: np.ndarray
    lows: np.ndarray
    closes: np.ndarray
    minutes: np.ndarray


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
    parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
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
    df = df[
        (df["trading_day"] >= start_date) & (df["trading_day"] <= end_date)
    ].copy()

    if df.empty:
        return pd.DataFrame()

    # Compute minutes from market open (9:30 AM ET)
    df["time_et"] = df["timestamp_et"].dt.time
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


def compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Compute ATR(14) from 1-minute bars aggregated to daily.

    Args:
        df: DataFrame with trading_day, high, low, close columns.
        period: ATR period (default 14).

    Returns:
        Series indexed by trading_day with ATR values.
        First (period-1) days will have NaN.
    """
    # Aggregate to daily OHLC
    daily = (
        df.groupby("trading_day")
        .agg(
            {
                "open": "first",
                "high": "max",
                "low": "min",
                "close": "last",
            }
        )
        .reset_index()
    )

    if len(daily) < 2:
        return pd.Series(dtype=float)

    # Compute True Range
    daily["prev_close"] = daily["close"].shift(1)
    daily["tr1"] = daily["high"] - daily["low"]
    daily["tr2"] = abs(daily["high"] - daily["prev_close"])
    daily["tr3"] = abs(daily["low"] - daily["prev_close"])
    daily["true_range"] = daily[["tr1", "tr2", "tr3"]].max(axis=1)

    # ATR as simple moving average of True Range
    daily["atr"] = daily["true_range"].rolling(window=period, min_periods=period).mean()

    return daily.set_index("trading_day")["atr"]


def compute_qualifying_days(
    df: pd.DataFrame,
    daily_atr: pd.Series,
    min_gap_pct: float,
    min_price: float = 5.0,
    max_price: float = 10000.0,
) -> set[date]:
    """Identify trading days that pass the gap and price filters.

    Args:
        df: DataFrame with trading_day, open, close columns.
        daily_atr: Series of ATR indexed by trading_day.
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
        DataFrame with columns: trading_day, or_high, or_low, or_range,
        or_complete_bar (bar index where OR window closes).
    """
    # Filter to opening range bars only
    or_bars = df[df["minutes_from_open"] < or_minutes].copy()

    if or_bars.empty:
        return pd.DataFrame(
            columns=["trading_day", "or_high", "or_low", "or_range", "or_complete_bar"]
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

    or_agg["or_range"] = or_agg["or_high"] - or_agg["or_low"]

    return or_agg


def _find_exit_vectorized(
    post_entry_highs: np.ndarray,
    post_entry_lows: np.ndarray,
    post_entry_closes: np.ndarray,
    post_entry_minutes: np.ndarray,
    entry_price: float,
    entry_minutes: int,
    stop_price: float,
    target_price: float,
    max_hold_minutes: int,
) -> dict | None:
    """Find exit using vectorized operations. No iterrows().

    Args:
        post_entry_highs: Array of high prices for bars after entry.
        post_entry_lows: Array of low prices for bars after entry.
        post_entry_closes: Array of close prices for bars after entry.
        post_entry_minutes: Array of minutes_from_open for bars after entry.
        entry_price: The entry price.
        entry_minutes: The minutes_from_open of entry bar.
        stop_price: Stop loss price.
        target_price: Target price.
        max_hold_minutes: Maximum hold time before time stop.

    Returns:
        Dict with trade details or None if no valid exit found.
    """
    n = len(post_entry_highs)
    if n == 0:
        return None

    # Compute hold times for each bar
    hold_times = post_entry_minutes - entry_minutes

    # Boolean masks for each exit condition
    stop_hit = post_entry_lows <= stop_price
    target_hit = post_entry_highs >= target_price
    hold_exceeded = hold_times >= max_hold_minutes
    eod_hit = post_entry_minutes >= 375  # 3:45 PM ET

    # Find first bar index for each condition (use n as "not found" sentinel)
    stop_idx = int(np.argmax(stop_hit)) if stop_hit.any() else n
    target_idx = int(np.argmax(target_hit)) if target_hit.any() else n
    hold_idx = int(np.argmax(hold_exceeded)) if hold_exceeded.any() else n
    eod_idx = int(np.argmax(eod_hit)) if eod_hit.any() else n

    # Earliest exit wins
    # Priority on same bar: EOD > time_stop > stop > target (conservative for longs)
    exit_idx = min(stop_idx, target_idx, hold_idx, eod_idx)

    if exit_idx >= n:
        # Shouldn't happen with EOD check, but safety fallback
        exit_idx = n - 1
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == eod_idx and eod_hit[exit_idx]:
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == hold_idx and hold_exceeded[exit_idx]:
        # Check if stop or target also hit on this bar (stop wins)
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        elif target_idx == exit_idx and target_hit[exit_idx]:
            reason = "time_stop"  # Time stop takes priority over target
            exit_price = float(post_entry_closes[exit_idx])
        else:
            reason = "time_stop"
            exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == stop_idx and stop_hit[exit_idx]:
        reason = "stop"
        exit_price = stop_price
    elif exit_idx == target_idx and target_hit[exit_idx]:
        reason = "target"
        exit_price = target_price
    else:
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])

    exit_minutes = int(hold_times[exit_idx])
    risk = entry_price - stop_price
    pnl = exit_price - entry_price
    r_multiple = pnl / risk if risk > 0 else 0.0

    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "risk": risk,
        "pnl": pnl,
        "r_multiple": r_multiple,
        "hold_minutes": exit_minutes,
        "exit_reason": reason,
    }


def _precompute_entries_for_day(
    day_bars: pd.DataFrame,
    or_high: float,
    or_low: float,
    or_complete_bar: int,
    or_range: float,
    atr: float | None,
) -> EntryInfo | None:
    """Pre-compute entry information and extract NumPy arrays for a day.

    The entry bar (first bar that closes above OR high after OR completes)
    is the same regardless of target_r, stop_buffer, max_hold, or max_range_atr.
    We compute it once here and extract the arrays needed for vectorized exit
    detection. The or_range and atr are stored for filtering at runtime.

    Args:
        day_bars: DataFrame of bars for a single trading day.
        or_high: Opening range high.
        or_low: Opening range low.
        or_complete_bar: Bar index where OR completes.
        or_range: Opening range size (or_high - or_low).
        atr: Daily ATR value, or None if not available.

    Returns:
        EntryInfo dict with entry details and NumPy arrays, or None if no entry.
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
    entry_price = float(entry_bar["close"])
    entry_bar_idx = int(entry_bar["bar_number_in_day"])
    entry_minutes = int(entry_bar["minutes_from_open"])

    # Extract post-entry bars as NumPy arrays
    post_entry_bars = day_bars[day_bars["bar_number_in_day"] > entry_bar_idx]

    if post_entry_bars.empty:
        return None

    return EntryInfo(
        entry_price=entry_price,
        entry_minutes=entry_minutes,
        or_low=or_low,
        or_range=or_range,
        atr=atr,
        highs=post_entry_bars["high"].to_numpy(),
        lows=post_entry_bars["low"].to_numpy(),
        closes=post_entry_bars["close"].to_numpy(),
        minutes=post_entry_bars["minutes_from_open"].to_numpy(),
    )


def run_single_symbol_sweep(
    df: pd.DataFrame,
    symbol: str,
    daily_atr: pd.Series,
    config: SweepConfig,
) -> list[SweepResult]:
    """Run parameter sweep for a single symbol (VECTORIZED VERSION).

    Uses pre-computed entries and vectorized exit detection to avoid
    iterrows() calls in the inner loop. Entries are pre-computed per
    (or_minutes, day) and include or_range/atr for runtime filtering.

    Args:
        df: DataFrame with all bar data for the symbol.
        symbol: Ticker symbol.
        daily_atr: ATR series indexed by trading_day.
        config: Sweep configuration with parameter ranges.

    Returns:
        List of SweepResult objects (one per parameter combination).
    """
    results: list[SweepResult] = []

    # Pre-group bars by day ONCE at the top
    day_groups: dict[date, pd.DataFrame] = {
        day: group for day, group in df.groupby("trading_day")
    }

    # Pre-compute qualifying days for each min_gap_pct
    gap_qualifying: dict[float, set[date]] = {}
    for min_gap in config.min_gap_list:
        gap_qualifying[min_gap] = compute_qualifying_days(
            df, daily_atr, min_gap, config.min_price, config.max_price
        )

    # Pre-compute opening ranges for each or_minutes
    or_data: dict[int, pd.DataFrame] = {}
    for or_min in config.or_minutes_list:
        or_data[or_min] = compute_opening_ranges(df, or_min)

    # Nested parameter loop
    total_combos = (
        len(config.min_gap_list)
        * len(config.or_minutes_list)
        * len(config.max_range_atr_list)
        * len(config.target_r_list)
        * len(config.stop_buffer_list)
        * len(config.max_hold_list)
    )

    combo_count = 0

    for min_gap in config.min_gap_list:
        qualifying_days = gap_qualifying[min_gap]

        for or_min in config.or_minutes_list:
            or_df = or_data[or_min]
            if or_df.empty:
                # No OR data for this window
                for max_range_atr in config.max_range_atr_list:
                    for target_r, stop_buf, max_hold in product(
                        config.target_r_list,
                        config.stop_buffer_list,
                        config.max_hold_list,
                    ):
                        combo_count += 1
                        if combo_count % 1000 == 0:
                            logger.debug(
                                "%s: processed %d/%d combinations",
                                symbol,
                                combo_count,
                                total_combos,
                            )
                        results.append(
                            _empty_result(
                                symbol,
                                or_min,
                                target_r,
                                stop_buf,
                                max_hold,
                                min_gap,
                                max_range_atr,
                                0,
                            )
                        )
                continue

            # Filter OR to gap-qualifying days and merge ATR
            # This is done ONCE per (min_gap, or_min) pair
            valid_or = or_df.copy()
            valid_or = valid_or[valid_or["trading_day"].isin(qualifying_days)]

            # Merge ATR
            valid_or = valid_or.merge(
                daily_atr.rename("atr").reset_index(),
                on="trading_day",
                how="left",
            )

            # Pre-compute entries for ALL gap-qualifying days (not ATR-filtered)
            # Entry computation depends only on (or_min, day) - ATR filtering
            # is applied at runtime in the max_range_atr loop
            all_day_entries: dict[date, EntryInfo] = {}

            for _, row in valid_or.iterrows():
                day = row["trading_day"]
                or_high = row["or_high"]
                or_low = row["or_low"]
                or_range = row["or_range"]
                or_complete = int(row["or_complete_bar"])
                atr_val = row["atr"] if pd.notna(row["atr"]) else None

                day_bars = day_groups.get(day)
                if day_bars is None or day_bars.empty:
                    continue

                entry_info = _precompute_entries_for_day(
                    day_bars, or_high, or_low, or_complete, or_range, atr_val
                )
                if entry_info is not None:
                    all_day_entries[day] = entry_info

            for max_range_atr in config.max_range_atr_list:
                # Filter entries by max_range_atr_ratio at RUNTIME
                # This is the critical fix: filtering happens HERE, not during
                # entry pre-computation
                if max_range_atr < 999.0:
                    day_entries = {
                        day: entry
                        for day, entry in all_day_entries.items()
                        if (
                            entry["atr"] is not None
                            and entry["or_range"] / entry["atr"] <= max_range_atr
                        )
                    }
                else:
                    # 999.0 = no ATR filtering (include all, even NaN ATR)
                    day_entries = all_day_entries

                valid_days_count = len(day_entries)

                # Inner loop over target_r, stop_buf, max_hold
                for target_r, stop_buf, max_hold in product(
                    config.target_r_list,
                    config.stop_buffer_list,
                    config.max_hold_list,
                ):
                    combo_count += 1
                    if combo_count % 1000 == 0:
                        logger.debug(
                            "%s: processed %d/%d combinations",
                            symbol,
                            combo_count,
                            total_combos,
                        )

                    if not day_entries:
                        results.append(
                            _empty_result(
                                symbol,
                                or_min,
                                target_r,
                                stop_buf,
                                max_hold,
                                min_gap,
                                max_range_atr,
                                0,
                            )
                        )
                        continue

                    # OPTIMIZATION: Vectorized exit detection
                    trades: list[dict] = []

                    for _day, entry_info in day_entries.items():
                        or_low = entry_info["or_low"]
                        stop_price = or_low * (1 - stop_buf / 100)
                        risk = entry_info["entry_price"] - stop_price
                        if risk <= 0:
                            continue
                        target_price = entry_info["entry_price"] + target_r * risk

                        trade = _find_exit_vectorized(
                            entry_info["highs"],
                            entry_info["lows"],
                            entry_info["closes"],
                            entry_info["minutes"],
                            entry_info["entry_price"],
                            entry_info["entry_minutes"],
                            stop_price,
                            target_price,
                            max_hold,
                        )

                        if trade is not None:
                            trades.append(trade)

                    # Compute metrics for this parameter combination
                    result = _compute_sweep_result(
                        symbol,
                        or_min,
                        target_r,
                        stop_buf,
                        max_hold,
                        min_gap,
                        max_range_atr,
                        trades,
                        valid_days_count,
                    )
                    results.append(result)

    return results


def _empty_result(
    symbol: str,
    or_minutes: int,
    target_r: float,
    stop_buffer_pct: float,
    max_hold_minutes: int,
    min_gap_pct: float,
    max_range_atr_ratio: float,
    qualifying_days: int,
) -> SweepResult:
    """Create an empty result for parameter combinations with no trades."""
    return SweepResult(
        symbol=symbol,
        or_minutes=or_minutes,
        target_r=target_r,
        stop_buffer_pct=stop_buffer_pct,
        max_hold_minutes=max_hold_minutes,
        min_gap_pct=min_gap_pct,
        max_range_atr_ratio=max_range_atr_ratio,
        total_trades=0,
        win_rate=0.0,
        total_return_pct=0.0,
        avg_r_multiple=0.0,
        max_drawdown_pct=0.0,
        sharpe_ratio=0.0,
        profit_factor=0.0,
        avg_hold_minutes=0.0,
        qualifying_days=qualifying_days,
    )


def _compute_sweep_result(
    symbol: str,
    or_minutes: int,
    target_r: float,
    stop_buffer_pct: float,
    max_hold_minutes: int,
    min_gap_pct: float,
    max_range_atr_ratio: float,
    trades: list[dict],
    qualifying_days: int,
) -> SweepResult:
    """Compute metrics from a list of trades."""
    if not trades:
        return _empty_result(
            symbol,
            or_minutes,
            target_r,
            stop_buffer_pct,
            max_hold_minutes,
            min_gap_pct,
            max_range_atr_ratio,
            qualifying_days,
        )

    total_trades = len(trades)
    pnls = [t["pnl"] for t in trades]
    r_multiples = [t["r_multiple"] for t in trades]
    hold_minutes_list = [t["hold_minutes"] for t in trades]

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

    # Total return (assuming $10k risk per trade for normalization)
    risk_per_trade = 100.0  # $100 risk per trade for percentage calculation
    total_r = sum(r_multiples)
    total_return_pct = total_r * risk_per_trade / 10000.0 * 100  # As percentage

    # Average hold time
    avg_hold = (
        sum(hold_minutes_list) / len(hold_minutes_list) if hold_minutes_list else 0.0
    )

    # Equity curve for drawdown and Sharpe
    equity = [10000.0]  # Start with $10k
    for r in r_multiples:
        equity.append(equity[-1] + r * risk_per_trade)

    # Max drawdown
    max_dd_pct = _compute_max_drawdown_pct(equity)

    # Sharpe ratio (annualized from per-trade returns)
    sharpe = _compute_sharpe_from_r_multiples(r_multiples)

    return SweepResult(
        symbol=symbol,
        or_minutes=or_minutes,
        target_r=target_r,
        stop_buffer_pct=stop_buffer_pct,
        max_hold_minutes=max_hold_minutes,
        min_gap_pct=min_gap_pct,
        max_range_atr_ratio=max_range_atr_ratio,
        total_trades=total_trades,
        win_rate=win_rate,
        total_return_pct=total_return_pct,
        avg_r_multiple=avg_r,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe,
        profit_factor=profit_factor,
        avg_hold_minutes=avg_hold,
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

    return max_dd * 100  # As percentage


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

    # Annualized Sharpe (assuming ~1 trade per trading day)
    return (mean_r / std_r) * (annualization_factor**0.5)


def run_sweep(config: SweepConfig) -> pd.DataFrame:
    """Run parameter sweep for all symbols.

    Args:
        config: Sweep configuration.

    Returns:
        DataFrame with all SweepResult data.
    """
    # Create output directory
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Discover symbols
    if config.symbols:
        symbols = config.symbols
    else:
        # Scan data_dir for symbol directories
        symbols = [
            d.name
            for d in config.data_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    logger.info("Starting sweep for %d symbols", len(symbols))

    all_results: list[SweepResult] = []

    for i, symbol in enumerate(symbols):
        logger.info("Processing %s (%d/%d)", symbol, i + 1, len(symbols))

        # Load data
        df = load_symbol_data(
            config.data_dir, symbol, config.start_date, config.end_date
        )

        if df.empty:
            logger.warning("No data for %s, skipping", symbol)
            continue

        # Compute ATR
        daily_atr = compute_atr(df)

        if daily_atr.empty:
            logger.warning("Insufficient data for ATR on %s, skipping", symbol)
            continue

        # Run sweep
        symbol_results = run_single_symbol_sweep(df, symbol, daily_atr, config)

        if symbol_results:
            all_results.extend(symbol_results)

            # Save per-symbol results
            symbol_df = pd.DataFrame([vars(r) for r in symbol_results])
            symbol_path = config.output_dir / f"sweep_{symbol}.parquet"
            symbol_df.to_parquet(symbol_path, index=False)
            logger.info("Saved %d results to %s", len(symbol_results), symbol_path)

    # Create summary DataFrame
    if not all_results:
        logger.warning("No results generated from sweep")
        return pd.DataFrame()

    results_df = pd.DataFrame([vars(r) for r in all_results])

    # Save cross-symbol summary
    summary_path = config.output_dir / "sweep_summary.parquet"
    results_df.to_parquet(summary_path, index=False)
    logger.info("Saved summary with %d results to %s", len(results_df), summary_path)

    return results_df


def generate_heatmaps(
    results_df: pd.DataFrame,
    output_dir: Path,
    all_symbols: bool = False,
) -> None:
    """Generate heatmaps for parameter pairs.

    Args:
        results_df: DataFrame with sweep results.
        output_dir: Directory to save heatmap files.
        all_symbols: If True, generate heatmaps for all symbols. Default: top 5 by trade count.
    """
    # Handle empty results
    if results_df.empty:
        logger.warning("No results to generate heatmaps from")
        return

    # Create output subdirectories
    static_dir = output_dir / "static"
    interactive_dir = output_dir / "interactive"
    static_dir.mkdir(parents=True, exist_ok=True)
    interactive_dir.mkdir(parents=True, exist_ok=True)

    # Parameter columns for heatmaps
    param_cols = [
        "or_minutes",
        "target_r",
        "stop_buffer_pct",
        "max_hold_minutes",
        "min_gap_pct",
        "max_range_atr_ratio",
    ]

    # Determine which symbols to process
    if all_symbols:
        symbols_to_process = results_df["symbol"].unique().tolist()
    else:
        # Top 5 symbols by total trade count
        symbol_trades = (
            results_df.groupby("symbol")["total_trades"].sum().sort_values(ascending=False)
        )
        symbols_to_process = symbol_trades.head(5).index.tolist()

    # Add "ALL" for cross-symbol aggregate
    symbols_to_process.append("ALL")

    for symbol in symbols_to_process:
        if symbol == "ALL":
            df_subset = results_df.copy()
        else:
            df_subset = results_df[results_df["symbol"] == symbol].copy()

        if df_subset.empty:
            continue

        # Generate heatmaps for each pair of parameters
        for i, param1 in enumerate(param_cols):
            for param2 in param_cols[i + 1 :]:
                _generate_single_heatmap(
                    df_subset,
                    param1,
                    param2,
                    symbol,
                    static_dir,
                    interactive_dir,
                )

    logger.info(
        "Generated heatmaps for %d symbols in %s",
        len(symbols_to_process),
        output_dir,
    )


def _generate_single_heatmap(
    df: pd.DataFrame,
    param1: str,
    param2: str,
    symbol: str,
    static_dir: Path,
    interactive_dir: Path,
) -> None:
    """Generate a single heatmap for a parameter pair."""
    import matplotlib.pyplot as plt
    import plotly.graph_objects as go
    import seaborn as sns

    # Aggregate by the two parameters (average Sharpe, sum trades)
    agg = (
        df.groupby([param1, param2])
        .agg(
            sharpe_ratio=("sharpe_ratio", "mean"),
            total_trades=("total_trades", "sum"),
            win_rate=("win_rate", "mean"),
            profit_factor=("profit_factor", "mean"),
        )
        .reset_index()
    )

    # Pivot for heatmap
    pivot_sharpe = agg.pivot(index=param2, columns=param1, values="sharpe_ratio")
    pivot_trades = agg.pivot(index=param2, columns=param1, values="total_trades")

    # Static heatmap (matplotlib + seaborn)
    fig, ax = plt.subplots(figsize=(10, 8))
    sns.heatmap(
        pivot_sharpe,
        annot=pivot_trades.astype(int),
        fmt="d",
        cmap="RdYlGn",
        center=0,
        ax=ax,
        cbar_kws={"label": "Sharpe Ratio"},
    )
    ax.set_title(f"{symbol}: {param1} vs {param2}")
    ax.set_xlabel(param1)
    ax.set_ylabel(param2)

    static_path = static_dir / f"heatmap_{symbol}_{param1}_vs_{param2}.png"
    plt.tight_layout()
    plt.savefig(static_path, dpi=150)
    plt.close(fig)

    # Interactive heatmap with metric dropdown (plotly)
    # Pivot all metrics for dropdown switching
    pivot_win_rate = agg.pivot(index=param2, columns=param1, values="win_rate")
    pivot_profit_factor = agg.pivot(index=param2, columns=param1, values="profit_factor")

    # Prepare data for each metric
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
                f"{param1}: %{{x}}<br>"
                f"{param2}: %{{y}}<br>"
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
                f"{param1}: %{{x}}<br>"
                f"{param2}: %{{y}}<br>"
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
                f"{param1}: %{{x}}<br>"
                f"{param2}: %{{y}}<br>"
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
                f"{param1}: %{{x}}<br>"
                f"{param2}: %{{y}}<br>"
                "Total Trades: %{z:,}<extra></extra>"
            ),
            visible=False,
            name="Total Trades",
        )
    )

    # Create dropdown menu buttons
    fig.update_layout(
        title=f"{symbol}: {param1} vs {param2}",
        xaxis_title=param1,
        yaxis_title=param2,
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

    interactive_path = interactive_dir / f"heatmap_{symbol}_{param1}_vs_{param2}.html"
    fig.write_html(str(interactive_path))


def main() -> None:
    """CLI entry point for VectorBT ORB parameter sweep."""
    parser = argparse.ArgumentParser(
        description="VectorBT ORB parameter sweep",
        prog="python -m argus.backtest.vectorbt_orb",
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
        default=Path("data/backtest_runs/sweeps"),
        help="Output directory for results",
    )
    parser.add_argument(
        "--all-symbols",
        action="store_true",
        help="Generate heatmaps for all symbols (default: top 5)",
    )
    # Optional parameter overrides for testing
    parser.add_argument(
        "--or-minutes",
        type=str,
        default=None,
        help="Override: comma-separated OR minute values",
    )
    parser.add_argument(
        "--target-r",
        type=str,
        default=None,
        help="Override: comma-separated target R values",
    )
    parser.add_argument(
        "--stop-buffer",
        type=str,
        default=None,
        help="Override: comma-separated stop buffer values",
    )
    parser.add_argument(
        "--max-hold",
        type=str,
        default=None,
        help="Override: comma-separated max hold values",
    )
    parser.add_argument(
        "--min-gap",
        type=str,
        default=None,
        help="Override: comma-separated min gap values",
    )
    parser.add_argument(
        "--max-range-atr",
        type=str,
        default=None,
        help="Override: comma-separated max range/ATR values",
    )

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Build config
    symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]

    config = SweepConfig(
        data_dir=args.data_dir,
        symbols=symbols,
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        output_dir=args.output_dir,
    )

    # Apply parameter overrides
    if args.or_minutes:
        config.or_minutes_list = [int(x) for x in args.or_minutes.split(",")]
    if args.target_r:
        config.target_r_list = [float(x) for x in args.target_r.split(",")]
    if args.stop_buffer:
        config.stop_buffer_list = [float(x) for x in args.stop_buffer.split(",")]
    if args.max_hold:
        config.max_hold_list = [int(x) for x in args.max_hold.split(",")]
    if args.min_gap:
        config.min_gap_list = [float(x) for x in args.min_gap.split(",")]
    if args.max_range_atr:
        config.max_range_atr_list = [float(x) for x in args.max_range_atr.split(",")]

    # Run sweep
    results = run_sweep(config)

    if results.empty:
        logger.warning("No results generated. Check data availability.")
        return

    # Generate heatmaps
    generate_heatmaps(results, config.output_dir, all_symbols=args.all_symbols)

    print(f"\nSweep complete: {len(results)} combinations evaluated")
    print(f"Results saved to {config.output_dir}")

    # Print summary statistics
    total_trades = results["total_trades"].sum()
    avg_sharpe = results[results["total_trades"] > 0]["sharpe_ratio"].mean()
    print(f"Total trades across all combinations: {total_trades:,}")
    print(f"Average Sharpe (where trades > 0): {avg_sharpe:.2f}")


if __name__ == "__main__":
    main()
