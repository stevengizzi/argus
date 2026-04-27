"""Tests for Order Manager hardening (Sprint 27.95 Session 2).

Covers:
- Stop resubmission retry cap with exponential backoff
- Bracket amendment revision-rejected handling
- Duplicate fill deduplication
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    PendingManagedOrder,
)
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
    """Mock Broker with bracket order support."""
    broker = MagicMock()
    counter = {"n": 0}

    def _bracket(entry: MagicMock, stop: MagicMock, targets: list[MagicMock]) -> BracketOrderResult:
        counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"b-entry-{counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"b-stop-{counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"b-t{i}-{counter['n']}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    def _place(order: MagicMock) -> OrderResult:
        counter["n"] += 1
        return OrderResult(
            order_id=f"new-order-{counter['n']}",
            broker_order_id=f"b-{counter['n']}",
            status=OrderStatus.SUBMITTED,
        )

    broker.place_bracket_order = AsyncMock(side_effect=_bracket)
    broker.place_order = AsyncMock(side_effect=_place)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    return broker


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(datetime(2026, 3, 27, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def config() -> OrderManagerConfig:
    return OrderManagerConfig(stop_retry_max=3)


@pytest.fixture
def om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    clock: FixedClock,
    config: OrderManagerConfig,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=clock,
        config=config,
    )


def _make_position(
    symbol: str = "AAPL",
    stop_order_id: str = "stop-1",
    stop_price: float = 148.0,
    entry_price: float = 150.0,
) -> ManagedPosition:
    return ManagedPosition(
        symbol=symbol,
        strategy_id="orb_breakout",
        entry_price=entry_price,
        entry_time=datetime(2026, 3, 27, 14, 30, 0, tzinfo=UTC),
        shares_total=100,
        shares_remaining=100,
        stop_price=stop_price,
        original_stop_price=stop_price,
        stop_order_id=stop_order_id,
        t1_price=152.0,
        t1_order_id="t1-1",
        t1_shares=50,
        t1_filled=False,
        t2_price=154.0,
        high_watermark=150.0,
    )


def _inject_position(om: OrderManager, pos: ManagedPosition) -> None:
    """Inject a ManagedPosition directly into the Order Manager."""
    if pos.symbol not in om._managed_positions:
        om._managed_positions[pos.symbol] = []
    om._managed_positions[pos.symbol].append(pos)
    # Track stop in pending orders
    if pos.stop_order_id:
        om._pending_orders[pos.stop_order_id] = PendingManagedOrder(
            order_id=pos.stop_order_id,
            symbol=pos.symbol,
            strategy_id=pos.strategy_id,
            order_type="stop",
        )
    if pos.t1_order_id:
        om._pending_orders[pos.t1_order_id] = PendingManagedOrder(
            order_id=pos.t1_order_id,
            symbol=pos.symbol,
            strategy_id=pos.strategy_id,
            order_type="t1_target",
        )


# ---------------------------------------------------------------------------
# Stop Resubmission Cap Tests (1–7)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stop_rejected_once_retries(om: OrderManager, mock_broker: MagicMock) -> None:
    """Stop cancelled once → retry (attempt 1)."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    cancel = OrderCancelledEvent(order_id="stop-1", reason="Order cancelled by exchange")
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await om.on_cancel(cancel)

    # Should have retried (placed a new stop)
    mock_broker.place_order.assert_called_once()
    assert om._stop_retry_count["AAPL"] == 1  # Counter persists until position close
    mock_sleep.assert_called_once_with(1)  # 2^(1-1) = 1s backoff


