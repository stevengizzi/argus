"""Tests for AlpacaDataService."""

import asyncio
import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import AlpacaConfig, DataServiceConfig
from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.alpaca_data_service import AlpacaDataService, IndicatorState


@pytest.fixture
def event_bus():
    """Create an event bus for testing."""
    return EventBus()


@pytest.fixture
def alpaca_config():
    """Create Alpaca configuration for testing."""
    return AlpacaConfig(
        api_key_env="TEST_ALPACA_API_KEY",
        secret_key_env="TEST_ALPACA_SECRET_KEY",
        paper=True,
        data_feed="iex",
        ws_reconnect_base_seconds=1.0,
        ws_reconnect_max_seconds=30.0,
        ws_reconnect_max_failures_before_alert=3,
        stale_data_timeout_seconds=30.0,
        subscribe_bars=True,
        subscribe_trades=True,
    )


@pytest.fixture
def data_config():
    """Create data service configuration for testing."""
    return DataServiceConfig(
        vwap_period=None,  # Session VWAP
        atr_period=14,
        sma_periods=[9, 20, 50],
        rvol_lookback_days=20,
    )


@pytest.fixture
def fixed_clock():
    """Create a fixed clock for testing."""
    return FixedClock(datetime(2026, 2, 15, 14, 30, 0, tzinfo=UTC))


@pytest.fixture
def mock_historical_client():
    """Create a mock StockHistoricalDataClient."""
    return MagicMock()


@pytest.fixture
def mock_data_stream():
    """Create a mock StockDataStream."""
    stream = MagicMock()
    stream._run_forever = AsyncMock()
    stream.stop_ws = AsyncMock()
    stream.close = AsyncMock()
    stream.subscribe_bars = MagicMock()
    stream.subscribe_trades = MagicMock()
    return stream


@pytest.fixture
async def data_service(event_bus, alpaca_config, data_config, fixed_clock):
    """Create an AlpacaDataService for testing."""
    service = AlpacaDataService(
        event_bus=event_bus,
        config=alpaca_config,
        data_config=data_config,
        clock=fixed_clock,
    )
    return service


class TestAlpacaDataServiceInit:
    """Test AlpacaDataService initialization."""

    def test_initialization_with_defaults(self, event_bus, alpaca_config, data_config):
        """Test service initializes with default clock."""
        service = AlpacaDataService(
            event_bus=event_bus,
            config=alpaca_config,
            data_config=data_config,
        )

        assert service._event_bus is event_bus
        assert service._alpaca_config is alpaca_config
        assert service._data_config is data_config
        assert service._clock is not None  # SystemClock by default
        assert service._data_stream is None
        assert service._historical_client is None
        assert service._price_cache == {}
        assert service._indicator_state == {}
        assert service._is_stale is False
        assert service._running is False

    def test_initialization_with_custom_clock(
        self, event_bus, alpaca_config, data_config, fixed_clock
    ):
        """Test service initializes with custom clock."""
        service = AlpacaDataService(
            event_bus=event_bus,
            config=alpaca_config,
            data_config=data_config,
            clock=fixed_clock,
        )

        assert service._clock is fixed_clock


class TestAlpacaDataServiceStart:
    """Test AlpacaDataService start method."""

    @pytest.mark.asyncio
    async def test_start_requires_api_keys(self, data_service):
        """Test start fails if API keys not in environment."""
        with pytest.raises(ValueError, match="API keys not found"):
            await data_service.start(["AAPL"], ["1m"])

    @pytest.mark.asyncio
    async def test_start_requires_1m_timeframe(self, data_service):
        """Test start fails if 1m timeframe not requested."""
        os.environ["TEST_ALPACA_API_KEY"] = "test_key"
        os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

        try:
            with pytest.raises(ValueError, match="Only 1m timeframe supported"):
                await data_service.start(["AAPL"], ["5m"])
        finally:
            del os.environ["TEST_ALPACA_API_KEY"]
            del os.environ["TEST_ALPACA_SECRET_KEY"]

    @pytest.mark.asyncio
    async def test_start_initializes_clients(
        self, data_service, mock_historical_client, mock_data_stream
    ):
        """Test start initializes Alpaca clients and subscribes."""
        os.environ["TEST_ALPACA_API_KEY"] = "test_key"
        os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

        try:
            with patch(
                "argus.data.alpaca_data_service.StockHistoricalDataClient",
                return_value=mock_historical_client,
            ), patch(
                "argus.data.alpaca_data_service.StockDataStream",
                return_value=mock_data_stream,
            ):
                # Mock warm-up to avoid historical data fetch
                with patch.object(
                    data_service, "_warm_up_indicators", new_callable=AsyncMock
                ):
                    await data_service.start(["AAPL", "TSLA"], ["1m"])

            # Verify clients initialized
            assert data_service._historical_client is mock_historical_client
            assert data_service._data_stream is mock_data_stream

            # Verify subscriptions
            mock_data_stream.subscribe_bars.assert_called_once()
            mock_data_stream.subscribe_trades.assert_called_once()

            # Verify running state
            assert data_service._running is True
            assert data_service._subscribed_symbols == {"AAPL", "TSLA"}

            # Clean up tasks
            await data_service.stop()

        finally:
            del os.environ["TEST_ALPACA_API_KEY"]
            del os.environ["TEST_ALPACA_SECRET_KEY"]


