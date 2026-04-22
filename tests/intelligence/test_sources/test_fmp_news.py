"""Tests for FMPNewsClient.

Sprint 23.5 Session 2: Data Source Clients.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.config import FMPNewsConfig
from argus.intelligence.sources.fmp_news import FMPNewsClient

_ET = ZoneInfo("America/New_York")


def _make_news_item(
    symbol: str,
    title: str,
    published_date: str = "2024-03-01 09:00:00",
    url: str = "https://example.com/news",
) -> dict[str, Any]:
    """Create a single FMP news item."""
    return {
        "symbol": symbol,
        "title": title,
        "publishedDate": published_date,
        "url": url,
        "site": "Example News",
        "text": "Sample news text content.",
    }


def _make_press_release_item(
    title: str,
    date: str = "2024-03-01",
    text: str = "Press release content.",
) -> dict[str, Any]:
    """Create a single FMP press release item."""
    return {
        "title": title,
        "date": date,
        "text": text,
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


class TestFMPNewsClient:
    """Tests for FMPNewsClient."""

    @pytest.fixture
    def config(self) -> FMPNewsConfig:
        """Default config for tests."""
        return FMPNewsConfig(
            api_key_env_var="FMP_API_KEY",
            endpoints=["stock_news", "press_releases"],
        )

    @pytest.fixture
    def client(self, config: FMPNewsConfig) -> FMPNewsClient:
        """Client instance for tests."""
        return FMPNewsClient(config)

    @pytest.mark.asyncio
    async def test_stock_news_parses_multi_ticker_response(
        self, client: FMPNewsClient
    ) -> None:
        """Test parsing of stock news response with multiple tickers."""
        news_items = [
            _make_news_item("AAPL", "Apple announces new product"),
            _make_news_item("MSFT", "Microsoft reports earnings beat"),
            _make_news_item("AAPL", "Apple stock rises on news"),
        ]

        mock_response = _create_mock_response(200, news_items)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        # Close the real session and replace with mock
        if client._session:
            await client._session.close()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_stock_news(["AAPL", "MSFT"], fetch_time)

        assert len(result) == 3
        assert result[0].symbol == "AAPL"
        assert result[0].headline == "Apple announces new product"
        assert result[0].source == "fmp_news"
        assert result[1].symbol == "MSFT"

        await client.stop()

    @pytest.mark.asyncio
    async def test_press_releases_parses_single_symbol_response(
        self, client: FMPNewsClient
    ) -> None:
        """Test parsing of press releases for a single symbol."""
        releases = [
            _make_press_release_item("Q1 2024 Results"),
            _make_press_release_item("Strategic Partnership Announced"),
        ]

        mock_response = _create_mock_response(200, releases)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        fetch_time = datetime.now(_ET)
        result = await client._fetch_press_releases("AAPL", fetch_time)

        assert len(result) == 2
        assert result[0].headline == "Q1 2024 Results"
        assert result[0].source == "fmp_press_release"
        assert result[0].symbol == "AAPL"

        await client.stop()

    @pytest.mark.asyncio
    async def test_batch_tickers_correctly_batched_in_groups_of_5(
        self, client: FMPNewsClient
    ) -> None:
        """Test that tickers are batched in groups of 5 for stock_news calls."""
        request_tickers: list[str] = []

        mock_response = _create_mock_response(200, [])

        def mock_get(url: str, params: dict[str, Any]) -> _MockContextManager:
            if "stock_news" in url:
                tickers = params.get("tickers", "")
                request_tickers.append(tickers)
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        # Provide 12 symbols - should result in 3 batches (5, 5, 2)
        symbols = [f"SYM{i}" for i in range(12)]
        fetch_time = datetime.now(_ET)
        await client._fetch_stock_news(symbols, fetch_time)

        assert len(request_tickers) == 3  # 3 batches
        # First batch should have 5 tickers
        assert len(request_tickers[0].split(",")) == 5
        # Second batch should have 5 tickers
        assert len(request_tickers[1].split(",")) == 5
        # Third batch should have 2 tickers
        assert len(request_tickers[2].split(",")) == 2

        await client.stop()

    @pytest.mark.asyncio
    async def test_dedup_filters_duplicate_headlines(
        self, client: FMPNewsClient
    ) -> None:
        """Test that duplicate headlines are filtered out."""
        # Same headline appears twice (simulating duplicate from different sources)
        news_items = [
            _make_news_item("AAPL", "Apple announces breakthrough"),
            _make_news_item("AAPL", "apple announces breakthrough"),  # Same, different case
        ]

        mock_response = _create_mock_response(200, news_items)
        mock_session = _create_mock_session(mock_response)

        # Disable press releases to isolate stock_news behavior
        config = FMPNewsConfig(
            api_key_env_var="FMP_API_KEY",
            endpoints=["stock_news"],
        )
        client = FMPNewsClient(config)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        result = await client.fetch_catalysts(["AAPL"])

        # Should only have 1 item (duplicate filtered)
        assert len(result) == 1
        assert result[0].headline == "Apple announces breakthrough"

        await client.stop()

    @pytest.mark.asyncio
    async def test_missing_api_key_returns_empty_list_with_warning(
        self, client: FMPNewsClient
    ) -> None:
        """Test that missing API key returns empty list."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure no FMP_API_KEY
            import os
            if "FMP_API_KEY" in os.environ:
                del os.environ["FMP_API_KEY"]

            await client.start()

        result = await client.fetch_catalysts(["AAPL"])

        assert result == []

        await client.stop()

    @pytest.mark.asyncio
    async def test_error_handling_429_triggers_backoff(
        self, client: FMPNewsClient
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

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        result = await client._make_request("https://test.url", {}, max_retries=3)

        assert result is None
        assert attempt_count == 3  # Should retry 3 times

        await client.stop()

    @pytest.mark.asyncio
    async def test_error_handling_401_disables_for_cycle(
        self, client: FMPNewsClient
    ) -> None:
        """Test that HTTP 401 disables client for the cycle."""
        mock_response = _create_mock_response(401, None)
        mock_session = _create_mock_session(mock_response)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        # First call triggers 401
        await client._make_request("https://test.url", {})

        # Client should be disabled
        assert client._disabled_for_cycle is True

        # Subsequent fetch should return empty immediately
        result = await client.fetch_catalysts(["AAPL"])
        assert result == []

        await client.stop()

    @pytest.mark.asyncio
    async def test_source_name_returns_fmp_news(
        self, client: FMPNewsClient
    ) -> None:
        """Test that source_name property returns correct identifier."""
        assert client.source_name == "fmp_news"

    @pytest.mark.asyncio
    async def test_session_timeout_includes_sock_connect_and_sock_read(
        self, config: FMPNewsConfig
    ) -> None:
        """Session is created with sock_connect=10 and sock_read=20 timeouts."""
        client = FMPNewsClient(config)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        assert client._session is not None
        timeout = client._session.timeout
        assert timeout.sock_connect == 10.0
        assert timeout.sock_read == 20.0
        assert timeout.total == 30.0

        await client.stop()

    @pytest.mark.asyncio
    async def test_circuit_breaker_403_skips_remaining_symbols(
        self, config: FMPNewsConfig
    ) -> None:
        """First 403 sets circuit breaker, remaining symbols are skipped."""
        # Use press_releases endpoint to test per-symbol circuit breaking
        config = FMPNewsConfig(
            api_key_env_var="FMP_API_KEY",
            endpoints=["press_releases"],
        )
        client = FMPNewsClient(config)

        request_urls: list[str] = []

        def mock_get(url: str, params: Any = None) -> _MockContextManager:
            request_urls.append(url)
            # Always return 403
            return _MockContextManager(_create_mock_response(403, None))

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        result = await client.fetch_catalysts(["AAPL", "MSFT", "TSLA"])

        # Only the first symbol should have made a request (403 trips breaker)
        assert len(request_urls) == 1
        assert result == []
        assert client._disabled_for_cycle is True

        await client.stop()

    @pytest.mark.asyncio
    async def test_circuit_breaker_sticky_across_cycles(
        self, config: FMPNewsConfig
    ) -> None:
        """FIX-06 audit 2026-04-21 (P1-D1-M04): the circuit breaker is sticky
        across poll cycles for the auth-backoff window. After a 401/403, the
        next ``fetch_catalysts`` call short-circuits without hitting the API
        and without re-logging the error. ``reset_disabled_flag()`` forces an
        immediate retry.
        """
        config = FMPNewsConfig(
            api_key_env_var="FMP_API_KEY",
            endpoints=["press_releases"],
        )
        client = FMPNewsClient(config)

        call_count = 0

        def mock_get(url: str, params: Any = None) -> _MockContextManager:
            nonlocal call_count
            call_count += 1
            if call_count <= 1:
                # First cycle: 403
                return _MockContextManager(_create_mock_response(403, None))
            # Second cycle (only reached after reset): 200 with empty list
            return _MockContextManager(_create_mock_response(200, []))

        mock_session = MagicMock()
        mock_session.get = mock_get
        mock_session.close = AsyncMock()

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        if client._session:
            await client._session.close()
        client._session = mock_session

        # Cycle 1: triggers 403 → auth-backoff armed.
        result1 = await client.fetch_catalysts(["AAPL"])
        assert result1 == []
        assert client._disabled_for_cycle is True
        assert client._auth_disabled_until is not None

        # Cycle 2: backoff still active → no API call, returns empty.
        result2 = await client.fetch_catalysts(["AAPL"])
        assert result2 == []
        assert call_count == 1, (
            "sticky circuit breaker must skip the API call while backoff active"
        )

        # Operator resets → next cycle retries.
        client.reset_disabled_flag()
        assert client._auth_disabled_until is None
        result3 = await client.fetch_catalysts(["AAPL"])
        assert result3 == []
        assert call_count == 2, "reset must allow the retry to hit the API"

        await client.stop()

    @pytest.mark.asyncio
    async def test_firehose_mode_logs_once_and_returns_empty(
        self, config: FMPNewsConfig
    ) -> None:
        """FIX-06 audit 2026-04-21 (P1-D1-M05): FMP has no firehose endpoint,
        so ``firehose=True`` returns empty. Log fires ONCE per session — not
        per poll — so the operator sees the explanation but not log spam."""
        import logging

        client = FMPNewsClient(config)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        with self._caplog_at_info() as records:
            r1 = await client.fetch_catalysts(["AAPL"], firehose=True)
            r2 = await client.fetch_catalysts(["AAPL"], firehose=True)

        assert r1 == []
        assert r2 == []
        # Exactly one explanatory log line, not two.
        firehose_logs = [
            rec for rec in records
            if "firehose mode" in rec.getMessage().lower()
        ]
        assert len(firehose_logs) == 1

        await client.stop()

    def _caplog_at_info(self):
        import logging
        from contextlib import contextmanager

        @contextmanager
        def _ctx():
            logger_ = logging.getLogger("argus.intelligence.sources.fmp_news")
            captured: list[logging.LogRecord] = []

            class _Handler(logging.Handler):
                def emit(self, record: logging.LogRecord) -> None:
                    captured.append(record)

            handler = _Handler(level=logging.INFO)
            prev_level = logger_.level
            logger_.addHandler(handler)
            logger_.setLevel(logging.INFO)
            try:
                yield captured
            finally:
                logger_.removeHandler(handler)
                logger_.setLevel(prev_level)

        return _ctx()

    @pytest.mark.asyncio
    async def test_fetch_catalysts_empty_symbols_returns_empty(
        self, client: FMPNewsClient
    ) -> None:
        """Test that fetch_catalysts with empty symbols returns empty list."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await client.start()

        result = await client.fetch_catalysts([])
        assert result == []

        await client.stop()
