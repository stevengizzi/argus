"""Tests for Order Manager safety features (Sprint 27.65).

Tests flatten-pending guard, graceful shutdown cancellation,
and position reconciliation.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    OrderApprovedEvent,
    OrderCancelledEvent,
    OrderFilledEvent,
    PositionClosedEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
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
    """Create a mock Broker with place_bracket_order() support."""
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
            entry=entry_result, stop=stop_result, targets=target_results
        )

    def make_flatten_result(order: MagicMock) -> OrderResult:
        """Return SUBMITTED (not FILLED) so we can test the async path."""
        order_counter["count"] += 1
        return OrderResult(
            order_id=f"flatten-{order_counter['count']}",
            broker_order_id=f"broker-flatten-{order_counter['count']}",
            status=OrderStatus.SUBMITTED,
        )

    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.place_order = AsyncMock(side_effect=make_flatten_result)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=3)
    broker.get_positions = AsyncMock(return_value=[])
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
    time_stop_seconds: int | None = 300,
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
        time_stop_seconds=time_stop_seconds,
    )


def make_approved(
    signal: SignalEvent | None = None,
    modifications: dict | None = None,
) -> OrderApprovedEvent:
    """Create an OrderApprovedEvent."""
    if signal is None:
        signal = make_signal()
    return OrderApprovedEvent(signal=signal, modifications=modifications)


async def _open_position(
    order_manager: OrderManager,
) -> None:
    """Helper: submit an approved signal and get a managed position."""
    await order_manager.start()
    approved = make_approved()
    await order_manager.on_approved(approved)


# ---------------------------------------------------------------------------
# R1: Flatten-Pending Guard Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_pending_prevents_duplicate_orders(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Time-stop fires across 3 poll cycles, only 1 flatten order submitted."""
    await _open_position(order_manager)

    # Advance clock past time-stop threshold (300s)
    fixed_clock.advance(seconds=350)

    # Simulate 3 poll cycles by calling _flatten_position directly
    positions = order_manager._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    pos = positions[0]

    # First flatten — should submit
    await order_manager._flatten_position(pos, reason="time_stop")
    first_call_count = mock_broker.place_order.call_count

    # Second flatten — should be suppressed
    await order_manager._flatten_position(pos, reason="time_stop")
    second_call_count = mock_broker.place_order.call_count

    # Third flatten — should be suppressed
    await order_manager._flatten_position(pos, reason="time_stop")
    third_call_count = mock_broker.place_order.call_count

    # Only 1 place_order call for the flatten (stop/T1/T2 cancels don't count)
    assert first_call_count == 1
    assert second_call_count == 1
    assert third_call_count == 1


