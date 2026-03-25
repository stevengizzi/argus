"""Tests for Shadow Strategy Mode (Sprint 27.7, Session 5).

Verifies StrategyMode enum, shadow routing in _process_signal(),
config parsing, and end-to-end counterfactual tracking.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.config import StrategyConfig
from argus.core.event_bus import EventBus
from argus.core.events import (
    Event,
    OrderApprovedEvent,
    OrderRejectedEvent,
    SignalEvent,
    SignalRejectedEvent,
    Side,
)
from argus.intelligence.counterfactual import CounterfactualTracker, RejectionStage
from argus.main import ArgusSystem
from argus.strategies.base_strategy import StrategyMode


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_signal(
    symbol: str = "TSLA",
    strategy_id: str = "orb_breakout",
    entry_price: float = 150.0,
    stop_price: float = 148.0,
) -> SignalEvent:
    """Build a realistic SignalEvent."""
    return SignalEvent(
        strategy_id=strategy_id,
        symbol=symbol,
        side=Side.LONG,
        entry_price=entry_price,
        stop_price=stop_price,
        target_prices=(153.0, 156.0),
        share_count=0,
        rationale="Test signal",
        pattern_strength=75.0,
        signal_context={"test": True},
    )


def _make_strategy_stub(
    mode: str = "live",
    allocated_capital: float = 25_000.0,
) -> MagicMock:
    """Create strategy-like stub with mode field on config."""
    strategy = MagicMock()
    strategy.allocated_capital = allocated_capital
    strategy.config.mode = mode
    strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
    return strategy


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
    quality_result = MagicMock()
    quality_result.grade = "B+"
    quality_result.score = 72.0
    quality_result.risk_tier = "moderate"
    quality_result.components = {"pattern_strength": 75.0}
    quality_result.rationale = "test"
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
# Test 1: StrategyMode enum
# ---------------------------------------------------------------------------


class TestStrategyModeEnum:
    """Verify StrategyMode enum values and StrEnum behavior."""

    def test_live_value(self) -> None:
        """LIVE has string value 'live'."""
        assert StrategyMode.LIVE == "live"
        assert StrategyMode.LIVE.value == "live"

    def test_shadow_value(self) -> None:
        """SHADOW has string value 'shadow'."""
        assert StrategyMode.SHADOW == "shadow"
        assert StrategyMode.SHADOW.value == "shadow"

    def test_str_enum_comparison(self) -> None:
        """StrategyMode members compare equal to their string values."""
        assert StrategyMode.LIVE == "live"
        assert StrategyMode.SHADOW == "shadow"
        assert "shadow" == StrategyMode.SHADOW

    def test_is_str_subclass(self) -> None:
        """StrategyMode members are str instances."""
        assert isinstance(StrategyMode.LIVE, str)
        assert isinstance(StrategyMode.SHADOW, str)


# ---------------------------------------------------------------------------
# Test 2: Shadow routing sends signal to tracker
# ---------------------------------------------------------------------------


class TestShadowRoutingPublishesEvent:
    """Shadow-mode strategy signal published as SignalRejectedEvent with SHADOW stage."""

    @pytest.mark.asyncio
    async def test_shadow_signal_published_as_rejected(self) -> None:
        """Shadow signal → SignalRejectedEvent with stage=SHADOW."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 1
        evt = rejected_events[0]
        assert evt.rejection_stage == "SHADOW"
        assert evt.signal is signal
        assert "Shadow mode" in evt.rejection_reason

    @pytest.mark.asyncio
    async def test_shadow_signal_has_regime_snapshot(self) -> None:
        """Shadow signal captures regime vector snapshot."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        mock_rv = MagicMock()
        mock_rv.to_dict.return_value = {"volatility": "low", "trend": "bullish"}

        system = _build_system(
            event_bus,
            counterfactual_enabled=True,
            orchestrator_regime_vector=mock_rv,
        )
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 1
        snapshot = rejected_events[0].regime_vector_snapshot
        assert snapshot is not None
        assert snapshot["volatility"] == "low"


# ---------------------------------------------------------------------------
# Test 3: Shadow routing bypasses quality engine
# ---------------------------------------------------------------------------


class TestShadowBypassesQualityEngine:
    """Shadow signal never reaches quality pipeline."""

    @pytest.mark.asyncio
    async def test_quality_engine_not_called(self) -> None:
        """Quality engine score_setup() is never called for shadow signals."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)

        # Quality engine should not be invoked
        assert system._quality_engine is not None
        system._quality_engine.score_setup.assert_not_called()

    @pytest.mark.asyncio
    async def test_quality_score_is_none_in_event(self) -> None:
        """Shadow signal's SignalRejectedEvent has quality_score=None."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))

        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 1
        assert rejected_events[0].quality_score is None
        assert rejected_events[0].quality_grade is None


# ---------------------------------------------------------------------------
# Test 4: Shadow routing bypasses risk manager
# ---------------------------------------------------------------------------


class TestShadowBypassesRiskManager:
    """Shadow signal never reaches risk manager."""

    @pytest.mark.asyncio
    async def test_risk_manager_not_called(self) -> None:
        """Risk manager evaluate_signal() is never called for shadow signals."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)

        system._risk_manager.evaluate_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_order_approved_event(self) -> None:
        """Shadow signal produces no OrderApprovedEvent."""
        event_bus = EventBus()
        approved_events: list[OrderApprovedEvent] = []
        rejected_order_events: list[OrderRejectedEvent] = []
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))
        event_bus.subscribe(OrderRejectedEvent, _event_collector(rejected_order_events))

        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(approved_events) == 0
        assert len(rejected_order_events) == 0


