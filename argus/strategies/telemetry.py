"""Strategy evaluation telemetry: event model and ring buffer.

Provides fire-and-forget decision logging for all strategies. Events accumulate
in a bounded ring buffer (BUFFER_MAX_SIZE=1000) and are exposed via REST for
the Command Center Decision Explorer.
"""

from __future__ import annotations

import asyncio
import collections
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from argus.strategies.telemetry_store import EvaluationEventStore

logger = logging.getLogger(__name__)

BUFFER_MAX_SIZE = 1000


class EvaluationEventType(StrEnum):
    """Category of evaluation step emitted by a strategy."""

    TIME_WINDOW_CHECK = "TIME_WINDOW_CHECK"
    INDICATOR_STATUS = "INDICATOR_STATUS"
    OPENING_RANGE_UPDATE = "OPENING_RANGE_UPDATE"
    ENTRY_EVALUATION = "ENTRY_EVALUATION"
    CONDITION_CHECK = "CONDITION_CHECK"
    SIGNAL_GENERATED = "SIGNAL_GENERATED"
    SIGNAL_REJECTED = "SIGNAL_REJECTED"
    STATE_TRANSITION = "STATE_TRANSITION"
    QUALITY_SCORED = "QUALITY_SCORED"


class EvaluationResult(StrEnum):
    """Outcome of a single evaluation step."""

    PASS = "PASS"
    FAIL = "FAIL"
    INFO = "INFO"


@dataclass(frozen=True)
class EvaluationEvent:
    """A single strategy evaluation event.

    Attributes:
        timestamp: ET naive datetime (no tzinfo) per DEC-276.
        symbol: The ticker being evaluated.
        strategy_id: ID of the strategy that produced this event.
        event_type: Category of evaluation step.
        result: Whether the step passed, failed, or is informational.
        reason: Human-readable explanation of the result.
        metadata: Strategy-specific supplemental data.
    """

    timestamp: datetime
    symbol: str
    strategy_id: str
    event_type: EvaluationEventType
    result: EvaluationResult
    reason: str
    metadata: dict[str, object] = field(default_factory=dict)


class StrategyEvaluationBuffer:
    """Thread-safe bounded ring buffer for strategy evaluation events.

    Wraps a collections.deque with maxlen=BUFFER_MAX_SIZE. When full, the
    oldest events are automatically evicted (FIFO).
    """

    def __init__(self, maxlen: int = BUFFER_MAX_SIZE) -> None:
        """Initialize buffer with given max capacity.

        Args:
            maxlen: Maximum number of events to retain. Oldest are evicted when full.
        """
        self._events: collections.deque[EvaluationEvent] = collections.deque(maxlen=maxlen)
        self._store: EvaluationEventStore | None = None

    def set_store(self, store: EvaluationEventStore) -> None:
        """Attach a persistent store for durable event writes.

        Args:
            store: The initialized EvaluationEventStore instance.
        """
        self._store = store

    def record(self, event: EvaluationEvent) -> None:
        """Append an event to the buffer and persist to store if available.

        Args:
            event: The evaluation event to record.
        """
        self._events.append(event)
        if self._store is not None:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._store.write_event(event))
            except Exception:
                pass  # No event loop or store error — degrade gracefully

    def query(
        self,
        *,
        symbol: str | None = None,
        limit: int = 100,
    ) -> list[EvaluationEvent]:
        """Return events newest-first, optionally filtered by symbol.

        Args:
            symbol: If provided, only return events for this ticker.
            limit: Maximum number of events to return.

        Returns:
            List of matching events, newest first, capped at limit.
        """
        results: list[EvaluationEvent] = []
        for event in reversed(self._events):
            if symbol is not None and event.symbol != symbol:
                continue
            results.append(event)
            if len(results) >= limit:
                break
        return results

    def snapshot(self) -> list[EvaluationEvent]:
        """Return a point-in-time snapshot of all buffered events in insertion order.

        Returns:
            A new list containing all current events.
        """
        return list(self._events)

    def __len__(self) -> int:
        """Return the number of events currently in the buffer."""
        return len(self._events)
