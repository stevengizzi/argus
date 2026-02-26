"""Strategy routes for the Command Center API.

Provides endpoints for viewing and managing trading strategies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from argus.analytics.performance import compute_metrics
from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class PerformanceSummary(BaseModel):
    """Summary of a strategy's live trading performance."""

    trade_count: int
    win_rate: float
    net_pnl: float
    avg_r: float
    profit_factor: float


class BacktestSummary(BaseModel):
    """Summary of a strategy's backtest validation status."""

    status: str
    wfe_pnl: float | None = None
    oos_sharpe: float | None = None
    total_trades: int | None = None
    data_months: int | None = None
    last_run: str | None = None


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
    time_window: str = ""
    family: str = "uncategorized"
    description_short: str = ""
    performance_summary: PerformanceSummary | None = None
    backtest_summary: BacktestSummary | None = None


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
    - Time window, family, short description
    - Performance summary (if trades exist)
    - Backtest summary (from config)
    """
    strategies_list: list[StrategyInfo] = []

    # Get all managed positions for open position counting
    all_positions = state.order_manager.get_all_positions_flat()

    for strategy_id, strategy in state.strategies.items():
        # Count open positions for this strategy
        open_positions = sum(
            1 for pos in all_positions if pos.strategy_id == strategy_id and not pos.is_fully_closed
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

        # Extract new fields from config
        time_window = getattr(strategy.config, "time_window_display", "")
        family = getattr(strategy.config, "family", "uncategorized")
        description_short = getattr(strategy.config, "description_short", "")

        # Extract backtest summary from config (guaranteed on base StrategyConfig)
        bs = strategy.config.backtest_summary
        backtest_summary = BacktestSummary(
            status=bs.status,
            wfe_pnl=bs.wfe_pnl,
            oos_sharpe=bs.oos_sharpe,
            total_trades=bs.total_trades,
            data_months=bs.data_months,
            last_run=bs.last_run,
        )

        # Build performance summary from trade history
        performance_summary: PerformanceSummary | None = None
        trades = await state.trade_logger.get_trades_by_strategy(strategy_id, limit=10000)
        if trades:
            # Convert Trade objects to dicts for compute_metrics
            trade_dicts = [
                {
                    "net_pnl": t.net_pnl,
                    "gross_pnl": t.gross_pnl,
                    "commission": t.commission,
                    "r_multiple": t.r_multiple,
                    "hold_duration_seconds": t.hold_duration_seconds,
                    "entry_time": t.entry_time.isoformat(),
                    "exit_time": t.exit_time.isoformat(),
                }
                for t in trades
            ]
            metrics = compute_metrics(trade_dicts)
            pf = metrics.profit_factor if metrics.profit_factor != float("inf") else 0.0
            performance_summary = PerformanceSummary(
                trade_count=metrics.total_trades,
                win_rate=metrics.win_rate,
                net_pnl=metrics.net_pnl,
                avg_r=metrics.avg_r_multiple,
                profit_factor=pf,
            )

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
                time_window=time_window,
                family=family,
                description_short=description_short,
                performance_summary=performance_summary,
                backtest_summary=backtest_summary,
            )
        )

    return StrategiesResponse(
        strategies=strategies_list,
        count=len(strategies_list),
        timestamp=datetime.now(UTC).isoformat(),
    )


class StrategySpecResponse(BaseModel):
    """Response containing the strategy spec sheet content."""

    strategy_id: str
    content: str
    format: str = "markdown"


def _resolve_spec_path(strategy_id: str) -> Path | None:
    """Resolve strategy spec sheet path from naming convention.

    Convention: strat_X → STRATEGY_X.md (uppercase, underscore preserved)
    Examples:
        strat_orb_breakout → STRATEGY_ORB_BREAKOUT.md
        strat_vwap_reclaim → STRATEGY_VWAP_RECLAIM.md

    Args:
        strategy_id: The strategy ID (e.g., "strat_orb_breakout").

    Returns:
        Path to the spec sheet if it exists, None otherwise.
    """
    spec_dir = Path(__file__).resolve().parent.parent.parent.parent / "docs" / "strategies"
    # Remove "strat_" prefix and uppercase the remainder
    filename = f"STRATEGY_{strategy_id.removeprefix('strat_').upper()}.md"
    path = spec_dir / filename
    return path if path.exists() else None


@router.get("/{strategy_id}/spec", response_model=StrategySpecResponse)
async def get_strategy_spec(
    strategy_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> StrategySpecResponse:
    """Get the spec sheet (markdown) for a strategy.

    Returns the full strategy specification document containing:
    - Strategy overview and rationale
    - Entry/exit rules
    - Risk parameters
    - Backtest results

    Args:
        strategy_id: The strategy ID (e.g., "strat_orb_breakout").

    Returns:
        StrategySpecResponse with markdown content.

    Raises:
        HTTPException 404: If no spec sheet exists for the strategy.
    """
    spec_path = _resolve_spec_path(strategy_id)
    if not spec_path:
        raise HTTPException(status_code=404, detail=f"No spec sheet for strategy {strategy_id}")

    content = spec_path.read_text(encoding="utf-8")
    return StrategySpecResponse(strategy_id=strategy_id, content=content)
