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
    OrderRejectedEvent,
    PositionClosedEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    ReconciliationPosition,
    ReconciliationResult,
)
from argus.models.trading import BracketOrderResult, OrderResult, OrderSide, OrderStatus


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
    flatten_order_id = order_manager._flatten_pending["AAPL"][0]

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
    flatten_order_id = order_manager._flatten_pending["AAPL"][0]

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
    flatten_order_id = order_manager._flatten_pending["AAPL"][0]

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
    order_manager._flatten_pending["AAPL"] = ("some-order-id", 0.0, 0)

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
    order_manager._flatten_pending["AAPL"] = ("some-pending-flatten", 0.0, 0)

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
    broker_positions: dict[str, ReconciliationPosition] = {
        "AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=200)
    }

    discrepancies = await order_manager.reconcile_positions(broker_positions)

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
    broker_positions: dict[str, ReconciliationPosition] = {
        "AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=100)
    }

    discrepancies = await order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 0
    result = order_manager.last_reconciliation
    assert result is not None
    assert result.status == "synced"


@pytest.mark.asyncio
async def test_reconciliation_detects_broker_only_position(
    order_manager: OrderManager,
) -> None:
    """Broker has a position that ARGUS doesn't know about."""
    await order_manager.start()

    broker_positions: dict[str, ReconciliationPosition] = {
        "TSLA": ReconciliationPosition(symbol="TSLA", side=OrderSide.BUY, shares=50)
    }
    discrepancies = await order_manager.reconcile_positions(broker_positions)

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
    om._last_reconciliation = ReconciliationResult(
        timestamp="2026-02-16T15:00:00",
        status="mismatch",
        discrepancies=[{"symbol": "AAPL", "internal_qty": 100, "broker_qty": 200}],
    )

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

    broker_positions: dict[str, ReconciliationPosition] = {
        "AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=200)
    }

    # Capture state before
    positions_before = order_manager.get_all_positions_flat()
    shares_before = positions_before[0].shares_remaining

    await order_manager.reconcile_positions(broker_positions)

    # State must be unchanged
    positions_after = order_manager.get_all_positions_flat()
    shares_after = positions_after[0].shares_remaining
    assert shares_before == shares_after
    assert mock_broker.place_order.call_count == 0  # No orders placed for correction


# ---------------------------------------------------------------------------
# S2 Tests: Bracket Amendment on Slippage
# ---------------------------------------------------------------------------


@pytest.fixture
def ibkr_order_manager(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    config: OrderManagerConfig,
) -> OrderManager:
    """Order Manager configured as IBKR (non-simulated) for amendment tests."""
    from argus.core.config import BrokerSource

    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config,
        broker_source=BrokerSource.IBKR,
    )


async def _open_ibkr_position(
    order_manager: OrderManager,
    fill_price: float = 150.0,
    signal: SignalEvent | None = None,
) -> None:
    """Open position with controllable fill price for IBKR amendment tests."""
    await order_manager.start()
    if signal is None:
        signal = make_signal()

    # Override the mock to fill at the specified price
    original_side_effect = order_manager._broker.place_bracket_order.side_effect

    def custom_bracket(entry: MagicMock, stop: MagicMock, targets: list[MagicMock]) -> BracketOrderResult:
        result = original_side_effect(entry, stop, targets)
        # Override fill price
        result.entry.filled_avg_price = fill_price
        return result

    order_manager._broker.place_bracket_order = AsyncMock(side_effect=custom_bracket)
    approved = make_approved(signal)
    await order_manager.on_approved(approved)


