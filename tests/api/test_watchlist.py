"""Tests for watchlist API endpoint."""

from __future__ import annotations

import pytest
from httpx import AsyncClient

from argus.api.routes.watchlist import SparklinePoint, VwapState, WatchlistItem


class TestWatchlistEndpoint:
    """Tests for GET /api/v1/watchlist endpoint."""

    @pytest.mark.asyncio
    async def test_watchlist_empty_without_mock_data(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Empty watchlist returns empty list when no mock data is injected."""
        response = await client.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["symbols"] == []
        assert data["count"] == 0
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_watchlist_with_mock_data(
        self,
        client_with_watchlist: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Returns watchlist items with correct shape and fields."""
        response = await client_with_watchlist.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert len(data["symbols"]) == 3

        # Check required fields exist in each item
        for item in data["symbols"]:
            assert "symbol" in item
            assert "current_price" in item
            assert "gap_pct" in item
            assert "strategies" in item
            assert "vwap_state" in item
            assert "sparkline" in item

            # Verify strategies is a list
            assert isinstance(item["strategies"], list)

            # Verify sparkline has points
            assert isinstance(item["sparkline"], list)
            if item["sparkline"]:
                point = item["sparkline"][0]
                assert "timestamp" in point
                assert "price" in point

    @pytest.mark.asyncio
    async def test_watchlist_vwap_states(
        self,
        client_with_watchlist: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Watchlist items have valid VWAP states."""
        response = await client_with_watchlist.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        valid_states = {"watching", "above_vwap", "below_vwap", "entered"}
        for item in data["symbols"]:
            assert item["vwap_state"] in valid_states

    @pytest.mark.asyncio
    async def test_watchlist_strategies_format(
        self,
        client_with_watchlist: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Strategies field contains valid strategy identifiers."""
        response = await client_with_watchlist.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        valid_strategies = {"orb", "scalp", "vwap_reclaim"}
        for item in data["symbols"]:
            for strategy in item["strategies"]:
                assert strategy in valid_strategies

    @pytest.mark.asyncio
    async def test_watchlist_sparkline_format(
        self,
        client_with_watchlist: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Sparkline data has correct format."""
        response = await client_with_watchlist.get("/api/v1/watchlist", headers=auth_headers)

        assert response.status_code == 200
        data = response.json()

        for item in data["symbols"]:
            sparkline = item["sparkline"]
            assert len(sparkline) == 30  # Expected 30 data points

            for point in sparkline:
                # Verify timestamp is ISO format
                assert isinstance(point["timestamp"], str)
                assert "T" in point["timestamp"]  # ISO format includes T

                # Verify price is numeric
                assert isinstance(point["price"], (int, float))
                assert point["price"] > 0

    @pytest.mark.asyncio
    async def test_watchlist_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Returns 401 without valid auth."""
        response = await client.get("/api/v1/watchlist")

        assert response.status_code == 401
        assert "detail" in response.json()

    @pytest.mark.asyncio
    async def test_watchlist_invalid_token(
        self,
        client: AsyncClient,
    ) -> None:
        """Returns 401 with invalid token."""
        response = await client.get(
            "/api/v1/watchlist",
            headers={"Authorization": "Bearer invalid_token"},
        )

        assert response.status_code == 401


# Fixture for client with mock watchlist data
@pytest.fixture
async def app_state_with_watchlist(app_state):
    """Provide AppState with mock watchlist data injected."""
    from datetime import UTC, datetime, timedelta

    now = datetime.now(UTC)

    # Create mock sparkline data
    def create_sparkline(base_price: float) -> list[SparklinePoint]:
        return [
            SparklinePoint(
                timestamp=(now - timedelta(minutes=30 - i)).isoformat(),
                price=round(base_price + (i * 0.01 * base_price * 0.01), 2),
            )
            for i in range(30)
        ]

    mock_watchlist = [
        WatchlistItem(
            symbol="NVDA",
            current_price=875.50,
            gap_pct=3.2,
            strategies=["orb", "scalp", "vwap_reclaim"],
            vwap_state=VwapState.ABOVE_VWAP,
            sparkline=create_sparkline(875.50),
        ),
        WatchlistItem(
            symbol="TSLA",
            current_price=225.80,
            gap_pct=2.8,
            strategies=["orb", "scalp"],
            vwap_state=VwapState.WATCHING,
            sparkline=create_sparkline(225.80),
        ),
        WatchlistItem(
            symbol="PLTR",
            current_price=32.50,
            gap_pct=5.5,
            strategies=["vwap_reclaim"],
            vwap_state=VwapState.ENTERED,
            sparkline=create_sparkline(32.50),
        ),
    ]

    app_state._mock_watchlist = mock_watchlist
    return app_state


@pytest.fixture
async def client_with_watchlist(
    app_state_with_watchlist,
    jwt_secret: str,
):
    """Provide client with AppState containing mock watchlist."""
    from collections.abc import AsyncGenerator

    from httpx import ASGITransport, AsyncClient

    from argus.api.server import create_app

    app = create_app(app_state_with_watchlist)
    app.state.app_state = app_state_with_watchlist
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client
