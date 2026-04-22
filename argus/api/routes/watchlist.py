"""Watchlist routes for the Command Center API.

Provides endpoint for viewing scanner candidates and their status across strategies.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from argus.api.auth import require_auth
from argus.api.dependencies import AppState, get_app_state

router = APIRouter()


class VwapState(StrEnum):
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
    vwap_distance_pct: float | None = None  # (price - vwap) / vwap, signed. None if no VWAP.
    scan_source: str = ""  # "fmp" | "fmp_fallback" | "static" | ""
    selection_reason: str = ""  # "gap_up_3.2%" | "gap_down_1.8%" | "high_volume" | ""


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
    #
    # Tests may monkey-patch a ``_mock_watchlist`` list of
    # ``WatchlistItem`` onto AppState to exercise the response shape
    # without a full data_service stack. The getattr() is intentionally
    # permissive — production paths always hit the ``cached_watchlist``
    # branch below because ``data_service`` is always wired in main.py.

    watchlist_items: list[WatchlistItem] = []

    # Test-only injection: monkey-patched list of WatchlistItem
    mock_watchlist = getattr(state, "_mock_watchlist", None)
    if mock_watchlist is not None:
        watchlist_items = mock_watchlist
    else:
        # Production: aggregate from scanner's cached watchlist
        for core_item in state.cached_watchlist:
            watchlist_items.append(
                WatchlistItem(
                    symbol=core_item.symbol,
                    current_price=0.0,  # Populated from data_service in Sprint 22+
                    gap_pct=core_item.gap_pct,
                    strategies=[],  # Populated from strategy states in Sprint 22+
                    vwap_state=VwapState.WATCHING,
                    sparkline=[],
                    scan_source=core_item.scan_source,
                    selection_reason=core_item.selection_reason,
                )
            )

    return WatchlistResponse(
        symbols=watchlist_items,
        count=len(watchlist_items),
        timestamp=datetime.now(UTC).isoformat(),
    )
