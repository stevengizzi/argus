"""Tests for AI Insight session elapsed time calculation.

Verifies that _assemble_insight_data computes session_status,
session_elapsed_minutes, and minutes_until_open based on 9:30 ET reference.
"""

from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from argus.ai.summary import DailySummaryGenerator

_ET = ZoneInfo("America/New_York")


def _make_app_state() -> MagicMock:
    """Create a minimal mock AppState."""
    state = MagicMock()
    state.order_manager = None
    state.trade_logger = None
    state.orchestrator = None
    state.risk_manager = None
    state.data_service = None
    return state


@pytest.mark.asyncio
async def test_session_status_pre_market() -> None:
    """Before 9:30 ET should be pre_market with minutes_until_open set."""
    generator = DailySummaryGenerator(client=None)
    state = _make_app_state()

    # 8:00 ET → 90 minutes until open
    fake_now = datetime(2026, 3, 16, 8, 0, tzinfo=_ET)
    with patch("argus.ai.summary.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        data = await generator._assemble_insight_data(state)

    assert data["session_status"] == "pre_market"
    assert data["session_elapsed_minutes"] is None
    assert data["minutes_until_open"] == 90
    assert data["market_open"] is False


@pytest.mark.asyncio
async def test_session_status_open() -> None:
    """At 10:00 ET should be open with 30 minutes elapsed."""
    generator = DailySummaryGenerator(client=None)
    state = _make_app_state()

    # 10:00 ET → 30 minutes after 9:30
    fake_now = datetime(2026, 3, 16, 10, 0, tzinfo=_ET)
    with patch("argus.ai.summary.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        data = await generator._assemble_insight_data(state)

    assert data["session_status"] == "open"
    assert data["session_elapsed_minutes"] == 30
    assert data["minutes_until_open"] is None
    assert data["market_open"] is True


@pytest.mark.asyncio
async def test_session_status_closed() -> None:
    """At 17:00 ET should be closed with both fields None."""
    generator = DailySummaryGenerator(client=None)
    state = _make_app_state()

    # 17:00 ET → after close
    fake_now = datetime(2026, 3, 16, 17, 0, tzinfo=_ET)
    with patch("argus.ai.summary.datetime") as mock_dt:
        mock_dt.now.return_value = fake_now
        mock_dt.side_effect = lambda *args, **kw: datetime(*args, **kw)

        data = await generator._assemble_insight_data(state)

    assert data["session_status"] == "closed"
    assert data["session_elapsed_minutes"] is None
    assert data["minutes_until_open"] is None
    assert data["market_open"] is False
