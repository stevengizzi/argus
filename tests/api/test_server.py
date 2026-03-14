"""Tests for the FastAPI server factory."""

from __future__ import annotations

import pytest
from fastapi import FastAPI

from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQualityEngine


@pytest.mark.asyncio
async def test_app_creation(app_state):
    """create_app returns a FastAPI instance."""
    from argus.api.server import create_app

    app = create_app(app_state)

    assert isinstance(app, FastAPI)
    assert app.title == "Argus Command Center API"


@pytest.mark.asyncio
async def test_cors_headers(client):
    """OPTIONS request returns CORS headers."""
    response = await client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    # CORS preflight should return 200
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


@pytest.mark.asyncio
async def test_routes_under_api_v1(client, auth_headers):
    """Routes are mounted under /api/v1 prefix."""
    # /api/v1/account should exist
    response = await client.get("/api/v1/account", headers=auth_headers)

    # Should return 200 (not 404)
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_openapi_available(client):
    """OpenAPI docs endpoint returns 200."""
    response = await client.get("/docs")

    assert response.status_code == 200


@pytest.mark.asyncio
async def test_static_not_mounted_when_empty(app_state):
    """No static files mounted when static_dir is empty."""
    from argus.api.server import create_app

    # Ensure static_dir is empty
    if app_state.config and app_state.config.api:
        app_state.config.api.static_dir = ""

    app = create_app(app_state)

    # Check that no static files route is mounted
    # The root path should return 404 or redirect, not serve static
    from httpx import ASGITransport, AsyncClient

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as test_client:
        response = await test_client.get("/")
        # Root should be 404 (no static mount) or 307 redirect
        assert response.status_code in (404, 307)


class TestPortAvailabilityGuard:
    """Tests for port-availability guard in run_server (Sprint 23.7 S2)."""

    def test_check_port_available_when_free(self) -> None:
        """Test check_port_available returns True when port is free."""
        from argus.api.server import check_port_available

        # Use a high port that's likely to be free
        result = check_port_available("127.0.0.1", 59999)

        assert result is True

    def test_check_port_available_when_occupied(self) -> None:
        """Test check_port_available returns False when port is in use."""
        import socket

        from argus.api.server import check_port_available

        # Bind a port first
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 59998))
        sock.listen(1)

        try:
            # Now check_port_available should return False
            result = check_port_available("127.0.0.1", 59998)
            assert result is False
        finally:
            sock.close()

    @pytest.mark.asyncio
    async def test_run_server_raises_on_port_in_use(
        self, app_state, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Test run_server raises PortInUseError when port is occupied."""
        import logging
        import socket

        from argus.api.server import PortInUseError, create_app, run_server

        caplog.set_level(logging.CRITICAL)

        app = create_app(app_state)

        # Bind a port first
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", 59997))
        sock.listen(1)

        try:
            with pytest.raises(PortInUseError) as exc_info:
                await run_server(app, "127.0.0.1", 59997)

            assert "59997" in str(exc_info.value)
            assert "already in use" in caplog.text.lower()
        finally:
            sock.close()

    @pytest.mark.asyncio
    async def test_run_server_succeeds_when_port_free(self, app_state) -> None:
        """Test run_server returns a task when port is available."""
        import asyncio

        from argus.api.server import create_app, run_server

        app = create_app(app_state)

        # Use a high port that's likely to be free
        task = await run_server(app, "127.0.0.1", 59996)

        try:
            # Verify we got a task back
            assert isinstance(task, asyncio.Task)
        finally:
            # Clean up
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass


class TestServerLifespanQualityInit:
    """Tests for quality component initialization in server lifespan (S24-S7)."""

    @pytest.mark.asyncio
    async def test_server_lifespan_quality_init(self, app_state) -> None:
        """Quality components created during startup when enabled."""
        from argus.api.server import create_app

        app_state.config.quality_engine = QualityEngineConfig(enabled=True)

        app = create_app(app_state)

        async with app.router.lifespan_context(app):
            assert app_state.quality_engine is not None
            assert isinstance(app_state.quality_engine, SetupQualityEngine)
            assert app_state.position_sizer is not None
            assert isinstance(app_state.position_sizer, DynamicPositionSizer)

    @pytest.mark.asyncio
    async def test_server_lifespan_quality_disabled(self, app_state) -> None:
        """No components when quality engine is disabled."""
        from argus.api.server import create_app

        app_state.config.quality_engine = QualityEngineConfig(enabled=False)

        app = create_app(app_state)

        async with app.router.lifespan_context(app):
            assert app_state.quality_engine is None
            assert app_state.position_sizer is None

    @pytest.mark.asyncio
    async def test_health_component_registered(self, app_state) -> None:
        """quality_engine registered in health monitor when enabled."""
        from argus.api.server import create_app

        app_state.config.quality_engine = QualityEngineConfig(enabled=True)

        app = create_app(app_state)

        async with app.router.lifespan_context(app):
            status = app_state.health_monitor.get_status()
            assert "quality_engine" in status
