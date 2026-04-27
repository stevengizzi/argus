"""Tests for DEF-158: Duplicate SELL order prevention.

Three root causes addressed:
1. Flatten-pending timeout resubmits while original order fills at broker
2. Startup cleanup doesn't cancel pre-existing bracket orders
3. Stop fill doesn't cancel concurrent flatten orders

These tests verify that duplicate SELL orders are prevented regardless
of which code path creates the race condition.
"""

from __future__ import annotations

import time as _time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    ExitEscalationConfig,
    ExitManagementConfig,
    OrderManagerConfig,
    ReconciliationConfig,
    StartupConfig,
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
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus


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

    def make_order_id() -> str:
        order_counter["count"] += 1
        return f"order-{order_counter['count']}"

    def make_bracket_result(entry, stop, targets) -> BracketOrderResult:
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{make_order_id()}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{make_order_id()}",
            status=OrderStatus.PENDING,
        )
        target_results = []
        for target in targets:
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{make_order_id()}",
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
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    # 10:00 AM ET = 14:00 UTC (market open)
    return FixedClock(datetime(2026, 4, 20, 14, 0, 0, tzinfo=UTC))


def _make_signal(
    symbol: str = "ARX",
    time_stop_seconds: int | None = 900,
) -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=14.44,
        stop_price=14.36,
        target_prices=(14.54, 14.64),
        share_count=205,
        rationale="Test signal",
        atr_value=0.15,
        time_stop_seconds=time_stop_seconds,
    )


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
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
    )


async def _open_position(
    om: OrderManager,
    mock_broker: MagicMock,
    symbol: str = "ARX",
) -> ManagedPosition:
    """Submit and fill an entry to create a ManagedPosition."""
    signal = _make_signal(symbol=symbol)
    approved = OrderApprovedEvent(signal=signal, modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get(symbol, [])
    assert len(positions) == 1
    return positions[0]


# ---------------------------------------------------------------------------
# Test 1: Flatten-pending timeout does NOT resubmit when broker position is 0
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_timeout_skips_resubmit_when_broker_position_closed(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock
) -> None:
    """DEF-158 Root Cause 1: The flatten-pending timeout mechanism resubmits
    a fresh MARKET SELL when the original order hasn't had its fill callback
    arrive within 120s. If the original order already filled at IBKR (delayed
    callback), the resubmission creates a short position.

    Fix: Before resubmitting, query broker position. If 0, clear pending.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock, flatten_pending_timeout=10)
    position = await _open_position(om, mock_broker)

    # Simulate a flatten order being placed (e.g., from time-stop)
    om._flatten_pending["ARX"] = ("flatten-order-1", _time.monotonic() - 10, 0)
    om._pending_orders["flatten-order-1"] = MagicMock(
        symbol="ARX", order_type="flatten", strategy_id="orb_breakout"
    )

    # Broker reports position is already closed (original order filled)
    mock_broker.get_positions.return_value = []

    # Reset place_order call count
    mock_broker.place_order.reset_mock()

    # Run timeout check
    await om._check_flatten_pending_timeouts()

    # Should NOT have placed a new order (position already flat at broker)
    mock_broker.place_order.assert_not_called()

    # Flatten-pending should be cleared
    assert "ARX" not in om._flatten_pending


@pytest.mark.asyncio
async def test_flatten_timeout_does_resubmit_when_broker_position_exists(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock
) -> None:
    """Verify timeout resubmission still works when broker position exists."""
    om = _make_om(event_bus, mock_broker, fixed_clock, flatten_pending_timeout=10)
    position = await _open_position(om, mock_broker)

    # Simulate a flatten order being placed
    om._flatten_pending["ARX"] = ("flatten-order-1", _time.monotonic() - 10, 0)
    om._pending_orders["flatten-order-1"] = MagicMock(
        symbol="ARX", order_type="flatten", strategy_id="orb_breakout"
    )

    # Broker reports position still open (103 shares — original hasn't filled)
    mock_broker.get_positions.return_value = [
        MagicMock(symbol="ARX", shares=103)
    ]

    # Configure place_order to return a new order
    mock_broker.place_order.return_value = OrderResult(
        order_id="flatten-order-2",
        broker_order_id="broker-flatten-2",
        status=OrderStatus.PENDING,
    )

    # Run timeout check
    await om._check_flatten_pending_timeouts()

    # SHOULD have placed a new order (position still open)
    mock_broker.place_order.assert_called_once()

    # Flatten-pending should be updated with new order
    assert "ARX" in om._flatten_pending
    assert om._flatten_pending["ARX"][0] == "flatten-order-2"


# ---------------------------------------------------------------------------
# Test 2: Startup cleanup cancels pre-existing orders before flatten
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_cleanup_cancels_existing_orders_before_flatten(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock
) -> None:
    """DEF-158 Root Cause 2: Startup cleanup places a MARKET SELL without
    cancelling residual bracket orders from a prior session. If those bracket
    legs fill after the flatten, the position goes short.

    Fix: Cancel all open orders for the symbol before placing the flatten.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)

    # Simulate IBKR has open stop + T1 orders for ARX (from prior session)
    residual_stop = MagicMock(symbol="ARX", order_id="old-stop-123")
    residual_t1 = MagicMock(symbol="ARX", order_id="old-t1-456")
    other_symbol_order = MagicMock(symbol="TSLA", order_id="other-789")
    mock_broker.get_open_orders.return_value = [
        residual_stop, residual_t1, other_symbol_order,
    ]

    # Place flatten
    await om._flatten_unknown_position("ARX", 103)

    # Should have cancelled ARX orders but NOT TSLA order
    cancel_calls = [
        call.args[0] for call in mock_broker.cancel_order.call_args_list
    ]
    assert "old-stop-123" in cancel_calls
    assert "old-t1-456" in cancel_calls
    assert "other-789" not in cancel_calls

    # Should have placed the sell order
    mock_broker.place_order.assert_called_once()
    sell_order = mock_broker.place_order.call_args[0][0]
    assert sell_order.symbol == "ARX"
    assert sell_order.quantity == 103


