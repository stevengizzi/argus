"""VIX-based regime calculators (Sprint 27.9, Session 2b).

Four calculators that consume VIXDataService data to classify the VIX
landscape dimension of RegimeVector. Each follows the Sprint 27.6
calculator pattern: accept a data source in constructor, expose a
classify() method that returns the enum value or None.

All calculators return None when VIX data is unavailable or stale.
"""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING

from argus.data.vix_config import (
    TermStructureRegime,
    VolRegimeMomentum,
    VolRegimePhase,
    VRPTier,
)

if TYPE_CHECKING:
    from argus.data.vix_config import (
        TermStructureBoundaries,
        VolRegimeBoundaries,
        VRPBoundaries,
    )
    from argus.data.vix_data_service import VIXDataService

logger = logging.getLogger(__name__)


class VolRegimePhaseCalculator:
    """Classify current position in vol-of-vol phase space.

    Uses 2D coordinates (vol_of_vol_ratio, vix_percentile) to determine
    whether the volatility environment is calm, transitioning, expanding,
    or in crisis. CRISIS check has highest priority.

    Args:
        vix_service: VIXDataService providing daily VIX metrics.
        boundaries: VolRegimeBoundaries with phase thresholds.
    """

    def __init__(
        self,
        vix_service: VIXDataService,
        boundaries: VolRegimeBoundaries,
    ) -> None:
        """Initialize with VIX data source and boundary thresholds."""
        self._vix_service = vix_service
        self._boundaries = boundaries

    def classify(self) -> VolRegimePhase | None:
        """Classify the current vol regime phase.

        Returns:
            VolRegimePhase enum value, or None if data unavailable.
        """
        if not self._vix_service.is_ready or self._vix_service.is_stale:
            return None

        latest = self._vix_service.get_latest_daily()
        if latest is None:
            return None

        x = latest.get("vol_of_vol_ratio")
        y = latest.get("vix_percentile")
        if x is None or y is None:
            return None

        bounds = self._boundaries

        # CRISIS check first (highest priority)
        if y >= bounds.crisis_min_y:
            return VolRegimePhase.CRISIS

        if x <= bounds.calm_max_x and y <= bounds.calm_max_y:
            return VolRegimePhase.CALM

        if x <= bounds.transition_max_x and y <= bounds.transition_max_y:
            return VolRegimePhase.TRANSITION

        return VolRegimePhase.VOL_EXPANSION


class VolRegimeMomentumCalculator:
    """Classify directional momentum in vol-of-vol coordinate space.

    Computes Euclidean displacement between current and N-days-ago
    coordinates to determine whether vol conditions are stabilizing,
    neutral, or deteriorating.

    Args:
        vix_service: VIXDataService providing daily VIX metrics.
        momentum_window: Number of days to look back for displacement.
        momentum_threshold: Minimum displacement magnitude to be non-neutral.
    """

    # Attractor point — the "calm center" of vol phase space
    _ATTRACTOR_X = 0.94
    _ATTRACTOR_Y = 0.38

    def __init__(
        self,
        vix_service: VIXDataService,
        momentum_window: int,
        momentum_threshold: float,
    ) -> None:
        """Initialize with VIX data source and momentum parameters."""
        self._vix_service = vix_service
        self._momentum_window = momentum_window
        self._momentum_threshold = momentum_threshold

    def classify(self) -> VolRegimeMomentum | None:
        """Classify vol regime momentum direction.

        Returns:
            VolRegimeMomentum enum value, or None if data unavailable.
        """
        if not self._vix_service.is_ready or self._vix_service.is_stale:
            return None

        history = self._vix_service.get_history(self._momentum_window)
        if history is None or len(history) < 2:
            return None

        # Current = most recent, past = oldest in the window
        current = history[0]  # Most recent (descending order)
        past = history[-1]  # Oldest

        curr_x = current.get("vol_of_vol_ratio")
        curr_y = current.get("vix_percentile")
        past_x = past.get("vol_of_vol_ratio")
        past_y = past.get("vix_percentile")

        if any(v is None for v in (curr_x, curr_y, past_x, past_y)):
            return None

        # Euclidean displacement magnitude
        dx = curr_x - past_x
        dy = curr_y - past_y
        magnitude = math.sqrt(dx * dx + dy * dy)

        if magnitude < self._momentum_threshold:
            return VolRegimeMomentum.NEUTRAL

        # Direction: moving toward attractor = stabilizing
        dist_curr = math.sqrt(
            (curr_x - self._ATTRACTOR_X) ** 2
            + (curr_y - self._ATTRACTOR_Y) ** 2
        )
        dist_past = math.sqrt(
            (past_x - self._ATTRACTOR_X) ** 2
            + (past_y - self._ATTRACTOR_Y) ** 2
        )

        if dist_curr < dist_past:
            return VolRegimeMomentum.STABILIZING

        return VolRegimeMomentum.DETERIORATING


