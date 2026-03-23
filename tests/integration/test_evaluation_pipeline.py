"""Integration tests for the Sprint 27.5 evaluation pipeline.

Validates the full pipeline: BacktestResult → MOR → compare → ensemble,
plus slippage model wiring and report formatting.

Sprint 27.5 Session 6.
"""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from argus.analytics.comparison import (
    ComparisonVerdict,
    compare,
    format_comparison_report,
)
from argus.analytics.ensemble_evaluation import (
    EnsembleResult,
    build_ensemble_result,
    evaluate_cohort_addition,
    format_ensemble_report,
)
from argus.analytics.evaluation import (
    ConfidenceTier,
    MultiObjectiveResult,
    RegimeMetrics,
    from_backtest_result,
)
from argus.analytics.slippage_model import (
    SlippageConfidence,
    StrategySlippageModel,
    save_slippage_model,
)
from argus.backtest.config import BacktestEngineConfig
from argus.backtest.metrics import BacktestResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_backtest_result(
    strategy_id: str = "strat_orb_breakout",
    total_trades: int = 60,
    win_rate: float = 0.55,
    sharpe: float = 1.8,
    max_dd_pct: float = -0.08,
    profit_factor: float = 1.6,
    expectancy: float = 0.35,
    net_pnl: float = 5_000.0,
) -> BacktestResult:
    """Build a synthetic BacktestResult with plausible field values."""
    initial_capital = 100_000.0
    winning = int(total_trades * win_rate)
    losing = total_trades - winning
    return BacktestResult(
        strategy_id=strategy_id,
        start_date=date(2025, 6, 1),
        end_date=date(2025, 12, 31),
        initial_capital=initial_capital,
        final_equity=initial_capital + net_pnl,
        trading_days=140,
        total_trades=total_trades,
        winning_trades=winning,
        losing_trades=losing,
        breakeven_trades=0,
        win_rate=win_rate,
        profit_factor=profit_factor,
        avg_r_multiple=expectancy,
        avg_winner_r=0.8,
        avg_loser_r=-0.6,
        expectancy=expectancy,
        max_drawdown_dollars=initial_capital * abs(max_dd_pct),
        max_drawdown_pct=max_dd_pct,
        sharpe_ratio=sharpe,
        recovery_factor=net_pnl / (initial_capital * abs(max_dd_pct)),
        avg_hold_minutes=25.0,
        max_consecutive_wins=5,
        max_consecutive_losses=3,
        largest_win_dollars=800.0,
        largest_loss_dollars=-500.0,
        largest_win_r=2.1,
        largest_loss_r=-1.0,
    )


def _make_regime_results() -> dict[str, RegimeMetrics]:
    """Build per-regime metrics covering 3 regimes."""
    return {
        "bullish_trending": RegimeMetrics(
            sharpe_ratio=2.1,
            max_drawdown_pct=-0.05,
            profit_factor=2.0,
            win_rate=0.6,
            total_trades=20,
            expectancy_per_trade=0.45,
        ),
        "range_bound": RegimeMetrics(
            sharpe_ratio=1.4,
            max_drawdown_pct=-0.06,
            profit_factor=1.3,
            win_rate=0.52,
            total_trades=25,
            expectancy_per_trade=0.25,
        ),
        "bearish_trending": RegimeMetrics(
            sharpe_ratio=0.8,
            max_drawdown_pct=-0.10,
            profit_factor=1.1,
            win_rate=0.48,
            total_trades=15,
            expectancy_per_trade=0.15,
        ),
    }


def _make_mor(
    strategy_id: str = "strat_orb_breakout",
    sharpe: float = 1.8,
    max_dd: float = -0.08,
    profit_factor: float = 1.6,
    win_rate: float = 0.55,
    expectancy: float = 0.35,
    total_trades: int = 60,
    with_regimes: bool = True,
) -> MultiObjectiveResult:
    """Build a synthetic MOR directly."""
    regimes = _make_regime_results() if with_regimes else {}
    regime_counts = {k: v.total_trades for k, v in regimes.items()}

    from argus.analytics.evaluation import compute_confidence_tier

    confidence = compute_confidence_tier(total_trades, regime_counts)

    return MultiObjectiveResult(
        strategy_id=strategy_id,
        parameter_hash="abcd1234",
        evaluation_date=datetime.now(UTC),
        data_range=(date(2025, 6, 1), date(2025, 12, 31)),
        sharpe_ratio=sharpe,
        max_drawdown_pct=max_dd,
        profit_factor=profit_factor,
        win_rate=win_rate,
        total_trades=total_trades,
        expectancy_per_trade=expectancy,
        regime_results=regimes,
        confidence_tier=confidence,
    )