# ---------------------------------------------------------------------------
# Test 5: Live routing unchanged
# ---------------------------------------------------------------------------


class TestLiveRoutingUnchanged:
    """Strategy with mode=live follows normal path."""

    @pytest.mark.asyncio
    async def test_live_mode_reaches_risk_manager(self) -> None:
        """Live-mode signal reaches risk manager evaluate_signal()."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="live")

        await system._process_signal(signal, strategy)

        system._risk_manager.evaluate_signal.assert_called_once()

    @pytest.mark.asyncio
    async def test_live_mode_goes_through_quality(self) -> None:
        """Live-mode signal with quality enabled goes through scoring."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=True, quality_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="live")

        await system._process_signal(signal, strategy)

        system._quality_engine.score_setup.assert_called_once()


# ---------------------------------------------------------------------------
# Test 6: Default mode is live
# ---------------------------------------------------------------------------


class TestDefaultModeIsLive:
    """Strategy config without explicit mode field defaults to live."""

    def test_strategy_config_default_mode(self) -> None:
        """StrategyConfig default mode is 'live'."""
        config = StrategyConfig(strategy_id="test", name="Test")
        assert config.mode == "live"

    @pytest.mark.asyncio
    async def test_strategy_without_mode_treated_as_live(self) -> None:
        """Strategy stub without mode attr on config → treated as live (reaches RM)."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()

        # Strategy with no mode attribute at all — getattr default fallback
        strategy = MagicMock()
        strategy.allocated_capital = 25_000.0
        strategy.config.risk_limits.max_loss_per_trade_pct = 0.01
        del strategy.config.mode  # Force AttributeError on access

        await system._process_signal(signal, strategy)

        # Should have gone through normal path → risk manager called
        system._risk_manager.evaluate_signal.assert_called_once()


# ---------------------------------------------------------------------------
# Test 7: Shadow + counterfactual disabled = silent drop
# ---------------------------------------------------------------------------


class TestShadowCounterfactualDisabled:
    """Shadow signal silently dropped when counterfactual is disabled."""

    @pytest.mark.asyncio
    async def test_no_event_no_exception(self) -> None:
        """Shadow signal with counterfactual disabled → no event, no error."""
        event_bus = EventBus()
        rejected_events: list[SignalRejectedEvent] = []
        approved_events: list[OrderApprovedEvent] = []
        event_bus.subscribe(SignalRejectedEvent, _event_collector(rejected_events))
        event_bus.subscribe(OrderApprovedEvent, _event_collector(approved_events))

        system = _build_system(event_bus, counterfactual_enabled=False)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        # Should not raise
        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(rejected_events) == 0
        assert len(approved_events) == 0

    @pytest.mark.asyncio
    async def test_risk_manager_not_called_when_disabled(self) -> None:
        """Shadow + disabled → still bypasses risk manager (just no event)."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=False)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)

        system._risk_manager.evaluate_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_quality_engine_not_called_when_disabled(self) -> None:
        """Shadow + disabled → quality engine not called either."""
        event_bus = EventBus()
        system = _build_system(event_bus, counterfactual_enabled=False)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)

        assert system._quality_engine is not None
        system._quality_engine.score_setup.assert_not_called()


