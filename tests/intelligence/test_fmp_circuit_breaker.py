"""Tests for FMP News circuit breaker behavior (DEC-323).

Verifies that FMP circuit breaker trips on first 403 and skips remaining
symbols for the cycle, then resets on the next cycle.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from argus.intelligence.config import FMPNewsConfig
from argus.intelligence.sources.fmp_news import FMPNewsClient


def _make_client() -> FMPNewsClient:
    """Create an FMPNewsClient with mock session."""
    config = FMPNewsConfig()
    client = FMPNewsClient(config)
    client._api_key = "test-key"
    client._session = MagicMock()
    client._disabled_for_cycle = False
    return client


def _mock_403_response() -> AsyncMock:
    """Create a mock HTTP 403 response."""
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)
    return mock_response


@pytest.mark.asyncio
async def test_first_403_trips_breaker() -> None:
    """A 403 on the first request should set _disabled_for_cycle to True."""
    client = _make_client()
    mock_response = _mock_403_response()
    client._session.get = MagicMock(return_value=mock_response)

    result = await client._make_request(
        "https://financialmodelingprep.com/api/v3/stock_news",
        {"tickers": "AAPL", "apikey": "test"},
    )

    assert result is None
    assert client._disabled_for_cycle is True


@pytest.mark.asyncio
async def test_remaining_symbols_skipped() -> None:
    """After first 403, remaining symbols should not make HTTP requests."""
    client = _make_client()
    # Configure endpoints for press_releases only (per-symbol, easier to count)
    client._config = FMPNewsConfig(endpoints=["press_releases"])

    mock_response = _mock_403_response()
    call_count = 0

    def track_calls(*args: object, **kwargs: object) -> AsyncMock:
        nonlocal call_count
        call_count += 1
        return mock_response

    client._session.get = MagicMock(side_effect=track_calls)

    symbols = ["AAPL", "MSFT", "NVDA", "TSLA", "AMZN"]
    await client.fetch_catalysts(symbols)

    # Only 1 HTTP request should have been made (first symbol trips breaker)
    assert call_count == 1
    assert client._disabled_for_cycle is True


@pytest.mark.asyncio
async def test_cycle_reset_clears_breaker() -> None:
    """Calling fetch_catalysts again should reset the breaker."""
    client = _make_client()

    # Simulate tripped state from previous cycle
    client._disabled_for_cycle = True

    # Mock 200 response for the new cycle
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value=[])
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    client._session.get = MagicMock(return_value=mock_response)
    client._config = FMPNewsConfig(endpoints=["press_releases"])

    # fetch_catalysts resets _disabled_for_cycle at the start
    await client.fetch_catalysts(["AAPL"])

    assert client._disabled_for_cycle is False


def test_system_live_yaml_fmp_news_disabled() -> None:
    """Verify config/system_live.yaml has fmp_news.enabled: false."""
    with open("config/system_live.yaml") as f:
        config = yaml.safe_load(f)

    fmp_news_config = config.get("catalyst", {}).get("sources", {}).get("fmp_news", {})
    assert fmp_news_config.get("enabled") is False
