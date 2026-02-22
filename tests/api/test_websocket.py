"""Tests for WebSocket event streaming.

Tests the WebSocket bridge that streams Event Bus events to connected clients.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

import pytest
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from argus.api.auth import create_access_token
from argus.api.dependencies import AppState
from argus.api.server import create_app
from argus.api.websocket import get_bridge, reset_bridge
from argus.core.events import (
    OrderFilledEvent,
    PositionOpenedEvent,
    TickEvent,
)
from argus.execution.order_manager import ManagedPosition

# Re-use test constants from conftest
TEST_JWT_SECRET = "test-jwt-secret-for-argus-api-testing-minimum-32-chars"


@pytest.fixture(autouse=True)
def reset_websocket_bridge() -> None:
    """Reset the WebSocket bridge singleton before each test."""
    reset_bridge()


@pytest.fixture
def sync_client(
    app_state: AppState,
    jwt_secret: str,
) -> TestClient:
    """Provide a sync TestClient for WebSocket testing.

    Starlette's TestClient works synchronously for WebSocket tests.
    """
    app = create_app(app_state)
    app.state.app_state = app_state
    return TestClient(app)


@pytest.fixture
def valid_token(jwt_secret: str) -> str:
    """Get a valid JWT token for WebSocket auth."""
    token, _ = create_access_token(jwt_secret, expires_hours=24)
    return token


def test_ws_connect_valid_token(
    sync_client: TestClient,
    valid_token: str,
) -> None:
    """WebSocket connection should be accepted with valid token."""
    with sync_client.websocket_connect(f"/ws/v1/live?token={valid_token}") as ws:
        # Connection accepted - send a ping to verify it's working
        ws.send_json({"action": "ping"})
        response = ws.receive_json()
        assert response["type"] == "pong"
        assert "timestamp" in response


def test_ws_connect_invalid_token(
    sync_client: TestClient,
) -> None:
    """WebSocket connection should be closed with code 4001 for invalid token."""
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        sync_client.websocket_connect("/ws/v1/live?token=invalid-token"),
    ):
        pass
    # Verify close code is 4001
    assert exc_info.value.code == 4001


def test_ws_connect_missing_token(
    sync_client: TestClient,
) -> None:
    """WebSocket connection should be rejected without token."""
    # FastAPI should reject missing required query param with WebSocketDisconnect
    with (
        pytest.raises(WebSocketDisconnect) as exc_info,
        sync_client.websocket_connect("/ws/v1/live"),
    ):
        pass
    # Missing required query param results in 1008 (policy violation)
    assert exc_info.value.code in (1008, 1006, 4001, 1002)


def test_ws_ping_pong(
    sync_client: TestClient,
    valid_token: str,
) -> None:
    """Client should receive pong response with timestamp on ping."""
    with sync_client.websocket_connect(f"/ws/v1/live?token={valid_token}") as ws:
        ws.send_json({"action": "ping"})
        response = ws.receive_json()

        assert response["type"] == "pong"
        assert "timestamp" in response
        # Verify timestamp is valid ISO format
        datetime.fromisoformat(response["timestamp"])


@pytest.mark.asyncio
async def test_ws_receive_position_opened(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Client should receive position.opened event when published on EventBus."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    # Start the bridge
    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        # Give the connection time to register
        await asyncio.sleep(0.05)

        # Publish event on EventBus
        event = PositionOpenedEvent(
            position_id="pos_123",
            strategy_id="orb_breakout",
            symbol="AAPL",
            entry_price=185.00,
            shares=100,
            stop_price=183.00,
            target_prices=(187.00, 189.00),
        )
        await app_state.event_bus.publish(event)
        await app_state.event_bus.drain()

        # Give time for message to be queued
        await asyncio.sleep(0.05)

        # Receive the message
        response = ws.receive_json()

        assert response["type"] == "position.opened"
        assert response["data"]["position_id"] == "pos_123"
        assert response["data"]["symbol"] == "AAPL"
        assert response["data"]["entry_price"] == 185.00
        assert "sequence" in response
        assert "timestamp" in response

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_receive_order_filled(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Client should receive order.filled event when published on EventBus."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        await asyncio.sleep(0.05)

        event = OrderFilledEvent(
            order_id="order_456",
            fill_price=185.50,
            fill_quantity=100,
        )
        await app_state.event_bus.publish(event)
        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        response = ws.receive_json()

        assert response["type"] == "order.filled"
        assert response["data"]["order_id"] == "order_456"
        assert response["data"]["fill_price"] == 185.50

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_tick_position_filter(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """TickEvent for symbol without position should not be forwarded."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        await asyncio.sleep(0.05)

        # No positions, so tick should be filtered out
        event = TickEvent(
            symbol="AAPL",
            price=185.00,
            volume=1000,
        )
        await app_state.event_bus.publish(event)
        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        # Verify queue is empty by sending a ping and getting pong
        ws.send_json({"action": "ping"})
        response = ws.receive_json()
        # Should get pong, not price.update
        assert response["type"] == "pong"

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_tick_throttling(
    app_state: AppState,
    jwt_secret: str,
    test_clock,
) -> None:
    """Multiple TickEvents for same symbol should be throttled."""
    # Inject a position so ticks are not filtered
    now = test_clock.now()
    position = ManagedPosition(
        symbol="AAPL",
        strategy_id="orb_breakout",
        entry_price=185.00,
        entry_time=now - timedelta(minutes=10),
        shares_total=100,
        shares_remaining=100,
        stop_price=183.00,
        original_stop_price=183.00,
        stop_order_id="stop_001",
        t1_price=187.00,
        t1_order_id="t1_001",
        t1_shares=50,
        t1_filled=False,
        t2_price=189.00,
        high_watermark=185.50,
    )
    app_state.order_manager._managed_positions["AAPL"] = [position]

    # Configure fast throttle for testing (100ms)
    app_state.config.api.ws_tick_throttle_ms = 100

    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    received_count = 0
    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        await asyncio.sleep(0.05)

        # Publish 50 tick events rapidly
        for i in range(50):
            event = TickEvent(
                symbol="AAPL",
                price=185.00 + i * 0.01,
                volume=1000 + i,
            )
            await app_state.event_bus.publish(event)

        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        # Count received messages (with timeout)
        ws.send_json({"action": "ping"})
        while True:
            response = ws.receive_json()
            if response["type"] == "price.update":
                received_count += 1
            elif response["type"] == "pong":
                break

    # With 100ms throttle and near-instant publishing, should get <= 2 messages
    assert received_count <= 2, f"Expected <= 2 ticks, got {received_count}"

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_subscribe_filter(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Client subscribed to specific types should only receive those."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        await asyncio.sleep(0.05)

        # Subscribe only to position.opened
        ws.send_json({"action": "subscribe", "types": ["position.opened"]})
        await asyncio.sleep(0.05)

        # Publish an order.filled (should be filtered)
        order_event = OrderFilledEvent(
            order_id="order_999",
            fill_price=200.00,
            fill_quantity=50,
        )
        await app_state.event_bus.publish(order_event)

        # Publish a position.opened (should be received)
        position_event = PositionOpenedEvent(
            position_id="pos_filtered",
            strategy_id="orb_breakout",
            symbol="TSLA",
            entry_price=200.00,
            shares=50,
            stop_price=195.00,
            target_prices=(205.00, 210.00),
        )
        await app_state.event_bus.publish(position_event)
        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        # Should get position.opened, not order.filled
        response = ws.receive_json()
        assert response["type"] == "position.opened"
        assert response["data"]["symbol"] == "TSLA"

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_unsubscribe(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Client should stop receiving unsubscribed event types."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        await asyncio.sleep(0.05)

        # First, subscribe to specific types
        ws.send_json({"action": "subscribe", "types": ["position.opened", "order.filled"]})
        await asyncio.sleep(0.05)

        # Unsubscribe from position.opened
        ws.send_json({"action": "unsubscribe", "types": ["position.opened"]})
        await asyncio.sleep(0.05)

        # Publish position.opened (should be filtered now)
        pos_event = PositionOpenedEvent(
            position_id="pos_unsub",
            strategy_id="orb_breakout",
            symbol="GOOG",
            entry_price=180.00,
            shares=25,
            stop_price=175.00,
            target_prices=(185.00,),
        )
        await app_state.event_bus.publish(pos_event)

        # Publish order.filled (should still be received)
        order_event = OrderFilledEvent(
            order_id="order_unsub",
            fill_price=300.00,
            fill_quantity=10,
        )
        await app_state.event_bus.publish(order_event)
        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        # Should get order.filled, not position.opened
        response = ws.receive_json()
        assert response["type"] == "order.filled"
        assert response["data"]["order_id"] == "order_unsub"

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_heartbeat(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Client should receive heartbeat at configured interval."""
    # Configure 1-second heartbeat for faster testing
    app_state.config.api.ws_heartbeat_interval_seconds = 1

    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws:
        # Wait for heartbeat (1 second + buffer)
        await asyncio.sleep(1.2)

        response = ws.receive_json()
        assert response["type"] == "system.heartbeat"
        assert response["data"]["status"] == "alive"
        assert "timestamp" in response

    bridge.stop()


@pytest.mark.asyncio
async def test_ws_multiple_clients(
    app_state: AppState,
    jwt_secret: str,
) -> None:
    """Multiple connected clients should all receive the same events."""
    app = create_app(app_state)
    app.state.app_state = app_state
    sync_client = TestClient(app)

    bridge = get_bridge()
    bridge.start(
        event_bus=app_state.event_bus,
        order_manager=app_state.order_manager,
        config=app_state.config.api,
    )

    token, _ = create_access_token(jwt_secret, expires_hours=24)

    with (
        sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws1,
        sync_client.websocket_connect(f"/ws/v1/live?token={token}") as ws2,
    ):
        await asyncio.sleep(0.05)

        # Verify both clients are registered
        assert len(bridge.clients) == 2

        # Publish an event
        event = PositionOpenedEvent(
            position_id="pos_multi",
            strategy_id="orb_breakout",
            symbol="MULTI",
            entry_price=100.00,
            shares=10,
            stop_price=95.00,
            target_prices=(105.00,),
        )
        await app_state.event_bus.publish(event)
        await app_state.event_bus.drain()
        await asyncio.sleep(0.05)

        # Both clients should receive the event
        response1 = ws1.receive_json()
        response2 = ws2.receive_json()

        assert response1["type"] == "position.opened"
        assert response1["data"]["symbol"] == "MULTI"
        assert response2["type"] == "position.opened"
        assert response2["data"]["symbol"] == "MULTI"

    bridge.stop()
