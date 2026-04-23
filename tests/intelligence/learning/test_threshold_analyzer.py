"""Tests for the Threshold Analyzer.

Sprint 28, Session 2a.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from argus.intelligence.learning.models import (
    ConfidenceLevel,
    LearningLoopConfig,
    OutcomeRecord,
)
from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer


def _make_config(**overrides: object) -> LearningLoopConfig:
    """Create a LearningLoopConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "min_sample_count": 5,
    }
    defaults.update(overrides)
    return LearningLoopConfig(**defaults)  # type: ignore[arg-type]


def _make_cf_record(
    pnl: float,
    grade: str = "B+",
) -> OutcomeRecord:
    """Create a counterfactual OutcomeRecord for testing."""
    return OutcomeRecord(
        symbol="AAPL",
        strategy_id="orb_breakout",
        quality_score=75.0,
        quality_grade=grade,
        dimension_scores={},
        regime_context={},
        pnl=pnl,
        r_multiple=None,
        source="counterfactual",
        timestamp=datetime(2026, 3, 15, 10, 0, 0),
        rejection_stage="QUALITY_FILTER",
        rejection_reason="grade_below_threshold",
    )


def _make_trade_record(pnl: float, grade: str = "B+") -> OutcomeRecord:
    """Create a trade OutcomeRecord for testing."""
    return OutcomeRecord(
        symbol="AAPL",
        strategy_id="orb_breakout",
        quality_score=75.0,
        quality_grade=grade,
        dimension_scores={},
        regime_context={},
        pnl=pnl,
        r_multiple=None,
        source="trade",
        timestamp=datetime(2026, 3, 15, 10, 0, 0),
    )


_THRESHOLDS = {
    "A+": 95,
    "A": 85,
    "A-": 80,
    "B+": 70,
    "B": 60,
    "B-": 50,
    "C+": 40,
}


class TestThresholdAnalyzerRates:
    """Test per-grade rate computation from counterfactual records."""

    def test_high_missed_opportunity_recommends_lower(self) -> None:
        """missed > 0.40 with correct >= 0.50 should recommend 'lower'.

        FIX-08 P1-D2-M04 narrowed semantics: "lower" only fires via the
        elif branch when the "raise" branch (``correct < 0.50``) does
        not. Picking 9 profitable + 11 unprofitable = missed 0.45,
        correct 0.55 keeps "raise" off and exercises the "lower" path.
        """
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=10)

        records = [_make_cf_record(pnl=50.0) for _ in range(9)] + [
            _make_cf_record(pnl=-5.0) for _ in range(11)
        ]

        recs = analyzer.analyze(records, config, _THRESHOLDS)
        lower_recs = [r for r in recs if r.recommended_direction == "lower"]
        assert len(lower_recs) == 1
        assert lower_recs[0].grade == "B+"
        assert lower_recs[0].missed_opportunity_rate > 0.40
        assert lower_recs[0].correct_rejection_rate >= 0.50

    def test_low_correct_rejection_recommends_raise(self) -> None:
        """Correct rejection rate < 0.50 should recommend 'raise'."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        # 4 profitable + 1 unprofitable = 20% correct rejection rate (< 0.50)
        records = [
            _make_cf_record(pnl=50.0),
            _make_cf_record(pnl=30.0),
            _make_cf_record(pnl=20.0),
            _make_cf_record(pnl=10.0),
            _make_cf_record(pnl=-5.0),
        ]

        recs = analyzer.analyze(records, config, _THRESHOLDS)
        raise_recs = [r for r in recs if r.recommended_direction == "raise"]
        assert len(raise_recs) >= 1
        assert raise_recs[0].correct_rejection_rate < 0.50

    def test_both_conditions_simultaneous_emit_only_raise(self) -> None:
        """When both legacy triggers fire, 'raise' wins (FIX-08 P1-D2-M04).

        Pre-FIX-08 the analyzer emitted BOTH a "lower" AND a "raise"
        recommendation for the same grade whenever ``missed > 0.50``,
        producing two contradictory ConfigProposals on the same
        ``thresholds.<grade>`` field path. New semantics: emit at most
        one recommendation per grade with "raise" taking precedence.
        """
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        # 4 profitable + 1 unprofitable:
        # missed_opp = 4/5 = 0.80 > 0.40 → would have triggered "lower" pre-fix
        # correct_rej = 1/5 = 0.20 < 0.50 → triggers "raise" (wins)
        records = [
            _make_cf_record(pnl=50.0),
            _make_cf_record(pnl=30.0),
            _make_cf_record(pnl=20.0),
            _make_cf_record(pnl=10.0),
            _make_cf_record(pnl=-5.0),
        ]

        recs = analyzer.analyze(records, config, _THRESHOLDS)
        b_plus_recs = [r for r in recs if r.grade == "B+"]
        assert len(b_plus_recs) == 1, (
            f"FIX-08 P1-D2-M04: expected at most one rec per grade, "
            f"got {len(b_plus_recs)}"
        )
        assert b_plus_recs[0].recommended_direction == "raise"

    def test_no_recommendation_when_neither_threshold_breached(self) -> None:
        """missed=0.30, correct=0.70 → neither branch fires (FIX-08).

        Sanity check the new semantics: with both rates within bounds,
        the if/elif/else exits with no recommendation.
        """
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=10)

        # 6 profitable + 14 unprofitable: missed=0.30, correct=0.70
        records = [_make_cf_record(pnl=50.0) for _ in range(6)] + [
            _make_cf_record(pnl=-5.0) for _ in range(14)
        ]
        recs = analyzer.analyze(records, config, _THRESHOLDS)
        b_plus_recs = [r for r in recs if r.grade == "B+"]
        assert len(b_plus_recs) == 0

    def test_no_recommendation_when_rates_normal(self) -> None:
        """No recommendations when rates are within normal bounds."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        # 2 profitable + 4 unprofitable:
        # missed_opp = 2/6 = 0.33 (< 0.40 → no "lower")
        # correct_rej = 4/6 = 0.67 (> 0.50 → no "raise")
        records = [
            _make_cf_record(pnl=50.0),
            _make_cf_record(pnl=10.0),
            _make_cf_record(pnl=-5.0),
            _make_cf_record(pnl=-10.0),
            _make_cf_record(pnl=-20.0),
            _make_cf_record(pnl=-30.0),
        ]

        recs = analyzer.analyze(records, config, _THRESHOLDS)
        b_plus_recs = [r for r in recs if r.grade == "B+"]
        assert len(b_plus_recs) == 0


