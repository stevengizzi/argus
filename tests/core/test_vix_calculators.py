"""Tests for VIX-based regime calculators (Sprint 27.9, Session 2b).

8 tests covering all 4 calculators + RegimeClassifierV2 integration.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pandas as pd
import pytest

from argus.core.regime import RegimeClassifierV2, RegimeVector
from argus.core.vix_calculators import (
    TermStructureRegimeCalculator,
    VarianceRiskPremiumCalculator,
    VolRegimeMomentumCalculator,
    VolRegimePhaseCalculator,
)
from argus.data.vix_config import (
    TermStructureBoundaries,
    TermStructureRegime,
    VolRegimeBoundaries,
    VolRegimeMomentum,
    VolRegimePhase,
    VRPBoundaries,
    VRPTier,
)


def _mock_vix_service(
    latest: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
    is_ready: bool = True,
    is_stale: bool = False,
) -> MagicMock:
    """Create a mock VIXDataService with configurable responses."""
    svc = MagicMock()
    type(svc).is_ready = PropertyMock(return_value=is_ready)
    type(svc).is_stale = PropertyMock(return_value=is_stale)
    svc.get_latest_daily.return_value = latest
    svc.get_history.return_value = history
    return svc


class TestVolRegimePhaseCalculator:
    """Tests for VolRegimePhaseCalculator."""

    def test_vol_regime_phase_calm(self) -> None:
        """x=0.85, y=0.30 within calm bounds → CALM."""
        svc = _mock_vix_service(
            latest={"vol_of_vol_ratio": 0.85, "vix_percentile": 0.30}
        )
        calc = VolRegimePhaseCalculator(svc, VolRegimeBoundaries())
        assert calc.classify() == VolRegimePhase.CALM

    def test_vol_regime_phase_crisis(self) -> None:
        """y=0.90 above crisis_min_y → CRISIS (takes priority over x)."""
        svc = _mock_vix_service(
            latest={"vol_of_vol_ratio": 1.5, "vix_percentile": 0.90}
        )
        calc = VolRegimePhaseCalculator(svc, VolRegimeBoundaries())
        assert calc.classify() == VolRegimePhase.CRISIS

    def test_vol_regime_phase_unavailable(self) -> None:
        """VIXDataService returns None → calculator returns None."""
        svc = _mock_vix_service(latest=None)
        calc = VolRegimePhaseCalculator(svc, VolRegimeBoundaries())
        assert calc.classify() is None


class TestTermStructureRegimeCalculator:
    """Tests for TermStructureRegimeCalculator."""

    def test_term_structure_contango_low(self) -> None:
        """x=0.95 (contango), y=0.30 (low) → CONTANGO_LOW."""
        svc = _mock_vix_service(
            latest={"term_structure_proxy": 0.95, "vix_percentile": 0.30}
        )
        calc = TermStructureRegimeCalculator(svc, TermStructureBoundaries())
        assert calc.classify() == TermStructureRegime.CONTANGO_LOW

    def test_term_structure_backwardation_high(self) -> None:
        """x=1.15 (backwardation), y=0.70 (high) → BACKWARDATION_HIGH."""
        svc = _mock_vix_service(
            latest={"term_structure_proxy": 1.15, "vix_percentile": 0.70}
        )
        calc = TermStructureRegimeCalculator(svc, TermStructureBoundaries())
        assert calc.classify() == TermStructureRegime.BACKWARDATION_HIGH


class TestVarianceRiskPremiumCalculator:
    """Tests for VarianceRiskPremiumCalculator."""

    def test_vrp_tiers(self) -> None:
        """Test all 4 VRP tier boundaries."""
        bounds = VRPBoundaries()  # compressed_max=0, normal_max=50, elevated_max=150

        # COMPRESSED: vrp <= 0
        svc = _mock_vix_service(latest={"variance_risk_premium": -10.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.COMPRESSED
        assert calc.vrp_value == -10.0

        # NORMAL: 0 < vrp <= 50
        svc = _mock_vix_service(latest={"variance_risk_premium": 25.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.NORMAL
        assert calc.vrp_value == 25.0

        # ELEVATED: 50 < vrp <= 150
        svc = _mock_vix_service(latest={"variance_risk_premium": 100.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.ELEVATED
        assert calc.vrp_value == 100.0

        # EXTREME: vrp > 150
        svc = _mock_vix_service(latest={"variance_risk_premium": 200.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.EXTREME
        assert calc.vrp_value == 200.0

        # Boundary values
        svc = _mock_vix_service(latest={"variance_risk_premium": 0.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.COMPRESSED  # <= 0

        svc = _mock_vix_service(latest={"variance_risk_premium": 50.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.NORMAL  # <= 50

        svc = _mock_vix_service(latest={"variance_risk_premium": 150.0})
        calc = VarianceRiskPremiumCalculator(svc, bounds)
        assert calc.classify() == VRPTier.ELEVATED  # <= 150


class TestVolRegimeMomentumCalculator:
    """Tests for VolRegimeMomentumCalculator."""

    def test_momentum_stabilizing(self) -> None:
        """5-day displacement toward attractor → STABILIZING."""
        # Attractor is at (0.94, 0.38)
        # Past: far from attractor at (1.3, 0.70)
        # Current: closer to attractor at (1.0, 0.45)
        history = [
            {"vol_of_vol_ratio": 1.0, "vix_percentile": 0.45},  # current (most recent)
            {"vol_of_vol_ratio": 1.1, "vix_percentile": 0.55},
            {"vol_of_vol_ratio": 1.15, "vix_percentile": 0.60},
            {"vol_of_vol_ratio": 1.2, "vix_percentile": 0.65},
            {"vol_of_vol_ratio": 1.3, "vix_percentile": 0.70},  # past (oldest)
        ]
        svc = _mock_vix_service(history=history)
        calc = VolRegimeMomentumCalculator(svc, momentum_window=5, momentum_threshold=0.1)
        assert calc.classify() == VolRegimeMomentum.STABILIZING

    def test_momentum_insufficient_history(self) -> None:
        """Fewer than 2 history records → None."""
        svc = _mock_vix_service(history=[{"vol_of_vol_ratio": 1.0, "vix_percentile": 0.45}])
        calc = VolRegimeMomentumCalculator(svc, momentum_window=5, momentum_threshold=0.1)
        assert calc.classify() is None

    def test_momentum_not_ready(self) -> None:
        """VIXDataService not ready → None."""
        svc = _mock_vix_service(is_ready=False)
        calc = VolRegimeMomentumCalculator(svc, momentum_window=5, momentum_threshold=0.1)
        assert calc.classify() is None


class TestRegimeClassifierV2VixIntegration:
    """Tests for RegimeClassifierV2 with VIX calculators wired."""

    def test_classifier_v2_populates_new_fields(self) -> None:
        """Full V2 with mocked VIXDataService → RegimeVector has non-None VIX fields."""
        from argus.core.config import (
            BreadthConfig,
            CorrelationConfig,
            IntradayConfig,
            OrchestratorConfig,
            RegimeIntelligenceConfig,
            SectorRotationConfig,
        )
        from argus.data.vix_config import VixRegimeConfig

        orch_config = OrchestratorConfig()
        regime_config = RegimeIntelligenceConfig(
            vix_calculators_enabled=True,
            breadth=BreadthConfig(enabled=False),
            correlation=CorrelationConfig(enabled=False),
            sector_rotation=SectorRotationConfig(enabled=False),
            intraday=IntradayConfig(enabled=False),
        )

        vix_config = VixRegimeConfig()
        svc = _mock_vix_service(
            latest={
                "vol_of_vol_ratio": 0.85,
                "vix_percentile": 0.30,
                "term_structure_proxy": 0.95,
                "variance_risk_premium": 25.0,
                "vix_close": 18.5,
            },
            history=[
                {"vol_of_vol_ratio": 0.85, "vix_percentile": 0.30},
                {"vol_of_vol_ratio": 0.90, "vix_percentile": 0.35},
                {"vol_of_vol_ratio": 0.95, "vix_percentile": 0.40},
                {"vol_of_vol_ratio": 1.00, "vix_percentile": 0.45},
                {"vol_of_vol_ratio": 1.05, "vix_percentile": 0.50},
            ],
        )
        # FIX-05 (DEF-091): RegimeClassifierV2 now uses svc.config (public);
        # keep svc._config for any remaining legacy paths.
        type(svc).config = PropertyMock(return_value=vix_config)
        svc._config = vix_config

        classifier = RegimeClassifierV2(
            config=orch_config,
            regime_config=regime_config,
            vix_data_service=svc,
        )

        # Build minimal indicators for V1
        daily_bars = pd.DataFrame({
            "open": [100.0] * 55,
            "high": [105.0] * 55,
            "low": [95.0] * 55,
            "close": [102.0] * 55,
            "volume": [1000000] * 55,
        })
        indicators = classifier.compute_indicators(daily_bars)
        vector = classifier.compute_regime_vector(indicators)

        assert isinstance(vector, RegimeVector)
        assert vector.vol_regime_phase == VolRegimePhase.CALM
        assert vector.vol_regime_momentum is not None  # STABILIZING or NEUTRAL
        assert vector.term_structure_regime == TermStructureRegime.CONTANGO_LOW
        assert vector.variance_risk_premium == VRPTier.NORMAL
        assert vector.vix_close == 18.5

        # Existing 6 dimensions must still be populated
        assert vector.trend_score is not None
        assert vector.volatility_level is not None
        assert vector.primary_regime is not None

    def test_classifier_v2_no_vix_service_unchanged(self) -> None:
        """V2 without VIXDataService → VIX fields stay None, 6 dims unchanged."""
        from argus.core.config import (
            OrchestratorConfig,
            RegimeIntelligenceConfig,
        )

        orch_config = OrchestratorConfig()
        regime_config = RegimeIntelligenceConfig(
            vix_calculators_enabled=True,
        )

        classifier = RegimeClassifierV2(
            config=orch_config,
            regime_config=regime_config,
            vix_data_service=None,
        )

        daily_bars = pd.DataFrame({
            "open": [100.0] * 55,
            "high": [105.0] * 55,
            "low": [95.0] * 55,
            "close": [102.0] * 55,
            "volume": [1000000] * 55,
        })
        indicators = classifier.compute_indicators(daily_bars)
        vector = classifier.compute_regime_vector(indicators)

        assert vector.vol_regime_phase is None
        assert vector.vol_regime_momentum is None
        assert vector.term_structure_regime is None
        assert vector.variance_risk_premium is None
        assert vector.vix_close is None

        # Existing 6 dimensions must still work
        assert vector.trend_score is not None
        assert vector.volatility_level is not None
        assert vector.primary_regime is not None
