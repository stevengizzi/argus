"""Tests for BacktestEngine regime tagging — Sprint 27.5 Session 2.

Verifies SPY daily bar aggregation, regime tag computation, trade-to-regime
partitioning, to_multi_objective_result(), and edge cases.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from argus.analytics.evaluation import (
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
)
from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.backtest.metrics import BacktestResult
from argus.core.regime import MarketRegime

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a minimal BacktestEngineConfig pointing at tmp_path."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        cache_dir=tmp_path / "cache",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


def _write_spy_parquet(cache_dir: Path, trading_dates: list[date]) -> None:
    """Write synthetic SPY 1-min Parquet files for the given dates.

    Creates 390 bars per day (9:30 to 16:00 ET) with a deterministic
    price series.
    """
    spy_dir = cache_dir / "SPY"
    spy_dir.mkdir(parents=True, exist_ok=True)

    # Group dates by month
    months: dict[tuple[int, int], list[date]] = {}
    for d in trading_dates:
        months.setdefault((d.year, d.month), []).append(d)

    for (year, month), dates in months.items():
        rows = []
        for d in sorted(dates):
            base_price = 450.0 + d.day * 0.5
            for minute_offset in range(390):
                ts = datetime(
                    d.year, d.month, d.day, 9, 30, 0, tzinfo=ET
                ) + timedelta(minutes=minute_offset)
                ts_utc = ts.astimezone(UTC)
                noise = minute_offset * 0.01
                rows.append({
                    "timestamp": ts_utc,
                    "open": base_price + noise,
                    "high": base_price + noise + 0.50,
                    "low": base_price + noise - 0.30,
                    "close": base_price + noise + 0.10,
                    "volume": 10000 + minute_offset,
                })

        df = pd.DataFrame(rows)
        path = spy_dir / f"{year}-{month:02d}.parquet"
        df.to_parquet(path, index=False)


def _make_empty_result(
    strategy_id: str = "strat_orb_breakout",
    start: date | None = None,
    end: date | None = None,
    total_trades: int = 0,
) -> BacktestResult:
    """Create a BacktestResult with zeroed metrics."""
    return BacktestResult(
        strategy_id=strategy_id,
        start_date=start or date(2025, 6, 16),
        end_date=end or date(2025, 6, 20),
        initial_capital=100_000.0,
        final_equity=100_000.0,
        trading_days=5,
        total_trades=total_trades,
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


def _make_trade_dict(
    exit_date: date,
    net_pnl: float = 100.0,
    r_multiple: float = 1.0,
) -> dict[str, object]:
    """Create a minimal trade dict for regime partitioning."""
    exit_time = datetime(
        exit_date.year, exit_date.month, exit_date.day,
        14, 30, 0, tzinfo=ET,
    )
    return {
        "net_pnl": net_pnl,
        "r_multiple": r_multiple,
        "commission": 0.0,
        "hold_duration_seconds": 1800,
        "exit_price": 150.0,
        "exit_time": exit_time,
        "gross_pnl": net_pnl,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_spy_daily_bar_aggregation(tmp_path: Path) -> None:
    """Synthetic 1-min bars -> correct daily OHLCV."""
    config = _make_config(tmp_path)
    trading_dates = [date(2025, 6, 16), date(2025, 6, 17)]
    _write_spy_parquet(config.cache_dir, trading_dates)

    engine = BacktestEngine(config)
    daily = engine._load_spy_daily_bars(date(2025, 6, 16), date(2025, 6, 17))

    assert daily is not None
    assert len(daily) == 2
    assert list(daily.columns) == ["open", "high", "low", "close", "volume"]

    # Check aggregation correctness for first day
    row = daily.iloc[0]
    # base_price = 450.0 + 16 * 0.5 = 458.0
    # first bar: open = 458.0, last bar minute_offset=389: close = 458.0 + 389*0.01 + 0.10
    assert row["open"] == pytest.approx(458.0, abs=0.01)
    # high = max of all (base + noise + 0.50)
    assert row["high"] > row["open"]
    # low = min of all (base + noise - 0.30)
    assert row["low"] < row["open"]
    # volume = sum of all 390 bars
    expected_vol = sum(10000 + m for m in range(390))
    assert row["volume"] == expected_vol


def test_regime_tag_computation(tmp_path: Path) -> None:
    """Known daily bars -> correct MarketRegime assignment."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    # Build 60 days of daily bars with a steady uptrend (price > SMA-20 > SMA-50)
    dates = [date(2025, 4, 1) + timedelta(days=i) for i in range(100)]
    # Filter weekends
    dates = [d for d in dates if d.weekday() < 5][:60]
    n = len(dates)

    daily = pd.DataFrame(
        {
            "open": [400.0 + i * 1.0 for i in range(n)],
            "high": [401.0 + i * 1.0 for i in range(n)],
            "low": [399.0 + i * 1.0 for i in range(n)],
            "close": [400.5 + i * 1.0 for i in range(n)],
            "volume": [1_000_000] * n,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    assert len(tags) == 60
    # With steady uptrend, later days should be bullish_trending
    last_day = dates[-1]
    assert tags[last_day] == MarketRegime.BULLISH_TRENDING.value


def test_regime_tag_insufficient_history(tmp_path: Path) -> None:
    """Early dates with < 20 bars -> RANGE_BOUND default."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    dates = [date(2025, 6, 16) + timedelta(days=i) for i in range(10)]
    daily = pd.DataFrame(
        {
            "open": [450.0] * 10,
            "high": [451.0] * 10,
            "low": [449.0] * 10,
            "close": [450.5] * 10,
            "volume": [1_000_000] * 10,
        },
        index=dates,
    )
    daily.index.name = "date"

    tags = engine._compute_regime_tags(daily)

    # All dates should be RANGE_BOUND (insufficient history)
    for d in dates:
        assert tags[d] == MarketRegime.RANGE_BOUND.value


@pytest.mark.asyncio
async def test_to_multi_objective_result_basic(tmp_path: Path) -> None:
    """BacktestEngine with test data -> valid MOR with regime_results."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16), date(2025, 6, 17)]

    # Mock trade logger to return some trades
    mock_trade = MagicMock()
    mock_trade.net_pnl = 150.0
    mock_trade.r_multiple = 1.5
    mock_trade.commission = 2.0
    mock_trade.hold_duration_seconds = 3600
    mock_trade.exit_price = 155.0
    mock_trade.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    mock_trade.gross_pnl = 152.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=[mock_trade])
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=1)
    result = BacktestResult(
        **{**result.__dict__, "winning_trades": 1, "total_trades": 1,
           "win_rate": 1.0, "profit_factor": float("inf"),
           "expectancy": 1.5}
    )

    # Patch _load_spy_daily_bars to return None (triggers RANGE_BOUND fallback)
    with patch.object(engine, "_load_spy_daily_bars", return_value=None):
        mor = await engine.to_multi_objective_result(result)

    assert isinstance(mor, MultiObjectiveResult)
    assert mor.strategy_id == result.strategy_id
    assert mor.total_trades == 1
    # Should have regime results (single RANGE_BOUND)
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results
    regime_metrics = mor.regime_results[MarketRegime.RANGE_BOUND.value]
    assert regime_metrics.total_trades == 1


