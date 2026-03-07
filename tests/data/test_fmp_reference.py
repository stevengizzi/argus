"""Tests for FMPReferenceClient.

Sprint 23, Session 1a: FMP Reference Data Client.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from zoneinfo import ZoneInfo

import aiohttp
import pytest

from argus.data.fmp_reference import (
    FMPReferenceClient,
    FMPReferenceConfig,
    SymbolReferenceData,
)


def _make_profile_item(
    symbol: str,
    sector: str = "Technology",
    industry: str = "Consumer Electronics",
    mkt_cap: float = 3_000_000_000_000.0,
    exchange: str = "NASDAQ",
    price: float = 175.0,
    vol_avg: float = 50_000_000.0,
) -> dict:
    """Create a mock FMP company profile response item."""
    return {
        "symbol": symbol,
        "sector": sector,
        "industry": industry,
        "mktCap": mkt_cap,
        "exchangeShortName": exchange,
        "price": price,
        "volAvg": vol_avg,
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

        assert config.base_url == "https://financialmodelingprep.com/api/v3"
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
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        assert client._api_key == "test_key"


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
        """Test successful batch fetch populates all SymbolReferenceData fields."""
        mock_batch_result = {
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

        with patch.object(
            client, "_fetch_batch", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = mock_batch_result
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

    async def test_fetch_reference_data_batch_splitting(self) -> None:
        """Test that 120 symbols with batch_size=50 makes 3 API calls."""
        config = FMPReferenceConfig(batch_size=50)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = [f"SYM{i}" for i in range(120)]
        call_count = 0

        async def mock_fetch_batch(session, batch):
            nonlocal call_count
            call_count += 1
            return {sym: SymbolReferenceData(symbol=sym) for sym in batch}

        with patch.object(client, "_fetch_batch", side_effect=mock_fetch_batch):
            await client.fetch_reference_data(symbols)

        # 120 symbols / 50 batch_size = 3 batches (ceil division)
        assert call_count == 3

    async def test_fetch_reference_data_partial_failure(self) -> None:
        """Test that one batch failure doesn't prevent other batches from succeeding."""
        config = FMPReferenceConfig(batch_size=2, max_retries=1)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]  # 2 batches of 2
        batch_num = 0

        async def mock_fetch_batch(session, batch):
            nonlocal batch_num
            batch_num += 1

            if batch_num == 1:
                # First batch fails
                raise aiohttp.ClientError("API Error")
            else:
                # Second batch succeeds
                return {sym: SymbolReferenceData(symbol=sym) for sym in batch}

        with patch.object(client, "_fetch_batch", side_effect=mock_fetch_batch):
            result = await client.fetch_reference_data(symbols)

        # Should have results from second batch only
        assert len(result) == 2
        assert "NVDA" in result
        assert "GOOGL" in result
        assert "AAPL" not in result
        assert "MSFT" not in result

    async def test_fetch_reference_data_all_fail(self) -> None:
        """Test that all batches failing returns empty dict without exception."""
        config = FMPReferenceConfig(batch_size=2, max_retries=1)
        client = FMPReferenceClient(config)
        client._api_key = "test_key"

        symbols = ["AAPL", "MSFT", "NVDA", "GOOGL"]

        async def mock_fetch_batch(session, batch):
            raise aiohttp.ClientError("API Error")

        with patch.object(client, "_fetch_batch", side_effect=mock_fetch_batch):
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
