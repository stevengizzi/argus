"""IntradayCandleStore — centralized in-memory store for live session bars.

Subscribes to CandleEvent on the Event Bus and accumulates bars per symbol
during market hours. Provides a queryable API for the bars endpoint and
pattern strategy backfill.

Thread safety (FIX-06 audit 2026-04-21, P1-C2-4): writes come via
``call_soon_threadsafe`` (DEC-088), so ``on_candle`` runs on the asyncio
thread. The query methods (``get_bars``, ``get_latest``, ``has_bars``,
``bar_count``, ``symbols_with_bars``) are synchronous ``def`` — FastAPI
dispatches sync route handlers in a threadpool, so reads CAN happen on a
worker thread concurrent with the asyncio writer. This is safe on CPython
because ``deque.append`` / ``deque.popleft`` with ``maxlen`` are GIL-atomic
against ``list(deque)`` snapshots — no additional locking needed. If a
future caller needs a stronger consistency guarantee (e.g. coherent
multi-field snapshot across helpers), introduce an ``asyncio.Lock`` at
that caller rather than here.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, time as dt_time
from typing import TYPE_CHECKING

from zoneinfo import ZoneInfo

from argus.strategies.patterns.base import CandleBar

if TYPE_CHECKING:
    from argus.core.events import CandleEvent

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

# Session boundaries (ET): pre-market opens at 4:00 AM, regular close at 4:00 PM
_MARKET_OPEN = dt_time(4, 0)
_MARKET_CLOSE = dt_time(16, 0)

# 12 hours of 1-minute bars (4:00 AM to 4:00 PM ET)
_MAX_BARS_PER_SYMBOL = 720


class IntradayCandleStore:
    """In-memory store for intraday candle bars.

    Accumulates CandleEvents during market hours, providing queryable
    access for the market bars API endpoint and pattern strategy backfill.

    Attributes:
        _bars: Per-symbol deque of CandleBars, capped at 720 (12-hour session).
    """

    def __init__(self) -> None:
        """Initialize the candle store with empty state."""
        self._bars: dict[str, deque[CandleBar]] = {}

    async def on_candle(self, event: CandleEvent) -> None:
        """Handle a CandleEvent from the Event Bus.

        Filters out overnight bars and stores pre-market (4:00 AM ET+) through
        regular-session 1-minute bars.

        Args:
            event: The CandleEvent to process.
        """
        # Only store 1-minute bars
        if event.timeframe != "1m":
            return

        # Convert timestamp to ET for market hours check (DEC-061). FIX-06
        # audit 2026-04-21 (P1-C2-8): fail-fast on naive timestamps — the
        # production Databento path always emits UTC-aware timestamps, so
        # a naive ts means a test fixture or synthetic event forgot
        # ``tzinfo`` and would otherwise be silently mis-bucketed as ET.
        ts = event.timestamp
        if ts.tzinfo is None:
            raise ValueError(
                f"IntradayCandleStore.on_candle requires timezone-aware "
                f"timestamps; received naive {ts!r} for symbol "
                f"{event.symbol}. CandleEvent producers must attach "
                f"tzinfo (UTC for Databento, ET for replay)."
            )
        ts_et = ts.astimezone(ET)

        current_time = ts_et.time()
        if current_time < _MARKET_OPEN or current_time >= _MARKET_CLOSE:
            return

        bar = CandleBar(
            timestamp=event.timestamp,
            open=event.open,
            high=event.high,
            low=event.low,
            close=event.close,
            volume=event.volume,
        )

        if event.symbol not in self._bars:
            self._bars[event.symbol] = deque(maxlen=_MAX_BARS_PER_SYMBOL)

        self._bars[event.symbol].append(bar)

    def get_bars(
        self,
        symbol: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
    ) -> list[CandleBar]:
        """Get bars for a symbol, optionally filtered by time range.

        Args:
            symbol: Stock symbol (e.g., "AAPL").
            start_time: Optional start time filter (inclusive).
            end_time: Optional end time filter (inclusive).

        Returns:
            List of CandleBars matching the criteria, ordered by timestamp.
        """
        bars = self._bars.get(symbol)
        if not bars:
            return []

        if start_time is None and end_time is None:
            return list(bars)

        result: list[CandleBar] = []
        for bar in bars:
            if start_time is not None and bar.timestamp < start_time:
                continue
            if end_time is not None and bar.timestamp > end_time:
                continue
            result.append(bar)

        return result

    def get_latest(self, symbol: str, count: int = 1) -> list[CandleBar]:
        """Get the N most recent bars for a symbol.

        Args:
            symbol: Stock symbol.
            count: Number of bars to return.

        Returns:
            List of the most recent CandleBars (up to count).
        """
        bars = self._bars.get(symbol)
        if not bars:
            return []

        if count >= len(bars):
            return list(bars)

        return list(bars)[-count:]

    def has_bars(self, symbol: str) -> bool:
        """Check if bars exist for a symbol.

        Args:
            symbol: Stock symbol.

        Returns:
            True if at least one bar exists for the symbol.
        """
        bars = self._bars.get(symbol)
        return bars is not None and len(bars) > 0

    def bar_count(self, symbol: str) -> int:
        """Get the number of stored bars for a symbol.

        Args:
            symbol: Stock symbol.

        Returns:
            Number of bars stored for the symbol.
        """
        bars = self._bars.get(symbol)
        return len(bars) if bars else 0

    def symbols_with_bars(self) -> list[str]:
        """Get all symbols that have at least one stored bar.

        Returns:
            Sorted list of symbol names.
        """
        return sorted(sym for sym, bars in self._bars.items() if len(bars) > 0)

    def reset(self) -> None:
        """Clear all stored bar data (for start-of-day cleanup)."""
        self._bars.clear()
        logger.info("IntradayCandleStore reset — all bars cleared")
