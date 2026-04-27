"""Sprint 31.91 Session 1b — Standalone-SELL OCA threading tests.

Verifies that ``ManagedPosition.oca_group_id`` is threaded onto every SELL
``Order`` placed by the four standalone-SELL paths in
``argus/execution/order_manager.py``:

1. ``_trail_flatten``
2. ``_escalation_update_stop``
3. ``_resubmit_stop_with_retry`` (via ``_submit_stop_order``, the actual
   placement site)
4. ``_flatten_position``

Also verifies the ``oca_group_id is None`` fall-through (legacy no-OCA
behavior preserved for ``reconstruct_from_broker``-derived positions),
the two-paths-same-OCA race window, and Error 201 / "OCA group is
already filled" graceful handling — INFO log, ``redundant_exit_observed``
marker, no DEF-158 retry path entry. Distinguishes generic Error 201
(margin) which preserves the existing ERROR-and-retry flow.

These tests use IBKR-style ``MagicMock`` brokers per regression
invariant 21 — see
``tests/_regression_guards/test_oca_simulated_broker_tautology.py`` for
the rationale on which broker fixtures are appropriate for OCA
assertions.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    EscalationPhase,
    ExitEscalationConfig,
    ExitManagementConfig,
    OrderManagerConfig,
    TrailingStopConfig,
)
from argus.core.event_bus import EventBus
from argus.core.exit_math import StopToLevel
from argus.execution.order_manager import (
    _OCA_TYPE_BRACKET,
    ManagedPosition,
    OrderManager,
)
from argus.models.trading import (
    OrderResult,
    OrderSide,
    OrderStatus,
)


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


_OCA_TEST_GROUP = "oca_test"


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 4, 1, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def mock_broker() -> MagicMock:
    broker = MagicMock()
    counter = {"n": 0}

    async def _place(order):  # noqa: ANN001
        counter["n"] += 1
        return OrderResult(
            order_id=f"placed-{counter['n']}",
            broker_order_id=f"broker-{counter['n']}",
            status=OrderStatus.PENDING,
        )

    broker.place_order = AsyncMock(side_effect=_place)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    return broker


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    *,
    exit_config: ExitManagementConfig | None = None,
    config: OrderManagerConfig | None = None,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=config or OrderManagerConfig(),
        exit_config=exit_config,
    )


def _make_position(
    om: OrderManager,
    *,
    oca_group_id: str | None = _OCA_TEST_GROUP,
    symbol: str = "AAPL",
    strategy_id: str = "orb_breakout",
    entry_time: datetime | None = None,
    shares: int = 100,
    entry_price: float = 150.0,
    stop_price: float = 148.0,
) -> ManagedPosition:
    """Construct a ManagedPosition directly and register it with the OM.

    Bypasses ``on_approved`` / ``on_fill`` so the test can set
    ``oca_group_id`` to a known value (or ``None`` for the fall-through
    case) without depending on the bracket-placement code path.
    """
    et = entry_time or datetime(2026, 4, 1, 14, 30, 0, tzinfo=UTC)
    pos = ManagedPosition(
        symbol=symbol,
        strategy_id=strategy_id,
        entry_price=entry_price,
        entry_time=et,
        shares_total=shares,
        shares_remaining=shares,
        stop_price=stop_price,
        original_stop_price=stop_price,
        stop_order_id="bracket-stop-id",
        t1_price=152.0,
        t1_order_id="bracket-t1-id",
        t1_shares=50,
        t1_filled=False,
        t2_price=154.0,
        high_watermark=entry_price,
        oca_group_id=oca_group_id,
    )
    om._managed_positions.setdefault(symbol, []).append(pos)
    return pos


def _last_placed_sell_order(broker: MagicMock):
    """Return the last Order argument passed to broker.place_order."""
    assert broker.place_order.call_args is not None, (
        "broker.place_order was not called"
    )
    return broker.place_order.call_args[0][0]


# IBKR-shaped Error 201 exception payloads. ``ib_async`` raises Exception
# subclasses whose ``str(exc)`` carries the IBKR reason string;
# ``_is_oca_already_filled_error`` matches against that lowercased
# representation.
def _oca_filled_error() -> Exception:
    return RuntimeError(
        "IBKR error 201, reqId 7: OCA group is already filled."
    )


def _generic_201_margin_error() -> Exception:
    return RuntimeError(
        "IBKR error 201: Order rejected — Margin requirement not met."
    )


# ---------------------------------------------------------------------------
# Test 1 — _trail_flatten threads OCA
# ---------------------------------------------------------------------------


class TestThreadingPerPath:

    @pytest.mark.asyncio
    async def test_trail_flatten_threads_oca_group(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        position.trail_active = True
        position.trail_stop_price = 149.0

        await om._trail_flatten(position, current_price=148.5)

        placed = _last_placed_sell_order(mock_broker)
        assert placed.side == OrderSide.SELL
        assert placed.ocaGroup == _OCA_TEST_GROUP
        assert placed.ocaType == _OCA_TYPE_BRACKET == 1

    @pytest.mark.asyncio
    async def test_escalation_update_stop_threads_oca_group(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)

        await om._escalation_update_stop(position, new_stop_price=150.0)

        placed = _last_placed_sell_order(mock_broker)
        assert placed.side == OrderSide.SELL
        assert placed.ocaGroup == _OCA_TEST_GROUP
        assert placed.ocaType == _OCA_TYPE_BRACKET

    @pytest.mark.asyncio
    async def test_resubmit_stop_with_retry_threads_oca_group(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """``_resubmit_stop_with_retry`` indirectly places SELL via
        ``_submit_stop_order`` — that's where threading happens."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        # Drop stale stop_order_id so _submit_stop_order resubmits cleanly
        position.stop_order_id = None

        await om._resubmit_stop_with_retry(position)

        placed = _last_placed_sell_order(mock_broker)
        assert placed.side == OrderSide.SELL
        assert placed.ocaGroup == _OCA_TEST_GROUP
        assert placed.ocaType == _OCA_TYPE_BRACKET
        # DEC-372 retry-cap state still functional: counter incremented to 1
        assert om._stop_retry_count.get("AAPL") == 1

    @pytest.mark.asyncio
    async def test_flatten_position_threads_oca_group(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)

        await om._flatten_position(position, reason="test")

        placed = _last_placed_sell_order(mock_broker)
        assert placed.side == OrderSide.SELL
        assert placed.ocaGroup == _OCA_TEST_GROUP
        assert placed.ocaType == _OCA_TYPE_BRACKET


