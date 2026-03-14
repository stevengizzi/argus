"""Quality scoring routes for the Command Center API.

Provides endpoints for querying setup quality scores, history, and
grade distributions from the quality_history table.

Sprint 24, Session 8.
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

logger = logging.getLogger(__name__)

router = APIRouter()

_ET = ZoneInfo("America/New_York")

# All recognized quality grades, ordered best → worst.
_ALL_GRADES: tuple[str, ...] = ("A+", "A", "A-", "B+", "B", "B-", "C+", "C")


# --- Response Models ---


class QualityComponentsResponse(BaseModel):
    """Component dimension scores for a quality assessment."""

    ps: float
    cq: float
    vp: float
    hm: float
    ra: float


class QualityScoreResponse(BaseModel):
    """Single quality score record."""

    symbol: str
    score: float
    grade: str
    risk_tier: str
    components: QualityComponentsResponse
    scored_at: str


class QualityHistoryResponse(BaseModel):
    """Paginated quality history response."""

    items: list[QualityScoreResponse]
    total: int
    limit: int
    offset: int


class GradeDistributionResponse(BaseModel):
    """Today's grade distribution response."""

    grades: dict[str, int]
    total: int
    filtered: int


# --- Helpers ---


def _ensure_quality_engine(state: AppState) -> None:
    """Raise 503 if SetupQualityEngine is not available.

    Args:
        state: The application state.

    Raises:
        HTTPException 503: If quality engine or its DB is not initialized.
    """
    if state.quality_engine is None or state.quality_engine._db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Quality engine not available",
        )


def _row_to_response(row: object) -> QualityScoreResponse:
    """Convert a database row to a QualityScoreResponse.

    Args:
        row: A database row with indexed columns matching the
             quality_history table SELECT order.

    Returns:
        QualityScoreResponse model.
    """
    return QualityScoreResponse(
        symbol=row[0],  # type: ignore[index]
        score=row[1],  # type: ignore[index]
        grade=row[2],  # type: ignore[index]
        risk_tier=row[3],  # type: ignore[index]
        components=QualityComponentsResponse(
            ps=row[4],  # type: ignore[index]
            cq=row[5],  # type: ignore[index]
            vp=row[6],  # type: ignore[index]
            hm=row[7],  # type: ignore[index]
            ra=row[8],  # type: ignore[index]
        ),
        scored_at=row[9],  # type: ignore[index]
    )


# --- Endpoints ---
# NOTE: /history and /distribution MUST be defined before /{symbol}
# to avoid FastAPI matching them as path parameters.


@router.get("/history", response_model=QualityHistoryResponse)
async def get_quality_history(
    symbol: str | None = Query(None, description="Filter by symbol"),
    strategy_id: str | None = Query(None, description="Filter by strategy"),
    grade: str | None = Query(None, description="Filter by grade"),
    start_date: str | None = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, ge=1, le=200, description="Max results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> QualityHistoryResponse:
    """Get paginated quality history with optional filters.

    Query params:
        symbol: Filter by stock symbol.
        strategy_id: Filter by strategy ID.
        grade: Filter by quality grade (e.g. "A", "B+").
        start_date: Filter scored_at >= start_date (YYYY-MM-DD).
        end_date: Filter scored_at <= end_date (YYYY-MM-DD).
        limit: Maximum results per page (1-200, default 50).
        offset: Number of results to skip for pagination.

    Returns:
        Paginated list of quality scores with total count.
    """
    _ensure_quality_engine(state)
    db = state.quality_engine._db  # type: ignore[union-attr]

    conditions: list[str] = []
    params: list[object] = []

    if symbol is not None:
        conditions.append("symbol = ?")
        params.append(symbol.upper())
    if strategy_id is not None:
        conditions.append("strategy_id = ?")
        params.append(strategy_id)
    if grade is not None:
        conditions.append("grade = ?")
        params.append(grade)
    if start_date is not None:
        conditions.append("scored_at >= ?")
        params.append(start_date)
    if end_date is not None:
        conditions.append("scored_at <= ?")
        params.append(end_date + "T23:59:59")

    where = "WHERE " + " AND ".join(conditions) if conditions else ""

    # Total count
    count_row = await db.fetch_one(
        f"SELECT COUNT(*) FROM quality_history {where}",  # noqa: S608
        tuple(params),
    )
    total = count_row[0] if count_row else 0  # type: ignore[index]

    # Fetch page
    rows = await db.fetch_all(
        f"""
        SELECT symbol, composite_score, grade, risk_tier,
               pattern_strength, catalyst_quality, volume_profile,
               historical_match, regime_alignment, scored_at
        FROM quality_history
        {where}
        ORDER BY scored_at DESC
        LIMIT ? OFFSET ?
        """,  # noqa: S608
        tuple(params) + (limit, offset),
    )

    return QualityHistoryResponse(
        items=[_row_to_response(r) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/distribution", response_model=GradeDistributionResponse)
async def get_quality_distribution(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> GradeDistributionResponse:
    """Get today's quality grade distribution.

    Returns:
        Grade counts for today, including count of signals below
        the minimum trading grade.
    """
    _ensure_quality_engine(state)
    db = state.quality_engine._db  # type: ignore[union-attr]

    today = datetime.now(_ET).strftime("%Y-%m-%d")

    rows = await db.fetch_all(
        """
        SELECT grade, COUNT(*) as cnt
        FROM quality_history
        WHERE scored_at >= ?
        GROUP BY grade
        """,
        (today,),
    )

    # Build grade map with all grades initialized to 0
    grade_counts: dict[str, int] = {g: 0 for g in _ALL_GRADES}
    for row in rows:
        grade_counts[row[0]] = row[1]  # type: ignore[index]

    total = sum(grade_counts.values())

    # Count signals below min_grade_to_trade
    min_grade = state.quality_engine._config.min_grade_to_trade  # type: ignore[union-attr]
    min_idx = _ALL_GRADES.index(min_grade) if min_grade in _ALL_GRADES else len(_ALL_GRADES)
    below_grades = _ALL_GRADES[min_idx + 1:]
    filtered = sum(grade_counts.get(g, 0) for g in below_grades)

    return GradeDistributionResponse(
        grades=grade_counts,
        total=total,
        filtered=filtered,
    )


@router.get("/{symbol}", response_model=QualityScoreResponse)
async def get_quality_for_symbol(
    symbol: str,
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> QualityScoreResponse:
    """Get the most recent quality score for a symbol.

    Path params:
        symbol: Stock ticker symbol.

    Returns:
        The latest quality score record for the symbol.

    Raises:
        404: If no quality history exists for the symbol.
    """
    _ensure_quality_engine(state)
    db = state.quality_engine._db  # type: ignore[union-attr]

    row = await db.fetch_one(
        """
        SELECT symbol, composite_score, grade, risk_tier,
               pattern_strength, catalyst_quality, volume_profile,
               historical_match, regime_alignment, scored_at
        FROM quality_history
        WHERE symbol = ?
        ORDER BY scored_at DESC
        LIMIT 1
        """,
        (symbol.upper(),),
    )

    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No quality history for symbol {symbol.upper()}",
        )

    return _row_to_response(row)