@pytest.mark.asyncio
async def test_to_multi_objective_result_regime_partitioning(
    tmp_path: Path,
) -> None:
    """Trades on different regime days -> correct partition."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16), date(2025, 6, 17)]

    # Two trades on different days
    trade1 = MagicMock()
    trade1.net_pnl = 100.0
    trade1.r_multiple = 1.0
    trade1.commission = 1.0
    trade1.hold_duration_seconds = 1800
    trade1.exit_price = 150.0
    trade1.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    trade1.gross_pnl = 101.0

    trade2 = MagicMock()
    trade2.net_pnl = -50.0
    trade2.r_multiple = -0.5
    trade2.commission = 1.0
    trade2.hold_duration_seconds = 900
    trade2.exit_price = 148.0
    trade2.exit_time = datetime(2025, 6, 17, 11, 0, 0, tzinfo=ET)
    trade2.gross_pnl = -49.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(
        return_value=[trade1, trade2]
    )
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=2)

    # Simulate two different regimes
    regime_tags = {
        date(2025, 6, 16): MarketRegime.BULLISH_TRENDING.value,
        date(2025, 6, 17): MarketRegime.RANGE_BOUND.value,
    }

    with patch.object(engine, "_load_spy_daily_bars", return_value=None), \
         patch.object(engine, "_compute_regime_tags", return_value=regime_tags):
        # Need daily_bars to not be None to use _compute_regime_tags
        # Override _load_spy_daily_bars to return a non-None value
        mock_daily = pd.DataFrame(
            {"open": [450], "high": [451], "low": [449],
             "close": [450], "volume": [1000]},
            index=[date(2025, 6, 16)],
        )
        with patch.object(
            engine, "_load_spy_daily_bars", return_value=mock_daily
        ):
            mor = await engine.to_multi_objective_result(result)

    assert MarketRegime.BULLISH_TRENDING.value in mor.regime_results
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results
    assert mor.regime_results[MarketRegime.BULLISH_TRENDING.value].total_trades == 1
    assert mor.regime_results[MarketRegime.RANGE_BOUND.value].total_trades == 1


@pytest.mark.asyncio
async def test_to_multi_objective_result_confidence_tier(
    tmp_path: Path,
) -> None:
    """Tier computed from actual regime distribution."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16)]

    # 5 trades -> should be ENSEMBLE_ONLY (< 10 trades)
    trades = []
    for i in range(5):
        t = MagicMock()
        t.net_pnl = 50.0
        t.r_multiple = 0.5
        t.commission = 0.0
        t.hold_duration_seconds = 600
        t.exit_price = 150.0
        t.exit_time = datetime(2025, 6, 16, 10 + i, 0, 0, tzinfo=ET)
        t.gross_pnl = 50.0
        trades.append(t)

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=trades)
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=5)
    result = BacktestResult(**{**result.__dict__, "total_trades": 5})

    with patch.object(engine, "_load_spy_daily_bars", return_value=None):
        mor = await engine.to_multi_objective_result(result)

    assert mor.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY


