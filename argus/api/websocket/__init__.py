"""WebSocket handlers for real-time event streaming.

Bridges Event Bus events to connected WebSocket clients.
"""

from argus.api.websocket.ai_chat import ai_ws_router, get_active_connections
from argus.api.websocket.alerts_ws import (
    alerts_ws_router,
    get_active_alerts_connections,
)
from argus.api.websocket.arena_ws import arena_ws_router, get_active_arena_connections
from argus.api.websocket.live import (
    ClientConnection,
    WebSocketBridge,
    get_bridge,
    reset_bridge,
    ws_router,
)
from argus.api.websocket.observatory_ws import (
    get_active_observatory_connections,
    observatory_ws_router,
)

__all__ = [
    "ClientConnection",
    "WebSocketBridge",
    "get_bridge",
    "reset_bridge",
    "ws_router",
    "ai_ws_router",
    "get_active_connections",
    "observatory_ws_router",
    "get_active_observatory_connections",
    "arena_ws_router",
    "get_active_arena_connections",
    "alerts_ws_router",
    "get_active_alerts_connections",
]
