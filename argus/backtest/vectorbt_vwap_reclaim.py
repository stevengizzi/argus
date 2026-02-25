"""VectorBT VWAP Reclaim parameter sweep implementation.

Mean-reversion strategy that buys stocks reclaiming VWAP after a pullback.

VECTORIZED IMPLEMENTATION: Precomputes entry candidates per day, then filters
by parameters and uses vectorized exit detection. Matches the performance
pattern of vectorbt_orb.py.

State machine per day:
    WATCHING → ABOVE_VWAP → BELOW_VWAP → entry (or EXHAUSTED)

Entry candidates are identified once per day (parameter-independent). Only the
filtering conditions (pullback depth, bars below, volume) vary by parameter.

Usage:
    python -m argus.backtest.vectorbt_vwap_reclaim \
        --data-dir data/historical/1m \
        --start 2025-01-01 --end 2025-06-30 \
        --output-dir data/backtest_runs/vwap_sweeps
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
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET = 945 minutes

# VWAP Reclaim operates 10:00 AM – 12:00 PM ET
EARLIEST_ENTRY_MINUTES = 10 * 60  # 10:00 AM ET = 600 minutes
LATEST_ENTRY_MINUTES = 12 * 60  # 12:00 PM ET = 720 minutes


@dataclass
class VwapReclaimSweepConfig:
    """Configuration for a VWAP Reclaim parameter sweep."""

    data_dir: Path
    symbols: list[str]  # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (swept)
    min_pullback_pct_list: list[float] = field(
        default_factory=lambda: [0.001, 0.002, 0.003, 0.005]
    )
    min_pullback_bars_list: list[int] = field(default_factory=lambda: [2, 3, 5, 8])
    volume_multiplier_list: list[float] = field(
        default_factory=lambda: [1.0, 1.2, 1.5, 2.0]
    )
    target_r_list: list[float] = field(default_factory=lambda: [0.5, 1.0, 1.5])
    time_stop_bars_list: list[int] = field(default_factory=lambda: [10, 15, 20, 30])

    # Fixed parameters (not swept)
    max_pullback_pct: float = 0.02
    max_chase_above_vwap_pct: float = 0.003
    stop_buffer_pct: float = 0.001
    min_gap_pct: float = 2.0  # 2% gap minimum

    # Scanner filters
    min_price: float = 5.0
    max_price: float = 10000.0


@dataclass
class VwapReclaimSweepResult:
    """Results from a single parameter combination on a single symbol."""

    symbol: str
    min_pullback_pct: float
    min_pullback_bars: int
    volume_multiplier: float
    target_r: float
    time_stop_bars: int

    # Metrics
    total_trades: int
    win_rate: float  # 0.0-1.0
    total_return_pct: float
    avg_r_multiple: float
    max_drawdown_pct: float
    sharpe_ratio: float
    profit_factor: float
    avg_hold_bars: float
    qualifying_days: int


class ReclaimEntryInfo(TypedDict):
    """Pre-computed entry information for a VWAP reclaim candidate."""

    entry_bar_idx: int  # Index in the day's DataFrame
    entry_price: float
    entry_minutes: int  # Minutes from midnight ET
    pullback_low: float
    pullback_depth_pct: float  # (vwap - pullback_low) / vwap
    bars_below: int
    volume_ratio: float  # Entry bar volume / avg volume up to that point
    # NumPy arrays for post-entry bars (for vectorized exit detection)
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
    - minutes_from_midnight: int (for time comparisons)
    - bar_number_in_day: int (0-indexed per day)

    Args:
        data_dir: Directory containing Parquet files.
        symbol: Ticker symbol.
        start_date: Start date (inclusive).
        end_date: End date (inclusive).

    Returns:
        DataFrame with OHLCV and derived columns.
        Empty DataFrame if no data found.
    """
    symbol_dir = data_dir / symbol.upper()
    if not symbol_dir.exists():
        logger.warning("No data directory for symbol %s", symbol)
        return pd.DataFrame()

    parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
    if not parquet_files:
        logger.warning("No Parquet files found for symbol %s", symbol)
        return pd.DataFrame()

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

    # Compute minutes from midnight (vectorized)
    df["minutes_from_midnight"] = (
        df["timestamp_et"].dt.hour * 60 + df["timestamp_et"].dt.minute
    )

    # Filter to market hours only (9:30 AM - 4:00 PM ET)
    df = df[
        (df["minutes_from_midnight"] >= MARKET_OPEN_MINUTES)
        & (df["minutes_from_midnight"] < 16 * 60)  # 4:00 PM
    ].copy()

    if df.empty:
        return pd.DataFrame()

    # Sort and compute bar number within each day
    df = df.sort_values("timestamp").reset_index(drop=True)
    df["bar_number_in_day"] = df.groupby("trading_day").cumcount()

    result_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trading_day",
        "minutes_from_midnight",
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
    daily = (
        df.groupby("trading_day")
        .agg({"open": "first", "close": "last"})
        .reset_index()
    )

    if len(daily) < 2:
        return set()

    daily["prev_close"] = daily["close"].shift(1)
    daily["gap_pct"] = (
        (daily["open"] - daily["prev_close"]) / daily["prev_close"]
    ) * 100

    qualifying = daily[
        (daily["gap_pct"] >= min_gap_pct)
        & (daily["open"] >= min_price)
        & (daily["open"] <= max_price)
        & (~daily["prev_close"].isna())
    ]

    return set(qualifying["trading_day"].tolist())


