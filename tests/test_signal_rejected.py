"""Tests for SignalRejectedEvent creation and publishing.

Sprint 27.7, Session 3a: Verifies that SignalRejectedEvent is published
at three rejection points in _process_signal() and suppressed when
_counterfactual_enabled is False.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.event_bus import EventBus
from argus.core.events import (
    Event,
    OrderApprovedEvent,
    OrderRejectedEvent,
    QualitySignalEvent,
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
    pattern_strength: float = 75.0,
    share_count: int = 0,
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
        pattern_strength=pattern_strength,
        signal_context={"test": True},
    )


def _make_strategy_stub(allocated_capital: float = 25_000.0) -> MagicMock:
    """Create strategy-like stub with required fields."""
    strategy = MagicMock()
    strategy.allocated_capital = allocated_capital
    strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
    return strategy


def _make_quality_result(
    grade: str = "B+",
    score: float = 72.0,
    risk_tier: str = "moderate",
) -> MagicMock:
    """Create quality engine result stub."""
    result = MagicMock()
    result.grade = grade
    result.score = score
    result.risk_tier = risk_tier
    result.components = {"pattern_strength": 75.0}
    result.rationale = "test"
    return result


def _event_collector(target: list[Event]) -> Any:
    """Return async handler that appends events to target list."""
    async def _handler(event: Event) -> None:
        target.append(event)
    return _handler


def _build_system(
    event_bus: EventBus,
    *,
    counterfactual_enabled: bool = True,
    quality_enabled: bool = True,
    quality_grade: str = "B+",
    quality_score: float = 72.0,
    sizer_shares: int = 100,
    risk_result: Event | None = None,
    grade_meets_minimum: bool = True,
    orchestrator_regime_vector: object | None = None,
) -> ArgusSystem:
    """Build ArgusSystem with mocked components for _process_signal testing."""
    system = object.__new__(ArgusSystem)

    # Core components
    system._event_bus = event_bus
    system._counterfactual_enabled = counterfactual_enabled
    system._orchestrator = MagicMock()
    system._catalyst_storage = None

    # Regime vector
    if orchestrator_regime_vector is not None:
        system._orchestrator.latest_regime_vector = orchestrator_regime_vector
    else:
        system._orchestrator.latest_regime_vector = None

    # Config
    mock_config = MagicMock()
    if quality_enabled:
        mock_config.system.broker_source = MagicMock()
        mock_config.system.broker_source.__eq__ = lambda self, other: False
        mock_config.system.quality_engine.enabled = True
        mock_config.system.quality_engine.min_grade_to_trade = "C+"
    else:
        mock_config.system.broker_source = MagicMock()
        mock_config.system.broker_source.__eq__ = lambda self, other: False
        mock_config.system.quality_engine.enabled = False
    system._config = mock_config

    # Quality engine
    quality_result = _make_quality_result(grade=quality_grade, score=quality_score)
    mock_qe = MagicMock()
    mock_qe.score_setup = MagicMock(return_value=quality_result)
    mock_qe.record_quality_history = AsyncMock()
    system._quality_engine = mock_qe if quality_enabled else None

    # Position sizer
    mock_sizer = MagicMock()
    mock_sizer.calculate_shares = MagicMock(return_value=sizer_shares)
    system._position_sizer = mock_sizer

    # Broker
    mock_account = MagicMock()
    mock_account.buying_power = 200_000.0
    mock_broker = AsyncMock()
    mock_broker.get_account = AsyncMock(return_value=mock_account)
    system._broker = mock_broker

    # Risk Manager
    signal = _make_signal()
    if risk_result is None:
        risk_result = OrderApprovedEvent(signal=signal)
    mock_rm = AsyncMock()
    mock_rm.evaluate_signal = AsyncMock(return_value=risk_result)
    system._risk_manager = mock_rm

    # Grade check
    system._grade_meets_minimum = MagicMock(return_value=grade_meets_minimum)

    return system


# ---------------------------------------------------------------------------
# Test 1: SignalRejectedEvent creation (frozen dataclass)
# ---------------------------------------------------------------------------


class TestSignalRejectedEventCreation:
    """Verify SignalRejectedEvent can be constructed with all fields."""

    def test_create_with_all_fields(self) -> None:
        """Construct SignalRejectedEvent with all fields populated."""
        signal = _make_signal()
        event = SignalRejectedEvent(
            signal=signal,
            rejection_reason="Quality grade D below minimum C+",
            rejection_stage="quality_filter",
            quality_score=35.0,
            quality_grade="D",
            regime_vector_snapshot={"volatility": "low"},
            metadata={"extra": "info"},
        )

        assert event.signal is signal
        assert event.rejection_reason == "Quality grade D below minimum C+"
        assert event.rejection_stage == "quality_filter"
        assert event.quality_score == 35.0
        assert event.quality_grade == "D"
        assert event.regime_vector_snapshot == {"volatility": "low"}
        assert event.metadata == {"extra": "info"}

    def test_frozen_dataclass(self) -> None:
        """SignalRejectedEvent is frozen — cannot mutate."""
        event = SignalRejectedEvent(rejection_reason="test")
        with pytest.raises(AttributeError):
            event.rejection_reason = "changed"  # type: ignore[misc]

    def test_default_values(self) -> None:
        """Default values are sensible when no fields are set."""
        event = SignalRejectedEvent()
        assert event.signal is None
        assert event.rejection_reason == ""
        assert event.rejection_stage == ""
        assert event.quality_score is None
        assert event.quality_grade is None
        assert event.regime_vector_snapshot is None
        assert event.metadata == {}


# ---------------------------------------------------------------------------
# Test 2: Quality filter publishes SignalRejectedEvent
# ---------------------------------------------------------------------------


class TestQualityFilterRejection:
    """Verify QUALITY_FILTER rejection publishes SignalRejectedEvent."""

    @pytest.mark.asyncio
    async def test_quality_filter_publishes_event(self) -> None:
        """When grade below minimum, SignalRejectedEvent is published."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            quality_grade="D",
            quality_score=35.0,
            grade_meets_minimum=False,
        )

        signal = _make_signal()
        strategy = _make_strategy_stub()
        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "quality_filter"
        assert evt.quality_score == 35.0
        assert evt.quality_grade == "D"
        assert "below minimum" in evt.rejection_reason


