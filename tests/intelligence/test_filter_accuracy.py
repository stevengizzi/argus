"""Tests for FilterAccuracy computation module.

Verifies correct/incorrect rejection classification, grouping by
stage/reason/grade/strategy/regime, min sample threshold, empty data,
and date range filtering.

Sprint 27.7, Session 4.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from argus.intelligence.counterfactual_store import CounterfactualStore
from argus.intelligence.filter_accuracy import (
    FilterAccuracyBreakdown,
    FilterAccuracyReport,
    compute_filter_accuracy,
)


async def _seed_position(
    store: CounterfactualStore,
    position_id: str,
    *,
    rejection_stage: str = "quality_filter",
    rejection_reason: str = "grade too low",
    strategy_id: str = "orb_breakout",
    quality_grade: str | None = "B",
    theoretical_pnl: float = -2.0,
    regime_snapshot: dict[str, object] | None = None,
    opened_at: str | None = None,
    closed_at: str | None = None,
) -> None:
    """Insert a closed counterfactual position directly into the store."""
    if opened_at is None or closed_at is None:
        # DEF-205: seed within compute_filter_accuracy's rolling 30-day window.
        anchor = (datetime.now() - timedelta(days=5)).replace(microsecond=0)
        if opened_at is None:
            opened_at = anchor.isoformat()
        if closed_at is None:
            closed_at = (anchor + timedelta(minutes=30)).isoformat()
    assert store._conn is not None
    await store._conn.execute(
        """INSERT INTO counterfactual_positions (
            position_id, symbol, strategy_id, entry_price, stop_price,
            target_price, time_stop_seconds, rejection_stage, rejection_reason,
            quality_score, quality_grade, regime_vector_snapshot, signal_metadata,
            opened_at, closed_at, exit_price, exit_reason,
            theoretical_pnl, theoretical_r_multiple, duration_seconds,
            max_adverse_excursion, max_favorable_excursion, bars_monitored
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            position_id, "AAPL", strategy_id, 100.0, 95.0,
            110.0, None, rejection_stage, rejection_reason,
            72.5, quality_grade,
            json.dumps(regime_snapshot) if regime_snapshot else None,
            "{}",
            opened_at, closed_at, 98.0 if theoretical_pnl < 0 else 105.0,
            "stopped_out" if theoretical_pnl < 0 else "target_hit",
            theoretical_pnl, theoretical_pnl / 5.0, 1800.0,
            2.0, 3.0, 10,
        ),
    )
    await store._conn.commit()


@pytest.fixture
async def store(tmp_path: Path) -> CounterfactualStore:
    """Provide an initialized CounterfactualStore with a temp database."""
    s = CounterfactualStore(str(tmp_path / "cf_test.db"))
    await s.initialize()
    yield s  # type: ignore[misc]
    await s.close()


