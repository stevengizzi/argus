"""Tests for the VWAP Reclaim Strategy.

Comprehensive tests for VwapReclaimStrategy state machine, entry conditions,
signal construction, and edge cases.

Sprint 19, Session 3.
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import (
    OperatingWindow,
    StrategyRiskLimits,
    VwapReclaimConfig,
    load_vwap_reclaim_config,
)
from argus.core.events import CandleEvent, SignalEvent
from argus.strategies.vwap_reclaim import VwapReclaimStrategy, VwapState, VwapSymbolState

ET = ZoneInfo("America/New_York")


def make_vwap_reclaim_config(
    strategy_id: str = "strat_vwap_reclaim",
    min_pullback_pct: float = 0.002,
    max_pullback_pct: float = 0.02,
    min_pullback_bars: int = 3,
    volume_confirmation_multiplier: float = 1.2,
    max_chase_above_vwap_pct: float = 0.003,
    target_1_r: float = 1.0,
    target_2_r: float = 2.0,
    time_stop_minutes: int = 30,
    stop_buffer_pct: float = 0.001,
    max_trades_per_day: int = 10,
    max_daily_loss_pct: float = 0.03,
    max_loss_per_trade_pct: float = 0.01,
    max_concurrent_positions: int = 3,
    earliest_entry: str = "10:00",
    latest_entry: str = "12:00",
) -> VwapReclaimConfig:
    """Create a VwapReclaimConfig for testing."""
    return VwapReclaimConfig(
        strategy_id=strategy_id,
        name="VWAP Reclaim",
        min_pullback_pct=min_pullback_pct,
        max_pullback_pct=max_pullback_pct,
        min_pullback_bars=min_pullback_bars,
        volume_confirmation_multiplier=volume_confirmation_multiplier,
        max_chase_above_vwap_pct=max_chase_above_vwap_pct,
        target_1_r=target_1_r,
        target_2_r=target_2_r,
        time_stop_minutes=time_stop_minutes,
        stop_buffer_pct=stop_buffer_pct,
        risk_limits=StrategyRiskLimits(
            max_trades_per_day=max_trades_per_day,
            max_daily_loss_pct=max_daily_loss_pct,
            max_loss_per_trade_pct=max_loss_per_trade_pct,
            max_concurrent_positions=max_concurrent_positions,
        ),
        operating_window=OperatingWindow(
            earliest_entry=earliest_entry,
            latest_entry=latest_entry,
        ),
    )


def make_candle(
    symbol: str = "AAPL",
    timestamp: datetime | None = None,
    open_price: float = 100.0,
    high: float = 101.0,
    low: float = 99.0,
    close: float = 100.5,
    volume: int = 100_000,
) -> CandleEvent:
    """Create a CandleEvent for testing.

    Timestamps should be provided in UTC. The strategy will convert to ET
    for time window comparisons. For February 2026 (EST, UTC-5):
    - 10:00 AM ET = 15:00 UTC
    - 11:00 AM ET = 16:00 UTC
    - 12:00 PM ET = 17:00 UTC
    """
    if timestamp is None:
        # Default: 10:30 AM ET = 15:30 UTC in February (EST)
        timestamp = datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC)
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


class MockDataService:
    """Mock DataService for controlled VWAP values."""

    def __init__(self, vwap: float | None = 100.0) -> None:
        """Initialize with a default VWAP value."""
        self._vwap = vwap
        self._vwap_values: dict[str, float | None] = {}

    def set_vwap(self, symbol: str, vwap: float | None) -> None:
        """Set VWAP for a specific symbol."""
        self._vwap_values[symbol] = vwap

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Get indicator value. Only handles 'vwap'."""
        if indicator == "vwap":
            if symbol in self._vwap_values:
                return self._vwap_values[symbol]
            return self._vwap
        return None


# ===========================================================================
# Test Categories
# ===========================================================================


