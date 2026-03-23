"""VectorBT Red-to-Green parameter sweep implementation.

Gap-down reversal strategy that enters long when price reclaims a key support
level (VWAP, prior close) after a gap down.

VECTORIZED IMPLEMENTATION: Precomputes entry candidates per day, then filters
by parameters and uses vectorized exit detection. Matches the performance
pattern of vectorbt_vwap_reclaim.py.

State machine per day:
    GAP_DOWN_DETECTED -> price approaches level -> TESTING_LEVEL -> entry

Entry candidates are identified once per day (parameter-independent). Only the
filtering conditions (gap depth, level proximity, volume) vary by parameter.

Usage:
    python -m argus.backtest.vectorbt_red_to_green \
        --data-dir data/historical/1m \
        --start 2025-01-01 --end 2025-06-30 \
        --output-dir data/backtest_runs/r2g_sweeps
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
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET = 945 minutes

# Red-to-Green operates 9:45 AM - 11:00 AM ET
EARLIEST_ENTRY_MINUTES = 9 * 60 + 45  # 9:45 AM ET = 585 minutes
LATEST_ENTRY_MINUTES = 11 * 60  # 11:00 AM ET = 660 minutes


@dataclass
class R2GSweepConfig:
    """Configuration for a Red-to-Green parameter sweep."""

    data_dir: Path
    symbols: list[str]  # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (swept)
    min_gap_down_pct_list: list[float] = field(
        default_factory=lambda: [0.015, 0.02, 0.03, 0.04]
    )
    level_proximity_pct_list: list[float] = field(
        default_factory=lambda: [0.002, 0.003, 0.005]
    )
    volume_confirmation_multiplier_list: list[float] = field(
        default_factory=lambda: [1.0, 1.2, 1.5]
    )
    time_stop_minutes_list: list[int] = field(
        default_factory=lambda: [15, 20, 30]
    )

    # Fixed parameters (not swept)
    max_gap_down_pct: float = 0.10  # 10% max gap
    stop_buffer_pct: float = 0.001  # 0.1% below level
    min_level_test_bars: int = 2  # Min bars near level
    max_chase_pct: float = 0.003  # Max 0.3% above level
    target_1_r: float = 1.0
    target_2_r: float = 2.0

    # Scanner filters
    min_price: float = 5.0
    max_price: float = 200.0
    min_gap_pct_scanner: float = 2.0  # Scanner gap for qualifying days


@dataclass
class R2GSweepResult:
    """Results from a single parameter combination on a single symbol."""

    symbol: str
    min_gap_down_pct: float
    level_proximity_pct: float
    volume_confirmation_multiplier: float
    time_stop_minutes: int

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


class R2GEntryInfo(TypedDict):
    """Pre-computed entry information for a Red-to-Green candidate."""

    entry_bar_idx: int  # Index in the day's DataFrame
    entry_price: float
    entry_minutes: int  # Minutes from midnight ET
    level_price: float  # Price of the key level reclaimed
    level_type: str  # "vwap" or "prior_close"
    gap_down_pct: float  # Absolute gap percentage (positive)
    level_proximity: float  # Distance from level as fraction
    bars_at_level: int  # Bars spent near the level
    volume_ratio: float  # Entry bar volume / avg volume
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

    # Support both naming conventions:
    # - Legacy: {SYMBOL}_{YYYY-MM}.parquet (Alpaca-era data_fetcher)
    # - Current: {YYYY-MM}.parquet (HistoricalDataFeed / Databento cache)
    parquet_files = sorted(symbol_dir.glob(f"{symbol.upper()}_*.parquet"))
    if not parquet_files:
        parquet_files = sorted(symbol_dir.glob("*.parquet"))
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


def compute_gap_down_days(
    df: pd.DataFrame,
    min_price: float = 5.0,
    max_price: float = 200.0,
) -> dict[date, float]:
    """Identify trading days with gap downs and return gap percentages.

    For R2G we need gap-DOWN days (negative gap) with known prior close.

    Args:
        df: DataFrame with trading_day, open, close columns.
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.

    Returns:
        Dict mapping trading_day -> absolute gap down percentage (positive float).
    """
    daily = (
        df.groupby("trading_day")
        .agg({"open": "first", "close": "last"})
        .reset_index()
    )

    if len(daily) < 2:
        return {}

    daily["prev_close"] = daily["close"].shift(1)
    daily["gap_pct"] = (daily["open"] - daily["prev_close"]) / daily["prev_close"]

    # Gap down = negative gap_pct
    gap_downs = daily[
        (daily["gap_pct"] < 0)
        & (daily["open"] >= min_price)
        & (daily["open"] <= max_price)
        & (~daily["prev_close"].isna())
    ]

    return {
        row["trading_day"]: abs(row["gap_pct"])
        for _, row in gap_downs.iterrows()
    }


def _compute_vwap_vectorized(
    high: np.ndarray, low: np.ndarray, close: np.ndarray, volume: np.ndarray
) -> np.ndarray:
    """Compute VWAP using vectorized cumsum operations.

    VWAP = cumsum(TP x volume) / cumsum(volume)
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
    with np.errstate(divide="ignore", invalid="ignore"):
        vwap = cum_tp_vol / cum_vol
        vwap[cum_vol == 0] = np.nan
    return vwap


