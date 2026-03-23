"""Tests for slippage model calibration (Sprint 27.5 S5)."""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from argus.analytics.slippage_model import (
    SlippageConfidence,
    StrategySlippageModel,
    calibrate_slippage_model,
    load_slippage_model,
    save_slippage_model,
)
from argus.db.manager import DatabaseManager


@pytest.fixture
async def db() -> DatabaseManager:
    """In-memory database with execution_records table."""
    db_manager = DatabaseManager(":memory:")
    await db_manager.initialize()
    return db_manager


async def _insert_records(
    db: DatabaseManager,
    strategy_id: str,
    records: list[dict[str, object]],
) -> None:
    """Insert synthetic execution records into the database.

    Args:
        db: Initialized DatabaseManager.
        strategy_id: Strategy to associate records with.
        records: List of dicts with keys: actual_slippage_bps, time_of_day,
                 order_size_shares. Other columns get sensible defaults.
    """
    for i, rec in enumerate(records):
        await db.execute(
            """
            INSERT INTO execution_records (
                record_id, order_id, symbol, strategy_id, side,
                expected_fill_price, expected_slippage_bps,
                actual_fill_price, actual_slippage_bps,
                time_of_day, order_size_shares,
                avg_daily_volume, bid_ask_spread_bps, latency_ms,
                slippage_vs_model, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                f"rec_{i:04d}",
                f"ord_{i:04d}",
                "AAPL",
                strategy_id,
                "BUY",
                150.0,
                1.0,
                150.02,
                rec["actual_slippage_bps"],
                rec["time_of_day"],
                rec["order_size_shares"],
                1_000_000,
                2.0,
                5.0,
                float(rec["actual_slippage_bps"]) - 1.0,  # type: ignore[arg-type]
                datetime.now(timezone.utc).isoformat(),
            ),
        )
    await db.commit()


@pytest.mark.asyncio
async def test_calibrate_sufficient_records(db: DatabaseManager) -> None:
    """50 records → HIGH confidence, correct mean/std."""
    records = [
        {"actual_slippage_bps": 2.0 + i * 0.1, "time_of_day": "10:30:00", "order_size_shares": 100}
        for i in range(50)
    ]
    await _insert_records(db, "orb_breakout", records)

    model = await calibrate_slippage_model(db, "orb_breakout")

    assert model.confidence == SlippageConfidence.HIGH
    assert model.sample_count == 50

    # Mean of 2.0, 2.1, ..., 6.9 = (2.0 + 6.9) / 2 = 4.45
    expected_mean = sum(2.0 + i * 0.1 for i in range(50)) / 50
    assert abs(model.estimated_mean_slippage_bps - expected_mean) < 1e-6

    # Std dev should be positive for varying data
    assert model.estimated_std_slippage_bps > 0.0


@pytest.mark.asyncio
async def test_calibrate_moderate_records(db: DatabaseManager) -> None:
    """25 records → MODERATE confidence."""
    records = [
        {"actual_slippage_bps": 3.0, "time_of_day": "11:00:00", "order_size_shares": 100}
        for _ in range(25)
    ]
    await _insert_records(db, "vwap_reclaim", records)

    model = await calibrate_slippage_model(db, "vwap_reclaim")

    assert model.confidence == SlippageConfidence.MODERATE
    assert model.sample_count == 25
    assert abs(model.estimated_mean_slippage_bps - 3.0) < 1e-6


@pytest.mark.asyncio
async def test_calibrate_insufficient_records(db: DatabaseManager) -> None:
    """3 records → INSUFFICIENT confidence, zeroed model."""
    records = [
        {"actual_slippage_bps": 5.0, "time_of_day": "09:45:00", "order_size_shares": 200}
        for _ in range(3)
    ]
    await _insert_records(db, "bull_flag", records)

    model = await calibrate_slippage_model(db, "bull_flag")

    assert model.confidence == SlippageConfidence.INSUFFICIENT
    assert model.sample_count == 3
    assert model.estimated_mean_slippage_bps == 0.0
    assert model.estimated_std_slippage_bps == 0.0
    assert model.size_adjustment_slope == 0.0
    assert all(v == 0.0 for v in model.time_of_day_adjustment.values())


@pytest.mark.asyncio
async def test_time_of_day_adjustment(db: DatabaseManager) -> None:
    """Records clustered morning/afternoon → different adjustments."""
    # Morning records (pre-10am): higher slippage
    morning_records = [
        {"actual_slippage_bps": 6.0, "time_of_day": "09:35:00", "order_size_shares": 100}
        for _ in range(10)
    ]
    # Midday records (10am-2pm): lower slippage
    midday_records = [
        {"actual_slippage_bps": 2.0, "time_of_day": "11:00:00", "order_size_shares": 100}
        for _ in range(10)
    ]
    # Afternoon records (post-2pm): medium slippage
    afternoon_records = [
        {"actual_slippage_bps": 4.0, "time_of_day": "14:30:00", "order_size_shares": 100}
        for _ in range(10)
    ]
    all_records = morning_records + midday_records + afternoon_records
    await _insert_records(db, "orb_scalp", all_records)

    model = await calibrate_slippage_model(db, "orb_scalp")

    # Overall mean = (6*10 + 2*10 + 4*10) / 30 = 4.0
    assert abs(model.estimated_mean_slippage_bps - 4.0) < 1e-6

    # Morning adjustment = 6.0 - 4.0 = 2.0
    assert abs(model.time_of_day_adjustment["pre_10am"] - 2.0) < 1e-6
    # Midday adjustment = 2.0 - 4.0 = -2.0
    assert abs(model.time_of_day_adjustment["10am_2pm"] - (-2.0)) < 1e-6
    # Afternoon adjustment = 4.0 - 4.0 = 0.0
    assert abs(model.time_of_day_adjustment["post_2pm"] - 0.0) < 1e-6


@pytest.mark.asyncio
async def test_size_adjustment_slope(db: DatabaseManager) -> None:
    """Larger orders have higher slippage → positive slope."""
    records = [
        {
            "actual_slippage_bps": 1.0 + (shares / 100) * 0.5,
            "time_of_day": "10:30:00",
            "order_size_shares": shares,
        }
        for shares in range(100, 1100, 100)  # 100, 200, ..., 1000
    ]
    await _insert_records(db, "afternoon_momentum", records)

    model = await calibrate_slippage_model(db, "afternoon_momentum")

    # Slippage increases by 0.5 bps per 100 shares → slope ≈ 0.5
    assert model.size_adjustment_slope > 0.0
    assert abs(model.size_adjustment_slope - 0.5) < 0.01


@pytest.mark.asyncio
async def test_zero_slippage_records(db: DatabaseManager) -> None:
    """All zero slippage (paper trading) → mean=0.0, no error."""
    records = [
        {"actual_slippage_bps": 0.0, "time_of_day": "10:00:00", "order_size_shares": 100}
        for _ in range(10)
    ]
    await _insert_records(db, "paper_strategy", records)

    model = await calibrate_slippage_model(db, "paper_strategy")

    assert model.estimated_mean_slippage_bps == 0.0
    assert model.estimated_std_slippage_bps == 0.0
    assert model.confidence == SlippageConfidence.LOW
    assert model.sample_count == 10


def test_save_load_roundtrip(tmp_path: object) -> None:
    """save → load → identical model."""
    original = StrategySlippageModel(
        strategy_id="orb_breakout",
        estimated_mean_slippage_bps=3.5,
        estimated_std_slippage_bps=1.2,
        time_of_day_adjustment={"pre_10am": 1.0, "10am_2pm": -0.5, "post_2pm": 0.3},
        size_adjustment_slope=0.15,
        sample_count=75,
        confidence=SlippageConfidence.HIGH,
        last_calibrated=datetime(2026, 3, 23, 12, 0, 0, tzinfo=timezone.utc),
    )

    file_path = str(tmp_path) + "/model.json"  # type: ignore[operator]
    save_slippage_model(original, file_path)
    loaded = load_slippage_model(file_path)

    assert loaded.strategy_id == original.strategy_id
    assert loaded.estimated_mean_slippage_bps == original.estimated_mean_slippage_bps
    assert loaded.estimated_std_slippage_bps == original.estimated_std_slippage_bps
    assert loaded.time_of_day_adjustment == original.time_of_day_adjustment
    assert loaded.size_adjustment_slope == original.size_adjustment_slope
    assert loaded.sample_count == original.sample_count
    assert loaded.confidence == original.confidence
    assert loaded.last_calibrated == original.last_calibrated


def test_load_missing_file() -> None:
    """FileNotFoundError raised for missing file."""
    with pytest.raises(FileNotFoundError):
        load_slippage_model("/nonexistent/path/model.json")
