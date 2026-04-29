"""Health and status routes for the Command Center API.

Provides endpoints for system health, component status, and diagnostics.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.core.config import BrokerSource

router = APIRouter()


class ComponentStatusResponse(BaseModel):
    """Status of a single system component."""

    status: str
    details: str


class EvaluationDbHealth(BaseModel):
    """Sprint 31.915 (DEF-233): observability subfield for ``data/evaluation.db``.

    All four fields are nullable so the endpoint stays well-formed when
    the EvaluationEventStore has not been registered with HealthMonitor
    (test fixtures, boot race before phase 10.3) or before the first
    retention iteration has fired (fresh boot).
    """

    size_mb: float | None
    last_retention_run_at_et: str | None
    last_retention_deleted_count: int | None
    freelist_pct: float | None


class HealthResponse(BaseModel):
    """System health response."""

    status: str
    uptime_seconds: int
    components: dict[str, ComponentStatusResponse]
    last_heartbeat: str | None
    last_trade: str | None
    last_data_received: str | None
    paper_mode: bool
    timestamp: str
    evaluation_db: EvaluationDbHealth


@router.get("", response_model=HealthResponse)
async def get_health(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> HealthResponse:
    """Get system health status and diagnostics.

    Returns overall system health including:
    - Overall status (healthy, degraded, unhealthy)
    - Uptime in seconds
    - Per-component status
    - Timestamps for last heartbeat, trade, and data
    - Paper mode indicator
    """
    # Get overall status from health monitor
    overall_status = state.health_monitor.get_overall_status()

    # Calculate uptime
    uptime_seconds = int(time.time() - state.start_time)

    # Get component statuses
    component_healths = state.health_monitor.get_status()
    components: dict[str, ComponentStatusResponse] = {}
    for name, health in component_healths.items():
        components[name] = ComponentStatusResponse(
            status=health.status.value,
            details=health.message,
        )

    # Get last heartbeat time from health monitor's last update
    last_heartbeat: str | None = None
    # Look for any component's last_updated as proxy for heartbeat
    if component_healths:
        latest = max(h.last_updated for h in component_healths.values())
        last_heartbeat = latest.isoformat()

    # Get last trade from trade logger
    last_trade: str | None = None
    trades = await state.trade_logger.query_trades(limit=1)
    if trades:
        # exit_time is the most recent trade's end time
        exit_time = trades[0].get("exit_time")
        if exit_time:
            last_trade = exit_time if isinstance(exit_time, str) else str(exit_time)

    # Get last data received from data service if available
    last_data_received: str | None = None
    if state.data_service is not None:
        # Check if data_service has a last_update attribute
        last_update = getattr(state.data_service, "last_update", None)
        if last_update is not None:
            if isinstance(last_update, datetime):
                last_data_received = last_update.isoformat()
            else:
                last_data_received = str(last_update)

    # Determine paper mode from config
    paper_mode = True  # Default to paper mode
    if state.config:
        # IBKR is the only live broker; Alpaca and Simulated are paper/test
        paper_mode = state.config.broker_source != BrokerSource.IBKR

    # Sprint 31.915 (DEF-233): pull evaluation_db observability subfield.
    eval_db_payload = await state.health_monitor.get_evaluation_db_health()

    return HealthResponse(
        status=overall_status.value,
        uptime_seconds=uptime_seconds,
        components=components,
        last_heartbeat=last_heartbeat,
        last_trade=last_trade,
        last_data_received=last_data_received,
        paper_mode=paper_mode,
        timestamp=datetime.now(UTC).isoformat(),
        evaluation_db=EvaluationDbHealth(**eval_db_payload),
    )