def _make_slippage_model(
    strategy_id: str = "strat_orb_breakout",
    mean_bps: float = 3.5,
    std_bps: float = 1.2,
    confidence: SlippageConfidence = SlippageConfidence.MODERATE,
    sample_count: int = 30,
) -> StrategySlippageModel:
    """Build a synthetic slippage model."""
    return StrategySlippageModel(
        strategy_id=strategy_id,
        estimated_mean_slippage_bps=mean_bps,
        estimated_std_slippage_bps=std_bps,
        time_of_day_adjustment={"pre_10am": 1.0, "10am_2pm": 0.0, "post_2pm": -0.5},
        size_adjustment_slope=0.02,
        sample_count=sample_count,
        confidence=confidence,
        last_calibrated=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestFullPipelineRoundtrip:
    """Test BacktestResult → MOR conversion with regime data."""

    def test_full_pipeline_roundtrip(self) -> None:
        result = _make_backtest_result()
        regimes = _make_regime_results()

        mor = from_backtest_result(
            result=result,
            regime_results=regimes,
            wfe=0.45,
            is_oos=True,
            parameter_hash_value="deadbeef",
        )

        assert mor.strategy_id == result.strategy_id
        assert mor.sharpe_ratio == result.sharpe_ratio
        assert mor.max_drawdown_pct == result.max_drawdown_pct
        assert mor.profit_factor == result.profit_factor
        assert mor.win_rate == result.win_rate
        assert mor.total_trades == result.total_trades
        assert mor.expectancy_per_trade == result.expectancy
        assert mor.wfe == 0.45
        assert mor.is_oos is True
        assert mor.parameter_hash == "deadbeef"
        assert len(mor.regime_results) == 3
        assert "bullish_trending" in mor.regime_results
        assert "range_bound" in mor.regime_results
        assert "bearish_trending" in mor.regime_results
        # Confidence should be HIGH: 60 trades, 20+25+15 across 3 regimes (all >=15)
        assert mor.confidence_tier == ConfidenceTier.HIGH


class TestCompareTwoBacktestRuns:
    """Test Pareto comparison of two MORs."""

    def test_compare_two_backtest_runs(self) -> None:
        result_a = _make_backtest_result(
            strategy_id="strat_a",
            sharpe=2.0,
            max_dd_pct=-0.05,
            profit_factor=2.0,
            win_rate=0.60,
            expectancy=0.45,
        )
        result_b = _make_backtest_result(
            strategy_id="strat_b",
            sharpe=1.5,
            max_dd_pct=-0.10,
            profit_factor=1.3,
            win_rate=0.50,
            expectancy=0.20,
        )

        mor_a = from_backtest_result(
            result_a,
            regime_results=_make_regime_results(),
        )
        mor_b = from_backtest_result(
            result_b,
            regime_results=_make_regime_results(),
        )

        verdict = compare(mor_a, mor_b)
        # A is better on all 5 metrics → DOMINATES
        assert verdict == ComparisonVerdict.DOMINATES


class TestEnsembleFromBacktestResults:
    """Test ensemble construction from multiple MORs."""

    def test_ensemble_from_backtest_results(self) -> None:
        mor_a = _make_mor(strategy_id="strat_orb", sharpe=1.8)
        mor_b = _make_mor(strategy_id="strat_vwap", sharpe=1.2, max_dd=-0.12)

        ensemble = build_ensemble_result([mor_a, mor_b], cohort_id="test_cohort")

        assert isinstance(ensemble, EnsembleResult)
        assert len(ensemble.strategy_ids) == 2
        assert "strat_orb" in ensemble.strategy_ids
        assert "strat_vwap" in ensemble.strategy_ids
        assert ensemble.aggregate.total_trades == mor_a.total_trades + mor_b.total_trades
        assert len(ensemble.marginal_contributions) == 2
        assert "strat_orb" in ensemble.marginal_contributions
        assert "strat_vwap" in ensemble.marginal_contributions
        assert ensemble.diversification_ratio >= 1.0


class TestCohortAdditionIntegration:
    """Test cohort addition evaluation."""

    def test_cohort_addition_integration(self) -> None:
        mor_a = _make_mor(strategy_id="strat_orb", sharpe=1.8)
        mor_b = _make_mor(strategy_id="strat_vwap", sharpe=1.2)
        baseline = build_ensemble_result([mor_a, mor_b], cohort_id="baseline")

        new_mor = _make_mor(strategy_id="strat_r2g", sharpe=1.5, max_dd=-0.07)
        result = evaluate_cohort_addition(baseline, [new_mor])

        assert isinstance(result, EnsembleResult)
        assert result.baseline_ensemble is not None
        assert result.improvement_verdict in list(ComparisonVerdict)
        assert "strat_r2g" in result.strategy_ids


class TestSlippageModelWiring:
    """Test slippage model loading via BacktestEngineConfig."""

    def test_slippage_model_wiring(self, tmp_path: Path) -> None:
        model = _make_slippage_model()
        model_path = str(tmp_path / "slippage.json")
        save_slippage_model(model, model_path)

        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path=model_path,
        )

        # Verify config field works
        assert config.slippage_model_path == model_path

        # Verify engine loads the model
        from argus.backtest.engine import BacktestEngine

        engine = BacktestEngine(config)
        assert engine._slippage_model is not None
        assert engine._slippage_model.strategy_id == "strat_orb_breakout"
        assert engine._slippage_model.confidence == SlippageConfidence.MODERATE

    def test_slippage_model_file_not_found(self, tmp_path: Path) -> None:
        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path=str(tmp_path / "nonexistent.json"),
        )

        from argus.backtest.engine import BacktestEngine

        engine = BacktestEngine(config)
        # Should gracefully handle missing file
        assert engine._slippage_model is None


