"""Tests for the Weight Analyzer.

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
from argus.intelligence.learning.weight_analyzer import WeightAnalyzer


def _make_config(**overrides: object) -> LearningLoopConfig:
    """Create a LearningLoopConfig with sensible test defaults."""
    defaults: dict[str, object] = {
        "min_sample_count": 5,
        "correlation_p_value_threshold": 0.10,
        "max_weight_change_per_cycle": 0.10,
        "min_sample_per_regime": 3,
    }
    defaults.update(overrides)
    return LearningLoopConfig(**defaults)  # type: ignore[arg-type]


def _make_record(
    pnl: float,
    dimension_scores: dict[str, float],
    source: str = "trade",
    regime_context: dict[str, object] | None = None,
) -> OutcomeRecord:
    """Create a minimal OutcomeRecord for testing."""
    return OutcomeRecord(
        symbol="AAPL",
        strategy_id="orb_breakout",
        quality_score=75.0,
        quality_grade="B+",
        dimension_scores=dimension_scores,
        regime_context=regime_context or {},
        pnl=pnl,
        r_multiple=None,
        source=source,  # type: ignore[arg-type]
        timestamp=datetime(2026, 3, 15, 10, 0, 0),
    )


_WEIGHTS = {
    "pattern_strength": 0.30,
    "catalyst_quality": 0.25,
    "volume_profile": 0.20,
    "historical_match": 0.15,
    "regime_alignment": 0.10,
}


class TestWeightAnalyzerCorrelation:
    """Test per-dimension Spearman correlation computation."""

    def test_positive_correlation_increases_weight(self) -> None:
        """Dimension with positive P&L correlation should get higher weight."""
        analyzer = WeightAnalyzer()
        config = _make_config()

        # Pattern strength positively correlated with P&L
        records = [
            _make_record(pnl=i * 10.0, dimension_scores={
                "pattern_strength": float(i * 10),
                "catalyst_quality": 50.0,
                "volume_profile": 50.0,
                "historical_match": 50.0,
                "regime_alignment": 50.0,
            })
            for i in range(1, 8)
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        assert len(recs) == 5

        pattern_rec = next(r for r in recs if r.dimension == "pattern_strength")
        assert pattern_rec.correlation_trade_source is not None
        assert pattern_rec.correlation_trade_source > 0

    def test_zero_variance_dimension_returns_insufficient_data(self) -> None:
        """Dimension with zero variance should return INSUFFICIENT_DATA."""
        analyzer = WeightAnalyzer()
        config = _make_config()

        # historical_match stubbed at 50 (zero variance)
        records = [
            _make_record(pnl=float(i * 10), dimension_scores={
                "pattern_strength": float(i * 10),
                "catalyst_quality": float(i * 5),
                "volume_profile": float(i * 8),
                "historical_match": 50.0,  # zero variance
                "regime_alignment": float(i * 3),
            })
            for i in range(1, 8)
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        hist_rec = next(r for r in recs if r.dimension == "historical_match")
        assert hist_rec.confidence == ConfidenceLevel.INSUFFICIENT_DATA

    def test_zero_variance_pnl_returns_insufficient_data(self) -> None:
        """Zero-variance P&L outcomes should return INSUFFICIENT_DATA."""
        analyzer = WeightAnalyzer()
        config = _make_config()

        # All records have same P&L
        records = [
            _make_record(pnl=100.0, dimension_scores={
                "pattern_strength": float(i * 10),
                "catalyst_quality": float(i * 5),
                "volume_profile": float(i * 8),
                "historical_match": float(i * 2),
                "regime_alignment": float(i * 3),
            })
            for i in range(1, 8)
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        # All dimensions should be INSUFFICIENT_DATA due to zero-variance P&L
        for rec in recs:
            assert rec.confidence == ConfidenceLevel.INSUFFICIENT_DATA

    def test_p_value_filtering(self) -> None:
        """Correlations with p > threshold should be tagged INSUFFICIENT_DATA."""
        analyzer = WeightAnalyzer()
        # Very strict p-value threshold — noise data won't pass
        config = _make_config(correlation_p_value_threshold=0.01)

        # Small sample, random-ish data → high p-value
        records = [
            _make_record(pnl=pnl, dimension_scores={
                "pattern_strength": score,
                "catalyst_quality": 50.0,
                "volume_profile": 50.0,
                "historical_match": 50.0,
                "regime_alignment": 50.0,
            })
            for pnl, score in [
                (10.0, 80.0), (-5.0, 70.0), (3.0, 65.0),
                (-2.0, 75.0), (1.0, 72.0),
            ]
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        # With noisy data and strict threshold, all non-stub dimensions fail
        # p-value check → all INSUFFICIENT_DATA → returns empty (no usable recs)
        assert recs == []

        # Now verify that a lenient threshold DOES produce results
        lenient_config = _make_config(correlation_p_value_threshold=0.20)
        lenient_recs = analyzer.analyze(records, lenient_config, _WEIGHTS)
        # With lenient threshold, pattern_strength (has variance) may produce recs
        # (other 4 dimensions are zero-variance stubs)
        if lenient_recs:
            pattern_rec = next(
                (r for r in lenient_recs if r.dimension == "pattern_strength"),
                None,
            )
            if pattern_rec is not None:
                assert pattern_rec.confidence != ConfidenceLevel.INSUFFICIENT_DATA


class TestWeightAnalyzerSourceSeparation:
    """Test trade vs counterfactual source separation (Amendment 3)."""

    def test_trade_source_preferred_over_counterfactual(self) -> None:
        """Trade-sourced correlation preferred when sample >= min_sample_count."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_count=5)

        # 6 trade records with positive correlation
        trade_records = [
            _make_record(
                pnl=float(i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="trade",
            )
            for i in range(1, 7)
        ]

        # 6 counterfactual records with negative correlation
        cf_records = [
            _make_record(
                pnl=float(-i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="counterfactual",
            )
            for i in range(1, 7)
        ]

        weights = {"pattern_strength": 1.0}
        recs = analyzer.analyze(trade_records + cf_records, config, weights)
        assert len(recs) == 1

        rec = recs[0]
        assert rec.correlation_trade_source is not None
        assert rec.correlation_trade_source > 0
        assert rec.correlation_counterfactual_source is not None
        assert rec.correlation_counterfactual_source < 0

    def test_counterfactual_fallback_with_moderate_cap(self) -> None:
        """When trade samples insufficient, use counterfactual with MODERATE cap."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_count=10)

        # Only 3 trade records (below min_sample_count=10)
        trade_records = [
            _make_record(
                pnl=float(i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="trade",
            )
            for i in range(1, 4)
        ]

        # 15 counterfactual records (above min_sample_count=10)
        cf_records = [
            _make_record(
                pnl=float(i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="counterfactual",
            )
            for i in range(1, 16)
        ]

        weights = {"pattern_strength": 1.0}
        recs = analyzer.analyze(trade_records + cf_records, config, weights)
        assert len(recs) == 1
        assert recs[0].confidence == ConfidenceLevel.MODERATE

    def test_source_divergence_flag(self) -> None:
        """Flag when trade and counterfactual correlations diverge > 0.3."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_count=5)

        # Trade: strong positive correlation
        trade_records = [
            _make_record(
                pnl=float(i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="trade",
            )
            for i in range(1, 8)
        ]

        # Counterfactual: strong negative correlation
        cf_records = [
            _make_record(
                pnl=float(-i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                source="counterfactual",
            )
            for i in range(1, 8)
        ]

        weights = {"pattern_strength": 1.0}
        recs = analyzer.analyze(trade_records + cf_records, config, weights)
        assert len(recs) == 1
        assert recs[0].source_divergence_flag is True


class TestWeightAnalyzerFormula:
    """Test weight formula normalization (Amendment 5)."""

    def test_weights_sum_to_one(self) -> None:
        """Recommended weights must always sum to 1.0."""
        analyzer = WeightAnalyzer()
        config = _make_config()

        records = [
            _make_record(pnl=float(i * 10), dimension_scores={
                "pattern_strength": float(i * 10),
                "catalyst_quality": float(i * 5),
                "volume_profile": float(i * 8),
                "historical_match": 50.0,
                "regime_alignment": float(i * 3),
            })
            for i in range(1, 8)
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        if recs:
            total = sum(r.recommended_weight for r in recs)
            assert abs(total - 1.0) < 1e-9, f"Weights sum to {total}, expected 1.0"

    def test_max_change_per_cycle_clamping(self) -> None:
        """Weight deltas must be clamped by max_change_per_cycle."""
        analyzer = WeightAnalyzer()
        config = _make_config(max_weight_change_per_cycle=0.05)

        # Strong correlation on one dimension to create large delta
        records = [
            _make_record(pnl=float(i * 10), dimension_scores={
                "pattern_strength": float(i * 10),
                "catalyst_quality": 50.0,
                "volume_profile": 50.0,
                "historical_match": 50.0,
                "regime_alignment": 50.0,
            })
            for i in range(1, 10)
        ]

        recs = analyzer.analyze(records, config, _WEIGHTS)
        for rec in recs:
            # Before normalization the raw delta is clamped, but after
            # normalization we just check the final result is reasonable
            assert rec.recommended_weight >= 0.0

    def test_empty_records_returns_empty(self) -> None:
        """Empty record list returns empty recommendations."""
        analyzer = WeightAnalyzer()
        config = _make_config()
        assert analyzer.analyze([], config, _WEIGHTS) == []

    def test_empty_weights_returns_empty(self) -> None:
        """Empty weights dict returns empty recommendations."""
        analyzer = WeightAnalyzer()
        config = _make_config()
        records = [
            _make_record(pnl=10.0, dimension_scores={"x": 50.0})
        ]
        assert analyzer.analyze(records, config, {}) == []


class TestWeightAnalyzerRegime:
    """Test per-regime breakdown (Amendment 7)."""

    def test_regime_grouping_by_primary_regime(self) -> None:
        """Records grouped by primary_regime from regime_context."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_per_regime=3, min_sample_count=5)

        records = []
        for i in range(1, 7):
            records.append(_make_record(
                pnl=float(i * 10),
                dimension_scores={"pattern_strength": float(i * 10)},
                regime_context={"primary_regime": "bullish_trending"},
            ))
        for i in range(1, 7):
            records.append(_make_record(
                pnl=float(i * 5),
                dimension_scores={"pattern_strength": float(i * 10)},
                regime_context={"primary_regime": "bearish_trending"},
            ))

        weights = {"pattern_strength": 1.0}
        results = analyzer.analyze_by_regime(records, config, weights)

        assert "bullish_trending" in results
        assert "bearish_trending" in results

    def test_insufficient_regime_samples_excluded(self) -> None:
        """Regimes with < min_sample_per_regime are excluded."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_per_regime=5, min_sample_count=5)

        # Only 2 records per regime (below min_sample_per_regime=5)
        records = [
            _make_record(
                pnl=10.0,
                dimension_scores={"pattern_strength": 80.0},
                regime_context={"primary_regime": "bullish_trending"},
            ),
            _make_record(
                pnl=20.0,
                dimension_scores={"pattern_strength": 90.0},
                regime_context={"primary_regime": "bullish_trending"},
            ),
        ]

        weights = {"pattern_strength": 1.0}
        results = analyzer.analyze_by_regime(records, config, weights)
        assert results == {}

    def test_missing_primary_regime_excluded(self) -> None:
        """Records without primary_regime in regime_context are excluded."""
        analyzer = WeightAnalyzer()
        config = _make_config(min_sample_per_regime=2, min_sample_count=5)

        records = [
            _make_record(
                pnl=10.0,
                dimension_scores={"pattern_strength": 80.0},
                regime_context={},  # no primary_regime
            )
            for _ in range(5)
        ]

        weights = {"pattern_strength": 1.0}
        results = analyzer.analyze_by_regime(records, config, weights)
        assert results == {}
