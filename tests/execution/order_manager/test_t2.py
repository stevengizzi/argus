"""Tests for Order Manager T2 handling (IBKR native brackets — DEC-093).

Tests cover broker-side T2 limit orders, T2 fill handling, and the
interaction between broker-side T2 and tick-based monitoring.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderFilledEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.execution.order_manager import OrderManager
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
    """Create a mock Broker with order tracking.

    Uses place_bracket_order for atomic entry+stop+targets submission (DEC-117).
    Entry fills synchronously; stop/targets remain PENDING until market fills.
    """
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
        """Simulate broker bracket order with synchronous entry fill."""
        order_counter["count"] += 1
        # Entry fills synchronously
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{order_counter['count']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        # Stop and targets remain pending
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{order_counter['count']}",
            status=OrderStatus.PENDING,
        )
        target_results = [
            OrderResult(
                order_id=t.id,
                broker_order_id=f"broker-t{i + 1}-{order_counter['count']}",
                status=OrderStatus.PENDING,
            )
            for i, t in enumerate(targets)
        ]
        return BracketOrderResult(entry=entry_result, stop=stop_result, targets=target_results)

    broker.place_order = AsyncMock(side_effect=make_order_result)
    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
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
# T2 Tests (8)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_t2_order_submitted_on_entry_fill(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """T2 limit order submitted atomically via bracket order (DEC-117)."""
    await order_manager.start()

    # Submit signal with T1 and T2 targets
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Verify: bracket order placed (entry+stop+T1+T2 atomic)
    assert mock_broker.place_bracket_order.call_count == 1
    bracket_call = mock_broker.place_bracket_order.call_args
    target_orders = bracket_call[0][2]

    # Entry fills synchronously, position created immediately
    positions = order_manager._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    position = positions[0]

    # T2 order should be the 2nd target in the bracket
    assert len(target_orders) == 2
    t2_order = target_orders[1]
    assert t2_order.symbol == "AAPL"
    assert t2_order.limit_price == 154.0  # T2 target
    assert t2_order.quantity == 50  # 50% of position (remaining after T1)
    assert str(t2_order.order_type) == "limit"

    # Position should have t2_order_id set from bracket result
    assert position.t2_order_id is not None
    assert position.t2_order_id == t2_order.id

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t2_fill_cancels_stop_and_closes(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    event_bus: EventBus,
) -> None:
    """T2 fill cancels stop order and closes position."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    t2_order_id = position.t2_order_id

    # Simulate T1 fill first (required before T2)
    t1_order_id = position.t1_order_id
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t1_order_id, fill_price=152.0, fill_quantity=50)
    )

    # After T1 fill, position has new stop order at breakeven
    stop_order_id_after_t1 = position.stop_order_id

    # Reset mock to track T2-specific cancellations
    mock_broker.cancel_order.reset_mock()

    # Simulate T2 fill
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t2_order_id, fill_price=154.0, fill_quantity=50)
    )

    # Stop order should be cancelled (new stop from T1 fill)
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert stop_order_id_after_t1 in cancel_calls

    # Position should be fully closed
    assert position.shares_remaining == 0
    assert position.is_fully_closed

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t2_fill_records_correct_pnl(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """T2 fill records correct P&L calculation."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id
    t2_order_id = position.t2_order_id

    # Simulate T1 fill: 50 shares * ($152 - $150) = $100
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t1_order_id, fill_price=152.0, fill_quantity=50)
    )

    # T1 P&L recorded
    assert position.realized_pnl == 100.0

    # Simulate T2 fill: 50 shares * ($154 - $150) = $200
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t2_order_id, fill_price=154.0, fill_quantity=50)
    )

    # Total P&L: $100 + $200 = $300
    assert position.realized_pnl == 300.0

    await order_manager.stop()


@pytest.mark.asyncio
async def test_on_tick_skips_t2_when_broker_order_exists(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """on_tick skips T2 monitoring when t2_order_id is set."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Simulate T1 fill (required for T2 monitoring to be relevant)
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t1_order_id, fill_price=152.0, fill_quantity=50)
    )

    # Position has t2_order_id set from bracket
    assert position.t2_order_id is not None

    # Reset mock to track new calls
    mock_broker.place_order.reset_mock()

    # Send tick at T2 price - should NOT trigger flatten
    tick = TickEvent(symbol="AAPL", price=154.0, volume=1000)
    await order_manager.on_tick(tick)

    # No new orders placed (no flatten)
    assert mock_broker.place_order.call_count == 0

    # Position still open with remaining shares
    assert position.shares_remaining == 50

    await order_manager.stop()


