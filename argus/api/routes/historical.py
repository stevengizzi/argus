"""Historical data routes for the Command Center API.

Provides read-only endpoints for querying the Databento Parquet cache
via the DuckDB-backed HistoricalQueryService. All endpoints are JWT-protected
and use parameterized/template queries — no raw SQL passthrough from clients.

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state
from argus.data.historical_query_service import ServiceUnavailableError


class ValidateCoverageRequest(BaseModel):
    """Request body for POST /historical/validate-coverage."""

    symbols: list[str] = Field(..., min_length=1)
    start_date: str
    end_date: str
    min_bars: int = Field(default=100, ge=1)

router = APIRouter()

_MAX_BARS_PER_REQUEST = 50_000


def _get_service(state: AppState):  # type: ignore[return]
    """Return the HistoricalQueryService or raise 503."""
    svc = state.historical_query_service
    if svc is None or not svc.is_available:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Historical Query Service not available",
        )
    return svc


def _parse_date(value: str, param_name: str) -> str:
    """Validate YYYY-MM-DD format and return the value unchanged.

    Args:
        value: Date string supplied by the client.
        param_name: Name used in error messages.

    Returns:
        The validated date string.

    Raises:
        HTTPException 400: If the format is invalid.
    """
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return value
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format for '{param_name}': expected YYYY-MM-DD, got '{value}'",
        )


@router.get("/symbols")
async def get_symbols(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Return all symbols present in the Parquet cache.

    Returns:
        JSON with ``symbols`` list and ``count``.
    """
    svc = _get_service(state)
    try:
        symbols = svc.get_available_symbols()
        return {
            "symbols": symbols,
            "count": len(symbols),
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc


@router.get("/coverage")
async def get_coverage(
    symbol: str | None = Query(default=None, description="Ticker symbol for per-symbol coverage"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Return date coverage and bar count for the entire cache or one symbol.

    Query params:
        symbol: Optional ticker. If omitted, returns aggregate stats.

    Returns:
        JSON with coverage statistics and (when no symbol) cache_size_bytes.
    """
    svc = _get_service(state)
    try:
        if symbol is not None:
            coverage = svc.get_date_coverage(symbol=symbol)
            return {
                "symbol": symbol,
                **coverage,
                "timestamp": datetime.now(UTC).isoformat(),
            }

        health = svc.get_cache_health()
        return {
            **health,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc


@router.get("/bars/{symbol}")
async def get_bars(
    symbol: str,
    start_date: str = Query(..., description="Start date YYYY-MM-DD (inclusive)"),
    end_date: str = Query(..., description="End date YYYY-MM-DD (inclusive)"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Return OHLCV bars for a symbol within a date range.

    Path params:
        symbol: Ticker symbol (e.g., AAPL).

    Query params:
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Inclusive end date (YYYY-MM-DD).

    Returns:
        JSON with ``bars`` array, ``count``, and symbol metadata.

    Raises:
        400: Bad date format.
        404: Symbol not found in cache.
        503: Service unavailable.
    """
    svc = _get_service(state)
    start = _parse_date(start_date, "start_date")
    end = _parse_date(end_date, "end_date")

    try:
        df = svc.get_symbol_bars(symbol=symbol, start_date=start, end_date=end)
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc

    if df.empty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No bars found for symbol '{symbol}' in range {start_date} to {end_date}",
        )

    # Enforce max bars limit
    if len(df) > _MAX_BARS_PER_REQUEST:
        df = df.iloc[:_MAX_BARS_PER_REQUEST]

    # Serialize — convert timestamps to ISO strings for JSON
    records = df.copy()
    if "ts_event" in records.columns:
        records["ts_event"] = records["ts_event"].astype(str)
    if "date" in records.columns:
        records["date"] = records["date"].astype(str)

    return {
        "symbol": symbol,
        "start_date": start_date,
        "end_date": end_date,
        "count": len(records),
        "bars": records.to_dict(orient="records"),
        "timestamp": datetime.now(UTC).isoformat(),
    }


@router.post("/validate-coverage")
async def validate_coverage(
    request: ValidateCoverageRequest,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> dict:
    """Check whether each symbol has enough bars in the date range.

    Request body:
        symbols: List of ticker symbols (must be non-empty).
        start_date: Inclusive start date (YYYY-MM-DD).
        end_date: Inclusive end date (YYYY-MM-DD).
        min_bars: Minimum bar threshold (default 100).

    Returns:
        JSON with ``results`` dict mapping symbol -> bool.
    """
    svc = _get_service(state)

    start = _parse_date(request.start_date, "start_date")
    end = _parse_date(request.end_date, "end_date")

    try:
        results = svc.validate_symbol_coverage(
            symbols=request.symbols,
            start_date=start,
            end_date=end,
            min_bars=request.min_bars,
        )
        return {
            "results": results,
            "min_bars": request.min_bars,
            "timestamp": datetime.now(UTC).isoformat(),
        }
    except ServiceUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query failed: {exc}",
        ) from exc