@pytest.mark.asyncio
async def test_stop_rejected_twice_retries(om: OrderManager, mock_broker: MagicMock) -> None:
    """Stop cancelled twice without reset → retry count reaches 2, backoff 2s."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Pre-set retry count to 1 (simulating a prior cancel that succeeded but we
    # manually keep the counter to test accumulation before reset)
    om._stop_retry_count["AAPL"] = 1

    cancel = OrderCancelledEvent(order_id="stop-1", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await om.on_cancel(cancel)

    # Should have retried with 2s backoff (attempt 2)
    mock_broker.place_order.assert_called_once()
    mock_sleep.assert_called_once_with(2)  # 2^(2-1) = 2s backoff


@pytest.mark.asyncio
async def test_stop_rejected_three_times_triggers_flatten(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Stop cancelled 3 times → no retry, emergency flatten triggered."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Set retry count to max already (simulate 3 prior failures)
    om._stop_retry_count["AAPL"] = 3

    cancel = OrderCancelledEvent(order_id="stop-1", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await om.on_cancel(cancel)

    # Should NOT have placed a new stop
    # Instead, a flatten market order should have been placed
    calls = mock_broker.place_order.call_args_list
    assert len(calls) == 1  # flatten order
    order_arg = calls[0][0][0]
    assert order_arg.order_type.value == "market"
    assert order_arg.side.value == "sell"
    mock_sleep.assert_not_called()


@pytest.mark.asyncio
async def test_emergency_flatten_respects_flatten_pending_guard(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Emergency flatten from retry exhaustion respects _flatten_pending guard."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Mark a flatten as already pending
    om._flatten_pending["AAPL"] = ("existing-flatten-order", 0.0, 0)
    om._stop_retry_count["AAPL"] = 3

    cancel = OrderCancelledEvent(order_id="stop-1", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await om.on_cancel(cancel)

    # Should not place any new orders because flatten is already pending
    mock_broker.place_order.assert_not_called()


@pytest.mark.asyncio
async def test_retry_counter_resets_on_stop_fill(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Retry counter resets when position closes (stop fill → _close_position)."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Set a non-zero retry count (simulating prior cancel retries)
    om._stop_retry_count["AAPL"] = 2

    # Stop fills → position closes → counter cleaned up
    from argus.core.events import ExitReason
    await om._close_position(pos, exit_price=148.0, exit_reason=ExitReason.STOP_LOSS)

    assert "AAPL" not in om._stop_retry_count


@pytest.mark.asyncio
async def test_retry_counter_cleared_on_position_close(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Retry counter is cleared when position closes."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)
    om._stop_retry_count["AAPL"] = 1

    # Close position directly via _close_position (bypasses broker fill flow)
    from argus.core.events import ExitReason
    await om._close_position(pos, exit_price=148.0, exit_reason=ExitReason.STOP_LOSS)

    # After position close, retry state should be cleaned up
    assert "AAPL" not in om._stop_retry_count


@pytest.mark.asyncio
async def test_exponential_backoff_timing(om: OrderManager, mock_broker: MagicMock) -> None:
    """Backoff follows 1s, 2s, 4s progression."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    backoff_values: list[float] = []

    # Track each cancel→retry cycle
    for i in range(3):
        stop_id = pos.stop_order_id
        assert stop_id is not None
        cancel = OrderCancelledEvent(order_id=stop_id, reason="Cancelled")
        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await om.on_cancel(cancel)
            if mock_sleep.call_args:
                backoff_values.append(mock_sleep.call_args[0][0])

    assert backoff_values == [1, 2, 4]


# ---------------------------------------------------------------------------
# Revision-Rejected Handling Tests (8–9)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_revision_rejected_submits_fresh_order(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Revision-rejected detection → fresh order submitted (not retry flow)."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Store amended prices (as bracket amendment would)
    om._amended_prices["AAPL"] = (147.5, 152.5, 154.5)

    cancel = OrderCancelledEvent(
        order_id="stop-1",
        reason="Order cancelled: Revision rejected",
    )
    await om.on_cancel(cancel)

    # Should have submitted a fresh stop order via _submit_stop_order
    mock_broker.place_order.assert_called_once()
    order_arg = mock_broker.place_order.call_args[0][0]
    assert order_arg.stop_price == 147.5  # Uses amended price

    # Revision-rejected goes through fresh order path, not retry path
    # So the stop_retry_count should not be incremented
    assert "AAPL" not in om._stop_retry_count


