"""Strategy routes for the Command Center API.

Provides endpoints for viewing and managing trading strategies.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

from argus.analytics.performance import compute_metrics
from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

_ET = ZoneInfo("America/New_York")

router = APIRouter()


class StrategyDecisionEvent(BaseModel):
    """One entry from a strategy's decision ring buffer / telemetry store.

    Shape is permissive (extra fields allowed) because the payload is
    produced by ``dataclasses.asdict(event)`` on a dataclass whose
    fields expand over time as new telemetry dimensions are added
    (FIX-07 P1-F1-5).
    """

    model_config = {"extra": "allow"}


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


class StrategyDocument(BaseModel):
    """Document metadata and content for a strategy."""

    doc_id: str
    title: str
    filename: str
    word_count: int
    reading_time_min: int
    last_modified: str
    content: str


class StrategySpecResponse(BaseModel):
    """Response containing strategy documents with metadata."""

    strategy_id: str
    documents: list[StrategyDocument]


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


def _extract_title(content: str) -> str:
    """Extract title from first # heading in markdown content."""
    for line in content.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return "Untitled Document"


def _get_git_last_modified(path: Path) -> str | None:
    """Get last modified date from git log for a file."""
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%aI", "--", str(path)],
            capture_output=True,
            text=True,
            cwd=path.parent,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def _get_file_last_modified(path: Path) -> str:
    """Get last modified date from file mtime as fallback."""
    mtime = os.path.getmtime(path)
    return datetime.fromtimestamp(mtime, tz=UTC).isoformat()


def _build_document(path: Path, doc_id: str) -> StrategyDocument:
    """Build a StrategyDocument from a file path."""
    content = path.read_text(encoding="utf-8")
    title = _extract_title(content)
    word_count = len(content.split())
    reading_time_min = max(1, round(word_count / 200))

    # Try git first, fall back to file mtime
    last_modified = _get_git_last_modified(path) or _get_file_last_modified(path)

    return StrategyDocument(
        doc_id=doc_id,
        title=title,
        filename=path.name,
        word_count=word_count,
        reading_time_min=reading_time_min,
        last_modified=last_modified,
        content=content,
    )


@router.get("/{strategy_id}/spec", response_model=StrategySpecResponse)
async def get_strategy_spec(
    strategy_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> StrategySpecResponse:
    """Get strategy documents with metadata.

    Returns documents associated with the strategy, each including:
    - doc_id: Document identifier
    - title: Extracted from first # heading
    - filename: Original filename
    - word_count: Total word count
    - reading_time_min: Estimated reading time (words / 200, rounded up)
    - last_modified: ISO date from git log or file mtime
    - content: Full markdown content

    Args:
        strategy_id: The strategy ID (e.g., "orb_breakout").

    Returns:
        StrategySpecResponse with list of documents.

    Raises:
        HTTPException 404: If no documents exist for the strategy.
    """
    documents: list[StrategyDocument] = []

    # Strategy spec sheet (primary document)
    spec_path = _resolve_spec_path(strategy_id)
    if spec_path:
        documents.append(_build_document(spec_path, "strategy_spec"))

    if not documents:
        raise HTTPException(
            status_code=404, detail=f"No documents found for strategy {strategy_id}"
        )

    return StrategySpecResponse(strategy_id=strategy_id, documents=documents)


@router.get("/{strategy_id}/decisions", response_model=list[StrategyDecisionEvent])
async def get_strategy_decisions(
    strategy_id: str,
    symbol: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    date: str | None = Query(None, description="Date (YYYY-MM-DD) for historical query"),
    state: AppState = Depends(get_app_state),  # noqa: B008
    _auth: dict = Depends(require_auth),  # noqa: B008
) -> list[dict[str, object]]:
    """Get recent evaluation events from a strategy's decision buffer.

    Returns strategy evaluation telemetry newest-first. Optionally filter
    by symbol and cap the result count. If ``date`` is provided and is not
    today, queries the persistent SQLite store for historical data.

    Args:
        strategy_id: The strategy ID (e.g., "strat_orb_breakout").
        symbol: Optional ticker filter (e.g., "AAPL").
        limit: Maximum number of events to return (1–500, default 100).
        date: Optional date filter (YYYY-MM-DD) for historical queries.

    Returns:
        List of serialized EvaluationEvent dicts, newest first.

    Raises:
        HTTPException 404: If no strategy with that ID is registered.
    """
    strategy = state.strategies.get(strategy_id)
    if strategy is None:
        raise HTTPException(status_code=404, detail=f"Strategy {strategy_id} not found")

    # Route to persistent store for historical (non-today) dates
    today_str = datetime.now(_ET).strftime("%Y-%m-%d")
    use_store = (
        date is not None
        and date != today_str
        and getattr(state, "telemetry_store", None) is not None
    )

    if use_store:
        return await state.telemetry_store.query_events(  # type: ignore[union-attr]
            strategy_id=strategy_id,
            symbol=symbol,
            date=date,
            limit=limit,
        )

    # Default: use the in-memory ring buffer (today or no store)
    events = strategy.eval_buffer.query(symbol=symbol, limit=limit)
    return [
        {
            **dataclasses.asdict(event),
            "timestamp": event.timestamp.isoformat(),
        }
        for event in events
    ]
