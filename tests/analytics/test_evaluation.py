"""Tests for argus.analytics.evaluation — Sprint 27.5 Session 1."""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from unittest.mock import MagicMock

from argus.analytics.evaluation import (
    ComparisonVerdict,
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
    compute_confidence_tier,
    from_backtest_result,
    parameter_hash,
)


# ---------------------------------------------------------------------------
# RegimeMetrics
# ---------------------------------------------------------------------------


def test_regime_metrics_construction() -> None:
    """All fields present and correct types."""
    rm = RegimeMetrics(
        sharpe_ratio=1.5,
        max_drawdown_pct=-0.12,
        profit_factor=2.0,
        win_rate=0.55,
        total_trades=42,
        expectancy_per_trade=0.3,
    )
    assert rm.sharpe_ratio == 1.5
    assert rm.max_drawdown_pct == -0.12
    assert rm.profit_factor == 2.0
    assert rm.win_rate == 0.55
    assert rm.total_trades == 42
    assert rm.expectancy_per_trade == 0.3


def test_regime_metrics_serialization_roundtrip() -> None:
    """to_dict → from_dict produces identical object."""
    original = RegimeMetrics(
        sharpe_ratio=2.1,
        max_drawdown_pct=-0.08,
        profit_factor=3.5,
        win_rate=0.62,
        total_trades=100,
        expectancy_per_trade=0.45,
    )
    rebuilt = RegimeMetrics.from_dict(original.to_dict())
    assert rebuilt == original


def test_regime_metrics_serialization_infinite_profit_factor() -> None:
    """Infinite profit_factor survives serialization roundtrip."""
    original = RegimeMetrics(
        sharpe_ratio=1.0,
        max_drawdown_pct=0.0,
        profit_factor=float("inf"),
        win_rate=1.0,
        total_trades=5,
        expectancy_per_trade=1.0,
    )
    d = original.to_dict()
    assert d["profit_factor"] == "Infinity"
    rebuilt = RegimeMetrics.from_dict(d)
    assert math.isinf(rebuilt.profit_factor)


# ---------------------------------------------------------------------------
# ConfidenceTier
# ---------------------------------------------------------------------------


def test_confidence_tier_high() -> None:
    """50 trades, 15+ in 3 regimes → HIGH."""
    counts = {"bullish_trending": 20, "range_bound": 15, "high_volatility": 15}
    assert compute_confidence_tier(50, counts) == ConfidenceTier.HIGH


def test_confidence_tier_moderate_by_trades() -> None:
    """35 trades, 10+ in 2 regimes → MODERATE."""
    counts = {"bullish_trending": 20, "range_bound": 15}
    assert compute_confidence_tier(35, counts) == ConfidenceTier.MODERATE


def test_confidence_tier_moderate_by_regime_deficit() -> None:
    """60 trades but only 2 regimes with 15+ → MODERATE (not HIGH)."""
    counts = {"bullish_trending": 30, "range_bound": 25, "high_volatility": 5}
    assert compute_confidence_tier(60, counts) == ConfidenceTier.MODERATE


def test_confidence_tier_low() -> None:
    """15 trades → LOW."""
    counts = {"bullish_trending": 15}
    assert compute_confidence_tier(15, counts) == ConfidenceTier.LOW


def test_confidence_tier_ensemble_only() -> None:
    """5 trades → ENSEMBLE_ONLY."""
    counts = {"bullish_trending": 5}
    assert compute_confidence_tier(5, counts) == ConfidenceTier.ENSEMBLE_ONLY


def test_confidence_tier_boundary_50() -> None:
    """Exactly 50 trades with sufficient regimes → HIGH."""
    counts = {"a": 16, "b": 17, "c": 17}
    assert compute_confidence_tier(50, counts) == ConfidenceTier.HIGH


def test_confidence_tier_boundary_10() -> None:
    """Exactly 10 → LOW, 9 → ENSEMBLE_ONLY."""
    counts = {"a": 10}
    assert compute_confidence_tier(10, counts) == ConfidenceTier.LOW
    assert compute_confidence_tier(9, {"a": 9}) == ConfidenceTier.ENSEMBLE_ONLY


def test_confidence_tier_boundary_30() -> None:
    """30 trades with 10+ in 2 regimes → MODERATE, 29 → LOW."""
    counts = {"a": 15, "b": 15}
    assert compute_confidence_tier(30, counts) == ConfidenceTier.MODERATE
    assert compute_confidence_tier(29, counts) == ConfidenceTier.LOW


def test_confidence_tier_empty_regime_counts() -> None:
    """50+ trades but empty regime dict → not HIGH (regime criterion fails)."""
    assert compute_confidence_tier(60, {}) == ConfidenceTier.MODERATE


