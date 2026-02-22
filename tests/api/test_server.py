"""Tests for the FastAPI server factory."""

from __future__ import annotations

import pytest
from fastapi import FastAPI


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
