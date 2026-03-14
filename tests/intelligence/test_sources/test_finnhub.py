"""Tests for FinnhubClient.

Sprint 23.5 Session 2: Data Source Clients.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.config import FinnhubConfig
from argus.intelligence.sources.finnhub import FinnhubClient

_ET = ZoneInfo("America/New_York")


def _make_news_item(
    headline: str,
    timestamp: int = 1709280000,  # 2024-03-01 08:00:00 UTC
    category: str = "company news",
    url: str = "https://example.com/news",
) -> dict[str, Any]:
    """Create a single Finnhub news item."""
    return {
        "headline": headline,
        "datetime": timestamp,
        "category": category,
        "url": url,
        "source": "Example News",
        "summary": "News summary text.",
        "id": 12345,
        "related": "AAPL",
    }


def _make_recommendation_item(
    period: str = "2024-03-01",
    strong_buy: int = 10,
    buy: int = 15,
    hold: int = 8,
    sell: int = 2,
    strong_sell: int = 1,
) -> dict[str, Any]:
    """Create a single Finnhub recommendation item."""
    return {
        "period": period,
        "strongBuy": strong_buy,
        "buy": buy,
        "hold": hold,
        "sell": sell,
        "strongSell": strong_sell,
    }


def _create_mock_response(status: int, json_data: Any) -> MagicMock:
    """Create a mock aiohttp response."""
    mock_response = MagicMock()
    mock_response.status = status
    mock_response.json = AsyncMock(return_value=json_data)
    return mock_response


class _MockContextManager:
    """Mock async context manager for aiohttp session.get()."""

    def __init__(self, response: MagicMock) -> None:
        self._response = response

    async def __aenter__(self) -> MagicMock:
        return self._response

    async def __aexit__(self, *args: Any) -> None:
        pass


def _create_mock_session(mock_response: MagicMock) -> MagicMock:
    """Create a mock session with async close."""
    mock_session = MagicMock()
    mock_session.get = MagicMock(return_value=_MockContextManager(mock_response))
    mock_session.close = AsyncMock()
    return mock_session


class TestFinnhubClient:
    """Tests for FinnhubClient."""

    @pytest.fixture
    def config(self) -> FinnhubConfig:
        """Default config for tests."""
        return FinnhubConfig(
            api_key_env_var="FINNHUB_API_KEY",
            rate_limit_per_minute=60,
        )

    @pytest.fixture
    def client(self, config: FinnhubConfig) -> FinnhubClient:
        """Client instance for tests."""
        return FinnhubClient(config)

    @pytest.mark.asyncio
    async def test_company_news_parses_response_correctly(
        self, client: FinnhubClient
    ) -> None:
        """Test parsing of company news response."""
        news_items = [
            _make_news_item("Apple announces new iPhone"),
            _make_news_item("Apple stock rises amid positive outlook"),
        ]

        mock_response = _create_mock_response(200, news_items)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_company_news("AAPL", fetch_time)

        assert len(result) == 2
        assert result[0].headline == "Apple announces new iPhone"
        assert result[0].source == "finnhub"
        assert result[0].symbol == "AAPL"
        assert result[0].metadata["category"] == "company news"

        await client.stop()

    @pytest.mark.asyncio
    async def test_recommendation_trends_parses_and_converts_to_catalyst(
        self, client: FinnhubClient
    ) -> None:
        """Test parsing of recommendation trends into CatalystRawItem."""
        recommendations = [
            _make_recommendation_item(),
        ]

        mock_response = _create_mock_response(200, recommendations)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_recommendations("AAPL", fetch_time)

        assert len(result) == 1
        item = result[0]
        assert item.symbol == "AAPL"
        assert "Analyst recommendations" in item.headline
        assert "10 Strong Buy" in item.headline
        assert "15 Buy" in item.headline
        assert item.metadata["category"] == "analyst_recommendation"
        assert item.metadata["strong_buy"] == 10

        await client.stop()

    @pytest.mark.asyncio
    async def test_rate_limiting_respects_60_per_minute(
        self, client: FinnhubClient
    ) -> None:
        """Test that rate limiter enforces minimum interval between requests."""
        config = FinnhubConfig(
            api_key_env_var="FINNHUB_API_KEY",
            rate_limit_per_minute=60,  # 60 calls/min = 1 call/sec
        )
        client = FinnhubClient(config)

        request_times: list[float] = []

        mock_response = _create_mock_response(200, [])

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            request_times.append(asyncio.get_event_loop().time())
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        # Make multiple rate-limited requests
        for _ in range(3):
            await client._make_rate_limited_request("https://test.url", {})

        # Check intervals (should be >= 1s apart for 60/min)
        if len(request_times) >= 2:
            intervals = [
                request_times[i + 1] - request_times[i]
                for i in range(len(request_times) - 1)
            ]
            for interval in intervals:
                assert interval >= 0.9  # Allow small margin

        await client.stop()

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_empty_list_with_warning(
        self, client: FinnhubClient
    ) -> None:
        """Test that missing API key returns empty list."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure no FINNHUB_API_KEY
            import os
            if "FINNHUB_API_KEY" in os.environ:
                del os.environ["FINNHUB_API_KEY"]

            await client.start()

        result = await client.fetch_catalysts(["AAPL"])

        assert result == []

        await client.stop()

    @pytest.mark.asyncio
    async def test_error_handling_401_disables_for_cycle(
        self, client: FinnhubClient
    ) -> None:
        """Test that HTTP 401 disables client for the cycle."""
        mock_response = _create_mock_response(401, None)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        # First call triggers 401
        await client._make_rate_limited_request("https://test.url", {})

        # Client should be disabled
        assert client._disabled_for_cycle is True

        # Subsequent fetch should return empty immediately
        result = await client.fetch_catalysts(["AAPL"])
        assert result == []

        await client.stop()

    @pytest.mark.asyncio
    async def test_date_range_uses_last_24_hours(
        self, client: FinnhubClient
    ) -> None:
        """Test that company news uses last 24 hours date range."""
        captured_params: dict[str, Any] = {}

        mock_response = _create_mock_response(200, [])

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            if "company-news" in url:
                captured_params.update(params)
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        await client._fetch_company_news("AAPL", fetch_time)

        # Verify 'from' and 'to' params are present and formatted
        assert "from" in captured_params
        assert "to" in captured_params

        # Parse dates to verify they're valid and span ~1 day
        from_date = datetime.strptime(captured_params["from"], "%Y-%m-%d")
        to_date = datetime.strptime(captured_params["to"], "%Y-%m-%d")
        assert (to_date - from_date).days <= 1

        await client.stop()

    @pytest.mark.asyncio
    async def test_source_name_returns_finnhub(
        self, client: FinnhubClient
    ) -> None:
        """Test that source_name property returns correct identifier."""
        assert client.source_name == "finnhub"

    @pytest.mark.asyncio
    async def test_fetch_catalysts_empty_symbols_returns_empty(
        self, client: FinnhubClient
    ) -> None:
        """Test that fetch_catalysts with empty symbols returns empty list."""
        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        result = await client.fetch_catalysts([])
        assert result == []

        await client.stop()

    @pytest.mark.asyncio
    async def test_session_timeout_includes_sock_connect_and_sock_read(
        self, config: FinnhubConfig
    ) -> None:
        """Session is created with sock_connect=10 and sock_read=20 timeouts."""
        import aiohttp

        client = FinnhubClient(config)

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        # Inspect the session's timeout
        assert client._session is not None
        timeout = client._session.timeout
        assert timeout.sock_connect == 10.0
        assert timeout.sock_read == 20.0
        assert timeout.total == 30.0

        await client.stop()

    @pytest.mark.asyncio
    async def test_error_handling_429_triggers_backoff(
        self, client: FinnhubClient
    ) -> None:
        """Test that HTTP 429 triggers exponential backoff."""
        attempt_count = 0

        mock_response = _create_mock_response(429, None)

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            nonlocal attempt_count
            attempt_count += 1
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FINNHUB_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        result = await client._make_rate_limited_request("https://test.url", {}, max_retries=3)

        assert result is None
        assert attempt_count == 3  # Should retry 3 times

        await client.stop()


