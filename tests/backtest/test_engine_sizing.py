"""Tests for BacktestEngine position sizing and symbol auto-detection.

Sprint 21.6.1 Session 1: Verifies legacy position sizing in _on_candle_event(),
zero-risk-per-share passthrough, nonzero share preservation, and _load_data()
symbol auto-detection from cache directory.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
import pytest

from argus.backtest.config import BacktestEngineConfig, StrategyType
from argus.backtest.engine import BacktestEngine
from argus.core.events import CandleEvent, SignalEvent


@pytest.fixture
def engine_config(tmp_path: Path) -> BacktestEngineConfig:
    """Create a BacktestEngineConfig with temp output directory."""
    return BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "backtest_runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb_breakout",
        log_level="WARNING",
    )


def _make_candle(symbol: str = "AAPL") -> CandleEvent:
    """Create a minimal CandleEvent for testing."""
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=150.0,
        high=151.0,
        low=149.0,
        close=150.5,
        volume=10000,
        timestamp=datetime(2025, 6, 16, 14, 30, tzinfo=UTC),
    )


def _make_signal(
    entry: float = 150.0,
    stop: float = 149.0,
    share_count: int = 0,
) -> SignalEvent:
    """Create a SignalEvent with configurable sizing fields."""
    return SignalEvent(
        strategy_id="strat_orb_breakout",
        symbol="AAPL",
        entry_price=entry,
        stop_price=stop,
        target_prices=(151.0, 152.0),
        share_count=share_count,
        rationale="test signal",
        timestamp=datetime(2025, 6, 16, 14, 30, tzinfo=UTC),
    )


@pytest.mark.asyncio
async def test_on_candle_event_sizes_position(
    engine_config: BacktestEngineConfig,
) -> None:
    """Signal with share_count=0 gets legacy-sized before Risk Manager."""
    engine = BacktestEngine(engine_config)

    # Mock strategy that emits a signal with share_count=0
    mock_strategy = AsyncMock()
    mock_strategy.on_candle = AsyncMock(return_value=_make_signal(
        entry=150.0, stop=149.0, share_count=0,
    ))
    mock_strategy.allocated_capital = 100_000.0

    # Provide config.risk_limits.max_loss_per_trade_pct via nested mock
    risk_limits = MagicMock()
    risk_limits.max_loss_per_trade_pct = 0.01
    strategy_config = MagicMock()
    strategy_config.risk_limits = risk_limits
    mock_strategy.config = strategy_config

    mock_rm = AsyncMock()
    mock_rm.evaluate_signal = AsyncMock(return_value=MagicMock())

    engine._strategy = mock_strategy
    engine._risk_manager = mock_rm
    engine._event_bus = AsyncMock()

    await engine._on_candle_event(_make_candle())

    # Risk Manager should receive signal with share_count > 0
    evaluated_signal = mock_rm.evaluate_signal.call_args[0][0]
    # 100_000 * 0.01 / (150 - 149) = 1000 shares
    assert evaluated_signal.share_count == 1000


@pytest.mark.asyncio
async def test_on_candle_event_zero_risk_per_share(
    engine_config: BacktestEngineConfig,
) -> None:
    """Signal where entry == stop passes through with share_count=0."""
    engine = BacktestEngine(engine_config)

    mock_strategy = AsyncMock()
    mock_strategy.on_candle = AsyncMock(return_value=_make_signal(
        entry=150.0, stop=150.0, share_count=0,
    ))
    mock_strategy.allocated_capital = 100_000.0

    mock_rm = AsyncMock()
    mock_rm.evaluate_signal = AsyncMock(return_value=MagicMock())

    engine._strategy = mock_strategy
    engine._risk_manager = mock_rm
    engine._event_bus = AsyncMock()

    await engine._on_candle_event(_make_candle())

    # share_count stays 0 — Risk Manager will reject it (correct behavior)
    evaluated_signal = mock_rm.evaluate_signal.call_args[0][0]
    assert evaluated_signal.share_count == 0


@pytest.mark.asyncio
async def test_on_candle_event_preserves_nonzero_shares(
    engine_config: BacktestEngineConfig,
) -> None:
    """Signal with share_count > 0 is NOT overridden by sizing logic."""
    engine = BacktestEngine(engine_config)

    mock_strategy = AsyncMock()
    mock_strategy.on_candle = AsyncMock(return_value=_make_signal(
        entry=150.0, stop=149.0, share_count=50,
    ))

    mock_rm = AsyncMock()
    mock_rm.evaluate_signal = AsyncMock(return_value=MagicMock())

    engine._strategy = mock_strategy
    engine._risk_manager = mock_rm
    engine._event_bus = AsyncMock()

    await engine._on_candle_event(_make_candle())

    evaluated_signal = mock_rm.evaluate_signal.call_args[0][0]
    assert evaluated_signal.share_count == 50


@pytest.mark.asyncio
async def test_load_data_auto_detects_symbols(tmp_path: Path) -> None:
    """_load_data finds symbol dirs when config.symbols is None."""
    # Create cache directory with symbol subdirs
    cache_dir = tmp_path / "cache"
    (cache_dir / "AAPL").mkdir(parents=True)
    (cache_dir / "TSLA").mkdir(parents=True)
    (cache_dir / ".hidden").mkdir()  # should be skipped

    config = BacktestEngineConfig(
        start_date=date(2025, 6, 16),
        end_date=date(2025, 6, 20),
        output_dir=tmp_path / "runs",
        strategy_type=StrategyType.ORB_BREAKOUT,
        strategy_id="strat_orb",
        symbols=None,
        cache_dir=str(cache_dir),
        log_level="WARNING",
    )
    engine = BacktestEngine(config)

    # Mock HistoricalDataFeed.load to avoid actual file reads
    with patch(
        "argus.backtest.engine.HistoricalDataFeed"
    ) as mock_feed_cls:
        mock_feed = AsyncMock()
        mock_feed.load = AsyncMock(return_value={
            "AAPL": pd.DataFrame({"trading_date": [date(2025, 6, 16)]}),
            "TSLA": pd.DataFrame({"trading_date": [date(2025, 6, 16)]}),
        })
        mock_feed_cls.return_value = mock_feed

        await engine._load_data()

        # Verify feed.load was called with auto-detected symbols
        call_kwargs = mock_feed.load.call_args[1]
        loaded_symbols = sorted(call_kwargs["symbols"])
        assert loaded_symbols == ["AAPL", "TSLA"]
        assert ".hidden" not in call_kwargs["symbols"]
