"""Configuration routes for the Command Center API.

Provides endpoints for reading configuration values.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class GoalsConfigResponse(BaseModel):
    """Response for goals configuration."""

    monthly_target_usd: float
    timestamp: str


@router.get("/goals", response_model=GoalsConfigResponse)
async def get_goals_config(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> GoalsConfigResponse:
    """Get goal tracking configuration.

    Returns the monthly target and other goal-related settings
    used by the GoalTracker dashboard widget.

    Returns:
        GoalsConfigResponse with monthly_target_usd.
    """
    monthly_target = 5000.0  # Default
    if state.config and hasattr(state.config, "goals") and state.config.goals:
        monthly_target = state.config.goals.monthly_target_usd

    return GoalsConfigResponse(
        monthly_target_usd=monthly_target,
        timestamp=datetime.now(UTC).isoformat(),
    )
