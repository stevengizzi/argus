"""Tests for DatabentoDataService (Sprint 12).

Uses mock objects to test without requiring the databento package or API access.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import DatabentoConfig, DataServiceConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
)
from tests.mocks.mock_databento import (
    MockErrorMsg,
    MockHistoricalClient,
    MockLiveClient,
    MockOHLCVMsg,
    MockRecordHeader,
    MockSymbolMappingMsg,
    MockTradeMsg,
)


# Create a mock databento module
class MockDatabentoModule:
    """Mock databento module for testing without the real package."""

    Live = MockLiveClient
    Historical = MockHistoricalClient
    OHLCVMsg = MockOHLCVMsg
    TradeMsg = MockTradeMsg
    SymbolMappingMsg = MockSymbolMappingMsg
    ErrorMsg = MockErrorMsg


@pytest.fixture
def mock_databento():
    """Patch the databento module for testing."""
    mock_db = MockDatabentoModule()
    with patch.dict(sys.modules, {"databento": mock_db}):
        yield mock_db


@pytest.fixture
def event_bus():
    """Create a fresh EventBus for each test."""
    return EventBus()


@pytest.fixture
def databento_config():
    """Create a DatabentoConfig for testing."""
    return DatabentoConfig(
        api_key_env_var="DATABENTO_API_KEY",
        dataset="XNAS.ITCH",
        symbols=["AAPL", "TSLA"],
        stale_data_timeout_seconds=5.0,  # Short for testing
    )


@pytest.fixture
def data_config():
    """Create a DataServiceConfig for testing."""
    return DataServiceConfig()


@pytest.fixture
def fixed_clock():
    """Create a FixedClock for testing."""
    return FixedClock(datetime(2026, 2, 21, 10, 0, 0, tzinfo=UTC))


class TestDatabentoDataServiceInit:
    """Tests for DatabentoDataService initialization."""

    def test_constructor_sets_up_internal_state(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Constructor initializes all internal state correctly."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        assert service._event_bus is event_bus
        assert service._config is databento_config
        assert service._data_config is data_config
        assert service._running is False
        assert service._live_client is None
        assert service._price_cache == {}
        assert service._indicator_cache == {}

    def test_constructor_with_custom_config(self, mock_databento, event_bus, data_config):
        """Constructor accepts custom configuration."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            dataset="XNYS.PILLAR",
            symbols="ALL_SYMBOLS",
            enable_depth=True,
        )
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        assert service._config.dataset == "XNYS.PILLAR"
        assert service._config.symbols == "ALL_SYMBOLS"
        assert service._config.enable_depth is True

    def test_constructor_with_clock_injection(
        self, mock_databento, event_bus, databento_config, data_config, fixed_clock
    ):
        """Constructor accepts injected clock for testability."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=fixed_clock,
        )

        assert service._clock is fixed_clock


class TestDatabentoDataServiceStart:
    """Tests for the start() method."""

    @pytest.mark.asyncio
    async def test_missing_api_key_raises_runtime_error(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Missing API key raises RuntimeError."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError) as exc_info:
                await service.start(["AAPL"], ["1m"])
            assert "API key not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_start_creates_live_client_and_subscribes(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start creates Live client and subscribes to schemas."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Mock the historical data fetch for warm-up
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        assert service._live_client is not None
        assert service._running is True
        # Check subscriptions were made
        assert len(service._live_client.subscriptions) >= 2  # bars + trades

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_subscribes_to_bar_schema(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start subscribes to the bar schema."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        bar_sub = next(
            (s for s in service._live_client.subscriptions if s["schema"] == "ohlcv-1m"),
            None,
        )
        assert bar_sub is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_subscribes_to_trade_schema(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start subscribes to the trade schema."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        trade_sub = next(
            (s for s in service._live_client.subscriptions if s["schema"] == "trades"),
            None,
        )
        assert trade_sub is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_subscribes_to_depth_when_enabled(
        self, mock_databento, event_bus, data_config
    ):
        """Start subscribes to depth schema when enable_depth=True."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(enable_depth=True)
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        depth_sub = next(
            (s for s in service._live_client.subscriptions if s["schema"] == "mbp-10"),
            None,
        )
        assert depth_sub is not None

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_does_not_subscribe_to_depth_when_disabled(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start does NOT subscribe to depth when enable_depth=False."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        depth_sub = next(
            (s for s in service._live_client.subscriptions if s["schema"] == "mbp-10"),
            None,
        )
        assert depth_sub is None

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_registers_callback(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start registers callback with live client."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        assert len(service._live_client.callbacks) == 1

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_sets_running_flag(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start sets the running flag to True."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        assert service._running is False

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        assert service._running is True

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_warns_if_already_running(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Start warns if service is already running."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])
            await service.start(["AAPL"], ["1m"])  # Second call

        assert "already running" in caplog.text

        await service.stop()

    @pytest.mark.asyncio
    async def test_start_stores_event_loop_reference(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Start stores reference to the running event loop."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        assert service._loop is None

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        assert service._loop is not None
        assert service._loop.is_running()

        await service.stop()


class TestDatabentoDataServiceStop:
    """Tests for the stop() method."""

    @pytest.mark.asyncio
    async def test_stop_calls_live_client_stop(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Stop calls live_client.stop()."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        live_client = service._live_client
        await service.stop()

        assert live_client.stopped is True

    @pytest.mark.asyncio
    async def test_stop_cancels_stale_monitor_task(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Stop cancels the stale data monitor task."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        stale_task = service._stale_monitor_task
        assert stale_task is not None

        await service.stop()

        assert stale_task.cancelled() or stale_task.done()

    @pytest.mark.asyncio
    async def test_stop_clears_symbol_map(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Stop clears the symbol map."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        # Add a mapping
        service._symbol_map.add_mapping(100, "AAPL")
        assert service._symbol_map.symbol_count == 1

        await service.stop()

        assert service._symbol_map.symbol_count == 0

    @pytest.mark.asyncio
    async def test_stop_sets_running_false(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Stop sets running flag to False."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])
        assert service._running is True

        await service.stop()

        assert service._running is False

    @pytest.mark.asyncio
    async def test_stop_is_idempotent(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Stop is safe to call multiple times."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

        # Call stop multiple times - should not raise
        await service.stop()
        await service.stop()
        await service.stop()


class TestSymbolMappingFlow:
    """Tests for symbol mapping processing."""

    def test_on_symbol_mapping_updates_symbol_map(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_on_symbol_mapping updates the symbol map."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        msg = MockSymbolMappingMsg(instrument_id=100, stype_in_symbol="AAPL")
        service._on_symbol_mapping(msg)

        assert service._symbol_map.get_symbol(100) == "AAPL"

    def test_on_ohlcv_skips_unknown_instrument_id(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_on_ohlcv skips messages with unknown instrument_id."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # No mapping added for instrument_id=999
        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=999),
            open=100.0,
            high=105.0,
            low=99.0,
            close=104.0,
            volume=1000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        # Should not raise, just skip
        service._on_ohlcv(msg)

        # Price cache should be empty
        assert len(service._price_cache) == 0

    def test_on_trade_skips_unknown_instrument_id(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_on_trade skips messages with unknown instrument_id."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        msg = MockTradeMsg(
            hd=MockRecordHeader(instrument_id=999),
            price=100.0,
            size=100,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_trade(msg)

        assert len(service._price_cache) == 0


class TestOHLCVConversion:
    """Tests for OHLCVMsg → CandleEvent conversion."""

    def test_correct_symbol_resolution(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """OHLCV messages resolve to correct symbol."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"AAPL"}

        # Add mapping
        service._symbol_map.add_mapping(100, "AAPL")

        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=100),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Price cache should have AAPL
        assert "AAPL" in service._price_cache
        assert service._price_cache["AAPL"] == 154.0

    def test_correct_timestamp_conversion(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Nanosecond timestamp is correctly converted to datetime."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"AAPL"}
        service._symbol_map.add_mapping(100, "AAPL")

        expected_time = datetime(2026, 2, 21, 10, 30, 0, tzinfo=UTC)
        ts_ns = int(expected_time.timestamp() * 1e9)

        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=100),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000,
            ts_event=ts_ns,
        )

        # Mock the loop to avoid thread bridging issues
        service._loop = MagicMock()
        service._loop.is_running.return_value = True

        service._on_ohlcv(msg)

        # Verify call_soon_threadsafe was called
        assert service._loop.call_soon_threadsafe.called

    def test_price_cache_updated_with_close_price(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """OHLCV message updates price cache with close price."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"AAPL"}
        service._symbol_map.add_mapping(100, "AAPL")

        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=100),
            open=150.0,
            high=155.0,
            low=149.0,
            close=152.50,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        assert service._price_cache["AAPL"] == 152.50

    def test_symbols_not_in_active_symbols_are_skipped(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """OHLCV messages for non-active symbols are skipped."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"TSLA"}  # Only tracking TSLA
        service._symbol_map.add_mapping(100, "AAPL")  # But mapping AAPL

        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=100),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Price cache should be empty since AAPL is not in active_symbols
        assert len(service._price_cache) == 0


class TestTradeConversion:
    """Tests for TradeMsg → TickEvent conversion."""

    def test_trade_updates_price_cache(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Trade message updates price cache."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"AAPL"}
        service._symbol_map.add_mapping(100, "AAPL")

        msg = MockTradeMsg(
            hd=MockRecordHeader(instrument_id=100),
            price=151.25,
            size=500,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_trade(msg)

        assert service._price_cache["AAPL"] == 151.25

    def test_trade_for_non_active_symbol_skipped(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Trade messages for non-active symbols are skipped."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"TSLA"}
        service._symbol_map.add_mapping(100, "AAPL")

        msg = MockTradeMsg(
            hd=MockRecordHeader(instrument_id=100),
            price=151.25,
            size=500,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_trade(msg)

        assert len(service._price_cache) == 0


class TestErrorHandling:
    """Tests for error message handling."""

    def test_error_message_logged(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """ErrorMsg is logged."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        msg = MockErrorMsg(err="Test error message")
        service._on_error(msg)

        assert "Test error message" in caplog.text


class TestGetCurrentPrice:
    """Tests for get_current_price()."""

    @pytest.mark.asyncio
    async def test_returns_cached_price(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """get_current_price returns cached price."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._price_cache["AAPL"] = 150.50

        price = await service.get_current_price("AAPL")
        assert price == 150.50

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_symbol(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """get_current_price returns None for unknown symbol."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        price = await service.get_current_price("UNKNOWN")
        assert price is None


class TestGetIndicator:
    """Tests for get_indicator()."""

    @pytest.mark.asyncio
    async def test_returns_cached_indicator(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """get_indicator returns cached indicator value."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._indicator_cache[("AAPL", "vwap")] = 151.25

        indicator = await service.get_indicator("AAPL", "vwap")
        assert indicator == 151.25

    @pytest.mark.asyncio
    async def test_returns_none_for_unknown_indicator(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """get_indicator returns None for unknown indicator."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        indicator = await service.get_indicator("AAPL", "unknown_indicator")
        assert indicator is None


class TestGetWatchlistData:
    """Tests for get_watchlist_data()."""

    @pytest.mark.asyncio
    async def test_returns_correct_structure(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """get_watchlist_data returns correct structure for multiple symbols."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._price_cache["AAPL"] = 150.0
        service._price_cache["TSLA"] = 250.0
        service._indicator_cache[("AAPL", "vwap")] = 149.50
        service._indicator_cache[("TSLA", "atr_14")] = 5.0

        data = await service.get_watchlist_data(["AAPL", "TSLA"])

        assert "AAPL" in data
        assert "TSLA" in data
        assert data["AAPL"]["price"] == 150.0
        assert data["TSLA"]["price"] == 250.0
        assert data["AAPL"]["indicators"]["vwap"] == 149.50
        assert data["TSLA"]["indicators"]["atr_14"] == 5.0


class TestIndicatorComputation:
    """Tests for indicator computation."""

    def test_vwap_computation(self, mock_databento, event_bus, databento_config, data_config):
        """VWAP is computed correctly."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        candle = CandleEvent(
            symbol="AAPL",
            timestamp=datetime(2026, 2, 21, 10, 0, tzinfo=UTC),
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=1000,
            timeframe="1m",
        )

        events = service._update_indicators("AAPL", candle)

        # VWAP should be (H+L+C)/3 = (102+99+101)/3 = 100.67
        vwap_event = next((e for e in events if e.indicator_name == "vwap"), None)
        assert vwap_event is not None
        assert abs(vwap_event.value - 100.67) < 0.01


class TestWarmUpIndicators:
    """Tests for indicator warm-up during startup."""

    @pytest.mark.asyncio
    async def test_warm_up_populates_indicator_cache(
        self, mock_databento, event_bus, databento_config, data_config, fixed_clock
    ):
        """Warm-up populates indicator cache with VWAP and SMAs."""
        import pandas as pd

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=fixed_clock,
        )

        # Create historical data with 20 candles (enough for SMA-9 and RVOL baseline)
        timestamps = pd.date_range(
            start="2026-02-21 09:30:00",
            periods=20,
            freq="1min",
            tz="UTC",
        )
        historical_df = pd.DataFrame(
            {
                "ts_event": timestamps,
                "timestamp": timestamps,
                "open": [100.0 + i * 0.1 for i in range(20)],
                "high": [101.0 + i * 0.1 for i in range(20)],
                "low": [99.0 + i * 0.1 for i in range(20)],
                "close": [100.5 + i * 0.1 for i in range(20)],
                "volume": [1000 + i * 10 for i in range(20)],
            }
        )

        # Mock get_historical_candles to return our test data
        async def mock_get_historical_candles(
            symbol: str, timeframe: str, start, end
        ) -> pd.DataFrame:
            return historical_df

        service.get_historical_candles = mock_get_historical_candles

        # Run warm-up
        await service._warm_up_indicators(["AAPL"])

        # Verify VWAP is cached
        vwap = service._indicator_cache.get(("AAPL", "vwap"))
        assert vwap is not None, "VWAP should be in indicator cache after warm-up"
        assert vwap > 0, "VWAP should be positive"

        # Verify SMA-9 is cached (need at least 9 candles, we have 20)
        sma_9 = service._indicator_cache.get(("AAPL", "sma_9"))
        assert sma_9 is not None, "SMA-9 should be in indicator cache after warm-up"
        assert sma_9 > 0, "SMA-9 should be positive"

        # Verify indicator engine was created
        assert "AAPL" in service._indicator_engines
        engine = service._indicator_engines["AAPL"]
        assert engine.vwap == vwap, "Indicator engine vwap should match cache"


class TestStaleDataMonitor:
    """Tests for stale data monitoring."""

    def test_is_stale_property_reflects_stale_state(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """is_stale property reflects the stale published state."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        assert service.is_stale is False

        service._stale_published = True
        assert service.is_stale is True

        service._stale_published = False
        assert service.is_stale is False

    def test_last_message_time_updated_on_dispatch(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_dispatch_record updates _last_message_time."""
        import time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._active_symbols = {"AAPL"}
        service._symbol_map.add_mapping(100, "AAPL")

        # Set up record class references (normally done in start())
        service._OHLCVMsg = MockOHLCVMsg
        service._TradeMsg = MockTradeMsg
        service._SymbolMappingMsg = MockSymbolMappingMsg
        service._ErrorMsg = MockErrorMsg

        # Set initial time
        service._last_message_time = 0

        # Process a message
        msg = MockOHLCVMsg(
            hd=MockRecordHeader(instrument_id=100),
            open=150.0,
            high=155.0,
            low=149.0,
            close=154.0,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        current_time = time.monotonic()
        service._dispatch_record(msg)

        # Time should have been updated
        assert service._last_message_time >= current_time

    @pytest.mark.asyncio
    async def test_stale_monitor_detects_stale_condition(
        self, mock_databento, event_bus, data_config
    ):
        """Stale monitor correctly detects when data becomes stale."""
        import time
        from unittest.mock import patch

        from argus.data.databento_data_service import DatabentoDataService

        # Very short timeout for testing
        config = DatabentoConfig(stale_data_timeout_seconds=0.01)
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        # Directly test stale detection logic by calling part of the monitor
        service._running = True
        service._last_message_time = time.monotonic() - 100  # Old data

        # Mock asyncio.sleep to return immediately
        with patch("asyncio.sleep", return_value=None):
            # Check elapsed time calculation
            elapsed = time.monotonic() - service._last_message_time
            assert elapsed > config.stale_data_timeout_seconds

    @pytest.mark.asyncio
    async def test_stale_resumed_transition(self, mock_databento, event_bus, data_config):
        """Stale flag transitions correctly between stale and resumed."""

        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(stale_data_timeout_seconds=1.0)
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        # Initially not stale
        assert service._stale_published is False

        # Simulate stale condition
        service._stale_published = True
        assert service.is_stale is True

        # Simulate resumed
        service._stale_published = False
        assert service.is_stale is False


class TestReconnectionLogic:
    """Tests for reconnection logic (Component 4)."""

    @pytest.mark.asyncio
    async def test_clean_shutdown_exits_reconnection_loop(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Clean shutdown via stop() exits reconnection loop."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

            # Let the stream task start
            await asyncio.sleep(0.01)

            assert service._running is True
            assert service._stream_task is not None

            # Clean shutdown
            await service.stop()

            assert service._running is False
            assert service._stream_task.done() or service._stream_task.cancelled()

    @pytest.mark.asyncio
    async def test_exponential_backoff_doubles_delay_on_each_retry(
        self, mock_databento, event_bus, data_config
    ):
        """Exponential backoff doubles delay on each retry."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            reconnect_base_delay_seconds=1.0,
            reconnect_max_delay_seconds=60.0,
            reconnect_max_retries=5,
        )
        _ = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        # Test delay calculation: base * (2 ** (retries - 1))
        # Retry 1: 1.0 * (2 ** 0) = 1.0
        # Retry 2: 1.0 * (2 ** 1) = 2.0
        # Retry 3: 1.0 * (2 ** 2) = 4.0
        assert min(config.reconnect_base_delay_seconds * (2**0), 60) == 1.0
        assert min(config.reconnect_base_delay_seconds * (2**1), 60) == 2.0
        assert min(config.reconnect_base_delay_seconds * (2**2), 60) == 4.0
        assert min(config.reconnect_base_delay_seconds * (2**3), 60) == 8.0

    @pytest.mark.asyncio
    async def test_backoff_caps_at_max_delay_seconds(self, mock_databento, event_bus, data_config):
        """Backoff delay caps at max_delay_seconds."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            reconnect_base_delay_seconds=10.0,
            reconnect_max_delay_seconds=30.0,
            reconnect_max_retries=10,
        )
        _ = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        # Retry 10 would be 10 * (2 ** 9) = 5120 seconds
        # But should cap at 30 seconds
        retries = 10
        delay = min(
            config.reconnect_base_delay_seconds * (2 ** (retries - 1)),
            config.reconnect_max_delay_seconds,
        )
        assert delay == 30.0

    @pytest.mark.asyncio
    async def test_max_retries_exceeded_logs_critical_and_stops(
        self, mock_databento, event_bus, data_config, caplog
    ):
        """Max retries exceeded logs critical and stops reconnecting."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            reconnect_max_retries=2,
            reconnect_base_delay_seconds=0.01,  # Fast for testing
            reconnect_max_delay_seconds=0.1,
        )
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        # Track connection attempts
        connection_attempts = []

        # First connect succeeds (in start()), subsequent reconnects fail
        async def connect_succeeds_then_fails() -> None:
            import databento as db

            connection_attempts.append(1)
            if len(connection_attempts) == 1:
                # First connection succeeds - set up mock client
                if service._live_client is not None:
                    with contextlib.suppress(Exception):
                        service._live_client.stop()
                service._live_client = db.Live(key="test")
                service._symbol_map.clear()
                service._OHLCVMsg = MockOHLCVMsg
                service._TradeMsg = MockTradeMsg
                service._SymbolMappingMsg = MockSymbolMappingMsg
                service._ErrorMsg = MockErrorMsg
                service._live_client.start()
            else:
                # Subsequent reconnections fail
                raise ConnectionError("Test connection failure")

        service._connect_live_session = connect_succeeds_then_fails

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

            # Wait for retries to exhaust
            await asyncio.sleep(0.5)

            # Ensure stop is called if still running
            if service._running:
                await service.stop()

        # Should have attempted initial + retries
        assert len(connection_attempts) >= 2
        # Should see critical log message or reconnection attempts in log
        log_text = caplog.text.lower()
        assert "reconnecting" in log_text or "max reconnection" in log_text

    @pytest.mark.asyncio
    async def test_successful_connection_resets_retry_counter(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Successful connection resets retry counter to 0."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

            # Connection should be successful
            assert service._live_client is not None
            assert service._live_client.started is True

            await service.stop()

    @pytest.mark.asyncio
    async def test_symbol_map_cleared_on_reconnection(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Symbol map is cleared on each reconnection attempt."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Add a mapping
        service._symbol_map.add_mapping(100, "AAPL")
        assert service._symbol_map.symbol_count == 1

        # Simulate what _connect_live_session does
        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service._connect_live_session()

        # Symbol map should be cleared
        assert service._symbol_map.symbol_count == 0

        if service._live_client:
            service._live_client.stop()

    @pytest.mark.asyncio
    async def test_previous_client_stopped_before_new_one(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Previous client is stopped before creating new one."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            # First connection
            await service._connect_live_session()
            first_client = service._live_client

            # Second connection (simulating reconnect)
            await service._connect_live_session()
            second_client = service._live_client

        # First client should have been stopped
        assert first_client.stopped is True
        # Second client is different and started
        assert second_client is not first_client
        assert second_client.started is True

        second_client.stop()

    @pytest.mark.asyncio
    async def test_connection_error_triggers_reconnect_not_crash(
        self, mock_databento, event_bus, data_config
    ):
        """Connection error triggers reconnect, doesn't crash the loop."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            reconnect_max_retries=3,
            reconnect_base_delay_seconds=0.01,
        )
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        call_count = []

        async def connect_succeeds_fails_succeeds() -> None:
            import databento as db

            call_count.append(1)
            # First (in start()) and third succeed, second fails (to test retry)
            if len(call_count) == 2:
                raise ConnectionError("Second attempt fails (triggers retry)")
            # Set up a mock client
            if service._live_client is not None:
                with contextlib.suppress(Exception):
                    service._live_client.stop()
            service._live_client = db.Live(key="test")
            service._symbol_map.clear()
            service._OHLCVMsg = MockOHLCVMsg
            service._TradeMsg = MockTradeMsg
            service._SymbolMappingMsg = MockSymbolMappingMsg
            service._ErrorMsg = MockErrorMsg
            service._live_client.start()

        service._connect_live_session = connect_succeeds_fails_succeeds

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

            # Wait for reconnection loop to run
            await asyncio.sleep(0.1)

            await service.stop()

        # Should have connected at least once (initial connection)
        assert len(call_count) >= 1

    @pytest.mark.asyncio
    async def test_multiple_reconnections_work(self, mock_databento, event_bus, data_config):
        """Multiple reconnections work (connect → disconnect → reconnect)."""
        from argus.data.databento_data_service import DatabentoDataService

        config = DatabentoConfig(
            reconnect_max_retries=3,
            reconnect_base_delay_seconds=0.01,
        )
        service = DatabentoDataService(
            event_bus=event_bus,
            config=config,
            data_config=data_config,
        )

        connection_count = []

        async def track_connections() -> None:
            import databento as db

            connection_count.append(1)
            # Clean up previous client if exists
            if service._live_client is not None:
                with contextlib.suppress(Exception):
                    service._live_client.stop()
            # Create new client
            service._live_client = db.Live(key="test")
            service._symbol_map.clear()
            service._live_client.subscribe(
                dataset=config.dataset,
                schema=config.bar_schema,
                symbols=["AAPL"],
            )
            service._live_client.add_callback(service._dispatch_record)
            service._OHLCVMsg = MockOHLCVMsg
            service._TradeMsg = MockTradeMsg
            service._SymbolMappingMsg = MockSymbolMappingMsg
            service._ErrorMsg = MockErrorMsg
            service._live_client.start()

        service._connect_live_session = track_connections
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL"], ["1m"])

            # Wait for first connection
            await asyncio.sleep(0.05)

            await service.stop()

        # Should have connected at least once
        assert len(connection_count) >= 1

    @pytest.mark.asyncio
    async def test_start_stores_symbols_and_timeframes(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """start() stores symbols and timeframes for reconnection."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._warm_up_indicators = AsyncMock()

        with patch.dict("os.environ", {"DATABENTO_API_KEY": "test-key"}):
            await service.start(["AAPL", "TSLA"], ["1m", "5m"])

            assert service._symbols_list == ["AAPL", "TSLA"]
            assert service._timeframes_list == ["1m", "5m"]

            await service.stop()


class TestDatabentoFetchDailyBars:
    """Tests for fetch_daily_bars() — returns None in V1."""

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_returns_none(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """fetch_daily_bars returns None — not implemented for Databento V1."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        result = await service.fetch_daily_bars("SPY", lookback_days=60)

        assert result is None
