"""Synchronous Event Bus for backtest-speed dispatch.

A lightweight alternative to the production EventBus that awaits handlers
directly instead of spawning asyncio tasks. No locks, no pending-task
tracking — designed for single-threaded backtest loops where sequential
dispatch is both correct and fast.

Same conceptual interface as EventBus so components can use either
interchangeably.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import replace
from typing import Any, TypeVar

from argus.core.events import Event

logger = logging.getLogger(__name__)

EventHandler = Callable[[Any], Coroutine[Any, Any, None]]
T = TypeVar("T", bound=Event)


class SyncEventBus:
    """Synchronous async event bus — awaits handlers in subscription order.

    Critical differences from production EventBus:
    - No asyncio.create_task() — handlers are awaited directly
    - No asyncio.Lock — single-threaded, no contention
    - No self._pending set — no background tasks
    """

    def __init__(self) -> None:
        self._subscribers: dict[type[Event], list[EventHandler]] = defaultdict(list)
        self._sequence: int = 0

    def subscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Register an async handler for an event type."""
        self._subscribers[event_type].append(handler)
        # FIX-05 (P1-A2-L04): mirror EventBus debug log for parity.
        logger.debug("Subscribed %s to %s", handler.__qualname__, event_type.__name__)

    def unsubscribe(self, event_type: type[T], handler: EventHandler) -> None:
        """Remove a handler for an event type.

        Raises:
            ValueError: If the handler is not subscribed to this event type.
        """
        try:
            self._subscribers[event_type].remove(handler)
            logger.debug(
                "Unsubscribed %s from %s", handler.__qualname__, event_type.__name__
            )
        except ValueError:
            raise ValueError(
                f"Handler {handler.__qualname__} is not subscribed to {event_type.__name__}"
            ) from None

    async def publish(self, event: Event) -> None:
        """Publish an event, awaiting each subscriber handler sequentially."""
        self._sequence += 1
        stamped_event = replace(event, sequence=self._sequence)

        event_type = type(stamped_event)
        handlers = self._subscribers.get(event_type, [])

        for handler in handlers:
            try:
                await handler(stamped_event)
            except Exception:
                logger.exception(
                    "Handler %s raised on %s (seq=%d)",
                    handler.__qualname__,
                    event_type.__name__,
                    stamped_event.sequence,
                )

    async def drain(self) -> None:
        """No-op — all handlers complete within publish()."""

    def subscriber_count(self, event_type: type[Event]) -> int:
        """Return the number of subscribers for an event type."""
        return len(self._subscribers.get(event_type, []))

    def reset(self) -> None:
        """Clear all subscriptions and reset sequence counter."""
        self._subscribers.clear()
        self._sequence = 0
