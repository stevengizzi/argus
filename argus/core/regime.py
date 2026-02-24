"""Market regime classification for the Orchestrator.

Defines market regime types and the indicators used to determine
the current regime. The Orchestrator uses regime to adjust strategy
allocations and risk parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class MarketRegime(StrEnum):
    """Market regime classification.

    The Orchestrator monitors SPY and volatility indicators to classify
    the current market environment. Different regimes trigger different
    allocation and risk adjustments.
    """

    BULLISH_TRENDING = "bullish_trending"
    BEARISH_TRENDING = "bearish_trending"
    RANGE_BOUND = "range_bound"
    HIGH_VOLATILITY = "high_volatility"
    CRISIS = "crisis"


@dataclass(frozen=True)
class RegimeIndicators:
    """Snapshot of indicators used for regime classification.

    These values are computed periodically by the Orchestrator and
    used to determine the current MarketRegime.

    Attributes:
        spy_price: Current SPY price.
        spy_sma_20: SPY 20-day simple moving average (None if insufficient data).
        spy_sma_50: SPY 50-day simple moving average (None if insufficient data).
        spy_roc_5d: SPY 5-day rate of change as decimal (None if insufficient data).
        spy_realized_vol_20d: SPY 20-day realized volatility annualized (None if insufficient data).
        spy_vs_vwap: SPY price vs VWAP ratio (None if unavailable).
        timestamp: When these indicators were computed (UTC).
    """

    spy_price: float
    spy_sma_20: float | None
    spy_sma_50: float | None
    spy_roc_5d: float | None
    spy_realized_vol_20d: float | None
    spy_vs_vwap: float | None
    timestamp: datetime
