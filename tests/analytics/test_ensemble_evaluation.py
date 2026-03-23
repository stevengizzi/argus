"""Tests for ensemble evaluation module.

Sprint 27.5 Session 4.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

import pytest

from argus.analytics.comparison import ComparisonVerdict
from argus.analytics.ensemble_evaluation import (
    EnsembleResult,
    MarginalContribution,
    build_ensemble_result,
    evaluate_cohort_addition,
    format_ensemble_report,
    identify_deadweight,
    marginal_contribution,
)
from argus.analytics.evaluation import ConfidenceTier, MultiObjectiveResult


def _make_mor(
    strategy_id: str = "test_strategy",
    sharpe: float = 1.5,
    drawdown: float = -0.10,
    pf: float = 2.0,
    win_rate: float = 0.55,
    trades: int = 100,
    expectancy: float = 0.3,
    confidence: ConfidenceTier = ConfidenceTier.MODERATE,
) -> MultiObjectiveResult:
    """Helper to create a MultiObjectiveResult for testing."""
    return MultiObjectiveResult(
        strategy_id=strategy_id,
        parameter_hash="abc123",
        evaluation_date=datetime(2026, 1, 15, tzinfo=UTC),
        data_range=(date(2025, 1, 1), date(2025, 12, 31)),
        sharpe_ratio=sharpe,
        max_drawdown_pct=drawdown,
        profit_factor=pf,
        win_rate=win_rate,
        total_trades=trades,
        expectancy_per_trade=expectancy,
        confidence_tier=confidence,
    )


class TestMarginalContribution:
    """Tests for MarginalContribution dataclass."""

    def test_marginal_contribution_construction(self) -> None:
        """All fields present and accessible on frozen dataclass."""
        mc = MarginalContribution(
            strategy_id="orb_breakout",
            marginal_sharpe=0.25,
            marginal_drawdown=0.02,
            correlation_to_ensemble=0.45,
            trade_count=80,
            confidence_tier=ConfidenceTier.HIGH,
        )
        assert mc.strategy_id == "orb_breakout"
        assert mc.marginal_sharpe == 0.25
        assert mc.marginal_drawdown == 0.02
        assert mc.correlation_to_ensemble == 0.45
        assert mc.trade_count == 80
        assert mc.confidence_tier == ConfidenceTier.HIGH

    def test_marginal_contribution_frozen(self) -> None:
        """MarginalContribution is immutable."""
        mc = MarginalContribution(
            strategy_id="orb",
            marginal_sharpe=0.1,
            marginal_drawdown=0.0,
            correlation_to_ensemble=0.5,
            trade_count=50,
            confidence_tier=ConfidenceTier.MODERATE,
        )
        with pytest.raises(AttributeError):
            mc.marginal_sharpe = 0.5  # type: ignore[misc]

    def test_marginal_contribution_serialization_roundtrip(self) -> None:
        """to_dict → from_dict produces identical MarginalContribution."""
        mc = MarginalContribution(
            strategy_id="vwap_reclaim",
            marginal_sharpe=-0.12,
            marginal_drawdown=0.05,
            correlation_to_ensemble=0.33,
            trade_count=42,
            confidence_tier=ConfidenceTier.LOW,
        )
        d = mc.to_dict()
        restored = MarginalContribution.from_dict(d)
        assert restored == mc


class TestEnsembleResult:
    """Tests for EnsembleResult dataclass."""

    def test_ensemble_result_construction(self) -> None:
        """Valid aggregate + contributions build successfully."""
        mor = _make_mor()
        mc = MarginalContribution(
            strategy_id="test_strategy",
            marginal_sharpe=1.5,
            marginal_drawdown=0.0,
            correlation_to_ensemble=1.0,
            trade_count=100,
            confidence_tier=ConfidenceTier.MODERATE,
        )
        er = EnsembleResult(
            cohort_id="test_cohort",
            strategy_ids=["test_strategy"],
            evaluation_date=datetime(2026, 1, 15, tzinfo=UTC),
            data_range=(date(2025, 1, 1), date(2025, 12, 31)),
            aggregate=mor,
            diversification_ratio=1.0,
            marginal_contributions={"test_strategy": mc},
            tail_correlation=1.0,
            max_concurrent_drawdown=-0.10,
            capital_utilization=0.5,
            turnover_rate=250.0,
        )
        assert er.cohort_id == "test_cohort"
        assert len(er.strategy_ids) == 1
        assert er.aggregate.sharpe_ratio == 1.5
        assert er.diversification_ratio == 1.0
        assert er.baseline_ensemble is None
        assert er.improvement_verdict == ComparisonVerdict.INCOMPARABLE

    def test_ensemble_result_serialization_roundtrip(self) -> None:
        """to_dict → from_dict produces identical EnsembleResult."""
        mors = [
            _make_mor("strat_a", sharpe=1.2, drawdown=-0.08),
            _make_mor("strat_b", sharpe=1.8, drawdown=-0.12),
        ]
        er = build_ensemble_result(mors, cohort_id="roundtrip_test")
        d = er.to_dict()
        restored = EnsembleResult.from_dict(d)

        assert restored.cohort_id == er.cohort_id
        assert restored.strategy_ids == er.strategy_ids
        assert restored.diversification_ratio == er.diversification_ratio
        assert restored.tail_correlation == er.tail_correlation
        assert restored.max_concurrent_drawdown == er.max_concurrent_drawdown
        assert restored.aggregate.sharpe_ratio == er.aggregate.sharpe_ratio
        assert restored.aggregate.total_trades == er.aggregate.total_trades
        assert set(restored.marginal_contributions.keys()) == set(
            er.marginal_contributions.keys()
        )


class TestBuildEnsemble:
    """Tests for build_ensemble_result function."""

    def test_build_ensemble_basic(self) -> None:
        """3 MORs → valid EnsembleResult with all fields populated."""
        mors = [
            _make_mor("strat_a", sharpe=1.0, drawdown=-0.05),
            _make_mor("strat_b", sharpe=2.0, drawdown=-0.10),
            _make_mor("strat_c", sharpe=1.5, drawdown=-0.08),
        ]
        er = build_ensemble_result(mors, cohort_id="basic_test")

        assert er.cohort_id == "basic_test"
        assert len(er.strategy_ids) == 3
        assert er.aggregate.total_trades == 300
        assert len(er.marginal_contributions) == 3
        assert er.diversification_ratio > 1.0  # 3 strategies → diversification
        assert 0.0 <= er.capital_utilization <= 1.0
        assert er.turnover_rate > 0.0

    def test_build_ensemble_single_strategy(self) -> None:
        """1 MOR → diversification=1.0, tail_corr=1.0."""
        mor = _make_mor("solo", sharpe=1.5, drawdown=-0.10)
        er = build_ensemble_result([mor])

        assert er.diversification_ratio == 1.0
        assert er.tail_correlation == 1.0
        assert len(er.marginal_contributions) == 1
        mc = er.marginal_contributions["solo"]
        assert mc.marginal_sharpe == er.aggregate.sharpe_ratio
        assert mc.correlation_to_ensemble == 1.0

    def test_build_ensemble_diversification_ratio(self) -> None:
        """Uncorrelated strategies → diversification ratio > 1.0."""
        # Strategies with different drawdown profiles suggest uncorrelated returns
        mors = [
            _make_mor("low_vol", sharpe=1.0, drawdown=-0.03),
            _make_mor("high_vol", sharpe=2.0, drawdown=-0.20),
            _make_mor("mid_vol", sharpe=1.5, drawdown=-0.10),
        ]
        er = build_ensemble_result(mors)
        assert er.diversification_ratio > 1.0

    def test_build_ensemble_empty_raises(self) -> None:
        """Empty results list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            build_ensemble_result([])

    def test_build_ensemble_aggregate_metrics(self) -> None:
        """Aggregate metrics are reasonable weighted combinations."""
        mors = [
            _make_mor("a", sharpe=1.0, drawdown=-0.10, trades=50, win_rate=0.50),
            _make_mor("b", sharpe=2.0, drawdown=-0.20, trades=50, win_rate=0.60),
        ]
        er = build_ensemble_result(mors)

        # Sharpe: equal-weight average of 1.0 and 2.0 = 1.5
        assert er.aggregate.sharpe_ratio == pytest.approx(1.5)
        # Drawdown: equal-weight average of -0.10 and -0.20 = -0.15
        assert er.aggregate.max_drawdown_pct == pytest.approx(-0.15)
        # Win rate: trade-weighted (equal trades) = 0.55
        assert er.aggregate.win_rate == pytest.approx(0.55)
        assert er.aggregate.total_trades == 100