class TestVwapReclaimConfig:
    """Tests for VwapReclaimConfig validation."""

    def test_default_values(self) -> None:
        """Verify default configuration values."""
        config = VwapReclaimConfig(strategy_id="test_vwap", name="Test VWAP")

        assert config.min_pullback_pct == 0.002
        assert config.max_pullback_pct == 0.02
        assert config.min_pullback_bars == 3
        assert config.volume_confirmation_multiplier == 1.2
        assert config.max_chase_above_vwap_pct == 0.003
        assert config.target_1_r == 1.0
        assert config.target_2_r == 2.0
        assert config.time_stop_minutes == 30
        assert config.stop_buffer_pct == 0.001

    def test_validation_min_pullback_pct_bounds(self) -> None:
        """min_pullback_pct must be >= 0 and <= 0.05."""
        config = make_vwap_reclaim_config(min_pullback_pct=0.0)
        assert config.min_pullback_pct == 0.0

        # Need to also increase max_pullback_pct to satisfy cross-field validation
        config = make_vwap_reclaim_config(min_pullback_pct=0.05, max_pullback_pct=0.10)
        assert config.min_pullback_pct == 0.05

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(min_pullback_pct=-0.01)

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(min_pullback_pct=0.06)

    def test_validation_max_pullback_pct_bounds(self) -> None:
        """max_pullback_pct must be >= 0 and <= 0.10."""
        config = make_vwap_reclaim_config(max_pullback_pct=0.10)
        assert config.max_pullback_pct == 0.10

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(max_pullback_pct=0.11)

    def test_validation_min_pullback_bars_bounds(self) -> None:
        """min_pullback_bars must be >= 1 and <= 30."""
        config = make_vwap_reclaim_config(min_pullback_bars=1)
        assert config.min_pullback_bars == 1

        config = make_vwap_reclaim_config(min_pullback_bars=30)
        assert config.min_pullback_bars == 30

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(min_pullback_bars=0)

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(min_pullback_bars=31)

    def test_validation_volume_multiplier_bounds(self) -> None:
        """volume_confirmation_multiplier must be > 0 and <= 5.0."""
        config = make_vwap_reclaim_config(volume_confirmation_multiplier=0.1)
        assert config.volume_confirmation_multiplier == 0.1

        config = make_vwap_reclaim_config(volume_confirmation_multiplier=5.0)
        assert config.volume_confirmation_multiplier == 5.0

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(volume_confirmation_multiplier=0)

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(volume_confirmation_multiplier=5.1)

    def test_validation_time_stop_minutes_bounds(self) -> None:
        """time_stop_minutes must be >= 1."""
        config = make_vwap_reclaim_config(time_stop_minutes=1)
        assert config.time_stop_minutes == 1

        with pytest.raises(ValueError):
            make_vwap_reclaim_config(time_stop_minutes=0)

    def test_cross_field_validation_pullback_range(self) -> None:
        """min_pullback_pct must be less than max_pullback_pct."""
        # Valid: min < max
        config = make_vwap_reclaim_config(min_pullback_pct=0.002, max_pullback_pct=0.02)
        assert config.min_pullback_pct < config.max_pullback_pct

        # Invalid: min >= max
        with pytest.raises(ValueError, match="must be less than"):
            make_vwap_reclaim_config(min_pullback_pct=0.02, max_pullback_pct=0.02)

        with pytest.raises(ValueError, match="must be less than"):
            make_vwap_reclaim_config(min_pullback_pct=0.03, max_pullback_pct=0.02)

    def test_load_from_yaml(self, tmp_path: Path) -> None:
        """Test loading VwapReclaimConfig from YAML file."""
        yaml_content = """
strategy_id: "strat_vwap_reclaim_test"
name: "VWAP Reclaim Test"
version: "1.0.0"
enabled: true
asset_class: "us_stocks"

min_pullback_pct: 0.003
max_pullback_pct: 0.015
min_pullback_bars: 4
volume_confirmation_multiplier: 1.5
max_chase_above_vwap_pct: 0.002
target_1_r: 1.5
target_2_r: 2.5
time_stop_minutes: 45
stop_buffer_pct: 0.002

risk_limits:
  max_trades_per_day: 8
  max_concurrent_positions: 2
"""
        config_path = tmp_path / "vwap_reclaim.yaml"
        config_path.write_text(yaml_content)

        config = load_vwap_reclaim_config(config_path)

        assert config.strategy_id == "strat_vwap_reclaim_test"
        assert config.min_pullback_pct == 0.003
        assert config.min_pullback_bars == 4
        assert config.target_1_r == 1.5
        assert config.risk_limits.max_trades_per_day == 8


class TestVwapReclaimStrategyInit:
    """Tests for VwapReclaimStrategy initialization."""

    def test_strategy_id_from_config(self) -> None:
        """Strategy ID comes from config."""
        config = make_vwap_reclaim_config(strategy_id="strat_vwap_reclaim")
        strategy = VwapReclaimStrategy(config)

        assert strategy.strategy_id == "strat_vwap_reclaim"

    def test_operating_window_times_parsed(self) -> None:
        """Operating window times are parsed correctly."""
        config = make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00")
        strategy = VwapReclaimStrategy(config)

        from datetime import time

        assert strategy._earliest_entry_time == time(10, 0)
        assert strategy._latest_entry_time == time(12, 0)


