"""Structural Protocol types for duck-typed cross-package references.

Several components hold references to collaborators across package
boundaries where a direct import would create a circular dependency.
Before this module, those attributes were typed as ``object`` and the
call sites used ``hasattr()`` to probe the interface, losing static
type checking entirely (DEF-096).

The Protocols here describe the minimum method surface each collaborator
is expected to expose. Consumers import them under ``TYPE_CHECKING`` so
the type checker sees a real interface, but runtime dispatch remains
duck-typed and the circular import is avoided.

Added by FIX-07 (audit 2026-04-21) following the FIX-06 precedent for
additive type-safety scope expansion into core/.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from argus.core.events import Event
    from argus.intelligence.counterfactual import CounterfactualPosition
    from argus.strategies.patterns.base import CandleBar


@runtime_checkable
class CandleStoreProtocol(Protocol):
    """Read surface of ``IntradayCandleStore`` for duck-typed consumers.

    ``PatternBasedStrategy`` and ``CounterfactualTracker`` both hold a
    reference to the intraday candle store for auto-backfill. Importing
    ``IntradayCandleStore`` directly in either module would create a
    cycle through the data layer; this Protocol captures the read-only
    methods those consumers actually use.
    """

    def has_bars(self, symbol: str) -> bool:
        """Return True if at least one bar exists for ``symbol``."""
        ...

    def get_bars(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CandleBar]:
        """Return bars for ``symbol`` optionally filtered by time range."""
        ...


@runtime_checkable
class EventBusProtocol(Protocol):
    """Structural interface shared by ``EventBus`` and ``SyncEventBus``.

    Backtest components (``BacktestDataService``, ``BacktestEngine``) accept
    either the production async ``EventBus`` or the ``SyncEventBus`` used by
    the sprint-27 BacktestEngine path. Before this Protocol, call sites
    carried ``# type: ignore[arg-type]`` comments because the two concrete
    classes share no ancestor — even though both expose the same minimum
    ``subscribe`` + ``publish`` surface. FIX-09 P1-E1-L05 formalizes that
    shared surface so Pylance sees a real interface.

    Note: only ``BacktestDataService`` was retyped against this Protocol
    during FIX-09 (execution-layer sites outside FIX-09 scope remain on
    ``# type: ignore`` and are tracked in DEF-186).
    """

    def subscribe(
        self,
        event_type: type[Event],
        handler: Callable[[Any], Coroutine[Any, Any, None]],
    ) -> None:
        """Register ``handler`` for events of ``event_type``."""
        ...

    async def publish(self, event: Event) -> None:
        """Publish ``event`` to all subscribers of its type."""
        ...


@runtime_checkable
class CounterfactualStoreProtocol(Protocol):
    """Write surface of ``CounterfactualStore`` for fire-and-forget callers.

    ``CounterfactualTracker`` persists open/close snapshots without
    importing the store class (the store imports the tracker's dataclass,
    which would otherwise cycle). This Protocol captures the two async
    write methods the tracker invokes.
    """

    async def write_open(self, position: CounterfactualPosition) -> None:
        """Persist a newly opened counterfactual position snapshot."""
        ...

    async def write_close(self, position: CounterfactualPosition) -> None:
        """Persist a closed counterfactual position snapshot."""
        ...


__all__ = [
    "CandleStoreProtocol",
    "CounterfactualStoreProtocol",
    "EventBusProtocol",
]
