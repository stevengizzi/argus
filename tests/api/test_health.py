"""Tests for the health endpoint."""

from __future__ import annotations

import time

import pytest

from argus.core.health import ComponentStatus


@pytest.mark.asyncio
async def test_health_all_healthy(client, auth_headers, test_health_monitor):
    """GET /health returns 'healthy' when all components are healthy."""
    # Register some healthy components
    test_health_monitor.update_component(
        "event_bus",
        ComponentStatus.HEALTHY,
        "Event bus running",
    )
    test_health_monitor.update_component(
        "broker",
        ComponentStatus.HEALTHY,
        "Broker connected",
    )
    test_health_monitor.update_component(
        "data_service",
        ComponentStatus.HEALTHY,
        "Data service streaming",
    )

    response = await client.get("/api/v1/health", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "healthy"
    assert "components" in data
    assert len(data["components"]) == 3
    assert data["components"]["event_bus"]["status"] == "healthy"
    assert data["components"]["broker"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_health_degraded(client, auth_headers, test_health_monitor):
    """GET /health returns 'degraded' when one component is degraded."""
    # Register components with one degraded
    test_health_monitor.update_component(
        "event_bus",
        ComponentStatus.HEALTHY,
        "Event bus running",
    )
    test_health_monitor.update_component(
        "broker",
        ComponentStatus.DEGRADED,
        "Broker reconnecting",
    )
    test_health_monitor.update_component(
        "data_service",
        ComponentStatus.HEALTHY,
        "Data service streaming",
    )

    response = await client.get("/api/v1/health", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "degraded"
    assert data["components"]["broker"]["status"] == "degraded"
    assert data["components"]["broker"]["details"] == "Broker reconnecting"


@pytest.mark.asyncio
async def test_health_uptime(client, auth_headers, app_state):
    """Uptime_seconds is reasonable (greater than 0)."""
    # Ensure start_time is set in the past
    app_state.start_time = time.time() - 60  # 1 minute ago

    response = await client.get("/api/v1/health", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert "uptime_seconds" in data
    assert isinstance(data["uptime_seconds"], int)
    assert data["uptime_seconds"] >= 0


@pytest.mark.asyncio
async def test_health_paper_mode(client, auth_headers, app_state):
    """Paper_mode matches config broker_source."""
    # Default test config uses simulated broker (paper mode)
    response = await client.get("/api/v1/health", headers=auth_headers)

    assert response.status_code == 200

    data = response.json()

    assert "paper_mode" in data
    assert isinstance(data["paper_mode"], bool)
    # Simulated broker is paper mode
    assert data["paper_mode"] is True


@pytest.mark.asyncio
async def test_health_unauthenticated(client):
    """GET /health without token returns 401."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 401
