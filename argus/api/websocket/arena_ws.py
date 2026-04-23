"""WebSocket handler for Arena real-time position streaming.

Streams position ticks, candles (filtered to open symbols), position
open/close events, and aggregate stats to connected clients.

Sprint 32.75, Session 7.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import time
from collections import deque
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import jwt

from argus.api.auth import get_jwt_secret
from argus.api.dependencies import AppState
from argus.core.events import (
    CandleEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    PositionUpdatedEvent,
    TickEvent,
)

if TYPE_CHECKING:
    from argus.core.event_bus import EventBus
    from argus.execution.order_manager import OrderManager

logger = logging.getLogger(__name__)

arena_ws_router = APIRouter(tags=["arena-websocket"])

_STATS_INTERVAL_S: float = 1.0
_RING_WINDOW_S: float = 300.0  # 5 minutes

# Tracks active Arena WS connections for monitoring
_active_connections: set[WebSocket] = set()


def get_active_arena_connections() -> set[WebSocket]:
    """Return the set of active Arena WebSocket connections."""
    return _active_connections


# ---------------------------------------------------------------------------
# Message builders (pure functions — easy to unit-test)
# ---------------------------------------------------------------------------


def build_arena_tick(
    event: PositionUpdatedEvent,
    trailing_stop_price: float,
) -> dict[str, Any]:
    """Build an arena_tick message from a PositionUpdatedEvent.

    Args:
        event: The position update event.
        trailing_stop_price: Current trail stop price from OrderManager.

    Returns:
        arena_tick message dict.
    """
    return {
        "type": "arena_tick",
        "symbol": event.symbol,
        "price": event.current_price,
        "unrealized_pnl": event.unrealized_pnl,
        "r_multiple": event.r_multiple,
        "trailing_stop_price": trailing_stop_price,
    }


def build_arena_candle(event: CandleEvent) -> dict[str, Any]:
    """Build an arena_candle message from a CandleEvent.

    Args:
        event: The candle event.

    Returns:
        arena_candle message dict.
    """
    return {
        "type": "arena_candle",
        "symbol": event.symbol,
        "time": event.timestamp.isoformat(),
        "open": event.open,
        "high": event.high,
        "low": event.low,
        "close": event.close,
        "volume": event.volume,
    }


def build_arena_position_opened(event: PositionOpenedEvent) -> dict[str, Any]:
    """Build an arena_position_opened message from a PositionOpenedEvent.

    Args:
        event: The position opened event.

    Returns:
        arena_position_opened message dict.
    """
    return {
        "type": "arena_position_opened",
        "symbol": event.symbol,
        "strategy_id": event.strategy_id,
        "entry_price": event.entry_price,
        "stop_price": event.stop_price,
        "target_prices": list(event.target_prices),
        "side": "long",
        "shares": event.shares,
        "entry_time": event.timestamp.isoformat(),
    }


def build_arena_position_closed(
    event: PositionClosedEvent,
    r_multiple: float,
) -> dict[str, Any]:
    """Build an arena_position_closed message from a PositionClosedEvent.

    Args:
        event: The position closed event.
        r_multiple: Computed R-multiple for this position.

    Returns:
        arena_position_closed message dict.
    """
    return {
        "type": "arena_position_closed",
        "symbol": event.symbol,
        "strategy_id": event.strategy_id,
        "exit_price": event.exit_price,
        "pnl": event.realized_pnl,
        "r_multiple": r_multiple,
        "exit_reason": event.exit_reason.value,
    }


def build_arena_stats(
    position_count: int,
    total_pnl: float,
    net_r: float,
    entries_5m: int,
    exits_5m: int,
) -> dict[str, Any]:
    """Build an arena_stats message.

    Args:
        position_count: Current number of open positions.
        total_pnl: Sum of unrealized P&L across open positions.
        net_r: Sum of current R-multiples across open positions.
        entries_5m: Number of position opens in the last 5 minutes.
        exits_5m: Number of position closes in the last 5 minutes.

    Returns:
        arena_stats message dict.
    """
    return {
        "type": "arena_stats",
        "position_count": position_count,
        "total_pnl": total_pnl,
        "net_r": net_r,
        "entries_5m": entries_5m,
        "exits_5m": exits_5m,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def compute_r_multiple(
    entry_price: float,
    stop_price: float,
    exit_price: float,
) -> float:
    """Compute R-multiple from entry, stop, and exit prices.

    Args:
        entry_price: Position entry fill price.
        stop_price: Original stop-loss price.
        exit_price: Position exit price.

    Returns:
        R-multiple (positive = profit, negative = loss). Zero if risk is
        negligible (avoids division by near-zero).
    """
    risk = entry_price - stop_price
    if abs(risk) < 0.001:
        return 0.0
    return (exit_price - entry_price) / abs(risk)



def _prune_ring_buffer(buf: deque[float], cutoff: float) -> None:
    """Remove timestamps older than cutoff from the front of the deque.

    Args:
        buf: Deque of monotonic timestamps.
        cutoff: Timestamps before this value are discarded.
    """
    while buf and buf[0] < cutoff:
        buf.popleft()


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@arena_ws_router.websocket("/ws/v1/arena")
async def arena_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for real-time Arena position streaming.

    Protocol:
    1. Client sends: {type: "auth", token: "<JWT>"}
    2. Server validates JWT, closes with 4001 if invalid
    3. Server streams arena_tick, arena_candle, arena_position_opened,
       arena_position_closed on matching Event Bus events; arena_stats
       every 1 second via asyncio timer.

    CandleEvent messages are filtered to symbols with open managed
    positions only.  Subscriptions are cleaned up on client disconnect.
    """
    await websocket.accept()
    _active_connections.add(websocket)

    try:
        app_state: AppState = websocket.app.state.app_state

        # --- Auth handshake ---------------------------------------------------
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

        if auth_data.get("type") != "auth":
            await websocket.close(code=4001)
            return

        token = auth_data.get("token")
        if not token:
            await websocket.close(code=4001)
            return

        try:
            jwt_secret = get_jwt_secret()
            jwt.decode(token, jwt_secret, algorithms=["HS256"])
        except Exception:
            await websocket.close(code=4001)
            return

        await websocket.send_json({
            "type": "auth_success",
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # --- Per-connection state ---------------------------------------------
        event_bus: EventBus = app_state.event_bus
        order_manager: OrderManager = app_state.order_manager

        send_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=1000)
        # Symbols with currently open positions — used for CandleEvent filtering
        tracked_symbols: set[str] = set()
        # Cached entry/stop prices per symbol for r_multiple on close
        position_cache: dict[str, dict[str, float]] = {}
        # Tracked unrealized P&L and R per symbol for stats
        unrealized_pnl_map: dict[str, float] = {}
        r_multiple_map: dict[str, float] = {}
        # Cached trail stop price per symbol — updated at 1 Hz from on_position_updated
        trail_stop_cache: dict[str, float] = {}
        # Ring buffers: monotonic timestamps of recent opens/closes
        recent_entries: deque[float] = deque()
        recent_exits: deque[float] = deque()

        # Seed from currently open positions so mid-session clients are current
        for pos in order_manager.get_all_positions_flat():
            if not pos.is_fully_closed:
                tracked_symbols.add(pos.symbol)
                position_cache[pos.symbol] = {
                    "entry_price": pos.entry_price,
                    "stop_price": pos.original_stop_price,
                }

        def _enqueue(msg: dict[str, Any]) -> None:
            try:
                send_queue.put_nowait(msg)
            except asyncio.QueueFull:
                # Client is too slow — drain and replace with state_desync
                # so the client reconnects/refreshes instead of drifting.
                logger.warning(
                    "Arena WS send queue full, signalling state_desync "
                    "(dropped %s for %s)",
                    msg.get("type"),
                    msg.get("symbol", ""),
                )
                while not send_queue.empty():
                    try:
                        send_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                try:
                    send_queue.put_nowait(
                        {
                            "type": "state_desync",
                            "reason": "send_queue_full",
                            "dropped_type": msg.get("type"),
                        }
                    )
                except asyncio.QueueFull:
                    logger.error(
                        "Failed to enqueue Arena state_desync marker"
                    )

        # --- Event handlers ---------------------------------------------------

        async def on_position_updated(event: PositionUpdatedEvent) -> None:
            if event.symbol not in tracked_symbols:
                return
            unrealized_pnl_map[event.symbol] = event.unrealized_pnl
            r_multiple_map[event.symbol] = event.r_multiple
            trail = 0.0
            for pos in order_manager.get_all_positions_flat():
                if pos.symbol == event.symbol and not pos.is_fully_closed:
                    trail = pos.trail_stop_price
                    break
            trail_stop_cache[event.symbol] = trail
            _enqueue(build_arena_tick(event, trail))

        async def on_tick(event: TickEvent) -> None:
            if event.symbol not in tracked_symbols:
                return
            _enqueue({
                "type": "arena_tick_price",
                "symbol": event.symbol,
                "price": event.price,
                "timestamp": event.timestamp.isoformat(),
            })

        async def on_candle(event: CandleEvent) -> None:
            if event.symbol not in tracked_symbols:
                return
            _enqueue(build_arena_candle(event))

        async def on_position_opened(event: PositionOpenedEvent) -> None:
            tracked_symbols.add(event.symbol)
            position_cache[event.symbol] = {
                "entry_price": event.entry_price,
                "stop_price": event.stop_price,
            }
            recent_entries.append(time.monotonic())
            _enqueue(build_arena_position_opened(event))

        async def on_position_closed(event: PositionClosedEvent) -> None:
            tracked_symbols.discard(event.symbol)
            unrealized_pnl_map.pop(event.symbol, None)
            r_multiple_map.pop(event.symbol, None)
            recent_exits.append(time.monotonic())
            cached = position_cache.pop(event.symbol, None)
            r_multiple = 0.0
            if cached:
                r_multiple = compute_r_multiple(
                    cached["entry_price"],
                    cached["stop_price"],
                    event.exit_price,
                )
            _enqueue(build_arena_position_closed(event, r_multiple))

        # --- Subscribe --------------------------------------------------------
        event_bus.subscribe(PositionUpdatedEvent, on_position_updated)
        event_bus.subscribe(CandleEvent, on_candle)
        event_bus.subscribe(PositionOpenedEvent, on_position_opened)
        event_bus.subscribe(PositionClosedEvent, on_position_closed)
        event_bus.subscribe(TickEvent, on_tick)

        # --- Stats timer task -------------------------------------------------
        async def stats_loop() -> None:
            while True:
                await asyncio.sleep(_STATS_INTERVAL_S)
                now = time.monotonic()
                cutoff = now - _RING_WINDOW_S
                _prune_ring_buffer(recent_entries, cutoff)
                _prune_ring_buffer(recent_exits, cutoff)
                total_pnl = sum(unrealized_pnl_map.values())
                net_r = sum(r_multiple_map.values())
                _enqueue(build_arena_stats(
                    position_count=len(tracked_symbols),
                    total_pnl=total_pnl,
                    net_r=net_r,
                    entries_5m=len(recent_entries),
                    exits_5m=len(recent_exits),
                ))

        stats_task: asyncio.Task[None] = asyncio.create_task(stats_loop())

        # --- Sender task ------------------------------------------------------
        async def sender() -> None:
            try:
                while True:
                    msg = await send_queue.get()
                    await websocket.send_json(msg)
            except Exception:
                pass

        sender_task: asyncio.Task[None] = asyncio.create_task(sender())

        # --- Receive loop (keep connection alive, handle pings) ---------------
        try:
            while True:
                try:
                    await websocket.receive_json()
                except WebSocketDisconnect:
                    break
        except Exception:
            logger.debug("Arena WS receive loop ended")
        finally:
            # Unsubscribe before cancelling tasks to prevent queuing after cleanup
            event_bus.unsubscribe(PositionUpdatedEvent, on_position_updated)
            event_bus.unsubscribe(CandleEvent, on_candle)
            event_bus.unsubscribe(PositionOpenedEvent, on_position_opened)
            event_bus.unsubscribe(PositionClosedEvent, on_position_closed)
            event_bus.unsubscribe(TickEvent, on_tick)

            stats_task.cancel()
            sender_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stats_task
            with contextlib.suppress(asyncio.CancelledError):
                await sender_task

    except asyncio.TimeoutError:
        await websocket.close(code=4001)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Arena WebSocket error: %s", exc)
        with contextlib.suppress(Exception):
            await websocket.close()
    finally:
        _active_connections.discard(websocket)
