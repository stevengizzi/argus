"""Tests for trade replay and goals config endpoints.

Tests:
- GET /api/v1/trades/{trade_id}/replay
- GET /api/v1/config/goals
"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestTradeReplayEndpoint:
    """Tests for GET /api/v1/trades/{trade_id}/replay."""

    async def test_valid_trade_returns_replay_data(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Valid trade ID returns trade data with bars and indices."""
        # First get a trade ID from the seeded data
        response = await client_with_trades.get(
            "/api/v1/trades?limit=1",
            headers=auth_headers,
        )
        assert response.status_code == 200
        trade_id = response.json()["trades"][0]["id"]

        # Now fetch the replay
        response = await client_with_trades.get(
            f"/api/v1/trades/{trade_id}/replay",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Check response structure
        assert "trade" in data
        assert "bars" in data
        assert "entry_bar_index" in data
        assert "exit_bar_index" in data
        assert "vwap" in data
        assert "timestamp" in data

        # Trade should match the requested ID
        assert data["trade"]["id"] == trade_id

        # In test mode (not dev mode), bars may be empty
        # But the structure should be correct
        assert isinstance(data["bars"], list)
        assert isinstance(data["entry_bar_index"], int)

    async def test_nonexistent_trade_returns_404(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Nonexistent trade ID returns 404."""
        response = await client_with_trades.get(
            "/api/v1/trades/nonexistent_trade_id/replay",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    async def test_unauthenticated_returns_401(
        self,
        client_with_trades: AsyncClient,
    ) -> None:
        """Request without auth returns 401."""
        response = await client_with_trades.get(
            "/api/v1/trades/some_trade_id/replay"
        )

        assert response.status_code == 401
        assert "detail" in response.json()


class TestGoalsConfigEndpoint:
    """Tests for GET /api/v1/config/goals."""

    async def test_returns_default_monthly_target(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns default monthly target of 5000.0."""
        response = await client.get(
            "/api/v1/config/goals",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert "monthly_target_usd" in data
        assert "timestamp" in data
        assert data["monthly_target_usd"] == 5000.0

    async def test_unauthenticated_returns_401(
        self,
        client: AsyncClient,
    ) -> None:
        """Request without auth returns 401."""
        response = await client.get("/api/v1/config/goals")

        assert response.status_code == 401
        assert "detail" in response.json()
