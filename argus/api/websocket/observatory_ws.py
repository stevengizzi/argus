"""WebSocket handler for Observatory live pipeline updates.

Pushes real-time pipeline stage counts, tier transition events, and
evaluation summary updates at a configurable interval.  Authentication
via JWT token in first message (same pattern as ai_chat.py).

Sprint 25, Session 2.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import JWTError, jwt

from argus.api.auth import get_jwt_secret
from argus.api.dependencies import AppState

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)

observatory_ws_router = APIRouter(tags=["observatory-websocket"])

_active_connections: set[WebSocket] = set()


def get_active_observatory_connections() -> set[WebSocket]:
    """Get the set of active Observatory WebSocket connections."""
    return _active_connections


@observatory_ws_router.websocket("/ws/v1/observatory")
async def observatory_websocket(websocket: WebSocket) -> None:
    """WebSocket endpoint for live Observatory pipeline updates.

    Protocol:
    1. Client sends: {type: "auth", token: "<JWT>"}
    2. Server validates JWT, closes with 4001 if invalid
    3. Server pushes: pipeline_update, tier_transition, evaluation_summary
       at the configured interval until client disconnects.
    """
    await websocket.accept()
    _active_connections.add(websocket)

    try:
        app_state: AppState = websocket.app.state.app_state

        # Wait for auth message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)

        if auth_data.get("type") != "auth":
            await websocket.close(code=4001)
            return

        token = auth_data.get("token")
        if not token:
            await websocket.close(code=4001)
            return

        # Validate JWT
        try:
            jwt_secret = get_jwt_secret()
            jwt.decode(token, jwt_secret, algorithms=["HS256"])
        except (JWTError, Exception):
            await websocket.close(code=4001)
            return

        # Send auth success
        await websocket.send_json({
            "type": "auth_success",
            "timestamp": datetime.now(UTC).isoformat(),
        })

        # Resolve push interval from config
        interval_ms = 1000
        if (
            app_state.config is not None
            and app_state.config.observatory is not None
        ):
            interval_ms = app_state.config.observatory.ws_update_interval_ms
        interval_s = interval_ms / 1000.0

        observatory_service = app_state.observatory_service

        if observatory_service is None:
            await websocket.send_json({
                "type": "error",
                "message": "Observatory service not available",
            })
            await websocket.close(code=4002)
            return

        # Send initial full state
        initial_pipeline = await observatory_service.get_pipeline_stages()
        await websocket.send_json({
            "type": "pipeline_update",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": initial_pipeline,
        })

        # Track previous symbol tiers for transition detection
        previous_tiers = await observatory_service.get_symbol_tiers()

        # Track previous evaluation counts for summary delta
        previous_summary = await observatory_service.get_session_summary()
        previous_eval_count = previous_summary.get("total_evaluations", 0)
        previous_signal_count = previous_summary.get("total_signals", 0)

        # Push loop
        while True:
            await asyncio.sleep(interval_s)

            push_start = time.monotonic()

            try:
                # Gather pipeline data and symbol tiers
                pipeline_data = await observatory_service.get_pipeline_stages()
                current_tiers = await observatory_service.get_symbol_tiers()
                current_summary = await observatory_service.get_session_summary()
            except Exception as exc:
                logger.warning("Observatory WS query failed: %s", exc)
                # If query takes too long, skip this interval
                continue

            elapsed = time.monotonic() - push_start
            if elapsed > interval_s:
                logger.debug(
                    "Observatory WS query took %.1fms (interval %.0fms), skipping push",
                    elapsed * 1000,
                    interval_ms,
                )
                # Update tracked state even on skip so next diff is accurate
                previous_tiers = current_tiers
                previous_eval_count = current_summary.get("total_evaluations", 0)
                previous_signal_count = current_summary.get("total_signals", 0)
                continue

            now_iso = datetime.now(UTC).isoformat()

            # 1. Pipeline update
            await websocket.send_json({
                "type": "pipeline_update",
                "timestamp": now_iso,
                "data": pipeline_data,
            })

            # 2. Tier transitions
            transitions = _detect_tier_transitions(previous_tiers, current_tiers)
            for transition in transitions:
                await websocket.send_json({
                    "type": "tier_transition",
                    "timestamp": now_iso,
                    "data": transition,
                })

            # 3. Evaluation summary
            current_eval_count = current_summary.get("total_evaluations", 0)
            current_signal_count = current_summary.get("total_signals", 0)

            # Find new near-triggers by comparing tiers
            new_near_triggers = [
                {"symbol": sym, "tier": tier}
                for sym, tier in current_tiers.items()
                if tier == "near_trigger"
                and previous_tiers.get(sym) != "near_trigger"
            ]

            # Read regime vector summary from orchestrator if available
            regime_vector_summary = None
            if (
                app_state.orchestrator is not None
                and hasattr(app_state.orchestrator, "latest_regime_vector_summary")
            ):
                regime_vector_summary = app_state.orchestrator.latest_regime_vector_summary

            await websocket.send_json({
                "type": "evaluation_summary",
                "timestamp": now_iso,
                "data": {
                    "evaluations_count": current_eval_count - previous_eval_count,
                    "signals_count": current_signal_count - previous_signal_count,
                    "new_near_triggers": new_near_triggers,
                    "regime_vector_summary": regime_vector_summary,
                },
            })

            # Update tracked state for next interval
            previous_tiers = current_tiers
            previous_eval_count = current_eval_count
            previous_signal_count = current_signal_count

    except asyncio.TimeoutError:
        await websocket.close(code=4001)
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.warning("Observatory WebSocket error: %s", exc)
        try:
            await websocket.close()
        except Exception:
            pass
    finally:
        _active_connections.discard(websocket)


def _detect_tier_transitions(
    previous: dict[str, str],
    current: dict[str, str],
) -> list[dict[str, str]]:
    """Compare two tier snapshots and return transition events.

    Args:
        previous: Previous interval's symbol->tier mapping.
        current: Current interval's symbol->tier mapping.

    Returns:
        List of {symbol, from_tier, to_tier} dicts for changed symbols.
    """
    transitions: list[dict[str, str]] = []
    all_symbols = set(previous) | set(current)

    for symbol in all_symbols:
        prev_tier = previous.get(symbol)
        curr_tier = current.get(symbol)
        if prev_tier != curr_tier and prev_tier is not None and curr_tier is not None:
            transitions.append({
                "symbol": symbol,
                "from_tier": prev_tier,
                "to_tier": curr_tier,
            })

    return transitions
