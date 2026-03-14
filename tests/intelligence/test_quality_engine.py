"""Tests for SetupQualityEngine."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.core.events import Side, SignalEvent
from argus.core.regime import MarketRegime
from argus.intelligence.config import QualityEngineConfig, QualityThresholdsConfig, QualityWeightsConfig
from argus.intelligence.models import ClassifiedCatalyst
from argus.intelligence.quality_engine import SetupQuality, SetupQualityEngine


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def make_engine(
    weights: QualityWeightsConfig | None = None,
    thresholds: QualityThresholdsConfig | None = None,
) -> SetupQualityEngine:
    config = QualityEngineConfig(
        weights=weights or QualityWeightsConfig(
            pattern_strength=0.2,
            catalyst_quality=0.2,
            volume_profile=0.2,
            historical_match=0.2,
            regime_alignment=0.2,
        ),
        thresholds=thresholds or QualityThresholdsConfig(),
    )
    return SetupQualityEngine(config)


def make_signal(pattern_strength: float = 50.0) -> SignalEvent:
    return SignalEvent(
        strategy_id="test",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=100.0,
        stop_price=99.0,
        target_prices=(102.0,),
        share_count=0,
        pattern_strength=pattern_strength,
    )


def make_catalyst(quality_score: float, hours_ago: float = 1.0) -> ClassifiedCatalyst:
    published = datetime.now(UTC) - timedelta(hours=hours_ago)
    return ClassifiedCatalyst(
        headline="Test headline",
        symbol="AAPL",
        source="fmp_news",
        published_at=published,
        fetched_at=published,
        category="earnings",
        quality_score=quality_score,
        summary="Test summary",
        trading_relevance="high",
        classified_by="claude",
        classified_at=published,
        headline_hash="abc123",
    )


DEFAULT_REGIME = MarketRegime.BULLISH_TRENDING
DEFAULT_ALLOWED = ["bullish_trending"]


# ---------------------------------------------------------------------------
# Pattern strength dimension
# ---------------------------------------------------------------------------


def test_pattern_strength_basic():
    engine = make_engine()
    signal = make_signal(pattern_strength=75.0)
    result = engine.score_setup(signal, [], 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["pattern_strength"] == 75.0


def test_pattern_strength_clamped():
    engine = make_engine()
    signal_high = make_signal(pattern_strength=150.0)
    signal_low = make_signal(pattern_strength=-10.0)
    r_high = engine.score_setup(signal_high, [], 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    r_low = engine.score_setup(signal_low, [], 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert r_high.components["pattern_strength"] == 100.0
    assert r_low.components["pattern_strength"] == 0.0


# ---------------------------------------------------------------------------
# Catalyst quality dimension
# ---------------------------------------------------------------------------


def test_catalyst_quality_empty_list():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["catalyst_quality"] == 50.0


def test_catalyst_quality_single_catalyst():
    engine = make_engine()
    catalysts = [make_catalyst(quality_score=80.0)]
    result = engine.score_setup(make_signal(), catalysts, 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["catalyst_quality"] == 80.0


def test_catalyst_quality_max_from_list():
    engine = make_engine()
    catalysts = [
        make_catalyst(quality_score=60.0),
        make_catalyst(quality_score=90.0),
        make_catalyst(quality_score=45.0),
    ]
    result = engine.score_setup(make_signal(), catalysts, 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["catalyst_quality"] == 90.0


def test_catalyst_quality_filters_to_24h():
    engine = make_engine()
    old_catalyst = make_catalyst(quality_score=95.0, hours_ago=25.0)
    recent_catalyst = make_catalyst(quality_score=40.0, hours_ago=1.0)
    result = engine.score_setup(
        make_signal(), [old_catalyst, recent_catalyst], 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED
    )
    assert result.components["catalyst_quality"] == 40.0


def test_catalyst_quality_all_old_returns_50():
    engine = make_engine()
    catalysts = [make_catalyst(quality_score=95.0, hours_ago=48.0)]
    result = engine.score_setup(make_signal(), catalysts, 1.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["catalyst_quality"] == 50.0


# ---------------------------------------------------------------------------
# Volume profile dimension
# ---------------------------------------------------------------------------


def test_volume_profile_none():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], None, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["volume_profile"] == 50.0


def test_volume_profile_at_lower_bound():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 0.5, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["volume_profile"] == 10.0


def test_volume_profile_below_lower_bound():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 0.1, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["volume_profile"] == 10.0


def test_volume_profile_at_upper_bound():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 3.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["volume_profile"] == 95.0


def test_volume_profile_above_upper_bound():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 5.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["volume_profile"] == 95.0


def test_volume_profile_interpolation():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], 1.5, DEFAULT_REGIME, DEFAULT_ALLOWED)
    # Linear between (1.0, 40) and (2.0, 70): t=0.5 → 55.0
    assert result.components["volume_profile"] == pytest.approx(55.0)


# ---------------------------------------------------------------------------
# Historical match dimension
# ---------------------------------------------------------------------------


def test_historical_match_returns_50():
    engine = make_engine()
    result = engine.score_setup(make_signal(), [], None, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.components["historical_match"] == 50.0


# ---------------------------------------------------------------------------
# Regime alignment dimension
# ---------------------------------------------------------------------------


def test_regime_in_allowed():
    engine = make_engine()
    result = engine.score_setup(
        make_signal(), [], None, MarketRegime.BULLISH_TRENDING, ["bullish_trending"]
    )
    assert result.components["regime_alignment"] == 80.0


def test_regime_not_in_allowed():
    engine = make_engine()
    result = engine.score_setup(
        make_signal(), [], None, MarketRegime.BEARISH_TRENDING, ["bullish_trending"]
    )
    assert result.components["regime_alignment"] == 20.0


def test_regime_empty_allowed():
    engine = make_engine()
    result = engine.score_setup(
        make_signal(), [], None, MarketRegime.BULLISH_TRENDING, []
    )
    assert result.components["regime_alignment"] == 70.0


# ---------------------------------------------------------------------------
# Grade mapping
# ---------------------------------------------------------------------------


def test_grade_from_score_boundaries():
    engine = make_engine()
    # Directly test _grade_from_score via score_setup with controlled weights
    # Use weights that map score = pattern_strength (only dimension)
    weights = QualityWeightsConfig(
        pattern_strength=1.0,
        catalyst_quality=0.0,
        volume_profile=0.0,
        historical_match=0.0,
        regime_alignment=0.0,
    )
    eng = make_engine(weights=weights)

    def grade(ps: float) -> str:
        return eng.score_setup(
            make_signal(pattern_strength=ps), [], None, MarketRegime.BULLISH_TRENDING, []
        ).grade

    assert grade(90.0) == "A+"
    assert grade(89.0) == "A"
    assert grade(80.0) == "A"
    assert grade(79.0) == "A-"
    assert grade(30.0) == "C+"
    assert grade(29.0) == "C"


def test_grade_c_below_c_plus_threshold():
    weights = QualityWeightsConfig(
        pattern_strength=1.0,
        catalyst_quality=0.0,
        volume_profile=0.0,
        historical_match=0.0,
        regime_alignment=0.0,
    )
    eng = make_engine(weights=weights)
    result = eng.score_setup(
        make_signal(pattern_strength=10.0), [], None, MarketRegime.BULLISH_TRENDING, []
    )
    assert result.grade == "C"


def test_risk_tier_matches_grade():
    engine = make_engine()
    result = engine.score_setup(make_signal(80.0), [], 2.0, DEFAULT_REGIME, DEFAULT_ALLOWED)
    assert result.risk_tier == result.grade


# ---------------------------------------------------------------------------
# Full pipeline
# ---------------------------------------------------------------------------


def test_score_setup_full_pipeline():
    engine = make_engine()
    # PS=80, CQ=80 (catalyst), VP=55 (rvol=1.5), HM=50 (stub), RA=80 (in allowed)
    # Score = 0.2 * (80 + 80 + 55 + 50 + 80) = 0.2 * 345 = 69.0 → A-
    catalysts = [make_catalyst(quality_score=80.0)]
    result = engine.score_setup(
        make_signal(pattern_strength=80.0),
        catalysts,
        1.5,
        MarketRegime.BULLISH_TRENDING,
        ["bullish_trending"],
    )
    assert result.score == pytest.approx(69.0)
    assert result.grade == "B+"
    assert result.risk_tier == "B+"
    assert len(result.components) == 5


def test_score_setup_varied_inputs_produce_different_grades():
    engine = make_engine()

    def score_setup(ps: float, rvol: float | None, regime: MarketRegime, allowed: list) -> str:
        return engine.score_setup(make_signal(ps), [], rvol, regime, allowed).grade

    # A+ — high pattern + good rvol + in allowed
    # PS=100, CQ=50 (empty), VP=95 (rvol≥3), HM=50, RA=80 → 0.2*375=75 → A-
    # Need all-100 for A+: achievable by clamping
    weights_all_ps = QualityWeightsConfig(
        pattern_strength=1.0,
        catalyst_quality=0.0,
        volume_profile=0.0,
        historical_match=0.0,
        regime_alignment=0.0,
    )
    eng_pure = make_engine(weights=weights_all_ps)
    assert eng_pure.score_setup(
        make_signal(100.0), [], None, DEFAULT_REGIME, DEFAULT_ALLOWED
    ).grade == "A+"

    # C — low PS, low VP, regime not in allowed
    # PS=0, CQ=50, VP=10, HM=50, RA=20 → 0.2*130=26 → C (below c_plus=30)
    assert engine.score_setup(
        make_signal(0.0), [], 0.1, MarketRegime.RANGE_BOUND, ["bullish_trending"]
    ).grade == "C"


# ---------------------------------------------------------------------------
# Rationale format
# ---------------------------------------------------------------------------


def test_rationale_string_format():
    engine = make_engine()
    result = engine.score_setup(
        make_signal(75.0), [], 2.0, DEFAULT_REGIME, DEFAULT_ALLOWED
    )
    rationale = result.rationale
    assert "PS:" in rationale
    assert "CQ:" in rationale
    assert "VP:" in rationale
    assert "HM:" in rationale
    assert "RA:" in rationale
    assert "Score:" in rationale
    assert result.grade in rationale


# ---------------------------------------------------------------------------
# Public property accessors (Sprint 24.1 S1b — DEF-061)
# ---------------------------------------------------------------------------


def test_db_property_returns_db_manager():
    engine = make_engine()
    assert engine.db is None  # default: no db_manager

    sentinel = object()
    engine_with_db = SetupQualityEngine(
        QualityEngineConfig(
            weights=QualityWeightsConfig(),
            thresholds=QualityThresholdsConfig(),
        ),
        db_manager=sentinel,  # type: ignore[arg-type]
    )
    assert engine_with_db.db is sentinel


def test_config_property_returns_config():
    config = QualityEngineConfig(
        weights=QualityWeightsConfig(),
        thresholds=QualityThresholdsConfig(),
    )
    engine = SetupQualityEngine(config)
    assert engine.config is config
