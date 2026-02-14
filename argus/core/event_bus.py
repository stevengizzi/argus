"""Argus Event Bus — in-process async pub/sub.

The Event Bus is the communication backbone of the Argus system. Components
publish typed events and subscribe to event types. FIFO delivery per subscriber.
No global ordering guarantees. No priority queues.

Every event is assigned a monotonic sequence number at publish time for
debugging and deterministic replay.

Usage:
    bus = EventBus()

    async def my_handler(event: CandleEvent) -> None:
        print(f"Got candle: {event.symbol}")

    bus.subscribe(CandleEvent, my_handler)
    await bus.publish(CandleEvent(symbol="AAPL", ...))
    await bus.drain()  # Wait for all handlers to complete
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import replace
from typing import Any, TypeVar

from argus.core.events import Event

logger = logging.getLogger(__name__)

# Type alias for an async event handler
EventHandler = Callable[[Any], Coroutine[Any, Any, None]]

# TypeVar for event types
T = TypeVar("T", bound=Event)


class EventBus:
    """In-process async event bus with FIFO delivery per subscriber.

    Attributes:
        _subscribers: Mapping of event type to list of handler functions.
        _sequence: Monotonic counter for event sequence numbers.
        _pending: Set of pending handler tasks for drain().
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._sequence: int = 0
        self._pending: set[asyncio.Task[None]] = set()
        self._lock: asyncio.Lock = asyncio.Lock()

    def subscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Register a handler for an event type.

        The handler will be called with every event of this type (or subtype)
        published to the bus. Handlers are called in subscription order (FIFO).

        Args:
            event_type: The event class to subscribe to.
            handler: Async callable that takes an event instance.
        """
        self._subscribers[event_type].append(handler)
        logger.debug("Subscribed %s to %s", handler.__qualname__, event_type.__name__)

    def unsubscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Remove a handler for an event type.

        Args:
            event_type: The event class to unsubscribe from.
            handler: The handler to remove.

        Raises:
            ValueError: If the handler is not subscribed to this event type.
        """
        try:
            self._subscribers[event_type].remove(handler)
            logger.debug("Unsubscribed %s from %s", handler.__qualname__, event_type.__name__)
        except ValueError:
            raise ValueError(
                f"Handler {handler.__qualname__} is not subscribed to {event_type.__name__}"
            ) from None

    async def publish(self, event: Event) -> None:
        """Publish an event to all subscribers of its type.

        Assigns a monotonic sequence number to the event before delivery.
        Handlers are dispatched as async tasks and run concurrently.

        Args:
            event: The event to publish.
        """
        async with self._lock:
            self._sequence += 1
            seq = self._sequence

        # Replace the sequence number on the (frozen) event
        stamped_event = replace(event, sequence=seq)

        event_type = type(stamped_event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug(
                "No subscribers for %s (seq=%d)", event_type.__name__, seq
            )
            return

        for handler in handlers:
            task = asyncio.create_task(
                self._safe_call(handler, stamped_event),
                name=f"{event_type.__name__}->{handler.__qualname__}",
            )
            self._pending.add(task)
            task.add_done_callback(self._pending.discard)

    async def _safe_call(self, handler: EventHandler, event: Event) -> None:
        """Call a handler with error isolation.

        If a handler raises, the exception is logged but does not propagate.
        One bad handler must not break other subscribers.
        """
        try:
            await handler(event)
        except Exception:
            logger.exception(
                "Handler %s raised on %s (seq=%d)",
                handler.__qualname__,
                type(event).__name__,
                event.sequence,
            )

    async def drain(self) -> None:
        """Wait for all pending handler tasks to complete.

        Useful in tests and shutdown sequences to ensure all events
        have been fully processed before proceeding.
        """
        if self._pending:
            await asyncio.gather(*self._pending, return_exceptions=True)

    def subscriber_count(self, event_type: type[Event]) -> int:
        """Return the number of subscribers for an event type.

        Args:
            event_type: The event class to check.

        Returns:
            Number of registered handlers.
        """
        return len(self._subscribers.get(event_type, []))

    def reset(self) -> None:
        """Clear all subscriptions and reset sequence counter.

        Intended for testing only. Do not call during live trading.
        """
        self._subscribers.clear()
        self._sequence = 0
        self._pending.clear()
