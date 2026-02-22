"""Tests for the backtest data service module."""

from datetime import UTC, datetime, timedelta

import pytest

from argus.backtest.backtest_data_service import BacktestDataService
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent


@pytest.fixture
def event_bus() -> EventBus:
    """Create a fresh event bus for each test."""
    return EventBus()


@pytest.fixture
def data_service(event_bus: EventBus) -> BacktestDataService:
    """Create a backtest data service."""
    return BacktestDataService(event_bus)


class TestBacktestDataService:
    """Tests for BacktestDataService class."""

    @pytest.mark.asyncio
    async def test_feed_bar_publishes_candle_event(
        self, event_bus: EventBus, data_service: BacktestDataService
    ) -> None:
        """feed_bar publishes a CandleEvent to the event bus."""
        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        event_bus.subscribe(CandleEvent, handler)

        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        await data_service.feed_bar("AAPL", ts, 100, 105, 98, 104, 50000)
        await event_bus.drain()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].close == 104
        assert received[0].volume == 50000

    @pytest.mark.asyncio
    async def test_feed_bar_publishes_indicator_events(
        self, event_bus: EventBus, data_service: BacktestDataService
    ) -> None:
        """feed_bar publishes IndicatorEvents for computed indicators."""
        indicator_events: list[IndicatorEvent] = []

        async def handler(event: IndicatorEvent) -> None:
            indicator_events.append(event)

        event_bus.subscribe(IndicatorEvent, handler)

        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)

        # Feed enough bars to get indicators
        for i in range(15):
            await data_service.feed_bar(
                "AAPL",
                ts + timedelta(minutes=i),
                100 + i,
                102 + i,
                99 + i,
                101 + i,
                10000,
            )
        await event_bus.drain()

        # VWAP should be published with each bar
        vwap_events = [e for e in indicator_events if e.indicator_name == "vwap"]
        assert len(vwap_events) == 15

        # ATR requires 14 bars with a previous close, so we should have some
        atr_events = [e for e in indicator_events if e.indicator_name == "atr_14"]
        assert len(atr_events) > 0

    @pytest.mark.asyncio
    async def test_get_current_price_after_feed(self, data_service: BacktestDataService) -> None:
        """get_current_price returns the close price from the last feed_bar."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        await data_service.feed_bar("AAPL", ts, 100, 105, 98, 104, 50000)

        price = await data_service.get_current_price("AAPL")
        assert price == 104.0

    @pytest.mark.asyncio
    async def test_get_current_price_case_insensitive(
        self, data_service: BacktestDataService
    ) -> None:
        """get_current_price is case-insensitive."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        await data_service.feed_bar("AAPL", ts, 100, 105, 98, 104, 50000)

        price = await data_service.get_current_price("aapl")
        assert price == 104.0

    @pytest.mark.asyncio
    async def test_get_indicator_returns_vwap(self, data_service: BacktestDataService) -> None:
        """get_indicator returns VWAP after feeding bars."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)

        # Feed several bars
        for i in range(5):
            await data_service.feed_bar(
                "AAPL",
                ts + timedelta(minutes=i),
                100,
                101,
                99,
                100,
                10000,
            )

        vwap = await data_service.get_indicator("AAPL", "vwap")
        assert vwap is not None
        assert vwap > 0

    @pytest.mark.asyncio
    async def test_get_indicator_returns_sma_9(self, data_service: BacktestDataService) -> None:
        """get_indicator returns SMA(9) after 9+ bars."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)

        # Feed 9 bars with varying closes
        closes = [100, 102, 101, 103, 102, 104, 103, 105, 104]
        for i, close in enumerate(closes):
            await data_service.feed_bar(
                "AAPL",
                ts + timedelta(minutes=i),
                close - 1,
                close + 1,
                close - 2,
                close,
                10000,
            )

        sma_9 = await data_service.get_indicator("AAPL", "sma_9")
        assert sma_9 is not None
        expected_sma = sum(closes) / 9
        assert abs(sma_9 - expected_sma) < 0.01

    @pytest.mark.asyncio
    async def test_publish_tick_updates_price_cache(
        self, data_service: BacktestDataService
    ) -> None:
        """publish_tick updates the price cache."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        await data_service.publish_tick("AAPL", 105.50, 100, ts)

        price = await data_service.get_current_price("AAPL")
        assert price == 105.50

    @pytest.mark.asyncio
    async def test_publish_tick_publishes_tick_event(
        self, event_bus: EventBus, data_service: BacktestDataService
    ) -> None:
        """publish_tick publishes a TickEvent to the event bus."""
        received: list[TickEvent] = []

        async def handler(event: TickEvent) -> None:
            received.append(event)

        event_bus.subscribe(TickEvent, handler)

        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        await data_service.publish_tick("AAPL", 105.50, 100, ts)
        await event_bus.drain()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].price == 105.50

    @pytest.mark.asyncio
    async def test_reset_daily_state_resets_vwap(self, data_service: BacktestDataService) -> None:
        """reset_daily_state clears VWAP state."""
        day1_ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)
        day2_ts = datetime(2025, 6, 16, 9, 30, 0, tzinfo=UTC)

        # Feed bars for day 1
        for i in range(10):
            await data_service.feed_bar(
                "AAPL",
                day1_ts + timedelta(minutes=i),
                100,
                101,
                99,
                100,
                10000,
            )

        vwap_before = await data_service.get_indicator("AAPL", "vwap")
        assert vwap_before is not None

        # Reset for new day
        data_service.reset_daily_state()

        # VWAP should be None after reset
        vwap_after_reset = await data_service.get_indicator("AAPL", "vwap")
        assert vwap_after_reset is None

        # Feed first bar of day 2
        await data_service.feed_bar("AAPL", day2_ts, 200, 201, 199, 200, 10000)

        # VWAP should reflect only day 2's bar
        vwap_day2 = await data_service.get_indicator("AAPL", "vwap")
        assert vwap_day2 is not None
        # For single bar, VWAP = typical price = (H + L + C) / 3 = (201 + 199 + 200) / 3 = 200
        assert abs(vwap_day2 - 200.0) < 0.1

    @pytest.mark.asyncio
    async def test_reset_daily_state_preserves_sma(self, data_service: BacktestDataService) -> None:
        """reset_daily_state preserves SMA state (rolling window)."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)

        # Feed 9 bars
        for i in range(9):
            await data_service.feed_bar(
                "AAPL",
                ts + timedelta(minutes=i),
                100,
                101,
                99,
                100,
                10000,
            )

        sma_before = await data_service.get_indicator("AAPL", "sma_9")
        assert sma_before is not None

        # Reset for new day
        data_service.reset_daily_state()

        # SMA should still be available (rolling window carries over)
        sma_after = await data_service.get_indicator("AAPL", "sma_9")
        assert sma_after == sma_before

    @pytest.mark.asyncio
    async def test_get_historical_candles_raises_not_implemented(
        self, data_service: BacktestDataService
    ) -> None:
        """get_historical_candles raises NotImplementedError."""
        ts = datetime(2025, 6, 15, 9, 30, 0, tzinfo=UTC)

        with pytest.raises(NotImplementedError) as exc_info:
            await data_service.get_historical_candles("AAPL", "1m", ts, ts + timedelta(hours=1))

        assert "Parquet files" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_and_stop_are_noop(self, data_service: BacktestDataService) -> None:
        """start and stop methods are no-ops and don't raise."""
        await data_service.start(["AAPL", "TSLA"], ["1m"])
        await data_service.stop()
        # No assertions needed - just verify no exceptions

    @pytest.mark.asyncio
    async def test_get_indicator_unknown_symbol_returns_none(
        self, data_service: BacktestDataService
    ) -> None:
        """get_indicator returns None for unknown symbols."""
        result = await data_service.get_indicator("UNKNOWN", "vwap")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_current_price_unknown_symbol_returns_none(
        self, data_service: BacktestDataService
    ) -> None:
        """get_current_price returns None for unknown symbols."""
        result = await data_service.get_current_price("UNKNOWN")
        assert result is None
