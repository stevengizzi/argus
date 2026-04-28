"""Sprint 31.91 Session 3 — DEF-158 retry side-check (3-branch gate).

Verifies that ``OrderManager._check_flatten_pending_timeouts`` is
side-aware before resubmitting a flatten SELL. The fix mirrors
IMPROMPTU-04 EOD A1 at ``order_manager.py:1875-1904`` exactly:

- Branch 1 (``broker_side == OrderSide.BUY`` + qty > 0): resubmit SELL
  using IBKR-authoritative qty (DEF-158 normal case preserved).
- Branch 2 (``broker_side == OrderSide.SELL``): refuse retry, emit
  ``phantom_short_retry_blocked`` SystemAlertEvent (severity=critical),
  clear flatten-pending so the next cycle does not loop.
- Branch 3 (``broker_side`` is None / unrecognized): refuse retry,
  ERROR log, clear flatten-pending. No alert emission — alert flooding
  on a structural broker-adapter defect would not be useful.

Without the gate, an OCA-leak phantom short (DEF-204) reaching the
DEF-158 retry path would be DOUBLED by an unconditional SELL. The 3
branches collapse three remaining side-blind retry shapes into a
single defended path, completing the architectural property "every
flatten/retry path inspects ``side`` before placing SELL" across the
OrderManager.
"""

from __future__ import annotations

import logging
import time as _time
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    Side,
    SignalEvent,
    SystemAlertEvent,
)
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.models.trading import (
    BracketOrderResult,
    OrderResult,
    OrderSide,
    OrderStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def fixed_clock() -> FixedClock:
    # 10:00 AM ET = 14:00 UTC, weekday (market open).
    return FixedClock(datetime(2026, 4, 28, 14, 0, 0, tzinfo=UTC))


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    counter = {"n": 0}

    def _next() -> str:
        counter["n"] += 1
        return f"order-{counter['n']}"

    def _make_bracket(entry, stop, targets) -> BracketOrderResult:
        entry_result = OrderResult(
            order_id=entry.id,
            broker_order_id=f"broker-entry-{_next()}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        stop_result = OrderResult(
            order_id=stop.id,
            broker_order_id=f"broker-stop-{_next()}",
            status=OrderStatus.PENDING,
        )
        target_results = [
            OrderResult(
                order_id=t.id,
                broker_order_id=f"broker-target-{_next()}",
                status=OrderStatus.PENDING,
            )
            for t in targets
        ]
        return BracketOrderResult(
            entry=entry_result, stop=stop_result, targets=target_results,
        )

    broker.place_bracket_order = AsyncMock(side_effect=_make_bracket)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="resubmit-1",
            broker_order_id="broker-resubmit-1",
            status=OrderStatus.PENDING,
        )
    )
    broker.get_open_orders = AsyncMock(return_value=[])
    # ``get_positions`` is overridden per-test; default is empty list.
    broker.get_positions = AsyncMock(return_value=[])
    return broker


def _make_om(
    event_bus: EventBus,
    broker: MagicMock,
    clock: FixedClock,
    *,
    flatten_pending_timeout: int = 10,
    max_flatten_retries: int = 3,
) -> OrderManager:
    config = OrderManagerConfig(
        flatten_pending_timeout_seconds=flatten_pending_timeout,
        max_flatten_retries=max_flatten_retries,
    )
    return OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
    )


def _make_signal(symbol: str = "AAPL") -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test signal",
        atr_value=1.5,
        time_stop_seconds=900,
    )