class TestStateMachineTransitions:
    """Tests for VWAP Reclaim state machine transitions."""

    @pytest.mark.asyncio
    async def test_initial_state_is_watching(self) -> None:
        """Initial state for a new symbol is WATCHING."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # First candle
        candle = make_candle(symbol="AAPL", close=99.0)  # Below VWAP
        await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.WATCHING

    @pytest.mark.asyncio
    async def test_watching_to_above_vwap_on_close_above(self) -> None:
        """WATCHING → ABOVE_VWAP when close > VWAP."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Close above VWAP
        candle = make_candle(symbol="AAPL", close=101.0)
        await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ABOVE_VWAP

    @pytest.mark.asyncio
    async def test_watching_stays_watching_on_close_below(self) -> None:
        """WATCHING stays WATCHING when close < VWAP (never been above)."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Multiple candles below VWAP
        for i in range(5):
            candle = make_candle(
                symbol="AAPL",
                close=99.0 - i * 0.1,
                timestamp=datetime(2026, 2, 15, 15, 30 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.WATCHING

    @pytest.mark.asyncio
    async def test_above_vwap_to_below_vwap_on_close_below(self) -> None:
        """ABOVE_VWAP → BELOW_VWAP when close < VWAP."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # First above VWAP
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        # Then below VWAP
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.5,
                low=99.0,
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.BELOW_VWAP
        assert state.pullback_low == 99.0
        assert state.bars_below_vwap == 1

    @pytest.mark.asyncio
    async def test_above_vwap_stays_above_on_close_above(self) -> None:
        """ABOVE_VWAP stays ABOVE_VWAP when close > VWAP."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above VWAP and stay above
        for i in range(3):
            candle = make_candle(
                symbol="AAPL",
                close=101.0 + i * 0.1,
                timestamp=datetime(2026, 2, 15, 15, 30 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ABOVE_VWAP

    @pytest.mark.asyncio
    async def test_below_vwap_reclaim_triggers_entry(self) -> None:
        """BELOW_VWAP + reclaim with all conditions met → signal + ENTERED."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,  # Any volume works
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above VWAP
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000)
        )

        # Pull back below VWAP (3 bars, deep enough)
        for i in range(3):
            candle = make_candle(
                symbol="AAPL",
                close=99.5,
                low=99.5 - 0.5,  # Low enough pullback
                volume=100_000,
                timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        # Reclaim candle
        reclaim = make_candle(
            symbol="AAPL",
            close=100.2,  # Above VWAP
            low=99.5,
            volume=150_000,
            timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(reclaim)

        assert signal is not None
        assert isinstance(signal, SignalEvent)
        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ENTERED

    @pytest.mark.asyncio
    async def test_below_vwap_to_above_without_entry_allows_retry(self) -> None:
        """BELOW_VWAP → ABOVE_VWAP when conditions not met, allows retry."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.01,  # 1% required
            min_pullback_bars=3,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above, then below, then back above (too shallow pullback)
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))

        # Shallow pullback (only 0.3% below VWAP)
        for i in range(3):
            candle = make_candle(
                symbol="AAPL",
                close=99.7,  # Only 0.3% below 100
                low=99.7,
                volume=100_000,
                timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        # Reclaim with shallow pullback — should reset to ABOVE_VWAP
        reclaim = make_candle(
            symbol="AAPL",
            close=100.2,
            low=99.7,
            volume=150_000,
            timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
        )
        signal = await strategy.on_candle(reclaim)

        assert signal is None
        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ABOVE_VWAP  # Reset for retry

    @pytest.mark.asyncio
    async def test_below_vwap_to_exhausted_on_deep_pullback(self) -> None:
        """BELOW_VWAP → EXHAUSTED when pullback exceeds max_pullback_pct."""
        config = make_vwap_reclaim_config(
            max_pullback_pct=0.01,  # 1% max
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above VWAP
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5)
        )

        # First bar below VWAP (transitions to BELOW_VWAP)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.8,
                high=100.0,
                low=99.5,  # Initial pullback
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )

        # Second bar — deep pullback (2% below VWAP, exceeds 1% max)
        deep = make_candle(
            symbol="AAPL",
            close=98.5,
            high=99.0,
            low=98.0,  # 2% below VWAP
            timestamp=datetime(2026, 2, 15, 15, 32, 0, tzinfo=UTC),
        )
        await strategy.on_candle(deep)

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.EXHAUSTED

    @pytest.mark.asyncio
    async def test_exhausted_ignores_further_candles(self) -> None:
        """EXHAUSTED state ignores all further candles."""
        config = make_vwap_reclaim_config(max_pullback_pct=0.01)
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above, then exhaust
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=98.0,
                low=98.0,
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )

        # Further candles should be ignored
        for i in range(5):
            signal = await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=101.0 + i,  # Would be valid reclaim
                    timestamp=datetime(2026, 2, 15, 15, 35 + i, 0, tzinfo=UTC),
                )
            )
            assert signal is None

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.EXHAUSTED

    @pytest.mark.asyncio
    async def test_entered_ignores_further_candles(self) -> None:
        """ENTERED state ignores all further candles."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Get to ENTERED state
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.5,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                low=99.5,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )
        assert signal is not None

        # Further candles should be ignored
        signal2 = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=102.0,
                timestamp=datetime(2026, 2, 15, 15, 40, 0, tzinfo=UTC),
            )
        )
        assert signal2 is None

    @pytest.mark.asyncio
    async def test_multiple_pullback_attempts(self) -> None:
        """Multiple pullback attempts: above → below → above (no entry) → below → entry."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.005,  # 0.5% required
            min_pullback_bars=2,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        base_time = datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC)

        # First: above VWAP
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                high=101.0,
                low=100.5,
                timestamp=base_time,
            )
        )

        # First pullback: too shallow (0.3% — need 0.5%)
        # low=99.7 means pullback = (100-99.7)/100 = 0.3%
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.7,
                high=100.0,
                low=99.7,  # Explicitly set low to match close
                timestamp=base_time + timedelta(minutes=1),
            )
        )
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.7,
                high=99.8,
                low=99.7,  # Explicitly set low
                timestamp=base_time + timedelta(minutes=2),
            )
        )

        # Reclaim fails (too shallow), resets to ABOVE_VWAP
        signal1 = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.3,
                low=99.8,
                timestamp=base_time + timedelta(minutes=3),
            )
        )
        assert signal1 is None
        assert strategy._get_symbol_state("AAPL").state == VwapState.ABOVE_VWAP

        # Second pullback: deep enough (1%)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                high=99.5,
                low=99.0,
                timestamp=base_time + timedelta(minutes=4),
            )
        )
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                high=99.2,
                low=99.0,
                timestamp=base_time + timedelta(minutes=5),
            )
        )

        # Successful reclaim
        signal2 = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.3,
                low=99.5,
                volume=150_000,
                timestamp=base_time + timedelta(minutes=6),
            )
        )
        assert signal2 is not None
        assert strategy._get_symbol_state("AAPL").state == VwapState.ENTERED

    @pytest.mark.asyncio
    async def test_pullback_low_tracks_lowest_low_across_bars(self) -> None:
        """pullback_low tracks the lowest low across all bars below VWAP."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        # Pull back with varying lows
        lows = [99.5, 99.0, 99.3, 98.8, 99.2]
        for i, low in enumerate(lows):
            candle = make_candle(
                symbol="AAPL",
                close=99.5,
                low=low,
                timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
            )
            await strategy.on_candle(candle)

        state = strategy._get_symbol_state("AAPL")
        assert state.pullback_low == 98.8  # Minimum of all lows

    @pytest.mark.asyncio
    async def test_close_equals_vwap_in_below_vwap_increments_counter(self) -> None:
        """Candle with close == VWAP in BELOW_VWAP state increments bars_below_vwap.

        When close exactly equals VWAP while in BELOW_VWAP state, it should:
        - Increment bars_below_vwap
        - Update pullback_low if candle.low is lower
        - NOT trigger a reclaim (reclaim requires close > VWAP)
        """
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=5,  # Need 5 bars for entry
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above VWAP
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                timestamp=datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC),
            )
        )

        # First bar below VWAP (transitions to BELOW_VWAP)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.5,
                low=99.0,
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )
        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.BELOW_VWAP
        assert state.bars_below_vwap == 1
        assert state.pullback_low == 99.0

        # Second bar: close exactly at VWAP (100.0)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.0,  # Exactly at VWAP
                low=98.5,  # New low
                timestamp=datetime(2026, 2, 15, 15, 32, 0, tzinfo=UTC),
            )
        )

        # Should NOT trigger reclaim
        assert signal is None
        # Should increment bar count
        assert state.bars_below_vwap == 2
        # Should update pullback_low
        assert state.pullback_low == 98.5
        # Should still be in BELOW_VWAP state
        assert state.state == VwapState.BELOW_VWAP

        # Third bar: still at VWAP
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.0,  # Exactly at VWAP again
                low=98.5,
                timestamp=datetime(2026, 2, 15, 15, 33, 0, tzinfo=UTC),
            )
        )
        assert state.bars_below_vwap == 3
        assert state.state == VwapState.BELOW_VWAP


