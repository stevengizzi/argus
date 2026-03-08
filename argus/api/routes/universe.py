"""Universe data routes for the Command Center API.

Provides endpoints for querying universe status and symbol data.

Sprint 23: NLP Catalyst + Universe Manager
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class UniverseStatusResponse(BaseModel):
    """Response for GET /universe/status."""

    enabled: bool
    total_symbols: int | None = None
    viable_count: int | None = None
    per_strategy_counts: dict[str, int] | None = None
    last_refresh: str | None = None
    reference_data_age_minutes: float | None = None


class SymbolData(BaseModel):
    """Symbol data for the universe symbols list."""

    symbol: str
    sector: str | None = None
    market_cap: float | None = None
    float_shares: float | None = None
    avg_volume: float | None = None
    matching_strategies: list[str]


class UniverseSymbolsResponse(BaseModel):
    """Response for GET /universe/symbols."""

    enabled: bool
    symbols: list[SymbolData]
    total: int
    page: int
    per_page: int
    pages: int


@router.get("/status", response_model=UniverseStatusResponse)
async def get_universe_status(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> UniverseStatusResponse:
    """Get universe manager status and statistics.

    Returns information about the viable trading universe including:
    - Total symbol count in reference cache
    - Viable symbol count (passed system filters)
    - Per-strategy symbol counts from the routing table
    - Last refresh timestamp
    - Reference data age in minutes

    When Universe Manager is not enabled, returns {"enabled": false}.

    Returns:
        Universe status with statistics.
    """
    if state.universe_manager is None:
        return UniverseStatusResponse(enabled=False)

    # Get stats from Universe Manager
    stats = state.universe_manager.get_universe_stats()

    # Get total symbols (all in reference cache, before filtering)
    total_symbols = len(state.universe_manager.reference_cache)

    return UniverseStatusResponse(
        enabled=True,
        total_symbols=total_symbols,
        viable_count=stats["total_viable"],
        per_strategy_counts=stats["per_strategy_counts"],
        last_refresh=stats["last_build_time"],
        reference_data_age_minutes=stats["cache_age_minutes"],
    )


@router.get("/symbols", response_model=UniverseSymbolsResponse)
async def get_universe_symbols(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    per_page: int = Query(50, ge=1, le=250, description="Items per page"),
    strategy_id: str | None = Query(
        None, description="Filter by strategy ID (only symbols matching this strategy)"
    ),
) -> UniverseSymbolsResponse:
    """Get paginated list of universe symbols with reference data.

    Returns symbols from the viable universe with their reference data
    including sector, market cap, float shares, average volume, and
    which strategies they match.

    Args:
        page: Page number (1-indexed).
        per_page: Number of items per page (1-250).
        strategy_id: Optional filter to only include symbols matching a strategy.

    When Universe Manager is not enabled, returns empty list with enabled=false.

    Returns:
        Paginated list of symbols with reference data.
    """
    if state.universe_manager is None:
        return UniverseSymbolsResponse(
            enabled=False,
            symbols=[],
            total=0,
            page=page,
            per_page=per_page,
            pages=0,
        )

    # Get viable symbols, optionally filtered by strategy
    if strategy_id:
        all_symbols = state.universe_manager.get_strategy_symbols(strategy_id)
    else:
        all_symbols = state.universe_manager.viable_symbols

    # Sort for consistent pagination
    sorted_symbols = sorted(all_symbols)
    total = len(sorted_symbols)

    # Calculate pagination
    pages = (total + per_page - 1) // per_page if total > 0 else 0
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    page_symbols = sorted_symbols[start_idx:end_idx]

    # Build response with reference data
    symbols_data: list[SymbolData] = []
    for symbol in page_symbols:
        ref_data = state.universe_manager.get_reference_data(symbol)
        matching_strategies = list(state.universe_manager.route_candle(symbol))

        symbols_data.append(
            SymbolData(
                symbol=symbol,
                sector=ref_data.sector if ref_data else None,
                market_cap=ref_data.market_cap if ref_data else None,
                float_shares=ref_data.float_shares if ref_data else None,
                avg_volume=ref_data.avg_volume if ref_data else None,
                matching_strategies=matching_strategies,
            )
        )

    return UniverseSymbolsResponse(
        enabled=True,
        symbols=symbols_data,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages,
    )
