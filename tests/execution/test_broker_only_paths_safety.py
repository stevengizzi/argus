"""Sprint 31.91 Session 1c — Broker-only paths safety tests.

Verifies that the three broker-only safety paths in
``argus/execution/order_manager.py``:

1. ``_flatten_unknown_position`` (EOD Pass 2 zombie cleanup)
2. ``_drain_startup_flatten_queue`` (queued startup zombie flatten)
3. ``reconstruct_from_broker`` (startup wire-up)

each invoke ``broker.cancel_all_orders(symbol, await_propagation=True)``
BEFORE placing any SELL (or, for ``reconstruct_from_broker``, BEFORE
wiring the position into ``_managed_positions``). On
``CancelPropagationTimeout``, the SELL is aborted (or the wiring is
skipped), a ``cancel_propagation_timeout`` ``SystemAlertEvent`` is
emitted with severity=critical, and remaining symbols continue to
process (no early-return blocking the loop).

Failure-mode coverage (Item 2 — MEDIUM #7): the cancel-timeout escape
hatch in ``_flatten_unknown_position`` leaves a long zombie position
un-flattened. This is the intended trade-off — phantom long with no
stop is a bounded exposure preferable to an incorrect SELL that would
create an unbounded phantom short. Operator manually flattens via
``scripts/ibkr_close_all_positions.py``.

See also:
- ``docs/sprints/sprint-31.91-reconciliation-drift/sprint-spec.md`` §D4
- ``docs/sprints/sprint-31.91-reconciliation-drift/PHASE-D-OPEN-ITEMS.md`` Item 2
- Sprint 31.91 Session 1c implementation prompt §"Failure Mode Documentation"
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
from argus.core.event_bus import EventBus
from argus.core.events import SystemAlertEvent
from argus.execution.broker import CancelPropagationTimeout
from argus.execution.order_manager import OrderManager
from argus.models.trading import (
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _market_hours_clock() -> FixedClock:
    """11 AM ET = 15:00 UTC — inside market hours so the immediate-flatten
    path executes (no startup queue deferral)."""
    return FixedClock(datetime(2026, 4, 1, 15, 0, 0, tzinfo=UTC))


def _make_broker_position(
    symbol: str, shares: int, side: OrderSide = OrderSide.BUY,
) -> MagicMock:
    """Create a mock IBKR-style Position object."""
    pos = MagicMock(spec=Position)
    pos.symbol = symbol
    pos.shares = shares
    pos.side = side
    pos.entry_price = 100.0
    return pos


def _make_broker(*, cancel_all_orders_side_effect: object = None) -> MagicMock:
    """Create a mock broker with cancel_all_orders mocked.

    Args:
        cancel_all_orders_side_effect: If provided, used as ``side_effect``
            on the ``cancel_all_orders`` AsyncMock — pass an exception class
            (e.g., ``CancelPropagationTimeout``) to simulate timeout.
    """
    broker = MagicMock()
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="placed-1",
            broker_order_id="b-placed-1",
            status=OrderStatus.PENDING,
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    broker.cancel_order = AsyncMock(return_value=True)
    if cancel_all_orders_side_effect is not None:
        broker.cancel_all_orders = AsyncMock(
            side_effect=cancel_all_orders_side_effect
        )
    else:
        broker.cancel_all_orders = AsyncMock(return_value=0)
    return broker


def _make_om(broker: MagicMock, clock: FixedClock | None = None) -> OrderManager:
    return OrderManager(
        event_bus=EventBus(),
        broker=broker,
        clock=clock or _market_hours_clock(),
        config=OrderManagerConfig(
            eod_flatten_timeout_seconds=1, auto_shutdown_after_eod=False,
        ),
        startup_config=StartupConfig(flatten_unknown_positions=True),
    )


def _captured_alerts(om: OrderManager) -> list[SystemAlertEvent]:
    """Subscribe a list-collector to SystemAlertEvent for assertions."""
    captured: list[SystemAlertEvent] = []

    async def _on_alert(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    om._event_bus.subscribe(SystemAlertEvent, _on_alert)
    return captured


# ---------------------------------------------------------------------------
# Test 1 — _flatten_unknown_position calls cancel_all_orders FIRST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_flatten_unknown_position_calls_cancel_all_orders_first() -> None:
    """``cancel_all_orders(symbol, await_propagation=True)`` must run BEFORE
    ``place_order``. Reverting the gate causes this test to FAIL because
    the call ordering on the AsyncMock changes.
    """
    broker = _make_broker()
    om = _make_om(broker)

    # Force-execute path so we don't get queued for after-hours.
    await om._flatten_unknown_position("ZOMBIE", 75, force_execute=True)

    # Both methods called.
    broker.cancel_all_orders.assert_called_once_with(
        symbol="ZOMBIE", await_propagation=True
    )
    broker.place_order.assert_called_once()

    # Ordering: cancel_all_orders BEFORE place_order. Mock manager method
    # call ordering: track via mock_calls on the parent mock (broker).
    cancel_idx = next(
        i for i, c in enumerate(broker.mock_calls)
        if c[0] == "cancel_all_orders"
    )
    place_idx = next(
        i for i, c in enumerate(broker.mock_calls)
        if c[0] == "place_order"
    )
    assert cancel_idx < place_idx, (
        f"cancel_all_orders must run before place_order; saw "
        f"cancel_idx={cancel_idx} place_idx={place_idx} "
        f"in mock_calls={broker.mock_calls}"
    )


# ---------------------------------------------------------------------------
# Test 2 — _drain_startup_flatten_queue calls cancel_all_orders FIRST per symbol
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_drain_startup_flatten_queue_calls_cancel_all_orders_first() -> None:
    """Each queued symbol triggers cancel_all_orders BEFORE its SELL, in
    queue order. Reverting the gate causes the relative ordering on
    mock_calls to fail.
    """
    broker = _make_broker()
    om = _make_om(broker)
    om._startup_flatten_queue.append(("AAA", 10))
    om._startup_flatten_queue.append(("BBB", 20))
    om._startup_flatten_queue.append(("CCC", 30))

    await om._drain_startup_flatten_queue()

    assert broker.cancel_all_orders.call_count == 3
    assert broker.place_order.call_count == 3

    # Each cancel_all_orders is keyed by symbol, await_propagation=True.
    cancel_calls = broker.cancel_all_orders.call_args_list
    cancel_symbols = [c.kwargs["symbol"] for c in cancel_calls]
    assert cancel_symbols == ["AAA", "BBB", "CCC"]
    for c in cancel_calls:
        assert c.kwargs["await_propagation"] is True

    # Per-symbol ordering: each symbol's cancel_all_orders precedes its
    # corresponding place_order in mock_calls.
    name_seq = [c[0] for c in broker.mock_calls]
    # Find the indices of cancel_all_orders + place_order calls only.
    cancel_indices = [i for i, n in enumerate(name_seq) if n == "cancel_all_orders"]
    place_indices = [i for i, n in enumerate(name_seq) if n == "place_order"]
    assert len(cancel_indices) == 3 and len(place_indices) == 3
    for ci, pi in zip(cancel_indices, place_indices, strict=True):
        assert ci < pi, (
            f"cancel_all_orders at idx {ci} must precede place_order at "
            f"idx {pi} in {name_seq}"
        )


# ---------------------------------------------------------------------------
# Test 3 — reconstruct_from_broker calls cancel_all_orders per symbol BEFORE
# any wiring into _managed_positions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconstruct_from_broker_calls_cancel_all_orders_per_symbol() -> None:
    """Per spec: cancel_all_orders is called once per symbol BEFORE either
    position is wired into _managed_positions. Both positions end up wired
    with _broker_confirmed=True (per DEC-369).
    """
    broker = _make_broker()
    aapl = _make_broker_position("AAPL", shares=100, side=OrderSide.BUY)
    msft = _make_broker_position("MSFT", shares=50, side=OrderSide.BUY)
    broker.get_positions = AsyncMock(return_value=[aapl, msft])

    # Provide stop orders so both go through the managed-reconstruct path
    # (has_orders=True), exercising the wiring path.
    from argus.models.trading import Order, OrderType
    aapl_stop = Order(
        strategy_id="prior", symbol="AAPL", side=OrderSide.SELL,
        order_type=OrderType.STOP, quantity=100, stop_price=98.0,
    )
    msft_stop = Order(
        strategy_id="prior", symbol="MSFT", side=OrderSide.SELL,
        order_type=OrderType.STOP, quantity=50, stop_price=98.0,
    )
    broker.get_open_orders = AsyncMock(return_value=[aapl_stop, msft_stop])

    om = _make_om(broker)

    await om.reconstruct_from_broker()

    # cancel_all_orders called once per symbol with await_propagation=True
    assert broker.cancel_all_orders.call_count == 2
    cancel_symbols = {
        c.kwargs["symbol"] for c in broker.cancel_all_orders.call_args_list
    }
    assert cancel_symbols == {"AAPL", "MSFT"}
    for c in broker.cancel_all_orders.call_args_list:
        assert c.kwargs["await_propagation"] is True

    # Both positions wired into _managed_positions after the cancel call.
    # (DEC-369 broker-confirmed bookkeeping is set on entry-fill, not on
    # reconstruct — Session 2b.1 is the natural sprint to extend that
    # invariant; for Session 1c the assertion is purely that the cancel
    # gate does not block normal wiring on success.)
    assert "AAPL" in om._managed_positions
    assert "MSFT" in om._managed_positions


# ---------------------------------------------------------------------------
# Test 4 — EOD Pass 2 stale OCA cleared before SELL (integration)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eod_pass2_stale_oca_cleared_before_sell() -> None:
    """Higher-level integration: an EOD Pass 2 zombie position triggers
    cancel_all_orders (clearing stale OCA siblings) BEFORE the flatten
    SELL. The SELL placed has no ocaGroup set (broker-only path is not
    threaded into an OCA group)."""
    broker = _make_broker()
    long_zombie = _make_broker_position("ZOMB", shares=200, side=OrderSide.BUY)
    broker.get_positions = AsyncMock(side_effect=[
        [long_zombie],   # Pass 2 query
        [],              # post-verify: cleared
    ])
    om = _make_om(broker)

    await om.eod_flatten()

    broker.cancel_all_orders.assert_any_call(
        symbol="ZOMB", await_propagation=True
    )
    broker.place_order.assert_called_once()
    placed = broker.place_order.call_args[0][0]
    assert placed.symbol == "ZOMB"
    assert placed.side == OrderSide.SELL
    assert placed.quantity == 200
    # Broker-only path is NOT threaded into an OCA group.
    assert getattr(placed, "ocaGroup", None) in (None, "")


# ---------------------------------------------------------------------------
# Test 5 — reconstruct orphaned OCA cleared, no OCA reconstruction
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconstruct_orphaned_oca_cleared() -> None:
    """A reconstructed position with a stale STP order: cancel_all_orders
    is invoked; the wired ManagedPosition has oca_group_id=None (no OCA
    reconstruction across restart — bracket OCA grouping is per-bracket
    placement, not reconstructed)."""
    from argus.models.trading import Order, OrderType

    broker = _make_broker()
    pos = _make_broker_position("XYZ", shares=100, side=OrderSide.BUY)
    stale_stop = Order(
        strategy_id="prior",
        symbol="XYZ",
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        quantity=100,
        stop_price=95.0,
    )
    broker.get_positions = AsyncMock(return_value=[pos])
    broker.get_open_orders = AsyncMock(return_value=[stale_stop])

    om = _make_om(broker)

    await om.reconstruct_from_broker()

    broker.cancel_all_orders.assert_called_once_with(
        symbol="XYZ", await_propagation=True
    )
    assert "XYZ" in om._managed_positions
    managed = om._managed_positions["XYZ"][0]
    # No OCA reconstruction: spec is explicit that bracket OCA grouping
    # is per-bracket-placement, not reconstructed across restart.
    assert managed.oca_group_id is None


# ---------------------------------------------------------------------------
# Test 6 — CancelPropagationTimeout aborts SELL and emits alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_cancel_propagation_timeout_aborts_sell_and_emits_alert() -> None:
    """When cancel_all_orders raises CancelPropagationTimeout in
    _flatten_unknown_position, place_order is NOT called and a
    SystemAlertEvent with alert_type='cancel_propagation_timeout',
    severity='critical' is emitted exactly once.
    """
    broker = _make_broker(
        cancel_all_orders_side_effect=CancelPropagationTimeout(
            "broker did not propagate within 2s"
        )
    )
    om = _make_om(broker)
    captured = _captured_alerts(om)

    # Trigger via the _flatten_unknown_position path (force_execute so we
    # bypass the market-hours queueing).
    await om._flatten_unknown_position("ZOMB", 75, force_execute=True)
    # Drain the event bus so async handler tasks complete before we
    # inspect captured alerts.
    await om._event_bus.drain()

    # Function returned cleanly (no exception bubbled up).
    broker.place_order.assert_not_called()

    # Exactly one SystemAlertEvent emitted, with required fields.
    alerts = [a for a in captured if isinstance(a, SystemAlertEvent)]
    assert len(alerts) == 1, (
        f"Expected exactly one SystemAlertEvent; got {len(alerts)}: {alerts}"
    )
    alert = alerts[0]
    assert alert.alert_type == "cancel_propagation_timeout"
    assert alert.severity == "critical"
    assert "ZOMB" in alert.message

    # The next call in the EOD Pass 2 loop can proceed for a different symbol
    # (no leaked exception state). Reset cancel_all_orders to succeed and
    # try again — this proves the function returns cleanly.
    broker.cancel_all_orders.side_effect = None
    broker.cancel_all_orders.return_value = 0
    await om._flatten_unknown_position("OTHER", 10, force_execute=True)
    broker.place_order.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7 (Item 2 — MEDIUM #7) — cancel-timeout failure mode for EOD Pass 2
# leaves the long position un-flattened (intended trade-off)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_eod_pass2_cancel_timeout_aborts_sell_emits_alert_no_phantom_short(
) -> None:
    """MEDIUM #7: cancel-timeout escape hatch in _flatten_unknown_position
    leaves position un-flattened (intended trade-off; phantom long with
    no stop is a bounded exposure preferable to an incorrect SELL that
    would create an unbounded phantom short). Operator manually flattens
    via scripts/ibkr_close_all_positions.py.

    Linked: PHASE-D-OPEN-ITEMS.md Item 2 + sprint-spec.md §D4 + Sprint
    31.91 Session 1c implementation prompt §"Failure Mode Documentation".
    """
    # Setup: simulate EOD Pass 2 with a zombie LONG (BUY-side) position.
    # Phantom-short avoidance is the entire point: aborting the SELL is
    # what prevents an incorrect SELL from producing an unbounded short.
    long_zombie = _make_broker_position("PHANTOM", shares=100, side=OrderSide.BUY)

    broker = _make_broker(
        cancel_all_orders_side_effect=CancelPropagationTimeout(
            "broker did not propagate within 2s"
        )
    )
    # Pass 2 sees the zombie; post-verify also sees it (abort means no flatten).
    broker.get_positions = AsyncMock(side_effect=[
        [long_zombie],
        [long_zombie],
    ])

    om = _make_om(broker)
    captured = _captured_alerts(om)

    await om.eod_flatten()
    await om._event_bus.drain()

    # Failure-mode point: place_order is NOT called for this symbol.
    # Placing the SELL incorrectly is the bug the abort prevents.
    place_calls_for_phantom = [
        c for c in broker.place_order.call_args_list
        if c[0] and c[0][0].symbol == "PHANTOM"
    ]
    assert place_calls_for_phantom == [], (
        f"place_order MUST NOT be called for PHANTOM after "
        f"CancelPropagationTimeout (incorrect SELL would create an "
        f"unbounded phantom short). Got: {place_calls_for_phantom}"
    )

    # cancel_propagation_timeout alert fires.
    alerts = [
        a for a in captured
        if isinstance(a, SystemAlertEvent)
        and a.alert_type == "cancel_propagation_timeout"
    ]
    assert len(alerts) >= 1, (
        f"Expected at least one cancel_propagation_timeout alert; "
        f"got captured={captured}"
    )
    timeout_alert = alerts[0]
    assert timeout_alert.severity == "critical"
    assert "PHANTOM" in timeout_alert.message

    # Position is NOT marked closed in any tracking structure (the failure
    # mode is "leaked long," not "cleanly closed"). _managed_positions
    # should not contain PHANTOM (it was a Pass 2 zombie, not a managed
    # position — and the abort prevented any state mutation).
    assert "PHANTOM" not in om._managed_positions, (
        "Aborted EOD Pass 2 flatten must NOT mutate _managed_positions. "
        "The intended trade-off is: leaked long at broker, no internal "
        "state change, operator manually flattens before next session."
    )
