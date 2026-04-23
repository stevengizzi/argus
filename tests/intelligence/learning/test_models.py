"""Tests for Learning Loop data models.

Covers serialization round-trips, ConfigProposal status values,
and LearningLoopConfig Pydantic validation.

Sprint 28, Session 1.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    CorrelationResult,
    DataQualityPreamble,
    LearningLoopConfig,
    LearningReport,
    OutcomeRecord,
    PROPOSAL_STATUSES,
    StrategyMetricsSummary,
    ThresholdRecommendation,
    WeightRecommendation,
)


# --- Fixtures ---


def _make_data_quality() -> DataQualityPreamble:
    return DataQualityPreamble(
        trading_days_count=20,
        total_trades=50,
        total_counterfactual=30,
        effective_sample_size=80,
        known_data_gaps=["No counterfactual data before 2026-03-01"],
        earliest_date=datetime(2026, 3, 1, tzinfo=timezone.utc),
        latest_date=datetime(2026, 3, 28, tzinfo=timezone.utc),
    )


def _make_weight_rec() -> WeightRecommendation:
    return WeightRecommendation(
        dimension="pattern_strength",
        current_weight=0.20,
        recommended_weight=0.25,
        delta=0.05,
        correlation_trade_source=0.42,
        correlation_counterfactual_source=0.38,
        p_value=0.03,
        sample_size=50,
        confidence=ConfidenceLevel.HIGH,
        regime_breakdown={"bullish_trending": 0.55, "neutral_ranging": 0.30},
        source_divergence_flag=False,
    )


def _make_threshold_rec() -> ThresholdRecommendation:
    return ThresholdRecommendation(
        grade="B+",
        current_threshold=65.0,
        recommended_direction="lower",
        missed_opportunity_rate=0.45,
        correct_rejection_rate=0.52,
        sample_size=30,
        confidence=ConfidenceLevel.MODERATE,
    )


def _make_correlation_result() -> CorrelationResult:
    return CorrelationResult(
        strategy_pairs=[("orb_breakout", "vwap_reclaim")],
        correlation_matrix={("orb_breakout", "vwap_reclaim"): 0.75},
        flagged_pairs=[("orb_breakout", "vwap_reclaim")],
        overlap_counts={("orb_breakout", "vwap_reclaim"): 15},
        excluded_strategies=["afternoon_momentum"],
        window_days=20,
    )


def _make_learning_report() -> LearningReport:
    return LearningReport(
        report_id="01JTEST000000000000000REPORT",
        generated_at=datetime(2026, 3, 28, 16, 0, 0, tzinfo=timezone.utc),
        analysis_window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
        analysis_window_end=datetime(2026, 3, 28, tzinfo=timezone.utc),
        data_quality=_make_data_quality(),
        weight_recommendations=[_make_weight_rec()],
        threshold_recommendations=[_make_threshold_rec()],
        correlation_result=_make_correlation_result(),
        version=1,
    )


# --- LearningReport serialization round-trip ---


class TestLearningReportSerialization:
    """LearningReport.to_dict() / from_dict() round-trip."""

    def test_round_trip_with_all_fields(self) -> None:
        """Full report serializes and deserializes correctly."""
        report = _make_learning_report()
        d = report.to_dict()
        restored = LearningReport.from_dict(d)

        assert restored.report_id == report.report_id
        assert restored.generated_at == report.generated_at
        assert restored.version == report.version
        assert restored.data_quality == report.data_quality
        assert len(restored.weight_recommendations) == 1
        assert restored.weight_recommendations[0] == report.weight_recommendations[0]
        assert len(restored.threshold_recommendations) == 1
        assert restored.threshold_recommendations[0] == report.threshold_recommendations[0]
        assert restored.correlation_result is not None
        assert restored.correlation_result == report.correlation_result

    def test_round_trip_without_correlation(self) -> None:
        """Report without correlation_result round-trips."""
        report = LearningReport(
            report_id="01JTEST000000000000000REPORT",
            generated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
            analysis_window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            analysis_window_end=datetime(2026, 3, 28, tzinfo=timezone.utc),
            data_quality=_make_data_quality(),
            weight_recommendations=[],
            threshold_recommendations=[],
            correlation_result=None,
        )
        d = report.to_dict()
        restored = LearningReport.from_dict(d)

        assert restored.correlation_result is None
        assert restored.weight_recommendations == []
        assert restored.threshold_recommendations == []

    def test_round_trip_with_strategy_metrics(self) -> None:
        """strategy_metrics round-trips through to_dict/from_dict."""
        metrics = {
            "orb_breakout": StrategyMetricsSummary(
                strategy_id="orb_breakout",
                sharpe=1.82,
                win_rate=0.55,
                expectancy=0.42,
                trade_count=80,
                source="trade",
            ),
            "vwap_reclaim": StrategyMetricsSummary(
                strategy_id="vwap_reclaim",
                sharpe=None,
                win_rate=0.48,
                expectancy=-0.1,
                trade_count=3,
                source="insufficient",
            ),
        }
        report = LearningReport(
            report_id="01JTEST_METRICS",
            generated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
            analysis_window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            analysis_window_end=datetime(2026, 3, 28, tzinfo=timezone.utc),
            data_quality=_make_data_quality(),
            weight_recommendations=[],
            threshold_recommendations=[],
            correlation_result=None,
            strategy_metrics=metrics,
        )
        d = report.to_dict()
        restored = LearningReport.from_dict(d)

        assert len(restored.strategy_metrics) == 2
        orb = restored.strategy_metrics["orb_breakout"]
        assert orb.sharpe == 1.82
        assert orb.win_rate == 0.55
        assert orb.expectancy == 0.42
        assert orb.trade_count == 80
        assert orb.source == "trade"
        vwap = restored.strategy_metrics["vwap_reclaim"]
        assert vwap.sharpe is None
        assert vwap.source == "insufficient"

    def test_round_trip_backward_compatible_no_strategy_metrics(self) -> None:
        """Old serialized reports without strategy_metrics deserialize with empty dict."""
        report = _make_learning_report()
        d = report.to_dict()
        # Simulate old format: remove strategy_metrics key
        d.pop("strategy_metrics", None)
        restored = LearningReport.from_dict(d)
        assert restored.strategy_metrics == {}

    def test_to_dict_datetime_serialization(self) -> None:
        """Datetimes are serialized as ISO strings."""
        report = _make_learning_report()
        d = report.to_dict()

        assert isinstance(d["generated_at"], str)
        assert isinstance(d["analysis_window_start"], str)

    def test_to_dict_correlation_matrix_keys(self) -> None:
        """Correlation matrix tuple keys become pipe-delimited strings."""
        report = _make_learning_report()
        d = report.to_dict()

        assert d["correlation_result"] is not None
        cr = d["correlation_result"]
        assert isinstance(cr, dict)
        matrix = cr["correlation_matrix"]
        assert isinstance(matrix, dict)
        assert "orb_breakout|vwap_reclaim" in matrix

    def test_convert_datetimes_handles_date(self) -> None:
        """_convert_datetimes coerces bare ``date`` to ISO string.

        P1-D2-L01 (FIX-08): pre-fix only ``datetime`` was widened, so a
        bare ``date`` would survive ``to_dict()`` and crash the
        downstream ``json.dumps`` in ``learning_store.save_report``
        (no ``default=str``). This test exercises the helper directly
        with a payload containing both ``date`` and ``datetime`` fields
        — both must serialise to ISO strings.
        """
        from datetime import date as _date  # noqa: PLC0415
        from datetime import datetime as _dt  # noqa: PLC0415

        from argus.intelligence.learning.models import (  # noqa: PLC0415
            _convert_datetimes,
        )

        payload: dict[str, object] = {
            "as_of": _date(2026, 4, 21),
            "ts": _dt(2026, 4, 21, 13, 30, tzinfo=timezone.utc),
            "nested": {"opened_on": _date(2026, 4, 1)},
            "items": [
                {"d": _date(2026, 1, 1)},
                {"dt": _dt(2026, 2, 2, tzinfo=timezone.utc)},
            ],
        }
        _convert_datetimes(payload)

        assert payload["as_of"] == "2026-04-21"
        assert payload["ts"] == "2026-04-21T13:30:00+00:00"
        assert payload["nested"]["opened_on"] == "2026-04-01"  # type: ignore[index]
        assert payload["items"][0]["d"] == "2026-01-01"  # type: ignore[index]
        assert payload["items"][1]["dt"] == "2026-02-02T00:00:00+00:00"  # type: ignore[index]


# --- ConfigProposal ---


class TestConfigProposal:
    """ConfigProposal status values match Amendment 6."""

    def test_all_statuses_defined(self) -> None:
        """All required statuses are in PROPOSAL_STATUSES."""
        expected = {
            "PENDING", "APPROVED", "DISMISSED", "SUPERSEDED",
            "REJECTED_GUARD", "REJECTED_VALIDATION", "APPLIED", "REVERTED",
        }
        assert PROPOSAL_STATUSES == expected

    def test_proposal_creation(self) -> None:
        """ConfigProposal can be created with valid status."""
        proposal = ConfigProposal(
            proposal_id="01JTEST000000000000000PROPOS",
            report_id="01JTEST000000000000000REPORT",
            field_path="weights.pattern_strength",
            current_value=0.20,
            proposed_value=0.25,
            rationale="Correlation with outcomes is highest for this dimension",
            status="PENDING",
            created_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
            human_notes=None,
        )
        assert proposal.status == "PENDING"
        assert proposal.field_path == "weights.pattern_strength"

    def test_proposal_is_frozen(self) -> None:
        """ConfigProposal is immutable."""
        proposal = ConfigProposal(
            proposal_id="01JTEST",
            report_id="01JREP",
            field_path="weights.pattern_strength",
            current_value=0.20,
            proposed_value=0.25,
            rationale="test",
            status="PENDING",
            created_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
            updated_at=datetime(2026, 3, 28, tzinfo=timezone.utc),
        )
        with pytest.raises(AttributeError):
            proposal.status = "APPROVED"  # type: ignore[misc]


# --- LearningLoopConfig Pydantic validation ---


class TestLearningLoopConfig:
    """LearningLoopConfig Pydantic validation."""

    def test_valid_defaults(self) -> None:
        """Default config has correct field values."""
        config = LearningLoopConfig()
        assert config.enabled is True
        assert config.analysis_window_days == 30
        assert config.min_sample_count == 30
        assert config.min_sample_per_regime == 5
        assert config.max_weight_change_per_cycle == 0.10
        assert config.max_cumulative_drift == 0.20
        assert config.cumulative_drift_window_days == 30
        assert config.auto_trigger_enabled is True
        assert config.correlation_window_days == 20
        assert config.report_retention_days == 90
        assert config.correlation_threshold == 0.7
        assert config.weight_divergence_threshold == 0.10
        assert config.correlation_p_value_threshold == 0.10

    def test_valid_from_dict(self) -> None:
        """Config constructed from a full dict."""
        data = {
            "enabled": True,
            "analysis_window_days": 30,
            "min_sample_count": 30,
            "min_sample_per_regime": 5,
            "max_weight_change_per_cycle": 0.10,
            "max_cumulative_drift": 0.20,
            "cumulative_drift_window_days": 30,
            "auto_trigger_enabled": True,
            "correlation_window_days": 20,
            "report_retention_days": 90,
            "correlation_threshold": 0.7,
            "weight_divergence_threshold": 0.10,
            "correlation_p_value_threshold": 0.10,
        }
        config = LearningLoopConfig(**data)
        assert config.min_sample_count == 30

    def test_rejects_min_sample_count_below_5(self) -> None:
        """min_sample_count < 5 is rejected."""
        with pytest.raises(ValidationError, match="min_sample_count"):
            LearningLoopConfig(min_sample_count=2)

    def test_rejects_max_weight_change_zero(self) -> None:
        """max_weight_change_per_cycle = 0.0 is rejected."""
        with pytest.raises(ValidationError, match="max_weight_change_per_cycle"):
            LearningLoopConfig(max_weight_change_per_cycle=0.0)

    def test_rejects_max_weight_change_too_high(self) -> None:
        """max_weight_change_per_cycle > 0.50 is rejected."""
        with pytest.raises(ValidationError, match="max_weight_change_per_cycle"):
            LearningLoopConfig(max_weight_change_per_cycle=0.75)

    def test_rejects_cumulative_drift_below_min(self) -> None:
        """max_cumulative_drift < 0.05 is rejected."""
        with pytest.raises(ValidationError, match="max_cumulative_drift"):
            LearningLoopConfig(max_cumulative_drift=0.01)

    def test_rejects_p_value_threshold_out_of_range(self) -> None:
        """correlation_p_value_threshold outside [0.01, 0.20] is rejected."""
        with pytest.raises(ValidationError, match="correlation_p_value_threshold"):
            LearningLoopConfig(correlation_p_value_threshold=0.50)

    def test_accepts_boundary_values(self) -> None:
        """Boundary values are accepted."""
        config = LearningLoopConfig(
            min_sample_count=5,
            max_weight_change_per_cycle=0.01,
            max_cumulative_drift=0.05,
            correlation_p_value_threshold=0.01,
        )
        assert config.min_sample_count == 5
        assert config.max_weight_change_per_cycle == 0.01


# --- OutcomeRecord ---


class TestOutcomeRecord:
    """OutcomeRecord structure and immutability."""

    def test_trade_source(self) -> None:
        """OutcomeRecord with source='trade' has no rejection fields."""
        record = OutcomeRecord(
            symbol="AAPL",
            strategy_id="orb_breakout",
            quality_score=72.5,
            quality_grade="B+",
            dimension_scores={"pattern_strength": 80.0},
            regime_context={"primary_regime": "bullish_trending"},
            pnl=150.0,
            r_multiple=1.5,
            source="trade",
            timestamp=datetime(2026, 3, 15, 10, 30, tzinfo=timezone.utc),
        )
        assert record.source == "trade"
        assert record.rejection_stage is None

    def test_counterfactual_source(self) -> None:
        """OutcomeRecord with source='counterfactual' has rejection fields."""
        record = OutcomeRecord(
            symbol="TSLA",
            strategy_id="vwap_reclaim",
            quality_score=45.0,
            quality_grade="C+",
            dimension_scores={},
            regime_context={"primary_regime": "neutral_ranging"},
            pnl=-50.0,
            r_multiple=-0.5,
            source="counterfactual",
            timestamp=datetime(2026, 3, 15, 11, 0, tzinfo=timezone.utc),
            rejection_stage="quality_filter",
            rejection_reason="Grade C+ below minimum B-",
        )
        assert record.source == "counterfactual"
        assert record.rejection_stage == "quality_filter"

    def test_is_frozen(self) -> None:
        """OutcomeRecord is immutable."""
        record = OutcomeRecord(
            symbol="AAPL",
            strategy_id="orb",
            quality_score=70.0,
            quality_grade="B",
            dimension_scores={},
            regime_context={},
            pnl=100.0,
            r_multiple=1.0,
            source="trade",
            timestamp=datetime(2026, 3, 15, tzinfo=timezone.utc),
        )
        with pytest.raises(AttributeError):
            record.pnl = 200.0  # type: ignore[misc]


# --- ConfidenceLevel ---


class TestConfidenceLevel:
    """ConfidenceLevel enum values."""

    def test_all_levels(self) -> None:
        """All four confidence levels exist."""
        assert ConfidenceLevel.HIGH == "HIGH"
        assert ConfidenceLevel.MODERATE == "MODERATE"
        assert ConfidenceLevel.LOW == "LOW"
        assert ConfidenceLevel.INSUFFICIENT_DATA == "INSUFFICIENT_DATA"