# ---------------------------------------------------------------------------
# Test 5 — None oca_group_id falls through to legacy
# ---------------------------------------------------------------------------


class TestFallthroughWhenNone:

    @pytest.mark.asyncio
    async def test_oca_threading_falls_through_when_oca_group_id_none(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """``oca_group_id is None`` (e.g., reconstructed positions) MUST
        place SELLs with ocaGroup=None and ocaType=0 — the
        ``Order`` model's defaults — preserving legacy no-OCA
        behavior."""
        om = _make_om(event_bus, mock_broker, fixed_clock)

        # Path 1: trail_flatten
        pos_a = _make_position(om, oca_group_id=None, symbol="AAA")
        pos_a.trail_active = True
        pos_a.trail_stop_price = 149.0
        await om._trail_flatten(pos_a, current_price=148.5)
        placed = _last_placed_sell_order(mock_broker)
        assert placed.ocaGroup is None
        assert placed.ocaType == 0

        # Path 2: escalation
        pos_b = _make_position(om, oca_group_id=None, symbol="BBB")
        await om._escalation_update_stop(pos_b, new_stop_price=150.0)
        placed = _last_placed_sell_order(mock_broker)
        assert placed.ocaGroup is None
        assert placed.ocaType == 0

        # Path 3: _submit_stop_order (resubmit retry path)
        pos_c = _make_position(om, oca_group_id=None, symbol="CCC")
        pos_c.stop_order_id = None
        await om._resubmit_stop_with_retry(pos_c)
        placed = _last_placed_sell_order(mock_broker)
        assert placed.ocaGroup is None
        assert placed.ocaType == 0

        # Path 4: flatten_position
        pos_d = _make_position(om, oca_group_id=None, symbol="DDD")
        await om._flatten_position(pos_d, reason="test")
        placed = _last_placed_sell_order(mock_broker)
        assert placed.ocaGroup is None
        assert placed.ocaType == 0


# ---------------------------------------------------------------------------
# Test 6 — Race window: two paths fire, both share OCA
# ---------------------------------------------------------------------------


class TestRaceWindowSameOcaGroup:

    @pytest.mark.asyncio
    async def test_race_window_two_paths_same_oca_group(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """Two of the four threaded paths firing on the same position
        must both stamp the SAME ``ocaGroup``. IBKR's atomic OCA
        cancellation handles the actual race resolution; this unit test
        verifies the ARGUS-side stamping invariant."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        position.trail_active = True
        position.trail_stop_price = 149.0

        await om._trail_flatten(position, current_price=148.5)
        # Manually clear flatten_pending to allow the second path to fire
        # (in production IBKR would atomically cancel one; here we just
        # exercise the stamping invariant).
        om._flatten_pending.clear()
        # Reset position state to allow escalation to fire fresh
        position.shares_remaining = 100
        position.stop_order_id = None

        await om._escalation_update_stop(position, new_stop_price=150.0)

        # Both place_order calls should carry the same ocaGroup
        all_calls = mock_broker.place_order.call_args_list
        assert len(all_calls) >= 2
        oca_groups = [c[0][0].ocaGroup for c in all_calls]
        assert all(g == _OCA_TEST_GROUP for g in oca_groups), oca_groups
        oca_types = [c[0][0].ocaType for c in all_calls]
        assert all(t == _OCA_TYPE_BRACKET for t in oca_types), oca_types


# ---------------------------------------------------------------------------
# Test 8 — Error 201 OCA-filled handling
# ---------------------------------------------------------------------------


class TestError201OcaFilledHandling:

    @pytest.mark.asyncio
    async def test_oca_filled_logged_info_not_error_in_flatten_position(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """OCA-already-filled signature → INFO log,
        ``redundant_exit_observed`` flipped, ``_flatten_pending`` NOT
        seeded (DEF-158 retry path NOT triggered)."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)

        mock_broker.place_order = AsyncMock(side_effect=_oca_filled_error())

        with caplog.at_level(logging.DEBUG, logger="argus.execution.order_manager"):
            await om._flatten_position(position, reason="test")

        # 1. redundant_exit_observed marker set
        assert position.redundant_exit_observed is True

        # 2. INFO log emitted with the "redundant SELL skipped" phrase;
        #    NO ERROR-level log for the OCA-filled signature.
        info_records = [
            rec for rec in caplog.records
            if rec.levelno == logging.INFO
            and "OCA group already filled" in rec.getMessage()
            and "redundant SELL skipped" in rec.getMessage()
        ]
        assert info_records, (
            f"Expected INFO log for OCA-already-filled; got: "
            f"{[(r.levelname, r.getMessage()) for r in caplog.records]}"
        )
        error_records_oca = [
            rec for rec in caplog.records
            if rec.levelno >= logging.ERROR
            and "OCA group already filled" in rec.getMessage()
        ]
        assert not error_records_oca, (
            f"OCA-filled must NOT log at ERROR; got: "
            f"{[r.getMessage() for r in error_records_oca]}"
        )

        # 3. _flatten_pending was NOT populated (DEF-158 short-circuit)
        assert "AAPL" not in om._flatten_pending

    @pytest.mark.asyncio
    async def test_oca_filled_marks_redundant_in_trail_flatten(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        position.trail_active = True
        position.trail_stop_price = 149.0

        mock_broker.place_order = AsyncMock(side_effect=_oca_filled_error())

        with caplog.at_level(logging.DEBUG, logger="argus.execution.order_manager"):
            await om._trail_flatten(position, current_price=148.5)

        assert position.redundant_exit_observed is True
        # _flatten_pending must NOT have been seeded by the failed SELL
        assert "AAPL" not in om._flatten_pending

    @pytest.mark.asyncio
    async def test_oca_filled_marks_redundant_in_escalation(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)

        mock_broker.place_order = AsyncMock(side_effect=_oca_filled_error())

        await om._escalation_update_stop(position, new_stop_price=150.0)

        assert position.redundant_exit_observed is True
        # No emergency flatten triggered (no second place_order, since the
        # OCA-filled branch returns short-circuit BEFORE the
        # ``_flatten_position`` fallback).
        assert "AAPL" not in om._flatten_pending

    @pytest.mark.asyncio
    async def test_oca_filled_marks_redundant_in_submit_stop_order(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
    ) -> None:
        """``_submit_stop_order`` retry-loop short-circuits on the
        OCA-filled signature: no retry, no emergency flatten."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        position.stop_order_id = None

        mock_broker.place_order = AsyncMock(side_effect=_oca_filled_error())

        await om._resubmit_stop_with_retry(position)

        assert position.redundant_exit_observed is True
        # Only ONE place_order attempt (no retry loop iterations after
        # the OCA-filled signature). DEC-372 retry counter still ticked
        # forward by ``_resubmit_stop_with_retry`` itself.
        assert mock_broker.place_order.call_count == 1
        assert "AAPL" not in om._flatten_pending

    @pytest.mark.asyncio
    async def test_generic_201_margin_error_logs_error_and_retries(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        fixed_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Distinguishing case (regression invariant): generic Error 201
        (margin requirement) MUST still log at ERROR / retry / fall
        through to emergency flatten — the existing pre-Sprint-31.91
        behavior."""
        om = _make_om(event_bus, mock_broker, fixed_clock)
        position = _make_position(om, oca_group_id=_OCA_TEST_GROUP)
        position.stop_order_id = None

        # Margin error every time → retry loop exhausts → emergency
        # flatten via ``_flatten_position`` is invoked.
        mock_broker.place_order = AsyncMock(side_effect=_generic_201_margin_error())

        with caplog.at_level(logging.WARNING, logger="argus.execution.order_manager"):
            await om._resubmit_stop_with_retry(position)

        # Generic Error 201 path: redundant_exit_observed must remain
        # False (this is NOT a SAFE OCA-filled outcome).
        assert position.redundant_exit_observed is False

        # Retry loop exercises stop_retry_max+1 attempts in
        # _submit_stop_order; verify multiple retries took place.
        assert mock_broker.place_order.call_count >= 2

        # An ERROR or EXCEPTION-level record exists (the "Stop retry
        # failed" emergency-flatten log emitted by _submit_stop_order
        # when retries exhaust).
        error_records = [
            rec for rec in caplog.records if rec.levelno >= logging.ERROR
        ]
        assert error_records, (
            "Generic Error 201 must surface at ERROR severity (retry "
            "exhaustion); got no ERROR records."
        )
