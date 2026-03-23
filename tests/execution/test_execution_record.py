"""Tests for ExecutionRecord dataclass and persistence."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from argus.db.manager import DatabaseManager
from argus.execution.execution_record import (
    ExecutionRecord,
    create_execution_record,
    save_execution_record,
)


class TestCreateExecutionRecord:
    """Tests for the create_execution_record factory function."""

    def test_create_execution_record_computes_slippage(self) -> None:
        """Verify actual_slippage_bps computation: expected=100.0, actual=100.05 → 5.0 bps."""
        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 0, 500_000, tzinfo=timezone.utc)

        record = create_execution_record(
            order_id="order_001",
            symbol="AAPL",
            strategy_id="orb_breakout",
            side="BUY",
            expected_fill_price=100.0,
            actual_fill_price=100.05,
            order_size_shares=100,
            signal_timestamp=signal_ts,
            fill_timestamp=fill_ts,
        )

        assert record.actual_slippage_bps == pytest.approx(5.0, abs=0.01)
        assert record.slippage_vs_model == pytest.approx(4.0, abs=0.01)
        assert record.expected_slippage_bps == 1.0

    def test_create_execution_record_computes_latency(self) -> None:
        """Verify latency_ms computed from signal and fill timestamps."""
        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 1, 500_000, tzinfo=timezone.utc)

        record = create_execution_record(
            order_id="order_002",
            symbol="TSLA",
            strategy_id="vwap_reclaim",
            side="BUY",
            expected_fill_price=200.0,
            actual_fill_price=200.10,
            order_size_shares=50,
            signal_timestamp=signal_ts,
            fill_timestamp=fill_ts,
        )

        assert record.latency_ms == pytest.approx(1500.0, abs=1.0)
        assert record.time_of_day == "14:30:01"

    def test_create_execution_record_nullable_fields(self) -> None:
        """Verify avg_daily_volume=None and bid_ask_spread_bps=None work correctly."""
        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)

        record = create_execution_record(
            order_id="order_003",
            symbol="NVDA",
            strategy_id="bull_flag",
            side="BUY",
            expected_fill_price=150.0,
            actual_fill_price=150.0,
            order_size_shares=200,
            signal_timestamp=signal_ts,
            fill_timestamp=fill_ts,
            avg_daily_volume=None,
            bid_ask_spread_bps=None,
        )

        assert record.avg_daily_volume is None
        assert record.bid_ask_spread_bps is None
        assert record.actual_slippage_bps == pytest.approx(0.0)
        assert record.slippage_vs_model == pytest.approx(-1.0)

    def test_create_execution_record_zero_price_raises(self) -> None:
        """Verify ValueError raised when expected_fill_price is zero."""
        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)

        with pytest.raises(ValueError, match="expected_fill_price must be non-zero"):
            create_execution_record(
                order_id="order_004",
                symbol="BAD",
                strategy_id="test",
                side="BUY",
                expected_fill_price=0.0,
                actual_fill_price=1.0,
                order_size_shares=1,
                signal_timestamp=signal_ts,
                fill_timestamp=fill_ts,
            )


class TestSaveExecutionRecord:
    """Tests for save_execution_record and schema."""

    @pytest.mark.asyncio
    async def test_save_execution_record_round_trip(self) -> None:
        """Save to :memory: DB, read back, verify all fields match."""
        db = DatabaseManager(":memory:")
        await db.initialize()

        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 0, 250_000, tzinfo=timezone.utc)

        record = create_execution_record(
            order_id="order_rt",
            symbol="MSFT",
            strategy_id="orb_scalp",
            side="BUY",
            expected_fill_price=400.0,
            actual_fill_price=400.08,
            order_size_shares=75,
            signal_timestamp=signal_ts,
            fill_timestamp=fill_ts,
            avg_daily_volume=25_000_000,
            bid_ask_spread_bps=0.5,
        )

        await save_execution_record(db, record)

        row = await db.fetch_one(
            "SELECT * FROM execution_records WHERE record_id = ?",
            (record.record_id,),
        )
        assert row is not None

        assert row["order_id"] == "order_rt"
        assert row["symbol"] == "MSFT"
        assert row["strategy_id"] == "orb_scalp"
        assert row["side"] == "BUY"
        assert row["expected_fill_price"] == pytest.approx(400.0)
        assert row["actual_fill_price"] == pytest.approx(400.08)
        assert row["expected_slippage_bps"] == pytest.approx(1.0)
        assert row["actual_slippage_bps"] == pytest.approx(2.0, abs=0.01)
        assert row["slippage_vs_model"] == pytest.approx(1.0, abs=0.01)
        assert row["order_size_shares"] == 75
        assert row["avg_daily_volume"] == 25_000_000
        assert row["bid_ask_spread_bps"] == pytest.approx(0.5)
        assert row["latency_ms"] == pytest.approx(250.0, abs=1.0)
        assert row["time_of_day"] == "14:30:00"
        assert row["created_at"] is not None

        await db.close()

    @pytest.mark.asyncio
    async def test_execution_records_table_exists(self) -> None:
        """Verify execution_records table is created in the schema."""
        db = DatabaseManager(":memory:")
        await db.initialize()

        row = await db.fetch_one(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_records'"
        )
        assert row is not None
        assert row["name"] == "execution_records"

        await db.close()
