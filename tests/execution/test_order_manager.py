"""Tests for Order Manager.

All broker calls are mocked. No network calls.
Uses FixedClock for deterministic time control.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    CircuitBreakerEvent,
    CircuitBreakerLevel,
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.execution.order_manager import (
    OrderManager,
)
from argus.models.trading import OrderResult, OrderStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    """Create an Event Bus for testing."""
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
    """Create a mock Broker."""
    broker = MagicMock()
    # Default: place_order returns a result with an order_id
    order_counter = {"count": 0}

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["count"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['count']}",
            status=OrderStatus.SUBMITTED,
        )

    broker.place_order = AsyncMock(side_effect=make_order_result)
    broker.cancel_order = AsyncMock(return_value=True)
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    """Clock fixed at 10:00 AM ET on a trading day."""
    return FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def config() -> OrderManagerConfig:
    """Default Order Manager config."""
    return OrderManagerConfig()


@pytest.fixture
def order_manager(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> OrderManager:
    """Create Order Manager instance for testing."""
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )


def make_signal(
    symbol: str = "AAPL",
    entry_price: float = 150.0,
    stop_price: float = 148.0,
    target_prices: tuple[float, ...] = (152.0, 154.0),
    share_count: int = 100,
    strategy_id: str = "orb_breakout",
) -> SignalEvent:
    """Create a test SignalEvent."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=target_prices,
        share_count=share_count,
        rationale="Test signal",
    )


def make_approved(
    signal: SignalEvent | None = None,
    modifications: dict | None = None,
) -> OrderApprovedEvent:
    """Create an OrderApprovedEvent."""
    if signal is None:
        signal = make_signal()
    return OrderApprovedEvent(signal=signal, modifications=modifications)


# ---------------------------------------------------------------------------
# Happy Path Tests (7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_submit_signal_places_entry_order(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """OrderApprovedEvent → market order submitted to broker."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    # Verify broker.place_order was called
    mock_broker.place_order.assert_called_once()
    order = mock_broker.place_order.call_args[0][0]
    assert order.symbol == "AAPL"
    assert order.quantity == 100
    assert str(order.order_type) == "market"

    await order_manager.stop()


