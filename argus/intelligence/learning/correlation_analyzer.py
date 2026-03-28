"""Correlation Analyzer for the Learning Loop.

Computes pairwise Pearson correlations between strategy daily P&L series
to identify highly correlated strategy pairs. Uses trade-sourced records
preferentially per Amendment 3 (counterfactual positions lack real
execution timing).

Sprint 28, Session 2b.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import date
from zoneinfo import ZoneInfo

import numpy as np

from argus.intelligence.learning.models import (
    CorrelationResult,
    LearningLoopConfig,
    OutcomeRecord,
)

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class CorrelationAnalyzer:
    """Analyzes pairwise daily P&L correlations between strategies.

    Groups outcome records by strategy and ET date, computes daily P&L,
    then calculates Pearson correlation for each strategy pair. Pairs
    exceeding the configured threshold are flagged.
    """

    def analyze(
        self,
        records: list[OutcomeRecord],
        config: LearningLoopConfig,
    ) -> CorrelationResult:
        """Compute cross-strategy daily P&L correlation matrix.

        Args:
            records: Outcome records from OutcomeCollector.
            config: Learning loop configuration (correlation_window_days,
                correlation_threshold).

        Returns:
            CorrelationResult with matrix, flagged pairs, and exclusions.
        """
        trade_records = [r for r in records if r.source == "trade"]
        combined_records = records

        # Amendment 3: prefer trade-sourced records for correlation
        working_records, used_fallback = self._select_source(
            trade_records, combined_records
        )

        # Group daily P&L per strategy over the correlation window
        daily_pnl = self._aggregate_daily_pnl(
            working_records, config.correlation_window_days
        )

        # Identify all strategies and exclude those with zero trades
        all_strategies = sorted({r.strategy_id for r in records})
        active_strategies = sorted(daily_pnl.keys())
        excluded_strategies = [
            s for s in all_strategies if s not in daily_pnl
        ]

        if len(active_strategies) < 2:
            logger.info(
                "Fewer than 2 strategies with data (%d) — "
                "skipping correlation analysis",
                len(active_strategies),
            )
            return CorrelationResult(
                strategy_pairs=[],
                correlation_matrix={},
                flagged_pairs=[],
                excluded_strategies=excluded_strategies,
                window_days=config.correlation_window_days,
            )

        # Build aligned daily P&L arrays for each strategy pair
        strategy_pairs: list[tuple[str, str]] = []
        correlation_matrix: dict[tuple[str, str], float] = {}
        flagged_pairs: list[tuple[str, str]] = []

        for i, strat_a in enumerate(active_strategies):
            for strat_b in active_strategies[i + 1:]:
                pair = (strat_a, strat_b)
                strategy_pairs.append(pair)

                corr = self._compute_pearson(
                    daily_pnl[strat_a], daily_pnl[strat_b]
                )
                correlation_matrix[pair] = corr

                if abs(corr) >= config.correlation_threshold:
                    flagged_pairs.append(pair)

        if used_fallback:
            logger.info(
                "Correlation computed from combined sources "
                "(trade data insufficient) — MODERATE confidence"
            )

        return CorrelationResult(
            strategy_pairs=strategy_pairs,
            correlation_matrix=correlation_matrix,
            flagged_pairs=flagged_pairs,
            excluded_strategies=excluded_strategies,
            window_days=config.correlation_window_days,
        )

    # --- Internal helpers ---

    @staticmethod
    def _select_source(
        trade_records: list[OutcomeRecord],
        combined_records: list[OutcomeRecord],
    ) -> tuple[list[OutcomeRecord], bool]:
        """Select trade-sourced records if sufficient, else fall back.

        Amendment 3: counterfactual positions don't have real execution
        timing, so trade data is preferred. Fall back to combined if
        fewer than 2 strategies have trade data.

        Args:
            trade_records: Records with source="trade".
            combined_records: All records (trade + counterfactual).

        Returns:
            Tuple of (selected records, used_fallback flag).
        """
        trade_strategies = {r.strategy_id for r in trade_records}
        if len(trade_strategies) >= 2:
            return trade_records, False
        return combined_records, True

    @staticmethod
    def _aggregate_daily_pnl(
        records: list[OutcomeRecord],
        window_days: int,
    ) -> dict[str, dict[date, float]]:
        """Group records by strategy and ET date, summing daily P&L.

        Args:
            records: Outcome records to aggregate.
            window_days: Maximum number of recent trading days to include.

        Returns:
            Dict of strategy_id → {date → total_pnl}.
        """
        raw: dict[str, dict[date, float]] = defaultdict(
            lambda: defaultdict(float)
        )

        for record in records:
            et_date = record.timestamp.astimezone(_ET).date()
            raw[record.strategy_id][et_date] += record.pnl

        if not raw:
            return {}

        # Trim to most recent window_days trading days
        all_dates = sorted({d for pnl_by_date in raw.values() for d in pnl_by_date})
        if len(all_dates) > window_days:
            cutoff_dates = set(all_dates[-window_days:])
            for strategy_id in list(raw.keys()):
                raw[strategy_id] = {
                    d: v for d, v in raw[strategy_id].items()
                    if d in cutoff_dates
                }

        # Remove strategies with no remaining data
        return {
            sid: dict(pnl_by_date)
            for sid, pnl_by_date in raw.items()
            if pnl_by_date
        }

    @staticmethod
    def _compute_pearson(
        pnl_a: dict[date, float],
        pnl_b: dict[date, float],
    ) -> float:
        """Compute Pearson correlation between two daily P&L series.

        Aligns on common trading days. Missing days for a strategy are
        treated as zero P&L. Returns 0.0 if insufficient overlapping
        data or zero variance.

        Args:
            pnl_a: Daily P&L for strategy A.
            pnl_b: Daily P&L for strategy B.

        Returns:
            Pearson correlation coefficient, or 0.0 if not computable.
        """
        all_dates = sorted(set(pnl_a.keys()) | set(pnl_b.keys()))
        if len(all_dates) < 2:
            return 0.0

        arr_a = np.array([pnl_a.get(d, 0.0) for d in all_dates])
        arr_b = np.array([pnl_b.get(d, 0.0) for d in all_dates])

        # Handle zero-variance case (constant P&L series)
        if np.std(arr_a) == 0.0 or np.std(arr_b) == 0.0:
            return 0.0

        corrcoef = np.corrcoef(arr_a, arr_b)
        return float(corrcoef[0, 1])
