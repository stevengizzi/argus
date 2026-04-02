"""Tests for Order Manager.

All broker calls are mocked. No network calls.
Uses FixedClock for deterministic time control.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
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
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    """Create an Event Bus for testing."""
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
    """Create a mock Broker with place_bracket_order() support (DEC-117)."""
    broker = MagicMock()
    order_counter = {"count": 0}

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["count"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['count']}",
            status=OrderStatus.SUBMITTED,
        )

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with order IDs for all components."""
        order_counter["count"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['count']}",
            status=OrderStatus.FILLED,  # SimulatedBroker fills entry synchronously
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,  # Default fill price for tests
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
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    broker.place_order = AsyncMock(side_effect=make_order_result)
    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
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
async def test_submit_signal_places_bracket_order(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """OrderApprovedEvent → bracket order submitted to broker (DEC-117)."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    # Verify broker.place_bracket_order was called (not place_order)
    mock_broker.place_bracket_order.assert_called_once()
    entry, stop, targets = mock_broker.place_bracket_order.call_args[0]

    # Verify entry order
    assert entry.symbol == "AAPL"
    assert entry.quantity == 100
    assert str(entry.order_type) == "market"

    # Verify stop order
    assert stop.symbol == "AAPL"
    assert stop.quantity == 100
    assert str(stop.order_type) == "stop"
    assert stop.stop_price == 148.0

    # Verify targets (T1 and T2)
    assert len(targets) == 2
    assert targets[0].quantity == 50  # T1: 50% of 100
    assert targets[0].limit_price == 152.0
    assert targets[1].quantity == 50  # T2: remaining 50%
    assert targets[1].limit_price == 154.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_entry_fill_creates_managed_position(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Fill event → ManagedPosition created with bracket order IDs (DEC-117)."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    # Entry is handled synchronously via bracket_result.entry.status == FILLED
    # Position should already be created

    # Verify position was created
    assert "AAPL" in order_manager._managed_positions
    positions = order_manager._managed_positions["AAPL"]
    assert len(positions) == 1
    assert positions[0].entry_price == 150.0
    assert positions[0].shares_total == 100
    assert positions[0].shares_remaining == 100

    # Verify bracket order IDs are set on position (DEC-117)
    assert positions[0].stop_order_id is not None
    assert positions[0].t1_order_id is not None
    assert positions[0].t2_order_id is not None

    # No separate place_order calls for stop/T1/T2 — they're in the bracket
    assert mock_broker.place_order.call_count == 0
    assert mock_broker.place_bracket_order.call_count == 1

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t1_fill_moves_stop_to_breakeven(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    config: OrderManagerConfig,
) -> None:
    """T1 fill → old stop cancelled, new stop at entry + buffer."""
    await order_manager.start()

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Verify new stop order placed via place_order (stop-to-breakeven)
    assert mock_broker.place_order.call_count == 1
    new_stop_order = mock_broker.place_order.call_args[0][0]
    assert str(new_stop_order.order_type) == "stop"
    assert abs(new_stop_order.stop_price - expected_breakeven) < 0.01

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t2_reached_closes_remaining(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Tick at/above T2 → remaining shares closed (when no broker-side T2)."""
    await order_manager.start()

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Simulate T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Clear t2_order_id to simulate Alpaca path (no broker-side T2 order)
    # This tests the tick-based T2 monitoring fallback
    position.t2_order_id = None

    # Reset mock to track new calls (place_order was called for stop-to-breakeven)
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Clear T2 order ID to test tick-based T2 monitoring
    position.t2_order_id = None

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = order_manager._managed_positions["AAPL"][0]

    # T1 shares should be 50% of 100 = 50
    expected_t1_shares = int(100 * config.t1_position_pct)
    assert position.t1_shares == expected_t1_shares

    # Verify T1 order in bracket has correct quantity
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert targets[0].quantity == expected_t1_shares

    await order_manager.stop()


@pytest.mark.asyncio
async def test_partial_entry_adjusts_t1_shares(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """80 of 100 shares fill → T1 for 40."""
    # Create a custom mock broker that returns partial fill
    mock_broker = MagicMock()
    order_counter = {"count": 0}

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["count"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['count']}",
            status=OrderStatus.SUBMITTED,
        )

    def make_partial_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with partial entry fill (80 shares)."""
        order_counter["count"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['count']}",
            status=OrderStatus.FILLED,
            filled_quantity=80,  # Partial fill
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
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    mock_broker.place_order = AsyncMock(side_effect=make_order_result)
    mock_broker.place_bracket_order = AsyncMock(side_effect=make_partial_bracket_result)
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    approved = make_approved()
    await om.on_approved(approved)

    # Position created with 80 shares (partial fill)
    position = om._managed_positions["AAPL"][0]

    # T1 shares should be 50% of 80 = 40
    assert position.t1_shares == 40

    await om.stop()


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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await om.on_approved(approved)

    # Position created via synchronous fill from bracket result

    # Manually trigger EOD flatten check
    await om.eod_flatten()

    # Verify flatten order placed via place_order (not bracket)
    # Bracket order submitted first, then flatten order
    assert mock_broker.place_bracket_order.call_count == 1
    assert mock_broker.place_order.call_count >= 1  # Flatten order

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result

    mock_broker.cancel_order.reset_mock()

    await order_manager.emergency_flatten()

    # Verify cancel was called for stop and T1 (and T2)
    assert mock_broker.cancel_order.call_count >= 1

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Error Handling Tests (4)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_to_breakeven_failure_retries(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """If stop-to-breakeven order fails, retry once (DEC-117)."""
    await order_manager.start()

    # Setup position via bracket order
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Make stop order fail first, succeed second (for stop-to-breakeven)
    call_count = {"n": 0}
    original_place_order = mock_broker.place_order.side_effect

    async def flaky_place_order(order: MagicMock) -> OrderResult:
        call_count["n"] += 1
        # First call is stop-to-breakeven (fail), second is retry
        if call_count["n"] == 1:
            raise Exception("Simulated stop order failure")
        return await original_place_order(order)

    mock_broker.place_order.side_effect = flaky_place_order

    # T1 fill triggers stop-to-breakeven
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Should have retried stop (fail, retry = 2 calls)
    assert mock_broker.place_order.call_count >= 2

    await order_manager.stop()


@pytest.mark.asyncio
async def test_stop_to_breakeven_failure_after_retry_flattens(
    event_bus: EventBus,
    fixed_clock: FixedClock,
) -> None:
    """If stop-to-breakeven retry also fails, emergency flatten (DEC-117)."""
    # Create a fresh mock broker with custom behavior
    mock_broker = MagicMock()
    order_counter = {"n": 0}
    placed_orders: list = []

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with filled entry."""
        order_counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )

        order_counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['n']}",
            status=OrderStatus.PENDING,
        )

        target_results = []
        for target in targets:
            order_counter["n"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )

        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    async def track_and_fail_stops(order: MagicMock) -> OrderResult:
        order_counter["n"] += 1
        placed_orders.append(order)
        # Fail all stop orders (for stop-to-breakeven)
        if str(order.order_type) == "stop":
            raise Exception("Stop always fails")
        # Success for market orders (flatten)
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
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

    # Setup position via bracket order
    approved = make_approved()
    await om.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fill triggers stop-to-breakeven (which will fail)
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await om.on_fill(t1_fill)

    # After stop-to-breakeven fails twice (initial + 1 retry), should flatten
    # Check placed orders: stop (fail), retry (fail), flatten (market)
    market_orders = [o for o in placed_orders if str(o.order_type) == "market"]
    assert len(market_orders) >= 1  # Flatten

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Verify T1 was cancelled (T2 also cancelled now with DEC-093)
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert t1_order_id in cancel_calls

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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)
    await event_bus.drain()

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result

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

    # Create mock positions (use `shares` — the Position model attribute)
    pos1 = MagicMock()
    pos1.symbol = "AAPL"
    pos1.shares = 100
    pos1.avg_entry_price = 150.0

    pos2 = MagicMock()
    pos2.symbol = "TSLA"
    pos2.shares = 50
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

    # Verify positions were reconstructed (both have associated orders)
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
# Startup Zombie Cleanup Tests (Sprint 27.95 S4 + S5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_startup_flatten_unknown_positions_enabled(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Unknown IBKR positions flattened when flatten_unknown_positions=True."""
    mock_broker = MagicMock()

    zombie = MagicMock()
    zombie.symbol = "ZOMBIE"
    zombie.shares = 75
    zombie.avg_entry_price = 42.0

    mock_broker.get_positions = AsyncMock(return_value=[zombie])
    mock_broker.get_open_orders = AsyncMock(return_value=[])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=True)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    await om.reconstruct_from_broker()

    # Verify sell order was placed
    mock_broker.place_order.assert_called_once()
    sell_order = mock_broker.place_order.call_args[0][0]
    assert sell_order.symbol == "ZOMBIE"
    assert sell_order.side.value == "sell"
    assert sell_order.quantity == 75

    # Verify NO managed position was created
    assert "ZOMBIE" not in om._managed_positions