class TestEntryConditionRejections:
    """Tests for entry condition rejections."""

    @pytest.mark.asyncio
    async def test_reject_pullback_too_shallow(self) -> None:
        """Reject when pullback depth < min_pullback_pct."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.01,  # 1% required
            min_pullback_bars=1,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5)
        )

        # Shallow pullback (0.3% — need 1%)
        # low=99.7 means pullback = (100-99.7)/100 = 0.3%
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.7,
                high=100.0,
                low=99.7,  # Explicitly shallow
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )

        # Reclaim
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                high=100.3,
                low=99.8,
                timestamp=datetime(2026, 2, 15, 15, 32, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_pullback_too_few_bars(self) -> None:
        """Reject when bars_below_vwap < min_pullback_bars."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.001,
            min_pullback_bars=5,  # 5 bars required
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        # Only 2 bars below VWAP
        for i in range(2):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim with only 2 bars (need 5)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_volume_not_confirmed(self) -> None:
        """Reject when reclaim volume < required (avg × multiplier)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=2.0,  # Need 2x average
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Go above with 100K volume
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000)
        )

        # Pull back with 100K volume
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim with 150K volume (average is 100K, need 200K)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,  # < 2x average
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_chase_protection_triggered(self) -> None:
        """Reject when close > VWAP × (1 + max_chase_above_vwap_pct)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_chase_above_vwap_pct=0.003,  # 0.3% max chase
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))

        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim too far above VWAP (0.5%)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.5,  # 0.5% above VWAP, max is 0.3%
                volume=200_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_before_earliest_entry_time(self) -> None:
        """Reject when candle time < earliest_entry."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            earliest_entry="10:30",  # 10:30 AM ET
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # All candles at 10:00-10:10 AM ET (15:00-15:10 UTC in February)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),  # 10:00 AM ET
            )
        )

        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    timestamp=datetime(2026, 2, 15, 15, 1 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim at 10:10 AM ET (before 10:30 AM ET)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 10, 0, tzinfo=UTC),  # 10:10 AM ET
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_after_latest_entry_time(self) -> None:
        """Reject when candle time >= latest_entry."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            latest_entry="11:30",  # 11:30 AM ET
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Set up pullback at 11:00 AM ET (16:00 UTC)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                timestamp=datetime(2026, 2, 15, 16, 0, 0, tzinfo=UTC),
            )
        )

        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    timestamp=datetime(2026, 2, 15, 16, 1 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim at 11:35 AM ET (16:35 UTC) — after latest_entry
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 16, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_max_trades_per_day_reached(self) -> None:
        """Reject when max_trades_per_day reached."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_trades_per_day=2,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record 2 trades already
        strategy.record_trade_result(100)
        strategy.record_trade_result(100)

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_reject_max_concurrent_positions_reached(self) -> None:
        """Reject when max_concurrent_positions reached."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_concurrent_positions=1,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # AAPL enters first
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=101.0,
                volume=100_000,
                timestamp=datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC),
            )
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )
        signal1 = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )
        assert signal1 is not None

        # MSFT tries to enter — should be rejected
        await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                close=201.0,
                volume=100_000,
                timestamp=datetime(2026, 2, 15, 15, 40, 0, tzinfo=UTC),
            )
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="MSFT",
                    close=199.0,
                    low=199.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 41 + i, 0, tzinfo=UTC),
                )
            )
        signal2 = await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                close=200.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 45, 0, tzinfo=UTC),
            )
        )
        assert signal2 is None

    @pytest.mark.asyncio
    async def test_zero_allocated_capital_signal_still_fires(self) -> None:
        """Signal fires even with allocated_capital=0; share_count=0 deferred to Dynamic Sizer."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        # Don't set allocated_capital (defaults to 0)
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        assert signal.share_count == 0  # Dynamic Sizer will determine shares

    @pytest.mark.asyncio
    async def test_reject_internal_risk_limits_hit(self) -> None:
        """Reject when internal risk limits (daily loss) hit."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_daily_loss_pct=0.03,  # 3% max
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Record 3% loss (hits internal limit)
        strategy.record_trade_result(-3000)

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is None


