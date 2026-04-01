"""Tests for PromotionEvaluator — Sprint 32 Session 7."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.ids import generate_id
from argus.intelligence.experiments import (
    ExperimentRecord,
    ExperimentStatus,
    PromotionEvent,
    VariantDefinition,
)
from argus.intelligence.experiments.promotion import PromotionEvaluator
from argus.intelligence.experiments.store import ExperimentStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CONFIG = {
    "enabled": True,
    "auto_promote": True,
    "promotion_min_shadow_trades": 30,
    "promotion_min_shadow_days": 5,
}


def _make_variant(
    mode: str = "shadow",
    base_pattern: str = "bull_flag",
    variant_id: str | None = None,
) -> VariantDefinition:
    return VariantDefinition(
        variant_id=variant_id or f"strat_{base_pattern}_{generate_id()}",
        base_pattern=base_pattern,
        parameter_fingerprint="fp_abc123",
        parameters={"min_pole_candles": 3},
        mode=mode,
        source="manual",
        created_at=datetime.now(UTC),
    )


def _make_experiment(
    pattern_name: str = "bull_flag",
    is_baseline: bool = True,
    backtest_result: dict[str, Any] | None = None,
) -> ExperimentRecord:
    now = datetime.now(UTC)
    return ExperimentRecord(
        experiment_id=generate_id(),
        pattern_name=pattern_name,
        parameter_fingerprint="fp_base",
        parameters={"min_pole_candles": 3},
        status=ExperimentStatus.ACTIVE_LIVE,
        backtest_result=backtest_result,
        shadow_trades=0,
        shadow_expectancy=None,
        is_baseline=is_baseline,
        created_at=now,
        updated_at=now,
    )


def _strong_mor_dict() -> dict[str, Any]:
    """Returns a serialised MultiObjectiveResult dict with strong metrics."""
    from argus.analytics.evaluation import ConfidenceTier, MultiObjectiveResult
    from datetime import date

    result = MultiObjectiveResult(
        strategy_id="baseline",
        parameter_hash="base_hash",
        evaluation_date=datetime.now(UTC),
        data_range=(date.today(), date.today()),
        sharpe_ratio=3.0,
        max_drawdown_pct=-0.05,
        profit_factor=3.0,
        win_rate=0.65,
        total_trades=60,
        expectancy_per_trade=0.4,
        confidence_tier=ConfidenceTier.HIGH,
    )
    return result.to_dict()


def _weak_mor_dict() -> dict[str, Any]:
    """Returns a serialised MultiObjectiveResult dict with weak metrics."""
    from argus.analytics.evaluation import ConfidenceTier, MultiObjectiveResult
    from datetime import date

    result = MultiObjectiveResult(
        strategy_id="weak_live",
        parameter_hash="weak_hash",
        evaluation_date=datetime.now(UTC),
        data_range=(date.today(), date.today()),
        sharpe_ratio=0.5,
        max_drawdown_pct=-0.20,
        profit_factor=1.1,
        win_rate=0.45,
        total_trades=40,
        expectancy_per_trade=0.05,
        confidence_tier=ConfidenceTier.MODERATE,
    )
    return result.to_dict()


def _make_shadow_positions(
    count: int,
    strategy_id: str,
    days_spread: int = 6,
    r_multiple: float = 0.5,
) -> list[dict[str, Any]]:
    """Create fake closed counterfactual positions spread over days_spread days."""
    positions = []
    for i in range(count):
        day_offset = i % days_spread
        opened_at = (
            datetime.now(UTC) - timedelta(days=day_offset)
        ).strftime("%Y-%m-%dT10:00:00")
        positions.append(
            {
                "position_id": generate_id(),
                "strategy_id": strategy_id,
                "theoretical_r_multiple": r_multiple,
                "theoretical_pnl": r_multiple * 100,
                "opened_at": opened_at,
                "closed_at": opened_at,
            }
        )
    return positions


def _make_live_trades(
    count: int,
    strategy_id: str,
    r_multiple: float = 0.05,
) -> list[dict[str, Any]]:
    """Create fake live trade dicts with strategy_id and r_multiple."""
    return [
        {"strategy_id": strategy_id, "r_multiple": r_multiple}
        for _ in range(count)
    ]


def _make_store_with_variants(
    shadow_variants: list[VariantDefinition],
    live_variants: list[VariantDefinition],
    baseline: ExperimentRecord | None = None,
    promotion_events: list[PromotionEvent] | None = None,
) -> MagicMock:
    """Build a mock ExperimentStore populated with the given state."""
    store = MagicMock(spec=ExperimentStore)
    all_variants = shadow_variants + live_variants
    store.list_variants = AsyncMock(return_value=all_variants)
    store.get_baseline = AsyncMock(return_value=baseline)
    store.save_promotion_event = AsyncMock()
    store.update_variant_mode = AsyncMock()
    store.list_promotion_events = AsyncMock(return_value=promotion_events or [])
    return store


def _make_cf_store(positions: list[dict[str, Any]]) -> MagicMock:
    cf = MagicMock()
    cf.query = AsyncMock(return_value=positions)
    return cf


def _make_trade_logger(trades: list[dict[str, Any]]) -> MagicMock:
    tl = MagicMock()
    tl.query_trades = AsyncMock(return_value=trades)
    return tl


# ---------------------------------------------------------------------------
# Tests: promotion path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shadow_variant_dominates_live_returns_promote_event() -> None:
    """Shadow variant with 30+ trades that dominates a live variant → promote."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    store = _make_store_with_variants([shadow], [live])
    shadow_positions = _make_shadow_positions(
        count=35, strategy_id=shadow.variant_id, r_multiple=0.6
    )
    live_trades = _make_live_trades(
        count=40, strategy_id=live.variant_id, r_multiple=0.04
    )
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    assert len(events) >= 1
    promote_events = [e for e in events if e.action == "promote"]
    assert len(promote_events) == 1
    event = promote_events[0]
    assert event.variant_id == shadow.variant_id
    assert event.previous_mode == "shadow"
    assert event.new_mode == "live"
    assert event.shadow_trades == 35


