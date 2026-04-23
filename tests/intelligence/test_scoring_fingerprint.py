"""Tests for scoring-context fingerprint infrastructure (FIX-01 audit 2026-04-21).

Covers:
1. Stability — identical config produces identical fingerprint.
2. Sensitivity — a 0.01 weight delta produces a different fingerprint.
3. Round-trip persistence — shadow position's fingerprint survives write/read.
4. PromotionEvaluator filter — evaluate_all_variants with a fingerprint
   filter scopes to only matching shadow positions.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

from argus.core.fill_model import FillExitReason
from argus.core.ids import generate_id
from argus.intelligence.config import (
    QualityEngineConfig,
    QualityThresholdsConfig,
    QualityWeightsConfig,
)
from argus.intelligence.counterfactual import CounterfactualPosition, RejectionStage
from argus.intelligence.counterfactual_store import CounterfactualStore
from argus.intelligence.experiments import VariantDefinition
from argus.intelligence.experiments.promotion import PromotionEvaluator
from argus.intelligence.experiments.store import ExperimentStore
from argus.intelligence.scoring_fingerprint import compute_scoring_fingerprint

_ET = ZoneInfo("America/New_York")


def _make_position(
    position_id: str,
    *,
    strategy_id: str = "orb_breakout",
    opened_at: datetime | None = None,
    scoring_fingerprint: str | None = None,
    closed: bool = True,
    r_multiple: float = 1.5,
) -> CounterfactualPosition:
    """Build a CounterfactualPosition for persistence tests."""
    now = opened_at or datetime.now(_ET)
    return CounterfactualPosition(
        position_id=position_id,
        symbol="AAPL",
        strategy_id=strategy_id,
        entry_price=100.0,
        stop_price=95.0,
        target_price=110.0,
        time_stop_seconds=1800,
        rejection_stage=RejectionStage.QUALITY_FILTER,
        rejection_reason="Grade below minimum",
        quality_score=42.0,
        quality_grade="B-",
        regime_vector_snapshot={"volatility": "normal"},
        signal_metadata={"pattern_strength": 0.7},
        opened_at=now,
        closed_at=now + timedelta(minutes=15) if closed else None,
        exit_price=107.5 if closed else None,
        exit_reason=FillExitReason.TARGET_HIT if closed else None,
        theoretical_pnl=7.5 if closed else None,
        theoretical_r_multiple=r_multiple if closed else None,
        duration_seconds=900.0 if closed else None,
        max_adverse_excursion=2.0,
        max_favorable_excursion=8.0,
        bars_monitored=15 if closed else 0,
        scoring_fingerprint=scoring_fingerprint,
    )


# ---------------------------------------------------------------------------
# 1. Stability
# ---------------------------------------------------------------------------


def test_fingerprint_is_stable_for_identical_config() -> None:
    """Two calls with the same config object produce the same fingerprint."""
    config = QualityEngineConfig()

    fp1 = compute_scoring_fingerprint(config)
    fp2 = compute_scoring_fingerprint(config)

    assert fp1 == fp2
    assert len(fp1) == 16
    # Lowercase hex.
    assert all(c in "0123456789abcdef" for c in fp1)


# ---------------------------------------------------------------------------
# 2. Sensitivity
# ---------------------------------------------------------------------------


def test_fingerprint_changes_with_weight_delta() -> None:
    """A weight delta of 0.01 produces a different fingerprint."""
    baseline_weights = QualityWeightsConfig()
    baseline_config = QualityEngineConfig(weights=baseline_weights)

    # Bump pattern_strength by 0.01 (+), drop regime_alignment by 0.01 (-)
    # so that weights still sum to 1.0 and the validator is happy.
    shifted_weights = QualityWeightsConfig(
        pattern_strength=baseline_weights.pattern_strength + 0.01,
        catalyst_quality=baseline_weights.catalyst_quality,
        volume_profile=baseline_weights.volume_profile,
        historical_match=baseline_weights.historical_match,
        regime_alignment=baseline_weights.regime_alignment - 0.01,
    )
    shifted_config = QualityEngineConfig(weights=shifted_weights)

    fp_base = compute_scoring_fingerprint(baseline_config)
    fp_shifted = compute_scoring_fingerprint(shifted_config)

    assert fp_base != fp_shifted


# ---------------------------------------------------------------------------
# 3. Round-trip persistence through CounterfactualStore
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_fingerprint_round_trip_through_store(tmp_path: Path) -> None:
    """Write a shadow position with a known fingerprint and read it back."""
    db_path = str(tmp_path / "cf.db")
    store = CounterfactualStore(db_path=db_path)
    await store.initialize()

    try:
        config = QualityEngineConfig()
        fingerprint = compute_scoring_fingerprint(config)

        position = _make_position(
            position_id="pos_fingerprint_01",
            scoring_fingerprint=fingerprint,
        )
        await store.write_open(position)
        await store.write_close(position)

        rows = await store.query(scoring_fingerprint=fingerprint)
        assert len(rows) == 1
        assert rows[0]["scoring_fingerprint"] == fingerprint
        assert rows[0]["position_id"] == "pos_fingerprint_01"

        # Different fingerprint filter returns nothing.
        other_rows = await store.query(scoring_fingerprint="0" * 16)
        assert other_rows == []
    finally:
        await store.close()


# ---------------------------------------------------------------------------
# 4. PromotionEvaluator fingerprint filter
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_promotion_evaluator_filters_by_fingerprint(
    tmp_path: Path,
) -> None:
    """Seed two shadow positions with different fingerprints and verify the
    PromotionEvaluator's fingerprint filter scopes the query.

    Test strategy: use a CounterfactualStore stub that records the fingerprint
    filter it was called with. The evaluator does not need to complete a full
    promotion cycle — we only need to assert that the filter reaches the store.
    """
    # Two different fingerprints for two scoring contexts.
    baseline_config = QualityEngineConfig()
    shifted_weights = QualityWeightsConfig(
        pattern_strength=baseline_config.weights.pattern_strength + 0.01,
        catalyst_quality=baseline_config.weights.catalyst_quality,
        volume_profile=baseline_config.weights.volume_profile,
        historical_match=baseline_config.weights.historical_match,
        regime_alignment=baseline_config.weights.regime_alignment - 0.01,
    )
    shifted_config = QualityEngineConfig(weights=shifted_weights)

    fp_a = compute_scoring_fingerprint(baseline_config)
    fp_b = compute_scoring_fingerprint(shifted_config)
    assert fp_a != fp_b

    # Seed a real CounterfactualStore with one position under each fingerprint.
    db_path = str(tmp_path / "cf.db")
    cf_store = CounterfactualStore(db_path=db_path)
    await cf_store.initialize()

    try:
        variant_id = "strat_bull_flag_FP_TEST"
        for i in range(6):
            await cf_store.write_open(
                _make_position(
                    position_id=f"pos_a_{i}",
                    strategy_id=variant_id,
                    opened_at=datetime.now(_ET) - timedelta(days=i),
                    scoring_fingerprint=fp_a,
                    r_multiple=2.0,
                )
            )
            await cf_store.write_close(
                _make_position(
                    position_id=f"pos_a_{i}",
                    strategy_id=variant_id,
                    opened_at=datetime.now(_ET) - timedelta(days=i),
                    scoring_fingerprint=fp_a,
                    r_multiple=2.0,
                )
            )

        for i in range(6):
            await cf_store.write_open(
                _make_position(
                    position_id=f"pos_b_{i}",
                    strategy_id=variant_id,
                    opened_at=datetime.now(_ET) - timedelta(days=i),
                    scoring_fingerprint=fp_b,
                    r_multiple=-1.0,
                )
            )
            await cf_store.write_close(
                _make_position(
                    position_id=f"pos_b_{i}",
                    strategy_id=variant_id,
                    opened_at=datetime.now(_ET) - timedelta(days=i),
                    scoring_fingerprint=fp_b,
                    r_multiple=-1.0,
                )
            )

        # Direct store query sanity — each fingerprint scopes to its own set.
        rows_a = await cf_store.query(
            strategy_id=variant_id, scoring_fingerprint=fp_a, limit=100
        )
        rows_b = await cf_store.query(
            strategy_id=variant_id, scoring_fingerprint=fp_b, limit=100
        )
        assert len(rows_a) == 6
        assert len(rows_b) == 6
        assert all(r["scoring_fingerprint"] == fp_a for r in rows_a)
        assert all(r["scoring_fingerprint"] == fp_b for r in rows_b)

        # Evaluator-side assertion: shadow-derived MultiObjectiveResults
        # differ under each fingerprint (expectancy sign flips). FIX-08
        # P1-D2-L02 collapsed _build_result_from_shadow into a fetch +
        # pure-aggregation pair; the underlying behaviour is preserved.
        exp_store = MagicMock(spec=ExperimentStore)
        trade_logger = MagicMock()
        trade_logger.query_trades = AsyncMock(return_value=[])

        evaluator = PromotionEvaluator(
            store=exp_store,
            counterfactual_store=cf_store,
            trade_logger=trade_logger,
            config={"promotion_min_shadow_trades": 1},
        )

        positions_a = await evaluator._fetch_shadow_positions(
            variant_id, scoring_fingerprint=fp_a
        )
        positions_b = await evaluator._fetch_shadow_positions(
            variant_id, scoring_fingerprint=fp_b
        )
        positions_all = await evaluator._fetch_shadow_positions(variant_id)
        result_a = evaluator._build_result_from_positions(variant_id, positions_a)
        result_b = evaluator._build_result_from_positions(variant_id, positions_b)
        result_all = evaluator._build_result_from_positions(variant_id, positions_all)

        assert result_a is not None
        assert result_b is not None
        assert result_all is not None
        assert result_a.total_trades == 6
        assert result_b.total_trades == 6
        assert result_all.total_trades == 12
        # Expectancy sign reflects per-context r_multiples.
        assert result_a.expectancy_per_trade > 0
        assert result_b.expectancy_per_trade < 0
    finally:
        await cf_store.close()