# ---------------------------------------------------------------------------
# parameter_hash
# ---------------------------------------------------------------------------


def test_parameter_hash_determinism() -> None:
    """Same dict with different key order → same hash; different dict → different hash."""
    d1 = {"alpha": 0.5, "beta": 10, "gamma": "x"}
    d2 = {"gamma": "x", "alpha": 0.5, "beta": 10}
    d3 = {"alpha": 0.5, "beta": 11, "gamma": "x"}

    assert parameter_hash(d1) == parameter_hash(d2)
    assert parameter_hash(d1) != parameter_hash(d3)
    assert len(parameter_hash(d1)) == 16


# ---------------------------------------------------------------------------
# MultiObjectiveResult
# ---------------------------------------------------------------------------


def _make_mor(**overrides: object) -> MultiObjectiveResult:
    """Helper to build a MultiObjectiveResult with sensible defaults."""
    defaults: dict[str, object] = {
        "strategy_id": "orb_breakout",
        "parameter_hash": "abc123",
        "evaluation_date": datetime(2026, 3, 1, tzinfo=UTC),
        "data_range": (date(2025, 6, 1), date(2025, 12, 31)),
        "sharpe_ratio": 1.8,
        "max_drawdown_pct": -0.10,
        "profit_factor": 2.5,
        "win_rate": 0.58,
        "total_trades": 75,
        "expectancy_per_trade": 0.35,
        "regime_results": {},
        "confidence_tier": ConfidenceTier.LOW,
        "p_value": None,
        "confidence_interval": None,
        "wfe": 0.0,
        "is_oos": False,
        "execution_quality_adjustment": None,
    }
    defaults.update(overrides)
    return MultiObjectiveResult(**defaults)  # type: ignore[arg-type]


def test_multi_objective_result_construction() -> None:
    """All fields present and correct types."""
    mor = _make_mor()
    assert mor.strategy_id == "orb_breakout"
    assert mor.parameter_hash == "abc123"
    assert mor.evaluation_date == datetime(2026, 3, 1, tzinfo=UTC)
    assert mor.data_range == (date(2025, 6, 1), date(2025, 12, 31))
    assert mor.sharpe_ratio == 1.8
    assert mor.max_drawdown_pct == -0.10
    assert mor.profit_factor == 2.5
    assert mor.win_rate == 0.58
    assert mor.total_trades == 75
    assert mor.expectancy_per_trade == 0.35
    assert mor.regime_results == {}
    assert mor.confidence_tier == ConfidenceTier.LOW
    assert mor.p_value is None
    assert mor.confidence_interval is None
    assert mor.wfe == 0.0
    assert mor.is_oos is False
    assert mor.execution_quality_adjustment is None


def test_multi_objective_result_serialization_roundtrip() -> None:
    """to_dict → from_dict produces identical object."""
    regime = RegimeMetrics(
        sharpe_ratio=1.2,
        max_drawdown_pct=-0.05,
        profit_factor=1.8,
        win_rate=0.52,
        total_trades=30,
        expectancy_per_trade=0.2,
    )
    original = _make_mor(
        regime_results={"bullish_trending": regime},
        confidence_tier=ConfidenceTier.MODERATE,
        p_value=0.03,
        confidence_interval=(0.1, 0.5),
        wfe=0.42,
        is_oos=True,
        execution_quality_adjustment=-0.02,
    )
    d = original.to_dict()
    rebuilt = MultiObjectiveResult.from_dict(d)

    assert rebuilt.strategy_id == original.strategy_id
    assert rebuilt.parameter_hash == original.parameter_hash
    assert rebuilt.evaluation_date == original.evaluation_date
    assert rebuilt.data_range == original.data_range
    assert rebuilt.sharpe_ratio == original.sharpe_ratio
    assert rebuilt.max_drawdown_pct == original.max_drawdown_pct
    assert rebuilt.profit_factor == original.profit_factor
    assert rebuilt.win_rate == original.win_rate
    assert rebuilt.total_trades == original.total_trades
    assert rebuilt.expectancy_per_trade == original.expectancy_per_trade
    assert rebuilt.regime_results == original.regime_results
    assert rebuilt.confidence_tier == original.confidence_tier
    assert rebuilt.p_value == original.p_value
    assert rebuilt.confidence_interval == original.confidence_interval
    assert rebuilt.wfe == original.wfe
    assert rebuilt.is_oos == original.is_oos
    assert rebuilt.execution_quality_adjustment == original.execution_quality_adjustment


def test_multi_objective_result_serialization_none_fields() -> None:
    """Roundtrip with None p_value, confidence_interval, execution_quality_adjustment."""
    original = _make_mor()
    rebuilt = MultiObjectiveResult.from_dict(original.to_dict())
    assert rebuilt.p_value is None
    assert rebuilt.confidence_interval is None
    assert rebuilt.execution_quality_adjustment is None


