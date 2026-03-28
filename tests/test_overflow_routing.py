"""Tests for overflow routing in _process_signal().

Sprint 27.95, Session 3b: Verifies that when broker position capacity is
reached, approved signals are routed to counterfactual tracking via
SignalRejectedEvent with RejectionStage.BROKER_OVERFLOW instead of being
submitted to the broker.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, PropertyMock

import pytest

from argus.core.config import BrokerSource
from argus.core.event_bus import EventBus
from argus.core.events import (
    Event,
    OrderApprovedEvent,
    OrderRejectedEvent,
    SignalEvent,
    SignalRejectedEvent,
    Side,
)
from argus.main import ArgusSystem


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "TSLA",
    strategy_id: str = "orb_breakout",
    entry_price: float = 150.0,
    stop_price: float = 148.0,
    share_count: int = 0,
    quality_score: float | None = 72.0,
    quality_grade: str | None = "B+",
) -> SignalEvent:
    """Build a realistic SignalEvent with populated price fields."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(153.0, 156.0),
        share_count=share_count,
        rationale="Test signal",
        pattern_strength=75.0,
        signal_context={"test": True},
        quality_score=quality_score,
        quality_grade=quality_grade,
    )


def _make_strategy_stub(allocated_capital: float = 25_000.0) -> MagicMock:
    """Create strategy-like stub with required fields."""
    strategy = MagicMock()
    strategy.allocated_capital = allocated_capital
    strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
    return strategy


def _event_collector(target: list[Event]) -> Any:
    """Return async handler that appends events to target list."""
    async def _handler(event: Event) -> None:
        target.append(event)
    return _handler


def _build_overflow_system(
    event_bus: EventBus,
    *,
    counterfactual_enabled: bool = True,
    overflow_enabled: bool = True,
    broker_capacity: int = 5,
    open_position_count: int = 0,
    broker_source: object | None = None,
    risk_result: Event | None = None,
) -> ArgusSystem:
    """Build ArgusSystem with mocked components for overflow testing.

    Args:
        event_bus: EventBus for event publishing.
        counterfactual_enabled: Whether counterfactual tracking is active.
        overflow_enabled: Whether overflow routing is enabled.
        broker_capacity: Max concurrent broker positions.
        open_position_count: Current number of open positions.
        broker_source: BrokerSource value; defaults to non-SIMULATED.
        risk_result: Risk Manager result; defaults to OrderApprovedEvent.
    """
    system = object.__new__(ArgusSystem)

    # Core components
    system._event_bus = event_bus
    system._counterfactual_enabled = counterfactual_enabled
    system._orchestrator = MagicMock()
    system._orchestrator.latest_regime_vector = None
    system._catalyst_storage = None

    # Config — non-SIMULATED broker, quality disabled (legacy sizing bypass)
    mock_config = MagicMock()
    if broker_source is not None:
        mock_config.system.broker_source = broker_source
    else:
        # Non-SIMULATED: make BrokerSource.SIMULATED comparison return False
        mock_bs = MagicMock()
        mock_bs.__eq__ = lambda self, other: False
        mock_bs.__ne__ = lambda self, other: True
        mock_config.system.broker_source = mock_bs

    # Quality engine disabled → legacy sizing path (simpler for overflow tests)
    mock_config.system.quality_engine.enabled = False

    # Overflow config
    mock_config.system.overflow.enabled = overflow_enabled
    mock_config.system.overflow.broker_capacity = broker_capacity
    system._config = mock_config

    # Quality engine disabled
    system._quality_engine = None
    system._position_sizer = None

    # Broker (for legacy sizing — get_account not needed)
    system._broker = AsyncMock()

    # Order Manager with controllable position count
    mock_om = MagicMock()
    type(mock_om).open_position_count = PropertyMock(
        return_value=open_position_count
    )
    system._order_manager = mock_om

    # Risk Manager
    signal = _make_signal()
    if risk_result is None:
        risk_result = OrderApprovedEvent(signal=signal)
    mock_rm = AsyncMock()
    mock_rm.evaluate_signal = AsyncMock(return_value=risk_result)
    system._risk_manager = mock_rm

    return system


# ---------------------------------------------------------------------------
# Test 1: Below capacity → signal proceeds normally
# ---------------------------------------------------------------------------


class TestBelowCapacityProceeds:
    """When position count is below capacity, signal reaches order placement."""

    @pytest.mark.asyncio
    async def test_below_capacity_publishes_approved_event(self) -> None:
        """Signal approved by RM with positions below capacity is published."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            overflow_enabled=True,
            broker_capacity=5,
            open_position_count=3,  # below capacity
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(approved_events) == 1
        assert len(rejected_events) == 0


# ---------------------------------------------------------------------------
# Test 2: At capacity → signal routed to overflow
# ---------------------------------------------------------------------------


class TestAtCapacityOverflow:
    """When position count equals capacity, signal is overflow-routed."""

    @pytest.mark.asyncio
    async def test_at_capacity_publishes_signal_rejected(self) -> None:
        """Signal at capacity publishes SignalRejectedEvent, not approved."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            overflow_enabled=True,
            broker_capacity=5,
            open_position_count=5,  # at capacity
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(approved_events) == 0
        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "broker_overflow"
        assert "5/5" in evt.rejection_reason


# ---------------------------------------------------------------------------
# Test 3: Above capacity → signal routed to overflow
# ---------------------------------------------------------------------------


