"""VectorBT Afternoon Momentum parameter sweep implementation.

Consolidation breakout strategy that identifies stocks consolidating during
midday (12:00–2:00 PM) and enters on breakouts after 2:00 PM ET.

VECTORIZED IMPLEMENTATION: Precomputes entry candidates per day, then filters
by parameters and uses vectorized exit detection. Matches the performance
pattern of vectorbt_orb.py and vectorbt_vwap_reclaim.py.

Entry logic:
1. During consolidation window (12:00–2:00 PM), track midday range
2. Confirm consolidation: range < consolidation_atr_ratio * ATR-14
3. After 2:00 PM, enter on close above consolidation_high with volume

Operates 2:00 PM – 3:30 PM ET (entry window), force close at 3:45 PM.

DEC-152: Afternoon Momentum strategy — consolidation breakout entry.
DEC-149: VectorBT sweeps must use precompute + vectorize architecture.

Usage:
    python -m argus.backtest.vectorbt_afternoon_momentum \
        --data-dir data/historical/1m \
        --start 2025-01-01 --end 2025-06-30 \
        --output-dir data/backtest_runs/afternoon_sweeps
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Eastern timezone for market hours
ET = ZoneInfo("America/New_York")

# Market hours constants (in minutes from midnight ET)
MARKET_OPEN_MINUTES = 9 * 60 + 30  # 9:30 AM ET = 570 minutes

# Afternoon Momentum time windows (in minutes from midnight ET)
CONSOLIDATION_START_MINUTES = 12 * 60  # 12:00 PM = 720
CONSOLIDATION_END_MINUTES = 14 * 60  # 2:00 PM = 840
EARLIEST_ENTRY_MINUTES = 14 * 60  # 2:00 PM = 840
LATEST_ENTRY_MINUTES = 15 * 60 + 30  # 3:30 PM = 930
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM = 945


@dataclass
class AfternoonSweepConfig:
    """Configuration for an Afternoon Momentum parameter sweep."""

    data_dir: Path
    symbols: list[str]  # Empty = all symbols in data_dir
    start_date: date
    end_date: date
    output_dir: Path

    # Parameter ranges (swept)
    consolidation_atr_ratio_list: list[float] = field(
        default_factory=lambda: [0.5, 0.75, 1.0, 1.5]
    )
    min_consolidation_bars_list: list[int] = field(
        default_factory=lambda: [15, 30, 45, 60]
    )
    volume_multiplier_list: list[float] = field(
        default_factory=lambda: [1.0, 1.2, 1.5]
    )
    target_r_list: list[float] = field(
        default_factory=lambda: [1.0, 1.5, 2.0, 3.0]
    )
    time_stop_bars_list: list[int] = field(
        default_factory=lambda: [15, 30, 45, 60]
    )

    # Fixed parameters (not swept)
    max_chase_pct: float = 0.005  # 0.5% max above consolidation_high
    stop_buffer_pct: float = 0.001  # 0.1% below consolidation_low
    min_gap_pct: float = 2.0  # 2% gap minimum

    # Scanner filters
    min_price: float = 5.0
    max_price: float = 10000.0


@dataclass
class AfternoonSweepResult:
    """Results from a single parameter combination on a single symbol."""

    symbol: str
    consolidation_atr_ratio: float
    min_consolidation_bars: int
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


class AfternoonEntryInfo(TypedDict):
    """Pre-computed entry information for an afternoon breakout candidate."""

    entry_bar_idx: int  # Index in the day's DataFrame
    entry_price: float
    entry_minutes: int  # Minutes from midnight ET
    consolidation_high: float  # Midday high BEFORE the breakout bar
    consolidation_low: float  # Midday low (for stop placement)
    consolidation_ratio: float  # midday_range / ATR
    consolidation_bars: int  # Number of bars in consolidation window
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


def _compute_atr_for_day(day_df: pd.DataFrame) -> float | None:
    """Compute ATR-14 from morning+midday bars (9:30 AM–2:00 PM).

    Uses true range calculation on 1-minute bars and returns the ATR value
    that would be available at 2:00 PM (when breakout checking starts).

    This is a simplified ATR computation using intraday bars only.
    For a more accurate approach, we'd want daily ATR from prior days,
    but this provides reasonable approximation for the parameter sweep.

    Args:
        day_df: DataFrame with bar data for one trading day.

    Returns:
        ATR-14 value at 2:00 PM, or None if insufficient data.
    """
    # Filter to bars before 2:00 PM (used for ATR computation)
    pre_breakout_bars = day_df[
        day_df["minutes_from_midnight"] < CONSOLIDATION_END_MINUTES
    ]

    if len(pre_breakout_bars) < 14:
        return None

    high = pre_breakout_bars["high"].to_numpy()
    low = pre_breakout_bars["low"].to_numpy()
    close = pre_breakout_bars["close"].to_numpy()

    # Compute True Range for each bar
    # TR = max(high - low, |high - prev_close|, |low - prev_close|)
    prev_close = np.roll(close, 1)
    prev_close[0] = close[0]  # First bar uses its own close

    tr1 = high - low
    tr2 = np.abs(high - prev_close)
    tr3 = np.abs(low - prev_close)
    true_range = np.maximum(tr1, np.maximum(tr2, tr3))

    # ATR is the simple moving average of the last 14 true ranges
    if len(true_range) < 14:
        return None

    atr = float(np.mean(true_range[-14:]))
    return atr if atr > 0 else None


def _precompute_afternoon_entries_for_day(
    day_df: pd.DataFrame,
    atr_value: float,
    max_chase_pct: float,
    stop_buffer_pct: float,
) -> list[AfternoonEntryInfo]:
    """Precompute all potential afternoon breakout entries for a single day.

    Identifies the first breakout above the midday consolidation high after
    2:00 PM, capturing the consolidation metrics for later parameter filtering.

    This function is called ONCE per day, not per parameter combination.
    The consolidation_ratio and consolidation_bars are stored with the entry
    so they can be filtered at runtime by different parameter values.

    IMPORTANT: Uses the consolidation_high value from BEFORE the breakout bar
    for the breakout check, matching the live strategy behavior (DEC-XXX).

    Args:
        day_df: DataFrame with bar data for one trading day.
        atr_value: ATR-14 value at 2:00 PM.
        max_chase_pct: Max distance above consolidation_high for entry.
        stop_buffer_pct: Buffer below consolidation_low for stop.

    Returns:
        List of AfternoonEntryInfo dicts (typically 0-1 per day).
    """
    if len(day_df) < 10:  # Need enough bars for meaningful consolidation
        return []

    minutes = day_df["minutes_from_midnight"].to_numpy()
    high = day_df["high"].to_numpy()
    low = day_df["low"].to_numpy()
    close = day_df["close"].to_numpy()
    volume = day_df["volume"].to_numpy()

    # Extract midday consolidation bars (12:00 PM - 2:00 PM)
    consolidation_mask = (minutes >= CONSOLIDATION_START_MINUTES) & (
        minutes < CONSOLIDATION_END_MINUTES
    )

    if not consolidation_mask.any():
        return []

    consolidation_highs = high[consolidation_mask]
    consolidation_lows = low[consolidation_mask]

    if len(consolidation_highs) == 0:
        return []

    # Consolidation metrics at 2:00 PM (before any breakout checking)
    midday_high = float(np.max(consolidation_highs))
    midday_low = float(np.min(consolidation_lows))
    midday_range = midday_high - midday_low
    consolidation_bars = int(np.sum(consolidation_mask))

    consolidation_ratio = midday_range / atr_value

    # Extract afternoon bars (2:00 PM - 3:30 PM)
    afternoon_mask = (minutes >= EARLIEST_ENTRY_MINUTES) & (
        minutes < LATEST_ENTRY_MINUTES
    )

    if not afternoon_mask.any():
        return []

    afternoon_indices = np.where(afternoon_mask)[0]
    afternoon_closes = close[afternoon_mask]
    afternoon_highs = high[afternoon_mask]
    afternoon_lows = low[afternoon_mask]
    afternoon_volumes = volume[afternoon_mask]
    afternoon_minutes = minutes[afternoon_mask]

    # Track running consolidation high as we scan through afternoon bars
    # The breakout must be above the consolidation_high BEFORE that bar
    # This tracks cumulative high up to and including each afternoon bar
    running_consolidation_high = midday_high

    entries: list[AfternoonEntryInfo] = []

    for i, (idx, bar_close, bar_high, bar_volume, bar_minutes) in enumerate(
        zip(
            afternoon_indices,
            afternoon_closes,
            afternoon_highs,
            afternoon_volumes,
            afternoon_minutes,
        )
    ):
        # The consolidation_high used for breakout check is the high BEFORE this bar
        consolidation_high_before_bar = running_consolidation_high

        # Check for breakout: close > consolidation_high (value before this bar)
        if bar_close > consolidation_high_before_bar:
            # Chase protection: not too far above consolidation_high
            chase_limit = consolidation_high_before_bar * (1 + max_chase_pct)
            if bar_close > chase_limit:
                # Update running high and continue (may find later entry)
                running_consolidation_high = max(running_consolidation_high, bar_high)
                continue

            # Check risk > 0 (valid stop placement)
            stop_price = midday_low * (1 - stop_buffer_pct)
            risk = bar_close - stop_price
            if risk <= 0:
                running_consolidation_high = max(running_consolidation_high, bar_high)
                continue

            # Compute volume ratio
            # Use all bars up to and including this bar for average
            cum_volume = np.sum(volume[: idx + 1])
            bar_count = idx + 1
            avg_volume = cum_volume / bar_count if bar_count > 0 else 1.0
            volume_ratio = float(bar_volume / avg_volume) if avg_volume > 0 else 0.0

            # Extract post-entry bars as NumPy arrays
            post_entry_mask = np.arange(len(minutes)) > idx

            if not post_entry_mask.any():
                # No bars after entry (edge case near EOD)
                running_consolidation_high = max(running_consolidation_high, bar_high)
                continue

            entry_info = AfternoonEntryInfo(
                entry_bar_idx=int(idx),
                entry_price=float(bar_close),
                entry_minutes=int(bar_minutes),
                consolidation_high=consolidation_high_before_bar,
                consolidation_low=midday_low,
                consolidation_ratio=consolidation_ratio,
                consolidation_bars=consolidation_bars,
                volume_ratio=volume_ratio,
                highs=high[post_entry_mask].copy(),
                lows=low[post_entry_mask].copy(),
                closes=close[post_entry_mask].copy(),
                minutes=minutes[post_entry_mask].copy(),
            )
            entries.append(entry_info)

            # Single entry per day for sweep (matches live strategy behavior)
            break

        # Update running high to include this bar for next iteration
        running_consolidation_high = max(running_consolidation_high, bar_high)

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

    Exit priority (worst-case-for-longs):
    1. Stop loss — always uses stop price (worst case)
    2. Target — uses target price
    3. Time stop — uses close, BUT check if stop also hit (use stop price if so)
    4. EOD — uses close, BUT check if stop also hit (use stop price if so)

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


def _empty_afternoon_result(
    symbol: str,
    consolidation_atr_ratio: float,
    min_consolidation_bars: int,
    volume_multiplier: float,
    target_r: float,
    time_stop_bars: int,
    qualifying_days: int,
) -> AfternoonSweepResult:
    """Create an empty result for parameter combinations with no trades."""
    return AfternoonSweepResult(
        symbol=symbol,
        consolidation_atr_ratio=consolidation_atr_ratio,
        min_consolidation_bars=min_consolidation_bars,
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


def _compute_afternoon_result(
    symbol: str,
    consolidation_atr_ratio: float,
    min_consolidation_bars: int,
    volume_multiplier: float,
    target_r: float,
    time_stop_bars: int,
    trades: list[dict],
    qualifying_days: int,
) -> AfternoonSweepResult:
    """Compute metrics from a list of trades."""
    if not trades:
        return _empty_afternoon_result(
            symbol,
            consolidation_atr_ratio,
            min_consolidation_bars,
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

    return AfternoonSweepResult(
        symbol=symbol,
        consolidation_atr_ratio=consolidation_atr_ratio,
        min_consolidation_bars=min_consolidation_bars,
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