class TestMarginalContributionFunction:
    """Tests for marginal_contribution() and contribution values."""

    def test_marginal_contribution_positive(self) -> None:
        """Good strategy → positive marginal Sharpe."""
        # One great strategy + one mediocre → great one has positive marginal
        mors = [
            _make_mor("great", sharpe=3.0, drawdown=-0.05),
            _make_mor("mediocre", sharpe=0.5, drawdown=-0.15),
        ]
        er = build_ensemble_result(mors)
        mc = marginal_contribution(er, "great")
        assert mc.marginal_sharpe > 0.0

    def test_marginal_contribution_negative(self) -> None:
        """Bad strategy → negative marginal Sharpe."""
        # One good strategy + one terrible → terrible one has negative marginal
        mors = [
            _make_mor("good", sharpe=2.0, drawdown=-0.05),
            _make_mor("terrible", sharpe=-1.0, drawdown=-0.30),
        ]
        er = build_ensemble_result(mors)
        mc = marginal_contribution(er, "terrible")
        assert mc.marginal_sharpe < 0.0

    def test_marginal_contribution_key_error(self) -> None:
        """Non-existent strategy_id raises KeyError."""
        mor = _make_mor("only")
        er = build_ensemble_result([mor])
        with pytest.raises(KeyError):
            marginal_contribution(er, "nonexistent")