def _compute_vwap_vectorized(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
) -> np.ndarray:
    """Compute VWAP using vectorized cumsum operations.

    VWAP = cumsum(TP × volume) / cumsum(volume)
    where TP = (high + low + close) / 3

    Args:
        high: Array of high prices.
        low: Array of low prices.
        close: Array of close prices.
        volume: Array of volumes.

    Returns:
        Array of VWAP values.
    """
    tp = (high + low + close) / 3
    cum_tp_vol = np.cumsum(tp * volume)
    cum_vol = np.cumsum(volume)
    # Avoid division by zero
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = cum_tp_vol / cum_vol
        vwap[cum_vol == 0] = np.nan
    return vwap


def _precompute_reclaim_entries_for_day(
    day_df: pd.DataFrame,
    max_pullback_pct: float,
    max_chase_above_vwap_pct: float,
    stop_buffer_pct: float,
) -> list[ReclaimEntryInfo]:
    """Precompute all potential VWAP reclaim entries for a single day.

    Identifies all points where price crosses above VWAP after being below,
    capturing the state machine information (pullback depth, bars below, volume)
    for later filtering by parameter combination.

    This function is called ONCE per day, not per parameter combination.

    Args:
        day_df: DataFrame with bar data for one trading day.
        max_pullback_pct: Maximum pullback depth (entries beyond this are excluded).
        max_chase_above_vwap_pct: Max distance above VWAP for entry.
        stop_buffer_pct: Buffer below pullback low for stop (for risk > 0 check).

    Returns:
        List of ReclaimEntryInfo dicts (typically 0-3 per day).
    """
    if len(day_df) < 5:  # Need enough bars for meaningful VWAP
        return []

    # Extract arrays for vectorized operations
    high = day_df["high"].to_numpy()
    low = day_df["low"].to_numpy()
    close = day_df["close"].to_numpy()
    volume = day_df["volume"].to_numpy()
    minutes = day_df["minutes_from_midnight"].to_numpy()

    # Compute VWAP vectorized
    vwap = _compute_vwap_vectorized(high, low, close, volume)

    # Compute cumulative average volume for volume ratio calculation
    cum_volume = np.cumsum(volume)
    bar_counts = np.arange(1, len(volume) + 1)
    avg_volume = cum_volume / bar_counts

    # Find state transitions vectorized
    # above_vwap[i] = True if close[i] > vwap[i]
    above_vwap = close > vwap

    # Find crossings from below to above VWAP
    # crossing[i] = True if we crossed from below to above at bar i
    # This means: above_vwap[i] == True and above_vwap[i-1] == False
    crossings = np.zeros(len(close), dtype=bool)
    crossings[1:] = above_vwap[1:] & ~above_vwap[:-1]

    entries: list[ReclaimEntryInfo] = []
    in_below_state = False
    pullback_low = np.inf
    bars_below = 0
    first_above_idx = -1  # Index where we first went above VWAP

    for i in range(len(close)):
        bar_vwap = vwap[i]
        if np.isnan(bar_vwap) or bar_vwap <= 0:
            continue

        bar_close = close[i]
        bar_low = low[i]
        bar_minutes = minutes[i]
        bar_volume = volume[i]

        # State machine logic (simplified for one entry per day typical case)
        if not in_below_state:
            if bar_close > bar_vwap:
                # Transition to ABOVE_VWAP
                first_above_idx = i
            elif bar_close <= bar_vwap and first_above_idx >= 0:
                # Was above, now below - enter BELOW_VWAP state
                in_below_state = True
                pullback_low = bar_low
                bars_below = 1
        else:
            # In BELOW_VWAP state
            pullback_low = min(pullback_low, bar_low)

            # Check if pullback too deep
            pullback_depth = (bar_vwap - pullback_low) / bar_vwap
            if pullback_depth > max_pullback_pct:
                # EXHAUSTED - reset state machine
                in_below_state = False
                first_above_idx = -1
                pullback_low = np.inf
                bars_below = 0
                continue

            if bar_close <= bar_vwap:
                # Still below VWAP
                bars_below += 1
                continue

            # Close > VWAP: potential reclaim entry
            # Check time window
            if bar_minutes < EARLIEST_ENTRY_MINUTES or bar_minutes >= LATEST_ENTRY_MINUTES:
                # Outside entry window, go back to ABOVE_VWAP state
                in_below_state = False
                first_above_idx = i
                pullback_low = np.inf
                bars_below = 0
                continue

            # Check chase protection
            chase_limit = bar_vwap * (1 + max_chase_above_vwap_pct)
            if bar_close > chase_limit:
                in_below_state = False
                first_above_idx = i
                pullback_low = np.inf
                bars_below = 0
                continue

            # Compute volume ratio
            vol_ratio = bar_volume / avg_volume[i] if avg_volume[i] > 0 else 0.0

            # Check if risk would be positive
            stop_price = pullback_low * (1 - stop_buffer_pct)
            risk = bar_close - stop_price
            if risk <= 0:
                in_below_state = False
                first_above_idx = i
                pullback_low = np.inf
                bars_below = 0
                continue

            # Valid entry candidate - capture info
            # Extract post-entry arrays
            if i + 1 < len(close):
                entry_info = ReclaimEntryInfo(
                    entry_bar_idx=i,
                    entry_price=float(bar_close),
                    entry_minutes=int(bar_minutes),
                    pullback_low=float(pullback_low),
                    pullback_depth_pct=float(pullback_depth),
                    bars_below=bars_below,
                    volume_ratio=float(vol_ratio),
                    highs=high[i + 1 :].copy(),
                    lows=low[i + 1 :].copy(),
                    closes=close[i + 1 :].copy(),
                    minutes=minutes[i + 1 :].copy(),
                )
                entries.append(entry_info)

            # After entry, the day is done for this strategy (one trade per day)
            # But we capture it and let the caller decide
            # Reset state for potential additional entries (optional - conservative)
            in_below_state = False
            first_above_idx = i
            pullback_low = np.inf
            bars_below = 0

            # Single entry per day for sweep. The live strategy can retry after
            # failed entry conditions (resets to ABOVE_VWAP), so it may find
            # later reclaims that this sweep misses. This makes the backtest
            # slightly more conservative (fewer entries). See DEC-148.
            break

    return entries


