"""Tests for GET /api/v1/market/status endpoint."""

from __future__ import annotations

import datetime
from unittest.mock import patch

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestMarketStatusEndpoint:
    """Tests for GET /api/v1/market/status."""

    async def test_returns_holiday_info_on_good_friday(
        self, client: AsyncClient
    ) -> None:
        """GET /market/status returns is_holiday=True on Good Friday."""
        with patch(
            "argus.api.routes.market.is_market_holiday",
            return_value=(True, "Good Friday"),
        ), patch(
            "argus.api.routes.market.get_next_trading_day",
            return_value=datetime.date(2026, 4, 6),
        ):
            response = await client.get("/api/v1/market/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_holiday"] is True
        assert data["holiday_name"] == "Good Friday"
        assert data["next_trading_day"] == "2026-04-06"

    async def test_returns_not_holiday_on_normal_day(
        self, client: AsyncClient
    ) -> None:
        """GET /market/status returns is_holiday=False on a regular trading day."""
        with patch(
            "argus.api.routes.market.is_market_holiday",
            return_value=(False, None),
        ), patch(
            "argus.api.routes.market.get_next_trading_day",
            return_value=datetime.date(2026, 4, 7),
        ):
            response = await client.get("/api/v1/market/status")

        assert response.status_code == 200
        data = response.json()
        assert data["is_holiday"] is False
        assert data["holiday_name"] is None

    async def test_no_auth_required(self, client: AsyncClient) -> None:
        """GET /market/status is accessible without an Authorization header."""
        with patch(
            "argus.api.routes.market.is_market_holiday",
            return_value=(False, None),
        ), patch(
            "argus.api.routes.market.get_next_trading_day",
            return_value=datetime.date(2026, 4, 7),
        ):
            response = await client.get("/api/v1/market/status")

        # No auth header used — must still return 200
        assert response.status_code == 200

    async def test_holiday_status_sets_is_market_hours_false(
        self, client: AsyncClient
    ) -> None:
        """On a holiday, is_market_hours is always False in the response."""
        with patch(
            "argus.api.routes.market.is_market_holiday",
            return_value=(True, "Good Friday"),
        ), patch(
            "argus.api.routes.market.get_next_trading_day",
            return_value=datetime.date(2026, 4, 6),
        ):
            response = await client.get("/api/v1/market/status")

        data = response.json()
        assert "is_market_hours" in data
        assert data["is_market_hours"] is False

    async def test_response_shape(self, client: AsyncClient) -> None:
        """Response contains all expected fields with correct types."""
        with patch(
            "argus.api.routes.market.is_market_holiday",
            return_value=(False, None),
        ), patch(
            "argus.api.routes.market.get_next_trading_day",
            return_value=datetime.date(2026, 4, 7),
        ):
            response = await client.get("/api/v1/market/status")

        data = response.json()
        assert "is_holiday" in data
        assert "holiday_name" in data
        assert "is_market_hours" in data
        assert "next_trading_day" in data
        assert isinstance(data["is_holiday"], bool)
        assert isinstance(data["is_market_hours"], bool)
