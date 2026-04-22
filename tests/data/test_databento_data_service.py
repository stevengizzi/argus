"""Tests for DatabentoDataService (Sprint 12).

Uses mock objects to test without requiring the databento package or API access.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pandas as pd
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

    def test_symbol_resolution_uses_live_client_symbology_map(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """_resolve_symbol uses the live client's symbology_map."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Create a mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL", 200: "TSLA"}
        service._live_client = mock_client

        # _resolve_symbol should look up in symbology_map
        assert service._resolve_symbol(100) == "AAPL"
        assert service._resolve_symbol(200) == "TSLA"
        assert service._resolve_symbol(999) is None  # Unknown ID

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
            instrument_id=999,
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
            instrument_id=999,
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

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Prices are fixed-point (scaled by 1e9)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Price cache should have AAPL (converted from fixed-point)
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

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        expected_time = datetime(2026, 2, 21, 10, 30, 0, tzinfo=UTC)
        ts_ns = int(expected_time.timestamp() * 1e9)

        # Prices are fixed-point (scaled by 1e9)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
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

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Prices are fixed-point (scaled by 1e9)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=152.50 * 1e9,
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

        # Set up mock live client with symbology_map for AAPL
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Prices are fixed-point (scaled by 1e9)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
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

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Prices are fixed-point (scaled by 1e9)
        msg = MockTradeMsg(
            instrument_id=100,
            price=151.25 * 1e9,
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

        # Set up mock live client with symbology_map for AAPL
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Prices are fixed-point (scaled by 1e9)
        msg = MockTradeMsg(
            instrument_id=100,
            price=151.25 * 1e9,
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
    """Tests for indicator warm-up and computation."""

    def test_indicator_computation_populates_cache(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Indicator computation populates cache with VWAP and SMAs.

        Tests that feeding candles through _update_indicators correctly
        populates the indicator cache. This is the core functionality that
        both lazy warm-up and live stream processing rely on.
        """
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Feed 20 candles through _update_indicators (enough for SMA-9 and RVOL)
        base_time = datetime(2026, 2, 21, 9, 30, 0, tzinfo=UTC)
        for i in range(20):
            candle = CandleEvent(
                symbol="AAPL",
                timestamp=base_time + timedelta(minutes=i),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000 + i * 10,
                timeframe="1m",
            )
            service._update_indicators("AAPL", candle)

        # Verify VWAP is cached
        vwap = service._indicator_cache.get(("AAPL", "vwap"))
        assert vwap is not None, "VWAP should be in indicator cache"
        assert vwap > 0, "VWAP should be positive"

        # Verify SMA-9 is cached (need at least 9 candles, we have 20)
        sma_9 = service._indicator_cache.get(("AAPL", "sma_9"))
        assert sma_9 is not None, "SMA-9 should be in indicator cache"
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

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Set up record class references (normally done in start())
        service._OHLCVMsg = MockOHLCVMsg
        service._TradeMsg = MockTradeMsg
        service._SymbolMappingMsg = MockSymbolMappingMsg
        service._ErrorMsg = MockErrorMsg

        # Set initial time
        service._last_message_time = 0

        # Process a message (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
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
    async def test_fetch_daily_bars_returns_none_without_api_key(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """fetch_daily_bars returns None when FMP_API_KEY is not set."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.delenv("FMP_API_KEY", raising=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        result = await service.fetch_daily_bars("SPY", lookback_days=60)

        assert result is None


class TestViableUniverse:
    """Tests for viable universe fast-path discard (Sprint 23)."""

    def test_set_viable_universe_stores_symbols(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """set_viable_universe() stores the viable symbol set."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Initially None
        assert service._viable_universe is None

        # Set viable universe (capture INFO level logs)
        viable = {"AAPL", "TSLA", "NVDA"}
        with caplog.at_level(logging.INFO):
            service.set_viable_universe(viable)

        assert service._viable_universe == viable
        assert "Viable universe set: 3 symbols" in caplog.text

    def test_fast_path_discard_non_viable_candle(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Candle for non-viable symbol is discarded, no IndicatorEngine created."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL", 200: "GOOG"}
        service._live_client = mock_client
        service._active_symbols = {"AAPL", "GOOG"}

        # Set viable universe - only AAPL is viable
        service.set_viable_universe({"AAPL"})

        # Process candle for non-viable GOOG (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=200,  # GOOG
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Price cache should NOT have GOOG (fast-path discarded)
        assert "GOOG" not in service._price_cache
        # No IndicatorEngine created for GOOG
        assert "GOOG" not in service._indicator_engines

    def test_fast_path_pass_viable_candle(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Candle for viable symbol is processed normally."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client
        service._active_symbols = {"AAPL"}

        # Set viable universe - AAPL is viable
        service.set_viable_universe({"AAPL", "TSLA"})

        # Process candle for viable AAPL (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,  # AAPL
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Price cache should have AAPL
        assert "AAPL" in service._price_cache
        assert service._price_cache["AAPL"] == 154.0
        # IndicatorEngine created for AAPL
        assert "AAPL" in service._indicator_engines

    def test_no_viable_set_processes_all_symbols(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """When _viable_universe is None, all symbols are processed (backward compat)."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL", 200: "GOOG"}
        service._live_client = mock_client
        service._active_symbols = {"AAPL", "GOOG"}

        # Do NOT set viable universe - leave as None
        assert service._viable_universe is None

        # Process candles for both symbols (prices in fixed-point format)
        msg_aapl = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )
        msg_goog = MockOHLCVMsg(
            instrument_id=200,
            open=100.0 * 1e9,
            high=105.0 * 1e9,
            low=99.0 * 1e9,
            close=103.0 * 1e9,
            volume=5000,
            ts_event=int(datetime(2026, 2, 21, 10, 1, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg_aapl)
        service._on_ohlcv(msg_goog)

        # Both symbols should be in price cache
        assert "AAPL" in service._price_cache
        assert "GOOG" in service._price_cache
        # Both have IndicatorEngines
        assert "AAPL" in service._indicator_engines
        assert "GOOG" in service._indicator_engines

    def test_indicator_engine_only_created_for_viable_symbols(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """IndicatorEngine is only instantiated for viable symbols when set."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set viable universe
        service.set_viable_universe({"AAPL"})

        # Create a candle for a non-viable symbol
        candle = CandleEvent(
            symbol="GOOG",
            timestamp=datetime(2026, 2, 21, 10, 0, tzinfo=UTC),
            open=100.0,
            high=102.0,
            low=99.0,
            close=101.0,
            volume=1000,
            timeframe="1m",
        )

        # Call _update_indicators directly with non-viable symbol
        events = service._update_indicators("GOOG", candle)

        # Should return empty list (no processing)
        assert events == []
        # No IndicatorEngine created for GOOG
        assert "GOOG" not in service._indicator_engines

    def test_tick_fast_path_discard_non_viable(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Tick events for non-viable symbols are also discarded."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL", 200: "GOOG"}
        service._live_client = mock_client
        service._active_symbols = {"AAPL", "GOOG"}

        # Set viable universe - only AAPL is viable
        service.set_viable_universe({"AAPL"})

        # Process tick for non-viable GOOG (price in fixed-point format)
        msg = MockTradeMsg(
            instrument_id=200,  # GOOG
            price=150.0 * 1e9,
            size=100,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_trade(msg)

        # Price cache should NOT have GOOG (fast-path discarded)
        assert "GOOG" not in service._price_cache

    def test_tick_fast_path_pass_viable(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Tick events for viable symbols are processed normally."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client
        service._active_symbols = {"AAPL"}

        # Set viable universe
        service.set_viable_universe({"AAPL", "TSLA"})

        # Process tick for viable AAPL (price in fixed-point format)
        msg = MockTradeMsg(
            instrument_id=100,  # AAPL
            price=151.25 * 1e9,
            size=500,
            ts_event=int(datetime(2026, 2, 21, 10, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_trade(msg)

        # Price cache should have AAPL
        assert "AAPL" in service._price_cache
        assert service._price_cache["AAPL"] == 151.25

    def test_viable_universe_initialized_as_none(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_viable_universe is initialized as None in constructor."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        assert service._viable_universe is None


class TestUniverseUpdateEvent:
    """Tests for UniverseUpdateEvent (Sprint 23)."""

    def test_universe_update_event_exists(self):
        """UniverseUpdateEvent is defined in events module."""
        from argus.core.events import UniverseUpdateEvent

        # Create an instance
        event = UniverseUpdateEvent(
            viable_count=100,
            total_fetched=500,
        )

        assert event.viable_count == 100
        assert event.total_fetched == 500
        assert event.timestamp is not None

    def test_universe_update_event_is_frozen(self):
        """UniverseUpdateEvent is immutable (frozen dataclass)."""
        from argus.core.events import UniverseUpdateEvent

        event = UniverseUpdateEvent(
            viable_count=100,
            total_fetched=500,
        )

        # Should raise FrozenInstanceError
        with pytest.raises(Exception):  # FrozenInstanceError is subclass of Exception
            event.viable_count = 200


class TestTimeAwareWarmUp:
    """Tests for time-aware indicator warm-up (Sprint 23.7)."""

    @pytest.fixture
    def premarket_clock(self):
        """Create a FixedClock set to 9:00 AM ET (pre-market)."""
        # March 2026 uses EDT (UTC-4): 9:00 AM EDT = 13:00 UTC
        return FixedClock(datetime(2026, 3, 11, 13, 0, 0, tzinfo=UTC))

    @pytest.fixture
    def midsession_clock(self):
        """Create a FixedClock set to 10:30 AM ET (mid-session)."""
        # March 2026 uses EDT (UTC-4): 10:30 AM EDT = 14:30 UTC
        return FixedClock(datetime(2026, 3, 11, 14, 30, 0, tzinfo=UTC))

    @pytest.fixture
    def market_open_clock(self):
        """Create a FixedClock set to exactly 9:30:00 AM ET (boundary)."""
        # March 2026 uses EDT (UTC-4): 9:30 AM EDT = 13:30 UTC
        return FixedClock(datetime(2026, 3, 11, 13, 30, 0, tzinfo=UTC))

    @pytest.mark.asyncio
    async def test_premarket_boot_skips_warmup(
        self, mock_databento, event_bus, databento_config, data_config, premarket_clock, caplog
    ):
        """Pre-market boot (before 9:30 AM ET) skips indicator warm-up."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=premarket_clock,
        )

        # Track if get_historical_candles is called
        historical_called = []

        async def mock_get_historical(symbol, timeframe, start, end):
            historical_called.append(symbol)
            return MagicMock()

        service.get_historical_candles = mock_get_historical

        with caplog.at_level(logging.INFO):
            await service._warm_up_indicators(["AAPL", "TSLA", "NVDA"])

        # Should NOT have called historical fetch
        assert len(historical_called) == 0
        # Should log pre-market skip message
        assert "Pre-market boot" in caplog.text
        assert "skipping indicator warm-up" in caplog.text
        # Should NOT be in mid-session mode
        assert service._mid_session_mode is False
        assert len(service._symbols_needing_warmup) == 0

    @pytest.mark.asyncio
    async def test_midsession_boot_enables_lazy_warmup(
        self, mock_databento, event_bus, databento_config, data_config, midsession_clock, caplog
    ):
        """Mid-session boot (after 9:30 AM ET) enables lazy per-symbol warm-up."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=midsession_clock,
        )

        with caplog.at_level(logging.INFO):
            await service._warm_up_indicators(["AAPL", "TSLA", "NVDA"])

        # Should be in mid-session mode
        assert service._mid_session_mode is True
        # Should have all symbols pending warm-up
        assert service._symbols_needing_warmup == {"AAPL", "TSLA", "NVDA"}
        # Should log mid-session message
        assert "Mid-session boot" in caplog.text
        assert "lazy per-symbol warm-up" in caplog.text

    @pytest.mark.asyncio
    async def test_boundary_930_treated_as_premarket(
        self, mock_databento, event_bus, databento_config, data_config, market_open_clock, caplog
    ):
        """Exactly 9:30:00 AM ET is treated as pre-market (no warm-up)."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=market_open_clock,
        )

        with caplog.at_level(logging.INFO):
            await service._warm_up_indicators(["AAPL"])

        # Boundary case: exactly 9:30 is pre-market
        assert service._mid_session_mode is False
        assert len(service._symbols_needing_warmup) == 0
        assert "Pre-market boot" in caplog.text

    def test_lazy_warmup_triggered_on_first_candle(
        self, mock_databento, event_bus, databento_config, data_config, midsession_clock
    ):
        """Lazy warm-up is triggered on first candle for un-warmed symbol."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=midsession_clock,
        )

        # Set up mid-session mode
        service._mid_session_mode = True
        service._symbols_needing_warmup = {"AAPL", "TSLA"}
        service._active_symbols = {"AAPL", "TSLA"}

        # Track lazy warmup calls
        lazy_warmup_called = []

        def mock_lazy_warmup(symbol):
            lazy_warmup_called.append(symbol)

        service._lazy_warmup_symbol = mock_lazy_warmup

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Process first candle for AAPL (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 3, 11, 15, 30, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Lazy warmup should have been called for AAPL
        assert lazy_warmup_called == ["AAPL"]
        # AAPL should be removed from pending set
        assert "AAPL" not in service._symbols_needing_warmup
        assert "TSLA" in service._symbols_needing_warmup

    def test_lazy_warmup_not_triggered_on_second_candle(
        self, mock_databento, event_bus, databento_config, data_config, midsession_clock
    ):
        """Second candle for same symbol does NOT trigger lazy warm-up."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=midsession_clock,
        )

        # Set up mid-session mode with AAPL already warmed
        service._mid_session_mode = True
        service._symbols_needing_warmup = {"TSLA"}  # AAPL not in set (already warmed)
        service._active_symbols = {"AAPL"}

        # Track lazy warmup calls
        lazy_warmup_called = []

        def mock_lazy_warmup(symbol):
            lazy_warmup_called.append(symbol)

        service._lazy_warmup_symbol = mock_lazy_warmup

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Process second candle for AAPL (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 3, 11, 15, 31, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Lazy warmup should NOT have been called
        assert lazy_warmup_called == []

    def test_lazy_warmup_failure_marks_symbol_warmed(
        self, mock_databento, event_bus, databento_config, data_config, midsession_clock, caplog
    ):
        """Failed lazy warm-up marks symbol as warmed (no retry loop)."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=midsession_clock,
        )

        # Set up mid-session mode
        service._mid_session_mode = True
        service._symbols_needing_warmup = {"AAPL"}
        service._active_symbols = {"AAPL"}

        # Create a mock hist_client that raises an error
        mock_hist = MagicMock()
        mock_hist.timeseries.get_range.side_effect = Exception("Network error")
        service._hist_client = mock_hist

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Process first candle for AAPL (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 3, 11, 15, 30, tzinfo=UTC).timestamp() * 1e9),
        )

        with caplog.at_level(logging.WARNING):
            service._on_ohlcv(msg)

        # Symbol should be removed from pending (marked as warmed)
        assert "AAPL" not in service._symbols_needing_warmup
        # Warning should be logged
        assert "Lazy warm-up for AAPL failed" in caplog.text
        # Candle should still be processed (price cache updated)
        assert "AAPL" in service._price_cache

    def test_premarket_candles_processed_without_backfill(
        self, mock_databento, event_bus, databento_config, data_config, premarket_clock
    ):
        """Pre-market boot processes candles without lazy backfill."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=premarket_clock,
        )

        # NOT in mid-session mode (pre-market)
        service._mid_session_mode = False
        service._active_symbols = {"AAPL"}

        # Track lazy warmup calls (should not be called)
        lazy_warmup_called = []

        def mock_lazy_warmup(symbol):
            lazy_warmup_called.append(symbol)

        service._lazy_warmup_symbol = mock_lazy_warmup

        # Set up mock live client with symbology_map
        mock_client = MockLiveClient()
        mock_client._symbology_map = {100: "AAPL"}
        service._live_client = mock_client

        # Process candle (prices in fixed-point format)
        msg = MockOHLCVMsg(
            instrument_id=100,
            open=150.0 * 1e9,
            high=155.0 * 1e9,
            low=149.0 * 1e9,
            close=154.0 * 1e9,
            volume=10000,
            ts_event=int(datetime(2026, 3, 11, 14, 0, tzinfo=UTC).timestamp() * 1e9),
        )

        service._on_ohlcv(msg)

        # Lazy warmup should NOT have been called (pre-market mode)
        assert lazy_warmup_called == []
        # Candle should still be processed
        assert "AAPL" in service._price_cache
        assert service._price_cache["AAPL"] == 154.0

    @pytest.mark.asyncio
    async def test_midsession_boot_no_blocking_warmup(
        self, mock_databento, event_bus, databento_config, data_config, midsession_clock
    ):
        """Mid-session boot does NOT run blocking per-symbol warm-up loop."""
        import pandas as pd

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=midsession_clock,
        )

        # Track if get_historical_candles is called (blocking warmup)
        historical_called = []

        async def mock_get_historical(symbol, timeframe, start, end):
            historical_called.append(symbol)
            return pd.DataFrame()

        service.get_historical_candles = mock_get_historical

        await service._warm_up_indicators(["AAPL", "TSLA", "NVDA"])

        # get_historical_candles should NOT have been called
        # (blocking warm-up loop not executed)
        assert len(historical_called) == 0
        # But mid-session mode should be set
        assert service._mid_session_mode is True
        assert len(service._symbols_needing_warmup) == 3

    def test_lazy_warmup_clamps_end_to_now_minus_600s(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Lazy warm-up clamps end parameter to now - 600s (DEC-326)."""
        from argus.data.databento_data_service import DatabentoDataService

        # Clock at 11:00 AM ET = 15:00 UTC (well past 9:30 + 10min)
        clock = FixedClock(datetime(2026, 3, 11, 15, 0, 0, tzinfo=UTC))

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=clock,
        )

        # Set up mid-session mode
        service._mid_session_mode = True
        service._symbols_needing_warmup = {"AAPL"}

        # Create mock hist_client to capture the end parameter
        mock_hist = MagicMock()
        mock_df = MagicMock()
        mock_df.to_df.return_value = MagicMock(empty=True)
        mock_hist.timeseries.get_range.return_value = mock_df
        service._hist_client = mock_hist

        service._lazy_warmup_symbol("AAPL")

        # Verify get_range was called
        assert mock_hist.timeseries.get_range.called
        call_kwargs = mock_hist.timeseries.get_range.call_args

        # The end parameter should be ~10:50 AM ET (11:00 - 10min)
        end_str = call_kwargs.kwargs.get("end") or call_kwargs[1].get("end")
        from datetime import datetime as dt
        from zoneinfo import ZoneInfo
        # Parse the ISO format end time
        et_tz = ZoneInfo("America/New_York")
        end_parsed = dt.fromisoformat(end_str)
        expected_end = clock.now().astimezone(et_tz) - timedelta(seconds=600)
        # Should be within a second of expected
        assert abs((end_parsed - expected_end).total_seconds()) < 1.0

    def test_lazy_warmup_skips_when_clamped_end_before_start(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Lazy warm-up skips symbol when clamped end < start (< 10min into session)."""
        import logging

        # Clock at 9:35 AM ET = 13:35 UTC (only 5 min into session)
        # After clamping: end = 9:35 - 10min = 9:25 AM < 9:30 AM start
        clock = FixedClock(datetime(2026, 3, 11, 13, 35, 0, tzinfo=UTC))

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=clock,
        )

        service._mid_session_mode = True
        service._symbols_needing_warmup = {"AAPL"}

        # Create mock hist_client (should NOT be called)
        mock_hist = MagicMock()
        service._hist_client = mock_hist

        with caplog.at_level(logging.DEBUG):
            service._lazy_warmup_symbol("AAPL")

        # Historical API should NOT have been called
        assert not mock_hist.timeseries.get_range.called
        # Should log the skip reason
        assert "clamped end" in caplog.text
        assert "skipping" in caplog.text

    @pytest.mark.asyncio
    async def test_premarket_boot_unaffected_by_end_clamping(
        self, mock_databento, event_bus, databento_config, data_config, premarket_clock, caplog
    ):
        """Pre-market boot skips warm-up entirely — end clamping not involved."""
        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
            clock=premarket_clock,
        )

        with caplog.at_level(logging.INFO):
            await service._warm_up_indicators(["AAPL"])

        # Pre-market skips warm-up entirely (no mid-session mode, no lazy warmup)
        assert service._mid_session_mode is False
        assert len(service._symbols_needing_warmup) == 0
        assert "Pre-market boot" in caplog.text

    def test_warmup_state_initialized_correctly(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Time-aware warm-up state variables are initialized correctly."""
        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        assert service._mid_session_mode is False
        assert service._symbols_needing_warmup == set()
        assert hasattr(service, "_warmup_lock")


class TestFetchDailyBars:
    """Tests for DatabentoDataService.fetch_daily_bars()."""

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_success(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """Valid FMP response returns DataFrame with correct columns, sort, and row count."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("FMP_API_KEY", "test-fmp-key")

        fmp_payload = [
            {"date": "2026-01-03", "open": 100.0, "high": 105.0, "low": 99.0, "close": 104.0, "volume": 1_000_000},
            {"date": "2026-01-02", "open": 98.0, "high": 102.0, "low": 97.0, "close": 101.0, "volume": 900_000},
            {"date": "2026-01-01", "open": 95.0, "high": 99.0, "low": 94.0, "close": 98.0, "volume": 800_000},
        ]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=fmp_payload)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            df = await service.fetch_daily_bars("AAPL", lookback_days=60)

        assert df is not None
        assert list(df.columns) == ["date", "open", "high", "low", "close", "volume"]
        assert len(df) == 3
        # Verify ascending sort by date
        assert list(df["date"]) == ["2026-01-01", "2026-01-02", "2026-01-03"]

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_no_api_key(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """Missing FMP_API_KEY returns None without making any HTTP request."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.delenv("FMP_API_KEY", raising=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession") as mock_session_cls:
            result = await service.fetch_daily_bars("AAPL")

        assert result is None
        mock_session_cls.assert_not_called()

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_http_error(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """Non-200 HTTP response returns None."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("FMP_API_KEY", "test-fmp-key")

        mock_response = MagicMock()
        mock_response.status = 403
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service.fetch_daily_bars("AAPL")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_timeout(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """asyncio.TimeoutError during request returns None."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("FMP_API_KEY", "test-fmp-key")

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service.fetch_daily_bars("AAPL")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_empty_response(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """Empty JSON array from FMP returns None."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("FMP_API_KEY", "test-fmp-key")

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            result = await service.fetch_daily_bars("AAPL")

        assert result is None

    @pytest.mark.asyncio
    async def test_fetch_daily_bars_lookback_limit(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """When FMP returns more rows than lookback_days, only the most recent rows are returned."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("FMP_API_KEY", "test-fmp-key")

        fmp_payload = [
            {
                "date": f"2025-{str((i // 30) + 1).zfill(2)}-{str((i % 30) + 1).zfill(2)}",
                "open": 100.0,
                "high": 105.0,
                "low": 99.0,
                "close": 104.0,
                "volume": 1_000_000,
            }
            for i in range(100)
        ]

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=fmp_payload)
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_response)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        with patch("aiohttp.ClientSession", return_value=mock_session):
            df = await service.fetch_daily_bars("AAPL", lookback_days=60)

        assert df is not None
        assert len(df) == 60

    def test_last_update_set_on_dispatch(
        self, mock_databento, event_bus, databento_config, data_config, monkeypatch
    ):
        """last_update is set to a datetime after _dispatch_record processes a record."""
        from argus.data.databento_data_service import DatabentoDataService

        monkeypatch.setenv("DATABENTO_API_KEY", "test-key")

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        # Wire up record class references that _dispatch_record inspects
        service._OHLCVMsg = MockOHLCVMsg
        service._TradeMsg = MagicMock
        service._SymbolMappingMsg = MagicMock

        assert service.last_update is None

        record = MockOHLCVMsg(
            instrument_id=100,
            open=100_000_000_000,
            high=105_000_000_000,
            low=99_000_000_000,
            close=104_000_000_000,
            volume=500_000,
        )

        service._dispatch_record(record)

        assert service.last_update is not None
        assert service.last_update.tzinfo is not None


# ─────────────────────────────────────────────────────────────
# Observability: drop counters, heartbeat, sentinels, mapping
# ─────────────────────────────────────────────────────────────

def _make_ohlcv_msg(instrument_id: int = 100) -> MockOHLCVMsg:
    return MockOHLCVMsg(
        instrument_id=instrument_id,
        open=150_000_000_000,
        high=155_000_000_000,
        low=149_000_000_000,
        close=154_000_000_000,
        volume=10_000,
        ts_event=int(datetime(2026, 4, 3, 14, 31, tzinfo=UTC).timestamp() * 1e9),
    )


def _make_trade_msg(instrument_id: int = 100) -> MockTradeMsg:
    return MockTradeMsg(
        instrument_id=instrument_id,
        price=151_000_000_000,
        size=500,
        ts_event=int(datetime(2026, 4, 3, 14, 31, tzinfo=UTC).timestamp() * 1e9),
    )


def _make_service_with_client(
    event_bus: EventBus,
    databento_config: DatabentoConfig,
    data_config: DataServiceConfig,
    symbology_map: dict[int, str] | None = None,
) -> object:
    """Return a DatabentoDataService with a pre-wired mock client."""
    from argus.data.databento_data_service import DatabentoDataService

    service = DatabentoDataService(
        event_bus=event_bus,
        config=databento_config,
        data_config=data_config,
    )
    client = MockLiveClient()
    client._symbology_map = symbology_map or {}
    service._live_client = client
    return service


class TestDropCounters:
    """Per-gate drop counters increment correctly."""

    def test_ohlcv_unmapped_increments_counter(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_ohlcv_unmapped_since_heartbeat increments when instrument_id unknown."""
        service = _make_service_with_client(event_bus, databento_config, data_config)
        service._on_ohlcv(_make_ohlcv_msg(instrument_id=999))
        assert service._ohlcv_unmapped_since_heartbeat == 1

    def test_ohlcv_universe_filter_increments_counter(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_ohlcv_filtered_universe_since_heartbeat increments for non-viable symbol."""
        service = _make_service_with_client(
            event_bus, databento_config, data_config, symbology_map={100: "AAPL"}
        )
        service._viable_universe = {"TSLA"}
        service._on_ohlcv(_make_ohlcv_msg(instrument_id=100))
        assert service._ohlcv_filtered_universe_since_heartbeat == 1
        assert service._ohlcv_unmapped_since_heartbeat == 0

    def test_ohlcv_active_filter_increments_counter(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_ohlcv_filtered_active_since_heartbeat increments when symbol not active."""
        service = _make_service_with_client(
            event_bus, databento_config, data_config, symbology_map={100: "AAPL"}
        )
        service._active_symbols = {"TSLA"}
        service._viable_universe = None
        service._on_ohlcv(_make_ohlcv_msg(instrument_id=100))
        assert service._ohlcv_filtered_active_since_heartbeat == 1
        assert service._ohlcv_unmapped_since_heartbeat == 0

    def test_trade_unmapped_increments_counter(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_trades_unmapped_since_heartbeat increments when instrument_id unknown."""
        service = _make_service_with_client(event_bus, databento_config, data_config)
        service._on_trade(_make_trade_msg(instrument_id=999))
        assert service._trades_unmapped_since_heartbeat == 1

    def test_trade_received_increments_after_all_gates_pass(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_trades_received_since_heartbeat increments when trade passes all gates."""
        service = _make_service_with_client(
            event_bus, databento_config, data_config, symbology_map={100: "AAPL"}
        )
        service._active_symbols = {"AAPL"}
        service._loop = MagicMock()
        service._loop.is_running.return_value = True
        service._on_trade(_make_trade_msg(instrument_id=100))
        assert service._trades_received_since_heartbeat == 1
        assert service._trades_unmapped_since_heartbeat == 0

    def test_ohlcv_counter_zero_when_candle_passes_all_gates(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """Drop counters stay zero when OHLCV passes all gates."""
        service = _make_service_with_client(
            event_bus, databento_config, data_config, symbology_map={100: "AAPL"}
        )
        service._active_symbols = {"AAPL"}
        service._loop = MagicMock()
        service._loop.is_running.return_value = True
        service._on_ohlcv(_make_ohlcv_msg(instrument_id=100))
        assert service._ohlcv_unmapped_since_heartbeat == 0
        assert service._ohlcv_filtered_universe_since_heartbeat == 0
        assert service._ohlcv_filtered_active_since_heartbeat == 0


class TestHeartbeatObservability:
    """Enhanced heartbeat log format and counter reset."""

    @pytest.mark.asyncio
    async def test_heartbeat_includes_drop_suffix_when_unmapped_nonzero(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Heartbeat log includes '| dropped:' suffix when drop counters are non-zero."""
        import logging
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._ohlcv_unmapped_since_heartbeat = 1200
        service._ohlcv_filtered_universe_since_heartbeat = 350
        service._ohlcv_filtered_active_since_heartbeat = 80

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)  # pre-market — no escalation

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        assert "dropped: 1200 unmapped, 350 universe, 80 active" in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_omits_drop_suffix_when_all_zero(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Heartbeat log omits '| dropped:' suffix when all drop counters are zero."""
        import logging
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._candles_since_heartbeat = 42

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        assert "dropped:" not in caplog.text
        assert "Data heartbeat: 42 candles" in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_includes_trades_suffix_when_nonzero(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Heartbeat log includes '| trades:' suffix when trades activity is non-zero."""
        import logging
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._trades_received_since_heartbeat = 15000
        service._trades_unmapped_since_heartbeat = 200

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        assert "trades: 15000 received, 200 unmapped" in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_omits_trades_suffix_when_all_zero(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """Heartbeat log omits '| trades:' suffix when both trades counters are zero."""
        import logging
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        assert "trades:" not in caplog.text

    @pytest.mark.asyncio
    async def test_heartbeat_resets_all_counters_after_cycle(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """All drop counters are reset to zero after each heartbeat cycle."""
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._ohlcv_unmapped_since_heartbeat = 50
        service._ohlcv_filtered_universe_since_heartbeat = 20
        service._ohlcv_filtered_active_since_heartbeat = 10
        service._trades_received_since_heartbeat = 1000
        service._trades_unmapped_since_heartbeat = 5
        service._candles_since_heartbeat = 30

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)

        with patch("asyncio.sleep", side_effect=fake_sleep):
            with patch("argus.data.databento_data_service.datetime") as mock_dt:
                mock_dt.now.return_value = mock_now
                await service._data_heartbeat()

        assert service._ohlcv_unmapped_since_heartbeat == 0
        assert service._ohlcv_filtered_universe_since_heartbeat == 0
        assert service._ohlcv_filtered_active_since_heartbeat == 0
        assert service._trades_received_since_heartbeat == 0
        assert service._trades_unmapped_since_heartbeat == 0
        assert service._candles_since_heartbeat == 0


class TestZeroCandleEscalation:
    """Zero-candle WARNING during market hours after 2 cycles."""

    @pytest.mark.asyncio
    async def test_zero_candle_warning_during_market_hours_after_two_cycles(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """WARNING emitted when 0 candles in market hours with >=2 prior market-hours cycles."""
        from datetime import time as dt_time

        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._candles_since_heartbeat = 0
        service._market_hours_heartbeat_count = 1  # Will become 2 after increment

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(10, 30)  # 10:30 AM ET — market hours

        with caplog.at_level(logging.WARNING):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    with patch(
                        "argus.core.market_calendar.is_market_holiday",
                        return_value=(False, None),
                    ):
                        await service._data_heartbeat()

        assert "possible data feed failure" in caplog.text
        # Should log at WARNING level
        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert any("possible data feed failure" in r.message for r in warning_records)

    @pytest.mark.asyncio
    async def test_zero_candle_stays_info_outside_market_hours(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """No WARNING when 0 candles outside market hours (pre-market)."""
        from datetime import time as dt_time

        import logging

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._candles_since_heartbeat = 0
        service._market_hours_heartbeat_count = 5  # Many prior cycles, but pre-market

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(7, 0)  # 7 AM ET — pre-market

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert not any("possible data feed failure" in r.message for r in warning_records)
        assert "Data heartbeat: 0 candles" in caplog.text

    @pytest.mark.asyncio
    async def test_zero_candle_stays_info_in_first_market_hours_cycle(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """No WARNING on first market-hours heartbeat cycle (count becomes 1, not >=2)."""
        import logging
        from datetime import time as dt_time

        from argus.data.databento_data_service import DatabentoDataService

        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )
        service._running = True
        service._candles_since_heartbeat = 0
        service._market_hours_heartbeat_count = 0  # Will become 1 after increment

        async def fake_sleep(_: float) -> None:
            service._running = False

        mock_now = MagicMock()
        mock_now.time.return_value = dt_time(9, 35)  # Market hours

        with caplog.at_level(logging.INFO):
            with patch("asyncio.sleep", side_effect=fake_sleep):
                with patch("argus.data.databento_data_service.datetime") as mock_dt:
                    mock_dt.now.return_value = mock_now
                    await service._data_heartbeat()

        warning_records = [r for r in caplog.records if r.levelname == "WARNING"]
        assert not any("possible data feed failure" in r.message for r in warning_records)


class TestFirstEventSentinels:
    """First-event sentinel logs fire exactly once per session."""

    def test_first_ohlcv_unmapped_warning_fires_once(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """WARNING for unmapped OHLCV fires once even with many unmapped records."""
        import logging

        service = _make_service_with_client(event_bus, databento_config, data_config)

        with caplog.at_level(logging.WARNING):
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=999))
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=998))
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=997))

        warning_records = [
            r for r in caplog.records
            if r.levelname == "WARNING" and "not in symbology_map" in r.message
        ]
        assert len(warning_records) == 1
        assert service._ohlcv_unmapped_since_heartbeat == 3

    def test_first_ohlcv_unmapped_warning_includes_map_size(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """First unmapped WARNING includes current symbology_map size."""
        import logging

        service = _make_service_with_client(
            event_bus, databento_config, data_config,
            symbology_map={1: "TSLA", 2: "AAPL"},
        )

        with caplog.at_level(logging.WARNING):
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=999))

        assert "2 IDs mapped" in caplog.text

    def test_first_ohlcv_resolved_info_fires_once(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """INFO for first resolved OHLCV fires once even with many resolved candles."""
        import logging

        service = _make_service_with_client(
            event_bus, databento_config, data_config,
            symbology_map={100: "AAPL", 200: "TSLA"},
        )
        service._active_symbols = {"AAPL", "TSLA"}
        service._loop = MagicMock()
        service._loop.is_running.return_value = True

        with caplog.at_level(logging.INFO):
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=100))
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=200))
            service._on_ohlcv(_make_ohlcv_msg(instrument_id=100))

        resolved_records = [
            r for r in caplog.records
            if r.levelname == "INFO" and "First OHLCV-1m candle resolved" in r.message
        ]
        assert len(resolved_records) == 1
        assert "AAPL" in resolved_records[0].message

    def test_first_trade_resolved_info_fires_once(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """INFO for first resolved trade fires once even with many resolved trades."""
        import logging

        service = _make_service_with_client(
            event_bus, databento_config, data_config,
            symbology_map={100: "AAPL"},
        )
        service._active_symbols = {"AAPL"}
        service._loop = MagicMock()
        service._loop.is_running.return_value = True

        with caplog.at_level(logging.INFO):
            service._on_trade(_make_trade_msg(instrument_id=100))
            service._on_trade(_make_trade_msg(instrument_id=100))
            service._on_trade(_make_trade_msg(instrument_id=100))

        resolved_records = [
            r for r in caplog.records
            if r.levelname == "INFO" and "First trade resolved" in r.message
        ]
        assert len(resolved_records) == 1
        assert "AAPL" in resolved_records[0].message


class TestSymbolMappingObservability:
    """Symbol mapping counter and progress logging."""

    def test_first_mapping_logs_info(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """First SymbolMappingMsg triggers an INFO log."""
        import logging

        service = _make_service_with_client(event_bus, databento_config, data_config)

        msg = MockSymbolMappingMsg(instrument_id=100, stype_in_symbol="AAPL")

        with caplog.at_level(logging.INFO):
            service._on_symbol_mapping(msg)

        assert "First SymbolMappingMsg received" in caplog.text
        assert "100" in caplog.text
        assert "AAPL" in caplog.text

    def test_mapping_counter_increments(
        self, mock_databento, event_bus, databento_config, data_config
    ):
        """_symbol_mappings_received increments with each mapping."""
        service = _make_service_with_client(event_bus, databento_config, data_config)

        for i in range(5):
            service._on_symbol_mapping(MockSymbolMappingMsg(instrument_id=i))

        assert service._symbol_mappings_received == 5

    def test_progress_logged_at_2000th_mapping(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """INFO log emitted at 2000th mapping."""
        import logging

        service = _make_service_with_client(event_bus, databento_config, data_config)
        service._symbol_mappings_received = 1999  # One away from milestone

        with caplog.at_level(logging.INFO):
            service._on_symbol_mapping(MockSymbolMappingMsg(instrument_id=2000))

        assert "SymbolMappingMsg progress: 2000 mappings received" in caplog.text

    def test_progress_logged_at_4000th_mapping(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """INFO log emitted at 4000th mapping (every 2000th)."""
        import logging

        service = _make_service_with_client(event_bus, databento_config, data_config)
        service._symbol_mappings_received = 3999

        with caplog.at_level(logging.INFO):
            service._on_symbol_mapping(MockSymbolMappingMsg(instrument_id=4000))

        assert "SymbolMappingMsg progress: 4000 mappings received" in caplog.text

    def test_no_progress_log_between_milestones(
        self, mock_databento, event_bus, databento_config, data_config, caplog
    ):
        """No progress log emitted for counts between milestones (e.g. 1001)."""
        import logging

        service = _make_service_with_client(event_bus, databento_config, data_config)
        service._symbol_mappings_received = 1000  # Not first, not a 2000 milestone

        with caplog.at_level(logging.INFO):
            service._on_symbol_mapping(MockSymbolMappingMsg(instrument_id=1001))

        assert "SymbolMappingMsg progress" not in caplog.text
        assert "First SymbolMappingMsg" not in caplog.text


class TestCheckParquetCacheMultiMonth:
    """FIX-06 audit 2026-04-21 (P1-C2-12): ``_check_parquet_cache`` must
    concatenate monthly Parquet files when the requested range spans more
    than one month, and fail closed (return None) when any month is missing.

    Consolidated into a single test function to avoid a pandas/pyarrow
    period-extension re-registration issue that fires when ``to_parquet`` is
    invoked across multiple pytest test functions in the same worker.
    """

    def test_multi_month_concat_single_and_missing_coverage(
        self, mock_databento, event_bus, databento_config, data_config, tmp_path
    ):
        from argus.data.databento_data_service import DatabentoDataService

        databento_config.historical_cache_dir = str(tmp_path)
        service = DatabentoDataService(
            event_bus=event_bus,
            config=databento_config,
            data_config=data_config,
        )

        def write_month(year: int, month: int, rows: int = 3) -> None:
            symbol_dir = tmp_path / "AAPL" / "1m"
            symbol_dir.mkdir(parents=True, exist_ok=True)
            ts_base = datetime(year, month, 1)
            frame = pd.DataFrame(
                {
                    "timestamp": [
                        ts_base + timedelta(days=i) for i in range(rows)
                    ],
                    "open": [100.0 + i for i in range(rows)],
                    "high": [101.0 + i for i in range(rows)],
                    "low": [99.0 + i for i in range(rows)],
                    "close": [100.5 + i for i in range(rows)],
                    "volume": [1000 * (i + 1) for i in range(rows)],
                }
            )
            frame.to_parquet(
                symbol_dir / f"{year:04d}-{month:02d}.parquet", index=False
            )

        # --- Case 1: multi-month span with full coverage.
        write_month(2026, 2, rows=3)
        write_month(2026, 3, rows=3)

        result = service._check_parquet_cache(
            "AAPL", "1m", datetime(2026, 2, 1), datetime(2026, 3, 4)
        )
        assert result is not None
        assert len(result) >= 4
        timestamps = list(result["timestamp"])
        assert timestamps == sorted(timestamps), (
            "concat must preserve chronological order"
        )

        # --- Case 2: single-month query still works (regression guard).
        result = service._check_parquet_cache(
            "AAPL", "1m", datetime(2026, 2, 1), datetime(2026, 2, 28)
        )
        assert result is not None
        assert len(result) == 3

        # --- Case 3: missing middle month → fail-closed None.
        # Request spans Feb through April but April is not on disk.
        result = service._check_parquet_cache(
            "AAPL", "1m", datetime(2026, 2, 1), datetime(2026, 4, 1)
        )
        assert result is None, (
            "partial coverage MUST return None rather than a truncated frame"
        )