def _find_exit_vectorized(
    post_entry_highs: np.ndarray,
    post_entry_lows: np.ndarray,
    post_entry_closes: np.ndarray,
    post_entry_minutes: np.ndarray,
    entry_price: float,
    entry_minutes: int,
    stop_price: float,
    target_price: float,
    time_stop_bars: int,
) -> dict | None:
    """Find exit using vectorized operations. No iterrows().

    Args:
        post_entry_highs: Array of high prices for bars after entry.
        post_entry_lows: Array of low prices for bars after entry.
        post_entry_closes: Array of close prices for bars after entry.
        post_entry_minutes: Array of minutes_from_midnight for bars after entry.
        entry_price: The entry price.
        entry_minutes: The minutes_from_midnight of entry bar.
        stop_price: Stop loss price.
        target_price: Target price.
        time_stop_bars: Bars until time stop triggers.

    Returns:
        Dict with trade details or None if no valid exit found.
    """
    n = len(post_entry_highs)
    if n == 0:
        return None

    # Boolean masks for each exit condition
    stop_hit = post_entry_lows <= stop_price
    target_hit = post_entry_highs >= target_price

    # Time stop: bars held >= time_stop_bars
    bars_held = np.arange(1, n + 1)
    time_stop_hit = bars_held >= time_stop_bars

    # EOD: 3:45 PM ET = 945 minutes from midnight
    eod_hit = post_entry_minutes >= EOD_FLATTEN_MINUTES

    # Find first bar index for each condition (use n as "not found" sentinel)
    stop_idx = int(np.argmax(stop_hit)) if stop_hit.any() else n
    target_idx = int(np.argmax(target_hit)) if target_hit.any() else n
    time_idx = int(np.argmax(time_stop_hit)) if time_stop_hit.any() else n
    eod_idx = int(np.argmax(eod_hit)) if eod_hit.any() else n

    # Earliest exit wins
    exit_idx = min(stop_idx, target_idx, time_idx, eod_idx)

    if exit_idx >= n:
        # No exit found, use last bar
        exit_idx = n - 1
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == eod_idx and eod_hit[exit_idx]:
        # Check if stop also hit on this bar (stop takes priority — worst case for longs)
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "eod"
            exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == time_idx and time_stop_hit[exit_idx]:
        # Check if stop also hit on this bar (stop takes priority)
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
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

    hold_bars = exit_idx + 1  # 1-indexed
    risk = entry_price - stop_price
    pnl = exit_price - entry_price
    r_multiple = pnl / risk if risk > 0 else 0.0

    return {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "risk": risk,
        "pnl": pnl,
        "r_multiple": r_multiple,
        "hold_bars": hold_bars,
        "exit_reason": reason,
    }


