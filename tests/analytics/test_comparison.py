"""Tests for argus.analytics.comparison — individual comparison API.

Sprint 27.5 Session 3.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime

import pytest

from argus.analytics.comparison import (
    COMPARISON_METRICS,
    compare,
    format_comparison_report,
    is_regime_robust,
    pareto_frontier,
    soft_dominance,
)
from argus.analytics.evaluation import (
    ComparisonVerdict,
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
)


def _make_mor(
    *,
    strategy_id: str = "test_strategy",
    sharpe: float = 1.5,
    drawdown: float = -0.10,
    pf: float = 2.0,
    wr: float = 0.55,
    expectancy: float = 0.3,
    total_trades: int = 100,
    confidence: ConfidenceTier = ConfidenceTier.HIGH,
    regimes: dict[str, RegimeMetrics] | None = None,
    param_hash: str = "abc12345",
) -> MultiObjectiveResult:
    """Helper to create a MultiObjectiveResult with sensible defaults."""
    return MultiObjectiveResult(
        strategy_id=strategy_id,
        parameter_hash=param_hash,
        evaluation_date=datetime.now(UTC),
        data_range=(date(2025, 1, 1), date(2025, 12, 31)),
        sharpe_ratio=sharpe,
        max_drawdown_pct=drawdown,
        profit_factor=pf,
        win_rate=wr,
        total_trades=total_trades,
        expectancy_per_trade=expectancy,
        confidence_tier=confidence,
        regime_results=regimes or {},
    )


# ── compare() ────────────────────────────────────────────────────────


class TestCompare:
    """Tests for the compare() function."""

    def test_compare_dominates(self) -> None:
        """A better on all 5 metrics → DOMINATES."""
        a = _make_mor(sharpe=2.0, drawdown=-0.05, pf=3.0, wr=0.65, expectancy=0.5)
        b = _make_mor(sharpe=1.0, drawdown=-0.10, pf=1.5, wr=0.50, expectancy=0.2)
        assert compare(a, b) == ComparisonVerdict.DOMINATES

    def test_compare_dominated(self) -> None:
        """B better on all 5 → DOMINATED."""
        a = _make_mor(sharpe=1.0, drawdown=-0.10, pf=1.5, wr=0.50, expectancy=0.2)
        b = _make_mor(sharpe=2.0, drawdown=-0.05, pf=3.0, wr=0.65, expectancy=0.5)
        assert compare(a, b) == ComparisonVerdict.DOMINATED

    def test_compare_incomparable(self) -> None:
        """A better on Sharpe, B better on drawdown → INCOMPARABLE."""
        a = _make_mor(sharpe=2.0, drawdown=-0.15, pf=2.0, wr=0.55, expectancy=0.3)
        b = _make_mor(sharpe=1.5, drawdown=-0.05, pf=2.0, wr=0.55, expectancy=0.3)
        assert compare(a, b) == ComparisonVerdict.INCOMPARABLE

    def test_compare_equal(self) -> None:
        """Identical metrics → INCOMPARABLE (neither strictly better)."""
        a = _make_mor(sharpe=1.5, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        b = _make_mor(sharpe=1.5, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        assert compare(a, b) == ComparisonVerdict.INCOMPARABLE

    def test_compare_ensemble_only(self) -> None:
        """Either ENSEMBLE_ONLY → INSUFFICIENT_DATA."""
        a = _make_mor(confidence=ConfidenceTier.ENSEMBLE_ONLY)
        b = _make_mor(confidence=ConfidenceTier.HIGH)
        assert compare(a, b) == ComparisonVerdict.INSUFFICIENT_DATA
        assert compare(b, a) == ComparisonVerdict.INSUFFICIENT_DATA

    def test_compare_nan_handling(self) -> None:
        """NaN in any metric → INSUFFICIENT_DATA."""
        a = _make_mor(sharpe=float("nan"))
        b = _make_mor()
        assert compare(a, b) == ComparisonVerdict.INSUFFICIENT_DATA

    def test_compare_inf_profit_factor(self) -> None:
        """inf > finite is True for profit_factor comparison."""
        a = _make_mor(pf=float("inf"))
        b = _make_mor(pf=5.0)
        # A has inf PF, same or better on everything else → DOMINATES
        assert compare(a, b) == ComparisonVerdict.DOMINATES


# ── pareto_frontier() ────────────────────────────────────────────────


class TestParetoFrontier:
    """Tests for the pareto_frontier() function."""

    def test_pareto_frontier_basic(self) -> None:
        """5 results, 2 non-dominated → frontier size 2."""
        # Result A: best Sharpe and expectancy
        a = _make_mor(
            strategy_id="A", sharpe=3.0, drawdown=-0.05, pf=3.0, wr=0.70, expectancy=0.6,
        )
        # Result B: best drawdown
        b = _make_mor(
            strategy_id="B", sharpe=2.5, drawdown=-0.02, pf=2.8, wr=0.65, expectancy=0.5,
        )
        # C, D, E: dominated by A or B
        c = _make_mor(
            strategy_id="C", sharpe=1.0, drawdown=-0.15, pf=1.5, wr=0.50, expectancy=0.2,
        )
        d = _make_mor(
            strategy_id="D", sharpe=0.8, drawdown=-0.20, pf=1.2, wr=0.45, expectancy=0.1,
        )
        e = _make_mor(
            strategy_id="E", sharpe=0.5, drawdown=-0.25, pf=1.0, wr=0.40, expectancy=0.05,
        )

        frontier = pareto_frontier([a, b, c, d, e])
        frontier_ids = {r.strategy_id for r in frontier}
        assert len(frontier) == 2
        assert frontier_ids == {"A", "B"}

    def test_pareto_frontier_all_identical(self) -> None:
        """All same metrics → all returned (none dominates another)."""
        results = [_make_mor(strategy_id=f"S{i}") for i in range(4)]
        frontier = pareto_frontier(results)
        assert len(frontier) == 4

    def test_pareto_frontier_filters_low_confidence(self) -> None:
        """LOW and ENSEMBLE_ONLY excluded from frontier."""
        high = _make_mor(strategy_id="high", confidence=ConfidenceTier.HIGH)
        mod = _make_mor(strategy_id="mod", confidence=ConfidenceTier.MODERATE)
        low = _make_mor(strategy_id="low", confidence=ConfidenceTier.LOW)
        ens = _make_mor(strategy_id="ens", confidence=ConfidenceTier.ENSEMBLE_ONLY)

        frontier = pareto_frontier([high, mod, low, ens])
        frontier_ids = {r.strategy_id for r in frontier}
        assert "low" not in frontier_ids
        assert "ens" not in frontier_ids
        assert "high" in frontier_ids
        assert "mod" in frontier_ids

    def test_pareto_frontier_single(self) -> None:
        """One HIGH result → returned."""
        result = _make_mor(confidence=ConfidenceTier.HIGH)
        frontier = pareto_frontier([result])
        assert len(frontier) == 1
        assert frontier[0] is result

    def test_pareto_frontier_empty(self) -> None:
        """Empty input → empty output."""
        assert pareto_frontier([]) == []


# ── soft_dominance() ─────────────────────────────────────────────────


class TestSoftDominance:
    """Tests for the soft_dominance() function."""

    def test_soft_dominance_improves_one(self) -> None:
        """A improves Sharpe beyond tolerance, rest within → True."""
        b = _make_mor(sharpe=1.5, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        # Sharpe improves by 0.15 (> tolerance 0.1), rest identical
        a = _make_mor(sharpe=1.65, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        assert soft_dominance(a, b) is True

    def test_soft_dominance_degrades_one(self) -> None:
        """A improves Sharpe but degrades drawdown beyond tolerance → False."""
        b = _make_mor(sharpe=1.5, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        # Sharpe +0.15, but drawdown degrades by 0.05 (> tolerance 0.02)
        a = _make_mor(sharpe=1.65, drawdown=-0.15, pf=2.0, wr=0.55, expectancy=0.3)
        assert soft_dominance(a, b) is False

    def test_soft_dominance_custom_tolerance(self) -> None:
        """Non-default tolerance values change the outcome."""
        b = _make_mor(sharpe=1.5, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)
        # Sharpe improves by 0.05 — below default tolerance (0.1) but above custom (0.03)
        a = _make_mor(sharpe=1.55, drawdown=-0.10, pf=2.0, wr=0.55, expectancy=0.3)

        # Default tolerance: 0.05 < 0.1 → no meaningful improvement → False
        assert soft_dominance(a, b) is False

        # Custom tolerance: 0.05 >= 0.03 → meaningful improvement → True
        custom_tol = {
            "sharpe_ratio": 0.03,
            "max_drawdown_pct": 0.02,
            "profit_factor": 0.1,
            "win_rate": 0.02,
            "expectancy_per_trade": 0.05,
        }
        assert soft_dominance(a, b, tolerance=custom_tol) is True

    def test_soft_dominance_ensemble_only_returns_false(self) -> None:
        """ENSEMBLE_ONLY confidence → False regardless."""
        a = _make_mor(confidence=ConfidenceTier.ENSEMBLE_ONLY)
        b = _make_mor()
        assert soft_dominance(a, b) is False


# ── is_regime_robust() ───────────────────────────────────────────────


def _make_regime(expectancy: float) -> RegimeMetrics:
    """Helper to create a RegimeMetrics with given expectancy."""
    return RegimeMetrics(
        sharpe_ratio=1.0,
        max_drawdown_pct=-0.05,
        profit_factor=2.0,
        win_rate=0.55,
        total_trades=20,
        expectancy_per_trade=expectancy,
    )


class TestIsRegimeRobust:
    """Tests for the is_regime_robust() function."""

    def test_is_regime_robust_true(self) -> None:
        """4 positive-expectancy regimes, min=3 → True."""
        regimes = {
            "bull": _make_regime(0.3),
            "bear": _make_regime(0.1),
            "neutral": _make_regime(0.2),
            "volatile": _make_regime(0.15),
        }
        result = _make_mor(regimes=regimes, confidence=ConfidenceTier.HIGH)
        assert is_regime_robust(result, min_regimes=3) is True

    def test_is_regime_robust_false(self) -> None:
        """2 positive, min=3 → False."""
        regimes = {
            "bull": _make_regime(0.3),
            "bear": _make_regime(-0.1),
            "neutral": _make_regime(0.2),
            "volatile": _make_regime(-0.05),
        }
        result = _make_mor(regimes=regimes, confidence=ConfidenceTier.HIGH)
        assert is_regime_robust(result, min_regimes=3) is False

    def test_is_regime_robust_low_confidence(self) -> None:
        """LOW tier → False regardless of regimes."""
        regimes = {
            "bull": _make_regime(0.5),
            "bear": _make_regime(0.4),
            "neutral": _make_regime(0.3),
            "volatile": _make_regime(0.2),
        }
        result = _make_mor(regimes=regimes, confidence=ConfidenceTier.LOW)
        assert is_regime_robust(result, min_regimes=3) is False


# ── format_comparison_report() ───────────────────────────────────────


class TestFormatComparisonReport:
    """Tests for the format_comparison_report() function."""

    def test_format_comparison_report_nonempty(self) -> None:
        """Produces non-empty string with all required sections."""
        regimes_a = {"bull": _make_regime(0.3), "bear": _make_regime(0.1)}
        regimes_b = {"bull": _make_regime(0.2), "neutral": _make_regime(0.15)}

        a = _make_mor(
            strategy_id="ORB_v2", sharpe=2.0, drawdown=-0.05, pf=3.0,
            wr=0.60, expectancy=0.4, regimes=regimes_a,
        )
        b = _make_mor(
            strategy_id="ORB_v1", sharpe=1.5, drawdown=-0.10, pf=2.0,
            wr=0.55, expectancy=0.3, regimes=regimes_b,
        )

        report = format_comparison_report(a, b)

        assert len(report) > 0
        # Header elements
        assert "ORB_v2" in report
        assert "ORB_v1" in report
        assert "high" in report  # confidence tier
        # Metric table
        assert "sharpe_ratio" in report
        assert "max_drawdown_pct" in report
        assert "profit_factor" in report
        assert "win_rate" in report
        assert "expectancy_per_trade" in report
        # Verdict
        assert "dominates" in report
        # Regime breakdown
        assert "REGIME BREAKDOWN" in report
        assert "bull" in report
        assert "bear" in report
        assert "neutral" in report

    def test_format_report_no_regimes(self) -> None:
        """Report without regime data omits regime section."""
        a = _make_mor(strategy_id="A")
        b = _make_mor(strategy_id="B")
        report = format_comparison_report(a, b)
        assert "REGIME BREAKDOWN" not in report


# ── COMPARISON_METRICS constant ──────────────────────────────────────


class TestComparisonMetrics:
    """Tests for the COMPARISON_METRICS constant."""

    def test_has_exactly_5_entries(self) -> None:
        """COMPARISON_METRICS has exactly 5 entries."""
        assert len(COMPARISON_METRICS) == 5

    def test_all_directions_are_higher(self) -> None:
        """All metric directions are 'higher'."""
        for _, direction in COMPARISON_METRICS:
            assert direction == "higher"