def test_multi_objective_result_serialization_infinite_profit_factor() -> None:
    """Infinite profit_factor survives MOR serialization roundtrip."""
    original = _make_mor(profit_factor=float("inf"))
    d = original.to_dict()
    assert d["profit_factor"] == "Infinity"
    rebuilt = MultiObjectiveResult.from_dict(d)
    assert math.isinf(rebuilt.profit_factor)


# ---------------------------------------------------------------------------
# from_backtest_result
# ---------------------------------------------------------------------------


def _mock_backtest_result(**overrides: object) -> MagicMock:
    """Create a mock BacktestResult with realistic defaults."""
    defaults = {
        "strategy_id": "orb_breakout",
        "start_date": date(2025, 6, 1),
        "end_date": date(2025, 12, 31),
        "sharpe_ratio": 1.8,
        "max_drawdown_pct": -0.10,
        "profit_factor": 2.5,
        "win_rate": 0.58,
        "total_trades": 75,
        "expectancy": 0.35,
    }
    defaults.update(overrides)
    mock = MagicMock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


def test_from_backtest_result_mapping() -> None:
    """Every BacktestResult field maps correctly to MOR."""
    br = _mock_backtest_result()
    regime = RegimeMetrics(
        sharpe_ratio=1.2,
        max_drawdown_pct=-0.05,
        profit_factor=1.8,
        win_rate=0.52,
        total_trades=30,
        expectancy_per_trade=0.2,
    )
    mor = from_backtest_result(
        br,
        regime_results={"bullish_trending": regime},
        wfe=0.45,
        is_oos=True,
        parameter_hash_value="deadbeef",
    )

    assert mor.strategy_id == "orb_breakout"
    assert mor.parameter_hash == "deadbeef"
    assert mor.data_range == (date(2025, 6, 1), date(2025, 12, 31))
    assert mor.sharpe_ratio == 1.8
    assert mor.max_drawdown_pct == -0.10
    assert mor.profit_factor == 2.5
    assert mor.win_rate == 0.58
    assert mor.total_trades == 75
    assert mor.expectancy_per_trade == 0.35
    assert "bullish_trending" in mor.regime_results
    assert mor.wfe == 0.45
    assert mor.is_oos is True
    assert mor.execution_quality_adjustment is None
    assert mor.evaluation_date.tzinfo is not None  # UTC


def test_from_backtest_result_zero_trades() -> None:
    """Empty BacktestResult → ENSEMBLE_ONLY tier."""
    br = _mock_backtest_result(
        total_trades=0,
        sharpe_ratio=0.0,
        max_drawdown_pct=0.0,
        profit_factor=0.0,
        win_rate=0.0,
        expectancy=0.0,
    )
    mor = from_backtest_result(br)

    assert mor.total_trades == 0
    assert mor.confidence_tier == ConfidenceTier.ENSEMBLE_ONLY
    assert mor.regime_results == {}


def test_from_backtest_result_confidence_computed() -> None:
    """Confidence tier is correctly computed from trade count + regime distribution."""
    regime_results = {
        "bullish_trending": RegimeMetrics(1.0, -0.05, 2.0, 0.6, 20, 0.3),
        "range_bound": RegimeMetrics(0.8, -0.08, 1.5, 0.5, 15, 0.2),
        "high_volatility": RegimeMetrics(0.5, -0.15, 1.2, 0.45, 15, 0.1),
    }
    br = _mock_backtest_result(total_trades=50)
    mor = from_backtest_result(br, regime_results=regime_results)
    assert mor.confidence_tier == ConfidenceTier.HIGH


# ---------------------------------------------------------------------------
# ComparisonVerdict enum values
# ---------------------------------------------------------------------------


def test_regime_metrics_serialization_negative_infinity() -> None:
    """Negative infinity roundtrips correctly."""
    rm = RegimeMetrics(
        sharpe_ratio=-1.0,
        max_drawdown_pct=-0.5,
        profit_factor=float("-inf"),
        win_rate=0.0,
        total_trades=5,
        expectancy_per_trade=-2.0,
    )
    d = rm.to_dict()
    assert d["profit_factor"] == "-Infinity"
    restored = RegimeMetrics.from_dict(d)
    assert restored.profit_factor == float("-inf")


def test_comparison_verdict_values() -> None:
    """Verify enum string values."""
    assert ComparisonVerdict.DOMINATES == "dominates"
    assert ComparisonVerdict.DOMINATED == "dominated"
    assert ComparisonVerdict.INCOMPARABLE == "incomparable"
    assert ComparisonVerdict.INSUFFICIENT_DATA == "insufficient_data"
