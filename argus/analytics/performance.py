"""Shared performance metric computation for Argus.

This module provides performance metrics used by both the Command Center API
and the backtesting toolkit. Formulas are identical to those in backtest/metrics.py
to ensure consistency between live and backtested results.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PerformanceMetrics:
    """Aggregated performance metrics from a set of trades.

    All metrics are computed from closed trades only.
    """

    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    breakeven: int = 0
    win_rate: float = 0.0
    profit_factor: float = 0.0  # gross_wins / abs(gross_losses). inf if no losses.
    net_pnl: float = 0.0
    gross_pnl: float = 0.0
    total_commissions: float = 0.0
    avg_r_multiple: float = 0.0
    sharpe_ratio: float = 0.0  # annualized: mean(daily_returns) / std * sqrt(252)
    max_drawdown_pct: float = 0.0  # peak-to-trough on cumulative P&L
    avg_hold_seconds: float = 0.0
    largest_win: float = 0.0
    largest_loss: float = 0.0
    consecutive_wins_max: int = 0
    consecutive_losses_max: int = 0


def compute_metrics(trades: list[dict]) -> PerformanceMetrics:
    """Compute metrics from trade dicts.

    Expected dict keys:
    - net_pnl (or pnl_dollars): Net P&L in dollars
    - r_multiple (or pnl_r_multiple): R-multiple of the trade
    - commission: Commission paid
    - hold_duration_seconds: Hold duration in seconds
    - exit_price: Exit price (None for open trades)
    - entry_time or exit_time: For sorting (optional)

    Only closed trades (exit_price not None) are included.

    Args:
        trades: List of trade dictionaries from TradeLogger.query_trades()
            or similar.

    Returns:
        PerformanceMetrics with computed values.
    """
    # Filter to closed trades only
    closed_trades = [t for t in trades if t.get("exit_price") is not None]

    if not closed_trades:
        return PerformanceMetrics()

    # Get P&L field (handle both naming conventions)
    def get_pnl(t: dict) -> float:
        return t.get("net_pnl") or t.get("pnl_dollars") or 0.0

    def get_r_multiple(t: dict) -> float:
        return t.get("r_multiple") or t.get("pnl_r_multiple") or 0.0

    # Categorize trades (using $0.50 threshold consistent with backtest/metrics.py)
    winners = [t for t in closed_trades if get_pnl(t) > 0.50]
    losers = [t for t in closed_trades if get_pnl(t) < -0.50]
    breakevens = [t for t in closed_trades if -0.50 <= get_pnl(t) <= 0.50]

    total_trades = len(closed_trades)
    wins = len(winners)
    losses = len(losers)
    breakeven_count = len(breakevens)

    # Win rate
    win_rate = wins / total_trades if total_trades > 0 else 0.0

    # Profit factor
    gross_wins = sum(get_pnl(t) for t in winners) if winners else 0.0
    gross_losses = abs(sum(get_pnl(t) for t in losers)) if losers else 0.0
    profit_factor = gross_wins / gross_losses if gross_losses > 0 else float("inf")

    # P&L
    gross_pnl = sum(t.get("gross_pnl", get_pnl(t)) for t in closed_trades)
    total_commissions = sum(t.get("commission", 0.0) for t in closed_trades)
    net_pnl = sum(get_pnl(t) for t in closed_trades)

    # R-multiples
    r_multiples = [get_r_multiple(t) for t in closed_trades if get_r_multiple(t) != 0]
    avg_r_multiple = sum(r_multiples) / len(r_multiples) if r_multiples else 0.0

    # Hold duration
    hold_durations = [t.get("hold_duration_seconds", 0) or 0 for t in closed_trades]
    avg_hold_seconds = sum(hold_durations) / len(hold_durations) if hold_durations else 0.0

    # Extremes
    largest_win = max((get_pnl(t) for t in winners), default=0.0)
    largest_loss = min((get_pnl(t) for t in losers), default=0.0)

    # Consecutive streaks
    consecutive_wins_max, consecutive_losses_max = _compute_streaks(closed_trades)

    # Build daily P&L for Sharpe and drawdown calculation
    # Group by date, compute daily returns
    daily_pnl = _compute_daily_pnl(closed_trades)
    sharpe_ratio = compute_sharpe_ratio(daily_pnl) if daily_pnl else 0.0
    max_drawdown_pct = compute_max_drawdown_pct(daily_pnl) if daily_pnl else 0.0

    return PerformanceMetrics(
        total_trades=total_trades,
        wins=wins,
        losses=losses,
        breakeven=breakeven_count,
        win_rate=win_rate,
        profit_factor=profit_factor,
        net_pnl=net_pnl,
        gross_pnl=gross_pnl,
        total_commissions=total_commissions,
        avg_r_multiple=avg_r_multiple,
        sharpe_ratio=sharpe_ratio,
        max_drawdown_pct=max_drawdown_pct,
        avg_hold_seconds=avg_hold_seconds,
        largest_win=largest_win,
        largest_loss=largest_loss,
        consecutive_wins_max=consecutive_wins_max,
        consecutive_losses_max=consecutive_losses_max,
    )


def _compute_streaks(trades: list[dict]) -> tuple[int, int]:
    """Compute max consecutive wins and losses.

    Args:
        trades: List of trade dicts, sorted by exit_time preferred.

    Returns:
        Tuple of (max_consecutive_wins, max_consecutive_losses).
    """
    if not trades:
        return 0, 0

    # Sort by exit_time if available
    def get_sort_key(t: dict) -> str:
        return t.get("exit_time", "") or t.get("entry_time", "") or ""

    sorted_trades = sorted(trades, key=get_sort_key)

    max_wins = 0
    max_losses = 0
    current_wins = 0
    current_losses = 0

    def get_pnl(t: dict) -> float:
        return t.get("net_pnl") or t.get("pnl_dollars") or 0.0

    for trade in sorted_trades:
        pnl = get_pnl(trade)
        if pnl > 0.50:
            current_wins += 1
            current_losses = 0
            max_wins = max(max_wins, current_wins)
        elif pnl < -0.50:
            current_losses += 1
            current_wins = 0
            max_losses = max(max_losses, current_losses)
        else:
            # Breakeven resets both streaks
            current_wins = 0
            current_losses = 0

    return max_wins, max_losses


def _compute_daily_pnl(trades: list[dict]) -> list[float]:
    """Group trades by date and compute daily P&L.

    Args:
        trades: List of trade dicts with exit_time field.

    Returns:
        List of daily P&L values in chronological order.
    """
    from datetime import datetime

    daily_totals: dict[str, float] = {}

    def get_pnl(t: dict) -> float:
        return t.get("net_pnl") or t.get("pnl_dollars") or 0.0

    for trade in trades:
        exit_time = trade.get("exit_time")
        if not exit_time:
            continue

        # Handle both string and datetime
        if isinstance(exit_time, str):
            # Extract date portion
            date_str = exit_time[:10]  # "YYYY-MM-DD"
        elif isinstance(exit_time, datetime):
            date_str = exit_time.date().isoformat()
        else:
            continue

        daily_totals[date_str] = daily_totals.get(date_str, 0.0) + get_pnl(trade)

    # Return sorted by date
    sorted_dates = sorted(daily_totals.keys())
    return [daily_totals[d] for d in sorted_dates]


def compute_sharpe_ratio(
    daily_pnl: list[float],
    risk_free_rate: float = 0.05,  # 5% annual
    trading_days_per_year: int = 252,
) -> float:
    """Compute annualized Sharpe ratio from daily P&L.

    Formula matches backtest/metrics.py:
    Sharpe = (mean_daily_return - daily_risk_free) / std_daily_return * sqrt(252)

    For simplicity when we don't have capital data, we use raw P&L as returns.
    This gives a meaningful relative measure even without percentage returns.

    Args:
        daily_pnl: List of daily P&L values (dollars).
        risk_free_rate: Annual risk-free rate (default 5%).
        trading_days_per_year: Number of trading days (default 252).

    Returns:
        Annualized Sharpe ratio. Returns 0.0 if fewer than 2 data points
        or zero standard deviation.
    """
    if len(daily_pnl) < 2:
        return 0.0

    # Use raw P&L as pseudo-returns
    # When capital is unknown, this gives relative risk-adjusted measure
    mean_pnl = sum(daily_pnl) / len(daily_pnl)

    # Variance using sample std dev (n-1)
    variance = sum((p - mean_pnl) ** 2 for p in daily_pnl) / (len(daily_pnl) - 1)
    std_dev = variance**0.5

    # Use tolerance check for near-zero std dev (floating-point precision)
    if std_dev < 1e-10:
        return 0.0

    # Since we're using raw P&L not percentage returns, skip risk-free adjustment
    # This makes the Sharpe comparable within the system but not to external benchmarks
    return (mean_pnl / std_dev) * (trading_days_per_year**0.5)


def compute_max_drawdown_pct(daily_pnl: list[float]) -> float:
    """Compute maximum drawdown percentage from daily P&L.

    Builds a cumulative equity curve and finds the largest peak-to-trough decline.
    Formula matches backtest/metrics.py.

    Args:
        daily_pnl: List of daily P&L values (dollars).

    Returns:
        Maximum drawdown as a percentage (0.0 to 1.0 range).
        Returns 0.0 if no drawdown or empty data.
    """
    if not daily_pnl:
        return 0.0

    # Build cumulative equity curve
    equity_curve: list[float] = []
    cumulative = 0.0
    for pnl in daily_pnl:
        cumulative += pnl
        equity_curve.append(cumulative)

    if not equity_curve:
        return 0.0

    # Find max drawdown
    # Since we start at 0, need to handle the case where all values are positive
    # We track drawdown as percentage of peak (which could be the starting point or higher)
    peak = equity_curve[0]
    max_dd_pct = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity
        if peak > 0:
            drawdown_pct = (peak - equity) / peak
            max_dd_pct = max(max_dd_pct, drawdown_pct)

    return max_dd_pct