@pytest.mark.asyncio
async def test_on_tick_monitors_t2_when_no_broker_order(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """on_tick monitors T2 when t2_order_id is None (Alpaca path)."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    signal = make_signal(target_prices=(152.0, 154.0))
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    t1_order_id = position.t1_order_id

    # Simulate T1 fill
    await order_manager.on_fill(
        OrderFilledEvent(order_id=t1_order_id, fill_price=152.0, fill_quantity=50)
    )

    # Manually clear t2_order_id to simulate Alpaca path (no broker-side T2)
    position.t2_order_id = None

    # Reset mock to track new calls
    mock_broker.place_order.reset_mock()

    # Send tick at T2 price - should trigger flatten
    tick = TickEvent(symbol="AAPL", price=154.0, volume=1000)
    await order_manager.on_tick(tick)

    # Flatten order placed
    assert mock_broker.place_order.call_count == 1
    flatten_order = mock_broker.place_order.call_args[0][0]
    assert flatten_order.symbol == "AAPL"
    assert str(flatten_order.order_type) == "market"

    await order_manager.stop()


@pytest.mark.asyncio
async def test_stop_fill_cancels_t2_order(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Stop fill cancels T2 order if still open."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    stop_order_id = position.stop_order_id
    t2_order_id = position.t2_order_id

    # Verify T2 order exists
    assert t2_order_id is not None

    # Reset mock to track stop-related cancellations
    mock_broker.cancel_order.reset_mock()

    # Simulate stop fill
    await order_manager.on_fill(
        OrderFilledEvent(order_id=stop_order_id, fill_price=148.0, fill_quantity=100)
    )

    # T2 order should be cancelled
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert t2_order_id in cancel_calls

    await order_manager.stop()


@pytest.mark.asyncio
async def test_flatten_cancels_t2_order(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """_flatten_position cancels T2 order."""
    await order_manager.start()

    # Setup position via bracket order (entry fills synchronously)
    approved = make_approved()
    await order_manager.on_approved(approved)

    # Position created from bracket entry fill
    position = order_manager._managed_positions["AAPL"][0]
    t2_order_id = position.t2_order_id

    # Reset mock
    mock_broker.cancel_order.reset_mock()

    # Flatten position
    await order_manager._flatten_position(position, reason="test_flatten")

    # T2 order should be cancelled
    cancel_calls = [call[0][0] for call in mock_broker.cancel_order.call_args_list]
    assert t2_order_id in cancel_calls

    await order_manager.stop()


@pytest.mark.asyncio
async def test_t2_order_not_submitted_without_t2_price(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """No T2 order in bracket when target_prices has only T1."""
    await order_manager.start()

    # Signal with only T1 target
    signal = make_signal(target_prices=(152.0,))  # Only T1
    approved = make_approved(signal=signal)
    await order_manager.on_approved(approved)

    # Bracket order placed with only 1 target
    assert mock_broker.place_bracket_order.call_count == 1
    bracket_call = mock_broker.place_bracket_order.call_args
    target_orders = bracket_call[0][2]
    assert len(target_orders) == 1  # Only T1, no T2

    # Position created from bracket entry fill (entry fills synchronously)
    position = order_manager._managed_positions["AAPL"][0]
    assert position.t2_order_id is None
    assert position.t2_price == 0.0

    await order_manager.stop()