@pytest.mark.asyncio
async def test_shadow_variant_below_min_trades_returns_none() -> None:
    """Shadow variant with fewer than min_shadow_trades → no promotion."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    store = _make_store_with_variants([shadow], [live])
    # Only 20 shadow trades — below threshold of 30
    shadow_positions = _make_shadow_positions(
        count=20, strategy_id=shadow.variant_id, r_multiple=1.0
    )
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=0.04)
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    promote_events = [e for e in events if e.action == "promote"]
    assert len(promote_events) == 0


@pytest.mark.asyncio
async def test_shadow_variant_no_dominance_returns_none() -> None:
    """Shadow variant that does not Pareto-dominate any live variant → no event."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    store = _make_store_with_variants([shadow], [live])
    # Both have similar metrics — shadow won't dominate
    shadow_positions = _make_shadow_positions(
        count=35, strategy_id=shadow.variant_id, r_multiple=0.3
    )
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=0.3)
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    promote_events = [e for e in events if e.action == "promote"]
    assert len(promote_events) == 0


@pytest.mark.asyncio
async def test_promote_already_live_variant_is_noop() -> None:
    """Promoting a variant that is already live is a no-op."""
    already_live = _make_variant(mode="live")

    store = _make_store_with_variants([], [already_live])
    shadow_positions = _make_shadow_positions(
        count=35, strategy_id=already_live.variant_id, r_multiple=0.9
    )
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger([])

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    promote_events = [e for e in events if e.action == "promote"]
    assert len(promote_events) == 0


