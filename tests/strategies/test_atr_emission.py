"""Tests for ATR emission on SignalEvent across all strategies (Sprint 28.5 S3, AMD-9).

Verifies that strategies with IndicatorEngine access emit atr_value on
SignalEvent, and that main.py loads exit_management.yaml correctly.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import (
    ExitManagementConfig,
    OperatingWindow,
    OrderManagerConfig,
    OrbBreakoutConfig,
    StrategyConfig,
    StrategyRiskLimits,
    VwapReclaimConfig,
)
from argus.core.events import CandleEvent, Side, SignalEvent
from argus.execution.order_manager import OrderManager

ET = ZoneInfo("America/New_York")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_candle(
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 100_000,
) -> CandleEvent:
    if timestamp is None:
        timestamp = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
    return CandleEvent(
        symbol=symbol,
        timeframe="1m",
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        timestamp=timestamp,
    )


def _make_or_candles(
    symbol: str = "AAPL",
    num_candles: int = 15,
    or_high: float = 101.0,
    or_low: float = 99.0,
) -> list[CandleEvent]:
    """Generate OR-period candles bouncing between high and low."""
    base_time = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
    candles: list[CandleEvent] = []
    mid = (or_high + or_low) / 2
    for i in range(num_candles):
        ts = base_time + timedelta(minutes=i)
        candles.append(
            _make_candle(
                symbol=symbol,
                timestamp=ts,
                open_price=mid,
                high=or_high,
                low=or_low,
                close=mid + (0.5 if i % 2 == 0 else -0.5),
                volume=10_000,
            )
        )
    return candles


def _mock_data_service(atr_value: float = 0.25) -> AsyncMock:
    """Create a mock DataService returning ATR and VWAP."""
    ds = AsyncMock()
    ds.get_indicator.side_effect = lambda s, i: {
        "atr_14": atr_value,
        "vwap": 100.0,
        "atr": atr_value,
    }.get(i)
    return ds


# ---------------------------------------------------------------------------
# 1. ORB Breakout emits non-None atr_value
# ---------------------------------------------------------------------------


class TestOrbBreakoutAtrEmission:
    """ORB Breakout emits atr_value from IndicatorEngine."""

    @pytest.mark.asyncio
    async def test_orb_breakout_emits_atr_value(self) -> None:
        config = OrbBreakoutConfig(
            strategy_id="orb_breakout",
            name="ORB Breakout",
            orb_window_minutes=15,
            target_1_r=1.0,
            target_2_r=2.0,
            time_stop_minutes=30,
            chase_protection_pct=0.02,
            breakout_volume_multiplier=1.5,
            risk_limits=StrategyRiskLimits(max_concurrent_positions=2),
            operating_window=OperatingWindow(latest_entry="11:30"),
        )
        ds = _mock_data_service(atr_value=2.0)

        from argus.strategies.orb_breakout import OrbBreakoutStrategy

        strategy = OrbBreakoutStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # Build valid OR (range = 101 - 99 = 2.0, ATR = 2.0, ratio = 1.0)
        for candle in _make_or_candles():
            await strategy.on_candle(candle)
        # Finalize OR
        await strategy.on_candle(
            _make_candle(timestamp=datetime(2026, 2, 15, 14, 45, 0, tzinfo=UTC))
        )

        # Breakout candle
        signal = await strategy.on_candle(
            _make_candle(
                timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),
                open_price=101.0,
                high=102.5,
                low=100.8,
                close=102.0,
                volume=200_000,
            )
        )

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert signal.atr_value == 2.0


# ---------------------------------------------------------------------------
# 2. VWAP Reclaim emits non-None atr_value
# ---------------------------------------------------------------------------


class TestVwapReclaimAtrEmission:
    """VWAP Reclaim emits atr_value from IndicatorEngine."""

    @pytest.mark.asyncio
    async def test_vwap_reclaim_emits_atr_value(self) -> None:
        config = VwapReclaimConfig(
            strategy_id="vwap_reclaim",
            name="VWAP Reclaim",
            min_pullback_pct=0.001,
            max_pullback_pct=0.05,
            min_pullback_bars=1,
            volume_confirmation_multiplier=0.5,
            max_chase_above_vwap_pct=0.02,
            target_1_r=1.0,
            target_2_r=2.0,
            time_stop_minutes=60,
            stop_buffer_pct=0.002,
            risk_limits=StrategyRiskLimits(max_concurrent_positions=0),
            operating_window=OperatingWindow(
                earliest_entry="10:00", latest_entry="12:00"
            ),
        )
        ds = AsyncMock()
        # get_indicator must return VWAP for state machine, ATR for signal
        async def _get_indicator(symbol: str, name: str) -> float | None:
            return {"vwap": 100.0, "atr_14": 0.42}.get(name)

        ds.get_indicator = AsyncMock(side_effect=_get_indicator)

        from argus.strategies.vwap_reclaim import VwapReclaimStrategy

        strategy = VwapReclaimStrategy(config, data_service=ds)
        strategy.set_watchlist(["AAPL"])
        strategy.allocated_capital = 100_000

        # 10:00 AM ET = 15:00 UTC (Feb = EST)
        base = datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC)

        # 1. Above VWAP
        await strategy.on_candle(
            _make_candle(timestamp=base, close=101.0, volume=10_000)
        )
        # 2. Below VWAP (pullback)
        await strategy.on_candle(
            _make_candle(
                timestamp=base + timedelta(minutes=1),
                close=99.5,
                low=99.3,
                volume=10_000,
            )
        )
        # 3. Reclaim above VWAP with volume
        signal = await strategy.on_candle(
            _make_candle(
                timestamp=base + timedelta(minutes=2),
                close=100.3,
                low=99.8,
                volume=20_000,
            )
        )

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        assert signal.atr_value == 0.42


# ---------------------------------------------------------------------------
# 3. PatternBasedStrategy emits atr_value (None if no DataService ATR access)
# ---------------------------------------------------------------------------


class TestPatternStrategyAtrEmission:
    """PatternBasedStrategy emits atr_value from DataService when available."""

    @pytest.mark.asyncio
    async def test_pattern_strategy_emits_atr_value_none_without_data_service(
        self,
    ) -> None:
        """Without data_service, atr_value should be None."""
        from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule

        class StubPattern(PatternModule):
            @property
            def name(self) -> str:
                return "stub"

            @property
            def lookback_bars(self) -> int:
                return 2

            def detect(
                self,
                bars: list[CandleBar],
                indicators: dict[str, float],
            ) -> PatternDetection | None:
                if len(bars) < 2:
                    return None
                return PatternDetection(
                    pattern_type="stub",
                    entry_price=bars[-1].close,
                    stop_price=bars[-1].low,
                    confidence=80.0,
                    metadata={"test": True},
                )

            def score(self, detection: PatternDetection) -> float:
                return 75.0

            def get_default_params(self) -> list["PatternParam"]:
                from argus.strategies.patterns.base import PatternParam
                return []

        config = StrategyConfig(
            strategy_id="pattern_stub",
            name="Stub Pattern",
            operating_window=OperatingWindow(
                earliest_entry="10:00", latest_entry="15:00"
            ),
        )

        from argus.strategies.pattern_strategy import PatternBasedStrategy

        strategy = PatternBasedStrategy(StubPattern(), config, data_service=None)
        strategy.set_watchlist(["AAPL"])

        base = datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC)  # 10:30 AM ET
        await strategy.on_candle(
            _make_candle(timestamp=base, close=100.0, low=99.0, volume=10_000)
        )
        signal = await strategy.on_candle(
            _make_candle(
                timestamp=base + timedelta(minutes=1),
                close=101.0,
                low=99.5,
                volume=15_000,
            )
        )

        assert signal is not None
        assert signal.atr_value is None

    @pytest.mark.asyncio
    async def test_pattern_strategy_emits_atr_value_with_data_service(self) -> None:
        """With data_service providing ATR, atr_value should be populated."""
        from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule

        class StubPattern(PatternModule):
            @property
            def name(self) -> str:
                return "stub"

            @property
            def lookback_bars(self) -> int:
                return 2

            def detect(
                self,
                bars: list[CandleBar],
                indicators: dict[str, float],
            ) -> PatternDetection | None:
                if len(bars) < 2:
                    return None
                return PatternDetection(
                    pattern_type="stub",
                    entry_price=bars[-1].close,
                    stop_price=bars[-1].low,
                    confidence=80.0,
                    metadata={"test": True},
                )

            def score(self, detection: PatternDetection) -> float:
                return 75.0

            def get_default_params(self) -> list["PatternParam"]:
                from argus.strategies.patterns.base import PatternParam
                return []

        config = StrategyConfig(
            strategy_id="pattern_stub",
            name="Stub Pattern",
            operating_window=OperatingWindow(
                earliest_entry="10:00", latest_entry="15:00"
            ),
        )
        ds = _mock_data_service(atr_value=0.55)

        from argus.strategies.pattern_strategy import PatternBasedStrategy

        strategy = PatternBasedStrategy(StubPattern(), config, data_service=ds)
        strategy.set_watchlist(["AAPL"])

        base = datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC)
        await strategy.on_candle(
            _make_candle(timestamp=base, close=100.0, low=99.0, volume=10_000)
        )
        signal = await strategy.on_candle(
            _make_candle(
                timestamp=base + timedelta(minutes=1),
                close=101.0,
                low=99.5,
                volume=15_000,
            )
        )

        assert signal is not None
        assert signal.atr_value == 0.55


# ---------------------------------------------------------------------------
# 4. main.py loads exit_management.yaml without error
# ---------------------------------------------------------------------------


class TestExitManagementConfigLoading:
    """exit_management.yaml parses into ExitManagementConfig."""

    def test_exit_management_yaml_loads(self) -> None:
        from pathlib import Path

        from argus.core.config import ExitManagementConfig, load_yaml_file

        yaml_path = (
            Path(__file__).resolve().parents[2] / "config" / "exit_management.yaml"
        )
        data = load_yaml_file(yaml_path)
        config = ExitManagementConfig(**data)

        assert config.trailing_stop.enabled is True  # Enabled as of Sprint 28.5 config
        assert config.trailing_stop.atr_multiplier == 2.5
        assert config.escalation.enabled is False


# ---------------------------------------------------------------------------
# 5. OrderManager accepts exit_config parameter
# ---------------------------------------------------------------------------


class TestOrderManagerExitConfig:
    """OrderManager constructor stores exit_config."""

    def test_order_manager_accepts_exit_config(self) -> None:
        event_bus = MagicMock()
        broker = MagicMock()
        clock = MagicMock()
        config = MagicMock(spec=OrderManagerConfig)
        config.eod_flatten_time = "15:50"
        config.eod_flatten_timezone = "America/New_York"
        config.fallback_poll_interval_seconds = 5
        config.entry_timeout_seconds = 30

        exit_config = ExitManagementConfig()

        om = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=config,
            exit_config=exit_config,
        )

        assert om._exit_config is exit_config

    def test_order_manager_exit_config_defaults_to_none(self) -> None:
        event_bus = MagicMock()
        broker = MagicMock()
        clock = MagicMock()
        config = MagicMock(spec=OrderManagerConfig)
        config.eod_flatten_time = "15:50"
        config.eod_flatten_timezone = "America/New_York"
        config.fallback_poll_interval_seconds = 5
        config.entry_timeout_seconds = 30

        om = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=config,
        )

        assert om._exit_config is None


# ---------------------------------------------------------------------------
# Section removed by FIX-16 (audit 2026-04-21, DEF-109): AMD-10 deprecation
# warning for enable_trailing_stop / trailing_stop_atr_multiplier is gone —
# those fields were removed from OrderManagerConfig entirely. Trailing stops
# now live in config/exit_management.yaml via ExitManagementConfig (Sprint 28.5).
# ---------------------------------------------------------------------------