class TestFinnhubFirehose:
    """Tests for FinnhubClient firehose mode (DEC-327)."""

    @pytest.fixture
    def config(self) -> FinnhubConfig:
        """Default config for tests."""
        return FinnhubConfig(
            api_key_env_var="FINNHUB_API_KEY",
            rate_limit_per_minute=60,
        )

    @pytest.fixture
    def client(self, config: FinnhubConfig) -> FinnhubClient:
        """Client with API key set and mock session."""
        c = FinnhubClient(config)
        c._api_key = "test_key"
        return c

    def _make_session_with_responses(
        self, responses: list[tuple[str, Any]]
    ) -> tuple[MagicMock, list[str]]:
        """Create mock session that tracks URLs called.

        Args:
            responses: List of (url_fragment, json_data) pairs returned
                in order for each call.

        Returns:
            (mock_session, calls_made) where calls_made is appended to.
        """
        calls_made: list[str] = []
        response_iter = iter(responses)

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            calls_made.append(url)
            try:
                _, json_data = next(response_iter)
            except StopIteration:
                json_data = []
            mock_response = _create_mock_response(200, json_data)
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        return mock_session, calls_made

    @pytest.mark.asyncio
    async def test_finnhub_firehose_single_api_call(self, client: FinnhubClient) -> None:
        """firehose=True makes exactly 1 call to /news?category=general."""
        calls_made: list[str] = []

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            calls_made.append(url)
            return _MockContextManager(_create_mock_response(200, []))

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_general_news(fetch_time)

        assert len(calls_made) == 1
        assert "/news" in calls_made[0]
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_finnhub_firehose_symbol_association(
        self, client: FinnhubClient
    ) -> None:
        """Item with related='AAPL,MSFT' produces 2 CatalystRawItems."""
        item = _make_news_item("Market-wide news", category="general")
        item["related"] = "AAPL,MSFT"

        fetch_time = datetime.now(_ET)
        result = client._associate_symbols([item], fetch_time)

        assert len(result) == 2
        symbols = {r.symbol for r in result}
        assert symbols == {"AAPL", "MSFT"}
        assert all(r.headline == "Market-wide news" for r in result)

    @pytest.mark.asyncio
    async def test_finnhub_firehose_no_related_field(
        self, client: FinnhubClient
    ) -> None:
        """Item with no 'related' field is stored with symbol=''."""
        item = _make_news_item("Headline with no ticker")
        item.pop("related", None)

        fetch_time = datetime.now(_ET)
        result = client._associate_symbols([item], fetch_time)

        assert len(result) == 1
        assert result[0].symbol == ""

    @pytest.mark.asyncio
    async def test_finnhub_firehose_empty_related_field(
        self, client: FinnhubClient
    ) -> None:
        """Item with related='' is stored with symbol=''."""
        item = _make_news_item("Headline with empty related")
        item["related"] = ""

        fetch_time = datetime.now(_ET)
        result = client._associate_symbols([item], fetch_time)

        assert len(result) == 1
        assert result[0].symbol == ""

    @pytest.mark.asyncio
    async def test_finnhub_per_symbol_still_works(
        self, client: FinnhubClient
    ) -> None:
        """firehose=False triggers per-symbol company-news calls."""
        news_response = [_make_news_item("Company headline")]
        rec_response: list[dict] = []

        call_urls: list[str] = []

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            call_urls.append(url)
            if "company-news" in url:
                return _MockContextManager(_create_mock_response(200, news_response))
            return _MockContextManager(_create_mock_response(200, rec_response))

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        client._session = mock_session

        result = await client.fetch_catalysts(["AAPL"], firehose=False)

        company_news_calls = [u for u in call_urls if "company-news" in u]
        general_news_calls = [u for u in call_urls if "/news" in u and "company-news" not in u]

        assert len(company_news_calls) == 1
        assert len(general_news_calls) == 0
        assert len(result) == 1
        assert result[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_finnhub_firehose_suppresses_recommendations(
        self, client: FinnhubClient
    ) -> None:
        """In firehose mode, recommendations are suppressed (no per-symbol calls)."""
        call_urls: list[str] = []

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            call_urls.append(url)
            # /news endpoint for general news
            return _MockContextManager(_create_mock_response(200, []))

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()
        client._session = mock_session

        result = await client.fetch_catalysts(["AAPL", "MSFT"], firehose=True)

        rec_calls = [u for u in call_urls if "recommendation" in u]
        assert len(rec_calls) == 0  # No recommendation calls in firehose mode
        assert not any(
            r.metadata.get("category") == "analyst_recommendation" for r in result
        )

    @pytest.mark.asyncio
    async def test_finnhub_firehose_empty_response_returns_empty(
        self, client: FinnhubClient
    ) -> None:
        """firehose mode with empty API response returns []."""
        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=_MockContextManager(_create_mock_response(200, []))
        )
        mock_session.close = AsyncMock()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_general_news(fetch_time)

        assert result == []

    @pytest.mark.asyncio
    async def test_finnhub_firehose_api_error_returns_empty(
        self, client: FinnhubClient
    ) -> None:
        """firehose mode with API error (500) returns []."""
        mock_session = MagicMock()
        mock_session.get = MagicMock(
            return_value=_MockContextManager(_create_mock_response(500, None))
        )
        mock_session.close = AsyncMock()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_general_news(fetch_time)

        assert result == []

    @pytest.mark.asyncio
    async def test_catalyst_source_abc_firehose_param(
        self, client: FinnhubClient
    ) -> None:
        """CatalystSource ABC fetch_catalysts() accepts firehose parameter."""
        from argus.intelligence.sources import CatalystSource
        import inspect

        sig = inspect.signature(CatalystSource.fetch_catalysts)
        assert "firehose" in sig.parameters
        param = sig.parameters["firehose"]
        assert param.default is False