class TermStructureRegimeCalculator:
    """Classify VIX term structure regime.

    Uses the term structure proxy (VIX/VIX_MA) and VIX percentile to
    classify into contango/backwardation × low/high quadrants.

    Args:
        vix_service: VIXDataService providing daily VIX metrics.
        boundaries: TermStructureBoundaries with contango/percentile thresholds.
    """

    def __init__(
        self,
        vix_service: VIXDataService,
        boundaries: TermStructureBoundaries,
    ) -> None:
        """Initialize with VIX data source and boundary thresholds."""
        self._vix_service = vix_service
        self._boundaries = boundaries

    def classify(self) -> TermStructureRegime | None:
        """Classify the current term structure regime.

        Returns:
            TermStructureRegime enum value, or None if data unavailable.
        """
        if not self._vix_service.is_ready or self._vix_service.is_stale:
            return None

        latest = self._vix_service.get_latest_daily()
        if latest is None:
            return None

        x = latest.get("term_structure_proxy")
        y = latest.get("vix_percentile")
        if x is None or y is None:
            return None

        bounds = self._boundaries
        is_contango = x <= bounds.contango_threshold
        is_low = y < bounds.low_high_percentile_split

        if is_contango and is_low:
            return TermStructureRegime.CONTANGO_LOW
        if is_contango and not is_low:
            return TermStructureRegime.CONTANGO_HIGH
        if not is_contango and is_low:
            return TermStructureRegime.BACKWARDATION_LOW
        return TermStructureRegime.BACKWARDATION_HIGH


class VarianceRiskPremiumCalculator:
    """Classify the Variance Risk Premium tier.

    VRP = VIX^2 - RV^2. Higher VRP means options are expensive relative
    to realized movement.

    Args:
        vix_service: VIXDataService providing daily VIX metrics.
        boundaries: VRPBoundaries with tier thresholds.
    """

    def __init__(
        self,
        vix_service: VIXDataService,
        boundaries: VRPBoundaries,
    ) -> None:
        """Initialize with VIX data source and boundary thresholds."""
        self._vix_service = vix_service
        self._boundaries = boundaries
        self._latest_vrp: float | None = None

    @property
    def vrp_value(self) -> float | None:
        """Last computed VRP value (continuous), or None if unavailable."""
        return self._latest_vrp

    def classify(self) -> VRPTier | None:
        """Classify the current VRP tier.

        Returns:
            VRPTier enum value, or None if data unavailable.
        """
        if not self._vix_service.is_ready or self._vix_service.is_stale:
            self._latest_vrp = None
            return None

        latest = self._vix_service.get_latest_daily()
        if latest is None:
            self._latest_vrp = None
            return None

        vrp = latest.get("variance_risk_premium")
        if vrp is None:
            self._latest_vrp = None
            return None

        self._latest_vrp = float(vrp)
        bounds = self._boundaries

        if vrp <= bounds.compressed_max:
            return VRPTier.COMPRESSED
        if vrp <= bounds.normal_max:
            return VRPTier.NORMAL
        if vrp <= bounds.elevated_max:
            return VRPTier.ELEVATED
        return VRPTier.EXTREME
