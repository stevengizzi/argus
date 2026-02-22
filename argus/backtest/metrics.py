"""Backtest performance metrics.

Computes standard trading metrics from a trade log database (SQLite).
The trade log uses the same schema as the production database, so all
metrics work on both backtest and live trade data.

Core metric computation is delegated to argus.analytics.performance to ensure
consistency between backtest and live API metrics. Backtest-specific metrics
(capital-based Sharpe, dollar drawdown, time analysis) remain in this module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date
from typing import TYPE_CHECKING

from argus.analytics.performance import compute_metrics as _compute_core_metrics

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.models.trading import Trade

logger = logging.getLogger(__name__)


@dataclass
class BacktestResult:
    """Complete results from a backtest run.

    Contains all performance metrics computed from the trade log.
    """

    # Run metadata
    strategy_id: str
    start_date: date
    end_date: date
    initial_capital: float
    final_equity: float
    trading_days: int

    # Trade statistics
    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int  # P&L within ±$0.50

    # Performance
    win_rate: float  # winning_trades / total_trades
    profit_factor: float  # gross_wins / gross_losses (inf if no losses)
    avg_r_multiple: float  # average R per trade
    avg_winner_r: float  # average R of winning trades
    avg_loser_r: float  # average R of losing trades (negative)
    expectancy: float  # (win_rate * avg_winner_r) + ((1 - win_rate) * avg_loser_r)

    # Drawdown
    max_drawdown_dollars: float  # largest peak-to-trough decline
    max_drawdown_pct: float  # as percentage of peak equity

    # Risk-adjusted
    sharpe_ratio: float  # annualized, using daily returns
    recovery_factor: float  # net_profit / max_drawdown

    # Duration
    avg_hold_minutes: float  # average position hold duration

    # Streaks
    max_consecutive_wins: int
    max_consecutive_losses: int

    # Extremes
    largest_win_dollars: float
    largest_loss_dollars: float
    largest_win_r: float
    largest_loss_r: float

    # Time analysis
    pnl_by_hour: dict[int, float] = field(default_factory=dict)  # hour (ET) -> total P&L
    pnl_by_weekday: dict[int, float] = field(default_factory=dict)  # 0=Mon -> total P&L
    trades_by_hour: dict[int, int] = field(default_factory=dict)  # hour (ET) -> trade count
    trades_by_weekday: dict[int, int] = field(default_factory=dict)  # 0=Mon -> trade count

    # Daily equity curve
    daily_equity: list[tuple[date, float]] = field(default_factory=list)

    # Monthly P&L
    monthly_pnl: dict[str, float] = field(default_factory=dict)  # "YYYY-MM" -> net P&L


def _trades_to_dicts(trades: list[Trade]) -> list[dict]:
    """Convert Trade objects to dicts for the shared metrics computation.

    The shared compute_metrics expects dict keys:
    - net_pnl: Net P&L in dollars
    - r_multiple: R-multiple of the trade
    - commission: Commission paid
    - hold_duration_seconds: Hold duration in seconds
    - exit_price: Exit price (None for open trades)
    - exit_time: For sorting

    Args:
        trades: List of Trade model objects.

    Returns:
        List of dicts matching the expected interface.
    """
    return [
        {
            "net_pnl": t.net_pnl,
            "r_multiple": t.r_multiple,
            "commission": t.commission,
            "hold_duration_seconds": t.hold_duration_seconds,
            "exit_price": t.exit_price,
            "exit_time": t.exit_time,
            "gross_pnl": t.gross_pnl,
        }
        for t in trades
    ]


async def compute_metrics(
    trade_logger: TradeLogger,
    strategy_id: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
    trading_days: int | None = None,
) -> BacktestResult:
    """Compute all backtest metrics from the trade log.

    Core metrics (win rate, profit factor, streaks, etc.) are computed via the
    shared argus.analytics.performance module to ensure consistency with the
    live API. Backtest-specific metrics (capital-based Sharpe ratio, dollar
    drawdown, time analysis) are computed here.

    Args:
        trade_logger: TradeLogger connected to the backtest database.
        strategy_id: Strategy that was run.
        start_date: First trading day in the backtest.
        end_date: Last trading day in the backtest.
        initial_capital: Starting capital.
        trading_days: Number of trading days processed (if None, computed from trades).

    Returns:
        BacktestResult with all computed metrics.
    """
    # Query all trades from the trade log for the date range
    trades = await trade_logger.get_trades_by_date_range(start_date, end_date, strategy_id)

    # Handle empty trades
    if not trades:
        return _empty_result(strategy_id, start_date, end_date, initial_capital, trading_days or 0)

    # Compute core metrics via shared module
    trade_dicts = _trades_to_dicts(trades)
    core = _compute_core_metrics(trade_dicts)

    # Backtest-specific: R-multiple averages for winners/losers
    winners = [t for t in trades if t.net_pnl > 0.50]
    losers = [t for t in trades if t.net_pnl < -0.50]

    winner_rs = [t.r_multiple for t in winners if t.r_multiple != 0]
    avg_winner_r = sum(winner_rs) / len(winner_rs) if winner_rs else 0.0

    loser_rs = [t.r_multiple for t in losers if t.r_multiple != 0]
    avg_loser_r = sum(loser_rs) / len(loser_rs) if loser_rs else 0.0

    # Expectancy
    expectancy = (core.win_rate * avg_winner_r) + ((1 - core.win_rate) * avg_loser_r)

    # Final equity
    final_equity = initial_capital + core.net_pnl

    # Build daily equity curve (backtest-specific: includes initial capital)
    daily_pnl_map: dict[date, float] = {}
    for trade in trades:
        trade_date = trade.exit_time.date()
        daily_pnl_map[trade_date] = daily_pnl_map.get(trade_date, 0.0) + trade.net_pnl

    sorted_dates = sorted(daily_pnl_map.keys())
    daily_equity: list[tuple[date, float]] = []
    cumulative = initial_capital
    for d in sorted_dates:
        cumulative += daily_pnl_map[d]
        daily_equity.append((d, cumulative))

    # Trading days (use provided value or count from trades)
    actual_trading_days = trading_days if trading_days is not None else len(sorted_dates)

    # Drawdown (backtest-specific: returns both dollars and pct)
    equity_values = [initial_capital] + [eq for _, eq in daily_equity]
    max_dd_dollars, max_dd_pct = compute_max_drawdown(equity_values)

    # Daily returns for Sharpe (backtest-specific: uses % returns with capital)
    daily_returns: list[float] = []
    prev_equity = initial_capital
    for _, eq in daily_equity:
        if prev_equity > 0:
            daily_returns.append((eq - prev_equity) / prev_equity)
        prev_equity = eq

    sharpe_ratio = compute_sharpe_ratio(daily_returns)

    # Recovery factor
    recovery_factor = core.net_pnl / max_dd_dollars if max_dd_dollars > 0 else float("inf")

    # Hold duration in minutes (core has seconds)
    avg_hold_minutes = core.avg_hold_seconds / 60.0

    # Extremes in R-multiples (backtest-specific)
    largest_win_r = max((t.r_multiple for t in winners), default=0.0)
    largest_loss_r = min((t.r_multiple for t in losers), default=0.0)

    # Time analysis (backtest-specific)
    pnl_by_hour, trades_by_hour = _analyze_by_hour(trades)
    pnl_by_weekday, trades_by_weekday = _analyze_by_weekday(trades)

    # Monthly P&L (backtest-specific)
    monthly_pnl = _compute_monthly_pnl(trades)

    return BacktestResult(
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        final_equity=final_equity,
        trading_days=actual_trading_days,
        total_trades=core.total_trades,
        winning_trades=core.wins,
        losing_trades=core.losses,
        breakeven_trades=core.breakeven,
        win_rate=core.win_rate,
        profit_factor=core.profit_factor,
        avg_r_multiple=core.avg_r_multiple,
        avg_winner_r=avg_winner_r,
        avg_loser_r=avg_loser_r,
        expectancy=expectancy,
        max_drawdown_dollars=max_dd_dollars,
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe_ratio,
        recovery_factor=recovery_factor,
        avg_hold_minutes=avg_hold_minutes,
        max_consecutive_wins=core.consecutive_wins_max,
        max_consecutive_losses=core.consecutive_losses_max,
        largest_win_dollars=core.largest_win,
        largest_loss_dollars=core.largest_loss,
        largest_win_r=largest_win_r,
        largest_loss_r=largest_loss_r,
        pnl_by_hour=pnl_by_hour,
        pnl_by_weekday=pnl_by_weekday,
        trades_by_hour=trades_by_hour,
        trades_by_weekday=trades_by_weekday,
        daily_equity=daily_equity,
        monthly_pnl=monthly_pnl,
    )


def _empty_result(
    strategy_id: str,
    start_date: date,
    end_date: date,
    initial_capital: float,
    trading_days: int = 0,
) -> BacktestResult:
    """Create an empty result for when there are no trades."""
    return BacktestResult(
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        final_equity=initial_capital,
        trading_days=trading_days,
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        breakeven_trades=0,
        win_rate=0.0,
        profit_factor=0.0,
        avg_r_multiple=0.0,
        avg_winner_r=0.0,
        avg_loser_r=0.0,
        expectancy=0.0,
        max_drawdown_dollars=0.0,
        max_drawdown_pct=0.0,
        sharpe_ratio=0.0,
        recovery_factor=0.0,
        avg_hold_minutes=0.0,
        max_consecutive_wins=0,
        max_consecutive_losses=0,
        largest_win_dollars=0.0,
        largest_loss_dollars=0.0,
        largest_win_r=0.0,
        largest_loss_r=0.0,
    )


def _analyze_by_hour(trades: list[Trade]) -> tuple[dict[int, float], dict[int, int]]:
    """Analyze P&L and trade count by hour of day.

    Args:
        trades: List of trades.

    Returns:
        Tuple of (pnl_by_hour, trades_by_hour).
    """
    pnl_by_hour: dict[int, float] = {}
    trades_by_hour: dict[int, int] = {}

    for trade in trades:
        hour = trade.exit_time.hour
        pnl_by_hour[hour] = pnl_by_hour.get(hour, 0.0) + trade.net_pnl
        trades_by_hour[hour] = trades_by_hour.get(hour, 0) + 1

    return pnl_by_hour, trades_by_hour


def _analyze_by_weekday(trades: list[Trade]) -> tuple[dict[int, float], dict[int, int]]:
    """Analyze P&L and trade count by weekday.

    Args:
        trades: List of trades.

    Returns:
        Tuple of (pnl_by_weekday, trades_by_weekday) where 0=Monday.
    """
    pnl_by_weekday: dict[int, float] = {}
    trades_by_weekday: dict[int, int] = {}

    for trade in trades:
        weekday = trade.exit_time.weekday()
        pnl_by_weekday[weekday] = pnl_by_weekday.get(weekday, 0.0) + trade.net_pnl
        trades_by_weekday[weekday] = trades_by_weekday.get(weekday, 0) + 1

    return pnl_by_weekday, trades_by_weekday


def _compute_monthly_pnl(trades: list[Trade]) -> dict[str, float]:
    """Compute P&L by month.

    Args:
        trades: List of trades.

    Returns:
        Dict of "YYYY-MM" -> net P&L.
    """
    monthly_pnl: dict[str, float] = {}

    for trade in trades:
        month_key = trade.exit_time.strftime("%Y-%m")
        monthly_pnl[month_key] = monthly_pnl.get(month_key, 0.0) + trade.net_pnl

    return monthly_pnl


def compute_sharpe_ratio(
    daily_returns: list[float],
    risk_free_rate: float = 0.05,  # 5% annual
    trading_days_per_year: int = 252,
) -> float:
    """Compute annualized Sharpe ratio from daily returns.

    Sharpe = (mean_daily_return - daily_risk_free) / std_daily_return * sqrt(252)

    Args:
        daily_returns: List of daily return percentages.
        risk_free_rate: Annual risk-free rate (default 5%).
        trading_days_per_year: Number of trading days (default 252).

    Returns:
        Annualized Sharpe ratio. Returns 0.0 if fewer than 2 data points
        or zero standard deviation.
    """
    if len(daily_returns) < 2:
        return 0.0

    daily_rf = risk_free_rate / trading_days_per_year
    excess_returns = [r - daily_rf for r in daily_returns]

    mean_excess = sum(excess_returns) / len(excess_returns)
    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
    std_dev = variance**0.5

    # Use tolerance check for near-zero std dev (floating-point precision)
    if std_dev < 1e-10:
        return 0.0

    return (mean_excess / std_dev) * (trading_days_per_year**0.5)


def compute_max_drawdown(
    equity_curve: list[float],
) -> tuple[float, float]:
    """Compute maximum drawdown from an equity curve.

    Args:
        equity_curve: List of equity values (e.g., end-of-day equity).

    Returns:
        Tuple of (max_drawdown_dollars, max_drawdown_pct).
    """
    if not equity_curve:
        return 0.0, 0.0

    peak = equity_curve[0]
    max_dd_dollars = 0.0
    max_dd_pct = 0.0

    for equity in equity_curve:
        if equity > peak:
            peak = equity
        drawdown = peak - equity
        drawdown_pct = drawdown / peak if peak > 0 else 0.0
        if drawdown > max_dd_dollars:
            max_dd_dollars = drawdown
            max_dd_pct = drawdown_pct

    return max_dd_dollars, max_dd_pct
