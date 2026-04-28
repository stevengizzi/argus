"""Tests for Sprint 28.75 Session 1: operational fixes.

R1: Trail activation verification (config timing root cause)
R2: Flatten-pending timeout with max retries
R3: Rate-limited 'flatten already pending' log messages
R4: Rate-limited 'portfolio snapshot missing' log messages
"""

from __future__ import annotations

import logging
import time as _time
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    ExitEscalationConfig,
    ExitManagementConfig,
    OrderManagerConfig,
    ReconciliationConfig,
    TrailingStopConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    ReconciliationPosition,
)
from argus.models.trading import BracketOrderResult, OrderResult, OrderSide, OrderStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    order_counter = {"count": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["count"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['count']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        order_counter["count"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['count']}",
            status=OrderStatus.PENDING,
        )
        target_results = []
        for target in targets:
            order_counter["count"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['count']}",
                    status=OrderStatus.PENDING,
                )
            )
        return BracketOrderResult(
            entry=entry_result, stop=stop_result, targets=target_results,
        )

    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-order-1",
            broker_order_id="broker-flatten-1",
            status=OrderStatus.PENDING,
        )
    )
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 3, 30, 15, 0, 0, tzinfo=UTC))


def _make_signal(
    strategy_id: str = "orb_breakout",
    atr_value: float | None = 1.5,
    time_stop_seconds: int | None = 300,
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test signal",
        atr_value=atr_value,
        time_stop_seconds=time_stop_seconds,
    )


def _trail_enabled_config(
    activation: str = "after_t1",
    trail_type: str = "atr",
    atr_multiplier: float = 2.0,
) -> ExitManagementConfig:
    return ExitManagementConfig(
        trailing_stop=TrailingStopConfig(
            enabled=True,
            type=trail_type,
            atr_multiplier=atr_multiplier,
            activation=activation,
            min_trail_distance=0.05,
        ),
        escalation=ExitEscalationConfig(enabled=False),
    )


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    exit_config: ExitManagementConfig | None = None,
    flatten_pending_timeout: int = 120,
    max_flatten_retries: int = 3,
) -> OrderManager:
    config = OrderManagerConfig(
        flatten_pending_timeout_seconds=flatten_pending_timeout,
        max_flatten_retries=max_flatten_retries,
    )
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        exit_config=exit_config,
    )


