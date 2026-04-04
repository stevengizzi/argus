"""Tests for ExperimentStore — Sprint 32 Session 4."""

from __future__ import annotations

import os
from datetime import UTC, date, datetime, timedelta

import aiosqlite
import pytest

from argus.core.ids import generate_id
from argus.intelligence.experiments import (
    ExperimentRecord,
    ExperimentStatus,
    ExperimentStore,
    PromotionEvent,
    VariantDefinition,
)


def _make_experiment(
    pattern_name: str = "bull_flag",
    is_baseline: bool = False,
    status: ExperimentStatus = ExperimentStatus.PENDING,
    created_at: datetime | None = None,
) -> ExperimentRecord:
    now = created_at or datetime.now(UTC)
    return ExperimentRecord(
        experiment_id=generate_id(),
        pattern_name=pattern_name,
        parameter_fingerprint="fp_abc123",
        parameters={"min_pole_candles": 3, "flag_depth_pct": 0.05},
        status=status,
        backtest_result=None,
        shadow_trades=0,
        shadow_expectancy=None,
        is_baseline=is_baseline,
        created_at=now,
        updated_at=now,
    )


def _make_variant(
    base_pattern: str = "bull_flag",
    mode: str = "shadow",
    created_at: datetime | None = None,
) -> VariantDefinition:
    now = created_at or datetime.now(UTC)
    return VariantDefinition(
        variant_id=f"strat_{base_pattern}_{generate_id()}",
        base_pattern=base_pattern,
        parameter_fingerprint="fp_def456",
        parameters={"min_pole_candles": 4},
        mode=mode,
        source="manual",
        created_at=now,
    )