def _precompute_r2g_entries_for_day(
    day_df: pd.DataFrame,
    prev_close: float,
    max_gap_down_pct: float,
    stop_buffer_pct: float,
    max_chase_pct: float,
) -> list[R2GEntryInfo]:
    """Precompute all potential R2G entries for a single day.

    Identifies points where price reclaims a key level (VWAP or prior close)
    after a gap down. Captures state for later filtering by parameter combo.

    This function is called ONCE per day, not per parameter combination.

    Args:
        day_df: DataFrame with bar data for one trading day.
        prev_close: Previous day's closing price.
        max_gap_down_pct: Maximum gap down (entries beyond this excluded).
        stop_buffer_pct: Buffer below level for stop price.
        max_chase_pct: Max distance above level for entry.

    Returns:
        List of R2GEntryInfo dicts (typically 0-2 per day).
    """
    if len(day_df) < 5:
        return []

    # Extract arrays
    high = day_df["high"].to_numpy()
    low = day_df["low"].to_numpy()
    close = day_df["close"].to_numpy()
    volume = day_df["volume"].to_numpy()
    minutes = day_df["minutes_from_midnight"].to_numpy()

    # Check gap down
    day_open = float(day_df.iloc[0]["open"])
    gap_pct = (day_open - prev_close) / prev_close
    abs_gap = abs(gap_pct)

    if gap_pct >= 0:
        return []  # Not a gap down
    if abs_gap > max_gap_down_pct:
        return []  # Gap too large

    # Compute VWAP
    vwap = _compute_vwap_vectorized(high, low, close, volume)

    # Cumulative average volume for volume ratio
    cum_volume = np.cumsum(volume)
    bar_counts = np.arange(1, len(volume) + 1)
    avg_volume = cum_volume / bar_counts

    # Key levels to test: VWAP (dynamic) and prior close (static)
    entries: list[R2GEntryInfo] = []

    # Track whether we've already found an entry for each level type
    entered_level_types: set[str] = set()

    # State tracking for level testing
    bars_near_vwap = 0
    bars_near_prior_close = 0

    for i in range(len(close)):
        bar_minutes = int(minutes[i])
        bar_close = float(close[i])
        bar_volume = float(volume[i])
        bar_vwap = float(vwap[i]) if not np.isnan(vwap[i]) else 0.0

        # Only consider entries in the operating window
        if bar_minutes < EARLIEST_ENTRY_MINUTES or bar_minutes >= LATEST_ENTRY_MINUTES:
            # Still track proximity for bars_at_level even outside window
            if bar_vwap > 0:
                vwap_dist = abs(bar_close - bar_vwap) / bar_vwap
                if vwap_dist <= 0.01:  # Generous proximity for tracking
                    bars_near_vwap += 1
                else:
                    bars_near_vwap = 0
            if prev_close > 0:
                pc_dist = abs(bar_close - prev_close) / prev_close
                if pc_dist <= 0.01:
                    bars_near_prior_close += 1
                else:
                    bars_near_prior_close = 0
            continue

        vol_ratio = bar_volume / avg_volume[i] if avg_volume[i] > 0 else 0.0

        # --- Check VWAP reclaim ---
        if "vwap" not in entered_level_types and bar_vwap > 0:
            vwap_proximity = abs(bar_close - bar_vwap) / bar_vwap
            if vwap_proximity <= 0.01:
                bars_near_vwap += 1
            else:
                bars_near_vwap = 0

            # Entry: close above VWAP, not too far (chase), positive risk
            if bar_close > bar_vwap:
                chase_dist = (bar_close - bar_vwap) / bar_vwap
                if chase_dist <= max_chase_pct:
                    stop_price = bar_vwap * (1 - stop_buffer_pct)
                    risk = bar_close - stop_price
                    if risk > 0 and i + 1 < len(close):
                        entries.append(R2GEntryInfo(
                            entry_bar_idx=i,
                            entry_price=bar_close,
                            entry_minutes=bar_minutes,
                            level_price=bar_vwap,
                            level_type="vwap",
                            gap_down_pct=abs_gap,
                            level_proximity=vwap_proximity,
                            bars_at_level=bars_near_vwap,
                            volume_ratio=vol_ratio,
                            highs=high[i + 1:].copy(),
                            lows=low[i + 1:].copy(),
                            closes=close[i + 1:].copy(),
                            minutes=minutes[i + 1:].copy(),
                        ))
                        entered_level_types.add("vwap")

        # --- Check prior close reclaim ---
        if "prior_close" not in entered_level_types and prev_close > 0:
            pc_proximity = abs(bar_close - prev_close) / prev_close
            if pc_proximity <= 0.01:
                bars_near_prior_close += 1
            else:
                bars_near_prior_close = 0

            if bar_close > prev_close:
                chase_dist = (bar_close - prev_close) / prev_close
                if chase_dist <= max_chase_pct:
                    stop_price = prev_close * (1 - stop_buffer_pct)
                    risk = bar_close - stop_price
                    if risk > 0 and i + 1 < len(close):
                        entries.append(R2GEntryInfo(
                            entry_bar_idx=i,
                            entry_price=bar_close,
                            entry_minutes=bar_minutes,
                            level_price=prev_close,
                            level_type="prior_close",
                            gap_down_pct=abs_gap,
                            level_proximity=pc_proximity,
                            bars_at_level=bars_near_prior_close,
                            volume_ratio=vol_ratio,
                            highs=high[i + 1:].copy(),
                            lows=low[i + 1:].copy(),
                            closes=close[i + 1:].copy(),
                            minutes=minutes[i + 1:].copy(),
                        ))
                        entered_level_types.add("prior_close")

        # Stop after finding entries for both levels (one trade per day typically)
        if len(entered_level_types) >= 2:
            break

    return entries


