"""Experiment pipeline REST API routes.

Exposes the experiment registry via four JWT-protected endpoints.
All endpoints return 503 when ``experiments.enabled: false``.

Sprint 32, Session 8.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

if TYPE_CHECKING:
    from argus.intelligence.experiments.store import ExperimentStore

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunSweepRequest(BaseModel):
    """Request body for POST /experiments/run."""

    pattern: str
    param_subset: list[str] | None = None
    dry_run: bool = False


class RunSweepResponse(BaseModel):
    """Response for POST /experiments/run."""

    experiment_count: int
    grid_size: int
    timestamp: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_experiment_store(state: AppState) -> ExperimentStore:
    """Return ExperimentStore or raise 503 if experiments disabled.

    Args:
        state: Shared AppState.

    Returns:
        ExperimentStore instance.

    Raises:
        HTTPException 503: If experiment_store is not initialized.
    """
    if state.experiment_store is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Experiment pipeline not available (experiments.enabled: false)",
        )
    return state.experiment_store  # type: ignore[return-value]


def _record_to_dict(record: object) -> dict[str, Any]:
    """Serialize an ExperimentRecord to a JSON-safe dict.

    Args:
        record: ExperimentRecord dataclass instance.

    Returns:
        Dict with all fields; datetimes as ISO strings.
    """
    import dataclasses

    if not dataclasses.is_dataclass(record) or isinstance(record, type):
        return {}
    raw: dict[str, Any] = dataclasses.asdict(record)  # type: ignore[call-overload]
    for key in ("created_at", "updated_at"):
        if key in raw and hasattr(raw[key], "isoformat"):
            raw[key] = raw[key].isoformat()
    return raw


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("")
async def list_experiments(
    pattern: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """List experiments, optionally filtered by pattern name.

    Returns a list of ExperimentRecord dicts ordered by created_at descending.
    503 if experiment pipeline is disabled.
    """
    store = _get_experiment_store(state)
    records = await store.list_experiments(pattern_name=pattern, limit=limit)
    return {
        "experiments": [_record_to_dict(r) for r in records],
        "count": len(records),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/baseline/{pattern_name}")
async def get_baseline(
    pattern_name: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Return the baseline experiment for a pattern.

    Returns the ExperimentRecord marked is_baseline=True, or 404 if no
    baseline is set. 503 if experiment pipeline is disabled.
    """
    store = _get_experiment_store(state)
    record = await store.get_baseline(pattern_name)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No baseline set for pattern '{pattern_name}'",
        )
    return {
        "experiment": _record_to_dict(record),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/variants")
async def list_variants_with_metrics(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """List all variants with experiment metrics where available.

    Returns each variant's definition plus joined experiment metrics
    (status, shadow_trade_count, win_rate, expectancy, sharpe).
    503 if experiment pipeline is disabled.
    """
    store = _get_experiment_store(state)
    try:
        variants = await store.query_variants_with_metrics()
    except Exception as exc:
        logger.error("Failed to query variants with metrics: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query variants: {exc}",
        ) from exc
    return {
        "variants": variants,
        "count": len(variants),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/promotions")
async def list_promotion_events(
    limit: int = Query(default=100, ge=1, le=500, description="Max results per page"),
    offset: int = Query(default=0, ge=0, description="Rows to skip for pagination"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """List promotion and demotion events with pagination.

    Returns events ordered by timestamp descending, joined with variant
    pattern_name for display. 503 if experiment pipeline is disabled.

    Query params:
        limit: Maximum results (default 100).
        offset: Pagination offset (default 0).
    """
    store = _get_experiment_store(state)
    try:
        events = await store.query_promotion_events(limit=limit, offset=offset)
        total_count = await store.count_promotion_events()
    except Exception as exc:
        logger.error("Failed to query promotion events: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to query promotions: {exc}",
        ) from exc
    return {
        "events": events,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/{experiment_id}")
async def get_experiment(
    experiment_id: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Return a single experiment by ID.

    Includes the full backtest_result field. 404 if not found. 503 if
    experiment pipeline is disabled.
    """
    store = _get_experiment_store(state)
    record = await store.get_experiment(experiment_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Experiment {experiment_id} not found",
        )
    return {
        "experiment": _record_to_dict(record),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/run", response_model=RunSweepResponse)
async def run_sweep(
    body: RunSweepRequest,
    background_tasks: BackgroundTasks,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> RunSweepResponse:
    """Trigger a parameter sweep for a pattern.

    Launches the sweep as a non-blocking background task. Returns the grid
    size immediately. 503 if experiment pipeline is disabled. 400 if the
    pattern is not registered.
    """
    store = _get_experiment_store(state)

    # Validate pattern by attempting grid generation — raises ValueError for
    # unknown patterns.
    from argus.intelligence.experiments.runner import ExperimentRunner

    exp_config = (
        state.config.experiments.model_dump()
        if state.config is not None
        else {}
    )
    runner = ExperimentRunner(store=store, config=exp_config)

    try:
        grid = runner.generate_parameter_grid(body.pattern, body.param_subset)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    grid_size = len(grid)

    if not body.dry_run:
        cache_dir = exp_config.get("cache_dir", "data/databento_cache")

        async def _run_sweep() -> None:
            try:
                await runner.run_sweep(
                    pattern_name=body.pattern,
                    cache_dir=str(cache_dir),
                    param_subset=body.param_subset,
                    dry_run=False,
                )
            except Exception:
                logger.error(
                    "Background sweep failed for pattern=%s", body.pattern, exc_info=True
                )

        background_tasks.add_task(_run_sweep)

    return RunSweepResponse(
        experiment_count=0,
        grid_size=grid_size,
        timestamp=datetime.now(UTC).isoformat(),
    )