class TestAboveCapacityOverflow:
    """When position count exceeds capacity, signal is overflow-routed."""

    @pytest.mark.asyncio
    async def test_above_capacity_publishes_signal_rejected(self) -> None:
        """Signal above capacity publishes SignalRejectedEvent."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            overflow_enabled=True,
            broker_capacity=5,
            open_position_count=8,  # above capacity
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(approved_events) == 0
        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "broker_overflow"
        assert "8/5" in evt.rejection_reason


# ---------------------------------------------------------------------------
# Test 4: BrokerSource.SIMULATED bypasses overflow check
# ---------------------------------------------------------------------------


class TestSimulatedBypass:
    """BrokerSource.SIMULATED must bypass overflow entirely."""

    @pytest.mark.asyncio
    async def test_simulated_skips_overflow_even_above_capacity(self) -> None:
        """SIMULATED broker proceeds normally even above capacity."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            overflow_enabled=True,
            broker_capacity=5,
            open_position_count=10,  # way above capacity
            broker_source=BrokerSource.SIMULATED,
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        # Signal should proceed — OrderApprovedEvent published
        assert len(approved_events) == 1
        assert len(rejected_events) == 0


# ---------------------------------------------------------------------------
# Test 5: overflow.enabled=False skips overflow check
# ---------------------------------------------------------------------------


class TestOverflowDisabled:
    """When overflow.enabled is False, overflow check is skipped."""

    @pytest.mark.asyncio
    async def test_disabled_overflow_proceeds_at_capacity(self) -> None:
        """Disabled overflow allows signal through even at capacity."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            overflow_enabled=False,  # disabled
            broker_capacity=5,
            open_position_count=10,
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(approved_events) == 1
        assert len(rejected_events) == 0


# ---------------------------------------------------------------------------
# Test 6: SignalRejectedEvent has correct fields
# ---------------------------------------------------------------------------


class TestOverflowEventFields:
    """Verify SignalRejectedEvent fields for overflow routing."""

    @pytest.mark.asyncio
    async def test_event_has_correct_stage_reason_and_signal_data(self) -> None:
        """Overflow event carries stage, reason with counts, and signal data."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            counterfactual_enabled=True,
            overflow_enabled=True,
            broker_capacity=3,
            open_position_count=3,
        )

        signal = _make_signal(
            symbol="NVDA",
            strategy_id="bull_flag",
            entry_price=200.0,
            stop_price=195.0,
            quality_score=85.0,
            quality_grade="A-",
        )
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt = rejected_events[0]

        # Stage
        assert evt.rejection_stage == "broker_overflow"

        # Reason contains count/capacity
        assert "Broker capacity reached" in evt.rejection_reason
        assert "3/3" in evt.rejection_reason

        # Signal data preserved
        assert evt.signal is not None
        assert evt.signal.symbol == "NVDA"
        assert evt.signal.strategy_id == "bull_flag"
        assert evt.signal.entry_price == 200.0
        assert evt.signal.stop_price == 195.0
        assert len(evt.signal.target_prices) > 0

    @pytest.mark.asyncio
    async def test_quality_metadata_carried_through(self) -> None:
        """Quality score and grade from signal are carried to rejection event."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            counterfactual_enabled=True,
            overflow_enabled=True,
            broker_capacity=2,
            open_position_count=5,
        )

        signal = _make_signal(quality_score=90.0, quality_grade="A")
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.quality_score == 90.0
        assert evt.quality_grade == "A"

    @pytest.mark.asyncio
    async def test_no_event_when_counterfactual_disabled(self) -> None:
        """Overflow still returns early but no SignalRejectedEvent published."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_overflow_system(
            event_bus,
            counterfactual_enabled=False,  # disabled
            overflow_enabled=True,
            broker_capacity=3,
            open_position_count=5,
        )

        signal = _make_signal()
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        # No approved event (overflow intercepted)
        assert len(approved_events) == 0
        # No rejected event (counterfactual disabled)
        assert len(rejected_events) == 0


# ---------------------------------------------------------------------------
# Test 7: RM rejection still works normally (no interference)
# ---------------------------------------------------------------------------


class TestRMRejectionUnaffected:
    """Overflow check does not interfere with RM rejections."""

    @pytest.mark.asyncio
    async def test_rm_rejection_bypasses_overflow_check(self) -> None:
        """When RM rejects, overflow check is irrelevant — rejection flows."""
        event_bus = EventBus()
        signal = _make_signal()
        rm_rejection = OrderRejectedEvent(
            signal=signal, reason="Daily loss limit exceeded"
        )

        order_rejected_events: list[OrderRejectedEvent] = []
        overflow_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(OrderRejectedEvent, _event_collector(order_rejected_events))
        event_bus.subscribe(SignalRejectedEvent, _event_collector(overflow_events))

        system = _build_overflow_system(
            event_bus,
            counterfactual_enabled=True,
            overflow_enabled=True,
            broker_capacity=5,
            open_position_count=10,  # above capacity
            risk_result=rm_rejection,
        )

        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        # RM rejection published normally
        assert len(order_rejected_events) == 1
        assert order_rejected_events[0].reason == "Daily loss limit exceeded"

        # SignalRejectedEvent published with risk_manager stage (not overflow)
        assert len(overflow_events) == 1
        assert overflow_events[0].rejection_stage == "risk_manager"
