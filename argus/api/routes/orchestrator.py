"""Orchestrator routes for the Command Center API.

Provides endpoints for viewing orchestrator status, decisions history,
and triggering manual rebalance.
"""

from __future__ import annotations

from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.api.routes.controls import ControlResponse

router = APIRouter(tags=["orchestrator"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_session_phase() -> str:
    """Compute current session phase from ET time.

    Returns one of:
    - pre_market: before 9:30
    - market_open: 9:30-11:30
    - midday: 11:30-14:00
    - power_hour: 14:00-16:00
    - after_hours: 16:00-20:00
    - market_closed: after 20:00 or weekends
    """
    now_et = datetime.now(ZoneInfo("America/New_York"))
    t = now_et.time()
    weekday = now_et.weekday()

    if weekday >= 5:  # Weekend
        return "market_closed"
    if t < time(9, 30):
        return "pre_market"
    if t < time(11, 30):
        return "market_open"
    if t < time(14, 0):
        return "midday"
    if t < time(16, 0):
        return "power_hour"
    if t < time(20, 0):
        return "after_hours"
    return "market_closed"


# Strategy operating windows (hardcoded for V1, could read from YAML later)
STRATEGY_WINDOWS: dict[str, dict[str, str]] = {
    "orb_breakout": {"earliest_entry": "09:35", "latest_entry": "11:30", "force_close": "15:50"},
    "orb_scalp": {"earliest_entry": "09:45", "latest_entry": "11:30", "force_close": "15:50"},
    "vwap_reclaim": {"earliest_entry": "10:00", "latest_entry": "12:00", "force_close": "15:50"},
    "afternoon_momentum": {
        "earliest_entry": "14:00",
        "latest_entry": "15:30",
        "force_close": "15:45",
    },
}


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------


class OperatingWindow(BaseModel):
    """Strategy operating window times."""

    earliest_entry: str  # "09:35"
    latest_entry: str  # "11:30"
    force_close: str  # "15:50"


class AllocationInfo(BaseModel):
    """Information about a single strategy allocation."""

    strategy_id: str
    allocation_pct: float
    allocation_dollars: float
    throttle_action: str
    eligible: bool
    reason: str
    # Deployment state (Sprint 18.75)
    deployed_capital: float
    deployed_pct: float
    is_throttled: bool
    # Extended fields (Sprint 21b)
    operating_window: OperatingWindow | None = None
    consecutive_losses: int = 0
    rolling_sharpe: float | None = None
    drawdown_pct: float = 0.0
    is_active: bool = True
    health_status: str = "healthy"
    trade_count_today: int = 0
    daily_pnl: float = 0.0
    open_position_count: int = 0
    override_active: bool = False
    override_until: str | None = None


class OrchestratorStatusResponse(BaseModel):
    """Orchestrator status response."""

    regime: str
    regime_indicators: dict[str, float]
    regime_updated_at: str | None
    allocations: list[AllocationInfo]
    cash_reserve_pct: float
    total_deployed_pct: float
    next_regime_check: str | None
    # Deployment state (Sprint 18.75)
    total_deployed_capital: float
    total_equity: float
    # Extended fields (Sprint 21b)
    session_phase: str
    pre_market_complete: bool
    pre_market_completed_at: str | None
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


class ThrottleOverrideRequest(BaseModel):
    """Request body for throttle override operation."""

    duration_minutes: int  # 30, 60, or 999 (rest of day)
    reason: str


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
        OrchestratorStatusResponse with current state including deployment data.

    Raises:
        HTTPException: 503 if orchestrator is not available.
    """
    from datetime import timedelta

    if state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available",
        )

    orchestrator = state.orchestrator

    # Get total equity from broker
    account_info = await state.broker.get_account()
    total_equity = account_info.equity

    # Compute deployed capital and open position count per strategy from open positions
    deployed_by_strategy: dict[str, float] = {}
    position_count_by_strategy: dict[str, int] = {}
    if state.order_manager is not None:
        all_positions = state.order_manager.get_all_positions_flat()
        for pos in all_positions:
            if not pos.is_fully_closed:
                capital = pos.entry_price * pos.shares_remaining
                deployed_by_strategy[pos.strategy_id] = (
                    deployed_by_strategy.get(pos.strategy_id, 0.0) + capital
                )
                position_count_by_strategy[pos.strategy_id] = (
                    position_count_by_strategy.get(pos.strategy_id, 0) + 1
                )

    total_deployed_capital = sum(deployed_by_strategy.values())

    # Compute session phase
    session_phase = _compute_session_phase()

    # Get pre_market_complete
    pre_market_complete = getattr(orchestrator, "pre_market_complete", True)

    # Find pre_market_completed_at from today's regime_classification decision
    pre_market_completed_at: str | None = None
    et_tz = ZoneInfo("America/New_York")
    today_et = datetime.now(et_tz).date().isoformat()
    decisions, _ = await state.trade_logger.get_orchestrator_decisions(
        limit=50, offset=0, decision_type="regime_classification", date=today_et
    )
    if decisions:
        # Get the earliest regime_classification decision today
        earliest = min(decisions, key=lambda d: d["created_at"])
        pre_market_completed_at = earliest["created_at"]

    # Build allocations list with extended data
    allocations: list[AllocationInfo] = []
    total_deployed_pct = 0.0

    for strategy_id, alloc in orchestrator.current_allocations.items():
        deployed_capital = deployed_by_strategy.get(strategy_id, 0.0)
        deployed_pct = deployed_capital / total_equity if total_equity > 0 else 0.0
        is_throttled = alloc.throttle_action.value == "suspend"

        # Get operating window
        op_window: OperatingWindow | None = None
        if strategy_id in STRATEGY_WINDOWS:
            window = STRATEGY_WINDOWS[strategy_id]
            op_window = OperatingWindow(
                earliest_entry=window["earliest_entry"],
                latest_entry=window["latest_entry"],
                force_close=window["force_close"],
            )

        # Get strategy-specific data
        strategy = state.strategies.get(strategy_id)
        is_active = True
        trade_count_today = 0
        daily_pnl = 0.0

        if strategy is not None:
            is_active = getattr(strategy, "is_active", True)
            trade_count_today = getattr(strategy, "_trade_count_today", 0)
            daily_pnl = getattr(strategy, "_daily_pnl", 0.0)

        # Get health status from health monitor
        health_status = "healthy"
        if state.health_monitor is not None:
            component_name = f"strategy_{strategy_id}"
            components = state.health_monitor.get_status()
            if component_name in components:
                status_value = components[component_name].status.value
                if status_value in ("unhealthy", "stopped"):
                    health_status = "error"
                elif status_value == "degraded":
                    health_status = "warning"

        # Compute throttle metrics from trade history
        consecutive_losses = 0
        rolling_sharpe: float | None = None
        drawdown_pct = 0.0

        try:
            trades = await state.trade_logger.get_trades_by_strategy(strategy_id, limit=20)
            # Count consecutive losses from most recent trade
            for trade in trades:
                if trade.net_pnl < 0:
                    consecutive_losses += 1
                else:
                    break

            # Get daily P&L for rolling Sharpe and drawdown
            daily_pnl_data = await state.trade_logger.get_daily_pnl(strategy_id=strategy_id)
            if len(daily_pnl_data) >= 5:
                from argus.analytics.performance import compute_sharpe_ratio

                # daily_pnl_data is sorted descending (most recent first)
                # Take last 20 days and compute Sharpe
                recent_data = daily_pnl_data[:20]
                pnl_values = [entry.get("pnl", 0.0) for entry in reversed(recent_data)]
                if len(pnl_values) >= 2:
                    rolling_sharpe = compute_sharpe_ratio(pnl_values)

                # Compute drawdown from peak
                if daily_pnl_data:
                    chronological = list(reversed(daily_pnl_data))
                    cumulative = 0.0
                    peak = 0.0
                    current = 0.0
                    for entry in chronological:
                        cumulative += entry.get("pnl", 0.0)
                        current = cumulative
                        if cumulative > peak:
                            peak = cumulative
                    if peak > 0 and current < peak:
                        drawdown_pct = (peak - current) / peak
        except Exception:
            # If trade data unavailable, use defaults
            pass

        # Open position count
        open_position_count = position_count_by_strategy.get(strategy_id, 0)

        # Get override status
        override_active = False
        override_until_str: str | None = None
        if hasattr(orchestrator, "_is_override_active"):
            override_active = orchestrator._is_override_active(strategy_id)
            if override_active and hasattr(orchestrator, "_override_until"):
                expiry = orchestrator._override_until.get(strategy_id)
                if expiry is not None:
                    override_until_str = expiry.isoformat()

        allocations.append(
            AllocationInfo(
                strategy_id=strategy_id,
                allocation_pct=alloc.allocation_pct,
                allocation_dollars=alloc.allocation_dollars,
                throttle_action=alloc.throttle_action.value,
                eligible=alloc.eligible,
                reason=alloc.reason,
                deployed_capital=deployed_capital,
                deployed_pct=deployed_pct,
                is_throttled=is_throttled,
                operating_window=op_window,
                consecutive_losses=consecutive_losses,
                rolling_sharpe=rolling_sharpe,
                drawdown_pct=drawdown_pct,
                is_active=is_active,
                health_status=health_status,
                trade_count_today=trade_count_today,
                daily_pnl=daily_pnl,
                open_position_count=open_position_count,
                override_active=override_active,
                override_until=override_until_str,
            )
        )
        total_deployed_pct += deployed_pct

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
    if orchestrator.last_regime_check and orchestrator.regime_check_interval_minutes:
        next_dt = orchestrator.last_regime_check + timedelta(
            minutes=orchestrator.regime_check_interval_minutes
        )
        next_check = next_dt.isoformat()

    return OrchestratorStatusResponse(
        regime=orchestrator.current_regime.value,
        regime_indicators=indicators,
        regime_updated_at=(
            orchestrator.last_regime_check.isoformat() if orchestrator.last_regime_check else None
        ),
        allocations=allocations,
        cash_reserve_pct=orchestrator.cash_reserve_pct,
        total_deployed_pct=total_deployed_pct,
        next_regime_check=next_check,
        total_deployed_capital=total_deployed_capital,
        total_equity=total_equity,
        session_phase=session_phase,
        pre_market_complete=pre_market_complete,
        pre_market_completed_at=pre_market_completed_at,
        timestamp=datetime.now(UTC).isoformat(),
    )


@router.get("/decisions", response_model=DecisionsResponse)
async def get_orchestrator_decisions(
    limit: int = 50,
    offset: int = 0,
    date: str | None = None,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> DecisionsResponse:
    """Get paginated orchestrator decision history.

    Args:
        limit: Maximum number of decisions to return (default 50).
        offset: Number of decisions to skip for pagination.
        date: Optional date filter (ISO YYYY-MM-DD format). Defaults to today if not provided.

    Returns:
        DecisionsResponse with decisions list and pagination info.
    """
    # Default to today's date if not provided
    if date is None:
        et_tz = ZoneInfo("America/New_York")
        date = datetime.now(et_tz).date().isoformat()

    decisions, total = await state.trade_logger.get_orchestrator_decisions(
        limit=limit, offset=offset, date=date
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

    # Get total equity from broker
    account_info = await state.broker.get_account()
    total_equity = account_info.equity

    # Compute deployed capital per strategy from open positions
    deployed_by_strategy: dict[str, float] = {}
    if state.order_manager is not None:
        all_positions = state.order_manager.get_all_positions_flat()
        for pos in all_positions:
            if not pos.is_fully_closed:
                capital = pos.entry_price * pos.shares_remaining
                deployed_by_strategy[pos.strategy_id] = (
                    deployed_by_strategy.get(pos.strategy_id, 0.0) + capital
                )

    allocations = [
        AllocationInfo(
            strategy_id=alloc.strategy_id,
            allocation_pct=alloc.allocation_pct,
            allocation_dollars=alloc.allocation_dollars,
            throttle_action=alloc.throttle_action.value,
            eligible=alloc.eligible,
            reason=alloc.reason,
            deployed_capital=deployed_by_strategy.get(alloc.strategy_id, 0.0),
            deployed_pct=(
                deployed_by_strategy.get(alloc.strategy_id, 0.0) / total_equity
                if total_equity > 0
                else 0.0
            ),
            is_throttled=alloc.throttle_action.value == "suspend",
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


@router.post("/strategies/{strategy_id}/override-throttle", response_model=ControlResponse)
async def override_strategy_throttle(
    strategy_id: str,
    request: ThrottleOverrideRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> ControlResponse:
    """Temporarily override throttle for a strategy.

    Allows a throttled or suspended strategy to resume trading for a limited time.
    This is a manual override intended for operator intervention.

    Args:
        strategy_id: The unique identifier of the strategy to override.
        request: Override request with duration and reason.

    Returns:
        ControlResponse with success status and message.

    Raises:
        HTTPException: 404 if strategy not found.
        HTTPException: 503 if orchestrator is not available.
    """
    if state.orchestrator is None:
        raise HTTPException(
            status_code=503,
            detail="Orchestrator not available",
        )

    # Validate strategy exists
    if strategy_id not in state.strategies:
        raise HTTPException(status_code=404, detail=f"Strategy '{strategy_id}' not found")

    # Call orchestrator override
    await state.orchestrator.override_throttle(
        strategy_id=strategy_id,
        duration_minutes=request.duration_minutes,
        reason=request.reason,
    )

    return ControlResponse(
        success=True,
        message=(
            f"Throttle override for '{strategy_id}' active for "
            f"{request.duration_minutes} minutes"
        ),
        timestamp=datetime.now(UTC).isoformat(),
    )