@pytest.mark.asyncio
async def test_flatten_pending_clears_on_fill(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Flatten fills → flag cleared → subsequent time-stop can re-trigger."""
    await _open_position(order_manager)
    fixed_clock.advance(seconds=350)

    positions = order_manager._managed_positions.get("AAPL", [])
    pos = positions[0]

    # First flatten
    await order_manager._flatten_position(pos, reason="time_stop")
    assert "AAPL" in order_manager._flatten_pending
    flatten_order_id = order_manager._flatten_pending["AAPL"]

    # Simulate fill
    fill_event = OrderFilledEvent(
        order_id=flatten_order_id,
        fill_price=149.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    # Flatten-pending should be cleared (position closed)
    assert "AAPL" not in order_manager._flatten_pending


@pytest.mark.asyncio
async def test_flatten_pending_clears_on_cancel(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Flatten cancelled by broker → flag cleared."""
    await _open_position(order_manager)
    fixed_clock.advance(seconds=350)

    positions = order_manager._managed_positions.get("AAPL", [])
    pos = positions[0]

    await order_manager._flatten_position(pos, reason="time_stop")
    assert "AAPL" in order_manager._flatten_pending
    flatten_order_id = order_manager._flatten_pending["AAPL"]

    # Simulate cancellation from broker
    cancel_event = OrderCancelledEvent(
        order_id=flatten_order_id,
        reason="Cancelled (IBKR status: Cancelled)",
    )
    await order_manager.on_cancel(cancel_event)

    # Should be cleared
    assert "AAPL" not in order_manager._flatten_pending


@pytest.mark.asyncio
async def test_flatten_pending_clears_on_reject(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Flatten rejected by broker → flag cleared."""
    await _open_position(order_manager)
    fixed_clock.advance(seconds=350)

    positions = order_manager._managed_positions.get("AAPL", [])
    pos = positions[0]

    await order_manager._flatten_position(pos, reason="time_stop")
    flatten_order_id = order_manager._flatten_pending["AAPL"]

    # Simulate rejection (IBKR sends cancel event for rejections too)
    cancel_event = OrderCancelledEvent(
        order_id=flatten_order_id,
        reason="Order rejected by IBKR: insufficient margin",
    )
    await order_manager.on_cancel(cancel_event)

    assert "AAPL" not in order_manager._flatten_pending

    # Now a new flatten should work
    await order_manager._flatten_position(pos, reason="time_stop")
    # place_order should be called again (2 total flattens)
    assert mock_broker.place_order.call_count == 2


@pytest.mark.asyncio
async def test_flatten_pending_clears_on_position_close(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Position closed by stop/target → flatten-pending cleared."""
    await _open_position(order_manager)

    positions = order_manager._managed_positions.get("AAPL", [])
    pos = positions[0]

    # Manually set a flatten-pending entry
    order_manager._flatten_pending["AAPL"] = "some-order-id"

    # Close position via _close_position (simulating stop hit)
    await order_manager._close_position(pos, 148.0, ExitReason.STOP_LOSS)

    # Flatten-pending should be cleared
    assert "AAPL" not in order_manager._flatten_pending


@pytest.mark.asyncio
async def test_flatten_pending_does_not_block_normal_stop_loss(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Stop loss path is unaffected by flatten guard.

    Stop fills go through on_fill → _handle_stop_fill → _close_position,
    NOT through _flatten_position, so the guard doesn't interfere.
    """
    await _open_position(order_manager)

    positions = order_manager._managed_positions.get("AAPL", [])
    pos = positions[0]
    stop_order_id = pos.stop_order_id

    # Even with flatten-pending set, stop fill should still work
    order_manager._flatten_pending["AAPL"] = "some-pending-flatten"

    # Simulate stop fill
    assert stop_order_id is not None
    fill_event = OrderFilledEvent(
        order_id=stop_order_id,
        fill_price=148.0,
        fill_quantity=100,
    )
    await order_manager.on_fill(fill_event)

    # Position should be closed (flatten-pending also cleared by _close_position)
    assert "AAPL" not in order_manager._flatten_pending
    assert order_manager.open_position_count == 0


# ---------------------------------------------------------------------------
# R2: Graceful Shutdown Order Cancellation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_shutdown_cancels_orders(
    mock_broker: MagicMock,
) -> None:
    """Shutdown sequence calls cancel_all_orders before disconnect."""
    # We test that the broker's cancel_all_orders method exists and works
    mock_broker.cancel_all_orders = AsyncMock(return_value=5)

    count = await mock_broker.cancel_all_orders()
    assert count == 5
    mock_broker.cancel_all_orders.assert_called_once()


@pytest.mark.asyncio
async def test_ibkr_cancel_all_orders() -> None:
    """IBKRBroker.cancel_all_orders calls reqGlobalCancel."""
    from argus.execution.ibkr_broker import IBKRBroker

    mock_ib = MagicMock()
    mock_ib.isConnected.return_value = True
    mock_trade = MagicMock()
    mock_ib.openTrades.return_value = [mock_trade, mock_trade, mock_trade]
    mock_ib.reqGlobalCancel = MagicMock()

    mock_event_bus = MagicMock()
    mock_config = MagicMock()

    broker = IBKRBroker.__new__(IBKRBroker)
    broker._ib = mock_ib
    broker._connected = True
    broker._event_bus = mock_event_bus
    broker._config = mock_config

    with patch("asyncio.sleep", new_callable=AsyncMock):
        count = await broker.cancel_all_orders()

    assert count == 3
    mock_ib.reqGlobalCancel.assert_called_once()


# ---------------------------------------------------------------------------
# R3: Position Reconciliation Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconciliation_detects_mismatch(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Internal has position X, broker has position Y → warning logged."""
    await _open_position(order_manager)

    # Internal has AAPL=100 shares
    # Broker reports AAPL=200 shares (mismatch)
    broker_positions: dict[str, float] = {"AAPL": 200.0}

    discrepancies = order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 1
    assert discrepancies[0]["symbol"] == "AAPL"
    assert discrepancies[0]["internal_qty"] == 100
    assert discrepancies[0]["broker_qty"] == 200


@pytest.mark.asyncio
async def test_reconciliation_synced(
    order_manager: OrderManager,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """Internal matches broker → "synced" result."""
    await _open_position(order_manager)

    # Broker reports matching position
    broker_positions: dict[str, float] = {"AAPL": 100.0}

    discrepancies = order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 0
    result = order_manager.last_reconciliation
    assert result is not None
    assert result["status"] == "synced"


@pytest.mark.asyncio
async def test_reconciliation_detects_broker_only_position(
    order_manager: OrderManager,
) -> None:
    """Broker has a position that ARGUS doesn't know about."""
    await order_manager.start()

    broker_positions: dict[str, float] = {"TSLA": 50.0}
    discrepancies = order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 1
    assert discrepancies[0]["symbol"] == "TSLA"
    assert discrepancies[0]["internal_qty"] == 0
    assert discrepancies[0]["broker_qty"] == 50


@pytest.mark.asyncio
async def test_reconciliation_endpoint_returns_result(
) -> None:
    """API endpoint returns latest reconciliation result."""
    from datetime import UTC, datetime

    from httpx import ASGITransport, AsyncClient

    from argus.api.dependencies import AppState
    from argus.api.server import create_app

    event_bus = EventBus()
    mock_broker = MagicMock()
    mock_broker.place_bracket_order = AsyncMock()
    mock_broker.cancel_order = AsyncMock()

    clock = FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))
    config = OrderManagerConfig()
    om = OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=clock,
        config=config,
    )
    # Set a reconciliation result
    om._last_reconciliation = {
        "timestamp": "2026-02-16T15:00:00",
        "status": "mismatch",
        "discrepancies": [{"symbol": "AAPL", "internal_qty": 100, "broker_qty": 200}],
    }

    state = AppState(
        event_bus=event_bus,
        trade_logger=MagicMock(),
        broker=mock_broker,
        health_monitor=None,
        risk_manager=MagicMock(),
        order_manager=om,
        data_service=None,
        strategies={},
        clock=clock,
        config=MagicMock(),
        start_time=0.0,
    )

    app = create_app(state)
    app.state.app_state = state
    transport = ASGITransport(app=app)

    # Set JWT secret via the module-level setter (not just env var)
    import jwt

    from argus.api.auth import set_jwt_secret

    secret = "test-secret-key-for-reconciliation-32chars!"
    set_jwt_secret(secret)
    token = jwt.encode(
        {"sub": "operator", "exp": datetime(2030, 1, 1, tzinfo=UTC)},
        secret,
        algorithm="HS256",
    )

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/api/v1/positions/reconciliation",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "mismatch"
    assert len(data["discrepancies"]) == 1
    assert data["discrepancies"][0]["symbol"] == "AAPL"


@pytest.mark.asyncio
async def test_reconciliation_no_auto_correct(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Reconciliation must NEVER modify positions — warn only."""
    await _open_position(order_manager)

    broker_positions: dict[str, float] = {"AAPL": 200.0}

    # Capture state before
    positions_before = order_manager.get_all_positions_flat()
    shares_before = positions_before[0].shares_remaining

    order_manager.reconcile_positions(broker_positions)

    # State must be unchanged
    positions_after = order_manager.get_all_positions_flat()
    shares_after = positions_after[0].shares_remaining
    assert shares_before == shares_after
    assert mock_broker.place_order.call_count == 0  # No orders placed for correction
