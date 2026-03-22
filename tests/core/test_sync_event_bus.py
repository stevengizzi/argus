"""Tests for the SynchronousEventBus used in backtest dispatch."""

from __future__ import annotations

import pytest

from argus.core.events import CandleEvent, HeartbeatEvent
from argus.core.sync_event_bus import SyncEventBus


@pytest.fixture
def bus() -> SyncEventBus:
    return SyncEventBus()


class TestSyncEventBus:
    """Tests for SyncEventBus subscribe/publish/drain/reset."""

    @pytest.mark.asyncio
    async def test_subscribe_and_publish(self, bus: SyncEventBus) -> None:
        """Handler receives a published event with sequence number set."""
        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="AAPL"))

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].sequence == 1

    @pytest.mark.asyncio
    async def test_publish_multiple_handlers(self, bus: SyncEventBus) -> None:
        """All handlers are called in subscription order."""
        call_order: list[str] = []

        async def first(event: CandleEvent) -> None:
            call_order.append("first")

        async def second(event: CandleEvent) -> None:
            call_order.append("second")

        async def third(event: CandleEvent) -> None:
            call_order.append("third")

        bus.subscribe(CandleEvent, first)
        bus.subscribe(CandleEvent, second)
        bus.subscribe(CandleEvent, third)
        await bus.publish(CandleEvent(symbol="TSLA"))

        assert call_order == ["first", "second", "third"]

    @pytest.mark.asyncio
    async def test_publish_no_subscribers(self, bus: SyncEventBus) -> None:
        """Publishing to an event type with no subscribers completes cleanly."""
        await bus.publish(CandleEvent(symbol="MSFT"))
        # No error — implicit pass

    @pytest.mark.asyncio
    async def test_sequence_numbers(self, bus: SyncEventBus) -> None:
        """Events get incrementing sequence numbers across publishes."""
        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="A"))
        await bus.publish(CandleEvent(symbol="B"))
        await bus.publish(CandleEvent(symbol="C"))

        assert [e.sequence for e in received] == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_error_isolation(self, bus: SyncEventBus) -> None:
        """A handler exception does not prevent other handlers from running."""
        called: list[str] = []

        async def bad_handler(event: CandleEvent) -> None:
            raise RuntimeError("boom")

        async def good_handler(event: CandleEvent) -> None:
            called.append("good")

        bus.subscribe(CandleEvent, bad_handler)
        bus.subscribe(CandleEvent, good_handler)
        await bus.publish(CandleEvent(symbol="NVDA"))

        assert called == ["good"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self, bus: SyncEventBus) -> None:
        """Unsubscribed handler is not called on subsequent publishes."""
        called: list[str] = []

        async def handler(event: CandleEvent) -> None:
            called.append("called")

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="A"))
        assert len(called) == 1

        bus.unsubscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="B"))
        assert len(called) == 1  # still 1 — handler not called again

    @pytest.mark.asyncio
    async def test_drain_is_noop(self, bus: SyncEventBus) -> None:
        """drain() completes immediately (no pending tasks to wait for)."""
        await bus.drain()
        # No error, no delay — implicit pass

    @pytest.mark.asyncio
    async def test_reset(self, bus: SyncEventBus) -> None:
        """reset() clears subscribers and resets the sequence counter."""
        received: list[HeartbeatEvent] = []

        async def handler(event: HeartbeatEvent) -> None:
            received.append(event)

        bus.subscribe(HeartbeatEvent, handler)
        await bus.publish(HeartbeatEvent())
        assert len(received) == 1
        assert received[0].sequence == 1

        bus.reset()

        assert bus.subscriber_count(HeartbeatEvent) == 0

        # Re-subscribe and verify sequence restarted
        bus.subscribe(HeartbeatEvent, handler)
        await bus.publish(HeartbeatEvent())
        assert len(received) == 2
        assert received[1].sequence == 1  # reset to 0, first publish = 1
