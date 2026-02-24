"""Market regime classification for the Orchestrator.

Defines market regime types and the indicators used to determine
the current regime. The Orchestrator uses regime to adjust strategy
allocations and risk parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from argus.core.config import OrchestratorConfig


class VolatilityBucket(StrEnum):
    """Volatility regime buckets based on realized volatility."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRISIS = "crisis"


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


class RegimeClassifier:
    """Rules-based market regime classification.

    V1 uses SPY indicators only (no VIX, no breadth — DEC-113).
    Designed for indicator-count growth without interface changes.

    Scoring system:
    1. Trend score (-2 to +2) based on SPY vs SMA-20/50
    2. Volatility bucket (LOW/NORMAL/HIGH/CRISIS) based on 20-day realized vol
    3. Momentum confirmation from 5-day ROC

    Decision matrix prioritizes crisis detection, then combines trend
    and volatility signals.
    """

    # Momentum thresholds for confirmation
    _ROC_BULLISH_THRESHOLD = 0.01  # +1%
    _ROC_BEARISH_THRESHOLD = -0.01  # -1%

    def __init__(self, config: OrchestratorConfig) -> None:
        """Initialize the regime classifier.

        Args:
            config: Orchestrator configuration containing volatility thresholds.
        """
        self._config = config

    def compute_indicators(self, daily_bars: pd.DataFrame) -> RegimeIndicators:
        """Compute regime indicators from SPY daily OHLCV bars.

        Args:
            daily_bars: DataFrame with columns [timestamp, open, high, low, close, volume].
                       Must be sorted oldest-first. Minimum 50 rows for SMA-50.

        Returns:
            RegimeIndicators with all computable values filled in.
            Missing indicators (insufficient data) set to None.

        Raises:
            ValueError: If daily_bars is empty or missing required columns.
        """
        if daily_bars.empty:
            raise ValueError("daily_bars DataFrame is empty")

        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(daily_bars.columns)
        if missing:
            raise ValueError(f"daily_bars missing required columns: {missing}")

        # Get the most recent bar for current price
        latest = daily_bars.iloc[-1]
        spy_price = float(latest["close"])

        # Compute SMAs if sufficient data
        spy_sma_20: float | None = None
        spy_sma_50: float | None = None

        if len(daily_bars) >= 20:
            spy_sma_20 = float(daily_bars["close"].tail(20).mean())

        if len(daily_bars) >= 50:
            spy_sma_50 = float(daily_bars["close"].tail(50).mean())

        # Compute 5-day rate of change
        spy_roc_5d: float | None = None
        if len(daily_bars) >= 6:  # Need at least 6 rows for 5-day ROC
            close_5d_ago = float(daily_bars["close"].iloc[-6])
            if close_5d_ago > 0:
                spy_roc_5d = (spy_price - close_5d_ago) / close_5d_ago

        # Compute 20-day realized volatility (annualized)
        spy_realized_vol_20d: float | None = None
        if len(daily_bars) >= 21:  # Need 21 bars for 20 daily returns
            daily_returns = daily_bars["close"].pct_change().dropna()
            if len(daily_returns) >= 20:
                vol_daily = float(daily_returns.tail(20).std())
                spy_realized_vol_20d = vol_daily * (252**0.5)  # Annualize

        # Compute VWAP relative position (daily approximation)
        # Using typical price as VWAP proxy for daily bar
        spy_vs_vwap: float | None = None
        typical_price = (latest["high"] + latest["low"] + latest["close"]) / 3
        if typical_price > 0:
            spy_vs_vwap = (spy_price - typical_price) / typical_price

        return RegimeIndicators(
            spy_price=spy_price,
            spy_sma_20=spy_sma_20,
            spy_sma_50=spy_sma_50,
            spy_roc_5d=spy_roc_5d,
            spy_realized_vol_20d=spy_realized_vol_20d,
            spy_vs_vwap=spy_vs_vwap,
            timestamp=datetime.now(UTC),
        )

    def classify(self, indicators: RegimeIndicators) -> MarketRegime:
        """Classify market regime from indicators.

        Scoring system:
        1. Trend score (-2 to +2):
           - SPY > SMA-20 AND > SMA-50 → +2 (strong bull)
           - SPY < SMA-20 AND < SMA-50 → -2 (strong bear)
           - Mixed (above one, below other) → 0 (range-bound)
           - Only one SMA available: above → +1, below → -1
           - SMA data missing → 0

        2. Volatility bucket:
           - realized_vol < vol_low_threshold → LOW
           - realized_vol < vol_normal_threshold → NORMAL
           - realized_vol < vol_high_threshold → HIGH
           - realized_vol >= vol_crisis_threshold → CRISIS
           - None → NORMAL (conservative default)

        3. Momentum confirmation:
           - ROC-5d > +1% → bullish confirmation (+1)
           - ROC-5d < -1% → bearish confirmation (-1)
           - Otherwise → neutral (0)

        Decision matrix:
        - Crisis vol → CRISIS (overrides everything)
        - High vol + strong trend (|trend_score| >= 2) → HIGH_VOLATILITY
        - Trend score >= +1 → BULLISH_TRENDING
        - Trend score <= -1 → BEARISH_TRENDING
        - Otherwise → RANGE_BOUND

        Args:
            indicators: Computed regime indicators.

        Returns:
            The classified market regime.
        """
        # Step 1: Compute trend score
        trend_score = self._compute_trend_score(indicators)

        # Step 2: Determine volatility bucket
        vol_bucket = self._compute_volatility_bucket(indicators)

        # Step 3: Compute momentum confirmation
        momentum_conf = self._compute_momentum_confirmation(indicators)

        # Apply momentum confirmation to trend score
        # Momentum in same direction strengthens conviction
        if (trend_score > 0 and momentum_conf > 0) or (trend_score < 0 and momentum_conf < 0):
            trend_score += momentum_conf

        # Step 4: Apply decision matrix
        # Crisis overrides everything
        if vol_bucket == VolatilityBucket.CRISIS:
            return MarketRegime.CRISIS

        # High volatility with strong trend
        if vol_bucket == VolatilityBucket.HIGH and abs(trend_score) >= 2:
            return MarketRegime.HIGH_VOLATILITY

        # Trend-based classification
        if trend_score >= 1:
            return MarketRegime.BULLISH_TRENDING
        if trend_score <= -1:
            return MarketRegime.BEARISH_TRENDING

        # Default: range-bound
        return MarketRegime.RANGE_BOUND

    def _compute_trend_score(self, indicators: RegimeIndicators) -> int:
        """Compute trend score based on SPY position vs SMAs.

        Returns:
            Score from -2 (strong bear) to +2 (strong bull).
        """
        # Missing SMA data → neutral
        if indicators.spy_sma_20 is None and indicators.spy_sma_50 is None:
            return 0

        price = indicators.spy_price

        # Compare to available SMAs
        above_sma_20 = (
            price > indicators.spy_sma_20 if indicators.spy_sma_20 is not None else None
        )
        above_sma_50 = (
            price > indicators.spy_sma_50 if indicators.spy_sma_50 is not None else None
        )
        below_sma_20 = (
            price < indicators.spy_sma_20 if indicators.spy_sma_20 is not None else None
        )
        below_sma_50 = (
            price < indicators.spy_sma_50 if indicators.spy_sma_50 is not None else None
        )

        # Both SMAs available
        if above_sma_20 is not None and above_sma_50 is not None:
            if above_sma_20 and above_sma_50:
                return 2  # Strong bull: above both
            if below_sma_20 and below_sma_50:
                return -2  # Strong bear: below both
            # Mixed: above one, below other → range-bound (0)
            # This includes cases where price is exactly at one or both SMAs
            if above_sma_20 and below_sma_50:
                return 0  # Above short-term, below long-term
            if below_sma_20 and above_sma_50:
                return 0  # Below short-term, above long-term
            # Price exactly at one or both SMAs
            return 0

        # Only SMA-20 available
        if above_sma_20 is not None:
            if above_sma_20:
                return 1
            if below_sma_20:
                return -1
            return 0  # Exactly at SMA-20

        # Only SMA-50 available
        if above_sma_50 is not None:
            if above_sma_50:
                return 1
            if below_sma_50:
                return -1
            return 0  # Exactly at SMA-50

        return 0

    def _compute_volatility_bucket(self, indicators: RegimeIndicators) -> VolatilityBucket:
        """Determine volatility bucket from realized volatility.

        Returns:
            VolatilityBucket classification.
        """
        vol = indicators.spy_realized_vol_20d

        # Missing data → conservative default
        if vol is None:
            return VolatilityBucket.NORMAL

        # Check thresholds in order from most severe
        if vol >= self._config.vol_crisis_threshold:
            return VolatilityBucket.CRISIS
        if vol >= self._config.vol_high_threshold:
            return VolatilityBucket.HIGH
        if vol >= self._config.vol_normal_threshold:
            return VolatilityBucket.NORMAL
        if vol < self._config.vol_low_threshold:
            return VolatilityBucket.LOW

        # Between low and normal thresholds → NORMAL
        return VolatilityBucket.NORMAL

    def _compute_momentum_confirmation(self, indicators: RegimeIndicators) -> int:
        """Compute momentum confirmation from ROC-5d.

        Returns:
            +1 for bullish, -1 for bearish, 0 for neutral.
        """
        roc = indicators.spy_roc_5d

        if roc is None:
            return 0

        if roc > self._ROC_BULLISH_THRESHOLD:
            return 1
        if roc < self._ROC_BEARISH_THRESHOLD:
            return -1

        return 0