class TestSignalConstruction:
    """Tests for signal construction details."""

    @pytest.mark.asyncio
    async def test_signal_stop_at_pullback_low_minus_buffer(self) -> None:
        """Stop price = pullback_low × (1 - stop_buffer_pct)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            stop_buffer_pct=0.001,  # 0.1%
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,  # pullback_low = 99.0
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        # Stop = 99.0 × (1 - 0.001) = 99.0 × 0.999 = 98.901
        assert signal.stop_price == pytest.approx(98.901)

    @pytest.mark.asyncio
    async def test_signal_targets_at_correct_r_multiples(self) -> None:
        """Target prices are entry + (risk × target_r)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            target_1_r=1.0,
            target_2_r=2.0,
            stop_buffer_pct=0.0,  # No buffer for clean math
            max_chase_above_vwap_pct=0.01,  # Allow 1% chase for test
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5, volume=100_000)
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,  # pullback_low = 99.0, stop = 99.0
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.5,  # Entry = 100.5 (within 1% chase)
                high=100.6,
                low=99.5,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        # Risk = 100.5 - 99 = 1.5
        # T1 = 100.5 + 1.5 × 1.0 = 102.0
        # T2 = 100.5 + 1.5 × 2.0 = 103.5
        assert signal.target_prices == (102.0, 103.5)

    @pytest.mark.asyncio
    async def test_signal_time_stop_seconds_matches_config(self) -> None:
        """time_stop_seconds = time_stop_minutes × 60."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            time_stop_minutes=45,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        assert signal.time_stop_seconds == 45 * 60

    @pytest.mark.asyncio
    async def test_signal_share_count_is_zero(self) -> None:
        """Share count is 0 — deferred to Dynamic Sizer (Sprint 24 S6a)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_loss_per_trade_pct=0.01,  # 1%
            stop_buffer_pct=0.0,
            max_chase_above_vwap_pct=0.01,  # Allow 1% chase for test
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5, volume=100_000)
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,  # Stop = 99
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.5,  # Entry = 100.5, within 1% chase
                high=101.0,
                low=100.0,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        # share_count deferred to Dynamic Sizer (Sprint 24 S6a)
        assert signal.share_count == 0

    @pytest.mark.asyncio
    async def test_signal_rationale_includes_key_values(self) -> None:
        """Rationale includes VWAP, pullback_low, bars_below."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        assert "VWAP" in signal.rationale
        assert "AAPL" in signal.rationale
        assert "100.00" in signal.rationale  # VWAP
        assert "99.00" in signal.rationale  # pullback_low
        assert "3 bars" in signal.rationale

    def test_minimum_risk_floor_prevents_oversizing(self) -> None:
        """Minimum risk floor (0.3% of entry) prevents huge positions.

        When the stop is very close to entry, the minimum risk floor
        (0.3% of entry price) is used instead to prevent enormous positions.
        This tests calculate_position_size directly.
        """
        config = make_vwap_reclaim_config(max_loss_per_trade_pct=0.01)
        strategy = VwapReclaimStrategy(config)
        strategy.allocated_capital = 100_000

        # Entry = 100, Stop = 99.9 (only 0.1 risk, but floor is 0.3)
        # Actual risk = 100 - 99.9 = 0.1
        # Min risk floor = 100 × 0.003 = 0.3
        # Effective risk = max(0.1, 0.3) = 0.3
        # Shares = 1000 / 0.3 = 3333
        shares = strategy.calculate_position_size(entry_price=100.0, stop_price=99.9)
        assert shares == 3333

        # Entry = 100, Stop = 98 (2.0 risk, > floor of 0.3)
        # Actual risk = 100 - 98 = 2
        # Min risk floor = 100 × 0.003 = 0.3
        # Effective risk = max(2, 0.3) = 2
        # Shares = 1000 / 2 = 500
        shares = strategy.calculate_position_size(entry_price=100.0, stop_price=98.0)
        assert shares == 500


class TestEdgeCases:
    """Tests for edge cases."""

    @pytest.mark.asyncio
    async def test_vwap_not_available_returns_none(self) -> None:
        """Returns None when VWAP not available from data service."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=None)  # No VWAP
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        signal = await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))
        assert signal is None

    @pytest.mark.asyncio
    async def test_symbol_not_in_watchlist_ignored(self) -> None:
        """Candles for symbols not in watchlist are ignored."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["MSFT"])  # Only MSFT

        # AAPL should be ignored
        signal = await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))
        assert signal is None
        assert "AAPL" not in strategy._symbol_state

    @pytest.mark.asyncio
    async def test_candle_exactly_at_vwap_treated_as_below(self) -> None:
        """Close == VWAP is not above VWAP (no transition from WATCHING)."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Close exactly at VWAP
        await strategy.on_candle(make_candle(symbol="AAPL", close=100.0))

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.WATCHING

    @pytest.mark.asyncio
    async def test_zero_volume_candle_handled(self) -> None:
        """Zero volume candle is handled without error."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Zero volume candle
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=0))

        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ABOVE_VWAP
        assert 0 in state.recent_volumes

    @pytest.mark.asyncio
    async def test_no_data_service_returns_none(self) -> None:
        """Returns None when no data service is configured."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config, data_service=None)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        signal = await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))
        assert signal is None

    def test_negative_allocated_capital_raises_error(self) -> None:
        """Setting negative allocated_capital raises ValueError."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        with pytest.raises(ValueError, match="cannot be negative"):
            strategy.allocated_capital = -10_000

    @pytest.mark.asyncio
    async def test_single_bar_below_vwap_not_enough(self) -> None:
        """Single bar below VWAP is not enough when min_pullback_bars=3."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))

        # Only 1 bar below VWAP
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.0,
                low=99.0,
                volume=100_000,
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )

        # Immediate reclaim — should fail min_pullback_bars
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 32, 0, tzinfo=UTC),
            )
        )

        assert signal is None

    @pytest.mark.asyncio
    async def test_pullback_low_updates_on_each_bar_below(self) -> None:
        """pullback_low is updated to minimum on each bar below VWAP."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        # First bar below
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.5,
                low=99.5,
                timestamp=datetime(2026, 2, 15, 15, 31, 0, tzinfo=UTC),
            )
        )
        state = strategy._get_symbol_state("AAPL")
        assert state.pullback_low == 99.5

        # Second bar — lower low
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.3,
                low=99.0,
                timestamp=datetime(2026, 2, 15, 15, 32, 0, tzinfo=UTC),
            )
        )
        assert state.pullback_low == 99.0

        # Third bar — higher low (should not update)
        await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=99.4,
                low=99.2,
                timestamp=datetime(2026, 2, 15, 15, 33, 0, tzinfo=UTC),
            )
        )
        assert state.pullback_low == 99.0


class TestOtherMethods:
    """Tests for other strategy methods."""

    def test_get_scanner_criteria_matches_orb(self) -> None:
        """Scanner criteria matches ORB strategies."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        criteria = strategy.get_scanner_criteria()

        assert criteria.min_price == 10.0
        assert criteria.max_price == 200.0
        assert criteria.min_volume_avg_daily == 1_000_000
        assert criteria.min_relative_volume == 2.0
        assert criteria.min_gap_pct == 0.02
        assert criteria.max_results == 20

    def test_get_exit_rules_has_two_targets(self) -> None:
        """Exit rules have two profit targets."""
        config = make_vwap_reclaim_config(target_1_r=1.0, target_2_r=2.0)
        strategy = VwapReclaimStrategy(config)

        rules = strategy.get_exit_rules()

        assert len(rules.targets) == 2
        assert rules.targets[0].r_multiple == 1.0
        assert rules.targets[0].position_pct == 0.5
        assert rules.targets[1].r_multiple == 2.0
        assert rules.targets[1].position_pct == 0.5

    def test_get_exit_rules_time_stop(self) -> None:
        """Exit rules have time stop in minutes."""
        config = make_vwap_reclaim_config(time_stop_minutes=45)
        strategy = VwapReclaimStrategy(config)

        rules = strategy.get_exit_rules()

        assert rules.time_stop_minutes == 45

    def test_get_market_conditions_filter_allows_correct_regimes(self) -> None:
        """Market conditions filter allows trending, range-bound, high volatility."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        filter = strategy.get_market_conditions_filter()

        assert "bullish_trending" in filter.allowed_regimes
        assert "range_bound" in filter.allowed_regimes
        assert "high_volatility" in filter.allowed_regimes

    def test_get_market_conditions_filter_max_vix(self) -> None:
        """Market conditions filter has max VIX of 35."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        filter = strategy.get_market_conditions_filter()

        assert filter.max_vix == 35.0

    def test_reset_daily_state_clears_symbol_states(self) -> None:
        """reset_daily_state clears all symbol states."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        # Add some state
        state = strategy._get_symbol_state("AAPL")
        state.state = VwapState.ABOVE_VWAP
        state.bars_below_vwap = 5

        strategy.reset_daily_state()

        assert "AAPL" not in strategy._symbol_state

    def test_mark_position_closed_resets_flag(self) -> None:
        """mark_position_closed sets position_active to False."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)

        state = strategy._get_symbol_state("AAPL")
        state.position_active = True

        strategy.mark_position_closed("AAPL")

        assert state.position_active is False

    def test_calculate_position_size_standard_formula(self) -> None:
        """Position size uses standard formula."""
        config = make_vwap_reclaim_config(max_loss_per_trade_pct=0.01)
        strategy = VwapReclaimStrategy(config)
        strategy.allocated_capital = 100_000

        # Risk = 100 - 98 = 2
        # Risk dollars = 100K × 1% = 1000
        # Shares = 1000 / 2 = 500
        shares = strategy.calculate_position_size(100.0, 98.0)
        assert shares == 500

    def test_calculate_position_size_invalid_long(self) -> None:
        """Position size returns 0 for invalid long (stop >= entry)."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config)
        strategy.allocated_capital = 100_000

        assert strategy.calculate_position_size(100.0, 100.0) == 0
        assert strategy.calculate_position_size(100.0, 101.0) == 0


class TestVolumeAveraging:
    """Tests for volume averaging logic."""

    @pytest.mark.asyncio
    async def test_volume_average_includes_all_bars(self) -> None:
        """Volume average includes all bars seen."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        volumes = [100_000, 150_000, 80_000, 120_000]
        for i, vol in enumerate(volumes):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=101.0,
                    volume=vol,
                    timestamp=datetime(2026, 2, 15, 15, 30 + i, 0, tzinfo=UTC),
                )
            )

        state = strategy._get_symbol_state("AAPL")
        assert len(state.recent_volumes) == 4
        assert sum(state.recent_volumes) / len(state.recent_volumes) == 112_500

    @pytest.mark.asyncio
    async def test_volume_average_with_single_bar(self) -> None:
        """Volume average with single bar is that bar's volume."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=75_000))

        state = strategy._get_symbol_state("AAPL")
        assert len(state.recent_volumes) == 1
        assert state.recent_volumes[0] == 75_000

    @pytest.mark.asyncio
    async def test_reclaim_volume_vs_average_threshold(self) -> None:
        """Reclaim volume must be >= average × multiplier."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.5,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Average volume = 100K
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim with 140K (< 150K required)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=140_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )
        assert signal is None

    @pytest.mark.asyncio
    async def test_high_volume_reclaim_passes(self) -> None:
        """Reclaim with high volume passes volume check."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.5,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # Average volume = 100K
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0, volume=100_000))
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )

        # Reclaim with 200K (> 150K required)
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=200_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )
        assert signal is not None


class TestTimezoneHandling:
    """Tests for correct timezone handling.

    The strategy stores time constants in ET (10:00 AM earliest, etc.) but
    receives candles with UTC timestamps. These tests verify that UTC timestamps
    are correctly converted to ET for time window comparisons.

    For February 2026 (EST, UTC-5):
    - 10:00 AM ET = 15:00 UTC
    - 11:00 AM ET = 16:00 UTC
    - 12:00 PM ET = 17:00 UTC
    """

    def test_utc_candle_at_10am_et_in_entry_window(self) -> None:
        """A candle at 15:00 UTC (10:00 AM EST) is in entry window."""
        config = make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00")
        strategy = VwapReclaimStrategy(config)

        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC),  # 10:00 AM EST
        )

        assert strategy._is_in_entry_window(candle) is True

    def test_utc_candle_before_10am_et_not_in_window(self) -> None:
        """A candle at 14:59 UTC (9:59 AM EST) is not in entry window."""
        config = make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00")
        strategy = VwapReclaimStrategy(config)

        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 14, 59, 0, tzinfo=UTC),  # 9:59 AM EST
        )

        assert strategy._is_in_entry_window(candle) is False

    def test_utc_candle_at_12pm_et_not_in_window(self) -> None:
        """A candle at 17:00 UTC (12:00 PM EST) is not in entry window."""
        config = make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00")
        strategy = VwapReclaimStrategy(config)

        candle = make_candle(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 15, 17, 0, 0, tzinfo=UTC),  # 12:00 PM EST
        )

        assert strategy._is_in_entry_window(candle) is False

    def test_dst_transition_edt_to_est(self) -> None:
        """Verify correct handling across DST boundary.

        In early November, clocks "fall back". A timestamp at 15:00 UTC is:
        - During DST (EDT): 11:00 AM
        - After DST ends (EST): 10:00 AM
        """
        config = make_vwap_reclaim_config(earliest_entry="10:00", latest_entry="12:00")
        strategy = VwapReclaimStrategy(config)

        # November 5, 2025 is after DST ends (EST, UTC-5)
        # 15:00 UTC = 10:00 AM EST = in window
        candle_est = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 11, 5, 15, 0, 0, tzinfo=UTC),
        )
        assert strategy._is_in_entry_window(candle_est) is True

        # June 2, 2025 is during DST (EDT, UTC-4)
        # 15:00 UTC = 11:00 AM EDT = in window
        candle_edt = make_candle(
            symbol="AAPL",
            timestamp=datetime(2025, 6, 2, 15, 0, 0, tzinfo=UTC),
        )
        assert strategy._is_in_entry_window(candle_edt) is True

    @pytest.mark.asyncio
    async def test_full_flow_with_utc_timestamps(self) -> None:
        """Full flow with UTC timestamps produces valid signal."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            earliest_entry="10:00",
            latest_entry="12:00",
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # All timestamps in UTC, strategy converts to ET
        # 10:00 AM ET = 15:00 UTC in February (EST)
        base_time = datetime(2026, 2, 15, 15, 0, 0, tzinfo=UTC)

        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000, timestamp=base_time)
        )

        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=base_time + timedelta(minutes=1 + i),
                )
            )

        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=base_time + timedelta(minutes=5),  # 10:05 AM ET
            )
        )

        assert signal is not None
        assert signal.symbol == "AAPL"


