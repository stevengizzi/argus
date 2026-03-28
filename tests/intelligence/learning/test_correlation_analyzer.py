"""Tests for CorrelationAnalyzer.

Sprint 28, Session 2b.
"""

from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest

from argus.intelligence.learning.correlation_analyzer import CorrelationAnalyzer
from argus.intelligence.learning.models import (
    CorrelationResult,
    LearningLoopConfig,
    OutcomeRecord,
)

_ET = ZoneInfo("America/New_York")


def _make_record(
    strategy_id: str,
    pnl: float,
    timestamp: datetime,
    source: str = "trade",
    symbol: str = "AAPL",
) -> OutcomeRecord:
    """Helper to create an OutcomeRecord with minimal required fields."""
    return OutcomeRecord(
        symbol=symbol,
        strategy_id=strategy_id,
        quality_score=50.0,
        quality_grade="B",
        dimension_scores={},
        regime_context={},
        pnl=pnl,
        r_multiple=None,
        source=source,  # type: ignore[arg-type]
        timestamp=timestamp,
    )


def _ts(year: int, month: int, day: int, hour: int = 12) -> datetime:
    """Create an ET datetime converted to UTC for test records."""
    return datetime(year, month, day, hour, 0, 0, tzinfo=_ET).astimezone(
        timezone.utc
    )


class TestCorrelationAnalyzerHappyPath:
    """Tests for the normal 3+ strategy case."""

    def test_three_strategies_produces_three_pairs(self) -> None:
        """Three strategies should produce 3 pairwise correlations."""
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2)),
            _make_record("orb", -50.0, _ts(2026, 3, 3)),
            _make_record("vwap", 80.0, _ts(2026, 3, 2)),
            _make_record("vwap", -40.0, _ts(2026, 3, 3)),
            _make_record("r2g", -20.0, _ts(2026, 3, 2)),
            _make_record("r2g", 60.0, _ts(2026, 3, 3)),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert len(result.strategy_pairs) == 3
        assert len(result.correlation_matrix) == 3
        assert ("orb", "r2g") in result.strategy_pairs
        assert ("orb", "vwap") in result.strategy_pairs
        assert ("r2g", "vwap") in result.strategy_pairs

    def test_highly_correlated_pair_is_flagged(self) -> None:
        """Strategies with identical P&L patterns should be flagged."""
        records = [
            # orb and vwap have perfectly correlated P&L
            _make_record("orb", 100.0, _ts(2026, 3, 2)),
            _make_record("orb", -50.0, _ts(2026, 3, 3)),
            _make_record("orb", 75.0, _ts(2026, 3, 4)),
            _make_record("vwap", 200.0, _ts(2026, 3, 2)),
            _make_record("vwap", -100.0, _ts(2026, 3, 3)),
            _make_record("vwap", 150.0, _ts(2026, 3, 4)),
        ]
        config = LearningLoopConfig(correlation_threshold=0.7)
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert ("orb", "vwap") in result.flagged_pairs
        assert result.correlation_matrix[("orb", "vwap")] > 0.99

    def test_negatively_correlated_pair_flagged_at_threshold(self) -> None:
        """Pairs with strong negative correlation should also be flagged."""
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2)),
            _make_record("orb", -50.0, _ts(2026, 3, 3)),
            _make_record("orb", 75.0, _ts(2026, 3, 4)),
            _make_record("r2g", -100.0, _ts(2026, 3, 2)),
            _make_record("r2g", 50.0, _ts(2026, 3, 3)),
            _make_record("r2g", -75.0, _ts(2026, 3, 4)),
        ]
        config = LearningLoopConfig(correlation_threshold=0.7)
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert ("orb", "r2g") in result.flagged_pairs
        corr = result.correlation_matrix[("orb", "r2g")]
        assert corr < -0.99


class TestCorrelationAnalyzerEdgeCases:
    """Edge case handling."""

    def test_single_strategy_returns_empty_matrix(self) -> None:
        """A single strategy should produce an empty result."""
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2)),
            _make_record("orb", -50.0, _ts(2026, 3, 3)),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert result.strategy_pairs == []
        assert result.correlation_matrix == {}
        assert result.flagged_pairs == []

    def test_empty_records_returns_empty_result(self) -> None:
        """Empty input should produce an empty result."""
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze([], config)

        assert result.strategy_pairs == []
        assert result.correlation_matrix == {}
        assert result.excluded_strategies == []

    def test_zero_trades_strategy_excluded(self) -> None:
        """Strategy with records only outside the window is excluded."""
        # r2g has no trades at all — only orb and vwap do
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2)),
            _make_record("orb", -50.0, _ts(2026, 3, 3)),
            _make_record("vwap", 80.0, _ts(2026, 3, 2)),
            _make_record("vwap", -40.0, _ts(2026, 3, 3)),
            # r2g only has counterfactual records — trade source selected,
            # so r2g won't appear in daily_pnl
            _make_record("r2g", 30.0, _ts(2026, 3, 2), source="counterfactual"),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert "r2g" in result.excluded_strategies
        # Only one pair: orb-vwap
        assert len(result.strategy_pairs) == 1


