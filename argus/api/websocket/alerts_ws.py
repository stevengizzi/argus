"""WebSocket fan-out for alert-state changes (Sprint 31.91 5a.2).

Pushes alert lifecycle deltas to connected clients in real time.
Authentication via JWT in the first client message — same idiom as
``observatory_ws.py``. Initial frame on connect is a full ``snapshot``
of every active alert; subsequent frames are state-change deltas.

Frame types:

- ``snapshot`` — initial state on connect. ``alerts`` is the full list.
- ``alert_active`` — new alert reached HealthMonitor.
- ``alert_acknowledged`` — operator acknowledged via REST.
- ``alert_auto_resolved`` — predicate fired; alert moved to ARCHIVED.
- ``alert_archived`` — ARCHIVED via any other path (operator close,
  retention purge, future late-state transitions).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import jwt
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jwt import PyJWTError

from argus.api.auth import get_jwt_secret
from argus.api.dependencies import AppState
from argus.core.health import HealthMonitor, _alert_to_payload

logger = logging.getLogger(__name__)

alerts_ws_router = APIRouter(tags=["alerts-websocket"])

_active_connections: set[WebSocket] = set()


def get_active_alerts_connections() -> set[WebSocket]:
    """Test/diagnostics accessor for the active connection set."""
    return _active_connections


@alerts_ws_router.websocket("/ws/v1/alerts")
async def alerts_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for live alert-state deltas.

    Protocol:
      1. Client sends ``{"type": "auth", "token": "<JWT>"}``.
      2. Server validates JWT; closes 4001 on failure.
      3. Server sends a ``snapshot`` frame containing every active alert.
      4. Server pushes ``alert_*`` deltas as HealthMonitor publishes them.
    """
    await websocket.accept()
    _active_connections.add(websocket)
    queue: asyncio.Queue[dict[str, Any]] | None = None
    health_monitor: HealthMonitor | None = None
    _watcher_task: asyncio.Task[None] | None = None

    try:
        app_state: AppState = websocket.app.state.app_state
        health_monitor = app_state.health_monitor

        # JWT auth (matches observatory_ws.py pattern).
        try:
            auth_data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=30.0,
            )
        except asyncio.TimeoutError:
            await websocket.close(code=4001)
            return

        if auth_data.get("type") != "auth":
            await websocket.close(code=4001)
            return
        token = auth_data.get("token")
        if not token:
            await websocket.close(code=4001)
            return
        try:
            jwt.decode(token, get_jwt_secret(), algorithms=["HS256"])
        except (PyJWTError, Exception):
            await websocket.close(code=4001)
            return

        await websocket.send_json({
            "type": "auth_success",
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Initial snapshot.
        snapshot = [
            _alert_to_payload(a) for a in health_monitor.get_active_alerts()
        ]
        await websocket.send_json({
            "type": "snapshot",
            "timestamp": datetime.now(UTC).isoformat(),
            "alerts": snapshot,
        })

        # Subscribe AFTER the snapshot send so a new alert that races the
        # connect doesn't appear twice (once in snapshot, once as
        # alert_active). Acceptable race on the other side: a brand-new
        # alert during the window between get_active_alerts() and
        # subscribe() is missed by this client; HealthMonitor logs the
        # alert so it's visible via REST recovery.
        queue = health_monitor.subscribe_state_changes()

        # Disconnect watcher (DEF-193 / DEF-200 idiom).
        _disconnect_event = asyncio.Event()

        async def _watch_disconnect() -> None:
            try:
                await websocket.receive()
            except WebSocketDisconnect:
                pass
            except Exception:
                pass
            finally:
                _disconnect_event.set()

        _watcher_task = asyncio.create_task(_watch_disconnect())

        # Push loop: race the queue against the disconnect sentinel.
        while not _disconnect_event.is_set():
            queue_get = asyncio.create_task(queue.get())
            disconnect_wait = asyncio.create_task(_disconnect_event.wait())
            try:
                done, pending = await asyncio.wait(
                    {queue_get, disconnect_wait},
                    return_when=asyncio.FIRST_COMPLETED,
                )
            finally:
                for task in (queue_get, disconnect_wait):
                    if not task.done():
                        task.cancel()
                        try:
                            await task
                        except (asyncio.CancelledError, Exception):
                            pass
            if _disconnect_event.is_set():
                break
            if queue_get in done:
                message = queue_get.result()
                message_with_ts = {
                    **message,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
                await websocket.send_json(message_with_ts)

    except WebSocketDisconnect:
        pass
    except Exception as exc:  # pragma: no cover - defensive
        logger.warning("Alerts WebSocket error: %s", exc)
    finally:
        if _watcher_task is not None:
            _watcher_task.cancel()
            try:
                await _watcher_task
            except (asyncio.CancelledError, Exception):
                pass
        if queue is not None and health_monitor is not None:
            health_monitor.unsubscribe_state_changes(queue)
        _active_connections.discard(websocket)
        try:
            await websocket.close()
        except Exception:
            pass
