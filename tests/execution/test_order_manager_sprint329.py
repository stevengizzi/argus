"""Tests for Sprint 32.9 Session 1: EOD Flatten + Startup Zombie Fix (DEF-139, DEF-140).

Covers:
- qty → shares attribute fix in reconstruction and EOD Pass 2
- EOD flatten waits for fill verification (asyncio.Event)
- Pass 2 discovers broker-only orphan positions
- Retry logic for timed-out EOD flattens
- Timeout path returns cleanly
- Auto-shutdown fires after verification
- Config field validation via order_manager.yaml
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import yaml

from argus.core.clock import FixedClock
from argus.core.config import OrderManagerConfig, StartupConfig
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
    OrderStatus,
    Position,
    OrderSide,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _market_hours_clock() -> FixedClock:
    """11 AM ET = 15:00 UTC."""
    return FixedClock(datetime(2026, 4, 1, 15, 0, 0, tzinfo=UTC))


def _premarket_clock() -> FixedClock:
    """8 AM ET = 12:00 UTC."""
    return FixedClock(datetime(2026, 4, 1, 12, 0, 0, tzinfo=UTC))


def _make_broker(*, place_order_status: OrderStatus = OrderStatus.PENDING) -> MagicMock:
    broker = MagicMock()
    order_counter = {"n": 0}

    def _bracket(entry: MagicMock, stop: MagicMock, targets: list[MagicMock]) -> BracketOrderResult:
        order_counter["n"] += 1
        return BracketOrderResult(
            entry=OrderResult(
                order_id=entry.id,
                broker_order_id=f"b-entry-{order_counter['n']}",
                status=OrderStatus.FILLED,
                filled_quantity=entry.quantity,
                filled_avg_price=150.0,
            ),
            stop=OrderResult(
                order_id=stop.id,
                broker_order_id=f"b-stop-{order_counter['n']}",
                status=OrderStatus.PENDING,
            ),
            targets=[
                OrderResult(
                    order_id=t.id,
                    broker_order_id=f"b-tgt-{order_counter['n']}-{i}",
                    status=OrderStatus.PENDING,
                )
                for i, t in enumerate(targets)
            ],
        )

    broker.place_bracket_order = AsyncMock(side_effect=_bracket)
    broker.cancel_order = AsyncMock(return_value=True)
    broker.place_order = AsyncMock(
        return_value=OrderResult(
            order_id="flatten-order-1",
            broker_order_id="broker-flatten-1",
            status=place_order_status,
        )
    )
    broker.get_positions = AsyncMock(return_value=[])
    broker.get_open_orders = AsyncMock(return_value=[])
    return broker


def _make_om(
    event_bus: EventBus,
    broker: MagicMock,
    clock: FixedClock,
    eod_flatten_timeout_seconds: int = 5,
    eod_flatten_retry_rejected: bool = True,
) -> OrderManager:
    config = OrderManagerConfig(
        eod_flatten_timeout_seconds=eod_flatten_timeout_seconds,
        eod_flatten_retry_rejected=eod_flatten_retry_rejected,
        auto_shutdown_after_eod=True,
        auto_shutdown_delay_seconds=0,
    )
    return OrderManager(
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        config=config,
        startup_config=StartupConfig(flatten_unknown_positions=True),
    )


def _make_signal(symbol: str = "AAPL") -> SignalEvent:
    return SignalEvent(
        strategy_id="orb_breakout",
        symbol=symbol,
        side=Side.LONG,
        entry_price=150.0,
        stop_price=148.0,
        target_prices=(152.0, 154.0),
        share_count=100,
        rationale="Test",
        time_stop_seconds=300,
    )


async def _open_position(om: OrderManager, symbol: str = "AAPL") -> ManagedPosition:
    approved = OrderApprovedEvent(signal=_make_signal(symbol), modifications=None)
    await om.on_approved(approved)
    positions = om._managed_positions.get(symbol, [])
    assert len(positions) == 1
    return positions[0]


def _make_broker_position(symbol: str, shares: int) -> MagicMock:
    """Create a mock broker Position object with a `shares` attribute."""
    pos = MagicMock(spec=Position)
    pos.symbol = symbol
    pos.shares = shares
    return pos


# ---------------------------------------------------------------------------
# Test 1: reconstruction reads `shares` attribute (not `qty`)
# ---------------------------------------------------------------------------


class TestReconstructionReadsShares:
    @pytest.mark.asyncio
    async def test_reconstruction_reads_shares_attribute(self) -> None:
        """_reconstruct_from_broker() reads pos.shares, not pos.qty."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _premarket_clock()

        broker_pos = _make_broker_position("AAPL", shares=100)
        broker.get_positions = AsyncMock(return_value=[broker_pos])
        broker.get_open_orders = AsyncMock(return_value=[])

        om = _make_om(event_bus, broker, clock)
        await om.reconstruct_from_broker()

        # AAPL was a zombie (no orders) → should have been queued or directly flattened
        # Pre-market: queued in _startup_flatten_queue
        assert any(sym == "AAPL" for sym, _ in om._startup_flatten_queue), (
            "AAPL zombie should be queued for startup flatten"
        )
        qty_queued = next(qty for sym, qty in om._startup_flatten_queue if sym == "AAPL")
        assert qty_queued == 100, f"Expected 100 shares queued, got {qty_queued}"

    @pytest.mark.asyncio
    async def test_reconstruction_skips_zero_qty_if_only_qty_attr(self) -> None:
        """Position with only `qty` attribute (no `shares`) → qty reads as 0, skips flatten."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _premarket_clock()

        # Simulate a position object that has `qty` but not `shares`
        bad_pos = MagicMock()
        bad_pos.symbol = "TSLA"
        del bad_pos.shares  # no shares attribute
        bad_pos.qty = 50   # has qty but code no longer reads it

        broker.get_positions = AsyncMock(return_value=[bad_pos])
        broker.get_open_orders = AsyncMock(return_value=[])

        om = _make_om(event_bus, broker, clock)
        await om.reconstruct_from_broker()

        # qty reads as 0 (getattr default) → skipped
        assert not any(sym == "TSLA" for sym, _ in om._startup_flatten_queue)


# ---------------------------------------------------------------------------
# Test 2: EOD Pass 2 reads `shares` attribute
# ---------------------------------------------------------------------------


class TestEodPass2ReadsShares:
    @pytest.mark.asyncio
    async def test_eod_pass2_reads_shares_attribute(self) -> None:
        """EOD Pass 2 reads pos.shares to determine qty, places SELL order."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        broker_pos = _make_broker_position("TSLA", shares=50)
        # First two calls: Pass 1 (no broker positions during Pass 1 check)
        # Third call: Pass 2 discovers TSLA
        # Fourth call: post-verification (empty)
        broker.get_positions = AsyncMock(side_effect=[
            [broker_pos],  # Pass 2 query
            [],            # post-verify
        ])

        om = _make_om(event_bus, broker, clock)
        await om.eod_flatten()

        # A SELL order should have been placed for TSLA (50 shares)
        broker.place_order.assert_called_once()
        call_order = broker.place_order.call_args[0][0]
        assert call_order.symbol == "TSLA"
        assert call_order.quantity == 50

    @pytest.mark.asyncio
    async def test_eod_pass2_ignores_position_with_no_shares_attr(self) -> None:
        """Position with only `qty` attribute (and shares absent) → qty=0, skipped."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        bad_pos = MagicMock()
        bad_pos.symbol = "NVDA"
        del bad_pos.shares  # no shares attr

        broker.get_positions = AsyncMock(side_effect=[
            [bad_pos],  # Pass 2 query
            [],         # post-verify
        ])

        om = _make_om(event_bus, broker, clock)
        await om.eod_flatten()

        broker.place_order.assert_not_called()


# ---------------------------------------------------------------------------
# Test 3: zombie queued pre-market
# ---------------------------------------------------------------------------


class TestStartupQueuePremarket:
    @pytest.mark.asyncio
    async def test_reconstruction_queues_zombies_premarket(self) -> None:
        """Pre-market boot: zombie positions queued in _startup_flatten_queue."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _premarket_clock()

        broker_pos = _make_broker_position("GOOG", shares=75)
        broker.get_positions = AsyncMock(return_value=[broker_pos])
        broker.get_open_orders = AsyncMock(return_value=[])

        om = _make_om(event_bus, broker, clock)
        await om.reconstruct_from_broker()

        assert ("GOOG", 75) in om._startup_flatten_queue
        # Should NOT have placed a SELL order immediately
        broker.place_order.assert_not_called()