# ---------------------------------------------------------------------------
# Test 3: Stop fill cancels concurrent flatten order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_fill_cancels_concurrent_flatten_order(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock
) -> None:
    """DEF-158 Root Cause 3: When a broker-side stop fills concurrently
    with a pending flatten order (e.g., time-stop placed a SELL, but the
    broker stop triggered first), the flatten order must be cancelled.
    Otherwise both SELLs execute and the position goes short.

    Fix: _handle_stop_fill cancels pending flatten orders for the symbol.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    position = await _open_position(om, mock_broker)

    # Simulate: time-stop placed a flatten order
    om._flatten_pending["ARX"] = ("flatten-order-concurrent", _time.monotonic(), 0)
    om._pending_orders["flatten-order-concurrent"] = MagicMock(
        symbol="ARX", order_type="flatten", strategy_id="orb_breakout",
        shares=103,
    )

    # Now the broker-side stop fires
    stop_order_id = position.stop_order_id
    assert stop_order_id is not None

    # Reset cancel mock to track new calls
    mock_broker.cancel_order.reset_mock()

    # Fire stop fill
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=14.36,
        fill_quantity=205,
    )
    await om.on_fill(stop_fill)

    # Verify the concurrent flatten order was cancelled
    cancel_calls = [
        call.args[0] for call in mock_broker.cancel_order.call_args_list
    ]
    assert "flatten-order-concurrent" in cancel_calls

    # Flatten-pending should be cleared
    assert "ARX" not in om._flatten_pending

    # Position should be closed
    assert position.is_fully_closed


# ---------------------------------------------------------------------------
# Test 4: Flatten fill cancels duplicate flatten orders
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_fill_cancels_other_pending_flatten_orders(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock
) -> None:
    """DEF-158: When a flatten fill arrives, any other pending flatten orders
    for the same symbol (from timeout resubmission) must be cancelled.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    position = await _open_position(om, mock_broker)

    # Simulate T1 fill to reduce shares
    position.shares_remaining = 103
    position.t1_filled = True

    # Two flatten orders pending: the original and a timeout resubmission
    from argus.execution.order_manager import PendingManagedOrder

    om._pending_orders["flatten-original"] = PendingManagedOrder(
        order_id="flatten-original",
        symbol="ARX",
        strategy_id="orb_breakout",
        order_type="flatten",
        shares=103,
    )
    om._pending_orders["flatten-resubmit"] = PendingManagedOrder(
        order_id="flatten-resubmit",
        symbol="ARX",
        strategy_id="orb_breakout",
        order_type="flatten",
        shares=103,
    )
    om._flatten_pending["ARX"] = ("flatten-resubmit", _time.monotonic(), 1)

    # Reset cancel mock
    mock_broker.cancel_order.reset_mock()

    # First flatten fills
    fill_event = OrderFilledEvent(
        order_id="flatten-original",
        fill_price=14.77,
        fill_quantity=103,
    )
    await om.on_fill(fill_event)

    # The resubmit order should have been cancelled
    cancel_calls = [
        call.args[0] for call in mock_broker.cancel_order.call_args_list
    ]
    assert "flatten-resubmit" in cancel_calls

    # Position should be closed
    assert position.is_fully_closed

    # The resubmit order should be removed from pending
    assert "flatten-resubmit" not in om._pending_orders