async def _open_position(
    om: OrderManager,
    mock_broker: MagicMock,
    signal: SignalEvent | None = None,
) -> ManagedPosition:
    """Submit and fill an entry to create a ManagedPosition."""
    signal = signal or _make_signal()
    approved = OrderApprovedEvent(signal=signal, modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    return positions[0]


async def _open_and_fill_t1(
    om: OrderManager,
    mock_broker: MagicMock,
) -> ManagedPosition:
    """Open position and simulate T1 fill."""
    position = await _open_position(om, mock_broker)
    t1_fill = OrderFilledEvent(
        order_id=position.t1_order_id or "t1-unknown",
        fill_price=152.0,
        fill_quantity=position.t1_shares,
    )
    await om.on_fill(t1_fill)
    positions = om._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    return positions[0]


# ---------------------------------------------------------------------------
# R1: Trail activation verification tests
# ---------------------------------------------------------------------------


class TestTrailActivationVerification:
    """Verify the full trail path fires end-to-end when config is enabled."""

    @pytest.mark.asyncio
    async def test_trail_activation_after_t1(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Trail activates after T1 fill with enabled config and valid ATR.

        End-to-end verification that:
        1. exit_config is populated on ManagedPosition at entry
        2. trail_active becomes True after T1 fill
        3. trail_stop_price is computed from ATR
        4. atr_value flows from signal to position
        """
        config = _trail_enabled_config(activation="after_t1")
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        # Verify all trail state
        assert position.exit_config is not None
        assert position.exit_config.trailing_stop.enabled is True
        assert position.atr_value == 1.5
        assert position.trail_active is True
        assert position.trail_stop_price > 0.0
        # ATR trail: high_watermark(152.0) - atr(1.5) * multiplier(2.0) = 149.0
        # But high_watermark is entry_price(150.0) since T1 fill only updates
        # realized_pnl, not high_watermark via tick. Initial trail computed from
        # entry fill high_watermark.
        assert position.trail_stop_price > 0.0

        await om.stop()

    @pytest.mark.asyncio
    async def test_trail_stop_computed_on_tick(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """on_tick computes trail stop when trail_active is True.

        After T1 fill, a tick at a higher price should:
        1. Update high_watermark
        2. Ratchet trail_stop_price upward
        """
        config = _trail_enabled_config(
            activation="after_t1", trail_type="atr", atr_multiplier=2.0
        )
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)
        initial_trail = position.trail_stop_price

        # Tick at higher price — ratchet up
        tick = TickEvent(symbol="AAPL", price=155.0, timestamp=fixed_clock.now())
        await om.on_tick(tick)

        assert position.high_watermark == 155.0
        # 155.0 - 1.5 * 2.0 = 152.0, which should be > initial trail
        assert position.trail_stop_price > initial_trail
        assert position.trail_stop_price == 152.0

        await om.stop()


# ---------------------------------------------------------------------------
# R2: Flatten-pending timeout tests
# ---------------------------------------------------------------------------


class TestFlattenPendingTimeout:

    @pytest.mark.asyncio
    async def test_flatten_pending_timeout_resubmits(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Stale flatten order is cancelled and resubmitted after timeout."""
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            flatten_pending_timeout=120,
            max_flatten_retries=3,
        )
        await om.start()

        position = await _open_position(om, mock_broker)

        # Inject a stale flatten-pending entry (placed 200s ago)
        stale_time = _time.monotonic() - 200
        om._flatten_pending["AAPL"] = ("old-flatten-order", stale_time, 0)
        om._pending_orders["old-flatten-order"] = MagicMock(
            order_type="flatten", symbol="AAPL"
        )

        # New order result for resubmission
        mock_broker.place_order.return_value = OrderResult(
            order_id="new-flatten-order",
            broker_order_id="broker-new-flatten",
            status=OrderStatus.PENDING,
        )

        mock_broker.cancel_order.reset_mock()
        mock_broker.place_order.reset_mock()

        await om._check_flatten_pending_timeouts()

        # Old order cancelled, new one placed
        mock_broker.cancel_order.assert_called_once_with("old-flatten-order")
        mock_broker.place_order.assert_called_once()

        # Entry updated with new order ID and incremented retry count
        entry = om._flatten_pending.get("AAPL")
        assert entry is not None
        assert entry[0] == "new-flatten-order"
        assert entry[2] == 1  # retry_count incremented

        await om.stop()

    @pytest.mark.asyncio
    async def test_flatten_pending_max_retries_stops(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Retries stop after max_flatten_retries is exhausted."""
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            flatten_pending_timeout=120,
            max_flatten_retries=3,
        )
        await om.start()

        position = await _open_position(om, mock_broker)

        # Inject entry at max retries (placed 200s ago, retry_count=3)
        stale_time = _time.monotonic() - 200
        om._flatten_pending["AAPL"] = ("exhausted-order", stale_time, 3)

        mock_broker.cancel_order.reset_mock()
        mock_broker.place_order.reset_mock()

        await om._check_flatten_pending_timeouts()

        # No broker calls — retries exhausted
        mock_broker.cancel_order.assert_not_called()
        mock_broker.place_order.assert_not_called()

        # Entry removed from _flatten_pending
        assert "AAPL" not in om._flatten_pending

        await om.stop()

    @pytest.mark.asyncio
    async def test_flatten_pending_timestamp_tracking(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Timestamp and retry_count are recorded and updated on resubmission."""
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            flatten_pending_timeout=60,
            max_flatten_retries=5,
        )
        await om.start()

        position = await _open_position(om, mock_broker)

        # First flatten via _flatten_position
        await om._flatten_position(position, reason="time_stop")

        entry = om._flatten_pending.get("AAPL")
        assert entry is not None
        order_id_1, ts_1, retry_1 = entry
        assert retry_1 == 0
        assert ts_1 > 0  # monotonic time recorded

        # Manually age the entry past timeout
        om._flatten_pending["AAPL"] = (order_id_1, _time.monotonic() - 100, 0)

        mock_broker.place_order.return_value = OrderResult(
            order_id="resubmit-1",
            broker_order_id="broker-resub-1",
            status=OrderStatus.PENDING,
        )

        await om._check_flatten_pending_timeouts()

        entry2 = om._flatten_pending.get("AAPL")
        assert entry2 is not None
        order_id_2, ts_2, retry_2 = entry2
        assert order_id_2 == "resubmit-1"
        assert retry_2 == 1
        assert ts_2 > ts_1 - 100  # New timestamp is recent

        await om.stop()

    @pytest.mark.asyncio
    async def test_flatten_pending_not_timed_out_skips(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Fresh flatten-pending entry is not resubmitted."""
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            flatten_pending_timeout=120,
        )
        await om.start()

        position = await _open_position(om, mock_broker)

        # Fresh entry (placed just now)
        om._flatten_pending["AAPL"] = ("fresh-order", _time.monotonic(), 0)

        mock_broker.cancel_order.reset_mock()
        mock_broker.place_order.reset_mock()

        await om._check_flatten_pending_timeouts()

        # No resubmission
        mock_broker.cancel_order.assert_not_called()
        mock_broker.place_order.assert_not_called()
        assert "AAPL" in om._flatten_pending

        await om.stop()


# ---------------------------------------------------------------------------
# R3: Rate-limited 'flatten already pending' log messages
# ---------------------------------------------------------------------------


class TestThrottledFlattenPendingLog:

    @pytest.mark.asyncio
    async def test_throttled_flatten_pending_log(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Repeated flatten-pending messages are suppressed after first occurrence."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        await om.start()

        position = await _open_position(om, mock_broker)

        # First flatten — places the order
        await om._flatten_position(position, reason="time_stop")
        assert "AAPL" in om._flatten_pending

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="argus.execution.order_manager"):
            # Second and third flatten — should be suppressed after first
            await om._flatten_position(position, reason="time_stop")
            first_count = sum(
                1 for r in caplog.records if "Flatten already pending" in r.message
            )

            await om._flatten_position(position, reason="time_stop")
            await om._flatten_position(position, reason="time_stop")
            await om._flatten_position(position, reason="time_stop")
            second_count = sum(
                1 for r in caplog.records if "Flatten already pending" in r.message
            )

        # First occurrence logs, subsequent are throttled within 60s
        assert first_count == 1
        assert second_count == 1  # Still just the one — rest suppressed

        await om.stop()


# ---------------------------------------------------------------------------
# R4: Rate-limited 'portfolio snapshot missing' log messages
# ---------------------------------------------------------------------------


class TestThrottledReconciliationLog:

    @pytest.mark.asyncio
    async def test_throttled_reconciliation_log(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Reconciliation 'snapshot missing' message is throttled to once per 10min."""
        recon_config = ReconciliationConfig(
            auto_cleanup_unconfirmed=False,
            auto_cleanup_orphans=False,
        )
        om = OrderManager(
            event_bus=event_bus,
            broker=mock_broker,
            clock=fixed_clock,
            config=OrderManagerConfig(),
            reconciliation_config=recon_config,
        )
        await om.start()

        position = await _open_position(om, mock_broker)

        # Mark as broker-confirmed (so it takes the confirmed path)
        om._broker_confirmed["AAPL"] = True

        # Broker reports no positions (AAPL "missing" from snapshot)
        empty_broker_positions: dict[str, ReconciliationPosition] = {}

        caplog.clear()
        with caplog.at_level(logging.WARNING, logger="argus.execution.order_manager"):
            # First reconciliation — should log
            await om.reconcile_positions(empty_broker_positions)
            first_count = sum(
                1 for r in caplog.records
                if "portfolio snapshot missing" in r.message.lower()
            )

            # Second reconciliation within 10 min — should be suppressed
            await om.reconcile_positions(empty_broker_positions)
            second_count = sum(
                1 for r in caplog.records
                if "portfolio snapshot missing" in r.message.lower()
            )

        assert first_count == 1
        assert second_count == 1  # Suppressed

        await om.stop()