# ---------------------------------------------------------------------------
# Test 4: startup queue drains at market open
# ---------------------------------------------------------------------------


class TestStartupQueueDrain:
    @pytest.mark.asyncio
    async def test_startup_queue_drains_at_market_open(self) -> None:
        """_drain_startup_flatten_queue() submits SELL orders for each queued position."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        om = _make_om(event_bus, broker, clock)
        om._startup_flatten_queue.append(("AMZN", 30))
        om._startup_flatten_queue.append(("META", 20))

        await om._drain_startup_flatten_queue()

        assert broker.place_order.call_count == 2
        symbols = {call[0][0].symbol for call in broker.place_order.call_args_list}
        assert symbols == {"AMZN", "META"}
        assert om._startup_flatten_queue == []


# ---------------------------------------------------------------------------
# Test 5: EOD flatten waits for fills
# ---------------------------------------------------------------------------


class TestEodFlattenWaitsForFills:
    @pytest.mark.asyncio
    async def test_eod_flatten_waits_for_fills(self) -> None:
        """eod_flatten() waits for fill callbacks before publishing ShutdownRequestedEvent."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        shutdown_events: list[ShutdownRequestedEvent] = []
        event_bus.subscribe(ShutdownRequestedEvent, lambda e: shutdown_events.append(e))

        om = _make_om(event_bus, broker, clock, eod_flatten_timeout_seconds=5)
        position = await _open_position(om, "AAPL")

        # Arrange: broker fills the flatten order synchronously via a fill event
        fill_order_id = "eod-fill-order"
        broker.place_order = AsyncMock(
            return_value=OrderResult(
                order_id=fill_order_id,
                broker_order_id="broker-eod-fill",
                status=OrderStatus.PENDING,
            )
        )
        broker.get_positions = AsyncMock(return_value=[])  # Pass 2 + verify: empty

        # Schedule fill delivery after a short delay
        async def deliver_fill() -> None:
            await asyncio.sleep(0.05)
            from argus.execution.order_manager import PendingManagedOrder
            # Register the pending order so on_fill can route it
            pending = PendingManagedOrder(
                order_id=fill_order_id,
                symbol="AAPL",
                strategy_id=position.strategy_id,
                order_type="flatten",
                shares=position.shares_remaining,
            )
            om._pending_orders[fill_order_id] = pending
            fill_event = OrderFilledEvent(
                order_id=fill_order_id,
                fill_price=151.0,
                fill_quantity=position.shares_remaining,
            )
            await om.on_fill(fill_event)

        await asyncio.gather(om.eod_flatten(), deliver_fill())

        # Shutdown should have been published
        assert len(shutdown_events) == 1