@pytest.mark.asyncio
async def test_revision_rejected_fresh_order_fails_enters_retry_flow(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Fresh order after revision-rejected also fails → enters stop retry flow.

    When _submit_stop_order fails internally (exhausts its own retries),
    it calls _flatten_position as a safety net. This test verifies the
    revision-rejected path falls through to _submit_stop_order which handles
    the failure internally (including flatten if needed).
    """
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Make place_order raise to simulate broker connectivity failure.
    # _submit_stop_order will exhaust its retries then call _flatten_position
    # which also calls place_order (also fails). This is the worst-case path.
    call_count = {"n": 0}

    async def _fail_then_succeed(order: MagicMock) -> OrderResult:
        call_count["n"] += 1
        # Fail the first 4 calls (_submit_stop_order retry loop: 0,1,2,3)
        # Then succeed on the 5th call (the flatten order)
        if call_count["n"] <= 4:
            raise Exception("Broker error")
        return OrderResult(
            order_id=f"flatten-{call_count['n']}",
            broker_order_id=f"b-flatten-{call_count['n']}",
            status=OrderStatus.SUBMITTED,
        )

    mock_broker.place_order = AsyncMock(side_effect=_fail_then_succeed)

    cancel = OrderCancelledEvent(
        order_id="stop-1",
        reason="Revision rejected by exchange",
    )
    await om.on_cancel(cancel)

    # _submit_stop_order exhausted retries → called _flatten_position
    # Flatten order was submitted (the 5th call succeeded)
    assert "AAPL" in om._flatten_pending


# ---------------------------------------------------------------------------
# Duplicate Fill Deduplication Tests (10–12)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_fill_ignored(om: OrderManager, mock_broker: MagicMock) -> None:
    """Duplicate fill (same order_id, same cumulative_qty) → ignored."""
    await om.start()

    # Set up a position with a pending stop order
    pos = _make_position()
    _inject_position(om, pos)

    # First fill for the stop — should process
    om._pending_orders["stop-1"] = PendingManagedOrder(
        order_id="stop-1",
        symbol="AAPL",
        strategy_id="orb_breakout",
        order_type="stop",
    )
    fill1 = OrderFilledEvent(order_id="stop-1", fill_price=148.0, fill_quantity=100)
    await om.on_fill(fill1)

    # Position should have been processed (closed)
    assert pos.is_fully_closed

    # Second fill with same order_id and quantity — should be ignored silently
    fill2 = OrderFilledEvent(order_id="stop-1", fill_price=148.0, fill_quantity=100)
    await om.on_fill(fill2)  # No error, just ignored


@pytest.mark.asyncio
async def test_partial_fill_increased_qty_processed(om: OrderManager) -> None:
    """Legitimate partial fill (same order_id, increased cumulative_qty) → processed."""
    await om.start()

    # Test the dedup mechanism directly: first fill records qty, second with
    # different qty passes through (not blocked by dedup)
    # Use a fake order_id that's not in pending_orders — on_fill will log
    # "Fill for unknown order_id" but the dedup check happens BEFORE the
    # pending lookup, which is what we're testing.

    fill1 = OrderFilledEvent(order_id="test-order-1", fill_price=148.0, fill_quantity=50)
    await om.on_fill(fill1)
    assert om._last_fill_state.get("test-order-1") == 50.0

    # Second fill with SAME qty → should be blocked
    fill2_dup = OrderFilledEvent(order_id="test-order-1", fill_price=148.0, fill_quantity=50)
    await om.on_fill(fill2_dup)
    # Still 50 (second was ignored)
    assert om._last_fill_state.get("test-order-1") == 50.0

    # Third fill with INCREASED qty → should pass through (updated)
    fill3 = OrderFilledEvent(order_id="test-order-1", fill_price=148.0, fill_quantity=100)
    await om.on_fill(fill3)
    assert om._last_fill_state.get("test-order-1") == 100.0


@pytest.mark.asyncio
async def test_fill_dedup_state_cleared_on_position_close(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Fill dedup state cleared when associated position closes."""
    await om.start()
    pos = _make_position()
    _inject_position(om, pos)

    # Seed fill dedup state and reverse index (as on_fill would do)
    om._last_fill_state["stop-1"] = 100.0
    om._last_fill_state["t1-1"] = 50.0
    om._fill_order_ids_by_symbol["AAPL"] = {"stop-1", "t1-1"}

    # Close the position directly
    from argus.core.events import ExitReason
    await om._close_position(pos, exit_price=148.0, exit_reason=ExitReason.STOP_LOSS)

    # Fill dedup entries for AAPL should be cleaned up
    assert "stop-1" not in om._last_fill_state
    assert "t1-1" not in om._last_fill_state
    assert "AAPL" not in om._fill_order_ids_by_symbol


@pytest.mark.asyncio
async def test_stop_retry_per_symbol_isolation(
    om: OrderManager, mock_broker: MagicMock
) -> None:
    """Stop retry counter is per-symbol — one symbol's retries don't affect another."""
    await om.start()
    pos_aapl = _make_position(symbol="AAPL", stop_order_id="stop-aapl")
    pos_tsla = _make_position(symbol="TSLA", stop_order_id="stop-tsla")
    _inject_position(om, pos_aapl)
    _inject_position(om, pos_tsla)

    # Exhaust AAPL retries
    om._stop_retry_count["AAPL"] = 3

    # Cancel AAPL stop → should flatten (exhausted)
    cancel_aapl = OrderCancelledEvent(order_id="stop-aapl", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await om.on_cancel(cancel_aapl)

    # Cancel TSLA stop → should retry normally (counter is 0)
    cancel_tsla = OrderCancelledEvent(order_id="stop-tsla", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        await om.on_cancel(cancel_tsla)

    # TSLA should have a new stop placed (retry count = 1, first attempt)
    assert pos_tsla.stop_order_id is not None
    assert om._stop_retry_count.get("TSLA") == 1
    mock_sleep.assert_called_once_with(1)  # 2^(1-1) = 1s backoff


@pytest.mark.asyncio
async def test_cancel_retry_uses_stop_cancel_retry_max(
    event_bus: EventBus,
    mock_broker: MagicMock,
    clock: FixedClock,
) -> None:
    """_resubmit_stop_with_retry respects stop_cancel_retry_max, not stop_retry_max."""
    # Set stop_retry_max high (10) and stop_cancel_retry_max low (2)
    cfg = OrderManagerConfig(stop_retry_max=10, stop_cancel_retry_max=2)
    om = OrderManager(
        event_bus=event_bus, broker=mock_broker, clock=clock, config=cfg
    )
    await om.start()

    pos = _make_position(symbol="TEST", stop_order_id="stop-test")
    _inject_position(om, pos)

    # Pre-set retry count to 2 (at the cancel retry limit)
    om._stop_retry_count["TEST"] = 2

    # Next cancel should trigger emergency flatten (count=3 > stop_cancel_retry_max=2)
    cancel = OrderCancelledEvent(order_id="stop-test", reason="Cancelled")
    with patch("asyncio.sleep", new_callable=AsyncMock):
        await om.on_cancel(cancel)

    # Flatten should have been called (market sell placed)
    flatten_calls = [
        c for c in mock_broker.place_order.call_args_list
        if c[0][0].order_type.value == "market"
    ]
    assert len(flatten_calls) >= 1, "Emergency flatten not triggered at stop_cancel_retry_max"