class TestCorrectRejection:
    """Tests for correct rejection classification (stop hit = P&L <= 0)."""

    @pytest.mark.asyncio
    async def test_stop_hit_counted_as_correct(self, store: CounterfactualStore) -> None:
        """Negative P&L means the filter was correct to reject."""
        await _seed_position(store, "pos_1", theoretical_pnl=-3.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 1
        assert report.by_stage[0].correct_rejections == 1
        assert report.by_stage[0].incorrect_rejections == 0
        assert report.by_stage[0].accuracy == 1.0

    @pytest.mark.asyncio
    async def test_zero_pnl_counted_as_correct(self, store: CounterfactualStore) -> None:
        """Zero P&L means the filter was correct (no profit missed)."""
        await _seed_position(store, "pos_1", theoretical_pnl=0.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.by_stage[0].correct_rejections == 1


class TestIncorrectRejection:
    """Tests for incorrect rejection classification (target hit = P&L > 0)."""

    @pytest.mark.asyncio
    async def test_target_hit_counted_as_incorrect(self, store: CounterfactualStore) -> None:
        """Positive P&L means the filter missed a profitable trade."""
        await _seed_position(store, "pos_1", theoretical_pnl=5.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.by_stage[0].correct_rejections == 0
        assert report.by_stage[0].incorrect_rejections == 1
        assert report.by_stage[0].accuracy == 0.0


class TestByStage:
    """Tests for accuracy grouping by rejection stage."""

    @pytest.mark.asyncio
    async def test_multiple_stages_separate_accuracy(
        self, store: CounterfactualStore
    ) -> None:
        """3 stages with known outcomes produce correct per-stage accuracy."""
        # Quality filter: target hit = incorrect (accuracy 0%)
        await _seed_position(
            store, "pos_qf", rejection_stage="quality_filter",
            theoretical_pnl=5.0,
        )
        # Position sizer: stop hit = correct (accuracy 100%)
        await _seed_position(
            store, "pos_ps", rejection_stage="position_sizer",
            theoretical_pnl=-3.0,
        )
        # Risk manager: stop hit = correct (accuracy 100%)
        await _seed_position(
            store, "pos_rm", rejection_stage="risk_manager",
            theoretical_pnl=-2.0,
        )

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.total_positions == 3

        stage_map = {b.category: b for b in report.by_stage}
        assert stage_map["quality_filter"].accuracy == 0.0
        assert stage_map["position_sizer"].accuracy == 1.0
        assert stage_map["risk_manager"].accuracy == 1.0


class TestByGrade:
    """Tests for accuracy grouping by quality grade."""

    @pytest.mark.asyncio
    async def test_different_grades_separate_breakdown(
        self, store: CounterfactualStore
    ) -> None:
        """Rejections at different grades produce separate breakdowns."""
        await _seed_position(store, "pos_b", quality_grade="B", theoretical_pnl=-1.0)
        await _seed_position(store, "pos_c", quality_grade="C", theoretical_pnl=3.0)
        await _seed_position(store, "pos_none", quality_grade=None, theoretical_pnl=-2.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        grade_map = {b.category: b for b in report.by_grade}

        assert "B" in grade_map
        assert grade_map["B"].accuracy == 1.0
        assert "C" in grade_map
        assert grade_map["C"].accuracy == 0.0
        assert "unknown" in grade_map
        assert grade_map["unknown"].accuracy == 1.0


class TestByStrategy:
    """Tests for accuracy grouping by strategy_id."""

    @pytest.mark.asyncio
    async def test_different_strategies_separate_breakdown(
        self, store: CounterfactualStore
    ) -> None:
        """Rejections from different strategies are grouped separately."""
        await _seed_position(
            store, "pos_orb", strategy_id="orb_breakout", theoretical_pnl=-2.0,
        )
        await _seed_position(
            store, "pos_vwap", strategy_id="vwap_reclaim", theoretical_pnl=4.0,
        )

        report = await compute_filter_accuracy(store, min_sample_count=1)
        strat_map = {b.category: b for b in report.by_strategy}

        assert strat_map["orb_breakout"].accuracy == 1.0
        assert strat_map["vwap_reclaim"].accuracy == 0.0


class TestByRegime:
    """Tests for accuracy grouping by primary_regime."""

    @pytest.mark.asyncio
    async def test_regime_extracted_from_snapshot(
        self, store: CounterfactualStore
    ) -> None:
        """Primary regime is extracted from the JSON regime_vector_snapshot."""
        await _seed_position(
            store, "pos_bull",
            regime_snapshot={"primary_regime": "bullish_trending"},
            theoretical_pnl=-1.0,
        )
        await _seed_position(
            store, "pos_bear",
            regime_snapshot={"primary_regime": "bearish_trending"},
            theoretical_pnl=3.0,
        )

        report = await compute_filter_accuracy(store, min_sample_count=1)
        regime_map = {b.category: b for b in report.by_regime}

        assert "bullish_trending" in regime_map
        assert "bearish_trending" in regime_map

    @pytest.mark.asyncio
    async def test_missing_regime_grouped_as_unknown(
        self, store: CounterfactualStore
    ) -> None:
        """Positions without regime snapshot are grouped as 'unknown'."""
        await _seed_position(store, "pos_1", regime_snapshot=None, theoretical_pnl=-1.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        assert report.by_regime[0].category == "unknown"


class TestMinSampleThreshold:
    """Tests for the min_sample_count threshold."""

    @pytest.mark.asyncio
    async def test_below_threshold_flagged_insufficient(
        self, store: CounterfactualStore
    ) -> None:
        """Fewer than min_sample_count → sample_sufficient=False."""
        await _seed_position(store, "pos_1", theoretical_pnl=-1.0)

        report = await compute_filter_accuracy(store, min_sample_count=10)
        assert report.by_stage[0].sample_sufficient is False
        assert report.by_stage[0].total_rejections == 1

    @pytest.mark.asyncio
    async def test_at_threshold_flagged_sufficient(
        self, store: CounterfactualStore
    ) -> None:
        """Exactly min_sample_count → sample_sufficient=True."""
        for i in range(10):
            await _seed_position(store, f"pos_{i}", theoretical_pnl=-1.0)

        report = await compute_filter_accuracy(store, min_sample_count=10)
        assert report.by_stage[0].sample_sufficient is True


class TestEmptyData:
    """Tests for zero-position edge case."""

    @pytest.mark.asyncio
    async def test_empty_store_returns_empty_report(
        self, store: CounterfactualStore
    ) -> None:
        """No positions → empty report with total=0."""
        report = await compute_filter_accuracy(store, min_sample_count=10)
        assert report.total_positions == 0
        assert report.by_stage == []
        assert report.by_reason == []
        assert report.by_grade == []
        assert report.by_strategy == []
        assert report.by_regime == []


class TestDateRangeFiltering:
    """Tests for date range filtering."""

    @pytest.mark.asyncio
    async def test_only_positions_in_range_included(
        self, store: CounterfactualStore
    ) -> None:
        """Positions outside the date range are excluded."""
        await _seed_position(
            store, "pos_old",
            opened_at="2026-03-01T10:00:00",
            closed_at="2026-03-01T10:30:00",
            theoretical_pnl=-1.0,
        )
        await _seed_position(
            store, "pos_new",
            opened_at="2026-03-25T10:00:00",
            closed_at="2026-03-25T10:30:00",
            theoretical_pnl=2.0,
        )

        start = datetime(2026, 3, 20)
        end = datetime(2026, 3, 26)
        report = await compute_filter_accuracy(
            store, start_date=start, end_date=end, min_sample_count=1,
        )
        assert report.total_positions == 1
        assert report.by_stage[0].incorrect_rejections == 1


class TestAvgPnl:
    """Tests for average theoretical P&L computation."""

    @pytest.mark.asyncio
    async def test_avg_pnl_computed_correctly(
        self, store: CounterfactualStore
    ) -> None:
        """Average P&L across multiple positions is computed correctly."""
        await _seed_position(store, "pos_1", theoretical_pnl=-4.0)
        await _seed_position(store, "pos_2", theoretical_pnl=6.0)

        report = await compute_filter_accuracy(store, min_sample_count=1)
        # (-4 + 6) / 2 = 1.0
        assert report.by_stage[0].avg_theoretical_pnl == pytest.approx(1.0)
