"""VIX data routes for the Command Center API.

Provides endpoints for current VIX landscape data and historical VIX records.
Config-gated: only mounted when vix_regime.enabled is true.

Sprint 27.9, Session 3a.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from fastapi import APIRouter, Depends, Query

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


@router.get("/current")
async def get_vix_current(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Get the latest VIX landscape data with regime classifications.

    Returns current VIX close, derived metrics, regime classifications,
    and staleness status. Returns status="unavailable" if no data loaded.
    """
    vix_service = state.vix_data_service
    if vix_service is None:
        return {
            "status": "unavailable",
            "message": "VIX data service not initialized",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    latest = vix_service.get_latest_daily()
    if latest is None:
        return {
            "status": "unavailable",
            "message": "VIX data not available",
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Build regime classifications from VIX calculators if available
    regime: dict = {}
    orchestrator = state.orchestrator
    if orchestrator is not None:
        regime_v2 = getattr(orchestrator, "_regime_classifier_v2", None)
        if regime_v2 is not None:
            vol_phase_calc = getattr(regime_v2, "_vol_phase_calc", None)
            vol_momentum_calc = getattr(regime_v2, "_vol_momentum_calc", None)
            term_structure_calc = getattr(regime_v2, "_term_structure_calc", None)
            vrp_calc = getattr(regime_v2, "_vrp_calc", None)

            if vol_phase_calc is not None:
                phase = vol_phase_calc.classify()
                regime["vol_regime_phase"] = phase.value if phase else None
            if vol_momentum_calc is not None:
                momentum = vol_momentum_calc.classify()
                regime["vol_regime_momentum"] = momentum.value if momentum else None
            if term_structure_calc is not None:
                ts = term_structure_calc.classify()
                regime["term_structure_regime"] = ts.value if ts else None
            if vrp_calc is not None:
                vrp = vrp_calc.classify()
                regime["vrp_tier"] = vrp.value if vrp else None

    is_stale = vix_service.is_stale

    return {
        "status": "ok" if not is_stale else "stale",
        "data_date": latest.get("data_date", latest.get("date")),
        "vix_close": latest.get("vix_close"),
        "vol_of_vol_ratio": latest.get("vol_of_vol_ratio"),
        "vix_percentile": latest.get("vix_percentile"),
        "term_structure_proxy": latest.get("term_structure_proxy"),
        "realized_vol_20d": latest.get("realized_vol_20d"),
        "variance_risk_premium": latest.get("variance_risk_premium"),
        "regime": regime,
        "is_stale": is_stale,
        "last_updated": datetime.now(UTC).isoformat(),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.get("/history")
async def get_vix_history(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    start_date: str | None = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(default=None, description="End date (YYYY-MM-DD)"),
) -> dict:
    """Get historical VIX data with derived metrics.

    Returns daily VIX records within the specified date range.
    Defaults to last 30 days if no dates provided.
    """
    vix_service = state.vix_data_service
    if vix_service is None:
        return {
            "status": "unavailable",
            "message": "VIX data service not initialized",
            "count": 0,
            "data": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    # Default to last 30 days
    if end_date is None:
        end_date = date.today().isoformat()
    if start_date is None:
        start_date = (date.today() - timedelta(days=30)).isoformat()

    records = vix_service.get_history_range(start_date, end_date)

    return {
        "status": "ok",
        "start_date": start_date,
        "end_date": end_date,
        "count": len(records) if records else 0,
        "data": records or [],
        "timestamp": datetime.now(UTC).isoformat(),
    }
