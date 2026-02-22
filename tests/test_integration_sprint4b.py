"""Sprint 4b Integration Tests.

Tests the full signal→risk→order manager→broker pipeline with position
lifecycle management (T1/T2 targets, stop-to-breakeven, time stops, EOD flatten).

All broker calls are mocked. No network calls.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from argus.core.clock import FixedClock
from argus.core.config import (
    AccountRiskConfig,
    OrderManagerConfig,
    RiskConfig,
)
from argus.core.event_bus import EventBus
from argus.core.events import (
    ExitReason,
    OrderApprovedEvent,
    OrderFilledEvent,
    PositionClosedEvent,
    PositionOpenedEvent,
    SignalEvent,
    TickEvent,
)
from argus.core.risk_manager import RiskManager
from argus.execution.order_manager import OrderManager
from argus.execution.simulated_broker import SimulatedBroker


class TestSprint4bIntegration:
    """Integration tests for Sprint 4b — Order Manager + Position Management."""

    @pytest.mark.asyncio
    async def test_full_pipeline_happy_path(self) -> None:
        """Test scanner → data → strategy → risk → order manager → broker → T1/T2.

        Simulates:
        1. Signal approved by Risk Manager
        2. Order Manager submits entry
        3. Entry fills → stop + T1 orders placed
        4. T1 fills → stop moved to breakeven
        5. T2 reached via tick → position closed
        """
        # Components
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 16, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
        )
        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        order_config = OrderManagerConfig(
            t1_position_pct=0.5,
            enable_stop_to_breakeven=True,
            breakeven_buffer_pct=0.001,
        )
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        # Track events
        opened_events: list[PositionOpenedEvent] = []
        closed_events: list[PositionClosedEvent] = []

        async def on_opened(e: PositionOpenedEvent) -> None:
            opened_events.append(e)

        async def on_closed(e: PositionClosedEvent) -> None:
            closed_events.append(e)

        event_bus.subscribe(PositionOpenedEvent, on_opened)
        event_bus.subscribe(PositionClosedEvent, on_closed)

        # Set current price in broker (required for market order fills)
        broker.set_price("AAPL", 150.0)

        # Create and approve signal
        signal = SignalEvent(
            strategy_id="orb_breakout",
            symbol="AAPL",
            entry_price=150.0,
            stop_price=148.0,
            target_prices=(152.0, 154.0),
            share_count=100,
            rationale="ORB breakout",
        )
        approved = await risk_manager.evaluate_signal(signal)
        assert isinstance(approved, OrderApprovedEvent)

        # Order Manager handles approval
        # SimulatedBroker fills immediately and Order Manager processes the fill
        await order_manager.on_approved(approved)
        await event_bus.drain()

        # Verify position created in broker
        positions = await broker.get_positions()
        assert len(positions) == 1

        # Verify position opened
        assert len(opened_events) == 1
        assert opened_events[0].symbol == "AAPL"
        assert opened_events[0].entry_price == 150.0

        # Verify managed position created
        assert "AAPL" in order_manager._managed_positions
        position = order_manager._managed_positions["AAPL"][0]
        assert position.shares_total == 100
        assert position.t1_shares == 50  # 50%

        # Get T1 order ID
        t1_order_id = position.t1_order_id
        assert t1_order_id is not None

        # Simulate T1 fill
        t1_fill = OrderFilledEvent(
            order_id=t1_order_id,
            fill_price=152.0,
            fill_quantity=50,
        )
        await order_manager.on_fill(t1_fill)

        # Verify T1 processed
        assert position.t1_filled is True
        assert position.shares_remaining == 50
        # Stop should be at breakeven
        expected_breakeven = 150.0 * (1 + 0.001)
        assert position.stop_price == pytest.approx(expected_breakeven, abs=0.01)

        # Clear t2_order_id to test Alpaca path (tick-based T2 monitoring)
        # With IBKR native brackets (DEC-093), T2 fills via broker-side order
        position.t2_order_id = None

        # Set broker price for T2 fill
        broker.set_price("AAPL", 154.0)

        # Simulate tick at T2 price - this triggers flatten which fills immediately
        tick = TickEvent(symbol="AAPL", price=154.0, volume=1000)
        await order_manager.on_tick(tick)
        await event_bus.drain()

        # Verify position closed
        assert len(closed_events) == 1
        # T1 P&L: (152 - 150) * 50 = 100
        # T2 P&L: (154 - 150) * 50 = 200
        # Total: 300
        assert closed_events[0].realized_pnl == pytest.approx(300.0)

        # Cleanup
        await order_manager.stop()
        await broker.disconnect()

    @pytest.mark.asyncio
    async def test_full_pipeline_stop_out(self) -> None:
        """Test same setup but price reverses → stop fills."""
        event_bus = EventBus()
        clock = FixedClock(datetime(2026, 2, 16, 10, 0, 0, tzinfo=UTC))
        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
        )
        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        order_config = OrderManagerConfig(t1_position_pct=0.5)
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        # Track closed events
        closed_events: list[PositionClosedEvent] = []

        async def on_closed(e: PositionClosedEvent) -> None:
            closed_events.append(e)

        event_bus.subscribe(PositionClosedEvent, on_closed)

        # Set current price in broker (required for market order fills)
        broker.set_price("TSLA", 250.0)

        # Create and approve signal
        signal = SignalEvent(
            strategy_id="orb_breakout",
            symbol="TSLA",
            entry_price=250.0,
            stop_price=245.0,  # $5 risk per share
            target_prices=(255.0, 260.0),
            share_count=100,
            rationale="ORB breakout",
        )
        approved = await risk_manager.evaluate_signal(signal)

        # Order Manager handles approval - SimulatedBroker fills immediately
        await order_manager.on_approved(approved)

        # Get stop order ID
        position = order_manager._managed_positions["TSLA"][0]
        stop_order_id = position.stop_order_id
        assert stop_order_id is not None

        # Simulate stop fill (price reversed)
        stop_fill = OrderFilledEvent(
            order_id=stop_order_id,
            fill_price=245.0,  # Stop price
            fill_quantity=100,
        )
        await order_manager.on_fill(stop_fill)
        await event_bus.drain()

        # Verify position closed at loss
        assert len(closed_events) == 1
        assert closed_events[0].exit_reason == ExitReason.STOP_LOSS
        # P&L: (245 - 250) * 100 = -500
        assert closed_events[0].realized_pnl == pytest.approx(-500.0)

        # Cleanup
        await order_manager.stop()
        await broker.disconnect()

    @pytest.mark.asyncio
    async def test_full_pipeline_eod_flatten(self) -> None:
        """Test position open at 3:50 PM → EOD flatten closes it."""
        event_bus = EventBus()
        # Start at 3:45 PM ET (20:45 UTC)
        clock = FixedClock(datetime(2026, 2, 16, 20, 45, 0, tzinfo=UTC))

        broker = SimulatedBroker(initial_cash=100_000)
        await broker.connect()

        risk_config = RiskConfig(
            account=AccountRiskConfig(
                daily_loss_limit_pct=0.03,
                max_concurrent_positions=10,
            ),
        )
        risk_manager = RiskManager(
            config=risk_config,
            broker=broker,
            event_bus=event_bus,
            clock=clock,
        )
        await risk_manager.initialize()
        await risk_manager.reset_daily_state()

        order_config = OrderManagerConfig(
            eod_flatten_time="15:50",  # 3:50 PM ET
            eod_flatten_timezone="America/New_York",
            fallback_poll_interval_seconds=1,
        )
        order_manager = OrderManager(
            event_bus=event_bus,
            broker=broker,
            clock=clock,
            config=order_config,
        )
        await order_manager.start()

        # Track closed events
        closed_events: list[PositionClosedEvent] = []

        async def on_closed(e: PositionClosedEvent) -> None:
            closed_events.append(e)

        event_bus.subscribe(PositionClosedEvent, on_closed)

        # Set current price in broker (required for market order fills)
        broker.set_price("NVDA", 900.0)

        # Create and approve signal
        signal = SignalEvent(
            strategy_id="orb_breakout",
            symbol="NVDA",
            entry_price=900.0,
            stop_price=890.0,
            target_prices=(910.0, 920.0),
            share_count=50,
            rationale="ORB breakout",
        )
        approved = await risk_manager.evaluate_signal(signal)

        # Order Manager handles approval - SimulatedBroker fills immediately
        await order_manager.on_approved(approved)

        # Verify position is open
        assert order_manager.has_open_positions

        # Advance clock past EOD flatten time (3:50 PM ET = 20:50 UTC)
        clock.advance(minutes=10)  # Now 20:55 UTC = 3:55 PM ET

        # Update broker price to simulate market movement (905.0)
        broker.set_price("NVDA", 905.0)

        # Trigger EOD flatten manually (normally done by poll loop)
        # SimulatedBroker fills immediately at current price (905.0)
        await order_manager.eod_flatten()
        await event_bus.drain()

        # Verify position closed with EOD reason
        assert len(closed_events) == 1
        assert closed_events[0].exit_reason == ExitReason.EOD_FLATTEN
        # P&L: (905 - 900) * 50 = 250
        assert closed_events[0].realized_pnl == pytest.approx(250.0)

        # Cleanup
        await order_manager.stop()
        await broker.disconnect()