class TestThresholdAnalyzerEdgeCases:
    """Test edge cases for threshold analysis."""

    def test_empty_records_returns_empty(self) -> None:
        """Empty record list returns no recommendations."""
        analyzer = ThresholdAnalyzer()
        config = _make_config()
        assert analyzer.analyze([], config, _THRESHOLDS) == []

    def test_no_counterfactual_records_returns_empty(self) -> None:
        """Only trade records (no counterfactual) returns empty."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        records = [_make_trade_record(pnl=100.0) for _ in range(10)]
        recs = analyzer.analyze(records, config, _THRESHOLDS)
        assert recs == []

    def test_insufficient_samples_returns_empty(self) -> None:
        """Below min_sample_count → no recommendations for that grade."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=10)

        # Only 3 records (below min_sample_count=10)
        records = [
            _make_cf_record(pnl=50.0),
            _make_cf_record(pnl=30.0),
            _make_cf_record(pnl=-5.0),
        ]

        recs = analyzer.analyze(records, config, _THRESHOLDS)
        assert recs == []

    def test_source_separation_ignores_trade_records(self) -> None:
        """Trade records are excluded from threshold analysis (Amendment 3/12)."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        # 10 trade records (should be ignored)
        trade_records = [_make_trade_record(pnl=100.0, grade="B+") for _ in range(10)]

        # 5 counterfactual records with normal rates
        cf_records = [
            _make_cf_record(pnl=-10.0),
            _make_cf_record(pnl=-20.0),
            _make_cf_record(pnl=-30.0),
            _make_cf_record(pnl=5.0),
            _make_cf_record(pnl=-5.0),
        ]

        # Only counterfactual rates matter: missed=1/5=0.20, correct=4/5=0.80
        recs = analyzer.analyze(trade_records + cf_records, config, _THRESHOLDS)
        b_plus_recs = [r for r in recs if r.grade == "B+"]
        assert len(b_plus_recs) == 0  # Both rates normal

    def test_multiple_grades_analyzed(self) -> None:
        """Multiple grades can generate recommendations in one call."""
        analyzer = ThresholdAnalyzer()
        config = _make_config(min_sample_count=5)

        # B+ records: 80% missed opportunity
        b_plus = [_make_cf_record(pnl=50.0, grade="B+") for _ in range(4)]
        b_plus.append(_make_cf_record(pnl=-5.0, grade="B+"))

        # A records: 80% missed opportunity
        a_recs = [_make_cf_record(pnl=50.0, grade="A") for _ in range(4)]
        a_recs.append(_make_cf_record(pnl=-5.0, grade="A"))

        recs = analyzer.analyze(b_plus + a_recs, config, _THRESHOLDS)
        grades_with_recs = {r.grade for r in recs}
        assert "B+" in grades_with_recs
        assert "A" in grades_with_recs
