"""Sprint 31.91 Session 2a — typed reconciliation contract tests.

Covers the new ``ReconciliationPosition`` frozen dataclass, the refactored
``OrderManager.reconcile_positions`` signature, and the ``main.py`` call
site that builds the typed dict from ``broker.get_positions()``.

The five tests in this module are revert-proof for the Session 2a refactor:

1. ``test_reconciliation_position_dataclass_frozen_round_trip`` — frozen
   dataclass mutability + ``__post_init__`` defensive checks.
2. ``test_reconcile_positions_signature_typed_dict`` — the signature
   accepts the typed dict and rejects the old ``float`` shape.
3. ``test_main_call_site_builds_typed_dict_from_broker_positions`` —
   ``main.py``'s loop body produces a dict whose values are
   ``ReconciliationPosition`` instances with the broker's side preserved.
4. ``test_argus_orphan_branch_unchanged_with_typed_contract`` — the
   existing ARGUS-orphan branch behavior is unchanged after the contract
   refactor (regression-protection).
5. ``test_reconcile_positions_with_pos_missing_side_attribute_fails_closed`` —
   the call site skips a ``Position`` whose ``side`` is ``None`` and
   logs CRITICAL; partial-failure does not crash the loop.
"""

from __future__ import annotations

import asyncio
import dataclasses
import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, ReconciliationConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    PositionClosedEvent,
)
from argus.execution.order_manager import (
    ManagedPosition,
    OrderManager,
    ReconciliationPosition,
)
from argus.models.trading import (
    AssetClass,
    OrderSide,
    Position,
    PositionStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    broker.place_bracket_order = AsyncMock()
    broker.cancel_order = AsyncMock(return_value=True)
    broker.cancel_all_orders = AsyncMock(return_value=0)
    broker.get_positions = AsyncMock(return_value=[])
    return broker


def _make_order_manager(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        reconciliation_config=ReconciliationConfig(auto_cleanup_orphans=True),
    )


def _make_managed_position(
    symbol: str = "AAPL",
    shares: int = 100,
) -> ManagedPosition:
    return ManagedPosition(
        symbol=symbol,
        strategy_id="orb_breakout",
        entry_price=150.0,
        entry_time=datetime(2026, 4, 28, 15, 0, 0, tzinfo=UTC),
        shares_total=shares,
        shares_remaining=shares,
        stop_price=148.0,
        original_stop_price=148.0,
        stop_order_id="stop-1",
        t1_price=152.0,
        t1_order_id="t1-1",
        t1_shares=shares // 2,
        t1_filled=False,
        t2_price=154.0,
        high_watermark=150.0,
    )


def _make_broker_position(
    symbol: str,
    side: OrderSide,
    shares: int,
) -> Position:
    """Build a Position object the same way ``IBKRBroker.get_positions``
    does (`argus/execution/ibkr_broker.py:1021-1035`).
    """
    return Position(
        strategy_id="",
        symbol=symbol,
        asset_class=AssetClass.US_STOCKS,
        side=side,
        status=PositionStatus.OPEN,
        entry_price=150.0,
        entry_time=datetime.now(UTC),
        shares=shares,
        stop_price=0.0,
        target_prices=[],
        current_price=150.0,
        unrealized_pnl=0.0,
    )


# ---------------------------------------------------------------------------
# Test 1: Frozen dataclass round-trip
# ---------------------------------------------------------------------------


def test_reconciliation_position_dataclass_frozen_round_trip() -> None:
    """``ReconciliationPosition`` is frozen and validates inputs.

    The frozen decorator structurally prevents downstream code from
    "patching up" a missing side or fabricating a default — any such
    attempt raises FrozenInstanceError. The ``__post_init__`` defensive
    checks fail closed on shares <= 0 and side is None; both are bugs
    that previously slipped through silently.
    """
    rp = ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=100)
    assert rp.symbol == "AAPL"
    assert rp.side is OrderSide.BUY
    assert rp.shares == 100

    # Frozen: mutation raises FrozenInstanceError.
    with pytest.raises(dataclasses.FrozenInstanceError):
        rp.shares = 200  # type: ignore[misc]
    with pytest.raises(dataclasses.FrozenInstanceError):
        rp.side = OrderSide.SELL  # type: ignore[misc]

    # __post_init__: shares must be positive (defensive against
    # caller-side bugs that pass 0 or negative).
    with pytest.raises(ValueError, match="shares must be positive"):
        ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=0)
    with pytest.raises(ValueError, match="shares must be positive"):
        ReconciliationPosition(symbol="AAPL", side=OrderSide.BUY, shares=-100)

    # __post_init__: side cannot be None (the structural cause of
    # DEF-204 was that side was never carried — the dataclass refuses
    # to be constructed without one).
    with pytest.raises(ValueError, match="side must be set"):
        ReconciliationPosition(
            symbol="AAPL",
            side=None,  # type: ignore[arg-type]
            shares=100,
        )