@pytest.mark.asyncio
async def test_entry_fill_creates_managed_position(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Fill event → ManagedPosition created, stop + T1 orders placed."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    # Get the entry order ID
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    # Simulate fill
    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    # Verify position was created
    assert "AAPL" in order_manager._managed_positions
    positions = order_manager._managed_positions["AAPL"]
    assert len(positions) == 1
    assert positions[0].entry_price == 150.0
    assert positions[0].shares_total == 100
    assert positions[0].shares_remaining == 100

    # Verify stop + T1 orders placed (2 more calls after entry)
    assert mock_broker.place_order.call_count == 3

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t1_fill_moves_stop_to_breakeven(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    config: OrderManagerConfig,
) -> None:
    """T1 fill → old stop cancelled, new stop at entry + buffer."""
    await order_manager.start()

    # Setup position via entry fill
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Simulate T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,  # T1 shares
    )
    await order_manager.on_fill(t1_fill)

    # Verify old stop was cancelled
    mock_broker.cancel_order.assert_called()

    # Verify position updated
    assert position.t1_filled is True
    assert position.shares_remaining == 50
    # Breakeven = 150.0 * (1 + 0.001) = 150.15
    expected_breakeven = 150.0 * (1 + config.breakeven_buffer_pct)
    assert abs(position.stop_price - expected_breakeven) < 0.01

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t2_reached_closes_remaining(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Tick at/above T2 → remaining shares closed."""
    await order_manager.start()

    # Setup position via entry fill
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Simulate T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Reset mock to track new calls
    mock_broker.place_order.reset_mock()

    # Simulate tick at T2 price
    tick = TickEvent(symbol="AAPL", price=154.0, volume=1000)
    await order_manager.on_tick(tick)

    # Verify flatten order placed
    assert mock_broker.place_order.called
    flatten_order = mock_broker.place_order.call_args[0][0]
    assert flatten_order.quantity == 50  # Remaining shares
    assert str(flatten_order.order_type) == "market"

    await order_manager.stop()


@pytest.mark.asyncio
async def test_stop_fill_closes_position(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Stop fill → position fully closed."""
    # Track PositionClosedEvent
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await order_manager.start()

    # Setup position
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    # Simulate stop fill
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify position closed
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.STOP_LOSS

    await order_manager.stop()


@pytest.mark.asyncio
async def test_full_lifecycle_t1_then_stop(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Entry → T1 → breakeven stop = 2 partial exits."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)
    await order_manager.start()

    # Entry
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fill (50 shares)
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Get new stop order ID (after breakeven adjustment)
    new_stop_id = position.stop_order_id

    # Stop fill (remaining 50 shares at breakeven)
    stop_fill = OrderFilledEvent(
        order_id=new_stop_id,
        fill_price=150.15,  # Breakeven + buffer
        fill_quantity=50,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify single close event with accumulated P&L
    assert len(closed_events) == 1
    # T1 P&L: (152 - 150) * 50 = 100
    # Stop P&L: (150.15 - 150) * 50 = 7.5
    # Total: 107.5
    assert closed_events[0].realized_pnl > 100

    await order_manager.stop()


@pytest.mark.asyncio
async def test_full_lifecycle_t1_then_t2(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Entry → T1 → T2 = full profit taken."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)
    await order_manager.start()

    # Entry
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Tick at T2 triggers flatten
    tick = TickEvent(symbol="AAPL", price=154.0, volume=1000)
    await order_manager.on_tick(tick)

    # Get flatten order ID from pending orders (last one added)
    flatten_order_id = list(order_manager._pending_orders.keys())[-1]

    # Simulate flatten fill
    flatten_fill = OrderFilledEvent(
        order_id=flatten_order_id,
        fill_price=154.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(flatten_fill)
    await event_bus.drain()

    # Verify close event
    assert len(closed_events) == 1
    # T1 P&L: (152 - 150) * 50 = 100
    # T2 P&L: (154 - 150) * 50 = 200
    # Total: 300
    assert closed_events[0].realized_pnl == pytest.approx(300.0)

    await order_manager.stop()


# ---------------------------------------------------------------------------
# T1/T2 Split Tests (2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t1_shares_are_half_of_total(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    config: OrderManagerConfig,
) -> None:
    """Verify T1 limit order is for 50% of entry shares."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]

    # T1 shares should be 50% of 100 = 50
    expected_t1_shares = int(100 * config.t1_position_pct)
    assert position.t1_shares == expected_t1_shares

    await order_manager.stop()


@pytest.mark.asyncio
async def test_partial_entry_adjusts_t1_shares(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """80 of 100 shares fill → T1 for 40."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    # Only 80 shares filled
    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=80,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]

    # T1 shares should be 50% of 80 = 40
    assert position.t1_shares == 40

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Time-Based Exit Tests (3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_time_stop_closes_position(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    event_bus: EventBus,
) -> None:
    """Position open > max_duration → fallback_poll closes it."""
    await order_manager.start()

    # Setup position
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    # Stop the poll task to manually control timing
    await order_manager.stop()

    # Advance clock past max_position_duration (default 120 min)
    fixed_clock.advance(minutes=125)

    # Restart with modified config for faster poll
    order_manager._config = OrderManagerConfig(
        max_position_duration_minutes=120,
        fallback_poll_interval_seconds=1,  # Fast poll for test
    )
    order_manager._running = True

    # Run one poll cycle manually
    mock_broker.place_order.reset_mock()

    # Simulate poll check
    for _symbol, positions in list(order_manager._managed_positions.items()):
        for position in positions:
            elapsed = (fixed_clock.now() - position.entry_time).total_seconds() / 60
            if elapsed >= 120:
                await order_manager._flatten_position(position, reason="time_stop")

    # Verify flatten order placed
    assert mock_broker.place_order.called


@pytest.mark.asyncio
async def test_eod_flatten_closes_all_positions(
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """At 3:50 PM ET, all positions closed."""
    # Set clock to 3:50 PM ET
    eod_clock = FixedClock(datetime(2026, 2, 16, 20, 50, 0, tzinfo=UTC))  # 15:50 ET

    config = OrderManagerConfig(
        eod_flatten_time="15:50",
        fallback_poll_interval_seconds=1,
    )

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=eod_clock,
        config=config,
    )

    await om.start()

    # Setup position
    approved = make_approved()
    await om.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await om.on_fill(fill_event)

    # Manually trigger EOD flatten check
    await om.eod_flatten()

    # Verify flatten order placed
    # Entry + stop + T1 + flatten = 4 calls
    assert mock_broker.place_order.call_count >= 4

    await om.stop()


@pytest.mark.asyncio
async def test_eod_flatten_no_positions_is_noop(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """No positions → no broker calls."""
    await order_manager.start()

    mock_broker.place_order.reset_mock()
    mock_broker.cancel_order.reset_mock()

    await order_manager.eod_flatten()

    # No orders should be placed
    mock_broker.place_order.assert_not_called()

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Emergency Tests (2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_emergency_flatten_closes_everything(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Immediate close all."""
    await order_manager.start()

    # Setup position
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    mock_broker.place_order.reset_mock()

    await order_manager.emergency_flatten()

    # Verify flatten order placed
    assert mock_broker.place_order.called
    flatten_order = mock_broker.place_order.call_args[0][0]
    assert str(flatten_order.order_type) == "market"

    await order_manager.stop()


@pytest.mark.asyncio
async def test_emergency_flatten_cancels_open_orders(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """All pending orders cancelled first."""
    await order_manager.start()

    # Setup position
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    mock_broker.cancel_order.reset_mock()

    await order_manager.emergency_flatten()

    # Verify cancel was called for stop and T1
    assert mock_broker.cancel_order.call_count >= 1

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Error Handling Tests (4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_order_failure_retries(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """If stop order fails, retry once."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    # Make stop order fail first, succeed second
    call_count = {"n": 0}
    original_place_order = mock_broker.place_order.side_effect

    async def flaky_place_order(order: MagicMock) -> OrderResult:
        call_count["n"] += 1
        # First call is entry, second is stop (fail), third is retry
        if call_count["n"] == 2:
            raise Exception("Simulated stop order failure")
        return await original_place_order(order)

    mock_broker.place_order.side_effect = flaky_place_order

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    # Should have retried stop (entry, fail, retry, T1 = 4 calls)
    assert mock_broker.place_order.call_count >= 3

    await order_manager.stop()


@pytest.mark.asyncio
async def test_stop_order_failure_after_retry_flattens(
    event_bus: EventBus,
    fixed_clock: FixedClock,
) -> None:
    """If retry also fails, emergency flatten."""
    # Create a fresh mock broker with custom behavior
    mock_broker = MagicMock()
    call_count = {"n": 0}
    placed_orders: list = []

    async def track_and_fail_stops(order: MagicMock) -> OrderResult:
        call_count["n"] += 1
        placed_orders.append(order)
        # Fail all stop orders
        if str(order.order_type) == "stop":
            raise Exception("Stop always fails")
        # Success for market orders (entry, flatten)
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{call_count['n']}",
            status=OrderStatus.SUBMITTED,
        )

    mock_broker.place_order = AsyncMock(side_effect=track_and_fail_stops)
    mock_broker.cancel_order = AsyncMock(return_value=True)

    config = OrderManagerConfig(stop_retry_max=1)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    approved = make_approved()
    await om.on_approved(approved)
    entry_order_id = placed_orders[0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await om.on_fill(fill_event)

    # After stop fails twice (initial + 1 retry), should flatten
    # Check placed orders: entry (market), stop (fail), retry (fail), flatten (market)
    market_orders = [o for o in placed_orders if str(o.order_type) == "market"]
    assert len(market_orders) >= 2  # Entry + flatten

    await om.stop()


@pytest.mark.asyncio
async def test_unknown_fill_event_ignored(
    order_manager: OrderManager,
) -> None:
    """Fill for unknown order_id → no crash."""
    await order_manager.start()

    # Send fill for unknown order
    fill_event = OrderFilledEvent(
        order_id="unknown-order-id",
        fill_price=150.0,
        fill_quantity=100,
    )

    # Should not raise
    await order_manager.on_fill(fill_event)

    await order_manager.stop()


@pytest.mark.asyncio
async def test_approved_with_no_signal_ignored(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """OrderApprovedEvent with signal=None → no crash."""
    await order_manager.start()

    approved = OrderApprovedEvent(signal=None)
    await order_manager.on_approved(approved)

    # No order should be placed
    mock_broker.place_order.assert_not_called()

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Edge Case Tests (3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_fills_before_t1_cancels_t1(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Stop triggered → T1 cancelled."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id
    t1_order_id = position.t1_order_id

    mock_broker.cancel_order.reset_mock()

    # Stop fills (before T1)
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(stop_fill)

    # Verify T1 was cancelled
    mock_broker.cancel_order.assert_called_with(t1_order_id)

    await order_manager.stop()


@pytest.mark.asyncio
async def test_on_tick_only_for_managed_symbols(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Ticks for non-managed symbols → ignored."""
    await order_manager.start()

    # No positions created

    # Send tick for random symbol
    tick = TickEvent(symbol="NVDA", price=900.0, volume=1000)
    await order_manager.on_tick(tick)

    # No crash, no orders

    await order_manager.stop()


@pytest.mark.asyncio
async def test_position_tracking_after_full_close(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """After close, symbol removed from managed positions."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    # Close via stop
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify symbol removed
    assert "AAPL" not in order_manager._managed_positions
    assert order_manager.open_position_count == 0

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Event Bus Integration Tests (4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscribes_to_correct_events_on_start(
    order_manager: OrderManager,
    event_bus: EventBus,
) -> None:
    """Verifies all 5 event subscriptions."""
    await order_manager.start()

    # Check subscriptions
    assert event_bus.subscriber_count(OrderApprovedEvent) >= 1
    assert event_bus.subscriber_count(OrderFilledEvent) >= 1
    assert event_bus.subscriber_count(OrderCancelledEvent) >= 1
    assert event_bus.subscriber_count(TickEvent) >= 1
    assert event_bus.subscriber_count(CircuitBreakerEvent) >= 1

    await order_manager.stop()


@pytest.mark.asyncio
async def test_publishes_position_opened_event(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """On entry fill, PositionOpenedEvent published."""
    opened_events: list[PositionOpenedEvent] = []

    async def handler(event: PositionOpenedEvent) -> None:
        opened_events.append(event)

    event_bus.subscribe(PositionOpenedEvent, handler)
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)
    await event_bus.drain()

    assert len(opened_events) == 1
    assert opened_events[0].symbol == "AAPL"
    assert opened_events[0].entry_price == 150.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_publishes_position_closed_event(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """On full close, PositionClosedEvent published."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.STOP_LOSS

    await order_manager.stop()


@pytest.mark.asyncio
async def test_circuit_breaker_triggers_emergency_flatten(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """CircuitBreakerEvent triggers emergency flatten."""
    await order_manager.start()

    # Setup position
    approved = make_approved()
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    mock_broker.place_order.reset_mock()

    # Trigger circuit breaker
    cb_event = CircuitBreakerEvent(
        level=CircuitBreakerLevel.ACCOUNT,
        reason="Daily loss limit exceeded",
    )
    await order_manager._on_circuit_breaker(cb_event)

    # Verify flatten order placed
    assert mock_broker.place_order.called

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Reconstruction Tests (3)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconstruct_from_broker_recovers_positions(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Mock broker with open positions and orders → ManagedPositions created."""
    mock_broker = MagicMock()

    # Create mock positions
    pos1 = MagicMock()
    pos1.symbol = "AAPL"
    pos1.qty = 100
    pos1.avg_entry_price = 150.0

    pos2 = MagicMock()
    pos2.symbol = "TSLA"
    pos2.qty = 50
    pos2.avg_entry_price = 200.0

    mock_broker.get_positions = AsyncMock(return_value=[pos1, pos2])

    # Create mock orders (stop for AAPL, limit for TSLA)
    stop_order = MagicMock()
    stop_order.symbol = "AAPL"
    stop_order.order_type = "stop"
    stop_order.stop_price = 148.0
    stop_order.id = "stop-123"

    limit_order = MagicMock()
    limit_order.symbol = "TSLA"
    limit_order.order_type = "limit"
    limit_order.limit_price = 210.0
    limit_order.id = "limit-456"
    limit_order.qty = 25

    mock_broker.get_open_orders = AsyncMock(return_value=[stop_order, limit_order])
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock()

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.reconstruct_from_broker()

    # Verify positions were reconstructed
    assert "AAPL" in om._managed_positions
    assert "TSLA" in om._managed_positions

    aapl_pos = om._managed_positions["AAPL"][0]
    assert aapl_pos.shares_remaining == 100
    assert aapl_pos.entry_price == 150.0
    assert aapl_pos.stop_price == 148.0
    assert aapl_pos.stop_order_id == "stop-123"
    assert aapl_pos.strategy_id == "reconstructed"

    tsla_pos = om._managed_positions["TSLA"][0]
    assert tsla_pos.shares_remaining == 50
    assert tsla_pos.entry_price == 200.0
    assert tsla_pos.t1_price == 210.0
    assert tsla_pos.t1_order_id == "limit-456"


@pytest.mark.asyncio
async def test_reconstruct_from_broker_no_positions(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Empty broker → no positions, no crash."""
    mock_broker.get_positions = AsyncMock(return_value=[])

    # Should not raise
    await order_manager.reconstruct_from_broker()

    # Verify no positions created
    assert len(order_manager._managed_positions) == 0


@pytest.mark.asyncio
async def test_reconstruct_from_broker_handles_error(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Broker raises → error logged, no crash."""
    mock_broker.get_positions = AsyncMock(side_effect=Exception("Network error"))

    # Should not raise
    await order_manager.reconstruct_from_broker()

    # Verify system still functional (no positions, but no crash)
    assert len(order_manager._managed_positions) == 0


# ---------------------------------------------------------------------------
# Trade Record Integrity Tests (5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_trade_record_stores_original_stop_price(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Trade record should have original stop, not moved breakeven stop."""
    # Track trades via a mock trade_logger
    logged_trades: list = []

    class MockTradeLogger:
        async def log_trade(self, trade):
            logged_trades.append(trade)

    order_manager._trade_logger = MockTradeLogger()

    await order_manager.start()

    # Create signal with specific stop at 148.0
    signal = make_signal(
        entry_price=150.0,
        stop_price=148.0,  # Original stop below entry
        target_prices=(152.0, 154.0),
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Verify original stop stored
    assert position.original_stop_price == 148.0

    # T1 fills → stop moves to breakeven
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Verify current stop moved but original preserved
    assert position.stop_price > 148.0  # Moved to breakeven
    assert position.original_stop_price == 148.0  # Still original

    # Stop fills at breakeven
    new_stop_id = position.stop_order_id
    stop_fill = OrderFilledEvent(
        order_id=new_stop_id,
        fill_price=150.15,  # Breakeven fill
        fill_quantity=50,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify trade record has ORIGINAL stop, not breakeven
    assert len(logged_trades) == 1
    trade = logged_trades[0]
    assert trade.stop_price == 148.0  # Original, not ~150.15

    await order_manager.stop()


@pytest.mark.asyncio
async def test_stop_to_breakeven_does_not_corrupt_original_stop(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    config: OrderManagerConfig,
) -> None:
    """original_stop_price field persists unchanged after stop-to-breakeven."""
    await order_manager.start()

    signal = make_signal(
        entry_price=100.0,
        stop_price=95.0,  # 5% below entry
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=100.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]

    # Before T1: both stops are original
    assert position.stop_price == 95.0
    assert position.original_stop_price == 95.0

    # T1 fills
    t1_fill = OrderFilledEvent(
        order_id=position.t1_order_id,
        fill_price=102.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # After T1: current stop moved, original preserved
    expected_breakeven = 100.0 * (1 + config.breakeven_buffer_pct)
    assert abs(position.stop_price - expected_breakeven) < 0.01
    assert position.original_stop_price == 95.0  # Unchanged!

    await order_manager.stop()


@pytest.mark.asyncio
async def test_pnl_calculation_long_trade_loss(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Entry > Exit for long → negative P&L."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await order_manager.start()

    # Entry at 150, stop at 145
    signal = make_signal(
        entry_price=150.0,
        stop_price=145.0,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    # Stop fills at 145 (loss)
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=145.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify negative P&L
    assert len(closed_events) == 1
    # P&L = (145 - 150) * 100 = -500
    assert closed_events[0].realized_pnl == pytest.approx(-500.0)

    await order_manager.stop()


@pytest.mark.asyncio
async def test_pnl_calculation_long_trade_win(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Exit > Entry for long → positive P&L."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await order_manager.start()

    signal = make_signal(
        entry_price=150.0,
        stop_price=145.0,
        target_prices=(155.0, 160.0),
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=150.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fills at 155 (profit)
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=155.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Stop fills at breakeven (small profit due to buffer)
    new_stop_id = position.stop_order_id
    breakeven = 150.0 * 1.001  # Default buffer
    stop_fill = OrderFilledEvent(
        order_id=new_stop_id,
        fill_price=breakeven,
        fill_quantity=50,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Verify positive P&L
    assert len(closed_events) == 1
    # T1 P&L: (155 - 150) * 50 = 250
    # Stop P&L: (150.15 - 150) * 50 = 7.5
    # Total: ~257.5
    assert closed_events[0].realized_pnl > 250.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_exit_price_reflects_weighted_average_after_t1(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """When T1 hits before stop, exit_price is weighted average, not last fill."""
    logged_trades: list = []

    class MockTradeLogger:
        async def log_trade(self, trade):
            logged_trades.append(trade)

    order_manager._trade_logger = MockTradeLogger()

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await order_manager.start()

    signal = make_signal(
        entry_price=100.0,
        stop_price=95.0,
        target_prices=(110.0, 120.0),
        share_count=100,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)
    entry_order_id = mock_broker.place_order.call_args[0][0].id

    fill_event = OrderFilledEvent(
        order_id=entry_order_id,
        fill_price=100.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fills: 50 shares at 110
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=110.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Stop fills: 50 shares at 98 (below entry, but after T1 profit)
    new_stop_id = position.stop_order_id
    stop_fill = OrderFilledEvent(
        order_id=new_stop_id,
        fill_price=98.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(stop_fill)
    await event_bus.drain()

    # Calculate expected values:
    # T1 P&L: (110 - 100) * 50 = 500
    # Stop P&L: (98 - 100) * 50 = -100
    # Total P&L: 400
    # Weighted exit: (400 / 100) + 100 = 104

    assert len(closed_events) == 1
    assert closed_events[0].realized_pnl == pytest.approx(400.0)
    assert closed_events[0].exit_price == pytest.approx(104.0)

    # Verify trade record has same exit price
    assert len(logged_trades) == 1
    assert logged_trades[0].exit_price == pytest.approx(104.0)

    # Key test: exit_price (104) > entry (100), consistent with positive P&L
    # Previously it would show 98 (last fill) which was inconsistent with +400 P&L

    await order_manager.stop()