def run_single_symbol_sweep(
    df: pd.DataFrame,
    symbol: str,
    config: VwapReclaimSweepConfig,
) -> list[VwapReclaimSweepResult]:
    """Run parameter sweep for a single symbol (VECTORIZED VERSION).

    Uses pre-computed entries and vectorized exit detection to avoid
    iterrows() calls in the inner loop.

    Architecture:
    1. Pre-group data by day ONCE
    2. Pre-compute qualifying days (gap filter) ONCE
    3. Pre-compute ALL potential reclaim entries per day ONCE (parameter-independent)
    4. Filter entries by (min_pullback_pct, min_pullback_bars, volume_multiplier) at runtime
    5. Compute exits vectorized for each (target_r, time_stop_bars) combination

    Args:
        df: DataFrame with all bar data for the symbol.
        symbol: Ticker symbol.
        config: Sweep configuration with parameter ranges.

    Returns:
        List of VwapReclaimSweepResult objects (one per parameter combination).
    """
    results: list[VwapReclaimSweepResult] = []

    # Pre-group bars by day ONCE
    day_groups: dict[date, pd.DataFrame] = {
        day: group.reset_index(drop=True) for day, group in df.groupby("trading_day")
    }

    # Compute qualifying days (gap filter) ONCE
    qualifying_days = compute_qualifying_days(
        df, config.min_gap_pct, config.min_price, config.max_price
    )
    valid_days_count = len(qualifying_days)

    # Pre-compute ALL potential reclaim entries for each qualifying day ONCE
    # This is the key optimization - entries are computed once, filtered by params later
    all_day_entries: dict[date, list[ReclaimEntryInfo]] = {}
    for day in qualifying_days:
        day_df = day_groups.get(day)
        if day_df is None or day_df.empty:
            continue
        entries = _precompute_reclaim_entries_for_day(
            day_df,
            config.max_pullback_pct,
            config.max_chase_above_vwap_pct,
            config.stop_buffer_pct,
        )
        if entries:
            all_day_entries[day] = entries

    if not all_day_entries:
        # No entry candidates at all - return empty results for all param combos
        for params in product(
            config.min_pullback_pct_list,
            config.min_pullback_bars_list,
            config.volume_multiplier_list,
            config.target_r_list,
            config.time_stop_bars_list,
        ):
            results.append(
                _empty_vwap_result(symbol, *params, qualifying_days=valid_days_count)
            )
        return results

    # Flatten all entries across days for easier filtering
    all_entries: list[tuple[date, ReclaimEntryInfo]] = [
        (day, entry)
        for day, entries in all_day_entries.items()
        for entry in entries
    ]

    # Nested parameter loop - but entry detection is already done
    total_combos = (
        len(config.min_pullback_pct_list)
        * len(config.min_pullback_bars_list)
        * len(config.volume_multiplier_list)
        * len(config.target_r_list)
        * len(config.time_stop_bars_list)
    )
    combo_count = 0

    for min_pullback_pct in config.min_pullback_pct_list:
        for min_pullback_bars in config.min_pullback_bars_list:
            for volume_multiplier in config.volume_multiplier_list:
                # Filter entries by these three parameters ONCE
                filtered_entries = [
                    (day, entry) for day, entry in all_entries
                    if (entry["pullback_depth_pct"] >= min_pullback_pct
                        and entry["bars_below"] >= min_pullback_bars
                        and entry["volume_ratio"] >= volume_multiplier)
                ]

                for target_r in config.target_r_list:
                    for time_stop_bars in config.time_stop_bars_list:
                        combo_count += 1
                        if combo_count % 100 == 0:
                            logger.debug(
                                "%s: processed %d/%d combinations",
                                symbol,
                                combo_count,
                                total_combos,
                            )

                        if not filtered_entries:
                            results.append(
                                _empty_vwap_result(
                                    symbol,
                                    min_pullback_pct,
                                    min_pullback_bars,
                                    volume_multiplier,
                                    target_r,
                                    time_stop_bars,
                                    valid_days_count,
                                )
                            )
                            continue

                        # Compute trades using vectorized exit detection
                        trades: list[dict] = []
                        for _day, entry in filtered_entries:
                            stop_price = entry["pullback_low"] * (
                                1 - config.stop_buffer_pct
                            )
                            risk = entry["entry_price"] - stop_price
                            if risk <= 0:
                                continue
                            target_price = entry["entry_price"] + risk * target_r

                            trade = _find_exit_vectorized(
                                entry["highs"],
                                entry["lows"],
                                entry["closes"],
                                entry["minutes"],
                                entry["entry_price"],
                                entry["entry_minutes"],
                                stop_price,
                                target_price,
                                time_stop_bars,
                            )
                            if trade is not None:
                                trades.append(trade)

                        # Compute metrics
                        result = _compute_vwap_result(
                            symbol,
                            min_pullback_pct,
                            min_pullback_bars,
                            volume_multiplier,
                            target_r,
                            time_stop_bars,
                            trades,
                            valid_days_count,
                        )
                        results.append(result)

    return results


