"""VectorBT VWAP Reclaim parameter sweep implementation.

Mean-reversion strategy that buys stocks reclaiming VWAP after a pullback.
This sweep iterates per symbol-day due to the inherently sequential state machine.

State machine:
    WATCHING → ABOVE_VWAP → BELOW_VWAP → entry (or EXHAUSTED)

Key difference from ORB sweeps: The state machine (above → below → reclaim) is
inherently sequential per symbol-day, so we iterate per day rather than trying
to fully vectorize. With 768 parameter combinations, this is computationally tractable.

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
from enum import StrEnum
from itertools import product
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# Market hours constants (in minutes from midnight ET)
MARKET_OPEN_MINUTES = 9 * 60 + 30  # 9:30 AM ET = 570 minutes
EOD_FLATTEN_MINUTES = 15 * 60 + 45  # 3:45 PM ET = 945 minutes

# VWAP Reclaim operates 10:00 AM – 12:00 PM ET
EARLIEST_ENTRY_MINUTES = 10 * 60  # 10:00 AM ET = 600 minutes
LATEST_ENTRY_MINUTES = 12 * 60  # 12:00 PM ET = 720 minutes


class VwapState(StrEnum):
    """State machine states for VWAP Reclaim tracking."""

    WATCHING = "watching"
    ABOVE_VWAP = "above_vwap"
    BELOW_VWAP = "below_vwap"
    ENTERED = "entered"
    EXHAUSTED = "exhausted"


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


class TradeResult(TypedDict):
    """Result from simulating a single trade."""

    entry_price: float
    exit_price: float
    risk: float
    pnl: float
    r_multiple: float
    hold_bars: int
    exit_reason: str


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
    from zoneinfo import ZoneInfo

    et_tz = ZoneInfo("America/New_York")

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
    df["timestamp_et"] = df["timestamp"].dt.tz_convert(et_tz)

    # Filter by date range
    df["trading_day"] = df["timestamp_et"].dt.date
    df = df[(df["trading_day"] >= start_date) & (df["trading_day"] <= end_date)].copy()

    if df.empty:
        return pd.DataFrame()

    # Compute minutes from midnight (for time comparisons)
    df["minutes_from_midnight"] = df["timestamp_et"].apply(
        lambda ts: ts.hour * 60 + ts.minute
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


def compute_day_vwap(day_df: pd.DataFrame) -> pd.Series:
    """Compute VWAP for a single trading day.

    VWAP = cumsum(TP × volume) / cumsum(volume)
    where TP = (high + low + close) / 3

    Args:
        day_df: DataFrame with high, low, close, volume columns.

    Returns:
        Series of VWAP values indexed to match day_df.
    """
    tp = (day_df["high"] + day_df["low"] + day_df["close"]) / 3
    cum_tp_vol = (tp * day_df["volume"]).cumsum()
    cum_vol = day_df["volume"].cumsum()
    return cum_tp_vol / cum_vol.replace(0, np.nan)


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


def simulate_trade_exit(
    day_df: pd.DataFrame,
    entry_bar_idx: int,
    entry_price: float,
    stop_price: float,
    target_price: float,
    time_stop_bars: int,
) -> TradeResult | None:
    """Simulate trade exit given entry point.

    Checks stop, target, time stop, and EOD flatten.

    Args:
        day_df: DataFrame with bar data for the day.
        entry_bar_idx: Index (in day_df) of entry bar.
        entry_price: Entry price.
        stop_price: Stop loss price.
        target_price: Target price.
        time_stop_bars: Bars until time stop triggers.

    Returns:
        TradeResult dict or None if no valid exit found.
    """
    # Get bars after entry
    post_entry = day_df.iloc[entry_bar_idx + 1 :]

    if post_entry.empty:
        return None

    risk = entry_price - stop_price
    if risk <= 0:
        return None

    # Walk forward through bars
    bars_held = 0
    for _idx, row in post_entry.iterrows():
        bars_held += 1

        # Check stop (hit if low <= stop_price)
        if row["low"] <= stop_price:
            pnl = stop_price - entry_price
            return TradeResult(
                entry_price=entry_price,
                exit_price=stop_price,
                risk=risk,
                pnl=pnl,
                r_multiple=pnl / risk,
                hold_bars=bars_held,
                exit_reason="stop",
            )

        # Check target (hit if high >= target_price)
        if row["high"] >= target_price:
            pnl = target_price - entry_price
            return TradeResult(
                entry_price=entry_price,
                exit_price=target_price,
                risk=risk,
                pnl=pnl,
                r_multiple=pnl / risk,
                hold_bars=bars_held,
                exit_reason="target",
            )

        # Check time stop
        if bars_held >= time_stop_bars:
            exit_price = float(row["close"])
            pnl = exit_price - entry_price
            return TradeResult(
                entry_price=entry_price,
                exit_price=exit_price,
                risk=risk,
                pnl=pnl,
                r_multiple=pnl / risk,
                hold_bars=bars_held,
                exit_reason="time_stop",
            )

        # Check EOD flatten (at 3:45 PM bar)
        if row["minutes_from_midnight"] >= EOD_FLATTEN_MINUTES:
            exit_price = float(row["close"])
            pnl = exit_price - entry_price
            return TradeResult(
                entry_price=entry_price,
                exit_price=exit_price,
                risk=risk,
                pnl=pnl,
                r_multiple=pnl / risk,
                hold_bars=bars_held,
                exit_reason="eod",
            )

    # If we reach end of data, exit at last close
    last_row = post_entry.iloc[-1]
    exit_price = float(last_row["close"])
    pnl = exit_price - entry_price
    return TradeResult(
        entry_price=entry_price,
        exit_price=exit_price,
        risk=risk,
        pnl=pnl,
        r_multiple=pnl / risk,
        hold_bars=bars_held,
        exit_reason="eod",
    )


def simulate_vwap_reclaim_day(
    day_df: pd.DataFrame,
    vwap: pd.Series,
    min_pullback_pct: float,
    max_pullback_pct: float,
    min_pullback_bars: int,
    volume_multiplier: float,
    max_chase_above_vwap_pct: float,
    stop_buffer_pct: float,
    target_r: float,
    time_stop_bars: int,
) -> list[TradeResult]:
    """Simulate VWAP Reclaim state machine for a single day.

    State machine:
        WATCHING: Initial, looking for price above VWAP
        ABOVE_VWAP: Price is above VWAP
        BELOW_VWAP: Price pulled below VWAP, tracking pullback
        ENTERED: Position taken (terminal)
        EXHAUSTED: Pullback too deep (terminal)

    Args:
        day_df: DataFrame with bar data for one trading day.
        vwap: Series of VWAP values aligned to day_df.
        min_pullback_pct: Minimum pullback depth required.
        max_pullback_pct: Maximum pullback depth (EXHAUSTED if exceeded).
        min_pullback_bars: Minimum bars below VWAP.
        volume_multiplier: Required volume vs average for reclaim.
        max_chase_above_vwap_pct: Max distance above VWAP for entry.
        stop_buffer_pct: Buffer below pullback low for stop.
        target_r: Target as R-multiple.
        time_stop_bars: Bars until time stop.

    Returns:
        List of TradeResult dicts (usually 0 or 1 trade per day).
    """
    trades: list[TradeResult] = []

    state = VwapState.WATCHING
    pullback_low: float | None = None
    bars_below = 0
    volumes: list[float] = []

    for i, (_idx, row) in enumerate(day_df.iterrows()):
        close = row["close"]
        low = row["low"]
        volume = row["volume"]
        bar_vwap = vwap.iloc[i]
        minutes = row["minutes_from_midnight"]

        volumes.append(volume)

        # Skip if VWAP not available (first bar edge case)
        if pd.isna(bar_vwap) or bar_vwap <= 0:
            continue

        # Terminal states
        if state in (VwapState.ENTERED, VwapState.EXHAUSTED):
            break

        if state == VwapState.WATCHING:
            if close > bar_vwap:
                state = VwapState.ABOVE_VWAP

        elif state == VwapState.ABOVE_VWAP:
            if close < bar_vwap:
                state = VwapState.BELOW_VWAP
                pullback_low = low
                bars_below = 1

        elif state == VwapState.BELOW_VWAP:
            pullback_low = low if pullback_low is None else min(pullback_low, low)

            # Check if pullback too deep
            pullback_depth = (bar_vwap - pullback_low) / bar_vwap
            if pullback_depth > max_pullback_pct:
                state = VwapState.EXHAUSTED
                continue

            if close <= bar_vwap:
                # Still below VWAP
                bars_below += 1
                continue

            # Close > VWAP: potential reclaim
            # Check time window
            if minutes < EARLIEST_ENTRY_MINUTES or minutes >= LATEST_ENTRY_MINUTES:
                # Outside entry window, reset to ABOVE_VWAP
                state = VwapState.ABOVE_VWAP
                pullback_low = None
                bars_below = 0
                continue

            # Check minimum pullback depth
            if pullback_depth < min_pullback_pct:
                state = VwapState.ABOVE_VWAP
                pullback_low = None
                bars_below = 0
                continue

            # Check minimum bars below
            if bars_below < min_pullback_bars:
                state = VwapState.ABOVE_VWAP
                pullback_low = None
                bars_below = 0
                continue

            # Check volume confirmation
            if volumes:
                avg_volume = sum(volumes) / len(volumes)
                if volume < avg_volume * volume_multiplier:
                    state = VwapState.ABOVE_VWAP
                    pullback_low = None
                    bars_below = 0
                    continue

            # Check chase protection
            chase_limit = bar_vwap * (1 + max_chase_above_vwap_pct)
            if close > chase_limit:
                state = VwapState.ABOVE_VWAP
                pullback_low = None
                bars_below = 0
                continue

            # All conditions met - entry
            entry_price = close
            stop_price = pullback_low * (1 - stop_buffer_pct)
            risk = entry_price - stop_price
            if risk <= 0:
                state = VwapState.ABOVE_VWAP
                pullback_low = None
                bars_below = 0
                continue

            target_price = entry_price + risk * target_r

            # Simulate exit
            trade = simulate_trade_exit(
                day_df,
                i,  # entry bar index within day_df iteration
                entry_price,
                stop_price,
                target_price,
                time_stop_bars,
            )
            if trade is not None:
                trades.append(trade)

            state = VwapState.ENTERED

    return trades


def run_single_symbol_sweep(
    df: pd.DataFrame,
    symbol: str,
    config: VwapReclaimSweepConfig,
) -> list[VwapReclaimSweepResult]:
    """Run parameter sweep for a single symbol.

    Args:
        df: DataFrame with all bar data for the symbol.
        symbol: Ticker symbol.
        config: Sweep configuration with parameter ranges.

    Returns:
        List of VwapReclaimSweepResult objects (one per parameter combination).
    """
    results: list[VwapReclaimSweepResult] = []

    # Pre-group bars by day
    day_groups: dict[date, pd.DataFrame] = {
        day: group.reset_index(drop=True) for day, group in df.groupby("trading_day")
    }

    # Compute qualifying days (gap filter)
    qualifying_days = compute_qualifying_days(
        df, config.min_gap_pct, config.min_price, config.max_price
    )

    valid_days_count = len(qualifying_days)

    # Pre-compute VWAP for each qualifying day
    day_vwaps: dict[date, pd.Series] = {}
    for day in qualifying_days:
        day_df = day_groups.get(day)
        if day_df is not None and not day_df.empty:
            day_vwaps[day] = compute_day_vwap(day_df)

    if not day_vwaps:
        # No qualifying days with VWAP - return empty results
        for params in product(
            config.min_pullback_pct_list,
            config.min_pullback_bars_list,
            config.volume_multiplier_list,
            config.target_r_list,
            config.time_stop_bars_list,
        ):
            results.append(
                _empty_vwap_result(symbol, *params, qualifying_days=0)
            )
        return results

    # Sweep over parameter combinations
    param_combos = list(
        product(
            config.min_pullback_pct_list,
            config.min_pullback_bars_list,
            config.volume_multiplier_list,
            config.target_r_list,
            config.time_stop_bars_list,
        )
    )
    total_combos = len(param_combos)

    for combo_count, params in enumerate(param_combos, start=1):
        (
            min_pullback_pct,
            min_pullback_bars,
            volume_multiplier,
            target_r,
            time_stop_bars,
        ) = params

        if combo_count % 100 == 0:
            logger.debug(
                "%s: processed %d/%d combinations", symbol, combo_count, total_combos
            )

        # Run state machine for each qualifying day
        trades: list[TradeResult] = []
        for day, vwap in day_vwaps.items():
            day_df = day_groups[day]
            day_trades = simulate_vwap_reclaim_day(
                day_df,
                vwap,
                min_pullback_pct,
                config.max_pullback_pct,
                min_pullback_bars,
                volume_multiplier,
                config.max_chase_above_vwap_pct,
                config.stop_buffer_pct,
                target_r,
                time_stop_bars,
            )
            trades.extend(day_trades)

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
    trades: list[TradeResult],
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

        # Best parameter combo by Sharpe
        best = results_with_trades.loc[results_with_trades["sharpe_ratio"].idxmax()]
        print(
            f"\nBest by Sharpe: "
            f"min_pullback_pct={best['min_pullback_pct']:.3f}, "
            f"min_pullback_bars={int(best['min_pullback_bars'])}, "
            f"volume_mult={best['volume_multiplier']:.1f}, "
            f"target_r={best['target_r']:.1f}, "
            f"time_stop_bars={int(best['time_stop_bars'])}, "
            f"sharpe={best['sharpe_ratio']:.2f}"
        )
    else:
        print("No trades generated across any parameter combination.")


if __name__ == "__main__":
    main()
