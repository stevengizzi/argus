"""Orchestrator routes for the Command Center API.

Provides endpoints for viewing orchestrator status, decisions history,
and triggering manual rebalance.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter(tags=["orchestrator"])


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class AllocationInfo(BaseModel):
    """Information about a single strategy allocation."""

    strategy_id: str
    allocation_pct: float
    allocation_dollars: float
    throttle_action: str
    eligible: bool
    reason: str


class OrchestratorStatusResponse(BaseModel):
    """Orchestrator status response."""

    regime: str
    regime_indicators: dict[str, float]
    regime_updated_at: str | None
    allocations: list[AllocationInfo]
    cash_reserve_pct: float
    total_deployed_pct: float
    next_regime_check: str | None
    timestamp: str


class DecisionInfo(BaseModel):
    """Information about a single orchestrator decision."""

    id: str
    date: str
    decision_type: str
    strategy_id: str | None
    details: dict[str, Any] | None
    rationale: str | None
    created_at: str


class DecisionsResponse(BaseModel):
    """Paginated orchestrator decisions response."""

    decisions: list[DecisionInfo]
    total: int
    limit: int
    offset: int
    timestamp: str


class RebalanceResponse(BaseModel):
    """Response from manual rebalance operation."""

    success: bool
    message: str
    regime: str
    allocations: list[AllocationInfo]
    timestamp: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/status", response_model=OrchestratorStatusResponse)
async def get_orchestrator_status(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> OrchestratorStatusResponse:
    """Get current orchestrator status including regime, indicators, and allocations.

    Returns:
        OrchestratorStatusResponse with current state.

    Raises:
        HTTPException: 503 if orchestrator is not available.
    """
    if state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available",
        )

    orchestrator = state.orchestrator

    # Build allocations list
    allocations: list[AllocationInfo] = []
    total_deployed = 0.0

    for strategy_id, alloc in orchestrator.current_allocations.items():
        allocations.append(
            AllocationInfo(
                strategy_id=strategy_id,
                allocation_pct=alloc.allocation_pct,
                allocation_dollars=alloc.allocation_dollars,
                throttle_action=alloc.throttle_action.value,
                eligible=alloc.eligible,
                reason=alloc.reason,
            )
        )
        total_deployed += alloc.allocation_pct

    # Get regime indicators
    indicators: dict[str, float] = {}
    if orchestrator.current_indicators is not None:
        indicators = {
            "spy_price": orchestrator.current_indicators.spy_price,
            "spy_sma_20": orchestrator.current_indicators.spy_sma_20 or 0.0,
            "spy_sma_50": orchestrator.current_indicators.spy_sma_50 or 0.0,
            "spy_roc_5d": orchestrator.current_indicators.spy_roc_5d or 0.0,
            "spy_realized_vol_20d": orchestrator.current_indicators.spy_realized_vol_20d or 0.0,
        }

    # Determine next regime check time
    next_check: str | None = None
    if orchestrator._last_regime_check and orchestrator._config.regime_check_interval_minutes:
        from datetime import timedelta

        next_dt = orchestrator._last_regime_check + timedelta(
            minutes=orchestrator._config.regime_check_interval_minutes
        )
        next_check = next_dt.isoformat()

    return OrchestratorStatusResponse(
        regime=orchestrator.current_regime.value,
        regime_indicators=indicators,
        regime_updated_at=(
            orchestrator._last_regime_check.isoformat()
            if orchestrator._last_regime_check
            else None
        ),
        allocations=allocations,
        cash_reserve_pct=orchestrator._config.cash_reserve_pct,
        total_deployed_pct=total_deployed,
        next_regime_check=next_check,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/decisions", response_model=DecisionsResponse)
async def get_orchestrator_decisions(
    limit: int = 50,
    offset: int = 0,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> DecisionsResponse:
    """Get paginated orchestrator decision history.

    Args:
        limit: Maximum number of decisions to return (default 50).
        offset: Number of decisions to skip for pagination.

    Returns:
        DecisionsResponse with decisions list and pagination info.
    """
    decisions, total = await state.trade_logger.get_orchestrator_decisions(
        limit=limit, offset=offset
    )

    decision_infos = [
        DecisionInfo(
            id=d["id"],
            date=d["date"],
            decision_type=d["decision_type"],
            strategy_id=d.get("strategy_id"),
            details=d.get("details"),
            rationale=d.get("rationale"),
            created_at=d["created_at"],
        )
        for d in decisions
    ]

    return DecisionsResponse(
        decisions=decision_infos,
        total=total,
        limit=limit,
        offset=offset,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.post("/rebalance", response_model=RebalanceResponse)
async def trigger_rebalance(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> RebalanceResponse:
    """Trigger manual rebalance of strategy allocations.

    Forces the orchestrator to recalculate allocations based on current
    account state and performance metrics.

    Returns:
        RebalanceResponse with new allocations.

    Raises:
        HTTPException: 503 if orchestrator is not available.
        HTTPException: 500 if rebalance fails.
    """
    if state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available",
        )

    try:
        new_allocations = await state.orchestrator.manual_rebalance()
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Rebalance failed: {e}",
        ) from e

    allocations = [
        AllocationInfo(
            strategy_id=alloc.strategy_id,
            allocation_pct=alloc.allocation_pct,
            allocation_dollars=alloc.allocation_dollars,
            throttle_action=alloc.throttle_action.value,
            eligible=alloc.eligible,
            reason=alloc.reason,
        )
        for alloc in new_allocations.values()
    ]

    return RebalanceResponse(
        success=True,
        message="Rebalance completed successfully",
        regime=state.orchestrator.current_regime.value,
        allocations=allocations,
        timestamp=datetime.now(UTC).isoformat(),
    )