def _find_exit_vectorized(
    post_entry_highs: np.ndarray,
    post_entry_lows: np.ndarray,
    post_entry_closes: np.ndarray,
    post_entry_minutes: np.ndarray,
    entry_price: float,
    stop_price: float,
    target_price: float,
    time_stop_bars: int,
) -> dict[str, Any] | None:
    """Find exit using vectorized operations.

    Exit priority (worst-case for longs):
    1. Stop loss - uses stop price
    2. Target - uses target price
    3. Time stop - uses close, but check if stop also hit
    4. EOD - uses close, but check if stop also hit

    Args:
        post_entry_highs: Array of high prices after entry.
        post_entry_lows: Array of low prices after entry.
        post_entry_closes: Array of close prices after entry.
        post_entry_minutes: Array of minutes_from_midnight after entry.
        entry_price: The entry price.
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
    bars_held = np.arange(1, n + 1)
    time_stop_hit = bars_held >= time_stop_bars
    eod_hit = post_entry_minutes >= EOD_FLATTEN_MINUTES

    # Find first bar index for each condition (n = not found sentinel)
    stop_idx = int(np.argmax(stop_hit)) if stop_hit.any() else n
    target_idx = int(np.argmax(target_hit)) if target_hit.any() else n
    time_idx = int(np.argmax(time_stop_hit)) if time_stop_hit.any() else n
    eod_idx = int(np.argmax(eod_hit)) if eod_hit.any() else n

    exit_idx = min(stop_idx, target_idx, time_idx, eod_idx)

    if exit_idx >= n:
        # No exit found, use last bar
        exit_idx = n - 1
        reason = "eod"
        exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == eod_idx and eod_hit[exit_idx]:
        if stop_idx == exit_idx and stop_hit[exit_idx]:
            reason = "stop"
            exit_price = stop_price
        else:
            reason = "eod"
            exit_price = float(post_entry_closes[exit_idx])
    elif exit_idx == time_idx and time_stop_hit[exit_idx]:
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

    hold_bars = exit_idx + 1
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
    config: R2GSweepConfig,
) -> list[R2GSweepResult]:
    """Run parameter sweep for a single symbol (VECTORIZED VERSION).

    Architecture:
    1. Pre-group data by day ONCE
    2. Pre-compute gap-down days with prior close ONCE
    3. Pre-compute ALL potential R2G entries per day ONCE (parameter-independent)
    4. Filter entries by (min_gap_down_pct, level_proximity_pct, volume) at runtime
    5. Compute exits vectorized for each time_stop_minutes combination

    Args:
        df: DataFrame with all bar data for the symbol.
        symbol: Ticker symbol.
        config: Sweep configuration with parameter ranges.

    Returns:
        List of R2GSweepResult objects (one per parameter combination).
    """
    results: list[R2GSweepResult] = []

    # Pre-group bars by day ONCE
    day_groups: dict[date, pd.DataFrame] = {
        day: group.reset_index(drop=True)
        for day, group in df.groupby("trading_day")  # type: ignore[misc]
    }

    # Compute gap-down days with prior close
    gap_down_days = compute_gap_down_days(df, config.min_price, config.max_price)
    valid_days_count = len(gap_down_days)

    # Get prior close for each gap-down day
    daily = (
        df.groupby("trading_day")
        .agg({"close": "last"})
        .reset_index()
        .sort_values("trading_day")
    )
    prev_close_map: dict[date, float] = {}
    for idx in range(1, len(daily)):
        day = daily.iloc[idx]["trading_day"]
        if day in gap_down_days:
            prev_close_map[day] = float(daily.iloc[idx - 1]["close"])

    # Pre-compute ALL potential R2G entries for each gap-down day ONCE
    all_day_entries: dict[date, list[R2GEntryInfo]] = {}
    for day, abs_gap in gap_down_days.items():
        day_df = day_groups.get(day)
        prev_close = prev_close_map.get(day)
        if day_df is None or day_df.empty or prev_close is None:
            continue
        entries = _precompute_r2g_entries_for_day(
            day_df,
            prev_close,
            config.max_gap_down_pct,
            config.stop_buffer_pct,
            config.max_chase_pct,
        )
        if entries:
            all_day_entries[day] = entries

    if not all_day_entries:
        for params in product(
            config.min_gap_down_pct_list,
            config.level_proximity_pct_list,
            config.volume_confirmation_multiplier_list,
            config.time_stop_minutes_list,
        ):
            results.append(
                _empty_r2g_result(symbol, *params, qualifying_days=valid_days_count)
            )
        return results

    # Flatten all entries across days
    all_entries: list[tuple[date, R2GEntryInfo]] = [
        (day, entry)
        for day, entries in all_day_entries.items()
        for entry in entries
    ]

    # Nested parameter loop - entry detection already done
    for min_gap_down_pct in config.min_gap_down_pct_list:
        for level_proximity_pct in config.level_proximity_pct_list:
            for volume_mult in config.volume_confirmation_multiplier_list:
                # Filter entries by these three parameters ONCE
                filtered_entries = [
                    (day, entry) for day, entry in all_entries
                    if (entry["gap_down_pct"] >= min_gap_down_pct
                        and entry["level_proximity"] <= level_proximity_pct
                        and entry["bars_at_level"] >= config.min_level_test_bars
                        and entry["volume_ratio"] >= volume_mult)
                ]

                for time_stop_minutes in config.time_stop_minutes_list:
                    if not filtered_entries:
                        results.append(
                            _empty_r2g_result(
                                symbol,
                                min_gap_down_pct,
                                level_proximity_pct,
                                volume_mult,
                                time_stop_minutes,
                                valid_days_count,
                            )
                        )
                        continue

                    # Compute trades using vectorized exit detection
                    trades: list[dict[str, Any]] = []
                    # One trade per day maximum
                    days_traded: set[date] = set()
                    for day, entry in filtered_entries:
                        if day in days_traded:
                            continue
                        level_price = entry["level_price"]
                        stop_price = level_price * (1 - config.stop_buffer_pct)
                        risk = entry["entry_price"] - stop_price
                        if risk <= 0:
                            continue
                        # Use T1 as primary target for sweep
                        target_price = entry["entry_price"] + risk * config.target_1_r

                        trade = _find_exit_vectorized(
                            entry["highs"],
                            entry["lows"],
                            entry["closes"],
                            entry["minutes"],
                            entry["entry_price"],
                            stop_price,
                            target_price,
                            time_stop_minutes,  # 1 bar = 1 minute
                        )
                        if trade is not None:
                            trades.append(trade)
                            days_traded.add(day)

                    result = _compute_r2g_result(
                        symbol,
                        min_gap_down_pct,
                        level_proximity_pct,
                        volume_mult,
                        time_stop_minutes,
                        trades,
                        valid_days_count,
                    )
                    results.append(result)

    return results


def _empty_r2g_result(
    symbol: str,
    min_gap_down_pct: float,
    level_proximity_pct: float,
    volume_confirmation_multiplier: float,
    time_stop_minutes: int,
    qualifying_days: int,
) -> R2GSweepResult:
    """Create an empty result for parameter combinations with no trades."""
    return R2GSweepResult(
        symbol=symbol,
        min_gap_down_pct=min_gap_down_pct,
        level_proximity_pct=level_proximity_pct,
        volume_confirmation_multiplier=volume_confirmation_multiplier,
        time_stop_minutes=time_stop_minutes,
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


def _compute_r2g_result(
    symbol: str,
    min_gap_down_pct: float,
    level_proximity_pct: float,
    volume_confirmation_multiplier: float,
    time_stop_minutes: int,
    trades: list[dict[str, Any]],
    qualifying_days: int,
) -> R2GSweepResult:
    """Compute metrics from a list of trades."""
    if not trades:
        return _empty_r2g_result(
            symbol,
            min_gap_down_pct,
            level_proximity_pct,
            volume_confirmation_multiplier,
            time_stop_minutes,
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

    max_dd_pct = _compute_max_drawdown_pct(equity)
    sharpe = _compute_sharpe_from_r_multiples(r_multiples)

    return R2GSweepResult(
        symbol=symbol,
        min_gap_down_pct=min_gap_down_pct,
        level_proximity_pct=level_proximity_pct,
        volume_confirmation_multiplier=volume_confirmation_multiplier,
        time_stop_minutes=time_stop_minutes,
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


def run_sweep(config: R2GSweepConfig) -> pd.DataFrame:
    """Run parameter sweep for all symbols.

    Args:
        config: Sweep configuration.

    Returns:
        DataFrame with all R2GSweepResult data.
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

    logger.info("Starting R2G sweep for %d symbols", len(symbols))

    total_combos = (
        len(config.min_gap_down_pct_list)
        * len(config.level_proximity_pct_list)
        * len(config.volume_confirmation_multiplier_list)
        * len(config.time_stop_minutes_list)
    )
    logger.info("Parameter combinations: %d", total_combos)

    all_results: list[R2GSweepResult] = []

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
            symbol_path = config.output_dir / f"r2g_sweep_{symbol}.parquet"
            symbol_df.to_parquet(symbol_path, index=False)
            logger.debug("Saved %d results to %s", len(symbol_results), symbol_path)

    if not all_results:
        logger.warning("No results generated from sweep")
        return pd.DataFrame()

    results_df = pd.DataFrame([vars(r) for r in all_results])

    # Save cross-symbol summary
    summary_path = config.output_dir / "r2g_sweep_summary.parquet"
    results_df.to_parquet(summary_path, index=False)
    logger.info("Saved summary with %d results to %s", len(results_df), summary_path)

    csv_path = config.output_dir / "r2g_sweep_summary.csv"
    results_df.to_csv(csv_path, index=False)
    logger.info("Saved CSV summary to %s", csv_path)

    return results_df


