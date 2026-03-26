"""VIX Regime configuration models and enums.

Pydantic models for the VIX landscape dimension of regime intelligence.
Defines volatility regime phases, term structure regimes, variance risk
premium tiers, and all boundary parameters.

Sprint 27.9, Session 1a.
"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class VolRegimePhase(StrEnum):
    """Volatility regime phase classification.

    Position in vol-of-vol phase space (σ_short/σ_long, VIX_percentile).
    """

    CALM = "calm"
    TRANSITION = "transition"
    VOL_EXPANSION = "vol_expansion"
    CRISIS = "crisis"


class VolRegimeMomentum(StrEnum):
    """Volatility momentum direction.

    5-day directional change in vol-of-vol coordinate space.
    """

    STABILIZING = "stabilizing"
    NEUTRAL = "neutral"
    DETERIORATING = "deteriorating"


class TermStructureRegime(StrEnum):
    """VIX term structure regime.

    Position in term structure phase space (VIX/VIX_MA, VIX_percentile).
    """

    CONTANGO_LOW = "contango_low"
    CONTANGO_HIGH = "contango_high"
    BACKWARDATION_LOW = "backwardation_low"
    BACKWARDATION_HIGH = "backwardation_high"


class VRPTier(StrEnum):
    """Variance Risk Premium tier."""

    COMPRESSED = "compressed"
    NORMAL = "normal"
    ELEVATED = "elevated"
    EXTREME = "extreme"


# ---------------------------------------------------------------------------
# Boundary Sub-Models
# ---------------------------------------------------------------------------


class VolRegimeBoundaries(BaseModel):
    """Boundary thresholds for volatility regime phase classification.

    Uses a 2D space of (vol_of_vol_ratio x, vix_percentile y) to classify
    the current volatility environment into one of four phases.
    """

    calm_max_x: float = Field(
        default=1.0,
        description="Max vol-of-vol ratio for calm regime",
    )
    calm_max_y: float = Field(
        default=0.50,
        description="Max VIX percentile for calm regime",
    )
    transition_max_x: float = Field(
        default=1.3,
        description="Max vol-of-vol ratio for transition regime",
    )
    transition_max_y: float = Field(
        default=0.70,
        description="Max VIX percentile for transition regime",
    )
    crisis_min_y: float = Field(
        default=0.85,
        description="Min VIX percentile for crisis regime",
    )


class TermStructureBoundaries(BaseModel):
    """Boundary thresholds for VIX term structure regime classification.

    Uses the ratio of front-month to back-month VIX futures (or proxy)
    to classify contango vs backwardation.
    """

    contango_threshold: float = Field(
        default=1.0,
        description="Ratio at or below which term structure is contango",
    )
    low_high_percentile_split: float = Field(
        default=0.50,
        description="Percentile split for low vs high contango/backwardation",
    )


class VRPBoundaries(BaseModel):
    """Boundary thresholds for Variance Risk Premium tier classification.

    VRP = implied vol (VIX) - realized vol. Positive VRP means options
    are expensive relative to realized movement.
    """

    compressed_max: float = Field(
        default=0.0,
        description="Max VRP for compressed tier (negative VRP)",
    )
    normal_max: float = Field(
        default=50.0,
        description="Max VRP for normal tier",
    )
    elevated_max: float = Field(
        default=150.0,
        description="Max VRP for elevated tier (above = extreme)",
    )


# ---------------------------------------------------------------------------
# Top-Level VIX Regime Config
# ---------------------------------------------------------------------------


class VixRegimeConfig(BaseModel):
    """Configuration for the VIX landscape dimension of regime intelligence.

    Gates the VIX data service and derived metric computation.
    All boundary sub-models use sensible defaults that can be overridden
    via config/vix_regime.yaml.
    """

    enabled: bool = False

    # Data source symbols
    yahoo_symbol_vix: str = "^VIX"
    yahoo_symbol_spx: str = "^GSPC"

    # Rolling window sizes (trading days)
    vol_short_window: int = Field(default=5, ge=1, description="Short vol-of-vol window")
    vol_long_window: int = Field(default=20, ge=2, description="Long vol-of-vol window")
    percentile_window: int = Field(default=252, ge=20, description="VIX percentile lookback")
    ma_window: int = Field(default=20, ge=2, description="VIX moving average window")
    rv_window: int = Field(default=20, ge=2, description="Realized vol window (SPX)")

    # Momentum detection
    momentum_window: int = Field(default=5, ge=1, description="VIX momentum lookback")
    momentum_threshold: float = Field(
        default=2.0, gt=0, description="VIX points change for rising/falling"
    )

    # Update and staleness
    update_interval_seconds: int = Field(
        default=300, ge=60, description="Seconds between data refreshes"
    )
    history_years: int = Field(
        default=3, ge=1, description="Years of historical data to fetch"
    )
    max_staleness_days: int = Field(
        default=3, ge=1, description="Max business days before data is stale"
    )

    # FMP fallback (Starter plan may not support ^VIX)
    fmp_fallback_enabled: bool = False

    # Boundary sub-models
    vol_regime_boundaries: VolRegimeBoundaries = Field(
        default_factory=VolRegimeBoundaries
    )
    term_structure_boundaries: TermStructureBoundaries = Field(
        default_factory=TermStructureBoundaries
    )
    vrp_boundaries: VRPBoundaries = Field(default_factory=VRPBoundaries)

    @model_validator(mode="after")
    def validate_window_ordering(self) -> VixRegimeConfig:
        """Ensure vol_short_window < vol_long_window."""
        if self.vol_short_window >= self.vol_long_window:
            raise ValueError(
                f"vol_short_window ({self.vol_short_window}) must be less than "
                f"vol_long_window ({self.vol_long_window})"
            )
        return self