class TestCohortAddition:
    """Tests for evaluate_cohort_addition."""

    def test_evaluate_cohort_addition_improvement(self) -> None:
        """Candidates improve ensemble → DOMINATES verdict."""
        baseline_mors = [
            _make_mor("base_a", sharpe=0.5, drawdown=-0.15, pf=1.2,
                       win_rate=0.45, expectancy=0.1),
        ]
        baseline = build_ensemble_result(baseline_mors, cohort_id="base")

        # Add a much better strategy
        candidates = [
            _make_mor("new_star", sharpe=3.0, drawdown=-0.02, pf=4.0,
                       win_rate=0.70, expectancy=0.8),
        ]
        new_er = evaluate_cohort_addition(baseline, candidates)

        assert new_er.baseline_ensemble is baseline
        # New ensemble should be better on all metrics → DOMINATES
        assert new_er.improvement_verdict == ComparisonVerdict.DOMINATES

    def test_evaluate_cohort_addition_degradation(self) -> None:
        """Candidates hurt ensemble → DOMINATED verdict."""
        baseline_mors = [
            _make_mor("base_good", sharpe=3.0, drawdown=-0.02, pf=4.0,
                       win_rate=0.70, expectancy=0.8),
        ]
        baseline = build_ensemble_result(baseline_mors, cohort_id="base")

        # Add a terrible strategy
        candidates = [
            _make_mor("bad_add", sharpe=0.1, drawdown=-0.30, pf=0.8,
                       win_rate=0.35, expectancy=-0.1),
        ]
        new_er = evaluate_cohort_addition(baseline, candidates)

        assert new_er.baseline_ensemble is baseline
        assert new_er.improvement_verdict == ComparisonVerdict.DOMINATED

    def test_evaluate_cohort_addition_empty_candidates_raises(self) -> None:
        """Empty candidates raises ValueError."""
        baseline = build_ensemble_result([_make_mor()])
        with pytest.raises(ValueError, match="empty"):
            evaluate_cohort_addition(baseline, [])


class TestIdentifyDeadweight:
    """Tests for identify_deadweight."""

    def test_identify_deadweight_none(self) -> None:
        """All positive marginals → empty list."""
        # Use equal Sharpe so neither drags down the ensemble
        mors = [
            _make_mor("good_a", sharpe=2.0, drawdown=-0.05),
            _make_mor("good_b", sharpe=2.0, drawdown=-0.08),
        ]
        er = build_ensemble_result(mors)
        deadweight = identify_deadweight(er)
        assert deadweight == []

    def test_identify_deadweight_found(self) -> None:
        """One negative marginal → returned."""
        mors = [
            _make_mor("strong", sharpe=3.0, drawdown=-0.03),
            _make_mor("drag", sharpe=-1.0, drawdown=-0.25),
        ]
        er = build_ensemble_result(mors)
        deadweight = identify_deadweight(er)
        assert "drag" in deadweight

    def test_identify_deadweight_custom_threshold(self) -> None:
        """Custom threshold filters strategies below it."""
        mors = [
            _make_mor("great", sharpe=3.0, drawdown=-0.03),
            _make_mor("okay", sharpe=0.8, drawdown=-0.10),
        ]
        er = build_ensemble_result(mors)
        # With a high threshold, "okay" should be deadweight
        deadweight = identify_deadweight(er, threshold=1.0)
        # The marginal Sharpe of "okay" should be < 1.0
        assert len(deadweight) >= 1


class TestFormatEnsembleReport:
    """Tests for format_ensemble_report."""

    def test_format_ensemble_report_nonempty(self) -> None:
        """Produces non-empty readable string with expected sections."""
        mors = [
            _make_mor("strat_a", sharpe=1.5, drawdown=-0.08),
            _make_mor("strat_b", sharpe=2.0, drawdown=-0.12),
        ]
        er = build_ensemble_result(mors, cohort_id="test_report")
        report = format_ensemble_report(er)

        assert len(report) > 100
        assert "ENSEMBLE EVALUATION REPORT" in report
        assert "test_report" in report
        assert "AGGREGATE METRICS" in report
        assert "ENSEMBLE HEALTH" in report
        assert "MARGINAL CONTRIBUTIONS" in report
        assert "strat_a" in report
        assert "strat_b" in report

    def test_format_report_with_baseline(self) -> None:
        """Report includes comparison section when baseline present."""
        baseline_mors = [_make_mor("base", sharpe=1.0)]
        baseline = build_ensemble_result(baseline_mors)
        candidates = [_make_mor("new", sharpe=2.0, drawdown=-0.05)]
        new_er = evaluate_cohort_addition(baseline, candidates)
        report = format_ensemble_report(new_er)

        assert "COMPARISON TO BASELINE" in report
        assert "Verdict" in report

    def test_format_report_with_deadweight(self) -> None:
        """Report includes deadweight warning when present."""
        mors = [
            _make_mor("strong", sharpe=3.0, drawdown=-0.03),
            _make_mor("terrible", sharpe=-2.0, drawdown=-0.30),
        ]
        er = build_ensemble_result(mors)
        report = format_ensemble_report(er)

        assert "DEADWEIGHT" in report
        assert "terrible" in report
