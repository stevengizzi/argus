# allow-oca-sim: this file references "SimulatedBroker" only in its module
# docstring (citing the regression-guard sibling for context). All actual
# OCA-cancellation assertions in this file use IBKR mocks (mock_ib +
# patched IBKRBroker), not SimulatedBroker — invariant 21 spirit upheld.
"""Sprint 31.91 Session 1a — Bracket OCA grouping + Error 201 defensive handling.

Covers D2 acceptance criteria:
1. Bracket children carry ``ocaGroup == oca_group_id`` and ``ocaType == 1``.
2. ``oca_group_id`` persists from broker through to ``ManagedPosition``.
3. ``reconstruct_from_broker``-derived positions have ``oca_group_id is None``.
4. Re-entry on the same symbol generates a fresh ``oca_group_id``.
5. ``IBKRConfig.bracket_oca_type`` accepts only 0 or 1 (Pydantic validator).
6. DEC-117 atomic-bracket rollback fires end-to-end with ``ocaType=1``.
7. ``oca_group_id == f"oca_{parent_ulid}"`` deterministic derivation.
8. Defensive Error 201 / "OCA group is already filled" handled at INFO not
   ERROR; rollback STILL fires; distinguishing test for generic Error 201
   still treated as ERROR.
9. Config-validation: ``ibkr.bracket_oca_type`` present in both
   ``config/system.yaml`` and ``config/system_live.yaml``; YAML keys are a
   subset of the Pydantic ``IBKRConfig`` model fields (no silent drop).

All tests use ``unittest.mock`` against ``argus.execution.ibkr_broker.IB``
or the ``OrderManager`` mock-broker pattern. Per Sprint 31.91 regression
invariant 21, OCA-behavior tests MUST use IBKR mocks rather than
``SimulatedBroker`` — see ``tests/_regression_guards/test_oca_simulated_broker_tautology.py``.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml
from pydantic import ValidationError

from argus.core.clock import FixedClock
from argus.core.config import IBKRConfig, OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    Side,
    SignalEvent,
)
from argus.execution.ibkr_broker import IBKRBroker
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.models.trading import (
    BracketOrderResult,
    Order,
    OrderResult,
    OrderSide,
    OrderStatus,
    OrderType,
)

if TYPE_CHECKING:
    from ib_async import Order as IBOrder
    from ib_async import Stock


# ---------------------------------------------------------------------------
# Mocks for IBKRBroker tests (mirrors tests/execution/test_ibkr_broker.py)
# ---------------------------------------------------------------------------


class _MockEvent:
    """Mock event object that tracks ``+=`` subscriptions."""

    def __init__(self) -> None:
        self.handlers: list = []

    def __iadd__(self, handler):
        self.handlers.append(handler)
        return self


def _build_mock_ib() -> MagicMock:
    """Construct a mock ``ib_async.IB`` instance for IBKR broker tests."""
    ib = MagicMock()
    ib.isConnected.return_value = True
    ib.managedAccounts.return_value = ["U24619949"]
    ib.positions.return_value = []
    ib.openTrades.return_value = []
    ib.trades.return_value = []
    ib.accountValues.return_value = []
    ib.orderStatusEvent = _MockEvent()
    ib.errorEvent = _MockEvent()
    ib.disconnectedEvent = _MockEvent()
    ib.connectedEvent = _MockEvent()
    ib.newOrderEvent = _MockEvent()
    ib.connectAsync = AsyncMock()

    order_id_counter = itertools.count(1)

    def make_trade(contract: Stock, order: IBOrder) -> MagicMock:
        trade = MagicMock()
        trade.order = order
        trade.contract = contract
        trade.orderStatus = MagicMock()
        trade.orderStatus.status = "Submitted"
        trade.orderStatus.filled = 0
        trade.orderStatus.remaining = order.totalQuantity
        trade.orderStatus.avgFillPrice = 0.0
        trade.fills = []
        if not hasattr(order, "_mock_order_id"):
            order._mock_order_id = next(order_id_counter)
            order.orderId = order._mock_order_id
        return trade

    ib.placeOrder = MagicMock(side_effect=make_trade)
    ib.cancelOrder = MagicMock()
    ib.reqGlobalCancel = MagicMock()
    return ib


@pytest.fixture
def mock_ib() -> MagicMock:
    return _build_mock_ib()


@pytest.fixture
def ibkr_config() -> IBKRConfig:
    return IBKRConfig(
        host="127.0.0.1",
        port=4002,
        client_id=1,
        account="U24619949",
        timeout_seconds=10.0,
        readonly=False,
    )


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


def _bracket_orders(
    symbol: str = "AAPL",
    t2_price: float | None = 160.0,
    t2_quantity: int | None = 50,
) -> tuple[Order, Order, list[Order]]:
    """Build (entry, stop, [t1, t2]) Order triple for bracket placement."""
    entry = Order(
        strategy_id="test",
        symbol=symbol,
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        quantity=100,
    )
    stop = Order(
        strategy_id="test",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.STOP,
        quantity=100,
        stop_price=145.0,
    )
    t1 = Order(
        strategy_id="test",
        symbol=symbol,
        side=OrderSide.SELL,
        order_type=OrderType.LIMIT,
        quantity=50,
        limit_price=155.0,
    )
    targets: list[Order] = [t1]
    if t2_price is not None and t2_quantity is not None:
        t2 = Order(
            strategy_id="test",
            symbol=symbol,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            quantity=t2_quantity,
            limit_price=t2_price,
        )
        targets.append(t2)
    return entry, stop, targets


# ---------------------------------------------------------------------------
# Test 1 — Bracket children carry oca_group_id + ocaType=1
# ---------------------------------------------------------------------------


class TestBracketChildrenCarryOcaGroup:
    """All 3 bracket children (stop, T1, T2) carry the OCA decoration."""

    @pytest.mark.asyncio
    async def test_bracket_children_carry_oca_group(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Stop, T1, and T2 are decorated with ocaGroup and ocaType=1."""
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()
            result = await broker.place_bracket_order(entry, stop, targets)

            calls = mock_ib.placeOrder.call_args_list
            # 4 calls: parent (entry), stop, T1, T2
            assert len(calls) == 4

            # Parent (entry) MUST NOT carry an OCA group — only children do.
            # ARGUS-side rationale: an entry-fill should not OCA-cancel its
            # own protection legs. The default for an ib_async Order's
            # ocaGroup is "" / None depending on attribute initialization;
            # we assert it was not assigned the bracket's group.
            parent_ib = calls[0][0][1]
            expected_oca = f"oca_{result.entry.order_id}"
            assert getattr(parent_ib, "ocaGroup", None) != expected_oca, (
                "Parent (entry) order MUST NOT be in the bracket's OCA group"
            )

            # Children MUST carry ocaGroup == oca_group_id and ocaType == 1
            for i, child_call in enumerate(calls[1:], start=1):
                child_ib = child_call[0][1]
                assert child_ib.ocaGroup == expected_oca, (
                    f"Child {i} ocaGroup mismatch: "
                    f"expected {expected_oca!r}, got {child_ib.ocaGroup!r}"
                )
                assert child_ib.ocaType == 1, (
                    f"Child {i} ocaType mismatch: expected 1, got {child_ib.ocaType}"
                )

    @pytest.mark.asyncio
    async def test_parent_id_linkage_preserved(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Adding ocaGroup/ocaType MUST NOT alter the parentId linkage
        between parent (entry) and the three children. DEC-117 invariant.
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()
            await broker.place_bracket_order(entry, stop, targets)

            calls = mock_ib.placeOrder.call_args_list
            parent_id = calls[0][0][1].orderId
            for i, call in enumerate(calls[1:], start=1):
                child_ib = call[0][1]
                assert child_ib.parentId == parent_id, (
                    f"Child {i} parentId broken by OCA decoration"
                )

    @pytest.mark.asyncio
    async def test_transmit_pattern_preserved(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Transmit-flag pattern preserved: only the LAST order has
        ``transmit=True``. Adding ocaGroup must not change transmit semantics.
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()
            await broker.place_bracket_order(entry, stop, targets)

            calls = mock_ib.placeOrder.call_args_list
            # parent, stop, T1: transmit=False; T2 (last): transmit=True
            assert calls[0][0][1].transmit is False
            assert calls[1][0][1].transmit is False
            assert calls[2][0][1].transmit is False
            assert calls[3][0][1].transmit is True


# ---------------------------------------------------------------------------
# Test 7 — Deterministic OCA group derivation from parent ULID
# ---------------------------------------------------------------------------


class TestOcaGroupDeterministicFromParentUlid:
    """oca_group_id == f"oca_{parent_ulid}" — formula directly."""

    @pytest.mark.asyncio
    async def test_oca_group_deterministic_from_parent_ulid(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """The OCA group ID returned in the BracketOrderResult is
        ``f"oca_{result.entry.order_id}"`` — verify against children's
        actually-set ocaGroup.
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()
            result = await broker.place_bracket_order(entry, stop, targets)

            expected = f"oca_{result.entry.order_id}"
            calls = mock_ib.placeOrder.call_args_list
            for i, call in enumerate(calls[1:], start=1):
                child_ib = call[0][1]
                assert child_ib.ocaGroup == expected, (
                    f"Child {i} OCA group {child_ib.ocaGroup!r} != "
                    f"f'oca_{{parent_ulid}}' = {expected!r}"
                )


# ---------------------------------------------------------------------------
# Test 6 — DEC-117 rollback under ocaType=1 still cancels the parent
# ---------------------------------------------------------------------------


class TestDec117RollbackWithOcaType1:
    """DEC-117 atomic-bracket rollback behavior unchanged by OCA decoration."""

    @pytest.mark.asyncio
    async def test_dec117_rollback_with_oca_type_1_cancels_partial_children(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus
    ) -> None:
        """Force the T2 placement to raise mid-loop (after stop and T1
        placed, before T2 placed). Rollback path at ``ibkr_broker.py:783-805``
        equivalent fires; parent order is cancelled. DEC-117 invariant must
        hold end-to-end with ocaType=1 in effect.
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()
            assert len(targets) == 2  # T1 + T2

            # Inject a failure on the 4th placeOrder call (T2).
            # Calls so far: parent (1), stop (2), T1 (3), T2 (4 — explodes).
            order_id_counter = itertools.count(100)
            real_ib_placeOrder_inputs = []

            def _flaky_place_order(contract, order):
                real_ib_placeOrder_inputs.append((contract, order))
                if len(real_ib_placeOrder_inputs) == 4:
                    raise RuntimeError("Simulated IBKR placement failure on T2")
                # Mimic make_trade behavior
                trade = MagicMock()
                trade.order = order
                trade.contract = contract
                trade.orderStatus = MagicMock()
                trade.orderStatus.status = "Submitted"
                trade.orderStatus.filled = 0
                trade.orderStatus.remaining = order.totalQuantity
                trade.orderStatus.avgFillPrice = 0.0
                trade.fills = []
                if not hasattr(order, "orderId") or order.orderId in (None, 0):
                    order.orderId = next(order_id_counter)
                return trade

            mock_ib.placeOrder.side_effect = _flaky_place_order

            with pytest.raises(RuntimeError, match="Simulated IBKR placement failure"):
                await broker.place_bracket_order(entry, stop, targets)

            # The rollback must have called cancelOrder on the parent.
            # parent_trade.order is the first placeOrder input's order arg.
            parent_order = real_ib_placeOrder_inputs[0][1]
            mock_ib.cancelOrder.assert_called_once_with(parent_order)

    @pytest.mark.asyncio
    async def test_dec117_rollback_logs_warning_for_generic_failure(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Generic placement failure (not OCA-filled) is logged at WARNING.

        Distinguishing assertion against the OCA-filled INFO path (Test 8).
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()

            order_id_counter = itertools.count(200)

            def _flaky_place_order(contract, order):
                # Fail T2 with a non-OCA error
                if hasattr(order, "ocaGroup") and order.ocaGroup and order.lmtPrice == 160.0:
                    raise RuntimeError("Margin requirement not met")
                trade = MagicMock()
                trade.order = order
                trade.contract = contract
                trade.orderStatus = MagicMock()
                trade.orderStatus.status = "Submitted"
                trade.fills = []
                if not hasattr(order, "orderId") or order.orderId in (None, 0):
                    order.orderId = next(order_id_counter)
                return trade

            mock_ib.placeOrder.side_effect = _flaky_place_order

            caplog.set_level(logging.INFO, logger="argus.execution.ibkr_broker")
            with pytest.raises(RuntimeError, match="Margin requirement not met"):
                await broker.place_bracket_order(entry, stop, targets)

            warning_records = [
                r
                for r in caplog.records
                if r.levelno == logging.WARNING
                and "place_bracket_order failed" in r.getMessage()
            ]
            info_records_oca = [
                r
                for r in caplog.records
                if r.levelno == logging.INFO
                and "OCA group already filled" in r.getMessage()
            ]
            assert warning_records, (
                "Generic placement failure must log at WARNING "
                "(distinguishing from OCA-filled INFO path)"
            )
            assert not info_records_oca, (
                "Generic placement failure must NOT use the OCA-filled INFO path"
            )


# ---------------------------------------------------------------------------
# Test 8 — Error 201 "OCA group is already filled" is logged INFO; rollback fires
# ---------------------------------------------------------------------------


class TestErrorOcaAlreadyFilledHandling:
    """Defensive handling for IBKR Error 201 / 'OCA group is already filled'."""

    @pytest.mark.asyncio
    async def test_t1_t2_placement_error_201_oca_filled_handled_gracefully(
        self, mock_ib: MagicMock, ibkr_config: IBKRConfig, event_bus: EventBus,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """If T2 placement raises with 'OCA group is already filled':
        - Logged at INFO (not WARNING/ERROR).
        - Rollback STILL fires (parent cancelled).
        - No orphaned OCA-A working orders remain (parent cancelled).
        - The exception still propagates so callers can react.
        """
        with patch("argus.execution.ibkr_broker.IB", return_value=mock_ib):
            broker = IBKRBroker(ibkr_config, event_bus)
            await broker.connect()

            entry, stop, targets = _bracket_orders()

            order_id_counter = itertools.count(300)
            placed: list = []

            def _flaky_place_order(contract, order):
                placed.append((contract, order))
                # Fail on 4th call (T2) with the OCA-filled error string
                if len(placed) == 4:
                    raise RuntimeError(
                        "Order Rejected - reason: OCA group is already filled"
                    )
                trade = MagicMock()
                trade.order = order
                trade.contract = contract
                trade.orderStatus = MagicMock()
                trade.orderStatus.status = "Submitted"
                trade.fills = []
                if not hasattr(order, "orderId") or order.orderId in (None, 0):
                    order.orderId = next(order_id_counter)
                return trade

            mock_ib.placeOrder.side_effect = _flaky_place_order

            caplog.set_level(logging.INFO, logger="argus.execution.ibkr_broker")
            with pytest.raises(RuntimeError, match="OCA group is already filled"):
                await broker.place_bracket_order(entry, stop, targets)

            # Rollback fired
            parent_order = placed[0][1]
            mock_ib.cancelOrder.assert_called_once_with(parent_order)

            # Logged INFO — not WARNING / ERROR — for the OCA-filled case
            info_records = [
                r
                for r in caplog.records
                if r.levelno == logging.INFO
                and "OCA group already filled" in r.getMessage()
            ]
            assert info_records, (
                "OCA-filled rollback must log at INFO with the "
                "'OCA group already filled' message"
            )

            warning_records = [
                r
                for r in caplog.records
                if r.levelno == logging.WARNING
                and "place_bracket_order failed" in r.getMessage()
            ]
            assert not warning_records, (
                "OCA-filled rollback must NOT use the generic-failure WARNING path"
            )

    def test_oca_already_filled_helper_classification(self) -> None:
        """``_is_oca_already_filled_error`` classifies known error strings."""
        from argus.execution.ibkr_broker import _is_oca_already_filled_error

        # Positive cases
        assert _is_oca_already_filled_error(
            Exception("Order Rejected - reason: OCA group is already filled")
        ) is True
        assert _is_oca_already_filled_error(
            Exception("OCA group is already filled.")
        ) is True
        # Case-insensitive
        assert _is_oca_already_filled_error(
            Exception("OCA Group Is Already Filled")
        ) is True

        # Negative cases — generic Error 201
        assert _is_oca_already_filled_error(
            Exception("Margin requirement not met")
        ) is False
        assert _is_oca_already_filled_error(
            Exception("Price-protection rejected the order")
        ) is False
        assert _is_oca_already_filled_error(
            Exception("Insufficient buying power")
        ) is False

        # Defensive: non-exception input
        assert _is_oca_already_filled_error("not an exception") is False  # type: ignore[arg-type]
        assert _is_oca_already_filled_error(None) is False  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Test 5 — IBKRConfig.bracket_oca_type Pydantic validator
# ---------------------------------------------------------------------------


class TestBracketOcaTypeConfigValidation:
    """``bracket_oca_type`` accepts only 0 or 1; ocaType=2 rejected."""

    def test_default_is_one(self) -> None:
        assert IBKRConfig().bracket_oca_type == 1

    def test_zero_accepted(self) -> None:
        assert IBKRConfig(bracket_oca_type=0).bracket_oca_type == 0

    def test_one_accepted(self) -> None:
        assert IBKRConfig(bracket_oca_type=1).bracket_oca_type == 1

    def test_two_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IBKRConfig(bracket_oca_type=2)

    def test_negative_rejected(self) -> None:
        with pytest.raises(ValidationError):
            IBKRConfig(bracket_oca_type=-1)


# ---------------------------------------------------------------------------
# YAML / Pydantic config alignment
# ---------------------------------------------------------------------------


class TestBracketOcaTypeYamlAlignment:
    """``ibkr.bracket_oca_type`` present in both YAMLs and matches Pydantic."""

    def test_bracket_oca_type_yaml_loadable_no_silent_drop(self) -> None:
        """Sprint 31.91 Session 1a: verify config field added to YAML
        matches Pydantic model field name (no silent drop).
        """
        with open("config/system.yaml") as fh:
            cfg = yaml.safe_load(fh)
        ibkr_cfg = cfg.get("ibkr", {})
        assert "bracket_oca_type" in ibkr_cfg, (
            "config/system.yaml must include ibkr.bracket_oca_type "
            "explicitly; relying on Pydantic default hides the contract."
        )
        # Verify YAML keys are subset of model fields (no silent drop)
        yaml_keys = set(ibkr_cfg.keys())
        model_fields = set(IBKRConfig.model_fields.keys())
        extra = yaml_keys - model_fields
        assert not extra, f"YAML keys not in Pydantic model: {extra}"

        # Same for system_live.yaml
        with open("config/system_live.yaml") as fh:
            cfg_live = yaml.safe_load(fh)
        ibkr_cfg_live = cfg_live.get("ibkr", {})
        assert "bracket_oca_type" in ibkr_cfg_live
        extra_live = set(ibkr_cfg_live.keys()) - model_fields
        assert not extra_live, f"system_live.yaml keys not in Pydantic model: {extra_live}"


# ---------------------------------------------------------------------------
# Tests 2, 3, 4 — ManagedPosition.oca_group_id lifecycle
# ---------------------------------------------------------------------------


def _mock_order_manager_broker() -> MagicMock:
    """Create a mock Broker with place_bracket_order() returning FILLED entry."""
    broker = MagicMock()
    counter = {"n": 0}

    def make_bracket_result(
        entry: Order, stop: Order, targets: list[Order]
    ) -> BracketOrderResult:
        counter["n"] += 1
        entry_id = f"entry-ulid-{counter['n']}"
        entry_result = OrderResult(
            order_id=entry_id,
            broker_order_id=f"broker-entry-{counter['n']}",
            status=OrderStatus.FILLED,
            filled_quantity=entry.quantity,
            filled_avg_price=150.0,
        )
        stop_result = OrderResult(
            order_id=f"stop-ulid-{counter['n']}",
            broker_order_id=f"broker-stop-{counter['n']}",
            status=OrderStatus.PENDING,
        )
        target_results = []
        for i, target in enumerate(targets):
            target_results.append(
                OrderResult(
                    order_id=f"target-{i}-ulid-{counter['n']}",
                    broker_order_id=f"broker-target-{i}-{counter['n']}",
                    status=OrderStatus.PENDING,
                )
            )
        return BracketOrderResult(
            entry=entry_result, stop=stop_result, targets=target_results
        )

    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.place_order = AsyncMock(
        side_effect=lambda o: OrderResult(
            order_id=o.id, broker_order_id="b", status=OrderStatus.SUBMITTED
        )
    )
    broker.cancel_order = AsyncMock(return_value=True)
    return broker


def _make_signal(symbol: str = "AAPL", strategy_id: str = "orb_breakout") -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="test",
    )


class TestManagedPositionOcaGroupLifecycle:
    """``ManagedPosition.oca_group_id`` is wired from bracket entry ULID."""

    @pytest.mark.asyncio
    async def test_bracket_oca_group_id_persists_to_managed_position(self) -> None:
        """After a successful bracket fill, the resulting ManagedPosition
        carries ``oca_group_id == f"oca_{entry_ulid}"``.
        """
        bus = EventBus()
        broker = _mock_order_manager_broker()
        clock = FixedClock(datetime(2026, 4, 27, 14, 0, 0, tzinfo=UTC))
        config = OrderManagerConfig(eod_flatten_timeout_seconds=1)
        om = OrderManager(event_bus=bus, broker=broker, clock=clock, config=config)
        await om.start()
        try:
            await om.on_approved(OrderApprovedEvent(signal=_make_signal()))
            positions = om._managed_positions.get("AAPL", [])
            assert len(positions) == 1, "exactly one ManagedPosition expected"
            pos = positions[0]
            assert pos.oca_group_id is not None
            # Formula: oca_<entry_ulid>; broker mock generates "entry-ulid-1"
            assert pos.oca_group_id == "oca_entry-ulid-1"
        finally:
            await om.stop()

    def test_managed_position_oca_group_id_default_none(self) -> None:
        """ManagedPosition constructed without ``oca_group_id`` (e.g. via
        the ``reconstruct_from_broker`` paths) defaults to ``None``.
        """
        pos = ManagedPosition(
            symbol="AAPL",
            strategy_id="reconstructed",
            entry_price=150.0,
            entry_time=datetime(2026, 4, 27, 14, 0, 0, tzinfo=UTC),
            shares_total=100,
            shares_remaining=100,
            stop_price=0.0,
            original_stop_price=0.0,
            stop_order_id=None,
            t1_price=0.0,
            t1_order_id=None,
            t1_shares=0,
            t1_filled=True,
            t2_price=0.0,
            high_watermark=150.0,
        )
        assert pos.oca_group_id is None

    @pytest.mark.asyncio
    async def test_re_entry_after_close_gets_new_oca_group(self) -> None:
        """Close a position, open a new one on the same symbol, and assert
        the new ``ManagedPosition`` has a DIFFERENT ``oca_group_id`` than
        the closed one — re-entry is identified by a fresh entry ULID.
        """
        bus = EventBus()
        broker = _mock_order_manager_broker()
        clock = FixedClock(datetime(2026, 4, 27, 14, 0, 0, tzinfo=UTC))
        config = OrderManagerConfig(eod_flatten_timeout_seconds=1)
        om = OrderManager(event_bus=bus, broker=broker, clock=clock, config=config)
        await om.start()
        try:
            # First entry
            await om.on_approved(OrderApprovedEvent(signal=_make_signal()))
            first = om._managed_positions["AAPL"][0]
            first_oca = first.oca_group_id
            assert first_oca == "oca_entry-ulid-1"

            # Drop the position to simulate close so the second entry
            # creates a brand-new ManagedPosition.
            om._managed_positions["AAPL"].clear()
            # Drain any pending state that would block a re-entry attempt
            # for the same symbol.
            om._fill_order_ids_by_symbol.pop("AAPL", None)

            # Re-entry on the same symbol — the broker mock allocates a
            # new ULID via the counter, so the new OCA group differs.
            await om.on_approved(OrderApprovedEvent(signal=_make_signal()))
            assert len(om._managed_positions["AAPL"]) == 1
            second = om._managed_positions["AAPL"][0]
            second_oca = second.oca_group_id

            assert second_oca is not None
            assert second_oca == "oca_entry-ulid-2"
            assert second_oca != first_oca, (
                "Re-entry on same symbol must produce a distinct oca_group_id"
            )
        finally:
            await om.stop()
