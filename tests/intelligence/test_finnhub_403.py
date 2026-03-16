"""Tests for Finnhub 403 log downgrade and per-cycle summary.

Verifies that 403 responses are logged at WARNING (not ERROR) and that
the cycle summary INFO log fires when 403s occur.
"""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.intelligence.config import FinnhubConfig
from argus.intelligence.sources.finnhub import FinnhubClient


def _make_client() -> FinnhubClient:
    """Create a FinnhubClient with defaults and mock session."""
    config = FinnhubConfig()
    client = FinnhubClient(config)
    client._api_key = "test-key"
    client._session = MagicMock()
    client._disabled_for_cycle = False
    return client


@pytest.mark.asyncio
async def test_403_logged_as_warning(caplog: pytest.LogCaptureFixture) -> None:
    """A 403 response should be logged at WARNING, not ERROR."""
    client = _make_client()

    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    client._session.get = MagicMock(return_value=mock_response)

    with caplog.at_level(logging.WARNING, logger="argus.intelligence.sources.finnhub"):
        result = await client._make_rate_limited_request(
            "https://finnhub.io/api/v1/company-news", {"token": "test"}
        )

    assert result is None
    assert client._disabled_for_cycle is True

    # Verify WARNING level, not ERROR
    warning_records = [
        r for r in caplog.records
        if r.levelno == logging.WARNING and "403" in r.message
    ]
    assert len(warning_records) >= 1

    error_records = [
        r for r in caplog.records
        if r.levelno == logging.ERROR and "403" in r.message
    ]
    assert len(error_records) == 0


@pytest.mark.asyncio
async def test_cycle_403_summary(caplog: pytest.LogCaptureFixture) -> None:
    """After 403s in a cycle, an INFO summary should be logged."""
    client = _make_client()

    # Mock: first request returns 403, remaining skipped by _disabled_for_cycle
    mock_response = AsyncMock()
    mock_response.status = 403
    mock_response.__aenter__ = AsyncMock(return_value=mock_response)
    mock_response.__aexit__ = AsyncMock(return_value=False)

    client._session.get = MagicMock(return_value=mock_response)

    with caplog.at_level(logging.INFO, logger="argus.intelligence.sources.finnhub"):
        await client.fetch_catalysts(["AAPL", "MSFT"])

    # Check for cycle summary INFO log
    info_records = [
        r for r in caplog.records
        if r.levelno == logging.INFO and "cycle summary" in r.message
    ]
    assert len(info_records) >= 1
    assert "403" in info_records[0].message
