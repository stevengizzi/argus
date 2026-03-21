"""Tests for control API endpoints and CSV export."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient

from argus.api.dependencies import AppState
from argus.api.server import create_app


class MockStrategy:
    """Mock strategy for testing control endpoints."""

    def __init__(self, strategy_id: str, is_active: bool = True) -> None:
        self.strategy_id = strategy_id
        self._is_active = is_active

    @property
    def is_active(self) -> bool:
        return self._is_active

    @is_active.setter
    def is_active(self, value: bool) -> None:
        self._is_active = value


class TestControlEndpoints:
    """Tests for /api/v1/controls/* endpoints."""

    @pytest.mark.asyncio
    async def test_pause_strategy_success(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Pause strategy sets is_active to False."""
        # Add mock strategy
        mock_strategy = MockStrategy("orb_breakout", is_active=True)
        app_state.strategies["orb_breakout"] = mock_strategy  # type: ignore[assignment]

        app = create_app(app_state)
        app.state.app_state = app_state

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/strategies/orb_breakout/pause",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "paused" in data["message"]
        assert mock_strategy.is_active is False

    @pytest.mark.asyncio
    async def test_pause_strategy_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Pause non-existent strategy returns 404."""
        response = await client.post(
            "/api/v1/controls/strategies/nonexistent/pause",
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_pause_strategy_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Pause without auth returns 401."""
        response = await client.post("/api/v1/controls/strategies/orb_breakout/pause")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_resume_strategy_success(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Resume strategy sets is_active to True."""
        mock_strategy = MockStrategy("orb_breakout", is_active=False)
        app_state.strategies["orb_breakout"] = mock_strategy  # type: ignore[assignment]

        app = create_app(app_state)
        app.state.app_state = app_state

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/strategies/orb_breakout/resume",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "resumed" in data["message"]
        assert mock_strategy.is_active is True

    @pytest.mark.asyncio
    async def test_resume_strategy_not_found(
        self,
        client: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """Resume non-existent strategy returns 404."""
        response = await client.post(
            "/api/v1/controls/strategies/nonexistent/resume",
            headers=auth_headers,
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_close_position_routes_through_order_manager(
        self,
        app_state_with_positions: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Close position routes through OrderManager.close_position."""
        app_state_with_positions.order_manager.close_position = AsyncMock(return_value=True)  # type: ignore[method-assign]

        app = create_app(app_state_with_positions)
        app.state.app_state = app_state_with_positions

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/positions/AAPL/close",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "close" in data["message"].lower()
        app_state_with_positions.order_manager.close_position.assert_called_once_with(
            "AAPL", reason="api_close"
        )

    @pytest.mark.asyncio
    async def test_close_position_not_managed_returns_404(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Close position returns 404 when OrderManager doesn't manage it."""
        app_state.order_manager.close_position = AsyncMock(return_value=False)  # type: ignore[method-assign]

        app = create_app(app_state)
        app.state.app_state = app_state

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/positions/ZZZZ/close",
                headers=auth_headers,
            )

        assert response.status_code == 404
        assert "not managed" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_close_position_does_not_call_broker_flatten_all(
        self,
        app_state_with_positions: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Close position must NOT call broker.flatten_all (that was the bug)."""
        app_state_with_positions.order_manager.close_position = AsyncMock(return_value=True)  # type: ignore[method-assign]
        app_state_with_positions.broker.flatten_all = AsyncMock()  # type: ignore[method-assign]

        app = create_app(app_state_with_positions)
        app.state.app_state = app_state_with_positions

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            await client.post(
                "/api/v1/controls/positions/AAPL/close",
                headers=auth_headers,
            )

        app_state_with_positions.broker.flatten_all.assert_not_called()

    @pytest.mark.asyncio
    async def test_emergency_flatten_success(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Emergency flatten calls order manager emergency_flatten."""
        app_state.order_manager.emergency_flatten = AsyncMock()  # type: ignore[method-assign]

        app = create_app(app_state)
        app.state.app_state = app_state

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/emergency/flatten",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "flatten" in data["message"].lower()
        app_state.order_manager.emergency_flatten.assert_called_once()

    @pytest.mark.asyncio
    async def test_emergency_flatten_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Emergency flatten without auth returns 401."""
        response = await client.post("/api/v1/controls/emergency/flatten")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_emergency_pause_all_success(
        self,
        app_state: AppState,
        jwt_secret: str,
        auth_headers: dict[str, str],
    ) -> None:
        """Emergency pause sets all strategies to inactive."""
        mock_strat1 = MockStrategy("orb_breakout", is_active=True)
        mock_strat2 = MockStrategy("orb_scalp", is_active=True)
        app_state.strategies["orb_breakout"] = mock_strat1  # type: ignore[assignment]
        app_state.strategies["orb_scalp"] = mock_strat2  # type: ignore[assignment]

        app = create_app(app_state)
        app.state.app_state = app_state

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.post(
                "/api/v1/controls/emergency/pause",
                headers=auth_headers,
            )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "2 strategies paused" in data["message"]
        assert mock_strat1.is_active is False
        assert mock_strat2.is_active is False

    @pytest.mark.asyncio
    async def test_emergency_pause_unauthenticated(
        self,
        client: AsyncClient,
    ) -> None:
        """Emergency pause without auth returns 401."""
        response = await client.post("/api/v1/controls/emergency/pause")
        assert response.status_code == 401


class TestCsvExport:
    """Tests for CSV export endpoint."""

    @pytest.mark.asyncio
    async def test_export_csv_success(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """CSV export returns valid CSV with headers."""
        response = await client_with_trades.get(
            "/api/v1/trades/export/csv",
            headers=auth_headers,
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "attachment" in response.headers["content-disposition"]
        assert "argus_trades_" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

        # Parse CSV content
        content = response.text
        lines = content.strip().split("\n")

        # Check header row
        header = lines[0]
        assert "id" in header
        assert "strategy_id" in header
        assert "symbol" in header
        assert "pnl_dollars" in header
        assert "exit_reason" in header

        # Check we have data rows (15 seeded trades)
        assert len(lines) > 1

    @pytest.mark.asyncio
    async def test_export_csv_with_strategy_filter(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """CSV export respects strategy_id filter."""
        response = await client_with_trades.get(
            "/api/v1/trades/export/csv?strategy_id=orb_breakout",
            headers=auth_headers,
        )

        assert response.status_code == 200
        content = response.text
        lines = content.strip().split("\n")

        # Should have header + orb_breakout trades only (9 trades)
        # All data rows should contain orb_breakout
        for line in lines[1:]:  # Skip header
            assert "orb_breakout" in line

    @pytest.mark.asyncio
    async def test_export_csv_with_date_filter(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """CSV export respects date filters."""
        response = await client_with_trades.get(
            "/api/v1/trades/export/csv?date_from=2026-02-22&date_to=2026-02-23",
            headers=auth_headers,
        )

        assert response.status_code == 200
        content = response.text
        lines = content.strip().split("\n")

        # Should only have trades from today and yesterday
        # Header + filtered trades
        assert len(lines) >= 2  # At least header + 1 trade

    @pytest.mark.asyncio
    async def test_export_csv_unauthenticated(
        self,
        client_with_trades: AsyncClient,
    ) -> None:
        """CSV export without auth returns 401."""
        response = await client_with_trades.get("/api/v1/trades/export/csv")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_export_csv_empty_result(
        self,
        client_with_trades: AsyncClient,
        auth_headers: dict[str, str],
    ) -> None:
        """CSV export with no matches returns header only."""
        response = await client_with_trades.get(
            "/api/v1/trades/export/csv?strategy_id=nonexistent",
            headers=auth_headers,
        )

        assert response.status_code == 200
        content = response.text
        lines = content.strip().split("\n")

        # Should just have header row
        assert len(lines) == 1
        assert "id" in lines[0]