class TestSetDataService:
    """Tests for set_data_service method."""

    def test_set_data_service_updates_reference(self) -> None:
        """set_data_service updates the internal data service reference."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config, data_service=None)

        mock_ds = MockDataService(vwap=100.0)
        strategy.set_data_service(mock_ds)

        assert strategy._data_service is mock_ds

    @pytest.mark.asyncio
    async def test_set_data_service_enables_vwap_queries(self) -> None:
        """After set_data_service, strategy can query VWAP."""
        config = make_vwap_reclaim_config()
        strategy = VwapReclaimStrategy(config, data_service=None)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        # No data service — stays in watching (VWAP returns None)
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5)
        )
        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.WATCHING

        # Reset and set data service
        strategy.reset_daily_state()
        strategy.set_watchlist(["AAPL"])  # Watchlist cleared by reset
        mock_ds = MockDataService(vwap=100.0)
        strategy.set_data_service(mock_ds)

        # Now transitions properly
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5)
        )
        state = strategy._get_symbol_state("AAPL")
        assert state.state == VwapState.ABOVE_VWAP


class TestMultipleSymbols:
    """Tests for multi-symbol handling."""

    @pytest.mark.asyncio
    async def test_independent_state_per_symbol(self) -> None:
        """Each symbol has independent state tracking."""
        config = make_vwap_reclaim_config()
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        # AAPL above VWAP
        await strategy.on_candle(make_candle(symbol="AAPL", close=101.0))

        # MSFT stays watching
        await strategy.on_candle(make_candle(symbol="MSFT", close=99.0))

        aapl_state = strategy._get_symbol_state("AAPL")
        msft_state = strategy._get_symbol_state("MSFT")

        assert aapl_state.state == VwapState.ABOVE_VWAP
        assert msft_state.state == VwapState.WATCHING

    @pytest.mark.asyncio
    async def test_multiple_symbols_can_enter(self) -> None:
        """Multiple symbols can enter positions."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            max_concurrent_positions=3,
            volume_confirmation_multiplier=1.0,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL", "MSFT"])

        base_time = datetime(2026, 2, 15, 15, 30, 0, tzinfo=UTC)

        # AAPL enters
        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, volume=100_000, timestamp=base_time)
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=base_time + timedelta(minutes=1 + i),
                )
            )
        signal1 = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.2,
                volume=150_000,
                timestamp=base_time + timedelta(minutes=5),
            )
        )
        assert signal1 is not None

        # MSFT enters separately
        await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                close=101.0,
                volume=100_000,
                timestamp=base_time + timedelta(minutes=10),
            )
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="MSFT",
                    close=99.0,
                    low=99.0,
                    volume=100_000,
                    timestamp=base_time + timedelta(minutes=11 + i),
                )
            )
        signal2 = await strategy.on_candle(
            make_candle(
                symbol="MSFT",
                close=100.2,
                volume=150_000,
                timestamp=base_time + timedelta(minutes=15),
            )
        )
        assert signal2 is not None
        assert signal2.symbol == "MSFT"


