"""Tests for Orchestrator API endpoints.

Tests the orchestrator routes:
- GET /api/v1/orchestrator/status
- GET /api/v1/orchestrator/decisions
- POST /api/v1/orchestrator/rebalance
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pytest

from argus.api.server import create_app
from argus.api.websocket.live import get_bridge, reset_bridge
from argus.core.config import OrchestratorConfig
from argus.core.events import AllocationUpdateEvent, RegimeChangeEvent
from argus.core.regime import MarketRegime, RegimeIndicators
from argus.core.throttle import StrategyAllocation, ThrottleAction

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

    from httpx import AsyncClient

    from argus.api.dependencies import AppState


# ---------------------------------------------------------------------------
# Mock Orchestrator for testing
# ---------------------------------------------------------------------------


@dataclass
class MockOrchestrator:
    """Mock orchestrator for API testing."""

    _config: OrchestratorConfig
    _current_regime: MarketRegime
    _current_allocations: dict[str, StrategyAllocation]
    _current_indicators: RegimeIndicators | None
    _last_regime_check: datetime | None
    _rebalance_called: bool = False

    @property
    def current_regime(self) -> MarketRegime:
        """Get current market regime."""
        return self._current_regime

    @property
    def current_allocations(self) -> dict[str, StrategyAllocation]:
        """Get current strategy allocations."""
        return self._current_allocations

    @property
    def current_indicators(self) -> RegimeIndicators | None:
        """Get current regime indicators."""
        return self._current_indicators

    @property
    def last_regime_check(self) -> datetime | None:
        """When the last regime re-check occurred."""
        return self._last_regime_check

    @property
    def regime_check_interval_minutes(self) -> int:
        """Minutes between regime re-checks."""
        return self._config.regime_check_interval_minutes

    @property
    def cash_reserve_pct(self) -> float:
        """Cash reserve percentage from config."""
        return self._config.cash_reserve_pct

    async def manual_rebalance(self) -> dict[str, StrategyAllocation]:
        """Mock rebalance - returns current allocations."""
        self._rebalance_called = True
        return self._current_allocations


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_orchestrator() -> MockOrchestrator:
    """Create a mock orchestrator for testing."""
    config = OrchestratorConfig()
    indicators = RegimeIndicators(
        spy_price=525.50,
        spy_sma_20=520.30,
        spy_sma_50=515.80,
        spy_roc_5d=1.25,
        spy_realized_vol_20d=12.5,
        spy_vs_vwap=0.002,
        timestamp=datetime.now(UTC),
    )
    allocations = {
        "orb_breakout": StrategyAllocation(
            strategy_id="orb_breakout",
            allocation_pct=0.40,
            allocation_dollars=40000.0,
            throttle_action=ThrottleAction.NONE,
            eligible=True,
            reason="Active: 40% allocation",
        ),
    }
    return MockOrchestrator(
        _config=config,
        _current_regime=MarketRegime.BULLISH_TRENDING,
        _current_allocations=allocations,
        _current_indicators=indicators,
        _last_regime_check=datetime.now(UTC) - timedelta(minutes=30),
    )


@pytest.fixture
async def app_state_with_orchestrator(
    app_state: AppState,
    mock_orchestrator: MockOrchestrator,
) -> AppState:
    """Provide AppState with mock orchestrator."""
    app_state.orchestrator = mock_orchestrator  # type: ignore[assignment]
    return app_state


@pytest.fixture
async def client_with_orchestrator(
    app_state_with_orchestrator: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing mock orchestrator."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(app_state_with_orchestrator)
    app.state.app_state = app_state_with_orchestrator
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
async def app_state_with_decisions(
    app_state_with_orchestrator: AppState,
) -> AppState:
    """Provide AppState with seeded orchestrator decisions."""
    trade_logger = app_state_with_orchestrator.trade_logger
    now = datetime.now(UTC)
    today = now.date().isoformat()
    yesterday = (now - timedelta(days=1)).date().isoformat()

    # Seed some decisions
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={"allocation_pct": 0.40, "regime": "bullish_trending"},
        rationale="Active: 40% allocation",
    )
    await trade_logger.log_orchestrator_decision(
        date=today,
        decision_type="regime_classification",
        strategy_id=None,
        details={"regime": "bullish_trending", "spy_price": 525.50},
        rationale="SPY above both SMAs",
    )
    await trade_logger.log_orchestrator_decision(
        date=yesterday,
        decision_type="allocation",
        strategy_id="orb_breakout",
        details={"allocation_pct": 0.35, "regime": "bullish_trending"},
        rationale="Active: 35% allocation",
    )

    return app_state_with_orchestrator


@pytest.fixture
async def client_with_decisions(
    app_state_with_decisions: AppState,
    jwt_secret: str,
) -> AsyncGenerator[AsyncClient, None]:
    """Provide client with AppState containing orchestrator decisions."""
    from httpx import ASGITransport, AsyncClient

    app = create_app(app_state_with_decisions)
    app.state.app_state = app_state_with_decisions
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


# ---------------------------------------------------------------------------
# Status Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_returns_regime_and_allocations(
    client_with_orchestrator: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status returns current regime and allocations."""
    response = await client_with_orchestrator.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    # Check regime
    assert data["regime"] == "bullish_trending"

    # Check allocations
    assert len(data["allocations"]) == 1
    alloc = data["allocations"][0]
    assert alloc["strategy_id"] == "orb_breakout"
    assert alloc["allocation_pct"] == 0.40
    assert alloc["allocation_dollars"] == 40000.0
    assert alloc["throttle_action"] == "none"
    assert alloc["eligible"] is True

    # Check indicators
    assert data["regime_indicators"]["spy_price"] == 525.50
    assert data["regime_indicators"]["spy_sma_20"] == 520.30

    # Check other fields
    assert data["cash_reserve_pct"] == 0.20  # Default from OrchestratorConfig
    assert data["total_deployed_pct"] == 0.40
    assert "regime_updated_at" in data
    assert "next_regime_check" in data
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_get_status_requires_auth(
    client_with_orchestrator: AsyncClient,
) -> None:
    """GET /orchestrator/status requires authentication."""
    response = await client_with_orchestrator.get("/api/v1/orchestrator/status")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_status_returns_503_without_orchestrator(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/status returns 503 when orchestrator not available."""
    response = await client.get(
        "/api/v1/orchestrator/status",
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "not available" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Decisions Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_decisions_paginated(
    client_with_decisions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions returns paginated decision history."""
    response = await client_with_decisions.get(
        "/api/v1/orchestrator/decisions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["decisions"]) == 3
    assert data["limit"] == 50
    assert data["offset"] == 0

    # Check first decision (most recent)
    decision = data["decisions"][0]
    assert "id" in decision
    assert "date" in decision
    assert "decision_type" in decision
    assert "created_at" in decision


@pytest.mark.asyncio
async def test_get_decisions_with_pagination(
    client_with_decisions: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions respects limit and offset."""
    response = await client_with_decisions.get(
        "/api/v1/orchestrator/decisions?limit=1&offset=1",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["total"] == 3
    assert len(data["decisions"]) == 1
    assert data["limit"] == 1
    assert data["offset"] == 1


@pytest.mark.asyncio
async def test_get_decisions_requires_auth(
    client_with_decisions: AsyncClient,
) -> None:
    """GET /orchestrator/decisions requires authentication."""
    response = await client_with_decisions.get("/api/v1/orchestrator/decisions")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Rebalance Endpoint Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_post_rebalance_triggers_rebalance(
    client_with_orchestrator: AsyncClient,
    auth_headers: dict[str, str],
    mock_orchestrator: MockOrchestrator,
) -> None:
    """POST /orchestrator/rebalance triggers manual rebalance."""
    response = await client_with_orchestrator.post(
        "/api/v1/orchestrator/rebalance",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["message"] == "Rebalance completed successfully"
    assert data["regime"] == "bullish_trending"
    assert len(data["allocations"]) == 1
    assert mock_orchestrator._rebalance_called is True


@pytest.mark.asyncio
async def test_post_rebalance_requires_auth(
    client_with_orchestrator: AsyncClient,
) -> None:
    """POST /orchestrator/rebalance requires authentication."""
    response = await client_with_orchestrator.post("/api/v1/orchestrator/rebalance")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_post_rebalance_returns_503_without_orchestrator(
    client: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """POST /orchestrator/rebalance returns 503 when orchestrator not available."""
    response = await client.post(
        "/api/v1/orchestrator/rebalance",
        headers=auth_headers,
    )
    assert response.status_code == 503


# ---------------------------------------------------------------------------
# WebSocket Event Forwarding Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_forwards_regime_change_event(
    app_state_with_orchestrator: AppState,
) -> None:
    """WebSocket bridge forwards RegimeChangeEvent to clients."""
    reset_bridge()
    bridge = get_bridge()

    # Start the bridge
    bridge.start(
        app_state_with_orchestrator.event_bus,
        app_state_with_orchestrator.order_manager,
        app_state_with_orchestrator.config.api,
    )

    try:
        # Create a mock client
        from unittest.mock import MagicMock

        from argus.api.websocket.live import ClientConnection

        mock_ws = MagicMock()
        client = ClientConnection(websocket=mock_ws)
        bridge.add_client(client)

        # Publish event
        event = RegimeChangeEvent(
            old_regime="bullish_trending",
            new_regime="bearish_trending",
            indicators={"spy_price": 500.0, "spy_sma_20": 505.0},
        )
        await app_state_with_orchestrator.event_bus.publish(event)

        # Small delay to allow event processing
        await asyncio.sleep(0.1)

        # Check that message was queued
        assert client.send_queue.qsize() == 1
        message = client.send_queue.get_nowait()
        assert message["type"] == "orchestrator.regime_change"
        assert message["data"]["old_regime"] == "bullish_trending"
        assert message["data"]["new_regime"] == "bearish_trending"

    finally:
        bridge.stop()
        reset_bridge()


@pytest.mark.asyncio
async def test_websocket_forwards_allocation_update_event(
    app_state_with_orchestrator: AppState,
) -> None:
    """WebSocket bridge forwards AllocationUpdateEvent to clients."""
    reset_bridge()
    bridge = get_bridge()

    # Start the bridge
    bridge.start(
        app_state_with_orchestrator.event_bus,
        app_state_with_orchestrator.order_manager,
        app_state_with_orchestrator.config.api,
    )

    try:
        # Create a mock client
        from unittest.mock import MagicMock

        from argus.api.websocket.live import ClientConnection

        mock_ws = MagicMock()
        client = ClientConnection(websocket=mock_ws)
        bridge.add_client(client)

        # Publish event
        event = AllocationUpdateEvent(
            strategy_id="orb_breakout",
            new_allocation_pct=0.50,
            reason="Increased allocation after strong performance",
        )
        await app_state_with_orchestrator.event_bus.publish(event)

        # Small delay to allow event processing
        await asyncio.sleep(0.1)

        # Check that message was queued
        assert client.send_queue.qsize() == 1
        message = client.send_queue.get_nowait()
        assert message["type"] == "orchestrator.allocation_update"
        assert message["data"]["strategy_id"] == "orb_breakout"
        assert message["data"]["new_allocation_pct"] == 0.50

    finally:
        bridge.stop()
        reset_bridge()


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_status_with_no_indicators(
    app_state_with_orchestrator: AppState,
    auth_headers: dict[str, str],
    jwt_secret: str,
) -> None:
    """GET /orchestrator/status handles missing indicators gracefully."""
    from httpx import ASGITransport, AsyncClient

    # Clear indicators
    app_state_with_orchestrator.orchestrator._current_indicators = None  # type: ignore[union-attr]
    app_state_with_orchestrator.orchestrator._last_regime_check = None  # type: ignore[union-attr]

    app = create_app(app_state_with_orchestrator)
    app.state.app_state = app_state_with_orchestrator

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        response = await client.get(
            "/api/v1/orchestrator/status",
            headers=auth_headers,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["regime_indicators"] == {}
    assert data["regime_updated_at"] is None
    assert data["next_regime_check"] is None


@pytest.mark.asyncio
async def test_get_decisions_empty(
    client_with_orchestrator: AsyncClient,
    auth_headers: dict[str, str],
) -> None:
    """GET /orchestrator/decisions returns empty list when no decisions exist."""
    response = await client_with_orchestrator.get(
        "/api/v1/orchestrator/decisions",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["decisions"] == []
