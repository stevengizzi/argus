"""Tests for Sprint 29.5 Session 1: Flatten/Zombie Safety Overhaul.

R1: IBKR error 404 root-cause fix (broker re-query on flatten retry)
R2: Global circuit breaker for flatten retry exhaustion
R3: EOD flatten covers broker-only positions
R4: Startup zombie flatten queued for market open
R5: Time-stop log suppression for flatten-pending/abandoned
R6: max_flatten_cycles config validation
"""

from __future__ import annotations

import logging
import time as _time
from datetime import UTC, datetime, time, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import yaml

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
    ShutdownRequestedEvent,
    Side,
    SignalEvent,
)
from argus.execution.order_manager import ManagedPosition, OrderManager
from argus.models.trading import (
    BracketOrderResult,
    OrderResult,
    OrderSide,
    OrderStatus,
    Position,
)


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
    broker.cancel_all_orders = AsyncMock(return_value=0)
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-order-1",
            broker_order_id="broker-flatten-1",
            status=OrderStatus.PENDING,
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    # No error_404_symbols by default (simulated broker)
    return broker


@pytest.fixture
def market_hours_clock() -> FixedClock:
    """Clock set during market hours (11 AM ET = 15:00 UTC)."""
    return FixedClock(datetime(2026, 3, 30, 15, 0, 0, tzinfo=UTC))


@pytest.fixture
def premarket_clock() -> FixedClock:
    """Clock set before market open (8 AM ET = 12:00 UTC)."""
    return FixedClock(datetime(2026, 3, 30, 12, 0, 0, tzinfo=UTC))


def _make_signal(
    symbol: str = "AAPL",
    time_stop_seconds: int | None = 300,
) -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test signal",
        time_stop_seconds=time_stop_seconds,
    )


def _make_om(
    event_bus: EventBus,
    mock_broker: MagicMock,
    clock: FixedClock,
    max_flatten_retries: int = 3,
    max_flatten_cycles: int = 2,
    flatten_pending_timeout: int = 120,
) -> OrderManager:
    config = OrderManagerConfig(
        flatten_pending_timeout_seconds=flatten_pending_timeout,
        max_flatten_retries=max_flatten_retries,
        max_flatten_cycles=max_flatten_cycles,
    )
    return OrderManager(
        event_bus=event_bus,
        broker=mock_broker,
        clock=clock,
        config=config,
    )


