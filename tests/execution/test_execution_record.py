"""Tests for ExecutionRecord dataclass and persistence."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderFilledEvent,
    PositionOpenedEvent,
    Side,
    SignalEvent,
)
from argus.db.manager import DatabaseManager
from argus.execution.execution_record import (
    ExecutionRecord,
    create_execution_record,
    save_execution_record,
)
from argus.execution.order_manager import OrderManager, PendingManagedOrder
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus


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


# ---------------------------------------------------------------------------
# Helpers for OrderManager integration tests
# ---------------------------------------------------------------------------


def _make_signal(
    entry_price: float = 150.0,
    stop_price: float = 148.0,
    target_prices: tuple[float, ...] = (152.0, 154.0),
    share_count: int = 100,
) -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=share_count,
        rationale="Test signal",
    )


def _make_bracket_broker() -> MagicMock:
    """Mock broker that fills entry synchronously (SimulatedBroker pattern)."""
    broker = MagicMock()
    counter = {"n": 0}

    def bracket_side_effect(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"b-entry-{counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.02,
        )
        counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"b-stop-{counter['n']}",
            status=OrderStatus.PENDING,
        )
        target_results = []
        for t in targets:
            counter["n"] += 1
            target_results.append(
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"b-tgt-{counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )
        return BracketOrderResult(
            entry=entry_result, stop=stop_result, targets=target_results
        )

    broker.place_bracket_order = AsyncMock(side_effect=bracket_side_effect)
    broker.cancel_order = AsyncMock(return_value=True)
    return broker


class TestOrderManagerExecutionRecord:
    """Tests for execution record integration in OrderManager."""

    @pytest.mark.asyncio
    async def test_handle_entry_fill_creates_execution_record(self) -> None:
        """Verify save_execution_record is called with correct fields after entry fill."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
        broker = _make_bracket_broker()
        db = DatabaseManager(":memory:")
        await db.initialize()

        om = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=OrderManagerConfig(),
            db_manager=db,
        )
        await om.start()

        signal = _make_signal(entry_price=150.0)
        approved = OrderApprovedEvent(signal=signal)
        await om.on_approved(approved)

        # Verify execution record was persisted
        row = await db.fetch_one("SELECT * FROM execution_records LIMIT 1")
        assert row is not None
        assert row["symbol"] == "AAPL"
        assert row["strategy_id"] == "orb_breakout"
        assert row["side"] == "BUY"
        assert row["expected_fill_price"] == pytest.approx(150.0)
        assert row["actual_fill_price"] == pytest.approx(150.02)
        assert row["order_size_shares"] == 100

        await om.stop()
        await db.close()

    @pytest.mark.asyncio
    async def test_handle_entry_fill_continues_on_record_failure(self) -> None:
        """Verify ManagedPosition created and PositionOpenedEvent published even when record save fails."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
        broker = _make_bracket_broker()

        # Use a db_manager mock that raises on execute
        bad_db = MagicMock()
        bad_db.execute = AsyncMock(side_effect=RuntimeError("DB exploded"))
        bad_db.commit = AsyncMock()

        opened_events: list[PositionOpenedEvent] = []

        async def capture_opened(e: PositionOpenedEvent) -> None:
            opened_events.append(e)

        event_bus.subscribe(PositionOpenedEvent, capture_opened)

        om = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=OrderManagerConfig(),
            db_manager=bad_db,
        )
        await om.start()

        signal = _make_signal()
        approved = OrderApprovedEvent(signal=signal)
        await om.on_approved(approved)

        # Allow event bus tasks to dispatch
        await asyncio.sleep(0)

        # Position should still be created despite record failure
        positions = om.get_managed_positions()
        assert "AAPL" in positions
        assert len(positions["AAPL"]) == 1

        # PositionOpenedEvent should still have been published
        assert len(opened_events) == 1

        await om.stop()

    def test_pending_order_carries_expected_price(self) -> None:
        """Verify PendingManagedOrder has expected_fill_price set from signal.entry_price."""
        pending = PendingManagedOrder(
            order_id="test-001",
            symbol="TSLA",
            strategy_id="vwap_reclaim",
            order_type="entry",
            expected_fill_price=45.50,
        )
        assert pending.expected_fill_price == 45.50

    def test_pending_order_carries_signal_timestamp(self) -> None:
        """Verify signal_timestamp is set from clock.now()."""
        ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=UTC)
        pending = PendingManagedOrder(
            order_id="test-002",
            symbol="NVDA",
            strategy_id="bull_flag",
            order_type="entry",
            signal_timestamp=ts,
        )
        assert pending.signal_timestamp == ts

    def test_pending_order_defaults_backward_compatible(self) -> None:
        """Verify default values are backward compatible."""
        pending = PendingManagedOrder(
            order_id="test-003",
            symbol="AMD",
            strategy_id="orb_scalp",
            order_type="stop",
        )
        assert pending.expected_fill_price == 0.0
        assert pending.signal_timestamp is None

    def test_execution_record_slippage_computation_realistic(self) -> None:
        """Test with realistic prices: entry=$45.50, fill=$45.52 → verify bps."""
        signal_ts = datetime(2026, 3, 23, 14, 30, 0, tzinfo=timezone.utc)
        fill_ts = datetime(2026, 3, 23, 14, 30, 0, 350_000, tzinfo=timezone.utc)

        record = create_execution_record(
            order_id="order_realistic",
            symbol="SOFI",
            strategy_id="orb_breakout",
            side="BUY",
            expected_fill_price=45.50,
            actual_fill_price=45.52,
            order_size_shares=200,
            signal_timestamp=signal_ts,
            fill_timestamp=fill_ts,
        )

        # $0.02 / $45.50 * 10000 = ~4.396 bps
        expected_bps = abs(45.52 - 45.50) / 45.50 * 10_000
        assert record.actual_slippage_bps == pytest.approx(expected_bps, abs=0.01)
        assert record.slippage_vs_model == pytest.approx(expected_bps - 1.0, abs=0.01)
        assert record.latency_ms == pytest.approx(350.0, abs=1.0)
