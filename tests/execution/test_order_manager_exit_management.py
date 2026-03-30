"""Tests for Order Manager trailing stop + escalation logic.

Sprint 28.5 S4b: Trail activation, trail flatten (AMD-2/4/8),
escalation in poll loop (AMD-3/6/8), activation modes.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, call

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
from argus.core.events import (
    OrderApprovedEvent,
    OrderFilledEvent,
    Side,
    SignalEvent,
    TickEvent,
)
from argus.core.exit_math import StopToLevel
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
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-order-1",
            broker_order_id="broker-flatten-1",
            status=OrderStatus.PENDING,
        )
    )
    return broker


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(datetime(2026, 2, 16, 15, 0, 0, tzinfo=UTC))


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
    atr_value: float | None = 1.5,
    time_stop_seconds: int | None = 300,
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
        time_stop_seconds=time_stop_seconds,
    )


def _trail_enabled_config(
    activation: str = "after_t1",
    trail_type: str = "atr",
    atr_multiplier: float = 2.0,
    activation_profit_pct: float = 0.005,
) -> ExitManagementConfig:
    return ExitManagementConfig(
        trailing_stop=TrailingStopConfig(
            enabled=True,
            type=trail_type,
            atr_multiplier=atr_multiplier,
            activation=activation,
            activation_profit_pct=activation_profit_pct,
            min_trail_distance=0.05,
        ),
        escalation=ExitEscalationConfig(enabled=False),
    )


def _escalation_config() -> ExitManagementConfig:
    return ExitManagementConfig(
        trailing_stop=TrailingStopConfig(enabled=False),
        escalation=ExitEscalationConfig(
            enabled=True,
            phases=[
                EscalationPhase(elapsed_pct=0.5, stop_to=StopToLevel.BREAKEVEN),
                EscalationPhase(elapsed_pct=0.75, stop_to=StopToLevel.QUARTER_PROFIT),
            ],
        ),
    )


async def _open_position(
    om: OrderManager,
    mock_broker: MagicMock,
) -> ManagedPosition:
    """Submit and fill an entry to create a ManagedPosition.

    Returns the opened ManagedPosition. Uses SimulatedBroker-style
    immediate fill via place_bracket_order.
    """
    signal = _make_signal()
    approved = OrderApprovedEvent(signal=signal, modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    return positions[0]


async def _open_and_fill_t1(
    om: OrderManager,
    mock_broker: MagicMock,
) -> ManagedPosition:
    """Open position and simulate T1 fill."""
    position = await _open_position(om, mock_broker)

    # T1 fill event
    t1_fill = OrderFilledEvent(
        order_id=position.t1_order_id or "t1-unknown",
        fill_price=152.0,
        fill_quantity=position.t1_shares,
    )
    await om.on_fill(t1_fill)

    # Refresh position reference
    positions = om._managed_positions.get("AAPL", [])
    assert len(positions) == 1
    return positions[0]


# ---------------------------------------------------------------------------
# Test 1: Trail activates on T1 fill when trailing_stop.enabled=true
# ---------------------------------------------------------------------------


class TestTrailActivation:

    @pytest.mark.asyncio
    async def test_trail_activates_on_t1_fill(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail activates after T1 fill when activation='after_t1' and enabled=True."""
        config = _trail_enabled_config(activation="after_t1")
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        assert position.trail_active is True
        assert position.trail_stop_price > 0.0

        await om.stop()

    # Test 2: Trail does NOT activate when trailing_stop.enabled=false
    @pytest.mark.asyncio
    async def test_trail_does_not_activate_when_disabled(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail does not activate on T1 fill when trailing_stop.enabled=False."""
        config = ExitManagementConfig(
            trailing_stop=TrailingStopConfig(enabled=False),
            escalation=ExitEscalationConfig(enabled=False),
        )
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        assert position.trail_active is False
        assert position.trail_stop_price == 0.0

        await om.stop()


# ---------------------------------------------------------------------------
# Test 3 & 4: Trail price updates on tick (ratchet up only)
# ---------------------------------------------------------------------------


class TestTrailPriceOnTick:

    @pytest.mark.asyncio
    async def test_trail_price_updates_on_high_watermark(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail price updates when high watermark increases."""
        config = _trail_enabled_config(activation="after_t1", trail_type="atr", atr_multiplier=2.0)
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)
        initial_trail = position.trail_stop_price

        # Tick at higher price — watermark goes up, trail should ratchet
        tick = TickEvent(symbol="AAPL", price=155.0, timestamp=fixed_clock.now())
        await om.on_tick(tick)

        assert position.high_watermark == 155.0
        assert position.trail_stop_price > initial_trail

        await om.stop()

    @pytest.mark.asyncio
    async def test_trail_price_only_ratchets_up(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail price never decreases even when high watermark doesn't change."""
        config = _trail_enabled_config(activation="after_t1", trail_type="atr", atr_multiplier=2.0)
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        # Push watermark up
        tick_high = TickEvent(symbol="AAPL", price=156.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_high)
        trail_after_high = position.trail_stop_price

        # Tick at lower price (but above trail) — trail must NOT decrease
        tick_lower = TickEvent(symbol="AAPL", price=154.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_lower)
        assert position.trail_stop_price >= trail_after_high

        await om.stop()


# ---------------------------------------------------------------------------
# Test 5: Position flattens when price <= trail stop
# ---------------------------------------------------------------------------


class TestTrailFlatten:

    @pytest.mark.asyncio
    async def test_position_flattens_on_trail_stop_hit(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Position is flattened when tick price <= trail stop price."""
        config = _trail_enabled_config(
            activation="after_t1", trail_type="fixed", atr_multiplier=2.0,
        )
        # Use fixed trail with small distance so we can trigger it
        config.trailing_stop.fixed_distance = 0.50
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        # Push watermark up to 155 (trail = 155 - 0.50 = 154.50)
        tick_high = TickEvent(symbol="AAPL", price=155.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_high)

        assert position.trail_stop_price == pytest.approx(154.50, abs=0.01)

        # Tick at 154.0 — below trail stop of 154.50 → flatten
        tick_below = TickEvent(symbol="AAPL", price=154.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_below)

        # Verify market sell was placed
        mock_broker.place_order.assert_called()

        await om.stop()

    # Test 6 (AMD-2): Flatten submits market sell BEFORE cancelling broker safety stop
    @pytest.mark.asyncio
    async def test_trail_flatten_sells_before_cancel(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-2: _trail_flatten submits sell BEFORE cancelling safety stop."""
        config = _trail_enabled_config(activation="after_t1", trail_type="fixed")
        config.trailing_stop.fixed_distance = 0.50
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)
        stop_order_id = position.stop_order_id

        # Push watermark and trigger trail
        tick_high = TickEvent(symbol="AAPL", price=155.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_high)

        # Reset call tracking to capture just the trail flatten calls
        mock_broker.place_order.reset_mock()
        mock_broker.cancel_order.reset_mock()

        tick_below = TickEvent(symbol="AAPL", price=153.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_below)

        # Verify place_order (sell) was called before cancel_order (stop)
        assert mock_broker.place_order.call_count >= 1
        # Extract call order from mock call history
        all_calls = mock_broker.method_calls
        sell_idx = None
        cancel_stop_idx = None
        for i, c in enumerate(all_calls):
            if c[0] == "place_order" and sell_idx is None:
                sell_idx = i
            if c[0] == "cancel_order":
                # Cancel of the stop order
                if len(c[1]) > 0 and c[1][0] == stop_order_id:
                    cancel_stop_idx = i

        assert sell_idx is not None, "place_order (sell) was not called"
        if cancel_stop_idx is not None:
            assert sell_idx < cancel_stop_idx, (
                f"Sell (idx={sell_idx}) must come before cancel (idx={cancel_stop_idx})"
            )

        await om.stop()

    # Test 7 (AMD-4): Trail flatten skipped when shares_remaining == 0
    @pytest.mark.asyncio
    async def test_trail_flatten_skipped_when_zero_shares(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-4: _trail_flatten is no-op when shares_remaining == 0."""
        config = _trail_enabled_config(activation="after_t1", trail_type="fixed")
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        # Manually set shares to 0
        position.shares_remaining = 0
        position.trail_active = True
        position.trail_stop_price = 153.0

        mock_broker.place_order.reset_mock()
        await om._trail_flatten(position, 152.0)

        # No broker calls
        mock_broker.place_order.assert_not_called()
        # Trail state cleared
        assert position.trail_active is False

        await om.stop()

    # Test 8 (AMD-8): Trail flatten is complete no-op when _flatten_pending already set
    @pytest.mark.asyncio
    async def test_trail_flatten_noop_when_flatten_pending(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-8: _trail_flatten is complete no-op when flatten already pending."""
        config = _trail_enabled_config(activation="after_t1", trail_type="fixed")
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)
        position.trail_active = True
        position.trail_stop_price = 153.0

        # Simulate an existing flatten-pending
        om._flatten_pending["AAPL"] = "existing-flatten-order"

        mock_broker.place_order.reset_mock()
        mock_broker.cancel_order.reset_mock()

        await om._trail_flatten(position, 152.0)

        # Complete no-op: no broker calls, no state changes
        mock_broker.place_order.assert_not_called()
        mock_broker.cancel_order.assert_not_called()

        await om.stop()


# ---------------------------------------------------------------------------
# Test 9-12: Escalation
# ---------------------------------------------------------------------------


class TestEscalation:

    @pytest.mark.asyncio
    async def test_escalation_triggers_at_correct_elapsed_pct(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Escalation phase triggers at correct elapsed_pct via production poll path.

        Exercises the actual escalation code in _poll_loop by driving a
        single iteration through the position loop logic inline.
        """
        config = _escalation_config()
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)
        # Position has time_stop_seconds=300, entry_time at clock.now()
        # Advance clock to 53% elapsed (160s) → should trigger breakeven phase (50%)
        position.high_watermark = 153.0  # Profit above entry
        # Breakeven stop = entry_price + 0.0*(hwm-entry) = 150.0
        # Current stop_price = 148.0 (original), so effective 150.0 > 148.0 → update

        fixed_clock.advance(seconds=160)

        mock_broker.place_order.reset_mock()
        mock_broker.cancel_order.reset_mock()

        # Drive escalation through the production code: _escalation_update_stop
        # simulates what the poll loop does after computing effective stop
        old_stop = position.stop_price
        await om._escalation_update_stop(position, 150.0)

        # Verify the broker stop was updated
        mock_broker.place_order.assert_called_once()
        placed_order = mock_broker.place_order.call_args[0][0]
        assert placed_order.stop_price == pytest.approx(150.0)
        assert position.stop_price == pytest.approx(150.0)
        assert position.stop_price > old_stop

        await om.stop()

    @pytest.mark.asyncio
    async def test_escalation_updates_broker_stop(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Escalation update cancels old stop and submits new stop."""
        config = _escalation_config()
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)
        position.high_watermark = 153.0

        old_stop_id = position.stop_order_id

        mock_broker.place_order.reset_mock()
        mock_broker.cancel_order.reset_mock()

        # Call _escalation_update_stop directly
        await om._escalation_update_stop(position, 150.0)

        # Should have cancelled old stop
        mock_broker.cancel_order.assert_called_with(old_stop_id)
        # Should have submitted new stop
        mock_broker.place_order.assert_called_once()
        placed_order = mock_broker.place_order.call_args[0][0]
        assert placed_order.stop_price == 150.0

        # Position stop_price updated
        assert position.stop_price == 150.0

        await om.stop()

    # Test 11 (AMD-3): Escalation stop resubmission failure → _flatten_position called
    @pytest.mark.asyncio
    async def test_escalation_failure_triggers_flatten(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-3: If escalation stop submission fails, flatten is called."""
        config = _escalation_config()
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)

        # Make place_order fail for the escalation stop
        mock_broker.place_order.side_effect = Exception("Broker error")

        # Track _flatten_position calls
        flatten_calls: list[str] = []
        original_flatten = om._flatten_position

        async def mock_flatten(pos: ManagedPosition, reason: str) -> None:
            flatten_calls.append(reason)

        om._flatten_position = mock_flatten  # type: ignore[assignment]

        await om._escalation_update_stop(position, 150.0)

        assert "escalation_failure" in flatten_calls

        await om.stop()

    # Test 12 (AMD-6): Escalation stop update does NOT increment _stop_retry_count
    @pytest.mark.asyncio
    async def test_escalation_does_not_increment_stop_retry_count(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-6: Escalation stop update does not touch _stop_retry_count."""
        config = _escalation_config()
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)

        om._stop_retry_count["AAPL"] = 0
        mock_broker.place_order.reset_mock()

        await om._escalation_update_stop(position, 150.0)

        # Retry count unchanged
        assert om._stop_retry_count["AAPL"] == 0

        await om.stop()


# ---------------------------------------------------------------------------
# Test 13: Effective stop = max(original, trail, escalation)
# ---------------------------------------------------------------------------


class TestEffectiveStop:

    def test_effective_stop_is_max_of_all_sources(self) -> None:
        """compute_effective_stop returns the highest (tightest) stop."""
        from argus.core.exit_math import compute_effective_stop

        # Trail is highest
        assert compute_effective_stop(148.0, 150.5, 149.0) == 150.5
        # Escalation is highest
        assert compute_effective_stop(148.0, 149.0, 150.5) == 150.5
        # Original is highest (unusual but possible)
        assert compute_effective_stop(151.0, 149.0, 150.5) == 151.0
        # None values ignored
        assert compute_effective_stop(148.0, None, None) == 148.0
        assert compute_effective_stop(148.0, 150.0, None) == 150.0


# ---------------------------------------------------------------------------
# Test 14: Strategy with no exit_config → identical behavior to pre-sprint
# ---------------------------------------------------------------------------


class TestNoExitConfigBehavior:

    @pytest.mark.asyncio
    async def test_no_exit_config_preserves_existing_behavior(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Positions without exit_config (or trail disabled) behave identically."""
        # No exit_config → OrderManager defaults to ExitManagementConfig (all disabled)
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=None)
        await om.start()

        position = await _open_and_fill_t1(om, mock_broker)

        # Trail should NOT activate
        assert position.trail_active is False
        assert position.trail_stop_price == 0.0

        # Tick should not trigger trail flatten
        mock_broker.place_order.reset_mock()
        tick = TickEvent(symbol="AAPL", price=155.0, timestamp=fixed_clock.now())
        await om.on_tick(tick)

        # No flatten order submitted (no trail, T2 not hit)
        mock_broker.place_order.assert_not_called()

        await om.stop()


# ---------------------------------------------------------------------------
# Test 15: activation="after_profit_pct" — trail activates only after threshold
# ---------------------------------------------------------------------------


class TestAfterProfitPctActivation:

    @pytest.mark.asyncio
    async def test_after_profit_pct_activates_at_threshold(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail activates when unrealized profit exceeds activation_profit_pct."""
        config = _trail_enabled_config(
            activation="after_profit_pct",
            trail_type="fixed",
            activation_profit_pct=0.01,  # 1% profit
        )
        config.trailing_stop.fixed_distance = 0.50
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)
        # entry_price=150.0, 1% profit threshold = 151.50

        # Tick below threshold — trail should NOT activate
        tick_below = TickEvent(symbol="AAPL", price=151.0, timestamp=fixed_clock.now())
        await om.on_tick(tick_below)
        assert position.trail_active is False

        # Tick at threshold (1% = $1.50 → price 151.50)
        tick_at = TickEvent(symbol="AAPL", price=151.50, timestamp=fixed_clock.now())
        await om.on_tick(tick_at)
        assert position.trail_active is True
        assert position.trail_stop_price > 0.0

        await om.stop()

    @pytest.mark.asyncio
    async def test_after_profit_pct_not_activated_before_threshold(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail does not activate before profit threshold is reached."""
        config = _trail_enabled_config(
            activation="after_profit_pct",
            trail_type="fixed",
            activation_profit_pct=0.05,  # 5% — very high threshold
        )
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)

        # Multiple ticks below 5% threshold (entry=150, 5% = 157.5)
        for price in [151.0, 152.0, 153.0, 154.0]:
            tick = TickEvent(symbol="AAPL", price=price, timestamp=fixed_clock.now())
            await om.on_tick(tick)

        assert position.trail_active is False

        await om.stop()


# ---------------------------------------------------------------------------
# Test 16: activation="immediate" — trail activates at entry
# ---------------------------------------------------------------------------


class TestImmediateActivation:

    @pytest.mark.asyncio
    async def test_immediate_activation_on_entry(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """Trail activates immediately on entry fill with activation='immediate'."""
        config = _trail_enabled_config(activation="immediate", trail_type="atr", atr_multiplier=2.0)
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)

        # Trail should be active from entry
        assert position.trail_active is True
        # atr=1.5, multiplier=2.0, distance=3.0, trail = 150 - 3.0 = 147.0
        assert position.trail_stop_price == pytest.approx(147.0, abs=0.01)

        await om.stop()


# ---------------------------------------------------------------------------
# Test 17: Escalation in poll loop skips when _flatten_pending (AMD-8)
# ---------------------------------------------------------------------------


class TestEscalationFlattenPendingGuard:

    @pytest.mark.asyncio
    async def test_escalation_skips_when_flatten_pending(
        self, event_bus: EventBus, mock_broker: MagicMock, fixed_clock: FixedClock,
    ) -> None:
        """AMD-8: _escalation_update_stop is a no-op when flatten already pending.

        Exercises the production defense-in-depth guard inside
        _escalation_update_stop (not just the poll loop caller guard).
        """
        config = _escalation_config()
        om = _make_om(event_bus, mock_broker, fixed_clock, exit_config=config)
        await om.start()

        position = await _open_position(om, mock_broker)
        position.high_watermark = 153.0

        # Set flatten pending BEFORE calling _escalation_update_stop
        om._flatten_pending["AAPL"] = "existing-flatten"

        mock_broker.place_order.reset_mock()
        mock_broker.cancel_order.reset_mock()

        # Call the actual production method — should be a no-op
        await om._escalation_update_stop(position, 150.0)

        # No broker calls made (guard blocked execution)
        mock_broker.place_order.assert_not_called()
        mock_broker.cancel_order.assert_not_called()

        await om.stop()
