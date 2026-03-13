"""Tests for DynamicPositionSizer.

Sprint 24, Session 5a.
"""

from argus.intelligence.config import QualityEngineConfig
from argus.intelligence.position_sizer import DynamicPositionSizer
from argus.intelligence.quality_engine import SetupQuality


def _make_quality(grade: str, score: float = 75.0) -> SetupQuality:
    """Helper to build a SetupQuality with a given grade."""
    return SetupQuality(
        score=score,
        grade=grade,
        risk_tier=grade,
        components={},
        rationale="test",
    )


class TestDynamicPositionSizer:
    """Tests for DynamicPositionSizer share calculation."""

    def setup_method(self) -> None:
        self.config = QualityEngineConfig()
        self.sizer = DynamicPositionSizer(self.config)

    def test_sizer_a_plus_larger_than_b(self) -> None:
        """A+ grade produces more shares than B grade (same setup)."""
        quality_a_plus = _make_quality("A+", 95.0)
        quality_b = _make_quality("B", 55.0)

        shares_a_plus = self.sizer.calculate_shares(
            quality_a_plus, entry_price=100.0, stop_price=99.0,
            allocated_capital=100_000.0, buying_power=200_000.0,
        )
        shares_b = self.sizer.calculate_shares(
            quality_b, entry_price=100.0, stop_price=99.0,
            allocated_capital=100_000.0, buying_power=200_000.0,
        )
        assert shares_a_plus > shares_b

    def test_sizer_midpoint_calculation(self) -> None:
        """A grade (1.5%-2.0%) uses midpoint 1.75% risk."""
        quality = _make_quality("A", 85.0)
        # risk_pct = (0.015 + 0.02) / 2 = 0.0175
        # risk_dollars = 100_000 * 0.0175 = 1750
        # risk_per_share = |100 - 99| = 1.0
        # shares = int(1750 / 1.0) = 1750
        shares = self.sizer.calculate_shares(
            quality, entry_price=100.0, stop_price=99.0,
            allocated_capital=100_000.0, buying_power=500_000.0,
        )
        assert shares == 1750

    def test_sizer_zero_risk_per_share(self) -> None:
        """Entry == stop → 0 shares (no risk per share)."""
        quality = _make_quality("A+", 95.0)
        shares = self.sizer.calculate_shares(
            quality, entry_price=100.0, stop_price=100.0,
            allocated_capital=100_000.0, buying_power=200_000.0,
        )
        assert shares == 0

    def test_sizer_buying_power_limit(self) -> None:
        """Large position reduced by buying power constraint."""
        quality = _make_quality("A+", 95.0)
        # risk_pct = (0.02 + 0.03) / 2 = 0.025
        # risk_dollars = 100_000 * 0.025 = 2500
        # risk_per_share = |100 - 99| = 1.0
        # uncapped shares = 2500
        # cost = 2500 * 100 = 250_000 > buying_power (50_000)
        # capped shares = int(50_000 / 100) = 500
        shares = self.sizer.calculate_shares(
            quality, entry_price=100.0, stop_price=99.0,
            allocated_capital=100_000.0, buying_power=50_000.0,
        )
        assert shares == 500

    def test_sizer_returns_zero_for_tiny_position(self) -> None:
        """Very small capital → 0 shares (int truncation)."""
        quality = _make_quality("C+", 35.0)
        # risk_pct = (0.0025 + 0.0025) / 2 = 0.0025
        # risk_dollars = 100 * 0.0025 = 0.25
        # risk_per_share = |100 - 99| = 1.0
        # shares = int(0.25 / 1.0) = 0
        shares = self.sizer.calculate_shares(
            quality, entry_price=100.0, stop_price=99.0,
            allocated_capital=100.0, buying_power=200_000.0,
        )
        assert shares == 0

    def test_sizer_negative_entry_price(self) -> None:
        """Negative entry price returns 0 shares."""
        quality = _make_quality("A", 85.0)
        shares = self.sizer.calculate_shares(
            quality, entry_price=-1.0, stop_price=99.0,
            allocated_capital=100_000.0, buying_power=200_000.0,
        )
        assert shares == 0

    def test_sizer_all_grades_produce_shares(self) -> None:
        """Every valid grade produces a non-negative share count."""
        from argus.intelligence.config import VALID_GRADES

        for grade in VALID_GRADES:
            quality = _make_quality(grade)
            shares = self.sizer.calculate_shares(
                quality, entry_price=50.0, stop_price=49.0,
                allocated_capital=100_000.0, buying_power=500_000.0,
            )
            assert shares >= 0, f"Grade {grade} returned negative shares"
