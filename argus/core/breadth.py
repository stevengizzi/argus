"""Universe breadth calculator for regime intelligence (Sprint 27.6).

Tracks intraday universe participation breadth from 1-minute CandleEvents.
Returns universe_breadth_score and breadth_thrust for the RegimeVector
breadth dimension.

This is a standalone, passive module — no Event Bus subscription here.
Wiring happens in S6.
"""

from __future__ import annotations

import statistics
from collections import deque

from argus.core.config import BreadthConfig
from argus.core.events import CandleEvent


class BreadthCalculator:
    """Tracks per-symbol rolling close prices to compute universe breadth.

    Consumes CandleEvent updates via on_candle() and produces a breadth
    snapshot via get_breadth_snapshot(). O(1) per candle update.

    Args:
        config: BreadthConfig controlling MA period, thresholds, and minimums.
    """

    def __init__(self, config: BreadthConfig) -> None:
        """Initialize the breadth calculator.

        Args:
            config: BreadthConfig with ma_period, thrust_threshold,
                min_symbols, and min_bars_for_valid.
        """
        if not isinstance(config, BreadthConfig):
            raise TypeError(f"config must be BreadthConfig, got {type(config).__name__}")
        self._config = config
        self._symbol_closes: dict[str, deque[float]] = {}

    def on_candle(self, event: CandleEvent) -> None:
        """Update rolling close price for the candle's symbol.

        O(1) per call: dict lookup + deque append (bounded by maxlen).

        Args:
            event: A completed CandleEvent with symbol and close price.
        """
        if not isinstance(event, CandleEvent):
            raise TypeError(f"event must be CandleEvent, got {type(event).__name__}")

        symbol = event.symbol
        if symbol not in self._symbol_closes:
            self._symbol_closes[symbol] = deque(maxlen=self._config.ma_period)
        self._symbol_closes[symbol].append(event.close)

    def get_breadth_snapshot(self) -> dict[str, float | bool | int | None]:
        """Compute current breadth metrics from accumulated candle data.

        Returns:
            Dictionary with keys:
                - universe_breadth_score: float | None — ratio of (above - below) /
                  total qualifying symbols, range -1.0 to +1.0. None if insufficient data.
                - breadth_thrust: bool | None — True if fraction above MA >=
                  thrust_threshold. None if insufficient data.
                - symbols_tracked: int — total symbols receiving candle updates.
                - symbols_qualifying: int — symbols with >= min_bars_for_valid candles.
        """
        symbols_tracked = len(self._symbol_closes)
        min_bars = self._config.min_bars_for_valid

        # Count qualifying symbols and their MA relationships
        above_count = 0
        below_count = 0
        qualifying_count = 0

        for closes in self._symbol_closes.values():
            if len(closes) < min_bars:
                continue
            qualifying_count += 1
            current_close = closes[-1]
            ma = statistics.mean(closes)
            if current_close > ma:
                above_count += 1
            elif current_close < ma:
                below_count += 1
            # Exactly equal: neither above nor below

        # Not enough qualifying symbols
        if qualifying_count < self._config.min_symbols:
            return {
                "universe_breadth_score": None,
                "breadth_thrust": None,
                "symbols_tracked": symbols_tracked,
                "symbols_qualifying": qualifying_count,
            }

        universe_breadth_score = (above_count - below_count) / qualifying_count
        breadth_thrust = (above_count / qualifying_count) >= self._config.thrust_threshold

        return {
            "universe_breadth_score": universe_breadth_score,
            "breadth_thrust": breadth_thrust,
            "symbols_tracked": symbols_tracked,
            "symbols_qualifying": qualifying_count,
        }

    def reset(self) -> None:
        """Clear all accumulated state (new trading day)."""
        self._symbol_closes.clear()
