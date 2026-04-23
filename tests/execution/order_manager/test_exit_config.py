"""Tests for Order Manager exit config resolution and ManagedPosition exit fields.

Sprint 28.5 S4a: ExitManagementConfig lookup, deep merge, caching,
and ManagedPosition trail/escalation state fields.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    ExitEscalationConfig,
    ExitManagementConfig,
    OrderManagerConfig,
    TrailingStopConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    OrderApprovedEvent,
    OrderFilledEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.models.trading import BracketOrderResult, OrderResult, OrderStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def event_bus() -> EventBus:
    return EventBus()


@pytest.fixture
def mock_broker() -> MagicMock:
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
            entry=entry_result, stop=stop_result, targets=target_results,
        )

    broker.place_bracket_order = AsyncMock(side_effect=make_bracket_result)
    broker.cancel_order = AsyncMock(return_value=True)
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def global_exit_config() -> ExitManagementConfig:
    return ExitManagementConfig(
        trailing_stop=TrailingStopConfig(enabled=False, atr_multiplier=2.5),
        escalation=ExitEscalationConfig(enabled=False),
    )


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    fixed_clock: FixedClock,
    exit_config: ExitManagementConfig | None = None,
    strategy_exit_overrides: dict[str, dict] | None = None,
) -> OrderManager:
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=fixed_clock,
        config=OrderManagerConfig(),
        exit_config=exit_config,
        strategy_exit_overrides=strategy_exit_overrides,
    )


def _make_signal(
    strategy_id: str = "orb_breakout",
    atr_value: float | None = None,
) -> SignalEvent:
    return SignalEvent(
        strategy_id=strategy_id,
        symbol="AAPL",
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test signal",
        atr_value=atr_value,
    )


# ---------------------------------------------------------------------------
# Tests: _get_exit_config
# ---------------------------------------------------------------------------


class TestGetExitConfig:
    """Tests for _get_exit_config() resolution and caching."""

    def test_returns_global_default_when_no_strategy_override(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
        global_exit_config: ExitManagementConfig,
    ) -> None:
        """_get_exit_config returns the global config when no strategy override exists."""
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=global_exit_config)
        result = om._get_exit_config("orb_breakout")
        assert result is global_exit_config

    def test_returns_merged_config_with_strategy_override(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
        global_exit_config: ExitManagementConfig,
    ) -> None:
        """_get_exit_config deep-merges strategy override into global config (AMD-1)."""
        overrides = {
            "orb_breakout": {
                "trailing_stop": {"enabled": True, "atr_multiplier": 1.8},
            },
        }
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            exit_config=global_exit_config,
            strategy_exit_overrides=overrides,
        )
        result = om._get_exit_config("orb_breakout")

        # Override fields applied
        assert result.trailing_stop.enabled is True
        assert result.trailing_stop.atr_multiplier == 1.8
        # Non-overridden fields preserved from global
        assert result.trailing_stop.type == global_exit_config.trailing_stop.type
        assert result.trailing_stop.percent == global_exit_config.trailing_stop.percent
        assert result.escalation.enabled is False

    def test_caches_result_same_object_on_second_call(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
        global_exit_config: ExitManagementConfig,
    ) -> None:
        """_get_exit_config caches the result — same object returned on repeated calls."""
        overrides = {
            "orb_breakout": {"trailing_stop": {"enabled": True}},
        }
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            exit_config=global_exit_config,
            strategy_exit_overrides=overrides,
        )
        first = om._get_exit_config("orb_breakout")
        second = om._get_exit_config("orb_breakout")
        assert first is second

    def test_returns_default_config_when_no_global_config_provided(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """_get_exit_config returns a default ExitManagementConfig when exit_config=None."""
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=None)
        result = om._get_exit_config("orb_breakout")
        assert isinstance(result, ExitManagementConfig)
        assert result.trailing_stop.enabled is False


# ---------------------------------------------------------------------------
# Tests: ManagedPosition new fields
# ---------------------------------------------------------------------------


class TestManagedPositionExitFields:
    """Tests for ManagedPosition trail/escalation state defaults."""

    def test_default_trail_fields(self) -> None:
        """ManagedPosition initializes with trail_active=False, trail_stop_price=0.0."""
        pos = ManagedPosition(
            symbol="AAPL", strategy_id="orb_breakout", entry_price=150.0,
            entry_time=datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC),
            shares_total=100, shares_remaining=100, stop_price=148.0,
            original_stop_price=148.0, stop_order_id="stop-1",
            t1_price=152.0, t1_order_id="t1-1", t1_shares=50,
            t1_filled=False, t2_price=154.0, high_watermark=150.0,
        )
        assert pos.trail_active is False
        assert pos.trail_stop_price == 0.0
        assert pos.escalation_phase_index == -1
        assert pos.exit_config is None
        assert pos.atr_value is None

    def test_captures_atr_value(self) -> None:
        """ManagedPosition stores atr_value when provided."""
        pos = ManagedPosition(
            symbol="AAPL", strategy_id="orb_breakout", entry_price=150.0,
            entry_time=datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC),
            shares_total=100, shares_remaining=100, stop_price=148.0,
            original_stop_price=148.0, stop_order_id="stop-1",
            t1_price=152.0, t1_order_id="t1-1", t1_shares=50,
            t1_filled=False, t2_price=154.0, high_watermark=150.0,
            atr_value=1.25,
        )
        assert pos.atr_value == 1.25


# ---------------------------------------------------------------------------
# Tests: Entry fill wiring
# ---------------------------------------------------------------------------


class TestEntryFillExitConfigWiring:
    """Tests that _handle_entry_fill captures exit_config and atr_value."""

    @pytest.mark.asyncio
    async def test_entry_fill_captures_exit_config_and_atr(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
        global_exit_config: ExitManagementConfig,
    ) -> None:
        """Entry fill sets exit_config from _get_exit_config and atr_value from signal."""
        om = _make_om(
            event_bus, mock_broker, fixed_clock, exit_config=global_exit_config,
        )
        await om.start()

        signal = _make_signal(atr_value=1.75)
        approved = OrderApprovedEvent(signal=signal, modifications=None)
        # on_approved processes the fill inline (SimulatedBroker fills synchronously)
        await om.on_approved(approved)

        # Verify ManagedPosition was created with exit fields
        positions = om._managed_positions.get("AAPL", [])
        assert len(positions) == 1
        pos = positions[0]
        assert pos.exit_config is global_exit_config
        assert pos.atr_value == 1.75
        assert pos.trail_active is False
        assert pos.trail_stop_price == 0.0
        assert pos.escalation_phase_index == -1

        await om.stop()

    @pytest.mark.asyncio
    async def test_entry_fill_uses_strategy_specific_exit_config(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
        global_exit_config: ExitManagementConfig,
    ) -> None:
        """Entry fill uses merged strategy config when override exists."""
        overrides = {
            "orb_breakout": {"trailing_stop": {"enabled": True, "atr_multiplier": 3.0}},
        }
        om = _make_om(
            event_bus, mock_broker, fixed_clock,
            exit_config=global_exit_config,
            strategy_exit_overrides=overrides,
        )
        await om.start()

        signal = _make_signal(strategy_id="orb_breakout", atr_value=2.0)
        approved = OrderApprovedEvent(signal=signal, modifications=None)
        await om.on_approved(approved)

        positions = om._managed_positions.get("AAPL", [])
        assert len(positions) == 1
        pos = positions[0]
        assert pos.exit_config is not None
        assert pos.exit_config.trailing_stop.enabled is True
        assert pos.exit_config.trailing_stop.atr_multiplier == 3.0

        await om.stop()
