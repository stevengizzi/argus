"""Tests for the CorrelationTracker."""

import pytest

from argus.core.correlation import CorrelationTracker


class TestRecordAndRetrieveDailyPnl:
    """Tests for recording and retrieving daily P&L data."""

    def test_record_single_pnl(self) -> None:
        """Recording a single P&L entry creates the strategy."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)

        assert "orb_breakout" in tracker.get_strategy_ids()
        assert tracker.get_date_count("orb_breakout") == 1

    def test_record_multiple_days(self) -> None:
        """Recording multiple days accumulates correctly."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)
        tracker.record_daily_pnl("orb_breakout", "2026-02-21", -50.00)
        tracker.record_daily_pnl("orb_breakout", "2026-02-22", 200.00)

        assert tracker.get_date_count("orb_breakout") == 3

    def test_record_multiple_strategies(self) -> None:
        """Recording multiple strategies tracks them separately."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)
        tracker.record_daily_pnl("orb_scalp", "2026-02-20", -50.00)

        assert len(tracker.get_strategy_ids()) == 2
        assert "orb_breakout" in tracker.get_strategy_ids()
        assert "orb_scalp" in tracker.get_strategy_ids()

    def test_overwrite_existing_date(self) -> None:
        """Recording same date again overwrites the value."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 200.00)

        # Should still be one entry
        assert tracker.get_date_count("orb_breakout") == 1


class TestCorrelationMatrixTwoStrategies:
    """Tests for correlation matrix with two strategies."""

    def test_perfect_positive_correlation(self) -> None:
        """Two strategies with identical returns have correlation 1.0."""
        tracker = CorrelationTracker()

        # Same P&L pattern for both strategies
        for i, pnl in enumerate([100.0, -50.0, 200.0, -100.0, 150.0]):
            date = f"2026-02-{20 + i:02d}"
            tracker.record_daily_pnl("strategy_a", date, pnl)
            tracker.record_daily_pnl("strategy_b", date, pnl)

        matrix = tracker.get_correlation_matrix()
        assert matrix is not None
        assert matrix.loc["strategy_a", "strategy_b"] == pytest.approx(1.0)
        assert matrix.loc["strategy_b", "strategy_a"] == pytest.approx(1.0)

    def test_perfect_negative_correlation(self) -> None:
        """Two strategies with opposite returns have correlation -1.0."""
        tracker = CorrelationTracker()

        pnl_values = [100.0, -50.0, 200.0, -100.0, 150.0]
        for i, pnl in enumerate(pnl_values):
            date = f"2026-02-{20 + i:02d}"
            tracker.record_daily_pnl("strategy_a", date, pnl)
            tracker.record_daily_pnl("strategy_b", date, -pnl)

        matrix = tracker.get_correlation_matrix()
        assert matrix is not None
        assert matrix.loc["strategy_a", "strategy_b"] == pytest.approx(-1.0)

    def test_diagonal_is_one(self) -> None:
        """Diagonal of correlation matrix is 1.0 (self-correlation)."""
        tracker = CorrelationTracker()

        for i in range(5):
            date = f"2026-02-{20 + i:02d}"
            tracker.record_daily_pnl("strategy_a", date, float(i * 10))
            tracker.record_daily_pnl("strategy_b", date, float(i * -5 + 100))

        matrix = tracker.get_correlation_matrix()
        assert matrix is not None
        assert matrix.loc["strategy_a", "strategy_a"] == pytest.approx(1.0)
        assert matrix.loc["strategy_b", "strategy_b"] == pytest.approx(1.0)


class TestCorrelationMatrixInsufficientDataReturnsNone:
    """Tests for correlation matrix with insufficient data."""

    def test_single_strategy_returns_none(self) -> None:
        """Correlation matrix with only one strategy returns None."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)
        tracker.record_daily_pnl("orb_breakout", "2026-02-21", -50.00)

        assert tracker.get_correlation_matrix() is None

    def test_no_strategies_returns_none(self) -> None:
        """Correlation matrix with no data returns None."""
        tracker = CorrelationTracker()
        assert tracker.get_correlation_matrix() is None

    def test_single_overlapping_day_returns_none(self) -> None:
        """Correlation matrix with only one overlapping day returns None."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("strategy_a", "2026-02-20", 100.0)
        tracker.record_daily_pnl("strategy_a", "2026-02-21", 200.0)
        tracker.record_daily_pnl("strategy_b", "2026-02-20", 50.0)
        # strategy_b only has one day that overlaps with strategy_a

        assert tracker.get_correlation_matrix() is None