class TestAlpacaDataServiceStop:
    """Test AlpacaDataService stop method."""

    @pytest.mark.asyncio
    async def test_stop_cleans_up_resources(
        self, data_service, mock_historical_client, mock_data_stream
    ):
        """Test stop cancels tasks and closes connections."""
        os.environ["TEST_ALPACA_API_KEY"] = "test_key"
        os.environ["TEST_ALPACA_SECRET_KEY"] = "test_secret"

        try:
            with patch(
                "argus.data.alpaca_data_service.StockHistoricalDataClient",
                return_value=mock_historical_client,
            ), patch(
                "argus.data.alpaca_data_service.StockDataStream",
                return_value=mock_data_stream,
            ), patch.object(
                data_service, "_warm_up_indicators", new_callable=AsyncMock
            ):
                await data_service.start(["AAPL"], ["1m"])

            # Stop the service
            await data_service.stop()

            # Verify cleanup
            assert data_service._running is False
            mock_data_stream.stop_ws.assert_called_once()
            mock_data_stream.close.assert_called_once()

        finally:
            del os.environ["TEST_ALPACA_API_KEY"]
            del os.environ["TEST_ALPACA_SECRET_KEY"]


class TestAlpacaDataServicePriceCache:
    """Test AlpacaDataService price cache methods."""

    @pytest.mark.asyncio
    async def test_get_current_price_raises_for_unknown_symbol(self, data_service):
        """Test get_current_price raises ValueError for unknown symbol."""
        with pytest.raises(ValueError, match="No price data available"):
            await data_service.get_current_price("AAPL")

    @pytest.mark.asyncio
    async def test_get_current_price_returns_cached_value(self, data_service):
        """Test get_current_price returns latest trade price."""
        data_service._price_cache["AAPL"] = 150.50

        price = await data_service.get_current_price("AAPL")
        assert price == 150.50


class TestAlpacaDataServiceIndicators:
    """Test AlpacaDataService indicator methods."""

    @pytest.mark.asyncio
    async def test_get_indicator_raises_for_unknown_symbol(self, data_service):
        """Test get_indicator raises ValueError for unknown symbol."""
        with pytest.raises(ValueError, match="No indicator state"):
            await data_service.get_indicator("AAPL", "vwap")

    @pytest.mark.asyncio
    async def test_get_indicator_raises_for_unavailable_indicator(self, data_service):
        """Test get_indicator raises ValueError if indicator not computed yet."""
        # Create state with no data
        state = IndicatorState()
        data_service._indicator_state["AAPL"] = state

        with pytest.raises(ValueError, match="not available"):
            await data_service.get_indicator("AAPL", "vwap")

    @pytest.mark.asyncio
    async def test_get_indicator_returns_computed_value(self, data_service):
        """Test get_indicator returns computed indicator value."""
        # Create state and set a value
        state = IndicatorState()
        state.vwap = 150.25
        data_service._indicator_state["AAPL"] = state

        vwap = await data_service.get_indicator("AAPL", "vwap")
        assert isinstance(vwap, float)
        assert vwap == 150.25