# ---------------------------------------------------------------------------
# Test 3: Position sizer rejection publishes SignalRejectedEvent
# ---------------------------------------------------------------------------


class TestPositionSizerRejection:
    """Verify POSITION_SIZER rejection publishes SignalRejectedEvent."""

    @pytest.mark.asyncio
    async def test_sizer_zero_shares_publishes_event(self) -> None:
        """When sizer returns 0 shares, SignalRejectedEvent is published."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            quality_grade="C+",
            quality_score=55.0,
            sizer_shares=0,
            grade_meets_minimum=True,
        )

        signal = _make_signal()
        strategy = _make_strategy_stub()
        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "position_sizer"
        assert evt.quality_score == 55.0
        assert evt.quality_grade == "C+"
        assert "0 shares" in evt.rejection_reason


# ---------------------------------------------------------------------------
# Test 4: Risk Manager rejection publishes SignalRejectedEvent
# ---------------------------------------------------------------------------


class TestRiskManagerRejection:
    """Verify RISK_MANAGER rejection publishes SignalRejectedEvent."""

    @pytest.mark.asyncio
    async def test_risk_manager_rejection_publishes_event(self) -> None:
        """When RM rejects, SignalRejectedEvent published AFTER OrderRejectedEvent."""
        event_bus = EventBus()
        signal = _make_signal()

        rm_rejection = OrderRejectedEvent(
            signal=signal,
            reason="Daily loss limit exceeded",
        )

        rejected_events: list[SignalRejectedEvent] = []
        order_rejected_events: list[OrderRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))
        event_bus.subscribe(OrderRejectedEvent, _event_collector(order_rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            sizer_shares=100,
            risk_result=rm_rejection,
            grade_meets_minimum=True,
        )

        strategy = _make_strategy_stub()
        await system._process_signal(signal, strategy)
        await event_bus.drain()

        # OrderRejectedEvent still published
        assert len(order_rejected_events) == 1

        # SignalRejectedEvent also published
        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "risk_manager"
        assert evt.rejection_reason == "Daily loss limit exceeded"


# ---------------------------------------------------------------------------
# Test 5: Disabled flag suppresses all events
# ---------------------------------------------------------------------------


class TestCounterfactualDisabled:
    """Verify _counterfactual_enabled=False suppresses all SignalRejectedEvents."""

    @pytest.mark.asyncio
    async def test_quality_filter_no_event_when_disabled(self) -> None:
        """Quality filter rejection does NOT publish when disabled."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=False,
            quality_enabled=True,
            grade_meets_minimum=False,
        )

        await system._process_signal(_make_signal(), _make_strategy_stub())
        await event_bus.drain()
        assert len(rejected_events) == 0

    @pytest.mark.asyncio
    async def test_sizer_no_event_when_disabled(self) -> None:
        """Sizer rejection does NOT publish when disabled."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=False,
            quality_enabled=True,
            sizer_shares=0,
            grade_meets_minimum=True,
        )

        await system._process_signal(_make_signal(), _make_strategy_stub())
        await event_bus.drain()
        assert len(rejected_events) == 0

    @pytest.mark.asyncio
    async def test_risk_manager_no_event_when_disabled(self) -> None:
        """RM rejection does NOT publish SignalRejectedEvent when disabled."""
        event_bus = EventBus()
        signal = _make_signal()
        rm_rejection = OrderRejectedEvent(signal=signal, reason="limit hit")

        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=False,
            quality_enabled=True,
            sizer_shares=100,
            risk_result=rm_rejection,
            grade_meets_minimum=True,
        )

        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()
        assert len(rejected_events) == 0


# ---------------------------------------------------------------------------
# Test 6: Regime vector captured in snapshot
# ---------------------------------------------------------------------------


class TestRegimeVectorCapture:
    """Verify regime_vector_snapshot is populated from orchestrator."""

    @pytest.mark.asyncio
    async def test_regime_vector_captured_when_available(self) -> None:
        """When orchestrator has a regime vector, snapshot is populated."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        # Create a mock regime vector with to_dict()
        mock_rv = MagicMock()
        mock_rv.to_dict.return_value = {
            "volatility": "low",
            "trend": "bullish",
            "breadth": "healthy",
        }

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            grade_meets_minimum=False,
            orchestrator_regime_vector=mock_rv,
        )

        await system._process_signal(_make_signal(), _make_strategy_stub())
        await event_bus.drain()

        assert len(rejected_events) == 1
        snapshot = rejected_events[0].regime_vector_snapshot
        assert snapshot is not None
        assert snapshot["volatility"] == "low"
        assert snapshot["trend"] == "bullish"

    @pytest.mark.asyncio
    async def test_regime_vector_none_when_not_available(self) -> None:
        """When no regime vector, snapshot is None."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            grade_meets_minimum=False,
            orchestrator_regime_vector=None,
        )

        await system._process_signal(_make_signal(), _make_strategy_stub())
        await event_bus.drain()

        assert len(rejected_events) == 1
        assert rejected_events[0].regime_vector_snapshot is None


# ---------------------------------------------------------------------------
# Test 7: Signal carries entry/stop/target in rejection event
# ---------------------------------------------------------------------------


class TestSignalDataInRejection:
    """Verify the signal in SignalRejectedEvent has price data populated."""

    @pytest.mark.asyncio
    async def test_signal_has_entry_stop_targets(self) -> None:
        """Signal in rejection event has non-zero entry, stop, and targets."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            quality_enabled=True,
            grade_meets_minimum=False,
        )

        signal = _make_signal(entry_price=150.0, stop_price=148.0)
        await system._process_signal(signal, _make_strategy_stub())
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt_signal = rejected_events[0].signal
        assert evt_signal is not None
        assert evt_signal.entry_price == 150.0
        assert evt_signal.stop_price == 148.0
        assert len(evt_signal.target_prices) > 0
        assert evt_signal.target_prices[0] == 153.0
