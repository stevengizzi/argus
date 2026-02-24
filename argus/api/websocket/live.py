"""WebSocket bridge for real-time event streaming.

Bridges Event Bus events to connected WebSocket clients with filtering,
throttling, and authentication.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from jose import JWTError

from argus.api.auth import get_jwt_secret
from argus.api.serializers import serialize_event
from argus.core.events import (
    AllocationUpdateEvent,
    CircuitBreakerEvent,
    Event,
    HeartbeatEvent,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    OrderRejectedEvent,
    OrderSubmittedEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    PositionUpdatedEvent,
    RegimeChangeEvent,
    SignalEvent,
    StrategyActivatedEvent,
    StrategySuspendedEvent,
    TickEvent,
    WatchlistEvent,
)

if TYPE_CHECKING:
    from argus.core.config import ApiConfig
    from argus.core.event_bus import EventBus
    from argus.execution.order_manager import OrderManager

logger = logging.getLogger(__name__)

# WebSocket router - mounted without /api/v1 prefix
ws_router = APIRouter(tags=["websocket"])

# Event type mapping: internal class name -> WS type string
EVENT_TYPE_MAP: dict[type[Event], str] = {
    PositionOpenedEvent: "position.opened",
    PositionClosedEvent: "position.closed",
    PositionUpdatedEvent: "position.updated",
    OrderSubmittedEvent: "order.submitted",
    OrderFilledEvent: "order.filled",
    OrderCancelledEvent: "order.cancelled",
    CircuitBreakerEvent: "system.circuit_breaker",
    HeartbeatEvent: "system.heartbeat",
    WatchlistEvent: "scanner.watchlist",
    SignalEvent: "strategy.signal",
    OrderApprovedEvent: "order.approved",
    OrderRejectedEvent: "order.rejected",
    TickEvent: "price.update",
    # Orchestrator events
    RegimeChangeEvent: "orchestrator.regime_change",
    AllocationUpdateEvent: "orchestrator.allocation_update",
    StrategyActivatedEvent: "orchestrator.strategy_activated",
    StrategySuspendedEvent: "orchestrator.strategy_suspended",
}


@dataclass
class ClientConnection:
    """Represents a connected WebSocket client.

    Attributes:
        websocket: The WebSocket connection.
        subscribed_types: Set of event types to receive, or None for all.
        send_queue: Async queue for outgoing messages.
    """

    websocket: WebSocket
    subscribed_types: set[str] | None = None
    send_queue: asyncio.Queue[dict[str, Any]] = field(
        default_factory=lambda: asyncio.Queue(maxsize=1000)
    )

    def wants_event(self, ws_type: str) -> bool:
        """Check if this client wants to receive an event type.

        Args:
            ws_type: The WebSocket event type string.

        Returns:
            True if the client should receive this event.
        """
        if self.subscribed_types is None:
            # None means subscribe to all
            return True
        return ws_type in self.subscribed_types


class WebSocketBridge:
    """Bridges Event Bus events to WebSocket clients.

    Singleton class that manages client connections, subscribes to events,
    and broadcasts to connected clients with filtering and throttling.
    """

    def __init__(self) -> None:
        """Initialize the WebSocket bridge."""
        self._clients: list[ClientConnection] = []
        self._event_bus: EventBus | None = None
        self._order_manager: OrderManager | None = None
        self._config: ApiConfig | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._running = False

        # Tick throttling: {symbol: last_send_time_monotonic}
        self._tick_last_sent: dict[str, float] = {}

    @property
    def clients(self) -> list[ClientConnection]:
        """Get the list of connected clients."""
        return self._clients

    def start(
        self,
        event_bus: EventBus,
        order_manager: OrderManager,
        config: ApiConfig,
    ) -> None:
        """Start the WebSocket bridge.

        Subscribes to Event Bus events and starts the heartbeat loop.

        Args:
            event_bus: The Event Bus to subscribe to.
            order_manager: The Order Manager for position filtering.
            config: API configuration with WebSocket settings.
        """
        if self._running:
            logger.warning("WebSocketBridge already running")
            return

        self._event_bus = event_bus
        self._order_manager = order_manager
        self._config = config
        self._running = True

        # Subscribe to all standard events
        standard_events: list[type[Event]] = [
            PositionOpenedEvent,
            PositionClosedEvent,
            PositionUpdatedEvent,
            OrderSubmittedEvent,
            OrderFilledEvent,
            OrderCancelledEvent,
            CircuitBreakerEvent,
            HeartbeatEvent,
            WatchlistEvent,
            SignalEvent,
            OrderApprovedEvent,
            OrderRejectedEvent,
            # Orchestrator events
            RegimeChangeEvent,
            AllocationUpdateEvent,
            StrategyActivatedEvent,
            StrategySuspendedEvent,
        ]

        for event_type in standard_events:
            event_bus.subscribe(event_type, self._handle_standard_event)

        # Subscribe to TickEvent with throttled handling
        event_bus.subscribe(TickEvent, self._handle_tick_event)

        # Start heartbeat loop
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("WebSocketBridge started")

    def stop(self) -> None:
        """Stop the WebSocket bridge.

        Cancels heartbeat and unsubscribes from events.
        """
        if not self._running:
            return

        self._running = False

        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            self._heartbeat_task = None

        # Unsubscribe from events
        if self._event_bus:
            standard_events: list[type[Event]] = [
                PositionOpenedEvent,
                PositionClosedEvent,
                PositionUpdatedEvent,
                OrderSubmittedEvent,
                OrderFilledEvent,
                OrderCancelledEvent,
                CircuitBreakerEvent,
                HeartbeatEvent,
                WatchlistEvent,
                SignalEvent,
                OrderApprovedEvent,
                OrderRejectedEvent,
                # Orchestrator events
                RegimeChangeEvent,
                AllocationUpdateEvent,
                StrategyActivatedEvent,
                StrategySuspendedEvent,
            ]

            for event_type in standard_events:
                self._event_bus.unsubscribe(event_type, self._handle_standard_event)
            self._event_bus.unsubscribe(TickEvent, self._handle_tick_event)

        self._clients.clear()
        logger.info("WebSocketBridge stopped")

    def add_client(self, client: ClientConnection) -> None:
        """Add a client connection.

        Args:
            client: The client to add.
        """
        self._clients.append(client)
        logger.info(f"WebSocket client connected (total: {len(self._clients)})")

    def remove_client(self, client: ClientConnection) -> None:
        """Remove a client connection.

        Args:
            client: The client to remove.
        """
        if client in self._clients:
            self._clients.remove(client)
            logger.info(f"WebSocket client disconnected (total: {len(self._clients)})")

    async def _handle_standard_event(self, event: Event) -> None:
        """Handle standard (non-tick) events from the Event Bus.

        Args:
            event: The event to broadcast.
        """
        ws_type = EVENT_TYPE_MAP.get(type(event))
        if not ws_type:
            return

        message = self._create_message(event, ws_type)
        await self._broadcast(message, ws_type)

    async def _handle_tick_event(self, event: TickEvent) -> None:
        """Handle TickEvent with position filtering and throttling.

        Only forwards ticks for symbols with open positions, and throttles
        to max 1 per ws_tick_throttle_ms per symbol.

        Args:
            event: The TickEvent to handle.
        """
        if not self._order_manager:
            return

        # Check if we have an open position for this symbol
        positions = self._order_manager.get_all_positions_flat()
        position_symbols = {p.symbol for p in positions if not p.is_fully_closed}

        if event.symbol not in position_symbols:
            return

        # Throttle: check time since last send for this symbol
        throttle_ms = self._config.ws_tick_throttle_ms if self._config else 1000
        throttle_seconds = throttle_ms / 1000.0
        now = time.monotonic()
        last_sent = self._tick_last_sent.get(event.symbol, 0.0)

        if now - last_sent < throttle_seconds:
            return

        self._tick_last_sent[event.symbol] = now

        # Create simplified message for price updates
        message = {
            "type": "price.update",
            "data": {
                "symbol": event.symbol,
                "price": event.price,
                "volume": event.volume,
            },
            "sequence": event.sequence,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        await self._broadcast(message, "price.update")

    def _create_message(self, event: Event, ws_type: str) -> dict[str, Any]:
        """Create a WebSocket message from an event.

        Args:
            event: The event to serialize.
            ws_type: The WebSocket event type string.

        Returns:
            Dictionary with type, data, sequence, timestamp.
        """
        return {
            "type": ws_type,
            "data": serialize_event(event),
            "sequence": event.sequence,
            "timestamp": datetime.now(UTC).isoformat(),
        }

    async def _broadcast(self, message: dict[str, Any], ws_type: str) -> None:
        """Broadcast a message to all clients that want it.

        Args:
            message: The message to broadcast.
            ws_type: The event type for filtering.
        """
        for client in self._clients:
            if client.wants_event(ws_type):
                try:
                    client.send_queue.put_nowait(message)
                except asyncio.QueueFull:
                    logger.warning("WebSocket send queue full for client, dropping message")

    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeat messages to all clients."""
        interval = self._config.ws_heartbeat_interval_seconds if self._config else 30

        while self._running:
            try:
                await asyncio.sleep(interval)
                if not self._running:
                    break

                message = {
                    "type": "system.heartbeat",
                    "data": {"status": "alive"},
                    "sequence": 0,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await self._broadcast(message, "system.heartbeat")
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in heartbeat loop")


# Module-level singleton
_bridge: WebSocketBridge | None = None


def get_bridge() -> WebSocketBridge:
    """Get the WebSocketBridge singleton.

    Creates the instance if it doesn't exist.

    Returns:
        The WebSocketBridge singleton instance.
    """
    global _bridge
    if _bridge is None:
        _bridge = WebSocketBridge()
    return _bridge


def reset_bridge() -> None:
    """Reset the bridge singleton (for testing)."""
    global _bridge
    if _bridge:
        _bridge.stop()
    _bridge = None


@ws_router.websocket("/ws/v1/live")
async def websocket_endpoint(
    websocket: WebSocket,
    token: str = Query(...),
) -> None:
    """WebSocket endpoint for real-time event streaming.

    Authenticates via JWT token in query parameter, then streams events
    from the Event Bus to the client.

    Args:
        websocket: The WebSocket connection.
        token: JWT token for authentication (query parameter).
    """
    from jose import jwt

    # 1. Authenticate
    try:
        jwt_secret = get_jwt_secret()
        jwt.decode(token, jwt_secret, algorithms=["HS256"])
    except (JWTError, Exception):
        await websocket.close(code=4001)
        return

    # 2. Accept connection
    await websocket.accept()

    # 3. Create client and add to bridge
    bridge = get_bridge()
    client = ClientConnection(websocket=websocket)
    bridge.add_client(client)

    # 4. Start sender task
    async def sender() -> None:
        """Drain send_queue and send to websocket."""
        try:
            while True:
                message = await client.send_queue.get()
                await websocket.send_json(message)
        except (WebSocketDisconnect, Exception):
            pass

    sender_task = asyncio.create_task(sender())

    try:
        # 5. Receiver loop
        while True:
            try:
                data = await websocket.receive_json()
            except WebSocketDisconnect:
                break

            action = data.get("action")

            if action == "ping":
                # Send pong response
                await websocket.send_json(
                    {
                        "type": "pong",
                        "timestamp": datetime.now(UTC).isoformat(),
                    }
                )

            elif action == "subscribe":
                # Set subscribed types
                types = data.get("types", [])
                if types:
                    if client.subscribed_types is None:
                        client.subscribed_types = set()
                    client.subscribed_types.update(types)

            elif action == "unsubscribe":
                # Remove from subscribed types
                types = data.get("types", [])
                if client.subscribed_types and types:
                    client.subscribed_types -= set(types)
                    # If empty after unsubscribe, keep as empty set (not None)
                    # so we don't revert to "all events"

    except Exception:
        logger.exception("Error in WebSocket receiver loop")
    finally:
        # 6. Cleanup
        sender_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await sender_task
        bridge.remove_client(client)
