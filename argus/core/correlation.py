"""Strategy correlation tracking for the Orchestrator.

Tracks daily P&L across strategies to compute correlation matrices.
Used by the Orchestrator to limit combined allocation to highly
correlated strategies (reduces portfolio risk from strategy overlap).
"""

from __future__ import annotations

import logging

import pandas as pd

logger = logging.getLogger(__name__)


class CorrelationTracker:
    """Tracks daily P&L across strategies and computes correlations.

    Maintains a rolling window of daily P&L per strategy. When enough
    data is available, computes pairwise correlations to inform the
    Orchestrator's allocation decisions.

    Usage:
        tracker = CorrelationTracker()
        tracker.record_daily_pnl("orb_breakout", "2026-02-20", 150.00)
        tracker.record_daily_pnl("orb_scalp", "2026-02-20", -50.00)

        # After accumulating data over multiple days
        if tracker.has_sufficient_data(min_days=20):
            matrix = tracker.get_correlation_matrix()
            corr = tracker.get_pairwise_correlation("orb_breakout", "orb_scalp")
    """

    def __init__(self) -> None:
        """Initialize the correlation tracker.

        Internal storage maps strategy_id -> {date_str -> daily_pnl}.
        """
        self._data: dict[str, dict[str, float]] = {}

    def record_daily_pnl(self, strategy_id: str, date: str, pnl: float) -> None:
        """Record a strategy's daily P&L.

        Args:
            strategy_id: The strategy identifier.
            date: Date string in YYYY-MM-DD format.
            pnl: The net P&L for that day (can be positive or negative).
        """
        if strategy_id not in self._data:
            self._data[strategy_id] = {}
        self._data[strategy_id][date] = pnl
        logger.debug("Recorded P&L for %s on %s: %.2f", strategy_id, date, pnl)

    def seed_from_backtest(self, strategy_id: str, daily_pnl: dict[str, float]) -> None:
        """Bulk load historical P&L from backtest results.

        Useful for seeding the tracker with backtested data when a
        strategy first comes online.

        Args:
            strategy_id: The strategy identifier.
            daily_pnl: Dict mapping date strings (YYYY-MM-DD) to P&L values.
        """
        if strategy_id not in self._data:
            self._data[strategy_id] = {}
        self._data[strategy_id].update(daily_pnl)
        logger.info(
            "Seeded %d days of P&L for strategy %s",
            len(daily_pnl),
            strategy_id,
        )

    def get_correlation_matrix(self) -> pd.DataFrame | None:
        """Compute the correlation matrix across all tracked strategies.

        Returns:
            A pandas DataFrame with strategy IDs as both index and columns,
            containing pairwise Pearson correlation coefficients.
            Returns None if there are fewer than 2 strategies or insufficient
            overlapping data points.
        """
        if len(self._data) < 2:
            logger.debug("Insufficient strategies for correlation matrix (need >= 2)")
            return None

        # Build DataFrame with dates as index, strategies as columns
        df = pd.DataFrame(self._data)

        # Drop rows where any strategy has NaN (only use overlapping dates)
        df_clean = df.dropna()

        if len(df_clean) < 2:
            logger.debug("Insufficient overlapping dates for correlation matrix")
            return None

        return df_clean.corr()

    def get_pairwise_correlation(self, strategy_a: str, strategy_b: str) -> float | None:
        """Get the correlation between two specific strategies.

        Args:
            strategy_a: First strategy ID.
            strategy_b: Second strategy ID.

        Returns:
            Pearson correlation coefficient between -1 and 1, or None
            if either strategy lacks data or there's insufficient overlap.
        """
        if strategy_a not in self._data or strategy_b not in self._data:
            return None

        # Find overlapping dates
        dates_a = set(self._data[strategy_a].keys())
        dates_b = set(self._data[strategy_b].keys())
        overlapping = dates_a & dates_b

        if len(overlapping) < 2:
            return None

        # Build aligned series
        series_a = pd.Series({d: self._data[strategy_a][d] for d in overlapping})
        series_b = pd.Series({d: self._data[strategy_b][d] for d in overlapping})

        return float(series_a.corr(series_b))

    def has_sufficient_data(self, min_days: int = 20) -> bool:
        """Check if there's enough data for meaningful correlation.

        Args:
            min_days: Minimum number of overlapping trading days required.

        Returns:
            True if at least 2 strategies have min_days overlapping data.
        """
        if len(self._data) < 2:
            return False

        # Find overlapping dates across all strategies
        all_dates: set[str] | None = None
        for strategy_dates in self._data.values():
            dates = set(strategy_dates.keys())
            if all_dates is None:
                all_dates = dates
            else:
                all_dates &= dates

        if all_dates is None:
            return False

        return len(all_dates) >= min_days

    def get_strategy_ids(self) -> list[str]:
        """Get list of all tracked strategy IDs.

        Returns:
            List of strategy IDs that have recorded P&L data.
        """
        return list(self._data.keys())

    def get_date_count(self, strategy_id: str) -> int:
        """Get the number of days with P&L data for a strategy.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            Number of days with recorded P&L, or 0 if strategy not found.
        """
        if strategy_id not in self._data:
            return 0
        return len(self._data[strategy_id])
