"""Market regime classification for the Orchestrator.

Defines market regime types and the indicators used to determine
the current regime. The Orchestrator uses regime to adjust strategy
allocations and risk parameters.

V1: RegimeClassifier — rules-based SPY trend+vol (DEC-113).
V2: RegimeClassifierV2 — multi-dimensional RegimeVector with V1 delegation (Sprint 27.6).
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Optional, Protocol

import pandas as pd

from argus.data.vix_config import (
    TermStructureRegime,
    VolRegimeMomentum,
    VolRegimePhase,
    VRPTier,
)

if TYPE_CHECKING:
    from argus.core.breadth import BreadthCalculator as BreadthCalcImpl
    from argus.core.config import OrchestratorConfig, RegimeIntelligenceConfig
    from argus.core.intraday_character import IntradayCharacterDetector
    from argus.core.market_correlation import MarketCorrelationTracker
    from argus.core.sector_rotation import SectorRotationAnalyzer
    from argus.data.vix_data_service import VIXDataService

logger = logging.getLogger(__name__)


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


@dataclass(frozen=True)
class RegimeVector:
    """Multi-dimensional regime state vector (Sprint 27.6).

    Captures market environment across 6 dimensions: trend, volatility,
    breadth, correlation, sector rotation, and intraday character.
    Replaces the single MarketRegime enum with a continuous vector while
    maintaining backward compatibility via primary_regime.

    Attributes:
        computed_at: When this vector was computed (UTC).
        trend_score: Continuous trend signal (-1.0 bearish to +1.0 bullish).
        trend_conviction: Confidence in trend direction (0.0–1.0).
        volatility_level: Annualized realized volatility (continuous).
        volatility_direction: Vol term structure proxy (-1.0 falling to +1.0 rising).
        universe_breadth_score: Fraction of universe above their 20-day MA (0.0–1.0).
        breadth_thrust: Whether breadth crossed thrust threshold recently.
        average_correlation: Mean pairwise correlation of top symbols.
        correlation_regime: Categorical correlation state.
        sector_rotation_phase: Current risk appetite from sector flows.
        leading_sectors: Sectors with strongest relative performance.
        lagging_sectors: Sectors with weakest relative performance.
        opening_drive_strength: Magnitude of first-bar move vs ATR.
        first_30min_range_ratio: Range of first 30min vs prior day range.
        vwap_slope: Slope of intraday VWAP (price per bar).
        direction_change_count: Number of trend reversals in session.
        intraday_character: Categorical session character classification.
        primary_regime: Backward-compatible MarketRegime enum.
        regime_confidence: Overall confidence in regime assessment (0.0–1.0).
    """

    # Core timing
    computed_at: datetime

    # Dimension 1: Trend
    trend_score: float  # -1.0 to +1.0
    trend_conviction: float  # 0.0 to 1.0

    # Dimension 2: Volatility
    volatility_level: float  # Annualized realized vol
    volatility_direction: float  # -1.0 to +1.0

    # Dimension 3: Breadth
    universe_breadth_score: float | None = None
    breadth_thrust: bool | None = None

    # Dimension 4: Correlation
    average_correlation: float | None = None
    correlation_regime: str | None = None  # "dispersed", "normal", "concentrated"

    # Dimension 5: Sector Rotation
    sector_rotation_phase: str | None = None  # "risk_on", "risk_off", "mixed", "transitioning"
    leading_sectors: list[str] = field(default_factory=list)
    lagging_sectors: list[str] = field(default_factory=list)

    # Dimension 6: Intraday Character
    opening_drive_strength: float | None = None
    first_30min_range_ratio: float | None = None
    vwap_slope: float | None = None
    direction_change_count: int | None = None
    intraday_character: str | None = None  # "trending", "choppy", "reversal", "breakout"

    # Dimension 7: VIX Landscape (Sprint 27.9)
    vol_regime_phase: Optional[VolRegimePhase] = None
    vol_regime_momentum: Optional[VolRegimeMomentum] = None
    term_structure_regime: Optional[TermStructureRegime] = None
    variance_risk_premium: Optional[VRPTier] = None
    vix_close: Optional[float] = None

    # Backward compatibility + confidence
    primary_regime: MarketRegime = MarketRegime.RANGE_BOUND
    regime_confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary.

        Returns:
            Dictionary with all fields. None values serialize as null-equivalent.
        """
        return {
            "computed_at": self.computed_at.isoformat(),
            "trend_score": self.trend_score,
            "trend_conviction": self.trend_conviction,
            "volatility_level": self.volatility_level,
            "volatility_direction": self.volatility_direction,
            "universe_breadth_score": self.universe_breadth_score,
            "breadth_thrust": self.breadth_thrust,
            "average_correlation": self.average_correlation,
            "correlation_regime": self.correlation_regime,
            "sector_rotation_phase": self.sector_rotation_phase,
            "leading_sectors": list(self.leading_sectors),
            "lagging_sectors": list(self.lagging_sectors),
            "opening_drive_strength": self.opening_drive_strength,
            "first_30min_range_ratio": self.first_30min_range_ratio,
            "vwap_slope": self.vwap_slope,
            "direction_change_count": self.direction_change_count,
            "intraday_character": self.intraday_character,
            "vol_regime_phase": self.vol_regime_phase.value if self.vol_regime_phase is not None else None,
            "vol_regime_momentum": self.vol_regime_momentum.value if self.vol_regime_momentum is not None else None,
            "term_structure_regime": self.term_structure_regime.value if self.term_structure_regime is not None else None,
            "variance_risk_premium": self.variance_risk_premium.value if self.variance_risk_premium is not None else None,
            "vix_close": self.vix_close,
            "primary_regime": self.primary_regime.value,
            "regime_confidence": self.regime_confidence,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegimeVector:
        """Deserialize from a dictionary.

        Args:
            data: Dictionary with RegimeVector fields.

        Returns:
            Reconstructed RegimeVector instance.
        """
        return cls(
            computed_at=datetime.fromisoformat(data["computed_at"]),
            trend_score=float(data["trend_score"]),
            trend_conviction=float(data["trend_conviction"]),
            volatility_level=float(data["volatility_level"]),
            volatility_direction=float(data["volatility_direction"]),
            universe_breadth_score=data.get("universe_breadth_score"),
            breadth_thrust=data.get("breadth_thrust"),
            average_correlation=data.get("average_correlation"),
            correlation_regime=data.get("correlation_regime"),
            sector_rotation_phase=data.get("sector_rotation_phase"),
            leading_sectors=data.get("leading_sectors", []),
            lagging_sectors=data.get("lagging_sectors", []),
            opening_drive_strength=data.get("opening_drive_strength"),
            first_30min_range_ratio=data.get("first_30min_range_ratio"),
            vwap_slope=data.get("vwap_slope"),
            direction_change_count=data.get("direction_change_count"),
            intraday_character=data.get("intraday_character"),
            vol_regime_phase=VolRegimePhase(data["vol_regime_phase"]) if data.get("vol_regime_phase") is not None else None,
            vol_regime_momentum=VolRegimeMomentum(data["vol_regime_momentum"]) if data.get("vol_regime_momentum") is not None else None,
            term_structure_regime=TermStructureRegime(data["term_structure_regime"]) if data.get("term_structure_regime") is not None else None,
            variance_risk_premium=VRPTier(data["variance_risk_premium"]) if data.get("variance_risk_premium") is not None else None,
            vix_close=float(data["vix_close"]) if data.get("vix_close") is not None else None,
            primary_regime=MarketRegime(data["primary_regime"]),
            regime_confidence=float(data["regime_confidence"]),
        )

    def matches_conditions(self, conditions: RegimeOperatingConditions) -> bool:
        """Check if this RegimeVector satisfies all operating conditions.

        For each non-None range constraint: the corresponding RegimeVector
        field must be non-None and within [min, max] inclusive.
        For each non-None string list constraint: the corresponding field
        must be non-None and present in the allowed list.
        Empty conditions (all None) → always matches (vacuously true).

        Args:
            conditions: The operating conditions to check against.

        Returns:
            True if all non-None conditions are satisfied, False otherwise.
        """
        # Float range checks: (field_value, constraint)
        range_checks: list[tuple[float | None, tuple[float, float] | None]] = [
            (self.trend_score, conditions.trend_score),
            (self.trend_conviction, conditions.trend_conviction),
            (self.volatility_level, conditions.volatility_level),
            (self.universe_breadth_score, conditions.universe_breadth_score),
            (self.average_correlation, conditions.average_correlation),
            (self.regime_confidence, conditions.regime_confidence),
        ]
        for field_value, constraint in range_checks:
            if constraint is None:
                continue
            if field_value is None:
                return False
            low, high = constraint
            if not (low <= field_value <= high):
                return False

        # String list checks: (field_value, constraint)
        string_checks: list[tuple[str | None, list[str] | None]] = [
            (self.correlation_regime, conditions.correlation_regime),
            (self.sector_rotation_phase, conditions.sector_rotation_phase),
            (self.intraday_character, conditions.intraday_character),
        ]
        for field_value, constraint in string_checks:
            if constraint is None:
                continue
            if field_value is None:
                return False
            if field_value not in constraint:
                return False

        # VIX landscape enum checks (Sprint 27.9): condition None → skip,
        # vector None → match (match-any from vector side),
        # both non-None → compare equality.
        vix_enum_checks: list[tuple[StrEnum | None, StrEnum | None]] = [
            (self.vol_regime_phase, conditions.vol_regime_phase),
            (self.vol_regime_momentum, conditions.vol_regime_momentum),
            (self.term_structure_regime, conditions.term_structure_regime),
            (self.variance_risk_premium, conditions.variance_risk_premium),
        ]
        for field_value, constraint in vix_enum_checks:
            if constraint is None:
                continue
            if field_value is None:
                continue  # match-any from vector side
            if field_value != constraint:
                return False

        return True


@dataclass(frozen=True)
class RegimeOperatingConditions:
    """Defines acceptable regime ranges for strategy activation.

    Each field constrains a corresponding RegimeVector dimension.
    None means unconstrained (always matches). All non-None conditions
    must match (AND logic).

    Float dimensions use (min, max) inclusive ranges.
    String dimensions use list-of-allowed-values matching.

    Attributes:
        trend_score: Acceptable range for trend_score (-1.0 to +1.0).
        trend_conviction: Acceptable range for trend_conviction (0.0 to 1.0).
        volatility_level: Acceptable range for volatility_level.
        universe_breadth_score: Acceptable range for universe_breadth_score.
        average_correlation: Acceptable range for average_correlation.
        regime_confidence: Acceptable range for regime_confidence.
        correlation_regime: Allowed correlation regime strings.
        sector_rotation_phase: Allowed sector rotation phase strings.
        intraday_character: Allowed intraday character strings.
    """

    # Float range constraints (min, max inclusive)
    trend_score: tuple[float, float] | None = None
    trend_conviction: tuple[float, float] | None = None
    volatility_level: tuple[float, float] | None = None
    universe_breadth_score: tuple[float, float] | None = None
    average_correlation: tuple[float, float] | None = None
    regime_confidence: tuple[float, float] | None = None

    # String list constraints
    correlation_regime: list[str] | None = None
    sector_rotation_phase: list[str] | None = None
    intraday_character: list[str] | None = None

    # VIX landscape enum constraints (Sprint 27.9)
    vol_regime_phase: Optional[VolRegimePhase] = None
    vol_regime_momentum: Optional[VolRegimeMomentum] = None
    term_structure_regime: Optional[TermStructureRegime] = None
    variance_risk_premium: Optional[VRPTier] = None


class BreadthCalculator(Protocol):
    """Protocol for breadth dimension calculators."""

    def compute(self, indicators: RegimeIndicators) -> tuple[float | None, bool | None]:
        """Compute breadth score and thrust flag."""
        ...


class CorrelationCalculator(Protocol):
    """Protocol for correlation dimension calculators."""

    def compute(self, indicators: RegimeIndicators) -> tuple[float | None, str | None]:
        """Compute average correlation and regime string."""
        ...


class SectorRotationCalculator(Protocol):
    """Protocol for sector rotation dimension calculators."""

    def compute(
        self, indicators: RegimeIndicators
    ) -> tuple[str | None, list[str], list[str]]:
        """Compute rotation phase, leading sectors, lagging sectors."""
        ...


class IntradayCalculator(Protocol):
    """Protocol for intraday character dimension calculators."""

    def compute(
        self, indicators: RegimeIndicators
    ) -> tuple[float | None, float | None, float | None, int | None, str | None]:
        """Compute opening_drive, range_ratio, vwap_slope, direction_changes, character."""
        ...


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
        above_sma_20 = price > indicators.spy_sma_20 if indicators.spy_sma_20 is not None else None
        above_sma_50 = price > indicators.spy_sma_50 if indicators.spy_sma_50 is not None else None
        below_sma_20 = price < indicators.spy_sma_20 if indicators.spy_sma_20 is not None else None
        below_sma_50 = price < indicators.spy_sma_50 if indicators.spy_sma_50 is not None else None

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


class RegimeClassifierV2:
    """Multi-dimensional regime classifier (Sprint 27.6).

    Produces a RegimeVector capturing 6 regime dimensions. Delegates
    primary_regime classification to V1 RegimeClassifier — no reimplementation
    of trend/vol scoring logic.

    Optional dimension calculators (breadth, correlation, sector, intraday)
    default to None, filling those dimensions with defaults until the
    calculators are wired.

    Args:
        config: Orchestrator config (for V1 delegation).
        regime_config: RegimeIntelligenceConfig with dimension-specific settings.
        breadth: Optional BreadthCalculator instance.
        correlation: Optional MarketCorrelationTracker instance.
        sector: Optional SectorRotationAnalyzer instance.
        intraday: Optional IntradayCharacterDetector instance.
    """

    def __init__(
        self,
        config: OrchestratorConfig,
        regime_config: RegimeIntelligenceConfig,
        breadth: BreadthCalcImpl | None = None,
        correlation: MarketCorrelationTracker | None = None,
        sector: SectorRotationAnalyzer | None = None,
        intraday: IntradayCharacterDetector | None = None,
        vix_data_service: VIXDataService | None = None,
    ) -> None:
        """Initialize V2 classifier with V1 delegation and optional calculators."""
        self._v1_classifier = RegimeClassifier(config)
        self._regime_config = regime_config
        self._breadth = breadth
        self._correlation = correlation
        self._sector = sector
        self._intraday = intraday
        self._vix_data_service = vix_data_service

        # VIX calculators — instantiated when service provided and config enabled
        self._vol_phase_calc = None
        self._vol_momentum_calc = None
        self._term_structure_calc = None
        self._vrp_calc = None

        if vix_data_service is not None and regime_config.vix_calculators_enabled:
            from argus.core.vix_calculators import (
                TermStructureRegimeCalculator,
                VarianceRiskPremiumCalculator,
                VolRegimeMomentumCalculator,
                VolRegimePhaseCalculator,
            )
            from argus.data.vix_config import VixRegimeConfig

            # Get VIX config from the service for boundary access
            vix_config: VixRegimeConfig = vix_data_service._config

            self._vol_phase_calc = VolRegimePhaseCalculator(
                vix_data_service, vix_config.vol_regime_boundaries
            )
            self._vol_momentum_calc = VolRegimeMomentumCalculator(
                vix_data_service,
                vix_config.momentum_window,
                vix_config.momentum_threshold,
            )
            self._term_structure_calc = TermStructureRegimeCalculator(
                vix_data_service, vix_config.term_structure_boundaries
            )
            self._vrp_calc = VarianceRiskPremiumCalculator(
                vix_data_service, vix_config.vrp_boundaries
            )

    def attach_vix_service(self, vix_data_service: VIXDataService) -> None:
        """Attach a VIX data service post-construction.

        Mirrors ``Orchestrator.attach_vix_service``. Called by the API
        lifespan handler when the VIX service is initialized lazily after
        the classifier. Calculators are NOT re-instantiated here —
        constructor-time wiring remains the canonical path; this setter
        is for the specific case where the classifier was built without
        VIX (e.g., VIX service came up later) and only needs the raw
        service reference for ``latest_vix`` reads.
        """
        self._vix_data_service = vix_data_service

    @property
    def vol_phase_calc(self):  # type: ignore[no-untyped-def]
        """VolRegimePhaseCalculator instance (or None if not wired)."""
        return self._vol_phase_calc

    @property
    def vol_momentum_calc(self):  # type: ignore[no-untyped-def]
        """VolRegimeMomentumCalculator instance (or None if not wired)."""
        return self._vol_momentum_calc

    @property
    def term_structure_calc(self):  # type: ignore[no-untyped-def]
        """TermStructureRegimeCalculator instance (or None if not wired)."""
        return self._term_structure_calc

    @property
    def vrp_calc(self):  # type: ignore[no-untyped-def]
        """VarianceRiskPremiumCalculator instance (or None if not wired)."""
        return self._vrp_calc

    def classify(self, indicators: RegimeIndicators) -> MarketRegime:
        """Classify market regime — delegates entirely to V1.

        Args:
            indicators: Computed regime indicators.

        Returns:
            MarketRegime from V1 classifier (identical result by construction).
        """
        return self._v1_classifier.classify(indicators)

    def compute_indicators(self, daily_bars: pd.DataFrame) -> RegimeIndicators:
        """Compute regime indicators from daily bars — delegates to V1.

        Args:
            daily_bars: DataFrame with OHLCV columns.

        Returns:
            RegimeIndicators computed by V1.
        """
        return self._v1_classifier.compute_indicators(daily_bars)

    async def run_pre_market(
        self,
        fetch_daily_bars_fn: Any,
        get_top_symbols_fn: Any,
    ) -> None:
        """Run pre-market data fetches for correlation and sector rotation.

        Executes MarketCorrelationTracker.compute() and SectorRotationAnalyzer.fetch()
        concurrently via asyncio.gather(). Safe to call when either calculator is None.

        Args:
            fetch_daily_bars_fn: Async callable (symbol, lookback_days) -> DataFrame | None.
            get_top_symbols_fn: Callable () -> list[str] of top symbols.
        """
        tasks: list[Any] = []

        if self._correlation is not None and self._regime_config.correlation.enabled:
            tasks.append(
                self._correlation.compute(fetch_daily_bars_fn, get_top_symbols_fn)
            )

        if self._sector is not None and self._regime_config.sector_rotation.enabled:
            tasks.append(self._sector.fetch())

        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning("Pre-market V2 task failed: %s", result)

    def compute_regime_vector(self, indicators: RegimeIndicators) -> RegimeVector:
        """Compute the full multi-dimensional RegimeVector.

        Uses V1 for primary_regime, computes trend/vol from indicators,
        and fills remaining dimensions from optional calculators (or defaults).

        Args:
            indicators: Computed regime indicators.

        Returns:
            RegimeVector with all available dimensions populated.
        """
        primary_regime = self._v1_classifier.classify(indicators)

        # Trend dimension: normalize V1 trend score to [-1, 1]
        raw_trend = self._v1_classifier._compute_trend_score(indicators)
        trend_score = max(-1.0, min(1.0, raw_trend / 2.0))

        # Trend conviction: based on agreement of SMA signals
        trend_conviction = self._compute_trend_conviction(indicators)

        # Volatility dimension
        vol_level = indicators.spy_realized_vol_20d if indicators.spy_realized_vol_20d is not None else 0.0
        vol_direction = self._compute_vol_direction(indicators)

        # Breadth dimension — query snapshot from BreadthCalculator
        breadth_score: float | None = None
        breadth_thrust: bool | None = None
        if self._breadth is not None and self._regime_config.breadth.enabled:
            snap = self._breadth.get_breadth_snapshot()
            breadth_score = snap.get("universe_breadth_score")
            breadth_thrust = snap.get("breadth_thrust")

        # Correlation dimension — query snapshot from MarketCorrelationTracker
        avg_correlation: float | None = None
        correlation_regime: str | None = None
        if self._correlation is not None and self._regime_config.correlation.enabled:
            snap = self._correlation.get_correlation_snapshot()
            avg_correlation = snap.get("average_correlation")
            correlation_regime = snap.get("correlation_regime")

        # Sector rotation dimension — query snapshot from SectorRotationAnalyzer
        sector_phase: str | None = None
        leading: list[str] = []
        lagging: list[str] = []
        if self._sector is not None and self._regime_config.sector_rotation.enabled:
            snap = self._sector.get_sector_snapshot()
            sector_phase = snap.get("sector_rotation_phase")
            leading = snap.get("leading_sectors", [])
            lagging = snap.get("lagging_sectors", [])

        # Intraday character dimension — query snapshot from IntradayCharacterDetector
        drive_strength: float | None = None
        range_ratio: float | None = None
        vwap_slope: float | None = None
        dir_changes: int | None = None
        intraday_char: str | None = None
        if self._intraday is not None and self._regime_config.intraday.enabled:
            snap = self._intraday.get_intraday_snapshot()
            drive_strength = snap.get("opening_drive_strength")
            range_ratio = snap.get("first_30min_range_ratio")
            vwap_slope = snap.get("vwap_slope")
            dir_changes = snap.get("direction_change_count")
            intraday_char = snap.get("intraday_character")

        # VIX landscape dimension (Sprint 27.9)
        vol_regime_phase: Optional[VolRegimePhase] = None
        vol_regime_momentum: Optional[VolRegimeMomentum] = None
        term_structure_regime: Optional[TermStructureRegime] = None
        variance_risk_premium: Optional[VRPTier] = None
        vix_close: Optional[float] = None

        if self._vol_phase_calc is not None:
            vol_regime_phase = self._vol_phase_calc.classify()
        if self._vol_momentum_calc is not None:
            vol_regime_momentum = self._vol_momentum_calc.classify()
        if self._term_structure_calc is not None:
            term_structure_regime = self._term_structure_calc.classify()
        if self._vrp_calc is not None:
            variance_risk_premium = self._vrp_calc.classify()

        # Extract vix_close from VIXDataService latest daily
        if self._vix_data_service is not None:
            latest_vix = self._vix_data_service.get_latest_daily()
            if latest_vix is not None:
                raw_close = latest_vix.get("vix_close")
                if raw_close is not None:
                    vix_close = float(raw_close)

        # Confidence: signal_clarity × data_completeness
        regime_confidence = self._compute_regime_confidence(
            primary_regime=primary_regime,
            trend_score=trend_score,
            vol_level=vol_level,
            breadth_score=breadth_score,
            avg_correlation=avg_correlation,
            sector_phase=sector_phase,
            intraday_char=intraday_char,
        )

        return RegimeVector(
            computed_at=datetime.now(UTC),
            trend_score=trend_score,
            trend_conviction=trend_conviction,
            volatility_level=vol_level,
            volatility_direction=vol_direction,
            universe_breadth_score=breadth_score,
            breadth_thrust=breadth_thrust,
            average_correlation=avg_correlation,
            correlation_regime=correlation_regime,
            sector_rotation_phase=sector_phase,
            leading_sectors=leading,
            lagging_sectors=lagging,
            opening_drive_strength=drive_strength,
            first_30min_range_ratio=range_ratio,
            vwap_slope=vwap_slope,
            direction_change_count=dir_changes,
            intraday_character=intraday_char,
            vol_regime_phase=vol_regime_phase,
            vol_regime_momentum=vol_regime_momentum,
            term_structure_regime=term_structure_regime,
            variance_risk_premium=variance_risk_premium,
            vix_close=vix_close,
            primary_regime=primary_regime,
            regime_confidence=regime_confidence,
        )

    def _compute_trend_conviction(self, indicators: RegimeIndicators) -> float:
        """Compute trend conviction from SMA agreement and momentum.

        Returns:
            Conviction score from 0.0 (no data/conflicting) to 1.0 (strong agreement).
        """
        signals_agree = 0
        signals_total = 0

        # SMA-20 direction
        if indicators.spy_sma_20 is not None:
            signals_total += 1
            if indicators.spy_price > indicators.spy_sma_20:
                signals_agree += 1
            elif indicators.spy_price < indicators.spy_sma_20:
                signals_agree -= 1

        # SMA-50 direction
        if indicators.spy_sma_50 is not None:
            signals_total += 1
            if indicators.spy_price > indicators.spy_sma_50:
                signals_agree += 1
            elif indicators.spy_price < indicators.spy_sma_50:
                signals_agree -= 1

        # Momentum direction
        if indicators.spy_roc_5d is not None:
            signals_total += 1
            if indicators.spy_roc_5d > 0.01:
                signals_agree += 1
            elif indicators.spy_roc_5d < -0.01:
                signals_agree -= 1

        if signals_total == 0:
            return 0.0

        return abs(signals_agree) / signals_total

    def _compute_vol_direction(self, indicators: RegimeIndicators) -> float:
        """Compute volatility direction proxy.

        Uses the relationship between current vol and typical vol thresholds
        as a simple proxy until vol term structure data is available.

        Returns:
            Float from -1.0 (vol declining) to +1.0 (vol rising).
        """
        vol = indicators.spy_realized_vol_20d
        if vol is None:
            return 0.0

        # Normalize against midpoint of normal range
        midpoint = (self._v1_classifier._config.vol_low_threshold
                    + self._v1_classifier._config.vol_high_threshold) / 2.0
        if midpoint <= 0:
            return 0.0

        deviation = (vol - midpoint) / midpoint
        return max(-1.0, min(1.0, deviation))

    def _compute_regime_confidence(
        self,
        primary_regime: MarketRegime,
        trend_score: float,
        vol_level: float,
        breadth_score: float | None,
        avg_correlation: float | None,
        sector_phase: str | None,
        intraday_char: str | None,
    ) -> float:
        """Compute regime confidence as signal_clarity × data_completeness.

        Signal clarity (per C1 spec):
        - crisis → 0.95
        - strong trend + clear vol → 0.85
        - moderate + confirming → 0.70
        - conflicting → 0.50
        - indeterminate → 0.40

        Data completeness: dimensions_with_real_data / enabled_dimensions.

        Returns:
            Confidence clamped to [0.0, 1.0].
        """
        # Signal clarity
        signal_clarity = self._compute_signal_clarity(primary_regime, trend_score, vol_level)

        # Data completeness: count enabled dimensions with real data
        enabled_dimensions = 0
        dimensions_with_data = 0

        # Trend + Vol always enabled (from V1)
        enabled_dimensions += 2
        dimensions_with_data += 2  # Always have trend and vol from V1

        # Breadth
        if self._regime_config.breadth.enabled:
            enabled_dimensions += 1
            if breadth_score is not None:
                dimensions_with_data += 1

        # Correlation
        if self._regime_config.correlation.enabled:
            enabled_dimensions += 1
            if avg_correlation is not None:
                dimensions_with_data += 1

        # Sector rotation
        if self._regime_config.sector_rotation.enabled:
            enabled_dimensions += 1
            if sector_phase is not None:
                dimensions_with_data += 1

        # Intraday
        if self._regime_config.intraday.enabled:
            enabled_dimensions += 1
            if intraday_char is not None:
                dimensions_with_data += 1

        data_completeness = dimensions_with_data / enabled_dimensions if enabled_dimensions > 0 else 0.0

        return max(0.0, min(1.0, signal_clarity * data_completeness))

    def _compute_signal_clarity(
        self,
        primary_regime: MarketRegime,
        trend_score: float,
        vol_level: float,
    ) -> float:
        """Compute signal clarity component of confidence.

        Returns:
            Clarity score from 0.40 to 0.95.
        """
        # Crisis: highest clarity (extreme conditions are unambiguous)
        if primary_regime == MarketRegime.CRISIS:
            return 0.95

        # Strong trend with clear vol signal
        if abs(trend_score) >= 0.75 and vol_level > 0:
            return 0.85

        # Moderate trend with confirming signals
        if abs(trend_score) >= 0.25:
            return 0.70

        # Conflicting signals (near-zero trend)
        if abs(trend_score) > 0.0:
            return 0.50

        # Indeterminate (no trend signal at all)
        return 0.40