def _empty_vwap_result(
    symbol: str,
    min_pullback_pct: float,
    min_pullback_bars: int,
    volume_multiplier: float,
    target_r: float,
    time_stop_bars: int,
    qualifying_days: int,
) -> VwapReclaimSweepResult:
    """Create an empty result for parameter combinations with no trades."""
    return VwapReclaimSweepResult(
        symbol=symbol,
        min_pullback_pct=min_pullback_pct,
        min_pullback_bars=min_pullback_bars,
        volume_multiplier=volume_multiplier,
        target_r=target_r,
        time_stop_bars=time_stop_bars,
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


def _compute_vwap_result(
    symbol: str,
    min_pullback_pct: float,
    min_pullback_bars: int,
    volume_multiplier: float,
    target_r: float,
    time_stop_bars: int,
    trades: list[dict],
    qualifying_days: int,
) -> VwapReclaimSweepResult:
    """Compute metrics from a list of trades."""
    if not trades:
        return _empty_vwap_result(
            symbol,
            min_pullback_pct,
            min_pullback_bars,
            volume_multiplier,
            target_r,
            time_stop_bars,
            qualifying_days,
        )

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
    if gross_losses > 0:
        profit_factor = gross_wins / gross_losses
    elif gross_wins > 0:
        profit_factor = float("inf")
    else:
        profit_factor = 0.0

    # Total return (assuming $100 risk per trade for normalization)
    risk_per_trade = 100.0
    total_r = sum(r_multiples)
    total_return_pct = total_r * risk_per_trade / 10000.0 * 100

    # Average hold time
    avg_hold = sum(hold_bars_list) / len(hold_bars_list) if hold_bars_list else 0.0

    # Equity curve for drawdown and Sharpe
    equity = [10000.0]
    for r in r_multiples:
        equity.append(equity[-1] + r * risk_per_trade)

    # Max drawdown
    max_dd_pct = _compute_max_drawdown_pct(equity)

    # Sharpe ratio
    sharpe = _compute_sharpe_from_r_multiples(r_multiples)

    return VwapReclaimSweepResult(
        symbol=symbol,
        min_pullback_pct=min_pullback_pct,
        min_pullback_bars=min_pullback_bars,
        volume_multiplier=volume_multiplier,
        target_r=target_r,
        time_stop_bars=time_stop_bars,
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


def run_sweep(config: VwapReclaimSweepConfig) -> pd.DataFrame:
    """Run parameter sweep for all symbols.

    Args:
        config: Sweep configuration.

    Returns:
        DataFrame with all VwapReclaimSweepResult data.
    """
    config.output_dir.mkdir(parents=True, exist_ok=True)

    # Discover symbols
    if config.symbols:
        symbols = config.symbols
    else:
        symbols = [
            d.name
            for d in config.data_dir.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        ]

    logger.info("Starting VWAP Reclaim sweep for %d symbols", len(symbols))

    total_combos = (
        len(config.min_pullback_pct_list)
        * len(config.min_pullback_bars_list)
        * len(config.volume_multiplier_list)
        * len(config.target_r_list)
        * len(config.time_stop_bars_list)
    )
    logger.info("Parameter combinations: %d", total_combos)

    all_results: list[VwapReclaimSweepResult] = []

    for i, symbol in enumerate(symbols):
        logger.info("Processing %s (%d/%d)", symbol, i + 1, len(symbols))

        df = load_symbol_data(config.data_dir, symbol, config.start_date, config.end_date)

        if df.empty:
            logger.warning("No data for %s, skipping", symbol)
            continue

        symbol_results = run_single_symbol_sweep(df, symbol, config)

        if symbol_results:
            all_results.extend(symbol_results)

            # Save per-symbol results
            symbol_df = pd.DataFrame([vars(r) for r in symbol_results])
            symbol_path = config.output_dir / f"vwap_reclaim_sweep_{symbol}.parquet"
            symbol_df.to_parquet(symbol_path, index=False)
            logger.debug("Saved %d results to %s", len(symbol_results), symbol_path)

    if not all_results:
        logger.warning("No results generated from sweep")
        return pd.DataFrame()

    results_df = pd.DataFrame([vars(r) for r in all_results])

    # Save cross-symbol summary
    summary_path = config.output_dir / "vwap_reclaim_sweep_summary.parquet"
    results_df.to_parquet(summary_path, index=False)
    logger.info("Saved summary with %d results to %s", len(results_df), summary_path)

    # Also save as CSV for easy viewing
    csv_path = config.output_dir / "vwap_reclaim_sweep_summary.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info("Saved CSV summary to %s", csv_path)

    return results_df


def generate_heatmaps(
    results_df: pd.DataFrame,
    output_dir: Path,
) -> None:
    """Generate 2D heatmaps for key parameter pairs.

    Creates heatmaps for:
    - min_pullback_pct × min_pullback_bars
    - target_r × time_stop_bars
    - volume_multiplier × target_r

    Args:
        results_df: DataFrame with sweep results.
        output_dir: Directory to save heatmap files.
    """
    if results_df.empty:
        logger.warning("No results to generate heatmaps from")
        return

    import plotly.graph_objects as go

    output_dir.mkdir(parents=True, exist_ok=True)

    # Aggregate across all symbols
    agg = (
        results_df.groupby(
            [
                "min_pullback_pct",
                "min_pullback_bars",
                "volume_multiplier",
                "target_r",
                "time_stop_bars",
            ]
        )
        .agg(
            sharpe_ratio=("sharpe_ratio", "mean"),
            total_trades=("total_trades", "sum"),
            win_rate=("win_rate", "mean"),
            profit_factor=("profit_factor", "mean"),
            avg_r_multiple=("avg_r_multiple", "mean"),
        )
        .reset_index()
    )

    # Heatmap 1: min_pullback_pct × min_pullback_bars (aggregated over other params)
    heatmap1_agg = (
        agg.groupby(["min_pullback_pct", "min_pullback_bars"])
        .agg(sharpe_ratio=("sharpe_ratio", "mean"), total_trades=("total_trades", "sum"))
        .reset_index()
    )
    pivot1 = heatmap1_agg.pivot(
        index="min_pullback_bars", columns="min_pullback_pct", values="sharpe_ratio"
    )
    pivot1_trades = heatmap1_agg.pivot(
        index="min_pullback_bars", columns="min_pullback_pct", values="total_trades"
    )

    fig1 = go.Figure(
        go.Heatmap(
            z=pivot1.values,
            x=[f"{x:.3f}" for x in pivot1.columns],
            y=pivot1.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            text=pivot1_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Pullback Pct: %{x}<br>"
                "Pullback Bars: %{y}<br>"
                "Sharpe: %{z:.2f}<br>"
                "Trades: %{text}<extra></extra>"
            ),
        )
    )
    fig1.update_layout(
        title="VWAP Reclaim: Pullback Pct × Pullback Bars (Sharpe)",
        xaxis_title="Min Pullback Pct",
        yaxis_title="Min Pullback Bars",
    )
    fig1.write_html(str(output_dir / "vwap_heatmap_pullback.html"))
    logger.info("Saved pullback heatmap")

    # Heatmap 2: target_r × time_stop_bars
    heatmap2_agg = (
        agg.groupby(["target_r", "time_stop_bars"])
        .agg(sharpe_ratio=("sharpe_ratio", "mean"), total_trades=("total_trades", "sum"))
        .reset_index()
    )
    pivot2 = heatmap2_agg.pivot(
        index="time_stop_bars", columns="target_r", values="sharpe_ratio"
    )
    pivot2_trades = heatmap2_agg.pivot(
        index="time_stop_bars", columns="target_r", values="total_trades"
    )

    fig2 = go.Figure(
        go.Heatmap(
            z=pivot2.values,
            x=pivot2.columns.tolist(),
            y=pivot2.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            text=pivot2_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>"
                "Time Stop Bars: %{y}<br>"
                "Sharpe: %{z:.2f}<br>"
                "Trades: %{text}<extra></extra>"
            ),
        )
    )
    fig2.update_layout(
        title="VWAP Reclaim: Target R × Time Stop Bars (Sharpe)",
        xaxis_title="Target R",
        yaxis_title="Time Stop Bars",
    )
    fig2.write_html(str(output_dir / "vwap_heatmap_target_time.html"))
    logger.info("Saved target/time heatmap")

    # Heatmap 3: volume_multiplier × target_r
    heatmap3_agg = (
        agg.groupby(["volume_multiplier", "target_r"])
        .agg(sharpe_ratio=("sharpe_ratio", "mean"), total_trades=("total_trades", "sum"))
        .reset_index()
    )
    pivot3 = heatmap3_agg.pivot(
        index="volume_multiplier", columns="target_r", values="sharpe_ratio"
    )
    pivot3_trades = heatmap3_agg.pivot(
        index="volume_multiplier", columns="target_r", values="total_trades"
    )

    fig3 = go.Figure(
        go.Heatmap(
            z=pivot3.values,
            x=pivot3.columns.tolist(),
            y=pivot3.index.tolist(),
            colorscale="RdYlGn",
            zmid=0,
            text=pivot3_trades.values.astype(int),
            texttemplate="%{text}",
            hovertemplate=(
                "Target R: %{x}<br>"
                "Volume Mult: %{y}<br>"
                "Sharpe: %{z:.2f}<br>"
                "Trades: %{text}<extra></extra>"
            ),
        )
    )
    fig3.update_layout(
        title="VWAP Reclaim: Volume Multiplier × Target R (Sharpe)",
        xaxis_title="Target R",
        yaxis_title="Volume Multiplier",
    )
    fig3.write_html(str(output_dir / "vwap_heatmap_volume_target.html"))
    logger.info("Saved volume/target heatmap")