async def _open_position(
    om: OrderManager, broker: MagicMock, symbol: str = "AAPL",
) -> ManagedPosition:
    signal = _make_signal(symbol=symbol)
    approved = OrderApprovedEvent(signal=signal, modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get(symbol, [])
    assert len(positions) == 1
    return positions[0]


def _capture_alerts(event_bus: EventBus) -> list[SystemAlertEvent]:
    captured: list[SystemAlertEvent] = []

    async def _on_alert(evt: SystemAlertEvent) -> None:
        captured.append(evt)

    event_bus.subscribe(SystemAlertEvent, _on_alert)
    return captured


def _stage_pending_flatten(
    om: OrderManager,
    broker: MagicMock,
    symbol: str,
    *,
    age_seconds: int = 30,
) -> None:
    """Inject a stale flatten-pending entry that will trip the timeout."""
    om._flatten_pending[symbol] = (
        "old-flatten-order", _time.monotonic() - age_seconds, 0,
    )
    om._pending_orders["old-flatten-order"] = MagicMock(
        symbol=symbol,
        order_type="flatten",
        strategy_id="orb_breakout",
        shares=100,
    )


# ---------------------------------------------------------------------------
# Branch 1 — Long position (BUY) flattens normally
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_def158_retry_long_position_flattens_normally(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
) -> None:
    """Branch 1: broker reports BUY + qty > 0 → resubmit SELL as today.

    The pre-Session-3 happy path. Broker side is explicitly BUY; the
    new gate falls through to the existing flatten-resubmit code.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    await _open_position(om, mock_broker, symbol="AAPL")
    _stage_pending_flatten(om, mock_broker, "AAPL")

    mock_broker.get_positions.return_value = [
        MagicMock(symbol="AAPL", shares=100, side=OrderSide.BUY)
    ]
    mock_broker.place_order.reset_mock()

    await om._check_flatten_pending_timeouts()

    # Branch 1 — SELL was placed for the broker-reported qty.
    mock_broker.place_order.assert_called_once()
    placed_order = mock_broker.place_order.call_args[0][0]
    assert placed_order.side == OrderSide.SELL
    assert placed_order.quantity == 100

    # Flatten-pending updated to the new resubmit order id.
    assert "AAPL" in om._flatten_pending
    assert om._flatten_pending["AAPL"][0] == "resubmit-1"


# ---------------------------------------------------------------------------
# Branch 2 — Short position (SELL) blocks + emits CRITICAL alert
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_def158_retry_short_position_blocks_and_alerts_critical(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Branch 2: broker reports SHORT → refuse retry, emit critical alert.

    Mirrors IMPROMPTU-04 EOD A1 at ``order_manager.py:1888-1904``: the
    SELL would double the short (DEF-204), so refuse and operator-page.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    await _open_position(om, mock_broker, symbol="AAPL")
    _stage_pending_flatten(om, mock_broker, "AAPL")

    mock_broker.get_positions.return_value = [
        MagicMock(symbol="AAPL", shares=100, side=OrderSide.SELL)
    ]
    captured = _capture_alerts(event_bus)
    mock_broker.place_order.reset_mock()

    with caplog.at_level(logging.CRITICAL, logger="argus.execution.order_manager"):
        await om._check_flatten_pending_timeouts()
        # EventBus dispatches handlers as tasks; drain to let the
        # alert-capture coroutine append before assertions.
        await event_bus.drain()

    # No SELL placed — SELL-of-short prevented.
    mock_broker.place_order.assert_not_called()

    # Flatten-pending cleared so the next timeout cycle does not re-emit
    # the alert in an infinite loop.
    assert "AAPL" not in om._flatten_pending

    # Exactly one phantom_short_retry_blocked alert emitted.
    blocked = [
        a for a in captured
        if isinstance(a, SystemAlertEvent)
        and a.alert_type == "phantom_short_retry_blocked"
    ]
    assert len(blocked) == 1, (
        f"Expected exactly one phantom_short_retry_blocked alert; "
        f"got {len(blocked)}: {captured}"
    )
    assert blocked[0].severity == "critical"

    # CRITICAL log line surfaced for operator visibility.
    critical_messages = [
        rec for rec in caplog.records
        if rec.levelno == logging.CRITICAL
        and "Flatten retry refused" in rec.getMessage()
    ]
    assert critical_messages, (
        "Expected CRITICAL 'Flatten retry refused' log line; "
        f"saw: {[r.getMessage() for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# Branch 3 — Unknown side blocks + ERROR log (no alert)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_def158_retry_unknown_side_blocks_and_logs_error(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Branch 3: broker side is None → refuse retry, ERROR log, no alert.

    Defensive code path; the structural defect (malformed Position
    from broker adapter) deserves observability but not an alert that
    would flood every reconciliation cycle.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    await _open_position(om, mock_broker, symbol="AAPL")
    _stage_pending_flatten(om, mock_broker, "AAPL")

    # ``side`` is explicitly None to model a malformed Position.
    mock_broker.get_positions.return_value = [
        MagicMock(symbol="AAPL", shares=100, side=None)
    ]
    captured = _capture_alerts(event_bus)
    mock_broker.place_order.reset_mock()

    with caplog.at_level(logging.ERROR, logger="argus.execution.order_manager"):
        await om._check_flatten_pending_timeouts()
        # Drain even though branch 3 emits no alert — guards against a
        # regression where a future change adds one.
        await event_bus.drain()

    # No SELL placed — defensive refusal.
    mock_broker.place_order.assert_not_called()

    # Flatten-pending cleared (no infinite retry loop).
    assert "AAPL" not in om._flatten_pending

    # No alert emitted — branch 3 is log-only.
    assert not [
        a for a in captured
        if isinstance(a, SystemAlertEvent)
    ], (
        "Branch 3 (unknown side) must NOT emit a SystemAlertEvent; "
        f"got: {captured}"
    )

    # ERROR log line surfaced for operator visibility.
    error_messages = [
        rec for rec in caplog.records
        if rec.levelno == logging.ERROR
        and "Flatten retry refused" in rec.getMessage()
    ]
    assert error_messages, (
        "Expected ERROR 'Flatten retry refused' log line; "
        f"saw: {[r.getMessage() for r in caplog.records]}"
    )


# ---------------------------------------------------------------------------
# Anti-regression — DEF-158 qty-mismatch normal case (BUY) still uses broker qty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_def158_retry_qty_mismatch_long_uses_broker_qty(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
) -> None:
    """DEF-158 anti-regression: ARGUS=100 vs broker=80 (BUY) → SELL 80.

    The qty-mismatch path is independent of side. Branch 1 (BUY)
    falls through to the existing qty-mismatch update; ``sell_qty``
    is rebound to broker_qty before the SELL is placed.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    await _open_position(om, mock_broker, symbol="AAPL")
    _stage_pending_flatten(om, mock_broker, "AAPL")

    # ARGUS thinks 100; broker authoritative is 80.
    mock_broker.get_positions.return_value = [
        MagicMock(symbol="AAPL", shares=80, side=OrderSide.BUY)
    ]
    mock_broker.place_order.reset_mock()

    await om._check_flatten_pending_timeouts()

    mock_broker.place_order.assert_called_once()
    placed_order = mock_broker.place_order.call_args[0][0]
    assert placed_order.side == OrderSide.SELL
    assert placed_order.quantity == 80, (
        "DEF-158 anti-regression: SELL qty must come from the broker "
        "(80), not ARGUS-tracked shares_remaining (100)."
    )


# ---------------------------------------------------------------------------
# Alert payload — phantom_short_retry_blocked metadata shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phantom_short_retry_blocked_alert_severity_is_critical(
    event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
) -> None:
    """Focused verification of the alert payload from Branch 2.

    Asserts ``alert_type``, ``severity``, ``source``, and the full
    structured ``metadata`` dict. The metadata shape is consumed by
    Session 5a.2's auto-resolution policy table; field changes here
    propagate to the policy routing.
    """
    om = _make_om(event_bus, mock_broker, fixed_clock)
    await _open_position(om, mock_broker, symbol="AAPL")
    _stage_pending_flatten(om, mock_broker, "AAPL")

    mock_broker.get_positions.return_value = [
        MagicMock(symbol="AAPL", shares=250, side=OrderSide.SELL)
    ]
    captured = _capture_alerts(event_bus)

    await om._check_flatten_pending_timeouts()
    await event_bus.drain()

    blocked = [
        a for a in captured
        if isinstance(a, SystemAlertEvent)
        and a.alert_type == "phantom_short_retry_blocked"
    ]
    assert len(blocked) == 1
    alert = blocked[0]

    assert alert.severity == "critical"
    assert alert.source == "order_manager._check_flatten_pending_timeouts"
    assert alert.alert_type == "phantom_short_retry_blocked"

    assert alert.metadata is not None
    assert alert.metadata["symbol"] == "AAPL"
    assert alert.metadata["broker_shares"] == 250
    assert alert.metadata["broker_side"] == "SELL"
    assert alert.metadata["expected_side"] == "BUY"
    assert alert.metadata["detection_source"] == "def158_retry"