class TestPairwiseCorrelation:
    """Tests for pairwise correlation between two strategies."""

    def test_pairwise_positive_correlation(self) -> None:
        """Pairwise correlation for positively correlated strategies."""
        tracker = CorrelationTracker()

        for i, pnl in enumerate([100.0, -50.0, 200.0, -100.0, 150.0]):
            date = f"2026-02-{20 + i:02d}"
            tracker.record_daily_pnl("strategy_a", date, pnl)
            tracker.record_daily_pnl("strategy_b", date, pnl * 0.8)  # ~80% of A

        corr = tracker.get_pairwise_correlation("strategy_a", "strategy_b")
        assert corr is not None
        assert corr == pytest.approx(1.0)

    def test_pairwise_missing_strategy_returns_none(self) -> None:
        """Pairwise correlation with missing strategy returns None."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("strategy_a", "2026-02-20", 100.0)

        assert tracker.get_pairwise_correlation("strategy_a", "strategy_b") is None
        assert tracker.get_pairwise_correlation("strategy_b", "strategy_a") is None

    def test_pairwise_insufficient_overlap_returns_none(self) -> None:
        """Pairwise correlation with insufficient overlap returns None."""
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("strategy_a", "2026-02-20", 100.0)
        tracker.record_daily_pnl("strategy_b", "2026-02-21", 50.0)

        # No overlapping dates
        assert tracker.get_pairwise_correlation("strategy_a", "strategy_b") is None


class TestSeedFromBacktest:
    """Tests for seeding from backtest data."""

    def test_seed_creates_strategy(self) -> None:
        """Seeding creates the strategy with all dates."""
        tracker = CorrelationTracker()

        backtest_data = {
            "2026-01-15": 100.0,
            "2026-01-16": -50.0,
            "2026-01-17": 200.0,
            "2026-01-18": -30.0,
            "2026-01-19": 150.0,
        }
        tracker.seed_from_backtest("orb_breakout", backtest_data)

        assert "orb_breakout" in tracker.get_strategy_ids()
        assert tracker.get_date_count("orb_breakout") == 5

    def test_seed_can_be_extended(self) -> None:
        """Seeded data can be extended with record_daily_pnl."""
        tracker = CorrelationTracker()

        tracker.seed_from_backtest("orb_breakout", {"2026-01-15": 100.0})
        tracker.record_daily_pnl("orb_breakout", "2026-01-16", 200.0)

        assert tracker.get_date_count("orb_breakout") == 2

    def test_seed_overwrites_existing_dates(self) -> None:
        """Seeding overwrites existing dates for the strategy."""
        tracker = CorrelationTracker()

        tracker.record_daily_pnl("orb_breakout", "2026-01-15", 50.0)
        tracker.seed_from_backtest("orb_breakout", {"2026-01-15": 100.0})

        # Date count should still be 1 (same date overwritten)
        assert tracker.get_date_count("orb_breakout") == 1


class TestHasSufficientData:
    """Tests for has_sufficient_data method."""

    def test_insufficient_strategies(self) -> None:
        """Returns False with fewer than 2 strategies."""
        tracker = CorrelationTracker()
        tracker.seed_from_backtest(
            "strategy_a",
            {f"2026-01-{i:02d}": float(i * 10) for i in range(1, 25)},
        )

        assert tracker.has_sufficient_data(min_days=20) is False

    def test_insufficient_overlapping_days(self) -> None:
        """Returns False with insufficient overlapping days."""
        tracker = CorrelationTracker()

        # Strategy A: days 1-15
        tracker.seed_from_backtest(
            "strategy_a",
            {f"2026-01-{i:02d}": float(i * 10) for i in range(1, 16)},
        )
        # Strategy B: days 10-24 (only 6 days overlap: 10-15)
        tracker.seed_from_backtest(
            "strategy_b",
            {f"2026-01-{i:02d}": float(i * -5) for i in range(10, 25)},
        )

        assert tracker.has_sufficient_data(min_days=20) is False
        assert tracker.has_sufficient_data(min_days=5) is True

    def test_sufficient_data(self) -> None:
        """Returns True when sufficient overlapping data exists."""
        tracker = CorrelationTracker()

        # Both strategies: days 1-25
        data = {f"2026-01-{i:02d}": float(i * 10) for i in range(1, 26)}
        tracker.seed_from_backtest("strategy_a", data)
        tracker.seed_from_backtest("strategy_b", data)

        assert tracker.has_sufficient_data(min_days=20) is True
        assert tracker.has_sufficient_data(min_days=25) is True


class TestOverlappingDatesOnly:
    """Tests for correlation using only overlapping dates."""

    def test_non_overlapping_dates_excluded(self) -> None:
        """Correlation only uses overlapping dates."""
        tracker = CorrelationTracker()

        # Strategy A: days 1-10
        for i in range(1, 11):
            tracker.record_daily_pnl("strategy_a", f"2026-01-{i:02d}", float(i * 10))

        # Strategy B: days 5-14 (overlaps on 5-10)
        for i in range(5, 15):
            tracker.record_daily_pnl("strategy_b", f"2026-01-{i:02d}", float(i * 10))

        # Both strategies should still produce a valid correlation
        # using only the 6 overlapping days (5-10)
        corr = tracker.get_pairwise_correlation("strategy_a", "strategy_b")
        assert corr is not None
        assert corr == pytest.approx(1.0)  # Same pattern, perfect correlation

    def test_completely_disjoint_dates_returns_none(self) -> None:
        """No overlapping dates returns None."""
        tracker = CorrelationTracker()

        # Strategy A: days 1-5
        for i in range(1, 6):
            tracker.record_daily_pnl("strategy_a", f"2026-01-{i:02d}", float(i * 10))

        # Strategy B: days 10-14 (no overlap)
        for i in range(10, 15):
            tracker.record_daily_pnl("strategy_b", f"2026-01-{i:02d}", float(i * 10))

        assert tracker.get_pairwise_correlation("strategy_a", "strategy_b") is None
        assert tracker.get_correlation_matrix() is None
