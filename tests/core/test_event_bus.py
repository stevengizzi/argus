"""Tests for the Argus Event Bus."""

import pytest

from argus.core.event_bus import EventBus
from argus.core.events import (
    CandleEvent,
    Event,
    HeartbeatEvent,
    TickEvent,
)


@pytest.fixture
def bus() -> EventBus:
    """Fresh EventBus for each test."""
    return EventBus()


class TestSubscribePublish:
    """Core subscribe/publish behavior."""

    async def test_subscriber_receives_event(self, bus: EventBus) -> None:
        """A subscriber receives a published event."""
        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="AAPL", close=150.0))
        await bus.drain()

        assert len(received) == 1
        assert received[0].symbol == "AAPL"
        assert received[0].close == 150.0

    async def test_multiple_subscribers_all_receive(self, bus: EventBus) -> None:
        """Multiple subscribers to the same event type all receive it."""
        received_a: list[Event] = []
        received_b: list[Event] = []

        async def handler_a(event: CandleEvent) -> None:
            received_a.append(event)

        async def handler_b(event: CandleEvent) -> None:
            received_b.append(event)

        bus.subscribe(CandleEvent, handler_a)
        bus.subscribe(CandleEvent, handler_b)
        await bus.publish(CandleEvent(symbol="MSFT"))
        await bus.drain()

        assert len(received_a) == 1
        assert len(received_b) == 1

    async def test_subscriber_only_receives_subscribed_type(self, bus: EventBus) -> None:
        """A subscriber to CandleEvent does not receive TickEvent."""
        received: list[Event] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(TickEvent(symbol="AAPL", price=150.0))
        await bus.drain()

        assert len(received) == 0

    async def test_no_subscribers_no_error(self, bus: EventBus) -> None:
        """Publishing with no subscribers does not raise."""
        await bus.publish(CandleEvent(symbol="AAPL"))
        await bus.drain()  # Should not hang or raise


class TestSequenceNumbers:
    """Monotonic sequence numbering."""

    async def test_sequence_numbers_are_monotonic(self, bus: EventBus) -> None:
        """Events receive sequential, increasing sequence numbers."""
        received: list[Event] = []

        async def handler(event: HeartbeatEvent) -> None:
            received.append(event)

        bus.subscribe(HeartbeatEvent, handler)

        for _ in range(5):
            await bus.publish(HeartbeatEvent())
        await bus.drain()

        sequences = [e.sequence for e in received]
        assert sequences == [1, 2, 3, 4, 5]

    async def test_sequence_numbers_span_event_types(self, bus: EventBus) -> None:
        """Sequence numbers are global, not per-event-type."""
        all_events: list[Event] = []

        async def candle_handler(event: CandleEvent) -> None:
            all_events.append(event)

        async def tick_handler(event: TickEvent) -> None:
            all_events.append(event)

        bus.subscribe(CandleEvent, candle_handler)
        bus.subscribe(TickEvent, tick_handler)

        await bus.publish(CandleEvent(symbol="A"))
        await bus.publish(TickEvent(symbol="B"))
        await bus.publish(CandleEvent(symbol="C"))
        await bus.drain()

        sequences = sorted([e.sequence for e in all_events])
        assert sequences == [1, 2, 3]

    async def test_original_event_sequence_not_mutated(self, bus: EventBus) -> None:
        """The original event object is not mutated (frozen dataclass)."""
        original = CandleEvent(symbol="AAPL")
        assert original.sequence == 0  # Default

        received: list[CandleEvent] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(original)
        await bus.drain()

        assert original.sequence == 0  # Unchanged
        assert received[0].sequence == 1  # Stamped copy


class TestUnsubscribe:
    """Unsubscribe behavior."""

    async def test_unsubscribed_handler_stops_receiving(self, bus: EventBus) -> None:
        """After unsubscribing, handler no longer receives events."""
        received: list[Event] = []

        async def handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="A"))
        await bus.drain()
        assert len(received) == 1

        bus.unsubscribe(CandleEvent, handler)
        await bus.publish(CandleEvent(symbol="B"))
        await bus.drain()
        assert len(received) == 1  # No new events

    async def test_unsubscribe_unknown_handler_raises(self, bus: EventBus) -> None:
        """Unsubscribing a handler that was never subscribed raises ValueError."""

        async def handler(event: CandleEvent) -> None:
            pass

        with pytest.raises(ValueError):
            bus.unsubscribe(CandleEvent, handler)


class TestErrorIsolation:
    """Handler errors are isolated."""

    async def test_failing_handler_does_not_break_others(self, bus: EventBus) -> None:
        """If one handler raises, other handlers still receive the event."""
        received: list[Event] = []

        async def bad_handler(event: CandleEvent) -> None:
            raise RuntimeError("I broke")

        async def good_handler(event: CandleEvent) -> None:
            received.append(event)

        bus.subscribe(CandleEvent, bad_handler)
        bus.subscribe(CandleEvent, good_handler)
        await bus.publish(CandleEvent(symbol="AAPL"))
        await bus.drain()

        assert len(received) == 1  # good_handler still got it


class TestUtilities:
    """Helper methods."""

    async def test_subscriber_count(self, bus: EventBus) -> None:
        """subscriber_count returns the correct number."""
        assert bus.subscriber_count(CandleEvent) == 0

        async def handler(e: CandleEvent) -> None:
            pass

        bus.subscribe(CandleEvent, handler)
        assert bus.subscriber_count(CandleEvent) == 1

    async def test_reset_clears_everything(self, bus: EventBus) -> None:
        """reset() clears subscribers and resets sequence counter."""

        async def handler(e: CandleEvent) -> None:
            pass

        bus.subscribe(CandleEvent, handler)
        await bus.publish(CandleEvent())
        await bus.drain()

        bus.reset()
        assert bus.subscriber_count(CandleEvent) == 0

        # Sequence counter resets too
        received: list[Event] = []

        async def new_handler(e: HeartbeatEvent) -> None:
            received.append(e)

        bus.subscribe(HeartbeatEvent, new_handler)
        await bus.publish(HeartbeatEvent())
        await bus.drain()
        assert received[0].sequence == 1  # Reset to 1, not continuing
