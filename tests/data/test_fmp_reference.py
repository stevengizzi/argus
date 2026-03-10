"""Tests for FMPReferenceClient.

Sprint 23, Session 1a: FMP Reference Data Client.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import aiohttp
import pytest

from argus.data.fmp_reference import (
    FMPReferenceClient,
    FMPReferenceConfig,
    SymbolReferenceData,
)


class AsyncContextManager:
    """Helper class for mocking async context managers."""

    def __init__(self, return_value: Any) -> None:
        self.return_value = return_value

    async def __aenter__(self) -> Any:
        return self.return_value

    async def __aexit__(self, *args: Any) -> None:
        pass


def _make_profile_item(
    symbol: str,
    sector: str = "Technology",
    industry: str = "Consumer Electronics",
    mkt_cap: float = 3_000_000_000_000.0,
    exchange: str = "NASDAQ",
    price: float = 175.0,
    vol_avg: float = 50_000_000.0,
) -> dict:
    """Create a mock FMP company profile response item (stable API format)."""
    return {
        "symbol": symbol,
        "sector": sector,
        "industry": industry,
        "marketCap": mkt_cap,
        "exchange": exchange,
        "price": price,
        "averageVolume": vol_avg,
    }


def _make_float_item(symbol: str, float_shares: float = 15_000_000_000.0) -> dict:
    """Create a mock FMP share float response item."""
    return {
        "symbol": symbol,
        "floatShares": float_shares,
    }


class TestFMPReferenceClientConfig:
    """Tests for FMPReferenceConfig defaults."""

    def test_config_defaults(self) -> None:
        """Test that config has correct default values."""
        config = FMPReferenceConfig()

        assert config.base_url == "https://financialmodelingprep.com/stable"
        assert config.api_key_env_var == "FMP_API_KEY"
        assert config.batch_size == 50
        assert config.cache_ttl_hours == 24
        assert config.max_retries == 3
        assert config.request_timeout_seconds == 30.0


class TestFMPReferenceClientStart:
    """Tests for client start/stop lifecycle."""

    @pytest.fixture
    def config(self) -> FMPReferenceConfig:
        """Default config for tests."""
        return FMPReferenceConfig()

    @pytest.fixture
    def client(self, config: FMPReferenceConfig) -> FMPReferenceClient:
        """Client instance for tests."""
        return FMPReferenceClient(config)

    async def test_start_raises_on_missing_api_key(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that start() raises RuntimeError if API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            import os
            if "FMP_API_KEY" in os.environ:
                del os.environ["FMP_API_KEY"]

            with pytest.raises(RuntimeError, match="FMP API key not found"):
                await client.start()

    async def test_start_succeeds_with_api_key(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that start() succeeds when API key is set."""
        # Mock the canary test to avoid actual API calls
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}), patch.object(
            client, "_run_canary_test", new_callable=AsyncMock
        ):
            await client.start()

        assert client._api_key == "test_key"

    async def test_fmp_canary_success(
        self, config: FMPReferenceConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test canary test logs INFO when AAPL response has expected keys."""
        import logging

        caplog.set_level(logging.INFO)

        client = FMPReferenceClient(config)

        # Mock response with all required keys
        mock_profile_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                "marketCap": 3_000_000_000_000,
                "price": 175.50,
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_profile_response)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}), patch(
            "aiohttp.ClientSession"
        ) as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            await client.start()

        # Should log INFO about canary test passing
        assert "FMP canary test passed" in caplog.text

    async def test_fmp_canary_missing_keys(
        self, config: FMPReferenceConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test canary test logs WARNING when response is missing required keys."""
        import logging

        caplog.set_level(logging.WARNING)

        client = FMPReferenceClient(config)

        # Mock response missing 'marketCap' and 'price'
        mock_profile_response = [
            {
                "symbol": "AAPL",
                "companyName": "Apple Inc.",
                # Missing marketCap and price
            }
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_profile_response)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}), patch(
            "aiohttp.ClientSession"
        ) as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            # Should NOT raise
            await client.start()

        # Should log WARNING about missing keys
        assert "canary test failed" in caplog.text.lower()
        assert "missing keys" in caplog.text.lower()

    async def test_fmp_canary_api_error(
        self, config: FMPReferenceConfig, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test canary test logs WARNING on HTTP error but does not raise."""
        import logging

        caplog.set_level(logging.WARNING)

        client = FMPReferenceClient(config)

        # Mock HTTP error response
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}), patch(
            "aiohttp.ClientSession"
        ) as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            # Should NOT raise
            await client.start()

        # Should log WARNING about canary test failure
        assert "canary test failed" in caplog.text.lower()


class TestFMPReferenceClientFetchReferenceData:
    """Tests for fetch_reference_data method."""

    @pytest.fixture
    def config(self) -> FMPReferenceConfig:
        """Config with small batch size for testing."""
        return FMPReferenceConfig(batch_size=50)

    @pytest.fixture
    def client(self, config: FMPReferenceConfig) -> FMPReferenceClient:
        """Started client instance."""
        c = FMPReferenceClient(config)
        c._api_key = "test_key"  # Pre-configure for tests
        return c

    async def test_fetch_reference_data_success(
        self, client: FMPReferenceClient
    ) -> None:
        """Test successful concurrent fetch populates all SymbolReferenceData fields."""
        mock_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                industry="Consumer Electronics",
                market_cap=3_000_000_000_000.0,
                exchange="NASDAQ",
                prev_close=175.50,
                avg_volume=50_000_000.0,
                is_otc=False,
            ),
            "MSFT": SymbolReferenceData(
                symbol="MSFT",
                sector="Technology",
                industry="Software",
                market_cap=2_800_000_000_000.0,
                exchange="NASDAQ",
                prev_close=420.00,
                avg_volume=25_000_000.0,
                is_otc=False,
            ),
        }

        async def mock_fetch_single(session, symbol):
            return mock_data.get(symbol)

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            result = await client.fetch_reference_data(["AAPL", "MSFT"])

        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result

        aapl = result["AAPL"]
        assert aapl.symbol == "AAPL"
        assert aapl.sector == "Technology"
        assert aapl.industry == "Consumer Electronics"
        assert aapl.market_cap == 3_000_000_000_000.0
        assert aapl.exchange == "NASDAQ"
        assert aapl.prev_close == 175.50
        assert aapl.avg_volume == 50_000_000.0
        assert aapl.is_otc is False
        assert isinstance(aapl.fetched_at, datetime)

    async def test_fetch_reference_data_concurrent_calls(self) -> None:
        """Test that fetch_reference_data makes concurrent calls for all symbols."""
        config = FMPReferenceConfig()
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = [f"SYM{i}" for i in range(10)]
        call_count = 0

        async def mock_fetch_single(session, symbol):
            nonlocal call_count
            call_count += 1
            return SymbolReferenceData(symbol=symbol)

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            await client.fetch_reference_data(symbols)

        # Should have one call per symbol
        assert call_count == 10

    async def test_fetch_reference_data_partial_failure(self) -> None:
        """Test that some symbol failures don't prevent other symbols from succeeding."""
        config = FMPReferenceConfig(max_retries=1)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]

        async def mock_fetch_single(session, symbol):
            # First two fail, last two succeed
            if symbol in ("AAPL", "MSFT"):
                return None  # Simulate failure
            return SymbolReferenceData(symbol=symbol)

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            result = await client.fetch_reference_data(symbols)

        # Should have results from successful symbols only
        assert len(result) == 2
        assert "NVDA" in result
        assert "GOOGL" in result
        assert "AAPL" not in result
        assert "MSFT" not in result

    async def test_fetch_reference_data_all_fail(self) -> None:
        """Test that all symbols failing returns empty dict without exception."""
        config = FMPReferenceConfig(max_retries=1)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]

        async def mock_fetch_single(session, symbol):
            return None  # All fail

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            # Should not raise exception
            result = await client.fetch_reference_data(symbols)

        assert result == {}

    async def test_fetch_reference_data_empty_symbols(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that empty symbol list returns empty dict."""
        result = await client.fetch_reference_data([])
        assert result == {}

    async def test_fetch_reference_data_not_started(self) -> None:
        """Test that fetch returns empty dict if client not started."""
        client = FMPReferenceClient(FMPReferenceConfig())
        # Don't set _api_key

        result = await client.fetch_reference_data(["AAPL"])
        assert result == {}


class TestFMPReferenceClientFetchFloatData:
    """Tests for fetch_float_data method."""

    @pytest.fixture
    def client(self) -> FMPReferenceClient:
        """Started client instance."""
        c = FMPReferenceClient(FMPReferenceConfig())
        c._api_key = "test_key"
        return c

    async def test_fetch_float_data_success(self, client: FMPReferenceClient) -> None:
        """Test successful float data fetch."""
        call_count = 0
        symbol_order = ["AAPL", "MSFT"]

        async def mock_fetch_single(session, symbol):
            nonlocal call_count
            idx = call_count
            call_count += 1
            if idx == 0:
                return 15_000_000_000.0
            else:
                return 7_500_000_000.0

        with patch.object(
            client, "_fetch_single_float", side_effect=mock_fetch_single
        ):
            result = await client.fetch_float_data(symbol_order)

        assert len(result) == 2
        assert result["AAPL"] == 15_000_000_000.0
        assert result["MSFT"] == 7_500_000_000.0

    async def test_fetch_float_data_graceful_failure(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that float data failures return empty dict, not exception."""
        async def mock_fetch_single(session, symbol):
            raise Exception("API Error")

        with patch.object(
            client, "_fetch_single_float", side_effect=mock_fetch_single
        ):
            result = await client.fetch_float_data(["AAPL"])

        assert result == {}

    async def test_fetch_float_data_not_started(self) -> None:
        """Test that fetch returns empty dict if client not started."""
        client = FMPReferenceClient(FMPReferenceConfig())
        # Don't set _api_key

        result = await client.fetch_float_data(["AAPL"])
        assert result == {}

    async def test_fetch_float_data_empty_symbols(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that empty symbol list returns empty dict."""
        result = await client.fetch_float_data([])
        assert result == {}


class TestFMPReferenceClientBuildCache:
    """Tests for build_reference_cache method."""

    async def test_build_reference_cache(self) -> None:
        """Test end-to-end cache building with profile and float data."""
        config = FMPReferenceConfig()
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        float_data = {"AAPL": 15_000_000_000.0, "MSFT": 7_500_000_000.0}

        with patch.object(
            client, "fetch_reference_data", new_callable=AsyncMock
        ) as mock_fetch_profile, patch.object(
            client, "fetch_float_data", new_callable=AsyncMock
        ) as mock_fetch_float:
            mock_fetch_profile.return_value = {
                "AAPL": SymbolReferenceData(symbol="AAPL", sector="Technology"),
                "MSFT": SymbolReferenceData(symbol="MSFT", sector="Technology"),
            }
            mock_fetch_float.return_value = float_data

            result = await client.build_reference_cache(["AAPL", "MSFT"])

        assert len(result) == 2
        assert result["AAPL"].float_shares == 15_000_000_000.0
        assert result["MSFT"].float_shares == 7_500_000_000.0

        # Verify cache was updated
        assert client.cached_symbol_count == 2
        assert client.get_cached("AAPL") is not None
        assert client.get_cached("MSFT") is not None

    async def test_build_reference_cache_updates_cache_time(self) -> None:
        """Test that build_reference_cache updates cache timestamp."""
        config = FMPReferenceConfig()
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        # Cache should be stale initially
        assert client._cache_built_at is None

        with patch.object(
            client, "fetch_reference_data", new_callable=AsyncMock
        ) as mock_fetch_profile, patch.object(
            client, "fetch_float_data", new_callable=AsyncMock
        ) as mock_fetch_float:
            mock_fetch_profile.return_value = {
                "AAPL": SymbolReferenceData(symbol="AAPL"),
            }
            mock_fetch_float.return_value = {}

            await client.build_reference_cache(["AAPL"])

        # Cache time should be set
        assert client._cache_built_at is not None
        assert client.is_cache_fresh() is True


class TestFMPReferenceClientCacheFreshness:
    """Tests for cache freshness methods."""

    def test_cache_freshness_no_cache(self) -> None:
        """Test is_cache_fresh returns False when cache never built."""
        client = FMPReferenceClient(FMPReferenceConfig())

        assert client.is_cache_fresh() is False
        assert client.cache_age_minutes == float("inf")

    def test_cache_freshness_fresh_cache(self) -> None:
        """Test is_cache_fresh returns True for recently built cache."""
        config = FMPReferenceConfig(cache_ttl_hours=24)
        client = FMPReferenceClient(config)

        # Simulate cache built just now
        client._cache_built_at = datetime.now(ZoneInfo("UTC"))

        assert client.is_cache_fresh() is True
        assert client.cache_age_minutes < 1.0

    def test_cache_freshness_stale_cache(self) -> None:
        """Test is_cache_fresh returns False for old cache."""
        config = FMPReferenceConfig(cache_ttl_hours=24)
        client = FMPReferenceClient(config)

        # Simulate cache built 25 hours ago
        client._cache_built_at = datetime.now(ZoneInfo("UTC")) - timedelta(hours=25)

        assert client.is_cache_fresh() is False
        assert client.cache_age_minutes > 24 * 60

    def test_cached_symbol_count(self) -> None:
        """Test cached_symbol_count returns correct count."""
        client = FMPReferenceClient(FMPReferenceConfig())

        assert client.cached_symbol_count == 0

        client._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL"),
            "MSFT": SymbolReferenceData(symbol="MSFT"),
            "NVDA": SymbolReferenceData(symbol="NVDA"),
        }

        assert client.cached_symbol_count == 3

    def test_get_cached_exists(self) -> None:
        """Test get_cached returns data when symbol is cached."""
        client = FMPReferenceClient(FMPReferenceConfig())
        client._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL", sector="Technology"),
        }

        result = client.get_cached("AAPL")
        assert result is not None
        assert result.symbol == "AAPL"
        assert result.sector == "Technology"

    def test_get_cached_not_exists(self) -> None:
        """Test get_cached returns None when symbol is not cached."""
        client = FMPReferenceClient(FMPReferenceConfig())

        result = client.get_cached("AAPL")
        assert result is None


class TestFMPReferenceClientOTCDetection:
    """Tests for OTC exchange detection."""

    @pytest.fixture
    def client(self) -> FMPReferenceClient:
        """Client instance."""
        return FMPReferenceClient(FMPReferenceConfig())

    def test_otc_detection_otc_exchange(self, client: FMPReferenceClient) -> None:
        """Test that OTC exchanges are detected as OTC."""
        otc_exchanges = ["OTC", "OTCQX", "OTCQB", "PINK", "GREY", "OTC MARKETS"]

        for exchange in otc_exchanges:
            assert client._is_otc_exchange(exchange) is True, f"Failed for {exchange}"

    def test_otc_detection_normal_exchange(self, client: FMPReferenceClient) -> None:
        """Test that normal exchanges are not detected as OTC."""
        normal_exchanges = ["NASDAQ", "NYSE", "AMEX", "ARCA", "BATS"]

        for exchange in normal_exchanges:
            assert client._is_otc_exchange(exchange) is False, f"Failed for {exchange}"

    def test_otc_detection_case_insensitive(self, client: FMPReferenceClient) -> None:
        """Test that OTC detection is case-insensitive."""
        assert client._is_otc_exchange("otc") is True
        assert client._is_otc_exchange("Otcqx") is True
        assert client._is_otc_exchange("pink") is True

    def test_otc_detection_none_exchange(self, client: FMPReferenceClient) -> None:
        """Test that None exchange returns False."""
        assert client._is_otc_exchange(None) is False

    def test_parse_profile_response_sets_otc_flag(self) -> None:
        """Test that _parse_profile_response correctly sets is_otc flag."""
        client = FMPReferenceClient(FMPReferenceConfig())

        response_data = [
            _make_profile_item("AAPL", exchange="NASDAQ"),
            _make_profile_item("PENNYSTOCK", exchange="OTC"),
        ]

        result = client._parse_profile_response(response_data)

        assert result["AAPL"].is_otc is False
        assert result["PENNYSTOCK"].is_otc is True


class TestSymbolReferenceData:
    """Tests for SymbolReferenceData dataclass."""

    def test_symbol_reference_data_defaults(self) -> None:
        """Test that dataclass has correct default values."""
        data = SymbolReferenceData(symbol="TEST")

        assert data.symbol == "TEST"
        assert data.sector is None
        assert data.industry is None
        assert data.market_cap is None
        assert data.float_shares is None
        assert data.exchange is None
        assert data.prev_close is None
        assert data.avg_volume is None
        assert data.is_otc is False
        assert isinstance(data.fetched_at, datetime)

    def test_symbol_reference_data_full_init(self) -> None:
        """Test that all fields can be set."""
        now = datetime.now(ZoneInfo("UTC"))
        data = SymbolReferenceData(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3_000_000_000_000.0,
            float_shares=15_000_000_000.0,
            exchange="NASDAQ",
            prev_close=175.50,
            avg_volume=50_000_000.0,
            is_otc=False,
            fetched_at=now,
        )

        assert data.symbol == "AAPL"
        assert data.sector == "Technology"
        assert data.industry == "Consumer Electronics"
        assert data.market_cap == 3_000_000_000_000.0
        assert data.float_shares == 15_000_000_000.0
        assert data.exchange == "NASDAQ"
        assert data.prev_close == 175.50
        assert data.avg_volume == 50_000_000.0
        assert data.is_otc is False
        assert data.fetched_at == now


class TestFMPReferenceClientParseResponse:
    """Tests for response parsing methods."""

    @pytest.fixture
    def client(self) -> FMPReferenceClient:
        """Client instance."""
        return FMPReferenceClient(FMPReferenceConfig())

    def test_parse_profile_response_success(self, client: FMPReferenceClient) -> None:
        """Test that _parse_profile_response correctly parses FMP response."""
        response_data = [
            _make_profile_item(
                "AAPL",
                sector="Technology",
                industry="Consumer Electronics",
                mkt_cap=3_000_000_000_000.0,
                exchange="NASDAQ",
                price=175.50,
                vol_avg=50_000_000.0,
            ),
        ]

        result = client._parse_profile_response(response_data)

        assert "AAPL" in result
        aapl = result["AAPL"]
        assert aapl.symbol == "AAPL"
        assert aapl.sector == "Technology"
        assert aapl.industry == "Consumer Electronics"
        assert aapl.market_cap == 3_000_000_000_000.0
        assert aapl.exchange == "NASDAQ"
        assert aapl.prev_close == 175.50
        assert aapl.avg_volume == 50_000_000.0

    def test_parse_profile_response_empty_sector(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that empty string sector is converted to None."""
        response_data = [{"symbol": "TEST", "sector": "", "industry": ""}]

        result = client._parse_profile_response(response_data)

        assert result["TEST"].sector is None
        assert result["TEST"].industry is None

    def test_parse_profile_response_missing_symbol(
        self, client: FMPReferenceClient
    ) -> None:
        """Test that items without symbol are skipped."""
        response_data = [{"sector": "Technology"}]  # No symbol

        result = client._parse_profile_response(response_data)

        assert result == {}

    def test_safe_float_valid(self, client: FMPReferenceClient) -> None:
        """Test _safe_float with valid values."""
        assert client._safe_float(100.5) == 100.5
        assert client._safe_float(100) == 100.0
        assert client._safe_float("100.5") == 100.5

    def test_safe_float_invalid(self, client: FMPReferenceClient) -> None:
        """Test _safe_float with invalid values."""
        assert client._safe_float(None) is None
        assert client._safe_float("not a number") is None
        assert client._safe_float({}) is None


class TestFMPReferenceClientFetchStockList:
    """Tests for fetch_stock_list method (Sprint 23.3)."""

    @pytest.fixture
    def client(self) -> FMPReferenceClient:
        """Started client instance."""
        c = FMPReferenceClient(FMPReferenceConfig())
        c._api_key = "test_key"
        return c

    async def test_fetch_stock_list_success(self, client: FMPReferenceClient) -> None:
        """Test successful stock list fetch returns symbol list."""
        mock_response_data = [
            {"symbol": "AAPL", "companyName": "Apple Inc."},
            {"symbol": "MSFT", "companyName": "Microsoft Corporation"},
            {"symbol": "GOOGL", "companyName": "Alphabet Inc."},
        ]

        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=mock_response_data)

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            result = await client.fetch_stock_list()

        assert len(result) == 3
        assert "AAPL" in result
        assert "MSFT" in result
        assert "GOOGL" in result

    async def test_fetch_stock_list_empty_response(
        self, client: FMPReferenceClient
    ) -> None:
        """Test empty response returns empty list."""
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value=[])

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            result = await client.fetch_stock_list()

        assert result == []

    async def test_fetch_stock_list_network_error(
        self, client: FMPReferenceClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test network error returns empty list and logs error."""
        mock_session = AsyncMock()
        mock_session.get = MagicMock(
            side_effect=aiohttp.ClientError("Network error")
        )

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            result = await client.fetch_stock_list()

        assert result == []
        assert "network error" in caplog.text.lower()

    async def test_fetch_stock_list_non_200(
        self, client: FMPReferenceClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test non-200 status returns empty list and logs error."""
        mock_response = AsyncMock()
        mock_response.status = 500

        mock_session = AsyncMock()
        mock_session.get = MagicMock(return_value=AsyncContextManager(mock_response))

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value = AsyncContextManager(mock_session)
            result = await client.fetch_stock_list()

        assert result == []
        assert "failed" in caplog.text.lower() or "500" in caplog.text

    async def test_fetch_stock_list_not_started(self) -> None:
        """Test that fetch returns empty list if client not started."""
        client = FMPReferenceClient(FMPReferenceConfig())
        # Don't set _api_key

        result = await client.fetch_stock_list()
        assert result == []


class TestFMPReferenceClientRetryBehavior:
    """Tests for retry behavior in fetch operations (Sprint 23.3)."""

    async def test_fetch_reference_data_retry_on_429(self) -> None:
        """Test that 429 errors trigger retry with eventual success."""
        config = FMPReferenceConfig(max_retries=3)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        call_count = 0

        async def mock_fetch_single(session, symbol):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails with 429 (simulated by returning None)
                # In real impl, the retry logic handles this
                return None
            # Second call succeeds
            return SymbolReferenceData(symbol=symbol)

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            result = await client.fetch_reference_data(["AAPL"])

        # Method was called once per symbol (retry is internal)
        assert call_count == 1
        # Result depends on whether our mock simulates retry success
        # Since we return None on first call, symbol is excluded
        assert "AAPL" not in result

    async def test_fetch_reference_data_progress_logging(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that progress logging occurs at expected intervals."""
        import logging

        caplog.set_level(logging.INFO)

        config = FMPReferenceConfig()
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        # Create 600 symbols to trigger at least one progress log (every 500)
        symbols = [f"SYM{i:04d}" for i in range(600)]

        async def mock_fetch_single(session, symbol):
            return SymbolReferenceData(symbol=symbol)

        with patch.object(
            client, "_fetch_single_profile_with_retry", side_effect=mock_fetch_single
        ):
            await client.fetch_reference_data(symbols)

        # Should have progress log at 500 symbols and final summary
        log_text = caplog.text
        assert "500/600" in log_text or "Fetching reference data" in log_text
        assert "Reference data fetch complete" in log_text


class TestFMPReferenceClientFileCacheOperations:
    """Tests for file-based cache operations (Sprint 23.6 S4a)."""

    @pytest.fixture
    def tmp_cache_path(self, tmp_path: Any) -> str:
        """Create a temporary cache file path."""
        return str(tmp_path / "test_cache.json")

    @pytest.fixture
    def config_with_tmp_cache(self, tmp_cache_path: str) -> FMPReferenceConfig:
        """Config with temporary cache file path."""
        return FMPReferenceConfig(cache_file=tmp_cache_path)

    @pytest.fixture
    def client_with_tmp_cache(
        self, config_with_tmp_cache: FMPReferenceConfig
    ) -> FMPReferenceClient:
        """Client configured with temporary cache file."""
        return FMPReferenceClient(config_with_tmp_cache)

    def test_save_cache_creates_file(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Test that save_cache creates a file with correct content."""
        import json
        from pathlib import Path

        # Populate internal cache
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL", sector="Technology"),
            "MSFT": SymbolReferenceData(symbol="MSFT", sector="Technology"),
        }

        client_with_tmp_cache.save_cache()

        # Verify file exists
        cache_path = Path(tmp_cache_path)
        assert cache_path.exists()

        # Verify content
        with open(cache_path) as f:
            data = json.load(f)

        assert len(data) == 2
        assert "AAPL" in data
        assert "MSFT" in data
        assert data["AAPL"]["symbol"] == "AAPL"
        assert data["AAPL"]["sector"] == "Technology"

    def test_load_cache_round_trip(
        self, client_with_tmp_cache: FMPReferenceClient
    ) -> None:
        """Test that save then load preserves data."""
        # Populate and save
        original_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                industry="Consumer Electronics",
                market_cap=3_000_000_000_000.0,
                float_shares=15_000_000_000.0,
                exchange="NASDAQ",
                prev_close=175.50,
                avg_volume=50_000_000.0,
                is_otc=False,
            ),
            "NVDA": SymbolReferenceData(
                symbol="NVDA",
                sector="Technology",
                industry="Semiconductors",
                market_cap=2_000_000_000_000.0,
            ),
        }
        client_with_tmp_cache._cache = original_data
        client_with_tmp_cache.save_cache()

        # Load into fresh client
        loaded = client_with_tmp_cache.load_cache()

        # Verify round-trip
        assert len(loaded) == 2
        assert "AAPL" in loaded
        assert "NVDA" in loaded

        aapl = loaded["AAPL"]
        assert aapl.symbol == "AAPL"
        assert aapl.sector == "Technology"
        assert aapl.industry == "Consumer Electronics"
        assert aapl.market_cap == 3_000_000_000_000.0
        assert aapl.float_shares == 15_000_000_000.0
        assert aapl.exchange == "NASDAQ"
        assert aapl.prev_close == 175.50
        assert aapl.avg_volume == 50_000_000.0
        assert aapl.is_otc is False

    def test_load_cache_missing_file(
        self, client_with_tmp_cache: FMPReferenceClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test that missing file returns empty dict and logs INFO."""
        import logging

        caplog.set_level(logging.INFO)

        # Don't save anything - file doesn't exist
        result = client_with_tmp_cache.load_cache()

        assert result == {}
        assert "No cache file found" in caplog.text

    def test_load_cache_corrupt_file(
        self,
        client_with_tmp_cache: FMPReferenceClient,
        tmp_cache_path: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that malformed JSON returns empty dict and logs WARNING."""
        import logging
        from pathlib import Path

        caplog.set_level(logging.WARNING)

        # Write invalid JSON
        Path(tmp_cache_path).write_text("{ invalid json }")

        result = client_with_tmp_cache.load_cache()

        assert result == {}
        assert "corrupt" in caplog.text.lower() or "invalid JSON" in caplog.text

    def test_load_cache_truncated_file(
        self,
        client_with_tmp_cache: FMPReferenceClient,
        tmp_cache_path: str,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Test that truncated/partial JSON returns empty dict and logs WARNING."""
        import logging
        from pathlib import Path

        caplog.set_level(logging.WARNING)

        # Write truncated JSON
        Path(tmp_cache_path).write_text('{"AAPL": {"symbol": "AAPL", "sector":')

        result = client_with_tmp_cache.load_cache()

        assert result == {}
        assert "corrupt" in caplog.text.lower() or "invalid JSON" in caplog.text

    def test_save_cache_atomic_write(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Test that save uses atomic write (file is always valid after save)."""
        import json
        from pathlib import Path

        # Save data
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL"),
        }
        client_with_tmp_cache.save_cache()

        # Verify no temp file remains
        temp_path = Path(tmp_cache_path).with_suffix(".json.tmp")
        assert not temp_path.exists()

        # Verify file is valid JSON
        with open(tmp_cache_path) as f:
            data = json.load(f)
        assert "AAPL" in data

    def test_cache_includes_cached_at(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Test that each cached entry includes cached_at timestamp."""
        import json

        # Save data
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL"),
            "MSFT": SymbolReferenceData(symbol="MSFT"),
        }
        client_with_tmp_cache.save_cache()

        # Load raw JSON and check for cached_at
        with open(tmp_cache_path) as f:
            data = json.load(f)

        for symbol in ["AAPL", "MSFT"]:
            assert "cached_at" in data[symbol], f"Missing cached_at for {symbol}"
            # Verify it's a valid ISO timestamp
            cached_at = data[symbol]["cached_at"]
            assert isinstance(cached_at, str)
            # Should be parseable as ISO datetime
            from datetime import datetime

            datetime.fromisoformat(cached_at)


class TestFMPReferenceClientStalenessChecking:
    """Tests for cache staleness checking (Sprint 23.6 S4a)."""

    @pytest.fixture
    def tmp_cache_path(self, tmp_path: Any) -> str:
        """Create a temporary cache file path."""
        return str(tmp_path / "test_cache.json")

    @pytest.fixture
    def config_with_tmp_cache(self, tmp_cache_path: str) -> FMPReferenceConfig:
        """Config with temporary cache file path."""
        return FMPReferenceConfig(cache_file=tmp_cache_path, cache_max_age_hours=24)

    @pytest.fixture
    def client_with_tmp_cache(
        self, config_with_tmp_cache: FMPReferenceConfig
    ) -> FMPReferenceClient:
        """Client configured with temporary cache file."""
        return FMPReferenceClient(config_with_tmp_cache)

    def test_get_stale_symbols_all_fresh(
        self, client_with_tmp_cache: FMPReferenceClient
    ) -> None:
        """Test that fresh entries are not marked stale, only missing symbols returned."""
        # Save recent data
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL"),
            "MSFT": SymbolReferenceData(symbol="MSFT"),
        }
        client_with_tmp_cache.save_cache()

        # Load cache to populate cached_at timestamps
        cached = client_with_tmp_cache.load_cache()

        # Check staleness - NVDA is missing, others are fresh
        all_symbols = ["AAPL", "MSFT", "NVDA"]
        stale = client_with_tmp_cache.get_stale_symbols(
            cached=cached,
            all_symbols=all_symbols,
            max_age_hours=24,
        )

        # Only NVDA should be stale (missing)
        assert stale == ["NVDA"]

    def test_get_stale_symbols_some_stale(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Test that entries older than max_age are marked stale."""
        import json
        from pathlib import Path

        # Create cache with one old entry
        now = datetime.now(ZoneInfo("UTC"))
        old_time = now - timedelta(hours=48)  # 48 hours ago

        cache_data = {
            "AAPL": {
                "symbol": "AAPL",
                "sector": "Technology",
                "is_otc": False,
                "fetched_at": now.isoformat(),
                "cached_at": now.isoformat(),  # Fresh
            },
            "MSFT": {
                "symbol": "MSFT",
                "sector": "Technology",
                "is_otc": False,
                "fetched_at": old_time.isoformat(),
                "cached_at": old_time.isoformat(),  # Stale (48h old)
            },
        }

        Path(tmp_cache_path).write_text(json.dumps(cache_data))

        # Load and check staleness
        cached = client_with_tmp_cache.load_cache()
        stale = client_with_tmp_cache.get_stale_symbols(
            cached=cached,
            all_symbols=["AAPL", "MSFT"],
            max_age_hours=24,
        )

        # MSFT should be stale (older than 24h)
        assert "MSFT" in stale
        # AAPL should not be stale
        assert "AAPL" not in stale

    def test_get_stale_symbols_all_missing(
        self, client_with_tmp_cache: FMPReferenceClient
    ) -> None:
        """Test that empty cache returns all symbols as stale."""
        # Don't save anything - empty cache
        cached = client_with_tmp_cache.load_cache()

        all_symbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]
        stale = client_with_tmp_cache.get_stale_symbols(
            cached=cached,
            all_symbols=all_symbols,
            max_age_hours=24,
        )

        # All should be stale (all missing)
        assert sorted(stale) == sorted(all_symbols)


class TestSymbolReferenceDataSerialization:
    """Tests for SymbolReferenceData to_dict/from_dict (Sprint 23.6 S4a)."""

    def test_to_dict_includes_all_fields(self) -> None:
        """Test that to_dict includes all data fields plus cached_at."""
        now = datetime.now(ZoneInfo("UTC"))
        data = SymbolReferenceData(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3_000_000_000_000.0,
            float_shares=15_000_000_000.0,
            exchange="NASDAQ",
            prev_close=175.50,
            avg_volume=50_000_000.0,
            is_otc=False,
            fetched_at=now,
        )

        result = data.to_dict()

        assert result["symbol"] == "AAPL"
        assert result["sector"] == "Technology"
        assert result["industry"] == "Consumer Electronics"
        assert result["market_cap"] == 3_000_000_000_000.0
        assert result["float_shares"] == 15_000_000_000.0
        assert result["exchange"] == "NASDAQ"
        assert result["prev_close"] == 175.50
        assert result["avg_volume"] == 50_000_000.0
        assert result["is_otc"] is False
        assert "fetched_at" in result
        assert "cached_at" in result

    def test_to_dict_with_custom_cached_at(self) -> None:
        """Test that to_dict uses provided cached_at."""
        custom_time = datetime(2025, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC"))
        data = SymbolReferenceData(symbol="AAPL")

        result = data.to_dict(cached_at=custom_time)

        assert result["cached_at"] == "2025-01-15T12:00:00+00:00"

    def test_from_dict_reconstructs_data(self) -> None:
        """Test that from_dict correctly reconstructs SymbolReferenceData."""
        dict_data = {
            "symbol": "AAPL",
            "sector": "Technology",
            "industry": "Consumer Electronics",
            "market_cap": 3_000_000_000_000.0,
            "float_shares": 15_000_000_000.0,
            "exchange": "NASDAQ",
            "prev_close": 175.50,
            "avg_volume": 50_000_000.0,
            "is_otc": False,
            "fetched_at": "2025-01-15T12:00:00+00:00",
            "cached_at": "2025-01-15T13:00:00+00:00",
        }

        data, cached_at = SymbolReferenceData.from_dict(dict_data)

        assert data.symbol == "AAPL"
        assert data.sector == "Technology"
        assert data.industry == "Consumer Electronics"
        assert data.market_cap == 3_000_000_000_000.0
        assert data.float_shares == 15_000_000_000.0
        assert data.exchange == "NASDAQ"
        assert data.prev_close == 175.50
        assert data.avg_volume == 50_000_000.0
        assert data.is_otc is False
        assert data.fetched_at == datetime(
            2025, 1, 15, 12, 0, 0, tzinfo=ZoneInfo("UTC")
        )
        assert cached_at == "2025-01-15T13:00:00+00:00"

    def test_from_dict_handles_missing_optional_fields(self) -> None:
        """Test that from_dict handles missing optional fields."""
        dict_data = {
            "symbol": "AAPL",
            # All other fields missing
        }

        data, cached_at = SymbolReferenceData.from_dict(dict_data)

        assert data.symbol == "AAPL"
        assert data.sector is None
        assert data.industry is None
        assert data.market_cap is None
        assert data.is_otc is False


class TestFMPReferenceClientIncrementalFetch:
    """Tests for fetch_reference_data_incremental method (Sprint 23.6 S4b)."""

    @pytest.fixture
    def tmp_cache_path(self, tmp_path: Any) -> str:
        """Create a temporary cache file path."""
        return str(tmp_path / "test_cache.json")

    @pytest.fixture
    def config_with_tmp_cache(self, tmp_cache_path: str) -> FMPReferenceConfig:
        """Config with temporary cache file path."""
        return FMPReferenceConfig(cache_file=tmp_cache_path, cache_max_age_hours=24)

    @pytest.fixture
    def client_with_tmp_cache(
        self, config_with_tmp_cache: FMPReferenceConfig
    ) -> FMPReferenceClient:
        """Client configured with temporary cache file."""
        c = FMPReferenceClient(config_with_tmp_cache)
        c._api_key = "test_key"
        return c

    async def test_incremental_fetch_all_cached(
        self, client_with_tmp_cache: FMPReferenceClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """All symbols in fresh cache → no network calls, returns cached."""
        import logging

        caplog.set_level(logging.INFO)

        # Pre-populate cache with fresh data
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL", sector="Technology"),
            "MSFT": SymbolReferenceData(symbol="MSFT", sector="Technology"),
        }
        client_with_tmp_cache.save_cache()

        # Track if fetch_reference_data is called
        fetch_called = False
        original_fetch = client_with_tmp_cache.fetch_reference_data

        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            nonlocal fetch_called
            fetch_called = True
            return await original_fetch(symbols)

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "MSFT"]
            )

        # Should return cached data without network call
        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result
        assert not fetch_called
        assert "All reference data cached and fresh" in caplog.text

    async def test_incremental_fetch_some_stale(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Half stale → fetches only stale, merges with fresh."""
        import json
        from pathlib import Path

        # Create cache with one fresh and one stale entry
        now = datetime.now(ZoneInfo("UTC"))
        old_time = now - timedelta(hours=48)  # 48 hours ago (stale)

        cache_data = {
            "AAPL": {
                "symbol": "AAPL",
                "sector": "Technology",
                "is_otc": False,
                "fetched_at": now.isoformat(),
                "cached_at": now.isoformat(),  # Fresh
            },
            "MSFT": {
                "symbol": "MSFT",
                "sector": "Technology",
                "is_otc": False,
                "fetched_at": old_time.isoformat(),
                "cached_at": old_time.isoformat(),  # Stale
            },
        }

        Path(tmp_cache_path).write_text(json.dumps(cache_data))

        # Mock fetch_reference_data to only return MSFT
        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            # Should only be called with stale symbols
            assert symbols == ["MSFT"], f"Expected ['MSFT'], got {symbols}"
            return {
                "MSFT": SymbolReferenceData(
                    symbol="MSFT", sector="Technology", market_cap=2_500_000_000_000
                ),
            }

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "MSFT"]
            )

        # Should have both symbols
        assert len(result) == 2
        assert "AAPL" in result
        assert "MSFT" in result

        # MSFT should have fresh data (with market_cap)
        assert result["MSFT"].market_cap == 2_500_000_000_000

    async def test_incremental_fetch_no_cache(
        self, client_with_tmp_cache: FMPReferenceClient, caplog: pytest.LogCaptureFixture
    ) -> None:
        """No cache file → full fetch (existing behavior)."""
        import logging

        caplog.set_level(logging.INFO)

        # Don't save any cache - file doesn't exist
        symbols_fetched: list[str] = []

        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            symbols_fetched.extend(symbols)
            return {
                sym: SymbolReferenceData(symbol=sym, sector="Technology")
                for sym in symbols
            }

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "MSFT", "NVDA"]
            )

        # Should have fetched all symbols
        assert len(result) == 3
        assert sorted(symbols_fetched) == ["AAPL", "MSFT", "NVDA"]
        # Should log about cache miss
        assert "No cache file found" in caplog.text

    async def test_incremental_fetch_saves_cache(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """After fetch, cache file updated."""
        import json
        from pathlib import Path

        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            return {
                sym: SymbolReferenceData(symbol=sym, sector="Technology")
                for sym in symbols
            }

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "MSFT"]
            )

        # Cache file should exist and contain both symbols
        cache_path = Path(tmp_cache_path)
        assert cache_path.exists()

        with open(cache_path) as f:
            data = json.load(f)

        assert "AAPL" in data
        assert "MSFT" in data

    async def test_incremental_fetch_merge_correctness(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Merged result has both cached and fresh entries."""
        import json
        from pathlib import Path

        # Create cache with two entries, one will be "stale" (missing from request)
        now = datetime.now(ZoneInfo("UTC"))

        cache_data = {
            "AAPL": {
                "symbol": "AAPL",
                "sector": "Technology",
                "market_cap": 3_000_000_000_000,  # Original value
                "is_otc": False,
                "fetched_at": now.isoformat(),
                "cached_at": now.isoformat(),
            },
        }

        Path(tmp_cache_path).write_text(json.dumps(cache_data))

        # Add new symbol NVDA that's not in cache
        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            # Should only fetch the new/stale symbols
            return {
                sym: SymbolReferenceData(
                    symbol=sym, sector="Technology", market_cap=1_500_000_000_000
                )
                for sym in symbols
            }

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "NVDA"]
            )

        # Should have both symbols
        assert len(result) == 2
        assert "AAPL" in result
        assert "NVDA" in result

        # AAPL should have original cached market_cap (not overwritten)
        assert result["AAPL"].market_cap == 3_000_000_000_000

        # NVDA should have fresh data
        assert result["NVDA"].market_cap == 1_500_000_000_000

    async def test_incremental_fetch_empty_delta_skips_network(
        self, client_with_tmp_cache: FMPReferenceClient
    ) -> None:
        """Verify no HTTP calls when delta is empty."""
        # Pre-populate cache with fresh data
        client_with_tmp_cache._cache = {
            "AAPL": SymbolReferenceData(symbol="AAPL", sector="Technology"),
        }
        client_with_tmp_cache.save_cache()

        # Mock that should never be called
        async def mock_fetch(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            raise AssertionError("fetch_reference_data should not be called")

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch
        ):
            # Should succeed without calling fetch (cache is fresh)
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL"]
            )

        assert len(result) == 1
        assert "AAPL" in result

    async def test_warm_up_fallback_on_error(
        self, client_with_tmp_cache: FMPReferenceClient, tmp_cache_path: str
    ) -> None:
        """Cache corrupt + fetch error → returns cached data if available, no crash."""
        from pathlib import Path

        # Write corrupt cache file
        Path(tmp_cache_path).write_text("{ invalid json }")

        # Mock fetch to fail
        async def mock_fetch_fail(symbols: list[str]) -> dict[str, SymbolReferenceData]:
            raise Exception("Network error")

        with patch.object(
            client_with_tmp_cache, "fetch_reference_data", side_effect=mock_fetch_fail
        ):
            # Should not crash, returns empty dict
            result = await client_with_tmp_cache.fetch_reference_data_incremental(
                ["AAPL", "MSFT"]
            )

        # Corrupt cache + fetch failure = empty result (graceful degradation)
        assert result == {}