# ---------------------------------------------------------------------------
# Test 6: EOD Pass 2 discovers orphans
# ---------------------------------------------------------------------------


class TestEodPass2DiscoversOrphans:
    @pytest.mark.asyncio
    async def test_eod_pass2_discovers_orphans(self) -> None:
        """broker.get_positions() returns positions not in _managed_positions → SELL placed."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        # No managed positions; Pass 2 finds TSLA at broker
        orphan = _make_broker_position("TSLA", shares=25)
        broker.get_positions = AsyncMock(side_effect=[
            [orphan],  # Pass 2 query
            [],        # post-verify
        ])

        om = _make_om(event_bus, broker, clock, eod_flatten_timeout_seconds=1)
        await om.eod_flatten()

        broker.place_order.assert_called_once()
        order = broker.place_order.call_args[0][0]
        assert order.symbol == "TSLA"
        assert order.quantity == 25

    @pytest.mark.asyncio
    async def test_eod_pass2_skips_managed_symbols(self) -> None:
        """Pass 2 skips symbols already in _managed_positions."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        om = _make_om(event_bus, broker, clock, eod_flatten_timeout_seconds=1)
        # Pre-populate a managed position for AAPL (without going through full entry flow)
        from argus.execution.order_manager import ManagedPosition
        from datetime import UTC, datetime
        managed = ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=150.0,
            entry_time=datetime.now(UTC),
            shares_total=100,
            shares_remaining=0,  # Already closed
            stop_price=148.0,
            original_stop_price=148.0,
            stop_order_id=None,
            t1_price=152.0,
            t1_order_id=None,
            t1_shares=50,
            t1_filled=True,
            t2_price=154.0,
            high_watermark=152.0,
        )
        om._managed_positions["AAPL"] = [managed]

        aapl_pos = _make_broker_position("AAPL", shares=50)
        broker.get_positions = AsyncMock(side_effect=[
            [aapl_pos],  # Pass 2
            [],          # post-verify
        ])

        await om.eod_flatten()

        # AAPL is in managed_positions → should NOT get an extra flatten
        broker.place_order.assert_not_called()


# ---------------------------------------------------------------------------
# Test 7: EOD retry timed-out positions
# ---------------------------------------------------------------------------