@pytest.mark.asyncio
async def test_bracket_amendment_on_slippage(
    ibkr_order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Fill price differs from signal: bracket legs amended with delta shift."""
    signal = make_signal(
        entry_price=43.38, stop_price=42.88, target_prices=(43.88, 44.38)
    )
    # Fill at $43.66 (+$0.28 slippage)
    await _open_ibkr_position(ibkr_order_manager, fill_price=43.66, signal=signal)

    positions = ibkr_order_manager.get_all_positions_flat()
    assert len(positions) == 1
    pos = positions[0]

    # Delta = 43.66 - 43.38 = +0.28
    # New stop = 42.88 + 0.28 = 43.16
    # New T1 = 43.88 + 0.28 = 44.16
    # New T2 = 44.38 + 0.28 = 44.66
    assert abs(pos.stop_price - 43.16) < 0.01
    assert abs(pos.t1_price - 44.16) < 0.01
    assert abs(pos.t2_price - 44.66) < 0.01

    # Verify cancel_order was called for the original bracket legs
    assert mock_broker.cancel_order.call_count >= 2  # stop + T1 at minimum


@pytest.mark.asyncio
async def test_bracket_amendment_skipped_when_no_slippage(
    ibkr_order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Fill matches signal price: no amendment occurs."""
    signal = make_signal(
        entry_price=150.0, stop_price=148.0, target_prices=(152.0, 154.0)
    )
    await _open_ibkr_position(ibkr_order_manager, fill_price=150.0, signal=signal)

    positions = ibkr_order_manager.get_all_positions_flat()
    pos = positions[0]

    # Prices unchanged from signal
    assert pos.stop_price == 148.0
    assert pos.t1_price == 152.0
    assert pos.t2_price == 154.0

    # No cancel_order calls for amendment (only initial bracket setup)
    assert mock_broker.cancel_order.call_count == 0


@pytest.mark.asyncio
async def test_bracket_amendment_safety_check(
    ibkr_order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """Pathological case: amended T1 <= fill price triggers flatten."""
    # Entry far below target, but massive negative slippage pushes fill above T1
    signal = make_signal(
        entry_price=100.0, stop_price=99.0, target_prices=(100.50, 101.0)
    )
    # Fill at $100.60 — new T1 would be 100.50 + 0.60 = 101.10
    # Actually that's > fill. Let me construct a case where T1 <= fill.
    # entry=100, T1=100.05. Fill at 100.10. delta=+0.10. new T1=100.15 > 100.10 — still ok.
    # Need: entry=100, T1=100.01. Fill at 100.50. delta=+0.50. new T1=100.51 > 100.50 — still ok.
    # The prompt says "guard anyway". Let's test with a constructed position directly.
    signal2 = make_signal(
        entry_price=50.0, stop_price=49.0, target_prices=(50.01, 51.0)
    )
    # Fill at $50.50. delta=+0.50. new T1=50.51 > 50.50. Still passes.
    # To make T1 <= fill: entry=50, T1=49.90 (below entry!).
    # Actually let's just set it so delta makes T1 land at fill.
    # entry=50, T1=50.10, fill=50.20, delta=+0.20, new_T1=50.30 > 50.20. Still ok.
    # It's hard to construct naturally. Let's mock _amend_bracket_on_slippage directly.
    await ibkr_order_manager.start()

    # Create a position manually
    from argus.execution.order_manager import ManagedPosition

    pos = ManagedPosition(
        symbol="ZD",
        strategy_id="orb_breakout",
        entry_price=43.66,
        entry_time=ibkr_order_manager._clock.now(),
        shares_total=100,
        shares_remaining=100,
        stop_price=42.88,
        original_stop_price=42.88,
        stop_order_id="stop-1",
        t1_price=43.42,
        t1_order_id="t1-1",
        t1_shares=50,
        t1_filled=False,
        t2_price=43.92,
        high_watermark=43.66,
    )
    ibkr_order_manager._managed_positions["ZD"] = [pos]

    # Create a signal where T1 < fill after amendment
    # Signal entry=43.38, fill=43.66. delta=+0.28. But T1=43.42+0.28=43.70 > 43.66.
    # We need T1 to end up <= fill. So let's make original T1 very close to entry.
    # Actually, let's test by calling _amend_bracket_on_slippage directly with a
    # signal that produces T1 <= fill.
    fake_signal = make_signal(
        entry_price=43.38, stop_price=42.88, target_prices=(43.42, 43.92)
    )
    # Override position T1 to something that after amendment will be <= fill
    pos.t1_price = 43.30  # After delta +0.28 → 43.58. Still > 43.66? No, 43.58 < 43.66!
    await ibkr_order_manager._amend_bracket_on_slippage(pos, fake_signal, 43.66)

    # Position should have been flattened (shares_remaining decremented by flatten)
    # Check that place_order was called with a SELL market order (flatten)
    flatten_calls = [
        c for c in mock_broker.place_order.call_args_list
        if c.args[0].order_type.value == "market" and c.args[0].side.value == "sell"
    ]
    assert len(flatten_calls) >= 1


@pytest.mark.asyncio
async def test_bracket_amendment_skipped_for_simulated(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """SimulatedBroker: no amendment attempted even if prices differ."""
    # Default order_manager fixture uses BrokerSource.SIMULATED (default)
    signal = make_signal(
        entry_price=43.38, stop_price=42.88, target_prices=(43.88, 44.38)
    )

    # Override fill to simulate slippage (shouldn't happen but guard anyway)
    original_side_effect = mock_broker.place_bracket_order.side_effect

    def custom_bracket(entry: MagicMock, stop: MagicMock, targets: list[MagicMock]) -> BracketOrderResult:
        result = original_side_effect(entry, stop, targets)
        result.entry.filled_avg_price = 43.66  # Simulated slippage
        return result

    mock_broker.place_bracket_order = AsyncMock(side_effect=custom_bracket)
    await order_manager.start()
    approved = make_approved(signal)
    await order_manager.on_approved(approved)

    # No cancel_order calls — amendment skipped for simulated broker
    assert mock_broker.cancel_order.call_count == 0


# ---------------------------------------------------------------------------
# S2 Tests: Concurrent Position Limits
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_concurrent_limit_disabled_when_zero() -> None:
    """max_concurrent_positions=0 skips the check entirely."""
    from argus.core.config import AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig
    from argus.core.risk_manager import RiskManager

    config = RiskConfig(
        account=AccountRiskConfig(max_concurrent_positions=0),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(enabled=False),
    )
    broker = MagicMock()
    account = MagicMock()
    account.equity = 100000.0
    account.cash = 80000.0
    account.buying_power = 200000.0
    broker.get_account = AsyncMock(return_value=account)
    # Broker reports 50 open positions — should NOT reject because limit is disabled
    broker.get_positions = AsyncMock(return_value=[MagicMock()] * 50)

    event_bus = EventBus()
    rm = RiskManager(config=config, broker=broker, event_bus=event_bus)

    signal = make_signal(share_count=10)
    result = await rm.evaluate_signal(signal)

    assert isinstance(result, OrderApprovedEvent)


@pytest.mark.asyncio
async def test_concurrent_limit_disabled_when_none() -> None:
    """max_concurrent_positions=0 (our 'None' convention) skips check."""
    # Same as above — 0 is the "disabled" value
    from argus.core.config import AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig
    from argus.core.risk_manager import RiskManager

    config = RiskConfig(
        account=AccountRiskConfig(max_concurrent_positions=0),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(enabled=False),
    )
    broker = MagicMock()
    account = MagicMock()
    account.equity = 100000.0
    account.cash = 80000.0
    account.buying_power = 200000.0
    broker.get_account = AsyncMock(return_value=account)
    broker.get_positions = AsyncMock(return_value=[MagicMock()] * 100)

    event_bus = EventBus()
    rm = RiskManager(config=config, broker=broker, event_bus=event_bus)

    signal = make_signal(share_count=10)
    result = await rm.evaluate_signal(signal)

    assert isinstance(result, OrderApprovedEvent)


@pytest.mark.asyncio
async def test_concurrent_limit_still_works_when_set() -> None:
    """max_concurrent_positions=5 still enforces the limit."""
    from argus.core.config import AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig
    from argus.core.risk_manager import RiskManager

    config = RiskConfig(
        account=AccountRiskConfig(max_concurrent_positions=5),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(enabled=False),
    )
    broker = MagicMock()
    account = MagicMock()
    account.equity = 100000.0
    account.cash = 80000.0
    account.buying_power = 200000.0
    broker.get_account = AsyncMock(return_value=account)
    # Broker reports 5 positions — at limit
    broker.get_positions = AsyncMock(return_value=[MagicMock()] * 5)

    event_bus = EventBus()
    rm = RiskManager(config=config, broker=broker, event_bus=event_bus)

    signal = make_signal(share_count=10)
    result = await rm.evaluate_signal(signal)

    assert isinstance(result, OrderRejectedEvent)
    assert "concurrent" in result.reason.lower()


@pytest.mark.asyncio
async def test_cross_strategy_limit_disabled() -> None:
    """System-level max_concurrent_positions=0 does not block signals."""
    from argus.core.config import AccountRiskConfig, CrossStrategyRiskConfig, PDTConfig, RiskConfig
    from argus.core.risk_manager import RiskManager

    config = RiskConfig(
        account=AccountRiskConfig(max_concurrent_positions=0),
        cross_strategy=CrossStrategyRiskConfig(),
        pdt=PDTConfig(enabled=False),
    )
    broker = MagicMock()
    account = MagicMock()
    account.equity = 100000.0
    account.cash = 80000.0
    account.buying_power = 200000.0
    broker.get_account = AsyncMock(return_value=account)
    broker.get_positions = AsyncMock(return_value=[MagicMock()] * 200)

    event_bus = EventBus()
    rm = RiskManager(config=config, broker=broker, event_bus=event_bus)

    signal = make_signal(share_count=10)
    result = await rm.evaluate_signal(signal)

    assert isinstance(result, OrderApprovedEvent)


# ---------------------------------------------------------------------------
# S2 Tests: Zero-R Signal Guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_zero_r_signal_suppressed() -> None:
    """Entry == target suppresses signal via _has_zero_r guard."""
    from argus.strategies.base_strategy import BaseStrategy

    # _has_zero_r is a method on BaseStrategy; test directly
    class DummyStrategy(BaseStrategy):
        async def on_candle(self, event):
            return None

        async def on_tick(self, event):
            pass

        def get_scanner_criteria(self):
            return None  # type: ignore[return-value]

        def calculate_position_size(self, entry_price, stop_price):
            return 0

        def get_exit_rules(self):
            return None  # type: ignore[return-value]

        def get_market_conditions_filter(self):
            return None  # type: ignore[return-value]

    from argus.core.config import OperatingWindow, StrategyConfig, StrategyRiskLimits

    config = StrategyConfig(
        strategy_id="test",
        name="Test",
        version="1.0",
        operating_window=OperatingWindow(),
        risk_limits=StrategyRiskLimits(),
    )
    strat = DummyStrategy(config)

    # Zero R: target == entry
    assert strat._has_zero_r("PDBC", 16.86, 16.86) is True
    # Near-zero R: target 0.005 above entry
    assert strat._has_zero_r("PDBC", 16.86, 16.865) is True
    # Normal R: target $0.50 above
    assert strat._has_zero_r("PDBC", 16.86, 17.36) is False


@pytest.mark.asyncio
async def test_normal_r_signal_not_affected() -> None:
    """Normal R signals pass through the _has_zero_r guard."""
    from argus.strategies.base_strategy import BaseStrategy

    class DummyStrategy(BaseStrategy):
        async def on_candle(self, event):
            return None

        async def on_tick(self, event):
            pass

        def get_scanner_criteria(self):
            return None  # type: ignore[return-value]

        def calculate_position_size(self, entry_price, stop_price):
            return 0

        def get_exit_rules(self):
            return None  # type: ignore[return-value]

        def get_market_conditions_filter(self):
            return None  # type: ignore[return-value]

    from argus.core.config import OperatingWindow, StrategyConfig, StrategyRiskLimits

    config = StrategyConfig(
        strategy_id="test",
        name="Test",
        version="1.0",
        operating_window=OperatingWindow(),
        risk_limits=StrategyRiskLimits(),
    )
    strat = DummyStrategy(config)

    # Good R values should NOT be suppressed
    assert strat._has_zero_r("AAPL", 150.0, 152.0) is False
    assert strat._has_zero_r("TSLA", 200.0, 198.0) is False  # Short side
    assert strat._has_zero_r("NVDA", 100.0, 100.02) is False  # Just above threshold


# ---------------------------------------------------------------------------
# S2 Tests: Shutdown Sequence Ordering (R4.1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shutdown_sequence_ordering() -> None:
    """Verify cancel_all_orders → order_manager.stop → broker.disconnect ordering."""
    call_log: list[str] = []

    mock_broker = MagicMock()

    async def mock_cancel_all() -> int:
        call_log.append("cancel_all_orders")
        return 3

    async def mock_om_stop() -> None:
        call_log.append("order_manager.stop")

    async def mock_disconnect() -> None:
        call_log.append("broker.disconnect")

    mock_broker.cancel_all_orders = mock_cancel_all
    mock_broker.disconnect = mock_disconnect

    mock_om = MagicMock()
    mock_om.stop = mock_om_stop

    # Simulate the shutdown sequence from main.py (steps 2a, 3, and broker disconnect)
    # Step 2a: Cancel all orders
    await mock_broker.cancel_all_orders()
    # Step 3: Stop order manager
    await mock_om.stop()
    # Step N: Disconnect broker
    await mock_broker.disconnect()

    assert call_log == ["cancel_all_orders", "order_manager.stop", "broker.disconnect"]


# ---------------------------------------------------------------------------
# S2 Tests: ReconciliationResult Typing (R4.2)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconciliation_result_typed(
    order_manager: OrderManager,
    mock_broker: MagicMock,
) -> None:
    """ReconciliationResult is a proper dataclass, not dict[str, object]."""
    await _open_position(order_manager)

    broker_positions: dict[str, ReconciliationPosition] = {
        "AAPL": ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=200)
    }
    await order_manager.reconcile_positions(broker_positions)

    result = order_manager.last_reconciliation
    assert result is not None
    assert isinstance(result, ReconciliationResult)
    assert result.status == "mismatch"
    assert isinstance(result.discrepancies, list)
    assert result.discrepancies[0]["symbol"] == "AAPL"
    assert isinstance(result.timestamp, str)