async def _open_position(
    om: OrderManager,
    mock_broker: MagicMock,
    symbol: str = "AAPL",
) -> ManagedPosition:
    """Submit and fill an entry to create a ManagedPosition."""
    signal = _make_signal(symbol=symbol)
    approved = OrderApprovedEvent(signal=signal, modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get(symbol, [])
    assert len(positions) == 1
    return positions[0]


# ---------------------------------------------------------------------------
# R1: IBKR error 404 root-cause fix
# ---------------------------------------------------------------------------


class TestFlattenError404:
    """Verify broker re-query when error 404 is flagged."""

    @pytest.mark.asyncio
    async def test_flatten_error_404_requery_qty(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """SELL order gets 404, next retry re-queries broker, gets correct qty."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        position = await _open_position(om, mock_broker)

        # Simulate error 404 flag on broker
        mock_broker.error_404_symbols = {"AAPL"}

        # Broker reports different qty (e.g. 80 instead of position's 50).
        # ``side=OrderSide.BUY`` required post-Sprint-31.91-Session-3:
        # the retry path's 3-branch side gate refuses the resubmit when
        # broker side is anything other than BUY.
        broker_pos = MagicMock()
        broker_pos.symbol = "AAPL"
        broker_pos.shares = 80
        broker_pos.side = OrderSide.BUY
        mock_broker.get_positions = AsyncMock(return_value=[broker_pos])

        # Set up flatten pending with expired timeout
        om._flatten_pending["AAPL"] = ("old-order-1", _time.monotonic() - 200, 0)

        # New order result for resubmit
        mock_broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="new-flatten-1",
                broker_order_id="broker-new-1",
                status=OrderStatus.PENDING,
            )
        )

        await om._check_flatten_pending_timeouts()

        # Verify re-query happened
        mock_broker.get_positions.assert_called_once()

        # Verify order placed with broker's qty (80), not ARGUS qty
        call_args = mock_broker.place_order.call_args[0][0]
        assert call_args.quantity == 80

        # error_404_symbols should be cleared for this symbol
        assert "AAPL" not in mock_broker.error_404_symbols

    @pytest.mark.asyncio
    async def test_flatten_error_404_position_gone(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """SELL order gets 404, broker re-query shows 0 qty, flatten removed."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        position = await _open_position(om, mock_broker)

        # Simulate error 404 flag on broker
        mock_broker.error_404_symbols = {"AAPL"}

        # Broker reports no position for AAPL
        mock_broker.get_positions = AsyncMock(return_value=[])

        # Set up flatten pending with expired timeout
        om._flatten_pending["AAPL"] = ("old-order-1", _time.monotonic() - 200, 0)

        await om._check_flatten_pending_timeouts()

        # Flatten should be removed — no resubmit
        assert "AAPL" not in om._flatten_pending
        mock_broker.place_order.assert_not_called()


# ---------------------------------------------------------------------------
# R2: Global circuit breaker
# ---------------------------------------------------------------------------


class TestFlattenCircuitBreaker:
    """Verify flatten retry cycle counting and abandonment."""

    @pytest.mark.asyncio
    async def test_flatten_circuit_breaker_single_cycle(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """After max_retries exhausted, cycle count incremented."""
        om = _make_om(
            event_bus, mock_broker, market_hours_clock,
            max_flatten_retries=2, max_flatten_cycles=3,
        )
        position = await _open_position(om, mock_broker)

        # Set flatten pending at max retries, expired timeout
        om._flatten_pending["AAPL"] = (
            "old-order-1", _time.monotonic() - 200, 2,  # retry_count == max
        )

        await om._check_flatten_pending_timeouts()

        # Cycle count should be 1
        assert om._flatten_cycle_count["AAPL"] == 1
        # Not yet abandoned (max_cycles=3)
        assert "AAPL" not in om._flatten_abandoned
        # Removed from pending
        assert "AAPL" not in om._flatten_pending

    @pytest.mark.asyncio
    async def test_flatten_circuit_breaker_abandoned(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """After max_cycles exhausted, symbol added to abandoned set."""
        om = _make_om(
            event_bus, mock_broker, market_hours_clock,
            max_flatten_retries=2, max_flatten_cycles=2,
        )
        position = await _open_position(om, mock_broker)

        # Simulate first cycle already counted
        om._flatten_cycle_count["AAPL"] = 1

        # Set flatten pending at max retries, expired
        om._flatten_pending["AAPL"] = (
            "old-order-1", _time.monotonic() - 200, 2,
        )

        await om._check_flatten_pending_timeouts()

        # Should now be abandoned
        assert "AAPL" in om._flatten_abandoned
        assert om._flatten_cycle_count["AAPL"] == 2

    @pytest.mark.asyncio
    async def test_flatten_abandoned_skips_new_attempts(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """Time-stop check skips flatten for abandoned symbols."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        position = await _open_position(om, mock_broker)

        # Mark as abandoned
        om._flatten_abandoned.add("AAPL")

        # Set entry time far in the past to trigger time stop
        position.entry_time = market_hours_clock.now() - timedelta(hours=3)

        # _flatten_position should return immediately (skip)
        await om._flatten_position(position, reason="time_stop")

        # No market sell order should be placed
        mock_broker.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_flatten_abandoned_cleared_by_eod(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """eod_flatten clears abandoned set."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)

        # Pre-populate abandoned state
        om._flatten_abandoned.add("AAPL")
        om._flatten_abandoned.add("TSLA")
        om._flatten_cycle_count["AAPL"] = 2
        om._flatten_cycle_count["TSLA"] = 3

        # Capture shutdown events
        shutdowns: list[ShutdownRequestedEvent] = []
        event_bus.subscribe(
            ShutdownRequestedEvent, lambda e: shutdowns.append(e)
        )

        await om.eod_flatten()

        # Abandoned and cycle count should be cleared
        assert len(om._flatten_abandoned) == 0
        assert len(om._flatten_cycle_count) == 0


# ---------------------------------------------------------------------------
# R3: EOD flatten covers broker-only positions
# ---------------------------------------------------------------------------


class TestEodFlattenBrokerOnly:
    """Verify EOD flatten queries broker for untracked positions."""

    @pytest.mark.asyncio
    async def test_eod_flatten_broker_only_positions(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """eod_flatten queries broker, sells untracked positions."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        # FIX-13b F9: drop flatten fill-wait to 0.1s so the never-arriving
        # mock-broker fill callback stops burning the 30s production default.
        monkeypatch.setattr(om._config, "eod_flatten_timeout_seconds", 0.1)

        # Create one tracked position
        await _open_position(om, mock_broker)

        # Broker reports tracked AAPL + untracked TSLA.
        # IMPROMPTU-04 DEF-199 requires side=OrderSide.BUY so the Pass 2
        # side-check treats these as long positions eligible for flatten.
        aapl_pos = MagicMock()
        aapl_pos.symbol = "AAPL"
        aapl_pos.shares = 50
        aapl_pos.side = OrderSide.BUY
        tsla_pos = MagicMock()
        tsla_pos.symbol = "TSLA"
        tsla_pos.shares = 200
        tsla_pos.side = OrderSide.BUY

        # Reset place_order to track new calls
        mock_broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="eod-flatten-1",
                broker_order_id="broker-eod-1",
                status=OrderStatus.PENDING,
            )
        )
        mock_broker.get_positions = AsyncMock(return_value=[aapl_pos, tsla_pos])

        await om.eod_flatten()

        # get_positions should have been called for broker-only pass
        mock_broker.get_positions.assert_called()

        # place_order should have been called for AAPL (managed flatten)
        # and for TSLA (untracked broker-only flatten via _flatten_unknown_position)
        # At least TSLA's flatten should appear
        sell_symbols = [
            call[0][0].symbol
            for call in mock_broker.place_order.call_args_list
        ]
        assert "TSLA" in sell_symbols

    @pytest.mark.asyncio
    async def test_eod_flatten_broker_only_after_market_close(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
    ) -> None:
        """EOD Pass 2 executes even after 16:00 ET (force_execute=True)."""
        # Clock at 16:05 ET = 20:05 UTC — outside normal market hours
        after_close_clock = FixedClock(
            datetime(2026, 3, 30, 20, 5, 0, tzinfo=UTC)
        )
        om = _make_om(event_bus, mock_broker, after_close_clock)

        # Broker reports an untracked long position (DEF-199 side-check).
        tsla_pos = MagicMock()
        tsla_pos.symbol = "TSLA"
        tsla_pos.shares = 200
        tsla_pos.side = OrderSide.BUY

        mock_broker.get_positions = AsyncMock(return_value=[tsla_pos])
        mock_broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="eod-force-1",
                broker_order_id="broker-eod-force-1",
                status=OrderStatus.PENDING,
            )
        )

        await om.eod_flatten()

        # TSLA should have been flattened immediately (not queued)
        assert len(om._startup_flatten_queue) == 0
        sell_symbols = [
            call[0][0].symbol
            for call in mock_broker.place_order.call_args_list
        ]
        assert "TSLA" in sell_symbols

    @pytest.mark.asyncio
    async def test_eod_flatten_broker_query_failure(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Broker query fails, logged, no crash."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        mock_broker.get_positions = AsyncMock(
            side_effect=RuntimeError("broker disconnected")
        )

        # Should not raise
        with caplog.at_level(logging.ERROR):
            await om.eod_flatten()

        assert "broker position query failed" in caplog.text


# ---------------------------------------------------------------------------
# R4: Startup zombie flatten queued for market open
# ---------------------------------------------------------------------------


class TestStartupFlattenQueue:
    """Verify pre-market zombie flatten is queued and drained at open."""

    @pytest.mark.asyncio
    async def test_startup_flatten_queue_premarket(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        premarket_clock: FixedClock,
    ) -> None:
        """Pre-market zombie flatten queued, not executed."""
        om = _make_om(event_bus, mock_broker, premarket_clock)

        await om._flatten_unknown_position("TSLA", 100)

        # Should be queued, not executed
        assert len(om._startup_flatten_queue) == 1
        assert om._startup_flatten_queue[0] == ("TSLA", 100)
        mock_broker.place_order.assert_not_called()

    @pytest.mark.asyncio
    async def test_startup_flatten_queue_drain(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
    ) -> None:
        """Queue drained on first market-hours poll."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)

        # Pre-populate the queue (as if startup happened pre-market)
        om._startup_flatten_queue = [("TSLA", 100), ("NVDA", 50)]

        mock_broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id="drain-1",
                broker_order_id="broker-drain-1",
                status=OrderStatus.PENDING,
            )
        )

        await om._drain_startup_flatten_queue()

        # Queue should be empty
        assert len(om._startup_flatten_queue) == 0

        # Both symbols should have had sell orders
        assert mock_broker.place_order.call_count == 2
        symbols = [
            call[0][0].symbol for call in mock_broker.place_order.call_args_list
        ]
        assert "TSLA" in symbols
        assert "NVDA" in symbols


# ---------------------------------------------------------------------------
# R5: Time-stop log suppression
# ---------------------------------------------------------------------------


class TestTimeStopLogSuppression:
    """Verify throttled logging when flatten is pending."""

    @pytest.mark.asyncio
    async def test_time_stop_log_suppressed_when_flatten_pending(
        self,
        event_bus: EventBus,
        mock_broker: MagicMock,
        market_hours_clock: FixedClock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Verify throttled logging when flatten is already pending."""
        om = _make_om(event_bus, mock_broker, market_hours_clock)
        position = await _open_position(om, mock_broker)

        # Set entry time in the past to trigger time stop
        position.time_stop_seconds = 60
        position.entry_time = market_hours_clock.now() - timedelta(minutes=5)

        # Mark as flatten pending (so log is suppressed via throttle)
        om._flatten_pending["AAPL"] = ("pending-order-1", _time.monotonic(), 0)

        # First call should log via throttle (first occurrence passes through)
        with caplog.at_level(logging.WARNING):
            # Manually trigger the time-stop check path by calling
            # _flatten_position which will short-circuit on pending guard
            # Instead, test that _flatten_position skips due to pending
            await om._flatten_position(position, reason="time_stop")

        # The flatten_pending guard suppresses the actual flatten
        # (warn_throttled emits at WARNING level)
        assert "Flatten already pending" in caplog.text or "flatten pending" in caplog.text.lower()


# ---------------------------------------------------------------------------
# R6: Config validation
# ---------------------------------------------------------------------------


class TestMaxFlattenCyclesConfig:
    """Verify max_flatten_cycles config field."""

    def test_max_flatten_cycles_config_validation(self) -> None:
        """Config loads with new max_flatten_cycles field."""
        config = OrderManagerConfig(max_flatten_cycles=5)
        assert config.max_flatten_cycles == 5

    def test_max_flatten_cycles_default(self) -> None:
        """Default value is 2."""
        config = OrderManagerConfig()
        assert config.max_flatten_cycles == 2

    def test_max_flatten_cycles_yaml(self) -> None:
        """Config YAML file includes max_flatten_cycles."""
        from pathlib import Path

        yaml_path = Path("config/order_manager.yaml")
        with yaml_path.open() as f:
            data = yaml.safe_load(f)

        assert "max_flatten_cycles" in data
        config = OrderManagerConfig(**data)
        assert config.max_flatten_cycles == 2