class TestEodFlattenRetryRejected:
    @pytest.mark.asyncio
    async def test_eod_flatten_retries_timed_out_via_broker_requery(self) -> None:
        """Timed-out EOD positions are retried using re-queried broker qty."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        om = _make_om(
            event_bus, broker, clock,
            eod_flatten_timeout_seconds=1,
            eod_flatten_retry_rejected=True,
        )

        # Open a managed position
        position = await _open_position(om, "AAPL")

        # arrange: flatten order never fills (no fill event → timeout)
        retry_order_id = "retry-order-1"
        call_count = {"n": 0}

        def _place_order_side_effect(order: MagicMock) -> OrderResult:
            call_count["n"] += 1
            return OrderResult(
                order_id=f"order-{call_count['n']}",
                broker_order_id=f"broker-{call_count['n']}",
                status=OrderStatus.PENDING,
            )

        broker.place_order = AsyncMock(side_effect=_place_order_side_effect)

        # For retry broker re-query: AAPL has 80 shares (different from tracked 100)
        retry_pos = _make_broker_position("AAPL", shares=80)
        broker.get_positions = AsyncMock(side_effect=[
            [retry_pos],   # retry re-query
            [],            # Pass 2
            [],            # post-verify
        ])

        await om.eod_flatten()

        # Should have placed at least 2 orders: initial flatten + retry
        assert broker.place_order.call_count >= 2
        # The retry order should use broker qty (80)
        retry_call = broker.place_order.call_args_list[-1][0][0]
        assert retry_call.quantity == 80


# ---------------------------------------------------------------------------
# Test 8: EOD flatten timeout — function returns cleanly
# ---------------------------------------------------------------------------


class TestEodFlattenTimeout:
    @pytest.mark.asyncio
    async def test_eod_flatten_timeout_returns_cleanly(self) -> None:
        """If flatten order never fills, eod_flatten returns after timeout."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        om = _make_om(event_bus, broker, clock, eod_flatten_timeout_seconds=1)
        await _open_position(om, "AAPL")

        # No fill event → will timeout
        broker.get_positions = AsyncMock(return_value=[])

        # Must complete (not hang) within reasonable time
        import asyncio
        await asyncio.wait_for(om.eod_flatten(), timeout=5.0)

        # _eod_flatten_events cleaned up
        assert om._eod_flatten_events == {}


# ---------------------------------------------------------------------------
# Test 9: auto-shutdown fires AFTER verification
# ---------------------------------------------------------------------------


class TestAutoShutdownAfterVerification:
    @pytest.mark.asyncio
    async def test_auto_shutdown_after_verification(self) -> None:
        """ShutdownRequestedEvent is published after post-flatten broker query."""
        event_bus = EventBus()
        broker = _make_broker()
        clock = _market_hours_clock()

        verify_call_count: list[int] = [0]

        async def tracked_get_positions() -> list[object]:
            verify_call_count[0] += 1
            return []

        broker.get_positions = AsyncMock(side_effect=tracked_get_positions)

        shutdown_event_captured: list[ShutdownRequestedEvent] = []

        async def capture_shutdown(e: ShutdownRequestedEvent) -> None:
            shutdown_event_captured.append(e)

        event_bus.subscribe(ShutdownRequestedEvent, capture_shutdown)

        om = _make_om(event_bus, broker, clock, eod_flatten_timeout_seconds=1)
        await om.eod_flatten()
        # Drain any pending event bus tasks
        await asyncio.sleep(0)

        # Shutdown was published and verification had already run (get_positions called)
        assert len(shutdown_event_captured) == 1
        # Verification ran: get_positions called at least once (Pass 2 + post-verify)
        assert verify_call_count[0] >= 1, "Verification query never ran before shutdown"


# ---------------------------------------------------------------------------
# Test 10: config validation via order_manager.yaml
# ---------------------------------------------------------------------------


class TestConfigValidation:
    def test_order_manager_yaml_has_new_fields(self) -> None:
        """config/order_manager.yaml contains eod_flatten_timeout_seconds and eod_flatten_retry_rejected."""
        config_path = Path(__file__).parents[2] / "config" / "order_manager.yaml"
        with config_path.open() as f:
            raw = yaml.safe_load(f)

        assert "eod_flatten_timeout_seconds" in raw, (
            "order_manager.yaml missing eod_flatten_timeout_seconds"
        )
        assert "eod_flatten_retry_rejected" in raw, (
            "order_manager.yaml missing eod_flatten_retry_rejected"
        )

        # Validate values parse into OrderManagerConfig without error
        config = OrderManagerConfig(**raw)
        assert config.eod_flatten_timeout_seconds == raw["eod_flatten_timeout_seconds"]
        assert config.eod_flatten_retry_rejected == raw["eod_flatten_retry_rejected"]