class TestCorrelationAnalyzerDailyPnlAggregation:
    """Daily P&L aggregation correctness."""

    def test_multiple_trades_same_day_aggregated(self) -> None:
        """Multiple trades on the same ET day should sum."""
        records = [
            _make_record("orb", 50.0, _ts(2026, 3, 2, 10)),
            _make_record("orb", 30.0, _ts(2026, 3, 2, 14)),
            _make_record("orb", -20.0, _ts(2026, 3, 3)),
            _make_record("vwap", 100.0, _ts(2026, 3, 2)),
            _make_record("vwap", -60.0, _ts(2026, 3, 3)),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        # Verify aggregation via internal method
        daily_pnl = analyzer._aggregate_daily_pnl(records, 20)

        from datetime import date

        assert daily_pnl["orb"][date(2026, 3, 2)] == pytest.approx(80.0)
        assert daily_pnl["orb"][date(2026, 3, 3)] == pytest.approx(-20.0)

    def test_window_days_trims_old_data(self) -> None:
        """Records beyond correlation_window_days should be trimmed."""
        records = []
        # 25 trading days of data for two strategies
        for day_offset in range(25):
            day = 1 + day_offset
            month = 3 if day <= 28 else 4
            actual_day = day if day <= 28 else day - 28
            records.append(
                _make_record("orb", 10.0, _ts(2026, month, actual_day))
            )
            records.append(
                _make_record("vwap", 5.0, _ts(2026, month, actual_day))
            )

        config = LearningLoopConfig(correlation_window_days=10)
        analyzer = CorrelationAnalyzer()

        daily_pnl = analyzer._aggregate_daily_pnl(records, 10)

        # Should only have 10 days of data
        assert len(daily_pnl["orb"]) == 10
        assert len(daily_pnl["vwap"]) == 10


class TestCorrelationAnalyzerSourceSeparation:
    """Amendment 3: trade-sourced records preferred."""

    def test_trade_source_preferred_when_sufficient(self) -> None:
        """When 2+ strategies have trade data, counterfactual excluded."""
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2), source="trade"),
            _make_record("vwap", 80.0, _ts(2026, 3, 2), source="trade"),
            _make_record("orb", 50.0, _ts(2026, 3, 2), source="counterfactual"),
            _make_record("orb", -20.0, _ts(2026, 3, 3), source="trade"),
            _make_record("vwap", -10.0, _ts(2026, 3, 3), source="trade"),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        selected, used_fallback = analyzer._select_source(
            [r for r in records if r.source == "trade"],
            records,
        )

        assert not used_fallback
        assert all(r.source == "trade" for r in selected)

    def test_combined_fallback_when_trade_insufficient(self) -> None:
        """When <2 strategies have trade data, use combined sources."""
        records = [
            _make_record("orb", 100.0, _ts(2026, 3, 2), source="trade"),
            _make_record("vwap", 80.0, _ts(2026, 3, 2), source="counterfactual"),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        selected, used_fallback = analyzer._select_source(
            [r for r in records if r.source == "trade"],
            records,
        )

        assert used_fallback
        assert len(selected) == 2

    def test_zero_variance_returns_zero_correlation(self) -> None:
        """Constant P&L series should return 0.0 correlation."""
        records = [
            _make_record("orb", 50.0, _ts(2026, 3, 2)),
            _make_record("orb", 50.0, _ts(2026, 3, 3)),
            _make_record("orb", 50.0, _ts(2026, 3, 4)),
            _make_record("vwap", 100.0, _ts(2026, 3, 2)),
            _make_record("vwap", -50.0, _ts(2026, 3, 3)),
            _make_record("vwap", 75.0, _ts(2026, 3, 4)),
        ]
        config = LearningLoopConfig()
        analyzer = CorrelationAnalyzer()

        result = analyzer.analyze(records, config)

        assert result.correlation_matrix[("orb", "vwap")] == 0.0
        assert ("orb", "vwap") not in result.flagged_pairs