def main() -> None:
    """CLI entry point for VectorBT VWAP Reclaim parameter sweep."""
    parser = argparse.ArgumentParser(
        description="VectorBT VWAP Reclaim parameter sweep",
        prog="python -m argus.backtest.vectorbt_vwap_reclaim",
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
        default=Path("data/backtest_runs/vwap_sweeps"),
        help="Output directory for results",
    )
    # Optional parameter overrides
    parser.add_argument(
        "--min-pullback-pct",
        type=str,
        default=None,
        help="Override: comma-separated min pullback pct values",
    )
    parser.add_argument(
        "--min-pullback-bars",
        type=str,
        default=None,
        help="Override: comma-separated min pullback bars values",
    )
    parser.add_argument(
        "--volume-mult",
        type=str,
        default=None,
        help="Override: comma-separated volume multiplier values",
    )
    parser.add_argument(
        "--target-r",
        type=str,
        default=None,
        help="Override: comma-separated target R values",
    )
    parser.add_argument(
        "--time-stop-bars",
        type=str,
        default=None,
        help="Override: comma-separated time stop bars values",
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

    config = VwapReclaimSweepConfig(
        data_dir=args.data_dir,
        symbols=symbols,
        start_date=date.fromisoformat(args.start),
        end_date=date.fromisoformat(args.end),
        output_dir=args.output_dir,
    )

    # Apply parameter overrides
    if args.min_pullback_pct:
        config.min_pullback_pct_list = [float(x) for x in args.min_pullback_pct.split(",")]
    if args.min_pullback_bars:
        config.min_pullback_bars_list = [int(x) for x in args.min_pullback_bars.split(",")]
    if args.volume_mult:
        config.volume_multiplier_list = [float(x) for x in args.volume_mult.split(",")]
    if args.target_r:
        config.target_r_list = [float(x) for x in args.target_r.split(",")]
    if args.time_stop_bars:
        config.time_stop_bars_list = [int(x) for x in args.time_stop_bars.split(",")]
    if args.min_gap:
        config.min_gap_pct = args.min_gap

    # Run sweep
    results = run_sweep(config)

    if results.empty:
        logger.warning("No results generated. Check data availability.")
        return

    # Generate heatmaps
    generate_heatmaps(results, config.output_dir)

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

        # Best parameter combo by Sharpe (with min 20 trades)
        min_trades_results = results_with_trades[results_with_trades["total_trades"] >= 20]
        if not min_trades_results.empty:
            best = min_trades_results.loc[min_trades_results["sharpe_ratio"].idxmax()]
            print(
                f"\nBest by Sharpe (min 20 trades): "
                f"min_pullback_pct={best['min_pullback_pct']:.3f}, "
                f"min_pullback_bars={int(best['min_pullback_bars'])}, "
                f"volume_mult={best['volume_multiplier']:.1f}, "
                f"target_r={best['target_r']:.1f}, "
                f"time_stop_bars={int(best['time_stop_bars'])}, "
                f"sharpe={best['sharpe_ratio']:.2f}, "
                f"trades={int(best['total_trades'])}"
            )

            # Top 5 combos
            print("\nTop 5 combinations by Sharpe (min 20 trades):")
            top5 = min_trades_results.nlargest(5, "sharpe_ratio")
            for i, (_, row) in enumerate(top5.iterrows(), 1):
                print(
                    f"  {i}. sharpe={row['sharpe_ratio']:.2f}, "
                    f"trades={int(row['total_trades'])}, "
                    f"win_rate={row['win_rate']:.1%}, "
                    f"pullback={row['min_pullback_pct']:.3f}, "
                    f"bars={int(row['min_pullback_bars'])}, "
                    f"vol={row['volume_multiplier']:.1f}, "
                    f"target_r={row['target_r']:.1f}, "
                    f"time_stop={int(row['time_stop_bars'])}"
                )
        else:
            print("\nNo combinations with >= 20 trades found.")
    else:
        print("No trades generated across any parameter combination.")


if __name__ == "__main__":
    main()
