"""Watchlist routes for the Command Center API.

Provides endpoint for viewing scanner candidates and their status across strategies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class VwapState(str, Enum):
    """VWAP Reclaim state indicator for a symbol."""

    WATCHING = "watching"  # On watchlist but no VWAP position yet
    ABOVE_VWAP = "above_vwap"  # Price above VWAP, potential entry
    BELOW_VWAP = "below_vwap"  # Price below VWAP, waiting for reclaim
    ENTERED = "entered"  # Active position via VWAP Reclaim


class SparklinePoint(BaseModel):
    """Single point in a mini sparkline."""

    timestamp: str
    price: float


class WatchlistItem(BaseModel):
    """Single item in the watchlist with strategy status."""

    symbol: str
    current_price: float
    gap_pct: float
    strategies: list[str]  # Which strategies are watching: ["orb", "scalp", "vwap_reclaim"]
    vwap_state: VwapState
    sparkline: list[SparklinePoint]  # Last 30 data points for mini chart


class WatchlistResponse(BaseModel):
    """Response for GET /watchlist."""

    symbols: list[WatchlistItem]
    count: int
    timestamp: str


@router.get("", response_model=WatchlistResponse)
async def get_watchlist(
    _auth: dict = Depends(require_auth),  # noqa: B008
    state: AppState = Depends(get_app_state),  # noqa: B008
) -> WatchlistResponse:
    """Get the current scanner watchlist with strategy status.

    Returns symbols from the scanner with:
    - Current price
    - Gap percentage from previous close
    - Which strategies are tracking this symbol
    - VWAP state indicator for VWAP Reclaim strategy
    - Mini sparkline data (last 30 bars)

    Returns:
        List of watchlist items with strategy status.
    """
    # In production, this would aggregate data from:
    # - Scanner watchlist
    # - Strategy state (which symbols each strategy is tracking)
    # - Data service (current prices, sparkline data)
    # - VWAP Reclaim strategy state (vwap position)

    # For now, return mock data that will be populated by dev_state.py
    # when running in dev mode, or from real scanner in production

    watchlist_items: list[WatchlistItem] = []

    # Check if we have a scanner and data service
    # In dev mode, these may be None, and mock data is returned instead
    if state.data_service is None:
        # Dev mode: return mock data from state if available
        # The mock data is injected via state extension in dev_state.py
        mock_watchlist = getattr(state, "_mock_watchlist", None)
        if mock_watchlist is not None:
            watchlist_items = mock_watchlist
    else:
        # Production mode: aggregate from scanner and strategies
        # This is a placeholder for the production implementation
        pass

    return WatchlistResponse(
        symbols=watchlist_items,
        count=len(watchlist_items),
        timestamp=datetime.now(UTC).isoformat(),
    )