class TestSlippageModelNoneBackwardCompat:
    """Test backward compatibility with no slippage model."""

    def test_slippage_model_none_backward_compat(self) -> None:
        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
        )
        assert config.slippage_model_path is None

        from argus.backtest.engine import BacktestEngine

        engine = BacktestEngine(config)
        assert engine._slippage_model is None

    def test_execution_quality_adjustment_none_without_model(self) -> None:
        """MOR has execution_quality_adjustment=None when no slippage model."""
        result = _make_backtest_result()
        mor = from_backtest_result(result, regime_results=_make_regime_results())
        assert mor.execution_quality_adjustment is None


class TestFormatReports:
    """Test report formatting functions."""

    def test_format_comparison_report(self) -> None:
        mor_a = _make_mor(strategy_id="strat_orb", sharpe=1.8)
        mor_b = _make_mor(strategy_id="strat_vwap", sharpe=1.2)

        report = format_comparison_report(mor_a, mor_b)
        assert isinstance(report, str)
        assert len(report) > 0
        assert "COMPARISON REPORT" in report
        assert "strat_orb" in report
        assert "strat_vwap" in report

    def test_format_ensemble_report(self) -> None:
        mor_a = _make_mor(strategy_id="strat_orb", sharpe=1.8)
        mor_b = _make_mor(strategy_id="strat_vwap", sharpe=1.2)
        ensemble = build_ensemble_result([mor_a, mor_b], cohort_id="test")

        report = format_ensemble_report(ensemble)
        assert isinstance(report, str)
        assert len(report) > 0
        assert "ENSEMBLE EVALUATION REPORT" in report
        assert "strat_orb" in report


class TestNoCircularImports:
    """Test that all new analytics modules import without circular errors."""

    def test_no_circular_imports(self) -> None:
        import importlib

        modules = [
            "argus.analytics.evaluation",
            "argus.analytics.comparison",
            "argus.analytics.ensemble_evaluation",
            "argus.analytics.slippage_model",
            "argus.backtest.engine",
        ]

        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert mod is not None


class TestConfigValidation:
    """Test BacktestEngineConfig slippage_model_path field recognition."""

    def test_config_with_slippage_model_path(self) -> None:
        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path="/tmp/test.json",
        )
        assert config.slippage_model_path == "/tmp/test.json"

    def test_config_without_slippage_model_path(self) -> None:
        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
        )
        assert config.slippage_model_path is None


class TestExecutionQualityAdjustmentComputation:
    """Test the _compute_execution_quality_adjustment helper."""

    def test_returns_none_without_model(self) -> None:
        from argus.backtest.engine import BacktestEngine

        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
        )
        engine = BacktestEngine(config)
        result = _make_backtest_result()

        adjustment = engine._compute_execution_quality_adjustment(result)
        assert adjustment is None

    def test_returns_none_for_insufficient_confidence(
        self, tmp_path: Path
    ) -> None:
        model = _make_slippage_model(
            confidence=SlippageConfidence.INSUFFICIENT, sample_count=2
        )
        model_path = str(tmp_path / "slippage.json")
        save_slippage_model(model, model_path)

        from argus.backtest.engine import BacktestEngine

        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path=model_path,
        )
        engine = BacktestEngine(config)
        result = _make_backtest_result()

        adjustment = engine._compute_execution_quality_adjustment(result)
        assert adjustment is None

    def test_returns_value_with_valid_model(self, tmp_path: Path) -> None:
        model = _make_slippage_model(mean_bps=5.0)
        model_path = str(tmp_path / "slippage.json")
        save_slippage_model(model, model_path)

        from argus.backtest.engine import BacktestEngine

        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path=model_path,
        )
        engine = BacktestEngine(config)
        # Populate trading_days so computation works
        engine._trading_days = [
            date(2025, 6, d) for d in range(2, 30)
        ]

        result = _make_backtest_result(sharpe=1.8, net_pnl=5_000.0)
        adjustment = engine._compute_execution_quality_adjustment(result)

        assert adjustment is not None
        assert isinstance(adjustment, float)

    def test_returns_none_for_zero_trades(self, tmp_path: Path) -> None:
        model = _make_slippage_model()
        model_path = str(tmp_path / "slippage.json")
        save_slippage_model(model, model_path)

        from argus.backtest.engine import BacktestEngine

        config = BacktestEngineConfig(
            start_date=date(2025, 6, 1),
            end_date=date(2025, 12, 31),
            slippage_model_path=model_path,
        )
        engine = BacktestEngine(config)
        engine._trading_days = [date(2025, 6, 2)]

        result = _make_backtest_result(total_trades=0, sharpe=0.0, net_pnl=0.0)
        adjustment = engine._compute_execution_quality_adjustment(result)
        assert adjustment is None