# ---------------------------------------------------------------------------
# Tests: demotion path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_live_variant_dominated_by_baseline_returns_demote_event() -> None:
    """Live variant dominated by baseline backtest → PromotionEvent(action='demote')."""
    live = _make_variant(mode="live")
    baseline_exp = _make_experiment(is_baseline=True, backtest_result=_strong_mor_dict())

    # Promote happened more than min_shadow_days ago
    old_promote = PromotionEvent(
        event_id=generate_id(),
        variant_id=live.variant_id,
        action="promote",
        previous_mode="shadow",
        new_mode="live",
        reason="old promotion",
        comparison_verdict=None,
        shadow_trades=30,
        shadow_expectancy=0.4,
        timestamp=datetime.now(UTC) - timedelta(days=10),
    )

    store = _make_store_with_variants([], [live], baseline=baseline_exp,
                                      promotion_events=[old_promote])
    # Live trades with very poor metrics so baseline dominates
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=-0.1)
    cf_store = _make_cf_store([])
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    demote_events = [e for e in events if e.action == "demote"]
    assert len(demote_events) == 1
    event = demote_events[0]
    assert event.variant_id == live.variant_id
    assert event.previous_mode == "live"
    assert event.new_mode == "shadow"


@pytest.mark.asyncio
async def test_hysteresis_prevents_immediate_demotion() -> None:
    """Recently promoted variant is not immediately demoted."""
    live = _make_variant(mode="live")
    baseline_exp = _make_experiment(is_baseline=True, backtest_result=_strong_mor_dict())

    # Recent promotion — within min_shadow_days window
    recent_promote = PromotionEvent(
        event_id=generate_id(),
        variant_id=live.variant_id,
        action="promote",
        previous_mode="shadow",
        new_mode="live",
        reason="recent promotion",
        comparison_verdict=None,
        shadow_trades=30,
        shadow_expectancy=0.4,
        timestamp=datetime.now(UTC) - timedelta(days=2),  # only 2 days ago
    )

    store = _make_store_with_variants([], [live], baseline=baseline_exp,
                                      promotion_events=[recent_promote])
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=-0.1)
    cf_store = _make_cf_store([])
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    demote_events = [e for e in events if e.action == "demote"]
    assert len(demote_events) == 0, "Hysteresis should block demotion within min_shadow_days"


@pytest.mark.asyncio
async def test_promotion_event_persisted_before_mode_change() -> None:
    """PromotionEvent is saved to store before update_variant_mode is called."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    call_order: list[str] = []

    store = _make_store_with_variants([shadow], [live])

    async def record_save(event: PromotionEvent) -> None:
        call_order.append("save_event")

    async def record_update(variant_id: str, mode: str) -> None:
        call_order.append("update_mode")

    store.save_promotion_event = record_save  # type: ignore[assignment]
    store.update_variant_mode = record_update  # type: ignore[assignment]

    shadow_positions = _make_shadow_positions(
        count=35, strategy_id=shadow.variant_id, r_multiple=0.6
    )
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=0.04)
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    assert any(e.action == "promote" for e in events)
    assert call_order.index("save_event") < call_order.index("update_mode"), (
        "PromotionEvent must be persisted before mode is updated"
    )


@pytest.mark.asyncio
async def test_none_counterfactual_store_returns_no_events() -> None:
    """When counterfactual_store is None (subsystem disabled), no promotion occurs."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    store = _make_store_with_variants([shadow], [live])
    trade_logger = _make_trade_logger([])

    evaluator = PromotionEvaluator(store, None, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    assert len(events) == 0, "No events expected when counterfactual store is None"


@pytest.mark.asyncio
async def test_mode_update_changes_variant_to_live() -> None:
    """After promotion, update_variant_mode called with 'live' for shadow variant."""
    shadow = _make_variant(mode="shadow")
    live = _make_variant(mode="live")

    store = _make_store_with_variants([shadow], [live])
    shadow_positions = _make_shadow_positions(
        count=35, strategy_id=shadow.variant_id, r_multiple=0.6
    )
    live_trades = _make_live_trades(count=40, strategy_id=live.variant_id, r_multiple=0.04)
    cf_store = _make_cf_store(shadow_positions)
    trade_logger = _make_trade_logger(live_trades)

    evaluator = PromotionEvaluator(store, cf_store, trade_logger, _CONFIG)
    events = await evaluator.evaluate_all_variants()

    promote_events = [e for e in events if e.action == "promote"]
    assert len(promote_events) == 1
    store.update_variant_mode.assert_called_once_with(shadow.variant_id, "live")
