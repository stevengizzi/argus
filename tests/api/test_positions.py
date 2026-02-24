"""Tests for positions API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient


class TestPositionsEndpoint:
    """Tests for GET /api/v1/positions endpoint."""

    @pytest.mark.asyncio
    async def test_positions_empty(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """No managed positions returns empty list."""
        response = await client.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["positions"] == []
        assert data["count"] == 0
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_positions_with_data(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns positions with correct shape and fields."""
        response = await client_with_positions.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["positions"]) == 3

        # Check required fields exist in each position
        for pos in data["positions"]:
            assert "position_id" in pos
            assert "strategy_id" in pos
            assert "symbol" in pos
            assert "side" in pos
            assert "entry_price" in pos
            assert "entry_time" in pos
            assert "shares_total" in pos
            assert "shares_remaining" in pos
            assert "current_price" in pos
            assert "unrealized_pnl" in pos
            assert "unrealized_pnl_pct" in pos
            assert "stop_price" in pos
            assert "t1_price" in pos
            assert "t2_price" in pos
            assert "t1_filled" in pos
            assert "hold_duration_seconds" in pos
            assert "r_multiple_current" in pos

    @pytest.mark.asyncio
    async def test_positions_filter_by_strategy(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Filter positions by strategy_id parameter."""
        response = await client_with_positions.get(
            "/api/v1/positions?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        # AAPL and NVDA are orb_breakout, TSLA is orb_scalp
        assert data["count"] == 2
        for pos in data["positions"]:
            assert pos["strategy_id"] == "orb_breakout"

    @pytest.mark.asyncio
    async def test_positions_computed_unrealized_pnl(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Unrealized P&L computed correctly (using entry price as current)."""
        response = await client_with_positions.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Find AAPL position (entry=185, shares_remaining=50)
        aapl_pos = next(p for p in data["positions"] if p["symbol"] == "AAPL")
        # Without data_service, current_price = entry_price, so unrealized_pnl = 0
        assert aapl_pos["current_price"] == 185.00
        assert aapl_pos["unrealized_pnl"] == 0.0
        assert aapl_pos["unrealized_pnl_pct"] == 0.0

    @pytest.mark.asyncio
    async def test_positions_computed_r_multiple(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """R-multiple computed correctly from entry, stop, and current price."""
        response = await client_with_positions.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Find NVDA position (entry=750, original_stop=740)
        nvda_pos = next(p for p in data["positions"] if p["symbol"] == "NVDA")
        # risk_per_share = 750 - 740 = 10
        # current_price = entry_price (no data_service)
        # r_multiple = (750 - 750) / 10 = 0.0
        assert nvda_pos["r_multiple_current"] == 0.0

    @pytest.mark.asyncio
    async def test_positions_hold_duration(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Hold duration in seconds computed correctly."""
        response = await client_with_positions.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # Find AAPL position (entry_time = now - 45 minutes)
        aapl_pos = next(p for p in data["positions"] if p["symbol"] == "AAPL")
        expected_seconds = 45 * 60  # 2700 seconds
        # Allow small tolerance for execution time
        assert abs(aapl_pos["hold_duration_seconds"] - expected_seconds) < 5

        # Find TSLA position (entry_time = now - 15 minutes)
        tsla_pos = next(p for p in data["positions"] if p["symbol"] == "TSLA")
        expected_seconds = 15 * 60  # 900 seconds
        assert abs(tsla_pos["hold_duration_seconds"] - expected_seconds) < 5

    @pytest.mark.asyncio
    async def test_positions_data_service_none(
        self,
        client_with_positions: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Handles missing data service gracefully (uses entry_price as fallback)."""
        response = await client_with_positions.get("/api/v1/positions", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        # All positions should use entry_price as current_price
        for pos in data["positions"]:
            assert pos["current_price"] == pos["entry_price"]

    @pytest.mark.asyncio
    async def test_positions_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Returns 401 without valid auth."""
        response = await client.get("/api/v1/positions")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_positions_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Returns 401 with invalid token."""
        response = await client.get(
            "/api/v1/positions",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401