class TestAlpacaDataServiceHistoricalCandles:
    """Test AlpacaDataService historical candle fetching."""

    @pytest.mark.asyncio
    async def test_get_historical_candles_raises_if_client_not_initialized(
        self, data_service
    ):
        """Test get_historical_candles raises if client not ready."""
        start = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)
        end = datetime(2026, 2, 15, 10, 30, 0, tzinfo=UTC)

        with pytest.raises(ValueError, match="Historical client not initialized"):
            await data_service.get_historical_candles("AAPL", "1m", start, end)

    @pytest.mark.asyncio
    async def test_get_historical_candles_fetches_and_formats(
        self, data_service, mock_historical_client
    ):
        """Test get_historical_candles fetches from Alpaca and formats correctly."""
        data_service._historical_client = mock_historical_client

        # Mock response
        mock_bar = MagicMock()
        mock_bar.timestamp = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)
        mock_bar.open = 150.0
        mock_bar.high = 151.0
        mock_bar.low = 149.0
        mock_bar.close = 150.5
        mock_bar.volume = 1000000

        mock_historical_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        start = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)
        end = datetime(2026, 2, 15, 10, 30, 0, tzinfo=UTC)

        df = await data_service.get_historical_candles("AAPL", "1m", start, end)

        assert not df.empty
        assert len(df) == 1
        assert list(df.columns) == [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        assert df.iloc[0]["open"] == 150.0
        assert df.iloc[0]["close"] == 150.5
        assert df.iloc[0]["volume"] == 1000000

    @pytest.mark.asyncio
    async def test_get_historical_candles_returns_empty_for_no_data(
        self, data_service, mock_historical_client
    ):
        """Test get_historical_candles returns empty DataFrame if no data."""
        data_service._historical_client = mock_historical_client
        mock_historical_client.get_stock_bars.return_value = {}

        start = datetime(2026, 2, 15, 9, 30, 0, tzinfo=UTC)
        end = datetime(2026, 2, 15, 10, 30, 0, tzinfo=UTC)

        df = await data_service.get_historical_candles("AAPL", "1m", start, end)

        assert df.empty
        assert list(df.columns) == [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]


class TestAlpacaDataServiceWarmUp:
    """Test AlpacaDataService indicator warm-up."""

    @pytest.mark.asyncio
    async def test_warm_up_indicators_fetches_historical_data(
        self, data_service, mock_historical_client, fixed_clock
    ):
        """Test warm-up fetches historical candles and initializes engines."""
        data_service._historical_client = mock_historical_client

        # Mock historical data
        mock_bars = []
        base_time = fixed_clock.now() - timedelta(minutes=60)
        for i in range(60):
            bar = MagicMock()
            bar.timestamp = base_time + timedelta(minutes=i)
            bar.open = 150.0 + i * 0.1
            bar.high = 151.0 + i * 0.1
            bar.low = 149.0 + i * 0.1
            bar.close = 150.5 + i * 0.1
            bar.volume = 1000000
            mock_bars.append(bar)

        mock_historical_client.get_stock_bars.return_value = {"AAPL": mock_bars}

        await data_service._warm_up_indicators(["AAPL"])

        # Verify indicator state created
        assert "AAPL" in data_service._indicator_state

        # Verify VWAP computed
        state = data_service._indicator_state["AAPL"]
        assert state.vwap is not None
        assert state.vwap > 0


class TestAlpacaDataServiceEventHandlers:
    """Test AlpacaDataService WebSocket event handlers."""

    @pytest.mark.asyncio
    async def test_on_bar_publishes_candle_and_indicator_events(
        self, data_service, event_bus, fixed_clock
    ):
        """Test _on_bar handler publishes CandleEvent and IndicatorEvents."""
        # Initialize indicator state
        state = IndicatorState()
        state.vwap_date = fixed_clock.now().strftime("%Y-%m-%d")
        data_service._indicator_state["AAPL"] = state

        # Create mock bar
        bar = MagicMock()
        bar.symbol = "AAPL"
        bar.timestamp = fixed_clock.now()
        bar.open = 150.0
        bar.high = 151.0
        bar.low = 149.0
        bar.close = 150.5
        bar.volume = 1000000

        # Track published events
        published_events = []

        async def capture_event(event):
            published_events.append(event)

        event_bus.subscribe(CandleEvent, capture_event)
        event_bus.subscribe(IndicatorEvent, capture_event)

        # Call handler
        await data_service._on_bar(bar)

        # Give event loop time to process
        await asyncio.sleep(0.1)

        # Verify events published
        candle_events = [e for e in published_events if isinstance(e, CandleEvent)]
        indicator_events = [e for e in published_events if isinstance(e, IndicatorEvent)]

        assert len(candle_events) == 1
        assert candle_events[0].symbol == "AAPL"
        assert candle_events[0].close == 150.5

        # Should have published at least VWAP
        assert len(indicator_events) > 0
        vwap_events = [e for e in indicator_events if e.indicator_name == "vwap"]
        assert len(vwap_events) == 1

    @pytest.mark.asyncio
    async def test_on_trade_updates_price_cache_and_publishes_tick_event(
        self, data_service, event_bus, fixed_clock
    ):
        """Test _on_trade handler updates cache and publishes TickEvent."""
        # Create mock trade
        trade = MagicMock()
        trade.symbol = "AAPL"
        trade.timestamp = fixed_clock.now()
        trade.price = 150.75
        trade.size = 100

        # Track published events
        published_events = []

        async def capture_event(event):
            published_events.append(event)

        event_bus.subscribe(TickEvent, capture_event)

        # Call handler
        await data_service._on_trade(trade)

        # Give event loop time to process
        await asyncio.sleep(0.1)

        # Verify price cache updated
        assert data_service._price_cache["AAPL"] == 150.75

        # Verify TickEvent published
        tick_events = [e for e in published_events if isinstance(e, TickEvent)]
        assert len(tick_events) == 1
        assert tick_events[0].symbol == "AAPL"
        assert tick_events[0].price == 150.75
        assert tick_events[0].volume == 100


class TestAlpacaDataServiceStaleDataMonitor:
    """Test AlpacaDataService stale data monitoring."""

    @pytest.mark.asyncio
    async def test_stale_data_detection(
        self, data_service, alpaca_config, fixed_clock
    ):
        """Test stale data monitor sets flag after timeout."""
        # Set up initial state
        data_service._running = True
        data_service._subscribed_symbols = {"AAPL"}
        data_service._last_data_time["AAPL"] = fixed_clock.now()

        # Start monitor
        monitor_task = asyncio.create_task(data_service._stale_data_monitor())

        # Wait for first check
        await asyncio.sleep(0.1)
        assert data_service._is_stale is False

        # Advance clock past timeout
        fixed_clock.advance(seconds=alpaca_config.stale_data_timeout_seconds + 1)

        # Wait for next check
        await asyncio.sleep(6)

        # Verify stale flag set
        assert data_service._is_stale is True

        # Clean up
        data_service._running = False
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_stale_data_recovery(self, data_service, alpaca_config, fixed_clock):
        """Test stale data monitor clears flag when data resumes."""
        # Set up stale state
        data_service._running = True
        data_service._subscribed_symbols = {"AAPL"}
        data_service._last_data_time["AAPL"] = (
            fixed_clock.now() - timedelta(seconds=40)
        )
        data_service._is_stale = True

        # Start monitor
        monitor_task = asyncio.create_task(data_service._stale_data_monitor())

        # Simulate fresh data
        data_service._last_data_time["AAPL"] = fixed_clock.now()

        # Wait for check
        await asyncio.sleep(6)

        # Verify stale flag cleared
        assert data_service._is_stale is False

        # Clean up
        data_service._running = False
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


class TestAlpacaDataServiceReconnection:
    """Test AlpacaDataService WebSocket reconnection."""

    @pytest.mark.asyncio
    async def test_reconnection_with_exponential_backoff(
        self, data_service, mock_data_stream, alpaca_config
    ):
        """Test reconnection uses exponential backoff with jitter."""
        data_service._data_stream = mock_data_stream
        data_service._running = True

        # Mock stream to fail 3 times then succeed with CancelledError (stop)
        mock_data_stream._run_forever.side_effect = [
            Exception("Connection failed 1"),
            Exception("Connection failed 2"),
            Exception("Connection failed 3"),
            asyncio.CancelledError(),  # Simulate stop
        ]

        # Mock asyncio.sleep and random.random to make test deterministic
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("random.random", return_value=0.5):  # Jitter = 0% (0.5 * 2 - 1 = 0)
                # Run reconnection
                try:
                    await data_service._run_stream_with_reconnect()
                except asyncio.CancelledError:
                    pass

        # Verify exponential backoff delays
        # First failure: 1s * 2^0 = 1s (+ 0% jitter = 1.0s)
        # Second failure: 1s * 2^1 = 2s (+ 0% jitter = 2.0s)
        # Third failure: 1s * 2^2 = 4s (+ 0% jitter = 4.0s)
        assert mock_sleep.call_count == 3
        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        assert sleep_calls[0] == pytest.approx(1.0, abs=0.01)
        assert sleep_calls[1] == pytest.approx(2.0, abs=0.01)
        assert sleep_calls[2] == pytest.approx(4.0, abs=0.01)

        # Verify 3 consecutive failures tracked
        assert data_service._consecutive_failures == 3
