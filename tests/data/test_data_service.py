"""Tests for the Data Service module."""

import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent
from argus.data.replay_data_service import ReplayDataService
from argus.data.service import DataService


def generate_test_parquet(
    symbol: str,
    output_dir: Path,
    start_time: datetime | None = None,
    num_candles: int = 100,
    base_price: float = 100.0,
    volatility: float = 0.02,
    base_volume: int = 100_000,
) -> Path:
    """Generate a synthetic 1m Parquet file for testing.

    Creates realistic-ish OHLCV data with configurable parameters.

    Args:
        symbol: Ticker symbol (used for filename).
        output_dir: Directory to write the Parquet file.
        start_time: Starting timestamp. Defaults to market open today.
        num_candles: Number of 1-minute candles to generate.
        base_price: Starting price.
        volatility: Price volatility factor.
        base_volume: Base volume per candle.

    Returns:
        Path to the generated Parquet file.
    """
    import random

    random.seed(42)  # Reproducible test data

    if start_time is None:
        today = datetime.now(UTC).date()
        start_time = datetime(today.year, today.month, today.day, 14, 30, 0, tzinfo=UTC)

    timestamps = []
    opens = []
    highs = []
    lows = []
    closes = []
    volumes = []

    price = base_price

    for i in range(num_candles):
        timestamp = start_time + timedelta(minutes=i)
        timestamps.append(timestamp)

        # Random walk for price
        change_pct = random.uniform(-volatility, volatility)
        open_price = price
        close_price = price * (1 + change_pct)

        # High/low within the range
        high_price = max(open_price, close_price) * (1 + random.uniform(0, volatility / 2))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, volatility / 2))

        opens.append(open_price)
        highs.append(high_price)
        lows.append(low_price)
        closes.append(close_price)
        volumes.append(int(base_volume * random.uniform(0.5, 2.0)))

        price = close_price

    df = pd.DataFrame(
        {
            "timestamp": timestamps,
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": volumes,
        }
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    file_path = output_dir / f"{symbol.upper()}.parquet"
    df.to_parquet(file_path, index=False)

    return file_path


class TestReplayDataService:
    """Tests for the ReplayDataService implementation."""

    @pytest.mark.asyncio
    async def test_loads_and_publishes_candle_events(self, tmp_path: Path) -> None:
        """ReplayDataService loads Parquet and publishes CandleEvents."""
        generate_test_parquet("TEST", tmp_path, num_candles=10)

        bus = EventBus()
        candles: list[CandleEvent] = []
        bus.subscribe(CandleEvent, candles.append)

        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        assert len(candles) == 10
        assert all(c.symbol == "TEST" for c in candles)
        assert all(c.timeframe == "1m" for c in candles)

        await service.stop()

    @pytest.mark.asyncio
    async def test_candles_published_in_chronological_order(self, tmp_path: Path) -> None:
        """CandleEvents are published in chronological order."""
        generate_test_parquet("TEST", tmp_path, num_candles=20)

        bus = EventBus()
        candles: list[CandleEvent] = []
        bus.subscribe(CandleEvent, candles.append)

        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        # Verify timestamps are in order
        for i in range(1, len(candles)):
            assert candles[i].timestamp >= candles[i - 1].timestamp

        await service.stop()

    @pytest.mark.asyncio
    async def test_indicator_events_published(self, tmp_path: Path) -> None:
        """IndicatorEvents are published after each CandleEvent."""
        generate_test_parquet("TEST", tmp_path, num_candles=30)

        bus = EventBus()
        indicators: list[IndicatorEvent] = []
        bus.subscribe(IndicatorEvent, indicators.append)

        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        # Should have VWAP from candle 1, ATR from candle 15+, SMAs from 9+
        vwap_events = [i for i in indicators if i.indicator_name == "vwap"]
        assert len(vwap_events) == 30  # VWAP after every candle

        await service.stop()

    @pytest.mark.asyncio
    async def test_get_current_price_returns_latest_close(self, tmp_path: Path) -> None:
        """get_current_price returns the latest close price."""
        generate_test_parquet("TEST", tmp_path, num_candles=10, base_price=150.0)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        price = await service.get_current_price("TEST")
        assert price is not None
        assert price > 0

        await service.stop()

    @pytest.mark.asyncio
    async def test_get_indicator_returns_computed_value(self, tmp_path: Path) -> None:
        """get_indicator returns computed indicator values."""
        generate_test_parquet("TEST", tmp_path, num_candles=30)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        vwap = await service.get_indicator("TEST", "vwap")
        assert vwap is not None
        assert vwap > 0

        sma_9 = await service.get_indicator("TEST", "sma_9")
        assert sma_9 is not None

        sma_20 = await service.get_indicator("TEST", "sma_20")
        assert sma_20 is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_get_indicator_returns_none_before_enough_data(self, tmp_path: Path) -> None:
        """get_indicator returns None before enough candles are processed."""
        generate_test_parquet("TEST", tmp_path, num_candles=5)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        # Only 5 candles, not enough for SMA(9)
        sma_9 = await service.get_indicator("TEST", "sma_9")
        assert sma_9 is None

        # Not enough for ATR(14)
        atr = await service.get_indicator("TEST", "atr_14")
        assert atr is None

        # But VWAP should be available
        vwap = await service.get_indicator("TEST", "vwap")
        assert vwap is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_vwap_resets_on_date_boundary(self, tmp_path: Path) -> None:
        """VWAP resets when date changes."""
        # Create data spanning two days
        day1_start = datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC)
        day2_start = datetime(2026, 2, 16, 14, 30, 0, tzinfo=UTC)

        # Day 1 candles
        df1 = pd.DataFrame(
            {
                "timestamp": [day1_start + timedelta(minutes=i) for i in range(5)],
                "open": [100.0] * 5,
                "high": [101.0] * 5,
                "low": [99.0] * 5,
                "close": [100.5] * 5,
                "volume": [100000] * 5,
            }
        )

        # Day 2 candles with different prices
        df2 = pd.DataFrame(
            {
                "timestamp": [day2_start + timedelta(minutes=i) for i in range(5)],
                "open": [200.0] * 5,
                "high": [201.0] * 5,
                "low": [199.0] * 5,
                "close": [200.5] * 5,
                "volume": [100000] * 5,
            }
        )

        df = pd.concat([df1, df2], ignore_index=True)
        tmp_path.mkdir(parents=True, exist_ok=True)
        df.to_parquet(tmp_path / "TEST.parquet", index=False)

        bus = EventBus()
        vwap_values: list[float] = []

        def track_vwap(event: IndicatorEvent) -> None:
            if event.indicator_name == "vwap":
                vwap_values.append(event.value)

        bus.subscribe(IndicatorEvent, track_vwap)

        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        # Day 1 VWAPs should be around 100, Day 2 around 200
        # The reset should cause a jump
        assert vwap_values[4] < 150  # End of day 1
        assert vwap_values[5] > 150  # Start of day 2 (reset)

        await service.stop()

    @pytest.mark.asyncio
    async def test_atr_returns_none_before_14_candles(self, tmp_path: Path) -> None:
        """ATR returns None before 14 candles are available."""
        generate_test_parquet("TEST", tmp_path, num_candles=13)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        atr = await service.get_indicator("TEST", "atr_14")
        assert atr is None

        await service.stop()

    @pytest.mark.asyncio
    async def test_atr_available_after_14_candles(self, tmp_path: Path) -> None:
        """ATR is available after 14 candles."""
        generate_test_parquet("TEST", tmp_path, num_candles=20)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        atr = await service.get_indicator("TEST", "atr_14")
        assert atr is not None
        assert atr > 0

        await service.stop()

    @pytest.mark.asyncio
    async def test_sma_9_available_after_9_candles(self, tmp_path: Path) -> None:
        """SMA(9) is available after 9 candles."""
        generate_test_parquet("TEST", tmp_path, num_candles=9)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["TEST"], timeframes=["1m"])
        await service.wait_for_completion()

        sma_9 = await service.get_indicator("TEST", "sma_9")
        assert sma_9 is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_missing_parquet_file_raises(self, tmp_path: Path) -> None:
        """Missing Parquet file raises FileNotFoundError."""
        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)

        with pytest.raises(FileNotFoundError, match="NONEXISTENT"):
            await service.start(symbols=["NONEXISTENT"], timeframes=["1m"])

    @pytest.mark.asyncio
    async def test_unsupported_timeframe_logs_warning(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Unsupported timeframe logs warning but continues."""
        generate_test_parquet("TEST", tmp_path, num_candles=5)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)

        with caplog.at_level("WARNING"):
            await service.start(symbols=["TEST"], timeframes=["1m", "5m", "15m"])
            await service.wait_for_completion()

        assert "only supports 1m" in caplog.text
        await service.stop()

    @pytest.mark.asyncio
    async def test_multiple_symbols(self, tmp_path: Path) -> None:
        """ReplayDataService handles multiple symbols."""
        generate_test_parquet("AAPL", tmp_path, num_candles=10, base_price=150.0)
        generate_test_parquet("MSFT", tmp_path, num_candles=10, base_price=350.0)

        bus = EventBus()
        candles: list[CandleEvent] = []
        bus.subscribe(CandleEvent, candles.append)

        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)
        await service.start(symbols=["AAPL", "MSFT"], timeframes=["1m"])
        await service.wait_for_completion()

        assert len(candles) == 20  # 10 from each symbol

        aapl_candles = [c for c in candles if c.symbol == "AAPL"]
        msft_candles = [c for c in candles if c.symbol == "MSFT"]
        assert len(aapl_candles) == 10
        assert len(msft_candles) == 10

        await service.stop()

    @pytest.mark.asyncio
    async def test_stop_cancels_replay(self, tmp_path: Path) -> None:
        """stop() cancels ongoing replay."""
        generate_test_parquet("TEST", tmp_path, num_candles=1000)

        bus = EventBus()
        candles: list[CandleEvent] = []
        bus.subscribe(CandleEvent, candles.append)

        # Use non-zero speed so replay takes time
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=1000)
        await service.start(symbols=["TEST"], timeframes=["1m"])

        # Let it run briefly
        await asyncio.sleep(0.01)

        # Stop should cancel
        await service.stop()

        # Should have processed some but not all candles
        assert len(candles) < 1000


class TestReplayDataServiceFetchDailyBars:
    """Tests for ReplayDataService.fetch_daily_bars()."""

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_returns_none(self, tmp_path: Path) -> None:
        """fetch_daily_bars returns None — not supported in replay mode."""
        generate_test_parquet("TEST", tmp_path, num_candles=10)

        bus = EventBus()
        service = ReplayDataService(event_bus=bus, data_dir=tmp_path, speed=0)

        result = await service.fetch_daily_bars("SPY", lookback_days=60)

        assert result is None


class TestDataServiceABC:
    """Tests for the DataService ABC interface."""

    def test_data_service_is_abstract(self) -> None:
        """DataService cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            DataService()  # type: ignore[abstract]

    def test_replay_data_service_is_subclass(self) -> None:
        """ReplayDataService is a subclass of DataService."""
        assert issubclass(ReplayDataService, DataService)
