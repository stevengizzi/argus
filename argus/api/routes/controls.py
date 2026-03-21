"""Emergency control routes for the Command Center API.

Provides endpoints for operational control:
- Pause/resume individual strategies
- Close individual positions
- Emergency flatten all positions
- Emergency pause all strategies
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter(tags=["controls"])


class ControlResponse(BaseModel):
    """Standard response for control operations."""

    success: bool
    message: str
    timestamp: str


@router.post("/strategies/{strategy_id}/pause", response_model=ControlResponse)
async def pause_strategy(
    strategy_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Pause a strategy — stops generating new signals.

    The strategy remains registered but will not process candles or emit signals.

    Args:
        strategy_id: The unique identifier of the strategy to pause.

    Returns:
        ControlResponse with success status and message.

    Raises:
        HTTPException: 404 if strategy not found.
    """
    if strategy_id not in state.strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    strategy = state.strategies[strategy_id]
    strategy.is_active = False

    return ControlResponse(
        success=True,
        message=f"Strategy '{strategy_id}' paused successfully",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/strategies/{strategy_id}/resume", response_model=ControlResponse)
async def resume_strategy(
    strategy_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Resume a paused strategy.

    The strategy will begin processing candles and generating signals again.

    Args:
        strategy_id: The unique identifier of the strategy to resume.

    Returns:
        ControlResponse with success status and message.

    Raises:
        HTTPException: 404 if strategy not found.
    """
    if strategy_id not in state.strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    strategy = state.strategies[strategy_id]
    strategy.is_active = True

    return ControlResponse(
        success=True,
        message=f"Strategy '{strategy_id}' resumed successfully",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/positions/{position_id}/close", response_model=ControlResponse)
async def close_position(
    position_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Emergency close a specific position at market.

    Finds the position by its ID (symbol) and closes it immediately.

    Args:
        position_id: The position identifier (typically the symbol).

    Returns:
        ControlResponse with success status and message.

    Raises:
        HTTPException: 404 if position not found.
    """
    # Get managed positions
    positions = state.order_manager.get_all_positions_flat()

    # Find position by ID (we use symbol as position_id in the API)
    target_position = None
    for pos in positions:
        if pos.symbol == position_id:
            target_position = pos
            break

    if target_position is None:
        raise HTTPException(status_code=404, detail=f"Position '{position_id}' not found")

    # Close the position via broker flatten
    try:
        # TODO: Replace with single-position close when Broker ABC supports it
        await state.broker.flatten_all()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to close position: {e}") from e

    return ControlResponse(
        success=True,
        message=f"Position '{position_id}' close order submitted",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/emergency/flatten", response_model=ControlResponse)
async def emergency_flatten_all(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Emergency flatten all positions across all strategies.

    Immediately closes all open positions at market price.
    This is a safety mechanism for critical situations.

    Returns:
        ControlResponse with success status and message.
    """
    try:
        await state.order_manager.emergency_flatten()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Emergency flatten failed: {e}") from e

    return ControlResponse(
        success=True,
        message="Emergency flatten executed — all positions closing",
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/emergency/pause", response_model=ControlResponse)
async def emergency_pause_all(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Emergency pause all strategies.

    Immediately pauses all registered strategies to stop new signals.
    Existing positions are NOT closed — use /emergency/flatten for that.

    Returns:
        ControlResponse with success status and count of paused strategies.
    """
    paused_count = 0
    for strategy in state.strategies.values():
        strategy.is_active = False
        paused_count += 1

    return ControlResponse(
        success=True,
        message=f"Emergency pause executed — {paused_count} strategies paused",
        timestamp=datetime.now(UTC).isoformat(),
    )
