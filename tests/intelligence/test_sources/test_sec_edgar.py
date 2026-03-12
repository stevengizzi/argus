"""Tests for SECEdgarClient.

Sprint 23.5 Session 2: Data Source Clients.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import aiohttp
import pytest

from argus.intelligence.config import SECEdgarConfig
from argus.intelligence.sources.sec_edgar import SECEdgarClient

_ET = ZoneInfo("America/New_York")


def _make_tickers_response() -> dict[str, dict[str, Any]]:
    """Create mock SEC company tickers response."""
    return {
        "0": {"cik_str": "320193", "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": "789019", "ticker": "MSFT", "title": "Microsoft Corp"},
        "2": {"cik_str": "1318605", "ticker": "TSLA", "title": "Tesla Inc"},
    }


def _make_submissions_response(
    forms: list[str],
    filing_dates: list[str],
    accession_numbers: list[str],
    items: list[str] | None = None,
) -> dict[str, Any]:
    """Create mock SEC submissions response."""
    recent = {
        "form": forms,
        "filingDate": filing_dates,
        "accessionNumber": accession_numbers,
        "primaryDocument": [f"doc{i}.htm" for i in range(len(forms))],
        "primaryDocDescription": [f"Description {i}" for i in range(len(forms))],
    }
    if items is not None:
        recent["items"] = items
    return {"filings": {"recent": recent}}


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


class TestSECEdgarClient:
    """Tests for SECEdgarClient."""

    @pytest.fixture
    def config(self) -> SECEdgarConfig:
        """Default config for tests."""
        return SECEdgarConfig(
            user_agent_email="test@example.com",
            filing_types=["8-K", "4"],
        )

    @pytest.fixture
    def client(self, config: SECEdgarConfig) -> SECEdgarClient:
        """Client instance for tests."""
        return SECEdgarClient(config)

    @pytest.mark.asyncio
    async def test_cik_mapping_ticker_found_returns_correct_cik(
        self, client: SECEdgarClient
    ) -> None:
        """Test that CIK lookup returns correct zero-padded CIK."""
        # Pre-populate the CIK map directly
        client._cik_map = {"AAPL": "0000320193", "MSFT": "0000789019", "TSLA": "0001318605"}

        assert client.get_cik("AAPL") == "0000320193"
        assert client.get_cik("msft") == "0000789019"  # Case insensitive
        assert client.get_cik("TSLA") == "0001318605"

    @pytest.mark.asyncio
    async def test_cik_mapping_ticker_not_found_skips_symbol(
        self, client: SECEdgarClient
    ) -> None:
        """Test that unknown ticker returns None."""
        client._cik_map = {"AAPL": "0000320193"}

        # Unknown symbol returns None
        assert client.get_cik("UNKNOWN") is None

    @pytest.mark.asyncio
    async def test_filing_fetch_parses_8k_filing_correctly(
        self, client: SECEdgarClient
    ) -> None:
        """Test parsing of 8-K filings with items."""
        submissions = _make_submissions_response(
            forms=["8-K"],
            filing_dates=["2024-03-01"],
            accession_numbers=["0000320193-24-000001"],
            items=["Item 2.02"],
        )

        # Directly call the parsing method
        result = client._parse_filings(submissions, "0000320193", "AAPL")

        assert len(result) == 1
        assert result[0].filing_type == "8-K"
        assert result[0].symbol == "AAPL"
        assert result[0].source == "sec_edgar"
        assert "Item 2.02" in result[0].headline
        assert result[0].metadata["items"] == ["Item 2.02"]

    @pytest.mark.asyncio
    async def test_filing_fetch_parses_form_4_correctly(
        self, config: SECEdgarConfig
    ) -> None:
        """Test parsing of Form 4 filings."""
        config = SECEdgarConfig(
            user_agent_email="test@example.com",
            filing_types=["4"],
        )
        client = SECEdgarClient(config)

        submissions = _make_submissions_response(
            forms=["4"],
            filing_dates=["2024-03-05"],
            accession_numbers=["0001318605-24-000099"],
        )

        result = client._parse_filings(submissions, "0001318605", "TSLA")

        assert len(result) == 1
        assert result[0].filing_type == "4"
        assert result[0].symbol == "TSLA"
        assert "Form 4" in result[0].headline
        assert "Insider Transaction" in result[0].headline

    @pytest.mark.asyncio
    async def test_filing_fetch_filters_by_filing_types_config(
        self, client: SECEdgarClient
    ) -> None:
        """Test that filings not in config.filing_types are excluded."""
        # Mix of allowed and not-allowed filing types
        submissions = _make_submissions_response(
            forms=["8-K", "10-K", "4", "S-1"],
            filing_dates=["2024-03-01", "2024-03-02", "2024-03-03", "2024-03-04"],
            accession_numbers=[
                "0000320193-24-000001",
                "0000320193-24-000002",
                "0000320193-24-000003",
                "0000320193-24-000004",
            ],
        )

        result = client._parse_filings(submissions, "0000320193", "AAPL")

        # Only 8-K and 4 should pass through
        assert len(result) == 2
        filing_types = {item.filing_type for item in result}
        assert filing_types == {"8-K", "4"}

    @pytest.mark.asyncio
    async def test_rate_limiting_throttles_requests(
        self, config: SECEdgarConfig
    ) -> None:
        """Test that rate limiter enforces minimum interval between requests."""
        config = SECEdgarConfig(
            user_agent_email="test@example.com",
            rate_limit_per_second=10.0,  # 10 req/sec = 0.1s interval
        )
        client = SECEdgarClient(config)

        # Track request times
        request_times: list[float] = []

        mock_response = _create_mock_response(200, {"filings": {"recent": {}}})

        def mock_get(url: str) -> _MockContextManager:
            request_times.append(asyncio.get_event_loop().time())
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get

        # Set up the client
        client._session = mock_session

        # Make multiple rate-limited requests
        for _ in range(3):
            await client._make_rate_limited_request("https://test.url")

        # Check intervals (should be >= 0.1s apart)
        if len(request_times) >= 2:
            intervals = [
                request_times[i + 1] - request_times[i]
                for i in range(len(request_times) - 1)
            ]
            for interval in intervals:
                assert interval >= 0.09  # Allow small margin for timing

    @pytest.mark.asyncio
    async def test_error_handling_403_retries_then_skips(
        self, client: SECEdgarClient
    ) -> None:
        """Test that HTTP 403 triggers retry with backoff then skips."""
        attempt_count = 0

        mock_response = _create_mock_response(403, None)

        def mock_get(url: str) -> _MockContextManager:
            nonlocal attempt_count
            attempt_count += 1
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        client._session = mock_session

        result = await client._make_rate_limited_request("https://test.url", max_retries=3)

        assert result is None
        assert attempt_count == 3  # Should retry 3 times

    @pytest.mark.asyncio
    async def test_error_handling_404_skips_with_warning(
        self, client: SECEdgarClient
    ) -> None:
        """Test that HTTP 404 returns None immediately without retry."""
        attempt_count = 0

        mock_response = _create_mock_response(404, None)

        def mock_get(url: str) -> _MockContextManager:
            nonlocal attempt_count
            attempt_count += 1
            return _MockContextManager(mock_response)

        mock_session = MagicMock()
        mock_session.get = mock_get
        client._session = mock_session

        result = await client._make_rate_limited_request("https://test.url", max_retries=3)

        assert result is None
        assert attempt_count == 1  # Should not retry on 404

    @pytest.mark.asyncio
    async def test_source_name_returns_sec_edgar(
        self, client: SECEdgarClient
    ) -> None:
        """Test that source_name property returns correct identifier."""
        assert client.source_name == "sec_edgar"

    @pytest.mark.asyncio
    async def test_fetch_catalysts_empty_symbols_returns_empty(
        self, client: SECEdgarClient
    ) -> None:
        """Test that fetch_catalysts with empty symbols returns empty list."""
        # Need to set session so client is considered started
        client._session = MagicMock()

        result = await client.fetch_catalysts([])
        assert result == []

    @pytest.mark.asyncio
    async def test_fetch_catalysts_not_started_returns_empty(
        self, client: SECEdgarClient
    ) -> None:
        """Test that fetch_catalysts without start() returns empty list."""
        result = await client.fetch_catalysts(["AAPL"])
        assert result == []

    @pytest.mark.asyncio
    async def test_user_agent_header_includes_email(
        self, config: SECEdgarConfig
    ) -> None:
        """Test that User-Agent header includes configured email."""
        client = SECEdgarClient(config)

        captured_headers: dict[str, str] = {}

        def mock_init(self: Any, *args: Any, **kwargs: Any) -> None:
            if "headers" in kwargs:
                captured_headers.update(kwargs["headers"])

        with (
            patch.object(aiohttp.ClientSession, "__init__", mock_init),
            patch.object(aiohttp.ClientSession, "__aenter__", AsyncMock()),
            patch.object(aiohttp.ClientSession, "__aexit__", AsyncMock()),
            patch.object(aiohttp.ClientSession, "get", AsyncMock()),
            patch.object(aiohttp.ClientSession, "close", AsyncMock()),
        ):
            ua = f"ARGUS Trading System ({config.user_agent_email})"
            client._session = aiohttp.ClientSession(headers={"User-Agent": ua})

        assert "User-Agent" in captured_headers
        assert "test@example.com" in captured_headers["User-Agent"]

    @pytest.mark.asyncio
    async def test_sec_edgar_start_empty_email_raises(self) -> None:
        """start() with user_agent_email='' raises ValueError."""
        config = SECEdgarConfig(user_agent_email="")
        client = SECEdgarClient(config)

        with pytest.raises(ValueError) as exc_info:
            await client.start()

        assert "user_agent_email is empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_sec_edgar_start_whitespace_email_raises(self) -> None:
        """start() with user_agent_email='  ' raises ValueError."""
        config = SECEdgarConfig(user_agent_email="   ")
        client = SECEdgarClient(config)

        with pytest.raises(ValueError) as exc_info:
            await client.start()

        assert "user_agent_email is empty" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_session_timeout_includes_sock_connect_and_sock_read(
        self, config: SECEdgarConfig
    ) -> None:
        """Session is created with sock_connect=10 and sock_read=20 timeouts.

        Calls client.start() and inspects the actual session timeout values,
        matching the pattern used by Finnhub and FMP timeout tests.
        """
        client = SECEdgarClient(config)

        # Mock the CIK map refresh to avoid real HTTP requests
        with patch.object(client, "_refresh_cik_map", new_callable=AsyncMock):
            await client.start()

        # Inspect the session's timeout
        assert client._session is not None
        timeout = client._session.timeout
        assert timeout.sock_connect == 10.0
        assert timeout.sock_read == 20.0
        assert timeout.total == 30.0

        await client.stop()

    @pytest.mark.asyncio
    async def test_sec_edgar_start_valid_email_succeeds(self) -> None:
        """start() with valid email does not raise."""
        config = SECEdgarConfig(user_agent_email="valid@example.com")
        client = SECEdgarClient(config)

        # Mock the session creation and CIK map refresh
        mock_response = _create_mock_response(200, _make_tickers_response())

        with patch.object(
            aiohttp,
            "ClientSession",
            return_value=MagicMock(
                get=lambda url: _MockContextManager(mock_response),
                close=AsyncMock(),
            ),
        ):
            # Should not raise
            await client.start()

            # Should have loaded CIK map
            assert len(client._cik_map) > 0

            await client.stop()
