"""Tests for LearningService orchestrator.

Covers full pipeline happy path, sparse data, config-disabled, concurrent
guard, proposal supersession, proposal generation, regime enrichment,
CLI argument parsing, and dry-run mode.

Sprint 28, Session 3b.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
from argus.intelligence.learning.learning_service import (
    LearningService,
    _grade_to_yaml_key,
)
from argus.intelligence.learning.learning_store import LearningStore
from argus.intelligence.learning.models import (
    ConfidenceLevel,
    ConfigProposal,
    CorrelationResult,
    DataQualityPreamble,
    LearningLoopConfig,
    LearningReport,
    OutcomeRecord,
    ThresholdRecommendation,
    WeightRecommendation,
)
from argus.intelligence.learning.outcome_collector import OutcomeCollector
from argus.intelligence.learning.threshold_analyzer import ThresholdAnalyzer
from argus.intelligence.learning.weight_analyzer import WeightAnalyzer


# --- Fixtures ---

_NOW = datetime.now(UTC)

_SAMPLE_WEIGHTS = {
    "pattern_strength": 0.30,
    "catalyst_quality": 0.25,
    "volume_profile": 0.20,
    "historical_match": 0.15,
    "regime_alignment": 0.10,
}

_SAMPLE_THRESHOLDS = {
    "A+": 90,
    "A": 80,
    "A-": 70,
    "B+": 60,
    "B": 50,
    "B-": 40,
    "C+": 30,
}


def _make_outcome(
    strategy_id: str = "orb_breakout",
    quality_score: float = 75.0,
    pnl: float = 50.0,
    source: str = "trade",
) -> OutcomeRecord:
    """Create a minimal OutcomeRecord."""
    return OutcomeRecord(
        symbol="AAPL",
        strategy_id=strategy_id,
        quality_score=quality_score,
        quality_grade="B+",
        dimension_scores={"pattern_strength": 80.0, "volume_profile": 70.0},
        regime_context={"primary_regime": "bullish_trending"},
        pnl=pnl,
        r_multiple=1.5,
        source=source,  # type: ignore[arg-type]
        timestamp=_NOW - timedelta(days=5),
    )


def _make_weight_rec(
    dimension: str = "pattern_strength",
    confidence: ConfidenceLevel = ConfidenceLevel.HIGH,
    delta: float = 0.02,
) -> WeightRecommendation:
    """Create a minimal WeightRecommendation."""
    return WeightRecommendation(
        dimension=dimension,
        current_weight=0.30,
        recommended_weight=0.30 + delta,
        delta=delta,
        correlation_trade_source=0.45,
        correlation_counterfactual_source=None,
        p_value=0.03,
        sample_size=50,
        confidence=confidence,
        regime_breakdown={},
        source_divergence_flag=False,
    )


def _make_threshold_rec(
    grade: str = "B+",
    confidence: ConfidenceLevel = ConfidenceLevel.MODERATE,
) -> ThresholdRecommendation:
    """Create a minimal ThresholdRecommendation."""
    return ThresholdRecommendation(
        grade=grade,
        current_threshold=60.0,
        recommended_direction="lower",
        missed_opportunity_rate=0.45,
        correct_rejection_rate=0.55,
        sample_size=40,
        confidence=confidence,
    )


def _make_data_quality(
    total_trades: int = 50,
    total_cf: int = 30,
) -> DataQualityPreamble:
    """Create a minimal DataQualityPreamble."""
    return DataQualityPreamble(
        trading_days_count=20,
        total_trades=total_trades,
        total_counterfactual=total_cf,
        effective_sample_size=total_trades + total_cf,
        known_data_gaps=[],
        earliest_date=_NOW - timedelta(days=30),
        latest_date=_NOW,
    )


def _make_correlation_result() -> CorrelationResult:
    """Create a minimal CorrelationResult."""
    return CorrelationResult(
        strategy_pairs=[("orb_breakout", "vwap_reclaim")],
        correlation_matrix={("orb_breakout", "vwap_reclaim"): 0.35},
        flagged_pairs=[],
        excluded_strategies=[],
        window_days=20,
    )


@pytest.fixture()
def config() -> LearningLoopConfig:
    """Default enabled config."""
    return LearningLoopConfig(enabled=True, analysis_window_days=30)


@pytest.fixture()
def disabled_config() -> LearningLoopConfig:
    """Disabled config."""
    return LearningLoopConfig(enabled=False)


@pytest.fixture()
def mock_collector() -> AsyncMock:
    """Mock OutcomeCollector."""
    collector = AsyncMock(spec=OutcomeCollector)
    records = [_make_outcome(), _make_outcome(pnl=-20.0)]
    collector.collect.return_value = records
    collector.build_data_quality_preamble.return_value = _make_data_quality()
    return collector


@pytest.fixture()
def mock_weight_analyzer() -> MagicMock:
    """Mock WeightAnalyzer."""
    analyzer = MagicMock(spec=WeightAnalyzer)
    analyzer.analyze.return_value = [
        _make_weight_rec("pattern_strength", ConfidenceLevel.HIGH, 0.02),
        _make_weight_rec("catalyst_quality", ConfidenceLevel.LOW, 0.01),
    ]
    analyzer.analyze_by_regime.return_value = {
        "bullish_trending": [
            _make_weight_rec("pattern_strength", ConfidenceLevel.HIGH, 0.03),
        ]
    }
    return analyzer


@pytest.fixture()
def mock_threshold_analyzer() -> MagicMock:
    """Mock ThresholdAnalyzer."""
    analyzer = MagicMock(spec=ThresholdAnalyzer)
    analyzer.analyze.return_value = [
        _make_threshold_rec("B+", ConfidenceLevel.MODERATE),
    ]
    return analyzer


@pytest.fixture()
def mock_correlation_analyzer() -> MagicMock:
    """Mock CorrelationAnalyzer."""
    analyzer = MagicMock(spec=CorrelationAnalyzer)
    analyzer.analyze.return_value = _make_correlation_result()
    return analyzer


@pytest.fixture()
def mock_store() -> AsyncMock:
    """Mock LearningStore."""
    store = AsyncMock(spec=LearningStore)
    store.supersede_proposals.return_value = 2
    return store


@pytest.fixture()
def qe_yaml_path(tmp_path: object) -> str:
    """Create a temporary quality_engine.yaml."""
    import yaml as _yaml

    path = os.path.join(str(tmp_path), "quality_engine.yaml")
    data = {
        "enabled": True,
        "weights": dict(_SAMPLE_WEIGHTS),
        "thresholds": {
            "a_plus": 90, "a": 80, "a_minus": 70,
            "b_plus": 60, "b": 50, "b_minus": 40, "c_plus": 30,
        },
        "risk_tiers": {
            "a_plus": [0.002, 0.003], "a": [0.0015, 0.002],
            "a_minus": [0.001, 0.0015], "b_plus": [0.00075, 0.001],
            "b": [0.0005, 0.00075], "b_minus": [0.00025, 0.0005],
            "c_plus": [0.00025, 0.00025],
        },
        "min_grade_to_trade": "C+",
    }
    with open(path, "w") as f:
        _yaml.safe_dump(data, f)
    return path


@pytest.fixture()
def service(
    config: LearningLoopConfig,
    mock_collector: AsyncMock,
    mock_weight_analyzer: MagicMock,
    mock_threshold_analyzer: MagicMock,
    mock_correlation_analyzer: MagicMock,
    mock_store: AsyncMock,
    qe_yaml_path: str,
) -> LearningService:
    """Build a LearningService with all mocked dependencies."""
    return LearningService(
        config=config,
        outcome_collector=mock_collector,
        weight_analyzer=mock_weight_analyzer,
        threshold_analyzer=mock_threshold_analyzer,
        correlation_analyzer=mock_correlation_analyzer,
        store=mock_store,
        quality_engine_yaml_path=qe_yaml_path,
    )


# --- Tests ---


@pytest.mark.asyncio
async def test_full_pipeline_happy_path(
    service: LearningService,
    mock_collector: AsyncMock,
    mock_weight_analyzer: MagicMock,
    mock_threshold_analyzer: MagicMock,
    mock_correlation_analyzer: MagicMock,
    mock_store: AsyncMock,
) -> None:
    """Full pipeline: collect → analyze → report → persist → propose."""
    report = await service.run_analysis()
    assert report is not None
    assert report.version == 1
    assert len(report.weight_recommendations) == 2
    assert len(report.threshold_recommendations) == 1
    assert report.correlation_result is not None

    mock_collector.collect.assert_called_once()
    mock_collector.build_data_quality_preamble.assert_called_once()
    mock_weight_analyzer.analyze.assert_called_once()
    mock_weight_analyzer.analyze_by_regime.assert_called_once()
    mock_threshold_analyzer.analyze.assert_called_once()
    mock_correlation_analyzer.analyze.assert_called_once()
    mock_store.save_report.assert_called_once()
    mock_store.supersede_proposals.assert_called_once()


@pytest.mark.asyncio
async def test_sparse_data_empty_collector(
    config: LearningLoopConfig,
    mock_weight_analyzer: MagicMock,
    mock_threshold_analyzer: MagicMock,
    mock_correlation_analyzer: MagicMock,
    mock_store: AsyncMock,
    qe_yaml_path: str,
) -> None:
    """Pipeline handles empty data from collector without error."""
    collector = AsyncMock(spec=OutcomeCollector)
    collector.collect.return_value = []
    collector.build_data_quality_preamble.return_value = _make_data_quality(0, 0)

    svc = LearningService(
        config=config,
        outcome_collector=collector,
        weight_analyzer=mock_weight_analyzer,
        threshold_analyzer=mock_threshold_analyzer,
        correlation_analyzer=mock_correlation_analyzer,
        store=mock_store,
        quality_engine_yaml_path=qe_yaml_path,
    )

    report = await svc.run_analysis()
    assert report is not None
    assert report.data_quality.effective_sample_size == 0
    mock_store.save_report.assert_called_once()


@pytest.mark.asyncio
async def test_config_disabled_returns_none(
    disabled_config: LearningLoopConfig,
    mock_collector: AsyncMock,
    mock_weight_analyzer: MagicMock,
    mock_threshold_analyzer: MagicMock,
    mock_correlation_analyzer: MagicMock,
    mock_store: AsyncMock,
    qe_yaml_path: str,
) -> None:
    """Config disabled → returns None, no analysis."""
    svc = LearningService(
        config=disabled_config,
        outcome_collector=mock_collector,
        weight_analyzer=mock_weight_analyzer,
        threshold_analyzer=mock_threshold_analyzer,
        correlation_analyzer=mock_correlation_analyzer,
        store=mock_store,
        quality_engine_yaml_path=qe_yaml_path,
    )

    result = await svc.run_analysis()
    assert result is None
    mock_collector.collect.assert_not_called()
    mock_store.save_report.assert_not_called()


@pytest.mark.asyncio
async def test_concurrent_guard_rejects(service: LearningService) -> None:
    """Concurrent guard prevents simultaneous runs."""
    service._running = True
    with pytest.raises(RuntimeError, match="already running"):
        await service.run_analysis()


@pytest.mark.asyncio
async def test_concurrent_guard_resets_on_error(
    config: LearningLoopConfig,
    mock_store: AsyncMock,
    qe_yaml_path: str,
) -> None:
    """Concurrent guard resets (try/finally) even on error."""
    collector = AsyncMock(spec=OutcomeCollector)
    collector.collect.side_effect = RuntimeError("DB error")

    svc = LearningService(
        config=config,
        outcome_collector=collector,
        weight_analyzer=MagicMock(spec=WeightAnalyzer),
        threshold_analyzer=MagicMock(spec=ThresholdAnalyzer),
        correlation_analyzer=MagicMock(spec=CorrelationAnalyzer),
        store=mock_store,
        quality_engine_yaml_path=qe_yaml_path,
    )

    with pytest.raises(RuntimeError, match="DB error"):
        await svc.run_analysis()

    # Guard must be reset
    assert svc._running is False


@pytest.mark.asyncio
async def test_supersede_called_before_new_proposals(
    service: LearningService,
    mock_store: AsyncMock,
) -> None:
    """Supersession is called BEFORE new proposals are saved."""
    call_order: list[str] = []
    mock_store.supersede_proposals.side_effect = (
        lambda rid: call_order.append("supersede") or 0
    )
    original_save = mock_store.save_proposal.side_effect

    async def track_save(proposal: ConfigProposal) -> None:
        call_order.append("save_proposal")

    mock_store.save_proposal.side_effect = track_save

    await service.run_analysis()

    assert "supersede" in call_order
    # Supersede must come before any save_proposal
    if "save_proposal" in call_order:
        supersede_idx = call_order.index("supersede")
        first_save_idx = call_order.index("save_proposal")
        assert supersede_idx < first_save_idx


@pytest.mark.asyncio
async def test_proposals_generated_for_actionable_only(
    service: LearningService,
    mock_store: AsyncMock,
    mock_weight_analyzer: MagicMock,
) -> None:
    """Only HIGH/MODERATE confidence recs generate proposals."""
    # Weight recs: 1 HIGH (pattern_strength), 1 LOW (catalyst_quality)
    # Threshold recs: 1 MODERATE (B+)
    # Expected proposals: 1 weight (HIGH) + 1 threshold (MODERATE) = 2
    await service.run_analysis()

    proposals_saved = [
        call.args[0] for call in mock_store.save_proposal.call_args_list
    ]
    assert len(proposals_saved) == 2

    field_paths = {p.proposal_id: p.field_path for p in proposals_saved}
    statuses = {p.status for p in proposals_saved}
    assert all(s == "PENDING" for s in statuses)


@pytest.mark.asyncio
async def test_window_days_override(
    service: LearningService,
    mock_collector: AsyncMock,
) -> None:
    """Custom window_days is used for date range."""
    await service.run_analysis(window_days=60)

    call_args = mock_collector.collect.call_args
    start_date, end_date = call_args.args[0], call_args.args[1]
    delta = (end_date - start_date).days
    assert 59 <= delta <= 61  # Allow for sub-day rounding


@pytest.mark.asyncio
async def test_strategy_id_filter_passed(
    service: LearningService,
    mock_collector: AsyncMock,
) -> None:
    """Strategy ID filter is forwarded to collector."""
    await service.run_analysis(strategy_id="vwap_reclaim")

    call_args = mock_collector.collect.call_args
    assert call_args.args[2] == "vwap_reclaim"


@pytest.mark.asyncio
async def test_regime_enrichment(
    service: LearningService,
) -> None:
    """Weight recs are enriched with regime breakdown data."""
    report = await service.run_analysis()
    assert report is not None

    # pattern_strength should have regime breakdown from analyze_by_regime
    ps_rec = next(
        r for r in report.weight_recommendations
        if r.dimension == "pattern_strength"
    )
    assert "bullish_trending" in ps_rec.regime_breakdown


@pytest.mark.asyncio
async def test_report_version_is_set(service: LearningService) -> None:
    """Report version is set for forward compatibility (Sprint 32.5)."""
    report = await service.run_analysis()
    assert report is not None
    assert report.version == 1


@pytest.mark.asyncio
async def test_yaml_missing_uses_defaults(
    config: LearningLoopConfig,
    mock_collector: AsyncMock,
    mock_weight_analyzer: MagicMock,
    mock_threshold_analyzer: MagicMock,
    mock_correlation_analyzer: MagicMock,
    mock_store: AsyncMock,
    tmp_path: object,
) -> None:
    """Missing quality_engine.yaml falls back to default weights/thresholds."""
    missing_path = os.path.join(str(tmp_path), "nonexistent.yaml")
    svc = LearningService(
        config=config,
        outcome_collector=mock_collector,
        weight_analyzer=mock_weight_analyzer,
        threshold_analyzer=mock_threshold_analyzer,
        correlation_analyzer=mock_correlation_analyzer,
        store=mock_store,
        quality_engine_yaml_path=missing_path,
    )

    report = await svc.run_analysis()
    assert report is not None

    # Weight analyzer should have been called with default weights
    call_args = mock_weight_analyzer.analyze.call_args
    weights = call_args.args[2]
    assert weights["pattern_strength"] == 0.30


# --- CLI tests ---


def test_cli_parse_args_defaults() -> None:
    """CLI defaults: no overrides, no dry-run."""
    from scripts.run_learning_analysis import parse_args

    args = parse_args([])
    assert args.window_days is None
    assert args.strategy_id is None
    assert args.dry_run is False


def test_cli_parse_args_all_flags() -> None:
    """CLI with all flags set."""
    from scripts.run_learning_analysis import parse_args

    args = parse_args(["--window-days", "60", "--strategy-id", "orb", "--dry-run"])
    assert args.window_days == 60
    assert args.strategy_id == "orb"
    assert args.dry_run is True


def test_cli_load_config_missing_yaml() -> None:
    """Config loader returns defaults when YAML doesn't exist."""
    from scripts.run_learning_analysis import load_config

    with patch(
        "scripts.run_learning_analysis._LEARNING_LOOP_YAML",
        "/nonexistent/path.yaml",
    ):
        config = load_config()
        assert isinstance(config, LearningLoopConfig)
        assert config.enabled is True


# --- Helper tests ---


def test_grade_to_yaml_key() -> None:
    """Grade display format converts to YAML snake_case."""
    assert _grade_to_yaml_key("A+") == "a_plus"
    assert _grade_to_yaml_key("A-") == "a_minus"
    assert _grade_to_yaml_key("B") == "b"
    assert _grade_to_yaml_key("C+") == "c_plus"
