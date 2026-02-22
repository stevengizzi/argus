"""Strategy routes for the Command Center API.

Provides endpoints for viewing and managing trading strategies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class StrategyInfo(BaseModel):
    """Information about a single strategy."""

    strategy_id: str
    name: str
    version: str
    is_active: bool
    pipeline_stage: str
    allocated_capital: float
    daily_pnl: float
    trade_count_today: int
    open_positions: int
    config_summary: dict[str, Any]


class StrategiesResponse(BaseModel):
    """Strategies list response."""

    strategies: list[StrategyInfo]
    count: int
    timestamp: str


def extract_config_summary(config: Any) -> dict[str, Any]:
    """Extract key configuration parameters from a strategy config.

    Attempts to extract common strategy config fields that are useful
    for display in the UI.

    Args:
        config: Strategy configuration object (StrategyConfig subclass).

    Returns:
        Dict of key config parameters.
    """
    summary: dict[str, Any] = {}

    # Check if config is a Pydantic model with model_dump
    if hasattr(config, "model_dump"):
        # Get all fields and select key ones
        all_fields = config.model_dump()

        # Common strategy config fields to include
        key_fields = [
            # ORB-specific
            "orb_window_minutes",
            "target_1_r",
            "target_2_r",
            "time_stop_minutes",
            "stop_placement",
            "volume_threshold_rvol",
            "chase_protection_pct",
            "breakout_volume_multiplier",
            "min_range_atr_ratio",
            "max_range_atr_ratio",
            # Generic strategy fields
            "asset_class",
            "enabled",
        ]

        for field in key_fields:
            if field in all_fields:
                summary[field] = all_fields[field]

        # Include operating window if present
        if "operating_window" in all_fields:
            window = all_fields["operating_window"]
            if isinstance(window, dict):
                summary["earliest_entry"] = window.get("earliest_entry")
                summary["latest_entry"] = window.get("latest_entry")

        # Include risk limits summary if present
        if "risk_limits" in all_fields:
            limits = all_fields["risk_limits"]
            if isinstance(limits, dict):
                summary["max_trades_per_day"] = limits.get("max_trades_per_day")
                summary["max_loss_per_trade_pct"] = limits.get("max_loss_per_trade_pct")

    return summary


@router.get("", response_model=StrategiesResponse)
async def list_strategies(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> StrategiesResponse:
    """List all registered strategies with their status.

    Returns information about each strategy including:
    - Identity (id, name, version)
    - Status (active, pipeline stage)
    - Capital and P&L
    - Open position count
    - Key configuration parameters
    """
    strategies_list: list[StrategyInfo] = []

    # Get all managed positions for open position counting
    all_positions = state.order_manager.get_managed_positions()

    for strategy_id, strategy in state.strategies.items():
        # Count open positions for this strategy
        open_positions = sum(
            1 for pos in all_positions
            if pos.strategy_id == strategy_id and not pos.is_fully_closed
        )

        # Determine pipeline stage
        # Check if strategy has a pipeline_stage attribute or derive from config
        pipeline_stage = getattr(strategy, "pipeline_stage", None)
        if pipeline_stage is None:
            # Check config for pipeline_stage
            pipeline_stage = getattr(strategy.config, "pipeline_stage", None)
        if pipeline_stage is None:
            # Default based on whether we're in paper mode
            pipeline_stage = "paper"  # Default since we're in development

        # Extract config summary
        config_summary = extract_config_summary(strategy.config)

        strategies_list.append(
            StrategyInfo(
                strategy_id=strategy.strategy_id,
                name=strategy.name,
                version=strategy.version,
                is_active=strategy.is_active,
                pipeline_stage=str(pipeline_stage),
                allocated_capital=strategy.allocated_capital,
                daily_pnl=strategy.daily_pnl,
                trade_count_today=strategy.trade_count_today,
                open_positions=open_positions,
                config_summary=config_summary,
            )
        )

    return StrategiesResponse(
        strategies=strategies_list,
        count=len(strategies_list),
        timestamp=datetime.now(UTC).isoformat(),
    )