@pytest.mark.asyncio
async def test_to_multi_objective_result_no_spy(tmp_path: Path) -> None:
    """SPY not in cache -> WARNING + single RANGE_BOUND regime."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = [date(2025, 6, 16)]

    mock_trade = MagicMock()
    mock_trade.net_pnl = 100.0
    mock_trade.r_multiple = 1.0
    mock_trade.commission = 0.0
    mock_trade.hold_duration_seconds = 1800
    mock_trade.exit_price = 150.0
    mock_trade.exit_time = datetime(2025, 6, 16, 14, 0, 0, tzinfo=ET)
    mock_trade.gross_pnl = 100.0

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(
        return_value=[mock_trade]
    )
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=1)

    # SPY dir does not exist -> _load_spy_daily_bars returns None
    mor = await engine.to_multi_objective_result(result)

    # All trades should land in RANGE_BOUND
    assert len(mor.regime_results) == 1
    assert MarketRegime.RANGE_BOUND.value in mor.regime_results


@pytest.mark.asyncio
async def test_to_multi_objective_result_zero_trades(tmp_path: Path) -> None:
    """Empty backtest -> MOR with ENSEMBLE_ONLY."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    engine._trading_days = []

    mock_logger = AsyncMock()
    mock_logger.get_trades_by_date_range = AsyncMock(return_value=[])
    engine._trade_logger = mock_logger

    result = _make_empty_result(total_trades=0)

    with patch.object(engine, "_load_spy_daily_bars", return_value=None):
        mor = await engine.to_multi_objective_result(result)

    assert mor.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
    assert mor.total_trades == 0
    assert len(mor.regime_results) == 0


def test_regime_metrics_single_trade(tmp_path: Path) -> None:
    """One trade in a regime -> valid (degenerate) RegimeMetrics."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    trade = _make_trade_dict(date(2025, 6, 16), net_pnl=100.0, r_multiple=1.0)
    metrics = engine._compute_regime_metrics([trade])

    assert metrics.total_trades == 1
    assert metrics.win_rate == 1.0
    assert metrics.expectancy_per_trade == pytest.approx(1.0, abs=0.01)
    # Sharpe with single day -> 0.0 (not enough data points)
    assert metrics.sharpe_ratio == 0.0


@pytest.mark.asyncio
async def test_to_multi_objective_result_preserves_backtest_result(
    tmp_path: Path,
) -> None:
    """BacktestEngine.run() return unchanged by regime tagging existence."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)

    # Verify run() returns BacktestResult, not MOR
    with patch.object(engine, "_load_data", new_callable=AsyncMock):
        engine._trading_days = []  # Empty -> fast path
        result = await engine.run()

    assert isinstance(result, BacktestResult)
    assert not isinstance(result, MultiObjectiveResult)


def test_load_spy_daily_bars_no_spy_dir(tmp_path: Path) -> None:
    """SPY directory missing -> returns None."""
    config = _make_config(tmp_path)
    engine = BacktestEngine(config)
    result = engine._load_spy_daily_bars(date(2025, 6, 16), date(2025, 6, 20))
    assert result is None