def generate_report(results_df: pd.DataFrame) -> dict[str, Any]:
    """Generate a summary report from sweep results.

    Args:
        results_df: DataFrame with sweep results.

    Returns:
        Dict with summary statistics for config/close-out.
    """
    if results_df.empty:
        return {
            "status": "no_data",
            "total_trades": 0,
            "best_params": {},
            "data_months": 0,
        }

    # Aggregate across symbols
    param_cols = [
        "min_gap_down_pct",
        "level_proximity_pct",
        "volume_confirmation_multiplier",
        "time_stop_minutes",
    ]

    aggregated = (
        results_df.groupby(param_cols)
        .agg(
            total_trades=("total_trades", "sum"),
            sharpe_ratio=("sharpe_ratio", "mean"),
            win_rate=("win_rate", "mean"),
            profit_factor=("profit_factor", "mean"),
            total_return_pct=("total_return_pct", "sum"),
            max_drawdown_pct=("max_drawdown_pct", "max"),
        )
        .reset_index()
    )

    # Filter to combos with trades
    with_trades = aggregated[aggregated["total_trades"] > 0]

    if with_trades.empty:
        return {
            "status": "no_trades",
            "total_trades": 0,
            "best_params": {},
            "data_months": 0,
        }

    # Best by Sharpe
    best_idx = with_trades["sharpe_ratio"].idxmax()
    best_row = with_trades.loc[best_idx]  # type: ignore[call-overload]

    best_params = {col: best_row[col] for col in param_cols}

    return {
        "status": "validated",
        "total_trades": int(best_row["total_trades"]),  # type: ignore[arg-type]
        "sharpe_ratio": round(float(best_row["sharpe_ratio"]), 3),  # type: ignore[arg-type]
        "win_rate": round(float(best_row["win_rate"]), 3),  # type: ignore[arg-type]
        "profit_factor": round(float(best_row["profit_factor"]), 3),  # type: ignore[arg-type]
        "max_drawdown_pct": round(float(best_row["max_drawdown_pct"]), 3),  # type: ignore[arg-type]
        "best_params": best_params,
        "param_combos_tested": len(aggregated),
        "combos_with_trades": len(with_trades),
    }


def main() -> None:
    """CLI entry point for the Red-to-Green VectorBT sweep."""
    parser = argparse.ArgumentParser(
        description="Run Red-to-Green VectorBT parameter sweep.",
        prog="python -m argus.backtest.vectorbt_red_to_green",
    )
    parser.add_argument("--data-dir", type=str, default="data/historical/1m")
    parser.add_argument("--symbols", type=str, default=None)
    parser.add_argument("--start", type=str, required=True)
    parser.add_argument("--end", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="data/backtest_runs/r2g_sweeps")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    symbols = [s.strip().upper() for s in args.symbols.split(",")] if args.symbols else []
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    config = R2GSweepConfig(
        data_dir=Path(args.data_dir),
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        output_dir=Path(args.output_dir),
    )

    results_df = run_sweep(config)
    report = generate_report(results_df)

    print("\n" + "=" * 60)
    print("Red-to-Green VectorBT Sweep Report")
    print("=" * 60)
    for key, value in report.items():
        print(f"  {key}: {value}")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