def _make_promotion_event(
    variant_id: str = "v1",
    action: str = "promote",
    timestamp: datetime | None = None,
) -> PromotionEvent:
    ts = timestamp or datetime.now(UTC)
    return PromotionEvent(
        event_id=generate_id(),
        variant_id=variant_id,
        action=action,
        previous_mode="shadow",
        new_mode="live",
        reason="Sharpe improved above threshold",
        comparison_verdict=None,
        shadow_trades=50,
        shadow_expectancy=0.42,
        timestamp=ts,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def store(tmp_path: object) -> ExperimentStore:
    db_path = str(tmp_path) + "/test_experiments.db"  # type: ignore[operator]
    s = ExperimentStore(db_path=db_path)
    await s.initialize()
    return s


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_experiment_status_enum_values() -> None:
    """ExperimentStatus must expose all 8 expected values."""
    expected = {
        "PENDING", "RUNNING", "COMPLETED", "FAILED",
        "PROMOTED", "DEMOTED", "ACTIVE_SHADOW", "ACTIVE_LIVE",
    }
    actual = {s.value for s in ExperimentStatus}
    assert actual == expected


@pytest.mark.asyncio
async def test_save_and_retrieve_experiment(store: ExperimentStore) -> None:
    """save_experiment + get_experiment round-trip preserves all fields."""
    exp = _make_experiment(pattern_name="flat_top")
    exp.shadow_trades = 12
    exp.shadow_expectancy = 0.35
    exp.backtest_result = {"sharpe_ratio": 1.8, "max_drawdown_pct": -0.07}

    await store.save_experiment(exp)

    retrieved = await store.get_experiment(exp.experiment_id)
    assert retrieved is not None
    assert retrieved.experiment_id == exp.experiment_id
    assert retrieved.pattern_name == "flat_top"
    assert retrieved.shadow_trades == 12
    assert retrieved.shadow_expectancy == pytest.approx(0.35)
    assert retrieved.backtest_result == exp.backtest_result
    assert retrieved.status == ExperimentStatus.PENDING
    assert retrieved.is_baseline is False


@pytest.mark.asyncio
async def test_list_experiments_by_pattern_name(store: ExperimentStore) -> None:
    """list_experiments filters correctly by pattern_name."""
    exp_bf1 = _make_experiment(pattern_name="bull_flag")
    exp_bf2 = _make_experiment(pattern_name="bull_flag")
    exp_ft = _make_experiment(pattern_name="flat_top")

    for exp in (exp_bf1, exp_bf2, exp_ft):
        await store.save_experiment(exp)

    bull_flag_results = await store.list_experiments(pattern_name="bull_flag")
    all_results = await store.list_experiments()

    assert len(bull_flag_results) == 2
    assert all(r.pattern_name == "bull_flag" for r in bull_flag_results)
    assert len(all_results) == 3


@pytest.mark.asyncio
async def test_get_baseline_returns_none_when_absent(store: ExperimentStore) -> None:
    """get_baseline returns None when no baseline has been set."""
    exp = _make_experiment(pattern_name="hod_break")
    await store.save_experiment(exp)

    baseline = await store.get_baseline("hod_break")
    assert baseline is None


@pytest.mark.asyncio
async def test_set_baseline_marks_and_unmarks(store: ExperimentStore) -> None:
    """set_baseline unmarks the previous baseline before marking the new one."""
    exp_a = _make_experiment(pattern_name="bull_flag")
    exp_b = _make_experiment(pattern_name="bull_flag")
    await store.save_experiment(exp_a)
    await store.save_experiment(exp_b)

    await store.set_baseline(exp_a.experiment_id)
    baseline_a = await store.get_baseline("bull_flag")
    assert baseline_a is not None
    assert baseline_a.experiment_id == exp_a.experiment_id

    # Promote exp_b — exp_a must be unmarked
    await store.set_baseline(exp_b.experiment_id)
    baseline_b = await store.get_baseline("bull_flag")
    assert baseline_b is not None
    assert baseline_b.experiment_id == exp_b.experiment_id

    # Confirm only one baseline exists
    all_exps = await store.list_experiments(pattern_name="bull_flag")
    baselines = [e for e in all_exps if e.is_baseline]
    assert len(baselines) == 1


@pytest.mark.asyncio
async def test_save_and_retrieve_variant(store: ExperimentStore) -> None:
    """save_variant + get_variant round-trip preserves all fields."""
    variant = _make_variant(base_pattern="gap_and_go", mode="live")

    await store.save_variant(variant)

    retrieved = await store.get_variant(variant.variant_id)
    assert retrieved is not None
    assert retrieved.variant_id == variant.variant_id
    assert retrieved.base_pattern == "gap_and_go"
    assert retrieved.mode == "live"
    assert retrieved.source == "manual"
    assert retrieved.parameters == variant.parameters


@pytest.mark.asyncio
async def test_list_variants_and_update_mode(store: ExperimentStore) -> None:
    """list_variants filters by pattern; update_variant_mode persists the change."""
    v_bf = _make_variant(base_pattern="bull_flag", mode="shadow")
    v_ft = _make_variant(base_pattern="flat_top", mode="shadow")

    await store.save_variant(v_bf)
    await store.save_variant(v_ft)

    bull_flag_variants = await store.list_variants(pattern_name="bull_flag")
    assert len(bull_flag_variants) == 1
    assert bull_flag_variants[0].mode == "shadow"

    await store.update_variant_mode(v_bf.variant_id, "live")

    updated = await store.get_variant(v_bf.variant_id)
    assert updated is not None
    assert updated.mode == "live"


@pytest.mark.asyncio
async def test_save_and_list_promotion_events(store: ExperimentStore) -> None:
    """save_promotion_event + list_promotion_events round-trips correctly."""
    v_id = "variant_abc"
    event_a = _make_promotion_event(variant_id=v_id, action="promote")
    event_b = _make_promotion_event(variant_id=v_id, action="demote")
    event_other = _make_promotion_event(variant_id="other_variant")

    for ev in (event_a, event_b, event_other):
        await store.save_promotion_event(ev)

    by_variant = await store.list_promotion_events(variant_id=v_id)
    all_events = await store.list_promotion_events()

    assert len(by_variant) == 2
    assert all(e.variant_id == v_id for e in by_variant)
    assert len(all_events) == 3


@pytest.mark.asyncio
async def test_retention_enforcement_deletes_old_records(
    store: ExperimentStore,
) -> None:
    """enforce_retention removes records older than max_age_days."""
    old_ts = datetime.now(UTC) - timedelta(days=120)
    new_ts = datetime.now(UTC)

    old_exp = _make_experiment(created_at=old_ts)
    new_exp = _make_experiment(created_at=new_ts)
    old_var = _make_variant(created_at=old_ts)
    new_var = _make_variant(created_at=new_ts)
    old_promo = _make_promotion_event(timestamp=old_ts)
    new_promo = _make_promotion_event(timestamp=new_ts)

    for item in (old_exp, new_exp):
        await store.save_experiment(item)
    for item in (old_var, new_var):
        await store.save_variant(item)
    for item in (old_promo, new_promo):
        await store.save_promotion_event(item)

    deleted = await store.enforce_retention(max_age_days=90)

    # 3 old records (1 experiment + 1 variant + 1 promotion event) deleted
    assert deleted == 3

    # New records survive
    assert await store.get_experiment(new_exp.experiment_id) is not None
    assert await store.get_variant(new_var.variant_id) is not None
    remaining_promos = await store.list_promotion_events()
    assert len(remaining_promos) == 1


@pytest.mark.asyncio
async def test_wal_mode_enabled(store: ExperimentStore) -> None:
    """WAL journal mode is enabled on the database."""
    async with aiosqlite.connect(store._db_path) as conn:
        cursor = await conn.execute("PRAGMA journal_mode")
        row = await cursor.fetchone()
        assert row is not None
        assert str(row[0]).lower() == "wal"


@pytest.mark.asyncio
async def test_fire_and_forget_write_does_not_raise_on_bad_db() -> None:
    """save_experiment on a bad DB path logs a warning but never raises."""
    bad_store = ExperimentStore(db_path="/nonexistent_dir/experiments.db")
    # Do NOT call initialize — DB does not exist; write should swallow the error
    exp = _make_experiment()
    # Must not raise
    await bad_store.save_experiment(exp)


@pytest.mark.asyncio
async def test_get_experiment_returns_none_for_missing_id(
    store: ExperimentStore,
) -> None:
    """get_experiment returns None when the ID does not exist."""
    result = await store.get_experiment("nonexistent_id")
    assert result is None


@pytest.mark.asyncio
async def test_get_by_fingerprint_returns_matching_experiment(
    store: ExperimentStore,
) -> None:
    """get_by_fingerprint returns the correct record when fingerprint matches."""
    exp = _make_experiment(pattern_name="bull_flag")
    exp.parameter_fingerprint = "unique_fp_abc123"
    await store.save_experiment(exp)

    result = await store.get_by_fingerprint("bull_flag", "unique_fp_abc123")
    assert result is not None
    assert result.experiment_id == exp.experiment_id
    assert result.parameter_fingerprint == "unique_fp_abc123"


@pytest.mark.asyncio
async def test_get_by_fingerprint_returns_none_when_not_found(
    store: ExperimentStore,
) -> None:
    """get_by_fingerprint returns None when no record matches."""
    exp = _make_experiment(pattern_name="bull_flag")
    exp.parameter_fingerprint = "fp_exists"
    await store.save_experiment(exp)

    # Wrong fingerprint
    result = await store.get_by_fingerprint("bull_flag", "fp_does_not_exist")
    assert result is None

    # Wrong pattern name
    result = await store.get_by_fingerprint("flat_top", "fp_exists")
    assert result is None


@pytest.mark.asyncio
async def test_experiment_with_backtest_result_serializes_correctly(
    store: ExperimentStore,
) -> None:
    """backtest_result dict survives a JSON round-trip through the DB."""
    exp = _make_experiment(status=ExperimentStatus.COMPLETED)
    exp.backtest_result = {
        "sharpe_ratio": 2.1,
        "max_drawdown_pct": -0.08,
        "win_rate": 0.55,
        "total_trades": 100,
    }
    await store.save_experiment(exp)

    retrieved = await store.get_experiment(exp.experiment_id)
    assert retrieved is not None
    assert retrieved.backtest_result == exp.backtest_result
    assert retrieved.status == ExperimentStatus.COMPLETED


@pytest.mark.asyncio
async def test_save_experiment_with_date_objects_in_backtest_result(
    store: ExperimentStore,
) -> None:
    """DEF-151 regression: date objects in backtest_result must not raise TypeError.

    MultiObjectiveResult.to_dict() produces datetime.date values for
    start_date/end_date. save_experiment must serialize them without crashing.
    The dates are stored as ISO-format strings and round-trip correctly.
    """
    exp = _make_experiment(status=ExperimentStatus.COMPLETED)
    exp.backtest_result = {
        "start_date": date(2025, 1, 1),
        "end_date": date(2025, 12, 31),
        "sharpe_ratio": 1.5,
        "win_rate": 0.48,
    }

    # Must not raise TypeError: Object of type date is not JSON serializable
    await store.save_experiment(exp)

    retrieved = await store.get_experiment(exp.experiment_id)
    assert retrieved is not None
    assert retrieved.backtest_result is not None
    # Dates are stored as ISO strings
    assert retrieved.backtest_result["start_date"] == "2025-01-01"
    assert retrieved.backtest_result["end_date"] == "2025-12-31"
    assert retrieved.backtest_result["sharpe_ratio"] == pytest.approx(1.5)