@pytest.mark.asyncio
async def test_startup_flatten_unknown_positions_disabled(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Unknown IBKR positions logged as warnings when flatten disabled."""
    mock_broker = MagicMock()

    zombie = MagicMock()
    zombie.symbol = "ZOMBIE"
    zombie.shares = 75
    zombie.avg_entry_price = 42.0

    mock_broker.get_positions = AsyncMock(return_value=[zombie])
    mock_broker.get_open_orders = AsyncMock(return_value=[])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=False)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    await om.reconstruct_from_broker()

    # Verify NO sell order was placed
    mock_broker.place_order.assert_not_called()

    # Verify RECO position was created for UI visibility
    assert "ZOMBIE" in om._managed_positions
    assert om._managed_positions["ZOMBIE"][0].strategy_id == "reconstructed"


@pytest.mark.asyncio
async def test_startup_empty_ibkr_portfolio(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Empty IBKR portfolio → no action, no crash."""
    mock_broker = MagicMock()
    mock_broker.get_positions = AsyncMock(return_value=[])
    mock_broker.place_order = AsyncMock()

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.reconstruct_from_broker()

    mock_broker.place_order.assert_not_called()
    assert len(om._managed_positions) == 0


@pytest.mark.asyncio
async def test_startup_only_known_positions(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Position with associated orders → reconstruct, no flatten."""
    mock_broker = MagicMock()

    known = MagicMock()
    known.symbol = "AAPL"
    known.shares = 100
    known.avg_entry_price = 150.0

    # AAPL has a stop order → ARGUS was managing it
    stop_order = MagicMock()
    stop_order.symbol = "AAPL"
    stop_order.order_type = "stop"
    stop_order.stop_price = 148.0
    stop_order.id = "stop-abc"

    mock_broker.get_positions = AsyncMock(return_value=[known])
    mock_broker.get_open_orders = AsyncMock(return_value=[stop_order])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=True)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    await om.reconstruct_from_broker()

    # No sell order placed (position has orders → known/managed)
    mock_broker.place_order.assert_not_called()

    # Position was reconstructed
    assert len(om._managed_positions["AAPL"]) == 1
    assert om._managed_positions["AAPL"][0].entry_price == 150.0


@pytest.mark.asyncio
async def test_startup_mix_known_and_unknown(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Position with orders → reconstruct; position without orders → flatten."""
    mock_broker = MagicMock()

    known = MagicMock()
    known.symbol = "AAPL"
    known.shares = 100
    known.avg_entry_price = 150.0

    zombie = MagicMock()
    zombie.symbol = "ZOMBIE"
    zombie.shares = 50
    zombie.avg_entry_price = 30.0

    # Only AAPL has an associated order — ZOMBIE has none
    stop_order = MagicMock()
    stop_order.symbol = "AAPL"
    stop_order.order_type = "stop"
    stop_order.stop_price = 148.0
    stop_order.id = "stop-abc"

    mock_broker.get_positions = AsyncMock(return_value=[known, zombie])
    mock_broker.get_open_orders = AsyncMock(return_value=[stop_order])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=True)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    await om.reconstruct_from_broker()

    # ZOMBIE was flattened (no orders → zombie)
    mock_broker.place_order.assert_called_once()
    sell_order = mock_broker.place_order.call_args[0][0]
    assert sell_order.symbol == "ZOMBIE"

    # AAPL was reconstructed (has stop order → managed)
    assert len(om._managed_positions["AAPL"]) == 1
    assert om._managed_positions["AAPL"][0].entry_price == 150.0

    # ZOMBIE was NOT added as managed
    assert "ZOMBIE" not in om._managed_positions


@pytest.mark.asyncio
async def test_startup_portfolio_query_failure(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """IBKR portfolio query failure → graceful skip, no crash."""
    mock_broker = MagicMock()
    mock_broker.get_positions = AsyncMock(side_effect=ConnectionError("TWS offline"))
    mock_broker.place_order = AsyncMock()

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    # Should not raise
    await om.reconstruct_from_broker()

    mock_broker.place_order.assert_not_called()
    assert len(om._managed_positions) == 0


def test_startup_config_flatten_field() -> None:
    """StartupConfig recognizes flatten_unknown_positions field."""
    cfg = StartupConfig(flatten_unknown_positions=True)
    assert cfg.flatten_unknown_positions is True

    cfg_off = StartupConfig(flatten_unknown_positions=False)
    assert cfg_off.flatten_unknown_positions is False

    # Default is True
    cfg_default = StartupConfig()
    assert cfg_default.flatten_unknown_positions is True


@pytest.mark.asyncio
async def test_startup_real_sequence_position_with_orders_not_flattened(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Real startup: empty _managed_positions + position with orders → reconstruct."""
    mock_broker = MagicMock()

    # IBKR has a position with bracket orders (crash recovery scenario)
    pos = MagicMock()
    pos.symbol = "NVDA"
    pos.shares = 200
    pos.avg_entry_price = 120.0

    stop = MagicMock()
    stop.symbol = "NVDA"
    stop.order_type = "stop"
    stop.stop_price = 118.0
    stop.id = "stop-nvda"

    mock_broker.get_positions = AsyncMock(return_value=[pos])
    mock_broker.get_open_orders = AsyncMock(return_value=[stop])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=True)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    # _managed_positions is empty (real startup state)
    assert len(om._managed_positions) == 0

    await om.reconstruct_from_broker()

    # Position has orders → reconstructed, NOT flattened
    mock_broker.place_order.assert_not_called()
    assert "NVDA" in om._managed_positions
    assert om._managed_positions["NVDA"][0].entry_price == 120.0
    assert om._managed_positions["NVDA"][0].stop_price == 118.0


@pytest.mark.asyncio
async def test_startup_zero_qty_zombie_skips_flatten(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Zero-quantity zombie position skips flatten, emits DEBUG log."""
    mock_broker = MagicMock()

    ghost = MagicMock()
    ghost.symbol = "GHOST"
    ghost.shares = 0
    ghost.avg_entry_price = 50.0

    mock_broker.get_positions = AsyncMock(return_value=[ghost])
    mock_broker.get_open_orders = AsyncMock(return_value=[])
    mock_broker.place_order = AsyncMock()

    startup_cfg = StartupConfig(flatten_unknown_positions=True)
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        startup_config=startup_cfg,
    )

    await om.reconstruct_from_broker()

    # _flatten_unknown_position should NOT have been called
    mock_broker.place_order.assert_not_called()

    # No managed position created either
    assert "GHOST" not in om._managed_positions


def test_script_has_executable_permission() -> None:
    """ibkr_close_all_positions.py should have +x permission."""
    import os
    from pathlib import Path

    script_path = Path(__file__).parents[2] / "scripts" / "ibkr_close_all_positions.py"
    assert script_path.exists(), f"Script not found: {script_path}"
    assert os.access(script_path, os.X_OK), f"Script not executable: {script_path}"


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

    # Setup position via bracket order (DEC-117)
    signal = make_signal(
        entry_price=150.0,
        stop_price=148.0,  # Original stop below entry
        target_prices=(152.0, 154.0),
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """original_stop_price field persists unchanged after stop-to-breakeven."""
    # Create a custom mock broker with stop at 95.0
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["n"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with entry fill at 100.0."""
        order_counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=100.0,  # Fill at 100.0
        )

        order_counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['n']}",
            status=OrderStatus.PENDING,
        )

        target_results = []
        for target in targets:
            order_counter["n"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )

        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    mock_broker.place_order = AsyncMock(side_effect=make_order_result)
    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    signal = make_signal(
        entry_price=100.0,
        stop_price=95.0,  # 5% below entry
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = om._managed_positions["AAPL"][0]

    # Before T1: both stops are original
    assert position.stop_price == 95.0
    assert position.original_stop_price == 95.0

    # T1 fills
    t1_fill = OrderFilledEvent(
        order_id=position.t1_order_id,
        fill_price=102.0,
        fill_quantity=50,
    )
    await om.on_fill(t1_fill)

    # After T1: current stop moved, original preserved
    expected_breakeven = 100.0 * (1 + config.breakeven_buffer_pct)
    assert abs(position.stop_price - expected_breakeven) < 0.01
    assert position.original_stop_price == 95.0  # Unchanged!

    await om.stop()


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

    # Setup position via bracket order (DEC-117)
    signal = make_signal(
        entry_price=150.0,
        stop_price=145.0,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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

    # Setup position via bracket order (DEC-117)
    signal = make_signal(
        entry_price=150.0,
        stop_price=145.0,
        target_prices=(155.0, 160.0),
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Position created via synchronous fill from bracket result
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
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """When T1 hits before stop, exit_price is weighted average, not last fill."""
    # Create a custom mock broker with fill at 100.0
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["n"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with entry fill at 100.0."""
        order_counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=100.0,  # Fill at 100.0
        )

        order_counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['n']}",
            status=OrderStatus.PENDING,
        )

        target_results = []
        for target in targets:
            order_counter["n"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )

        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    mock_broker.place_order = AsyncMock(side_effect=make_order_result)
    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    logged_trades: list = []

    class MockTradeLogger:
        async def log_trade(self, trade):
            logged_trades.append(trade)

    om._trade_logger = MockTradeLogger()

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await om.start()

    signal = make_signal(
        entry_price=100.0,
        stop_price=95.0,
        target_prices=(110.0, 120.0),
        share_count=100,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    # Position created via synchronous fill from bracket result
    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fills: 50 shares at 110
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=110.0,
        fill_quantity=50,
    )
    await om.on_fill(t1_fill)

    # Stop fills: 50 shares at 98 (below entry, but after T1 profit)
    new_stop_id = position.stop_order_id
    stop_fill = OrderFilledEvent(
        order_id=new_stop_id,
        fill_price=98.0,
        fill_quantity=50,
    )
    await om.on_fill(stop_fill)
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

    await om.stop()


# ---------------------------------------------------------------------------
# Bracket Order Edge Case Tests (DEC-117) (8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bracket_entry_rejected(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Broker rejects entry → stop/targets not tracked."""
    mock_broker = MagicMock()

    async def fail_bracket_order(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        raise Exception("Insufficient buying power")

    mock_broker.place_bracket_order = AsyncMock(side_effect=fail_bracket_order)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock()

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    approved = make_approved()
    await om.on_approved(approved)

    # Verify no position created
    assert len(om._managed_positions) == 0

    # Verify no pending orders
    assert len(om._pending_orders) == 0

    # No orders should have been placed
    mock_broker.place_order.assert_not_called()

    await om.stop()


@pytest.mark.asyncio
async def test_bracket_with_t1_only_no_t2(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single target signal → bracket with T1 only, no T2."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        """Create a BracketOrderResult with only T1."""
        order_counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )

        order_counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['n']}",
            status=OrderStatus.PENDING,
        )

        target_results = []
        for target in targets:
            order_counter["n"] += 1
            target_results.append(
                OrderResult(
                    order_id=target.id,
                    broker_order_id=f"broker-target-{order_counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )

        return BracketOrderResult(
            entry=entry_result,
            stop=stop_result,
            targets=target_results,
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Signal with only T1 (single target)
    signal = make_signal(
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),  # Only T1, no T2
        share_count=100,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    # Verify position created
    assert "AAPL" in om._managed_positions
    position = om._managed_positions["AAPL"][0]

    # Verify T1 is set, T2 is not
    assert position.t1_price == 152.0
    assert position.t1_order_id is not None
    assert position.t2_price == 0.0
    assert position.t2_order_id is None

    # Verify bracket call had 1 target
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert len(targets) == 1

    await om.stop()


@pytest.mark.asyncio
async def test_bracket_with_t1_and_t2(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Dual target signal → bracket with both T1 and T2."""
    await order_manager.start()

    # Standard signal with T1 and T2
    signal = make_signal(
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),  # Both T1 and T2
        share_count=100,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Verify position created
    assert "AAPL" in order_manager._managed_positions
    position = order_manager._managed_positions["AAPL"][0]

    # Verify both T1 and T2 are set
    assert position.t1_price == 152.0
    assert position.t1_order_id is not None
    assert position.t2_price == 154.0
    assert position.t2_order_id is not None

    # Verify bracket call had 2 targets
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert len(targets) == 2
    assert targets[0].limit_price == 152.0
    assert targets[1].limit_price == 154.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_bracket_stop_to_breakeven_after_t1_fill(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    config: OrderManagerConfig,
) -> None:
    """T1 fill → old stop cancelled, new stop at breakeven via place_order()."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]
    original_stop_id = position.stop_order_id
    t1_order_id = position.t1_order_id

    # Track cancel calls
    mock_broker.cancel_order.reset_mock()
    mock_broker.place_order.reset_mock()

    # Simulate T1 fill
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await order_manager.on_fill(t1_fill)

    # Verify old stop was cancelled
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert original_stop_id in cancel_calls

    # Verify new stop order placed via place_order (not bracket)
    assert mock_broker.place_order.called
    new_stop_order = mock_broker.place_order.call_args[0][0]
    assert str(new_stop_order.order_type) == "stop"

    # Verify new stop is at breakeven
    expected_breakeven = 150.0 * (1 + config.breakeven_buffer_pct)
    assert abs(new_stop_order.stop_price - expected_breakeven) < 0.01

    # Verify position has new stop ID
    assert position.stop_order_id != original_stop_id
    assert position.stop_order_id is not None

    await order_manager.stop()


@pytest.mark.asyncio
async def test_bracket_stop_cancelled_resubmit(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Stop order cancelled by broker → resubmit via on_cancel handler."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    # Reset mock to track new calls
    mock_broker.place_order.reset_mock()

    # Simulate broker cancelling the stop order
    cancel_event = OrderCancelledEvent(
        order_id=stop_order_id,
        reason="Broker rejected order",
    )
    await order_manager.on_cancel(cancel_event)

    # Verify stop was resubmitted
    assert mock_broker.place_order.called
    resubmit_order = mock_broker.place_order.call_args[0][0]
    assert str(resubmit_order.order_type) == "stop"
    assert resubmit_order.stop_price == position.stop_price

    await order_manager.stop()


@pytest.mark.asyncio
async def test_bracket_order_ids_on_managed_position(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Verify all bracket order IDs are correctly propagated to ManagedPosition."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    # Get bracket result from mock
    bracket_call_args = mock_broker.place_bracket_order.call_args[0]
    entry, stop, targets = bracket_call_args

    # Position should have IDs from bracket result
    position = order_manager._managed_positions["AAPL"][0]

    # Entry order ID is tracked in pending initially, then position is created
    # Stop and target IDs should be on position
    assert position.stop_order_id == stop.id
    assert position.t1_order_id == targets[0].id
    assert position.t2_order_id == targets[1].id if len(targets) > 1 else True

    # Verify pending orders also track these IDs
    assert stop.id in order_manager._pending_orders
    assert targets[0].id in order_manager._pending_orders
    if len(targets) > 1:
        assert targets[1].id in order_manager._pending_orders

    await order_manager.stop()


@pytest.mark.asyncio
async def test_bracket_with_simulated_broker_sync_fill(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Entry fills immediately (sync) → position created with bracket IDs."""
    opened_events: list[PositionOpenedEvent] = []

    async def handler(event: PositionOpenedEvent) -> None:
        opened_events.append(event)

    event_bus.subscribe(PositionOpenedEvent, handler)

    await order_manager.start()

    # The mock broker returns FILLED status for entry (simulating sync fill)
    approved = make_approved()
    await order_manager.on_approved(approved)
    await event_bus.drain()

    # Position should be created immediately (not waiting for fill event)
    assert "AAPL" in order_manager._managed_positions
    position = order_manager._managed_positions["AAPL"][0]

    # Verify entry price from bracket result
    assert position.entry_price == 150.0  # From mock bracket result
    assert position.shares_total == 100

    # Verify bracket IDs are set
    assert position.stop_order_id is not None
    assert position.t1_order_id is not None
    assert position.t2_order_id is not None

    # Verify PositionOpenedEvent was published
    assert len(opened_events) == 1
    assert opened_events[0].symbol == "AAPL"

    await order_manager.stop()


@pytest.mark.asyncio
async def test_bracket_flatten_cancels_bracket_orders(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Emergency flatten cancels stop + T1 + T2 orders from bracket."""
    await order_manager.start()

    approved = make_approved()
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id
    t1_order_id = position.t1_order_id
    t2_order_id = position.t2_order_id

    # Reset mock to track cancel calls
    mock_broker.cancel_order.reset_mock()

    await order_manager.emergency_flatten()

    # Verify all bracket orders were cancelled
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert stop_order_id in cancel_calls
    assert t1_order_id in cancel_calls
    assert t2_order_id in cancel_calls

    # Verify flatten market order placed
    assert mock_broker.place_order.called

    await order_manager.stop()


# ---------------------------------------------------------------------------
# Per-Signal Time Stop Tests (DEC-122) (5)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_signal_time_stop_120_seconds(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    event_bus: EventBus,
) -> None:
    """Position with time_stop_seconds=120 flattened after 120s (DEC-122)."""
    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    await order_manager.start()

    # Create signal with 120 second time stop
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Scalp signal",
        time_stop_seconds=120,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Position created
    position = order_manager._managed_positions["AAPL"][0]
    assert position.time_stop_seconds == 120

    # Stop the poll task to manually control timing
    await order_manager.stop()

    # Advance clock by 120 seconds
    fixed_clock.advance(seconds=120)

    # Reset mock and manually trigger time stop check
    mock_broker.place_order.reset_mock()
    order_manager._running = True

    # Simulate poll check
    now = fixed_clock.now()
    for _symbol, positions in list(order_manager._managed_positions.items()):
        for pos in positions:
            if pos.is_fully_closed:
                continue
            elapsed_seconds = (now - pos.entry_time).total_seconds()
            if pos.time_stop_seconds is not None and elapsed_seconds >= pos.time_stop_seconds:
                await order_manager._flatten_position(pos, reason="time_stop")

    # Verify flatten order placed
    assert mock_broker.place_order.called


@pytest.mark.asyncio
async def test_per_signal_time_stop_30_seconds(
    event_bus: EventBus,
    config: OrderManagerConfig,
) -> None:
    """Position with time_stop_seconds=30 flattened after 30s (DEC-122)."""
    fixed_clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        order_counter["n"] += 1
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['n']}",
            status=OrderStatus.PENDING,
        )
        target_results = [
            OrderResult(
                order_id=t.id,
                broker_order_id=f"broker-target-{order_counter['n'] + i}",
                status=OrderStatus.PENDING,
            )
            for i, t in enumerate(targets)
        ]
        return BracketOrderResult(entry=entry_result, stop=stop_result, targets=target_results)

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        return_value=OrderResult(order_id="test", broker_order_id="b", status=OrderStatus.SUBMITTED)
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create signal with 30 second time stop
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
        time_stop_seconds=30,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    assert position.time_stop_seconds == 30

    await om.stop()

    # Advance clock by 30 seconds
    fixed_clock.advance(seconds=30)

    # Manually trigger time stop check
    mock_broker.place_order.reset_mock()
    om._running = True

    now = fixed_clock.now()
    for _symbol, positions in list(om._managed_positions.items()):
        for pos in positions:
            if pos.is_fully_closed:
                continue
            elapsed_seconds = (now - pos.entry_time).total_seconds()
            if pos.time_stop_seconds is not None and elapsed_seconds >= pos.time_stop_seconds:
                await om._flatten_position(pos, reason="time_stop")

    # Verify flatten order placed
    assert mock_broker.place_order.called


@pytest.mark.asyncio
async def test_no_per_signal_time_stop_uses_global(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Position without time_stop_seconds uses global max_position_duration_minutes."""
    await order_manager.start()

    # Create signal WITHOUT time_stop_seconds
    signal = make_signal()
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]
    assert position.time_stop_seconds is None

    await order_manager.stop()

    # Advance clock by 30 seconds (less than global 120 min)
    fixed_clock.advance(seconds=30)
    mock_broker.place_order.reset_mock()
    order_manager._running = True

    # Verify time stop NOT triggered (30s < 120min)
    now = fixed_clock.now()
    triggered = False
    for _symbol, positions in list(order_manager._managed_positions.items()):
        for pos in positions:
            elapsed_seconds = (now - pos.entry_time).total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            if pos.time_stop_seconds is not None:
                if elapsed_seconds >= pos.time_stop_seconds:
                    triggered = True
            elif elapsed_minutes >= order_manager._config.max_position_duration_minutes:
                triggered = True

    assert not triggered

    # Now advance to 125 minutes (past global limit)
    fixed_clock.advance(minutes=124)  # 124 + (30s) > 120 min
    now = fixed_clock.now()
    for _symbol, positions in list(order_manager._managed_positions.items()):
        for pos in positions:
            elapsed_seconds = (now - pos.entry_time).total_seconds()
            elapsed_minutes = elapsed_seconds / 60
            if (
                pos.time_stop_seconds is None
                and elapsed_minutes >= order_manager._config.max_position_duration_minutes
            ):
                await order_manager._flatten_position(pos, reason="time_stop")

    # Now flatten should have been called
    assert mock_broker.place_order.called


@pytest.mark.asyncio
async def test_per_signal_time_stop_fires_before_t1(
    event_bus: EventBus,
    config: OrderManagerConfig,
) -> None:
    """Time stop fires before T1 is hit (DEC-122)."""
    fixed_clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        return_value=OrderResult(order_id="test", broker_order_id="b", status=OrderStatus.SUBMITTED)
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create signal with 60 second time stop
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Scalp signal",
        time_stop_seconds=60,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    assert not position.t1_filled

    await om.stop()

    # Advance clock by 60 seconds (time stop triggers before T1)
    fixed_clock.advance(seconds=60)

    # Trigger time stop
    now = fixed_clock.now()
    for _symbol, positions in list(om._managed_positions.items()):
        for pos in positions:
            if pos.time_stop_seconds is not None:
                elapsed_seconds = (now - pos.entry_time).total_seconds()
                if elapsed_seconds >= pos.time_stop_seconds:
                    await om._flatten_position(pos, reason="time_stop")

    # Verify T1 was NOT filled
    assert not position.t1_filled

    # Verify flatten order placed
    assert mock_broker.place_order.called


@pytest.mark.asyncio
async def test_t1_hit_before_time_stop(
    event_bus: EventBus,
    config: OrderManagerConfig,
) -> None:
    """T1 hit before time stop fires (DEC-122)."""
    fixed_clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    def make_order_result(order: MagicMock) -> OrderResult:
        order_counter["n"] += 1
        return OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(side_effect=make_order_result)
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create signal with 120 second time stop
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Scalp signal",
        time_stop_seconds=120,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Advance clock by 30 seconds (before time stop)
    fixed_clock.advance(seconds=30)

    # T1 fills
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=50,
    )
    await om.on_fill(t1_fill)

    # Verify T1 was filled
    assert position.t1_filled

    # Time stop would be at 120s, but T1 already hit at 30s
    # Verify position still open (remaining 50 shares)
    assert position.shares_remaining == 50
    assert not position.is_fully_closed

    await om.stop()


# ---------------------------------------------------------------------------
# Single-Target Bracket Tests (DEC-122) (10)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_target_bracket_has_one_limit(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Signal with 1 target → bracket has stop + 1 limit only (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),  # Single target
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    # Verify bracket call had 1 target only
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert len(targets) == 1
    assert targets[0].quantity == 100  # All shares to T1
    assert targets[0].limit_price == 152.0

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_t1_closes_100_percent(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """T1 fill on single-target closes 100% of position (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Verify T1 has all shares
    assert position.t1_shares == 100

    # T1 fill for all 100 shares
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=100,
    )
    await om.on_fill(t1_fill)
    await event_bus.drain()

    # Verify position fully closed
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.TARGET_1
    # P&L = (152 - 150) * 100 = 200
    assert closed_events[0].realized_pnl == pytest.approx(200.0)

    # Verify position removed
    assert "AAPL" not in om._managed_positions

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_no_t2_monitoring(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target positions skip T2 monitoring in on_tick (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]

    # Verify no T2 price
    assert position.t2_price == 0.0
    assert position.t2_order_id is None

    # Send tick at some price — no T2 flatten should happen
    mock_broker.place_order.reset_mock()
    tick = TickEvent(symbol="AAPL", price=160.0, volume=1000)
    await om.on_tick(tick)

    # No flatten order should be placed (T2 check skipped when t2_price == 0)
    # Note: trailing stop might trigger if enabled, but not T2
    # Since t1_filled is False, trailing stop also won't trigger
    # Only high_watermark update should happen
    assert position.high_watermark == 160.0

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_no_stop_to_breakeven(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target positions don't need stop-to-breakeven (T1 = 100%) (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id
    original_stop_id = position.stop_order_id

    # Reset mock to track new calls
    mock_broker.place_order.reset_mock()

    # T1 fill for all 100 shares
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=152.0,
        fill_quantity=100,
    )
    await om.on_fill(t1_fill)

    # Verify NO new stop order placed (no stop-to-breakeven needed)
    # Only cancel calls should happen
    mock_broker.place_order.assert_not_called()

    # Verify original stop was cancelled
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert original_stop_id in cancel_calls

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_position_t1_shares_equals_total(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target position has t1_shares == shares_total (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]

    # Verify T1 shares equals total
    assert position.t1_shares == position.shares_total == 100

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_pnl_calculation(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target P&L is (exit - entry) * 100% shares (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(153.0,),  # $3 profit target
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # T1 fill at $153
    t1_fill = OrderFilledEvent(
        order_id=t1_order_id,
        fill_price=153.0,
        fill_quantity=100,
    )
    await om.on_fill(t1_fill)
    await event_bus.drain()

    # Verify P&L = (153 - 150) * 100 = 300
    assert len(closed_events) == 1
    assert closed_events[0].realized_pnl == pytest.approx(300.0)
    assert closed_events[0].exit_price == pytest.approx(153.0)

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_stop_hit_closes_position(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target position stop hit closes 100% of position (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    # Stop hit at 148
    stop_fill = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await om.on_fill(stop_fill)
    await event_bus.drain()

    # Verify position closed
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.STOP_LOSS
    # P&L = (148 - 150) * 100 = -200
    assert closed_events[0].realized_pnl == pytest.approx(-200.0)

    await om.stop()


@pytest.mark.asyncio
async def test_single_target_time_stop_closes_position(
    event_bus: EventBus,
    config: OrderManagerConfig,
) -> None:
    """Single-target position time stop closes 100% of position (DEC-122)."""
    fixed_clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        return_value=OrderResult(order_id="test", broker_order_id="b", status=OrderStatus.SUBMITTED)
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal with 60 second time stop
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=100,
        rationale="Scalp signal",
        time_stop_seconds=60,
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]
    assert position.time_stop_seconds == 60

    await om.stop()

    # Advance clock by 60 seconds
    fixed_clock.advance(seconds=60)

    # Trigger time stop
    mock_broker.place_order.reset_mock()
    now = fixed_clock.now()
    for _symbol, positions in list(om._managed_positions.items()):
        for pos in positions:
            if pos.time_stop_seconds is not None:
                elapsed_seconds = (now - pos.entry_time).total_seconds()
                if elapsed_seconds >= pos.time_stop_seconds:
                    await om._flatten_position(pos, reason="time_stop")

    # Verify flatten order placed for 100 shares
    assert mock_broker.place_order.called
    flatten_order = mock_broker.place_order.call_args[0][0]
    assert flatten_order.quantity == 100
    assert str(flatten_order.order_type) == "market"


@pytest.mark.asyncio
async def test_dual_target_still_works_normally(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """Dual-target signals still work as before (regression test for DEC-122)."""
    await order_manager.start()

    # Standard dual-target signal
    signal = make_signal(
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
    )
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]

    # Verify dual-target behavior unchanged
    assert position.t1_shares == 50  # 50% of 100
    assert position.t1_price == 152.0
    assert position.t2_price == 154.0
    assert position.t2_order_id is not None

    # Verify bracket had 2 targets
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert len(targets) == 2

    await order_manager.stop()


@pytest.mark.asyncio
async def test_single_target_with_odd_share_count(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single-target with odd share count still works (DEC-122)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock(return_value=True)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Single target signal with odd share count
    signal = SignalEvent(
        strategy_id="orb_scalp",
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0,),
        share_count=77,  # Odd number
        rationale="Scalp signal",
    )
    approved = make_approved(signal=signal)
    await om.on_approved(approved)

    position = om._managed_positions["AAPL"][0]

    # Verify all 77 shares go to T1
    assert position.t1_shares == 77

    # Verify bracket T1 order has all 77 shares
    _, _, targets = mock_broker.place_bracket_order.call_args[0]
    assert len(targets) == 1
    assert targets[0].quantity == 77

    await om.stop()


# ---------------------------------------------------------------------------
# Flatten Fill Routing Tests (DEC-261 Bug 1 Fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_fill_routes_to_correct_strategy_when_multiple_positions(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Flatten fill routes to correct strategy when multiple positions exist on same symbol."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        side_effect=lambda order: OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-flatten-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create two positions on same symbol from different strategies
    signal_breakout = make_signal(
        symbol="AAPL",
        strategy_id="orb_breakout",
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
    )
    signal_scalp = make_signal(
        symbol="AAPL",
        strategy_id="orb_scalp",
        entry_price=151.0,
        stop_price=149.0,
        target_prices=(153.0,),
        share_count=50,
    )

    await om.on_approved(make_approved(signal=signal_breakout))
    await om.on_approved(make_approved(signal=signal_scalp))

    # Both positions should exist
    positions = om._managed_positions["AAPL"]
    assert len(positions) == 2
    breakout_pos = next(p for p in positions if p.strategy_id == "orb_breakout")
    scalp_pos = next(p for p in positions if p.strategy_id == "orb_scalp")

    # Flatten the scalp position
    await om._flatten_position(scalp_pos, reason="time_stop")

    # Find the pending flatten order
    pending_order = None
    for pending in om._pending_orders.values():
        if pending.order_type == "flatten" and pending.strategy_id == "orb_scalp":
            pending_order = pending
            break
    assert pending_order is not None

    # Simulate fill
    fill_event = OrderFilledEvent(
        order_id=pending_order.order_id,
        fill_price=150.5,
        fill_quantity=50,
    )
    await om.on_fill(fill_event)
    await event_bus.drain()

    # Verify scalp position closed, breakout position still open
    assert len(closed_events) == 1
    assert closed_events[0].strategy_id == "orb_scalp"
    assert breakout_pos.shares_remaining == 100  # Still open

    await om.stop()


@pytest.mark.asyncio
async def test_flatten_fill_fallback_when_strategy_id_not_found(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Flatten fill falls back to first open position when strategy_id doesn't match."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        side_effect=lambda order: OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-flatten-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create a position
    signal = make_signal(
        symbol="AAPL",
        strategy_id="orb_breakout",
        share_count=100,
    )
    await om.on_approved(make_approved(signal=signal))

    position = om._managed_positions["AAPL"][0]

    # Flatten position
    await om._flatten_position(position, reason="time_stop")

    # Find the pending flatten order and modify its strategy_id to simulate mismatch
    pending_order = None
    for pending in om._pending_orders.values():
        if pending.order_type == "flatten":
            pending_order = pending
            # Force a strategy_id mismatch
            pending_order.strategy_id = "non_existent_strategy"
            break
    assert pending_order is not None

    # Simulate fill - should fall back to first open position
    fill_event = OrderFilledEvent(
        order_id=pending_order.order_id,
        fill_price=150.5,
        fill_quantity=100,
    )
    await om.on_fill(fill_event)
    await event_bus.drain()

    # Position should still be closed via fallback
    assert len(closed_events) == 1
    assert closed_events[0].strategy_id == "orb_breakout"

    await om.stop()


@pytest.mark.asyncio
async def test_flatten_fill_single_position_unchanged_behavior(
    event_bus: EventBus,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> None:
    """Single position flatten behavior unchanged (regression test)."""
    mock_broker = MagicMock()
    order_counter = {"n": 0}

    def make_bracket_result(
        entry: MagicMock, stop: MagicMock, targets: list[MagicMock]
    ) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"broker-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"broker-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"broker-target-{order_counter['n'] + i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    mock_broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    mock_broker.place_order = AsyncMock(
        side_effect=lambda order: OrderResult(
            order_id=order.id,
            broker_order_id=f"broker-flatten-{order_counter['n']}",
            status=OrderStatus.SUBMITTED,
        )
    )
    mock_broker.cancel_order = AsyncMock(return_value=True)

    closed_events: list[PositionClosedEvent] = []

    async def handler(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, handler)

    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
    )

    await om.start()

    # Create a single position
    signal = make_signal(
        symbol="AAPL",
        strategy_id="orb_breakout",
        share_count=100,
    )
    await om.on_approved(make_approved(signal=signal))

    position = om._managed_positions["AAPL"][0]

    # Flatten position
    await om._flatten_position(position, reason="eod")

    # Find the pending flatten order
    pending_order = None
    for pending in om._pending_orders.values():
        if pending.order_type == "flatten":
            pending_order = pending
            break
    assert pending_order is not None

    # Simulate fill
    fill_event = OrderFilledEvent(
        order_id=pending_order.order_id,
        fill_price=150.5,
        fill_quantity=100,
    )
    await om.on_fill(fill_event)
    await event_bus.drain()

    # Position should be closed
    assert len(closed_events) == 1
    assert closed_events[0].strategy_id == "orb_breakout"
    # Exit reason is TIME_STOP by default when _flattened_today flag is not set
    assert closed_events[0].exit_reason == ExitReason.TIME_STOP

    await om.stop()


# ---------------------------------------------------------------------------
# Pending Entry Exposure Tests (DEC-261 Bug 2 Fix)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_pending_entry_exposure_with_pending_orders(
    order_manager: OrderManager,
) -> None:
    """get_pending_entry_exposure returns correct exposure for pending entry orders."""
    await order_manager.start()

    # Create a signal
    signal = make_signal(
        symbol="AAPL",
        entry_price=150.0,
        share_count=100,
    )
    approved = make_approved(signal=signal)

    # Manually create a pending entry order (without the fill completing)
    from argus.execution.order_manager import PendingManagedOrder

    pending = PendingManagedOrder(
        order_id="test-pending-001",
        order_type="entry",
        symbol="AAPL",
        strategy_id="orb_breakout",
        shares=100,
        signal=approved,
    )
    order_manager._pending_orders["test-pending-001"] = pending

    # Check exposure
    exposure = order_manager.get_pending_entry_exposure("AAPL")
    assert exposure == 150.0 * 100  # entry_price * shares = 15000

    await order_manager.stop()


@pytest.mark.asyncio
async def test_get_pending_entry_exposure_no_pending_orders(
    order_manager: OrderManager,
) -> None:
    """get_pending_entry_exposure returns 0 when no pending orders."""
    await order_manager.start()

    exposure = order_manager.get_pending_entry_exposure("AAPL")
    assert exposure == 0.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_get_pending_entry_exposure_ignores_non_entry_orders(
    order_manager: OrderManager,
) -> None:
    """get_pending_entry_exposure ignores non-entry orders (stops, targets, flattens)."""
    await order_manager.start()

    # Create a signal
    signal = make_signal(
        symbol="AAPL",
        entry_price=150.0,
        share_count=100,
    )
    approved = make_approved(signal=signal)

    from argus.execution.order_manager import PendingManagedOrder

    # Add various pending orders
    order_manager._pending_orders["pending-stop"] = PendingManagedOrder(
        order_id="pending-stop",
        order_type="stop",
        symbol="AAPL",
        strategy_id="orb_breakout",
        shares=100,
        signal=approved,
    )
    order_manager._pending_orders["pending-target"] = PendingManagedOrder(
        order_id="pending-target",
        order_type="target",
        symbol="AAPL",
        strategy_id="orb_breakout",
        shares=50,
        signal=approved,
    )
    order_manager._pending_orders["pending-flatten"] = PendingManagedOrder(
        order_id="pending-flatten",
        order_type="flatten",
        symbol="AAPL",
        strategy_id="orb_breakout",
        shares=100,
        signal=approved,
    )

    # Check exposure - should be 0 since no entry orders
    exposure = order_manager.get_pending_entry_exposure("AAPL")
    assert exposure == 0.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_get_pending_entry_exposure_multiple_symbols(
    order_manager: OrderManager,
) -> None:
    """get_pending_entry_exposure only counts orders for the specified symbol."""
    await order_manager.start()

    # Create signals for different symbols
    signal_aapl = make_signal(
        symbol="AAPL",
        entry_price=150.0,
        share_count=100,
    )
    signal_nvda = make_signal(
        symbol="NVDA",
        entry_price=500.0,
        share_count=50,
    )

    from argus.execution.order_manager import PendingManagedOrder

    # Add pending entry orders for both symbols
    order_manager._pending_orders["pending-aapl"] = PendingManagedOrder(
        order_id="pending-aapl",
        order_type="entry",
        symbol="AAPL",
        strategy_id="orb_breakout",
        shares=100,
        signal=make_approved(signal=signal_aapl),
    )
    order_manager._pending_orders["pending-nvda"] = PendingManagedOrder(
        order_id="pending-nvda",
        order_type="entry",
        symbol="NVDA",
        strategy_id="orb_breakout",
        shares=50,
        signal=make_approved(signal=signal_nvda),
    )

    # Check exposure for each symbol
    aapl_exposure = order_manager.get_pending_entry_exposure("AAPL")
    nvda_exposure = order_manager.get_pending_entry_exposure("NVDA")
    tsla_exposure = order_manager.get_pending_entry_exposure("TSLA")

    assert aapl_exposure == 150.0 * 100  # 15000
    assert nvda_exposure == 500.0 * 50  # 25000
    assert tsla_exposure == 0.0  # No pending orders

    await order_manager.stop()


# ---------------------------------------------------------------------------
# close_position (DEF-085)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_position_found_flattens(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """close_position() returns True and flattens when symbol exists."""
    from argus.execution.order_manager import ManagedPosition

    position = ManagedPosition(
        symbol="AAPL",
        strategy_id="orb_breakout",
        entry_price=150.0,
        entry_time=datetime(2026, 3, 20, 14, 30, tzinfo=UTC),
        shares_total=100,
        shares_remaining=100,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id="stop-1",
        t1_price=152.0,
        t1_order_id="t1-1",
        t1_shares=50,
        t1_filled=False,
        t2_price=154.0,
        high_watermark=150.0,
    )
    order_manager._managed_positions["AAPL"] = [position]

    mock_broker.cancel_order = AsyncMock()
    mock_broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-1", status=OrderStatus.FILLED, filled_qty=100, filled_price=150.0
        )
    )

    await order_manager.start()
    result = await order_manager.close_position("AAPL", reason="api_close")
    await order_manager.stop()

    assert result is True
    # Should have cancelled stop and T1 orders
    assert mock_broker.cancel_order.call_count >= 1


@pytest.mark.asyncio
async def test_close_position_not_found_returns_false(
    order_manager: OrderManager,
) -> None:
    """close_position() returns False when symbol has no managed positions."""
    await order_manager.start()
    result = await order_manager.close_position("ZZZZ")
    await order_manager.stop()

    assert result is False


# ---------------------------------------------------------------------------
# MFE/MAE Tests (Sprint 29.5 S6)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mfe_mae_initialized_at_entry(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """mfe_price and mae_price are set to entry_price when position opens."""
    await order_manager.start()

    approved = make_approved(make_signal(entry_price=150.0, stop_price=148.0))
    await order_manager.on_approved(approved)

    position = order_manager._managed_positions["AAPL"][0]
    assert position.mfe_price == position.entry_price
    assert position.mae_price == position.entry_price
    assert position.mfe_r == 0.0
    assert position.mae_r == 0.0
    assert position.mfe_time is None
    assert position.mae_time is None

    await order_manager.stop()


@pytest.mark.asyncio
async def test_mfe_updated_on_price_increase(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Tick above entry_price updates mfe_price, mfe_r, and mfe_time."""
    await order_manager.start()

    approved = make_approved(make_signal(entry_price=150.0, stop_price=148.0))
    await order_manager.on_approved(approved)

    await order_manager.on_tick(TickEvent(symbol="AAPL", price=153.0))

    position = order_manager._managed_positions["AAPL"][0]
    assert position.mfe_price == 153.0
    assert position.mfe_r > 0.0
    assert position.mfe_time is not None
    # mae should be unchanged (price did not go below entry)
    assert position.mae_price == 150.0
    assert position.mae_time is None

    await order_manager.stop()


@pytest.mark.asyncio
async def test_mae_updated_on_price_decrease(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Tick below entry_price updates mae_price, mae_r (negative), and mae_time."""
    await order_manager.start()

    approved = make_approved(make_signal(entry_price=150.0, stop_price=148.0))
    await order_manager.on_approved(approved)

    await order_manager.on_tick(TickEvent(symbol="AAPL", price=149.0))

    position = order_manager._managed_positions["AAPL"][0]
    assert position.mae_price == 149.0
    assert position.mae_r < 0.0
    assert position.mae_time is not None
    # mfe should be unchanged (price did not go above entry)
    assert position.mfe_price == 150.0
    assert position.mfe_time is None

    await order_manager.stop()


@pytest.mark.asyncio
async def test_mfe_mae_r_calculation_correct(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """R-multiple: entry=100, stop=98, price=103 → mfe_r=1.5."""
    await order_manager.start()

    signal = make_signal(
        symbol="AAPL",
        entry_price=100.0,
        stop_price=98.0,
        target_prices=(103.0, 106.0),
    )
    approved = make_approved(signal)
    await order_manager.on_approved(approved)

    # Override entry_price on position to 100.0 (bracket fills at 150.0 by default in mock)
    # Use a signal where entry/stop are well-defined and tick at 103.0 above fill
    position = order_manager._managed_positions["AAPL"][0]
    # The fill price in mock is 150.0 — reset fields to simulate entry=100, stop=98
    position.entry_price = 100.0
    position.original_stop_price = 98.0
    position.mfe_price = 100.0
    position.mae_price = 100.0

    await order_manager.on_tick(TickEvent(symbol="AAPL", price=103.0))

    assert position.mfe_r == pytest.approx(1.5)

    await order_manager.stop()


@pytest.mark.asyncio
async def test_mfe_mae_preserved_on_neutral_tick(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """A tick at the same price as current MFE does not overwrite mfe_time."""
    await order_manager.start()

    approved = make_approved(make_signal(entry_price=150.0, stop_price=148.0))
    await order_manager.on_approved(approved)

    # First tick raises MFE and sets mfe_time
    await order_manager.on_tick(TickEvent(symbol="AAPL", price=152.0))
    position = order_manager._managed_positions["AAPL"][0]
    first_mfe_time = position.mfe_time
    assert first_mfe_time is not None

    # Second tick at same price: mfe_price is not > 152.0, so mfe_time is not updated
    await order_manager.on_tick(TickEvent(symbol="AAPL", price=152.0))
    assert position.mfe_time == first_mfe_time

    await order_manager.stop()


@pytest.mark.asyncio
async def test_mfe_mae_persisted_to_trade_log(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """MFE/MAE values are included in the trade logged on position close."""
    logged_trades: list = []

    class MockTradeLogger:
        async def log_trade(self, trade: object) -> None:
            logged_trades.append(trade)

    order_manager._trade_logger = MockTradeLogger()  # type: ignore[assignment]
    await order_manager.start()

    approved = make_approved(make_signal(entry_price=150.0, stop_price=148.0))
    await order_manager.on_approved(approved)

    # Tick up then close via stop fill
    await order_manager.on_tick(TickEvent(symbol="AAPL", price=153.0))

    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id

    fill_event = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    assert len(logged_trades) == 1
    trade = logged_trades[0]
    assert trade.mfe_price == 153.0
    assert trade.mfe_r is not None
    assert trade.mfe_r > 0.0
    # mae should be entry_price (no adverse tick), so mae_r=0.0 → stored as None
    assert trade.mae_r is None or trade.mae_r == 0.0

    await order_manager.stop()