# ---------------------------------------------------------------------------
# Sprint 24 S2: Pattern Strength Tests
# ---------------------------------------------------------------------------


class TestPatternStrength:
    """Tests for VWAP Reclaim pattern_strength scoring (Sprint 24 S2)."""

    def _make_strategy(self, **kwargs) -> VwapReclaimStrategy:
        config = make_vwap_reclaim_config(max_pullback_pct=0.02, **kwargs)
        return VwapReclaimStrategy(config)

    def _make_state(
        self,
        pullback_low: float = 99.2,
        bars_below_vwap: int = 3,
        volumes: list | None = None,
        below_vwap_entries: int = 1,
    ) -> VwapSymbolState:
        return VwapSymbolState(
            pullback_low=pullback_low,
            bars_below_vwap=bars_below_vwap,
            recent_volumes=volumes if volumes is not None else [100_000, 100_000, 100_000, 200_000],
            below_vwap_entries=below_vwap_entries,
        )

    def test_vwap_pattern_strength_varies_with_path_quality(self) -> None:
        """Clean path scores higher than choppy path."""
        strategy = self._make_strategy()
        vwap = 100.0
        candle = make_candle(close=100.2, volume=200_000)
        state_clean = self._make_state(below_vwap_entries=1)
        state_choppy = self._make_state(below_vwap_entries=3)

        strength_clean, ctx_clean = strategy._calculate_pattern_strength(candle, state_clean, vwap)
        strength_choppy, ctx_choppy = strategy._calculate_pattern_strength(
            candle, state_choppy, vwap
        )

        assert strength_clean > strength_choppy
        assert ctx_clean["path_quality"] == "clean"
        assert ctx_choppy["path_quality"] == "choppy"

    def test_vwap_pattern_strength_varies_with_pullback_depth(self) -> None:
        """Optimal pullback depth ratio (0.4x) scores higher than extremes."""
        strategy = self._make_strategy()
        vwap = 100.0
        candle = make_candle(close=100.2, volume=200_000)

        # Optimal: depth_ratio = 0.4 → pullback_low = vwap * (1 - 0.4 * max_pullback_pct)
        state_optimal = self._make_state(pullback_low=99.2)  # 0.8% depth -> ratio 0.4
        # Too shallow: ratio ~0.1 -> pullback_low ~99.8 (0.2% depth)
        state_shallow = self._make_state(pullback_low=99.8)
        # Too deep: ratio ~0.9 -> pullback_low ~98.2 (1.8% depth)
        state_deep = self._make_state(pullback_low=98.2)

        strength_optimal, _ = strategy._calculate_pattern_strength(candle, state_optimal, vwap)
        strength_shallow, _ = strategy._calculate_pattern_strength(candle, state_shallow, vwap)
        strength_deep, _ = strategy._calculate_pattern_strength(candle, state_deep, vwap)

        assert strength_optimal > strength_shallow
        assert strength_optimal > strength_deep

    def test_vwap_pattern_strength_varies_with_reclaim_volume(self) -> None:
        """Higher reclaim volume ratio produces higher volume credit."""
        strategy = self._make_strategy()
        vwap = 100.0
        state = self._make_state(pullback_low=99.2, bars_below_vwap=3)

        # Avg pullback = 100_000; high reclaim = 200_000 (2.0x) -> volume_credit = 80
        candle_high = make_candle(close=100.2, volume=200_000)
        # Low reclaim = 70_000 (0.7x) -> volume_credit = 30
        candle_low = make_candle(close=100.2, volume=70_000)

        strength_high, ctx_high = strategy._calculate_pattern_strength(candle_high, state, vwap)
        strength_low, ctx_low = strategy._calculate_pattern_strength(candle_low, state, vwap)

        assert strength_high > strength_low
        assert ctx_high["volume_credit"] == pytest.approx(80.0)
        assert ctx_low["volume_credit"] == pytest.approx(30.0)

    def test_vwap_pattern_strength_range(self) -> None:
        """All pattern_strength outputs are in [0, 100]."""
        strategy = self._make_strategy()
        vwap = 100.0

        test_cases = [
            # (pullback_low, bars, volumes, entries, close, vol)
            (99.2, 3, [100_000, 100_000, 100_000, 200_000], 1, 100.1, 200_000),
            (99.8, 1, [100_000, 50_000], 3, 100.05, 50_000),
            (98.5, 5, [100_000] * 5 + [300_000], 2, 100.3, 300_000),
            (99.0, 2, [50_000, 50_000, 10_000], 4, 100.5, 10_000),
            (99.5, 4, [200_000] * 4 + [400_000], 1, 100.01, 400_000),
        ]
        for pullback_low, bars, vols, entries, close, cvol in test_cases:
            state = VwapSymbolState(
                pullback_low=pullback_low,
                bars_below_vwap=bars,
                recent_volumes=vols,
                below_vwap_entries=entries,
            )
            candle = make_candle(close=close, volume=cvol)
            strength, _ = strategy._calculate_pattern_strength(candle, state, vwap)
            assert 0.0 <= strength <= 100.0, f"strength={strength} out of [0, 100] for {close}"

    @pytest.mark.asyncio
    async def test_vwap_signal_share_count_zero(self) -> None:
        """Signal share_count is 0 — deferred to Dynamic Sizer (Sprint 24 S6a)."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
            max_chase_above_vwap_pct=0.01,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5, volume=100_000)
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.3,
                high=101.0,
                low=100.0,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        assert signal.share_count == 0

    @pytest.mark.asyncio
    async def test_vwap_signal_context_populated(self) -> None:
        """Signal context contains all expected keys and pattern_strength is in [0, 100]."""
        config = make_vwap_reclaim_config(
            min_pullback_pct=0.002,
            min_pullback_bars=3,
            volume_confirmation_multiplier=1.0,
            max_chase_above_vwap_pct=0.01,
        )
        mock_ds = MockDataService(vwap=100.0)
        strategy = VwapReclaimStrategy(config, data_service=mock_ds)
        strategy.allocated_capital = 100_000
        strategy.set_watchlist(["AAPL"])

        await strategy.on_candle(
            make_candle(symbol="AAPL", close=101.0, high=101.0, low=100.5, volume=100_000)
        )
        for i in range(3):
            await strategy.on_candle(
                make_candle(
                    symbol="AAPL",
                    close=99.0,
                    high=99.5,
                    low=99.0,
                    volume=100_000,
                    timestamp=datetime(2026, 2, 15, 15, 31 + i, 0, tzinfo=UTC),
                )
            )
        signal = await strategy.on_candle(
            make_candle(
                symbol="AAPL",
                close=100.3,
                high=101.0,
                low=100.0,
                volume=150_000,
                timestamp=datetime(2026, 2, 15, 15, 35, 0, tzinfo=UTC),
            )
        )

        assert signal is not None
        expected_keys = {
            "path_quality",
            "pullback_depth_ratio",
            "reclaim_volume_ratio",
            "vwap_distance_pct",
            "path_credit",
            "depth_credit",
            "volume_credit",
            "distance_credit",
        }
        assert expected_keys.issubset(signal.signal_context.keys())
        assert 0.0 <= signal.pattern_strength <= 100.0