# ---------------------------------------------------------------------------
# Test 2: Signature accepts typed dict; old shape is rejected
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_positions_signature_typed_dict(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """``reconcile_positions`` accepts ``dict[str, ReconciliationPosition]``.

    Negative case: passing the OLD ``dict[str, float]`` shape causes the
    body's ``.shares`` access to raise AttributeError. This is the
    structural enforcement that prevents accidental contract regression.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    await om.start()

    # Empty typed dict: passes through cleanly.
    result_empty = await om.reconcile_positions({})
    assert result_empty == []

    # Populated typed dict: exercises the full body's ``.shares`` reads.
    typed = {
        "AAPL": ReconciliationPosition(
            symbol="AAPL", side=OrderSide.BUY, shares=100
        ),
        "MSFT": ReconciliationPosition(
            symbol="MSFT", side=OrderSide.SELL, shares=50
        ),
    }
    discrepancies = await om.reconcile_positions(typed)
    # Both symbols are broker-only (no internal positions), so both
    # report mismatch.
    assert len(discrepancies) == 2
    by_sym = {str(d["symbol"]): d for d in discrepancies}
    assert by_sym["AAPL"]["broker_qty"] == 100
    assert by_sym["MSFT"]["broker_qty"] == 50

    # Negative case: legacy float shape blows up at the body's ``.shares``
    # access. AttributeError is the structural canary that the contract
    # is enforced.
    om2 = _make_order_manager(event_bus, mock_broker, fixed_clock)
    await om2.start()
    om2._managed_positions["AAPL"] = [_make_managed_position()]
    with pytest.raises(AttributeError):
        # type: ignore on purpose — we are testing runtime rejection
        # of the deprecated shape.
        await om2.reconcile_positions({"AAPL": 100.0})  # type: ignore[dict-item]

    await om.stop()
    await om2.stop()


# ---------------------------------------------------------------------------
# Test 3: main.py call site builds typed dict from broker positions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_call_site_builds_typed_dict_from_broker_positions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``main.py``'s reconciliation tick converts ``Position`` objects to
    ``ReconciliationPosition`` instances with side preserved.

    Drives one iteration of ``ArgusSystem._run_position_reconciliation``
    by patching ``asyncio.sleep`` to short-circuit and the post-call
    cancellation point to break out of the ``while True`` loop.
    """
    from argus.main import ArgusSystem

    sys_obj = ArgusSystem.__new__(ArgusSystem)
    sys_obj._clock = FixedClock(datetime(2026, 4, 28, 14, 30, 0, tzinfo=UTC))

    broker = AsyncMock()
    broker.get_positions = AsyncMock(
        return_value=[
            _make_broker_position("AAPL", OrderSide.BUY, 100),
            _make_broker_position("MSFT", OrderSide.SELL, 50),
        ]
    )
    sys_obj._broker = broker

    om = AsyncMock()
    om.reconcile_positions = AsyncMock(return_value=[])
    sys_obj._order_manager = om

    # Patch asyncio.sleep so the first cycle starts immediately and the
    # second sleep raises CancelledError to break out of ``while True``.
    sleep_count = {"n": 0}

    async def fake_sleep(_seconds: float) -> None:
        sleep_count["n"] += 1
        if sleep_count["n"] >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr("argus.main.asyncio.sleep", fake_sleep)

    with pytest.raises(asyncio.CancelledError):
        await sys_obj._run_position_reconciliation()

    # reconcile_positions called exactly once with the typed dict.
    om.reconcile_positions.assert_awaited_once()
    (call_arg,), _ = om.reconcile_positions.call_args
    assert isinstance(call_arg, dict)
    assert set(call_arg.keys()) == {"AAPL", "MSFT"}
    aapl = call_arg["AAPL"]
    msft = call_arg["MSFT"]
    assert isinstance(aapl, ReconciliationPosition)
    assert isinstance(msft, ReconciliationPosition)
    assert aapl.side is OrderSide.BUY
    assert aapl.shares == 100
    assert msft.side is OrderSide.SELL
    assert msft.shares == 50


# ---------------------------------------------------------------------------
# Test 4: Existing ARGUS-orphan branch behavior preserved
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_argus_orphan_branch_unchanged_with_typed_contract(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
) -> None:
    """ARGUS-orphan branch (internal > 0, broker == 0) fires identically
    under the new typed contract.

    Setup: ARGUS knows it has 100 shares of AAPL; broker reports zero
    positions. The empty typed dict is the new shape's representation
    of "broker has nothing." Expected outcome: orphan detected,
    cleanup_orphans=True path closes the position with
    ExitReason.RECONCILIATION (the long-standing behavior). The contract
    refactor must not silently change this code path.
    """
    om = _make_order_manager(event_bus, mock_broker, fixed_clock)
    await om.start()

    closed_events: list[PositionClosedEvent] = []

    async def on_close(event: PositionClosedEvent) -> None:
        closed_events.append(event)

    event_bus.subscribe(PositionClosedEvent, on_close)

    pos = _make_managed_position(symbol="AAPL", shares=100)
    om._managed_positions["AAPL"] = [pos]

    # Empty typed dict — broker reports nothing, ARGUS has AAPL.
    discrepancies = await om.reconcile_positions({})
    await event_bus.drain()

    # Same outputs as before the contract change:
    # 1. exactly one mismatch detected.
    assert len(discrepancies) == 1
    assert discrepancies[0]["symbol"] == "AAPL"
    assert discrepancies[0]["internal_qty"] == 100
    assert discrepancies[0]["broker_qty"] == 0

    # 2. orphan cleanup fired with ExitReason.RECONCILIATION.
    assert len(closed_events) == 1
    assert closed_events[0].exit_reason == ExitReason.RECONCILIATION

    # 3. position is fully closed.
    assert om.get_all_positions_flat() == []

    await om.stop()


# ---------------------------------------------------------------------------
# Test 5: Fail-closed when broker Position has side=None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reconcile_positions_with_pos_missing_side_attribute_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The ``main.py`` call site skips a Position whose ``side`` is None
    and emits CRITICAL; remaining positions continue to be reconciled.

    This is the fail-closed posture. A side-less Position is a broker-
    layer bug; the reconciliation loop logs and skips rather than
    fabricating a default direction (which would silently re-create
    DEF-204's mechanism).
    """
    from argus.main import ArgusSystem

    sys_obj = ArgusSystem.__new__(ArgusSystem)
    sys_obj._clock = FixedClock(datetime(2026, 4, 28, 14, 30, 0, tzinfo=UTC))

    # First Position has side=None (the bug-shape); second is well-formed.
    bad_pos = MagicMock(spec=Position)
    bad_pos.symbol = "BADSYM"
    bad_pos.shares = 75
    bad_pos.side = None

    good_pos = _make_broker_position("AAPL", OrderSide.BUY, 100)

    broker = AsyncMock()
    broker.get_positions = AsyncMock(return_value=[bad_pos, good_pos])
    sys_obj._broker = broker

    om = AsyncMock()
    om.reconcile_positions = AsyncMock(return_value=[])
    sys_obj._order_manager = om

    sleep_count = {"n": 0}

    async def fake_sleep(_seconds: float) -> None:
        sleep_count["n"] += 1
        if sleep_count["n"] >= 2:
            raise asyncio.CancelledError()

    monkeypatch.setattr("argus.main.asyncio.sleep", fake_sleep)

    with caplog.at_level(logging.CRITICAL, logger="argus.main"):
        with pytest.raises(asyncio.CancelledError):
            await sys_obj._run_position_reconciliation()

    # Bad position skipped; good position reconciled normally; the loop
    # did not crash and reconcile_positions was still invoked once.
    om.reconcile_positions.assert_awaited_once()
    (call_arg,), _ = om.reconcile_positions.call_args
    assert "BADSYM" not in call_arg
    assert "AAPL" in call_arg
    assert isinstance(call_arg["AAPL"], ReconciliationPosition)

    # CRITICAL log line names the symbol.
    critical_messages = [
        r.message for r in caplog.records if r.levelno == logging.CRITICAL
    ]
    assert any("BADSYM" in m and "missing side" in m for m in critical_messages), (
        f"Expected CRITICAL log naming BADSYM and 'missing side'; got: "
        f"{critical_messages!r}"
    )