# ---------------------------------------------------------------------------
# Test 8: Shadow signal tracked as counterfactual (end-to-end)
# ---------------------------------------------------------------------------


class TestShadowSignalTrackedEndToEnd:
    """Shadow signal → SignalRejectedEvent → CounterfactualTracker opens position."""

    @pytest.mark.asyncio
    async def test_tracker_receives_shadow_signal(self) -> None:
        """CounterfactualTracker.track() is called for SHADOW-stage rejections."""
        event_bus = EventBus()
        tracker = CounterfactualTracker()

        # Subscribe tracker to SignalRejectedEvent (mimics S3b wiring)
        tracked_positions: list[str] = []

        async def _on_rejected(event: SignalRejectedEvent) -> None:
            if event.signal is not None and event.rejection_stage:
                pid = tracker.track(
                    signal=event.signal,
                    rejection_reason=event.rejection_reason,
                    rejection_stage=RejectionStage(event.rejection_stage.lower()),
                    metadata=(
                        {"regime_vector_snapshot": event.regime_vector_snapshot}
                        if event.regime_vector_snapshot
                        else None
                    ),
                )
                if pid is not None:
                    tracked_positions.append(pid)

        event_bus.subscribe(SignalRejectedEvent, _on_rejected)

        system = _build_system(event_bus, counterfactual_enabled=True)
        signal = _make_signal()
        strategy = _make_strategy_stub(mode="shadow")

        await system._process_signal(signal, strategy)
        await event_bus.drain()

        assert len(tracked_positions) == 1
        open_positions = tracker.get_open_positions()
        assert len(open_positions) == 1
        pos = open_positions[0]
        assert pos.symbol == "TSLA"
        assert pos.strategy_id == "orb_breakout"
        assert pos.rejection_stage == RejectionStage.SHADOW
        assert pos.entry_price == 150.0
        assert pos.stop_price == 148.0


# ---------------------------------------------------------------------------
# Test 9: Config parsing — mode field in YAML
# ---------------------------------------------------------------------------


class TestConfigParsing:
    """Strategy YAML with mode field parses correctly."""

    def test_mode_shadow_parses(self) -> None:
        """StrategyConfig with mode='shadow' validates."""
        config = StrategyConfig(
            strategy_id="test_shadow",
            name="Test Shadow",
            mode="shadow",
        )
        assert config.mode == "shadow"

    def test_mode_live_parses(self) -> None:
        """StrategyConfig with mode='live' validates."""
        config = StrategyConfig(
            strategy_id="test_live",
            name="Test Live",
            mode="live",
        )
        assert config.mode == "live"

    def test_mode_absent_defaults_live(self) -> None:
        """StrategyConfig without mode defaults to 'live'."""
        config = StrategyConfig(strategy_id="test", name="Test")
        assert config.mode == "live"
