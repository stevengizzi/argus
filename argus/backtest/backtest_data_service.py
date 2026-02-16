"""Backtest data service for the Replay Harness.

Step-by-step DataService that the ReplayHarness controls directly.
Implements the DataService ABC so strategies can call get_indicator()
and get_current_price() as normal.

Indicator computation reuses the same logic as ReplayDataService
(VWAP, ATR(14), SMA(9), SMA(20), SMA(50), RVOL).

Decision reference: DEC-055 (BacktestDataService - Step-Driven DataService)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime

import pandas as pd

from argus.core.event_bus import EventBus
from argus.core.events import CandleEvent, IndicatorEvent, TickEvent
from argus.data.replay_data_service import IndicatorState
from argus.data.service import DataService

logger = logging.getLogger(__name__)


class BacktestDataService(DataService):
    """DataService for the Replay Harness. Driven step-by-step.

    The harness calls feed_bar() for each 1m bar. This updates indicators,
    publishes CandleEvent and IndicatorEvents to the EventBus, and updates
    the price/indicator caches that strategies query via get_current_price()
    and get_indicator().

    The harness calls publish_tick() for each synthetic tick. This publishes
    a TickEvent and updates the price cache.

    Args:
        event_bus: EventBus for publishing events.
    """

    def __init__(self, event_bus: EventBus) -> None:
        """Initialize the backtest data service.

        Args:
            event_bus: EventBus for publishing events.
        """
        self._event_bus = event_bus

        # Price cache: symbol -> last known price
        self._price_cache: dict[str, float] = {}

        # Indicator state per symbol - reuse from ReplayDataService
        self._indicator_state: dict[str, IndicatorState] = defaultdict(IndicatorState)

        # Indicator cache: (symbol, indicator_name) -> value
        self._indicator_cache: dict[tuple[str, str], float] = {}

    # --- DataService ABC implementation ---

    async def start(self, symbols: list[str], timeframes: list[str]) -> None:
        """No-op. The harness drives data through feed_bar().

        Args:
            symbols: List of symbols to track.
            timeframes: List of timeframes (only 1m supported).
        """
        logger.info(
            "BacktestDataService initialized for %d symbols", len(symbols)
        )

    async def stop(self) -> None:
        """No-op. Nothing to clean up."""
        pass

    async def get_current_price(self, symbol: str) -> float | None:
        """Return last known price from feed_bar() or publish_tick().

        Args:
            symbol: The ticker symbol.

        Returns:
            Last known price or None if not available.
        """
        return self._price_cache.get(symbol.upper())

    async def get_indicator(self, symbol: str, indicator: str) -> float | None:
        """Return latest indicator value computed during feed_bar().

        Args:
            symbol: The ticker symbol.
            indicator: Indicator name (vwap, atr_14, sma_9, sma_20, sma_50, rvol).

        Returns:
            Indicator value or None if not computed yet.
        """
        return self._indicator_cache.get((symbol.upper(), indicator.lower()))

    async def get_historical_candles(
        self, symbol: str, timeframe: str, start: datetime, end: datetime
    ) -> pd.DataFrame:
        """Not used in backtest mode. Raise NotImplementedError.

        Args:
            symbol: The ticker symbol.
            timeframe: Candle timeframe.
            start: Start datetime.
            end: End datetime.

        Raises:
            NotImplementedError: Always - use Parquet files directly.
        """
        raise NotImplementedError(
            "BacktestDataService does not support historical candle queries. "
            "Use Parquet files directly."
        )

    # --- Harness-controlled methods ---

    async def feed_bar(
        self,
        symbol: str,
        timestamp: datetime,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timeframe: str = "1m",
    ) -> None:
        """Feed a single bar into the system.

        1. Update indicator state for this symbol (VWAP, ATR, SMA, RVOL)
        2. Update price cache
        3. Publish CandleEvent to EventBus
        4. Publish IndicatorEvents for all updated indicators

        Args:
            symbol: Ticker symbol.
            timestamp: Bar timestamp.
            open_: Bar open price.
            high: Bar high price.
            low: Bar low price.
            close: Bar close price.
            volume: Bar volume.
            timeframe: Bar timeframe (default: "1m").
        """
        symbol = symbol.upper()

        # Update price cache
        self._price_cache[symbol] = close

        # Publish CandleEvent
        candle = CandleEvent(
            symbol=symbol,
            timeframe=timeframe,
            open=open_,
            high=high,
            low=low,
            close=close,
            volume=volume,
            timestamp=timestamp,
        )
        await self._event_bus.publish(candle)

        # Compute and publish indicators
        await self._update_indicators(symbol, candle)

    async def _update_indicators(self, symbol: str, candle: CandleEvent) -> None:
        """Compute indicators and publish IndicatorEvents.

        Mirrors the logic in ReplayDataService._update_indicators exactly.

        Args:
            symbol: The ticker symbol.
            candle: The candle event with OHLCV data.
        """
        state = self._indicator_state[symbol]

        # Get date string for VWAP reset
        candle_date = candle.timestamp.strftime("%Y-%m-%d")

        # Reset VWAP on new day
        if state.vwap_date != candle_date:
            state.vwap_cumulative_tp_volume = 0.0
            state.vwap_cumulative_volume = 0
            state.vwap_date = candle_date
            # Reset RVOL baseline on new day too
            state.rvol_volume_samples = []
            state.rvol_baseline_volume = None

        # --- VWAP ---
        typical_price = (candle.high + candle.low + candle.close) / 3
        state.vwap_cumulative_tp_volume += typical_price * candle.volume
        state.vwap_cumulative_volume += candle.volume

        if state.vwap_cumulative_volume > 0:
            state.vwap = state.vwap_cumulative_tp_volume / state.vwap_cumulative_volume
            self._indicator_cache[(symbol, "vwap")] = state.vwap
            await self._publish_indicator(symbol, "vwap", state.vwap)

        # --- ATR(14) ---
        if state.atr_prev_close is not None:
            true_range = max(
                candle.high - candle.low,
                abs(candle.high - state.atr_prev_close),
                abs(candle.low - state.atr_prev_close),
            )
            state.atr_true_ranges.append(true_range)

            if len(state.atr_true_ranges) >= 14:
                # Use Wilder's smoothing (exponential moving average)
                if state.atr_14 is None:
                    # Initial ATR is simple average
                    state.atr_14 = sum(state.atr_true_ranges[-14:]) / 14
                else:
                    # Subsequent ATR uses smoothing: ATR = ((ATR_prev * 13) + TR) / 14
                    state.atr_14 = (state.atr_14 * 13 + true_range) / 14

                self._indicator_cache[(symbol, "atr_14")] = state.atr_14
                await self._publish_indicator(symbol, "atr_14", state.atr_14)

        state.atr_prev_close = candle.close

        # --- SMA (9, 20, 50) ---
        state.sma_closes.append(candle.close)

        if len(state.sma_closes) >= 9:
            state.sma_9 = sum(state.sma_closes[-9:]) / 9
            self._indicator_cache[(symbol, "sma_9")] = state.sma_9
            await self._publish_indicator(symbol, "sma_9", state.sma_9)

        if len(state.sma_closes) >= 20:
            state.sma_20 = sum(state.sma_closes[-20:]) / 20
            self._indicator_cache[(symbol, "sma_20")] = state.sma_20
            await self._publish_indicator(symbol, "sma_20", state.sma_20)

        if len(state.sma_closes) >= 50:
            state.sma_50 = sum(state.sma_closes[-50:]) / 50
            self._indicator_cache[(symbol, "sma_50")] = state.sma_50
            await self._publish_indicator(symbol, "sma_50", state.sma_50)

        # --- RVOL (relative volume) ---
        # Use first 20 candles as baseline
        state.rvol_volume_samples.append(candle.volume)
        if len(state.rvol_volume_samples) >= 20:
            if state.rvol_baseline_volume is None:
                # Set baseline from first 20 candles
                state.rvol_baseline_volume = sum(state.rvol_volume_samples[:20]) / 20

            if state.rvol_baseline_volume > 0:
                # RVOL = current cumulative volume / expected cumulative volume
                cumulative_volume = sum(state.rvol_volume_samples)
                expected_volume = state.rvol_baseline_volume * len(
                    state.rvol_volume_samples
                )
                state.rvol = cumulative_volume / expected_volume
                self._indicator_cache[(symbol, "rvol")] = state.rvol
                await self._publish_indicator(symbol, "rvol", state.rvol)

    async def _publish_indicator(
        self, symbol: str, indicator: str, value: float
    ) -> None:
        """Publish an IndicatorEvent to the Event Bus.

        Args:
            symbol: The ticker symbol.
            indicator: Indicator name.
            value: Indicator value.
        """
        event = IndicatorEvent(
            symbol=symbol,
            indicator_name=indicator,
            value=value,
        )
        await self._event_bus.publish(event)

    async def publish_tick(
        self, symbol: str, price: float, volume: int, timestamp: datetime
    ) -> None:
        """Publish a synthetic tick to the EventBus.

        Called by the harness during tick synthesis. Updates price cache
        and publishes TickEvent.

        Args:
            symbol: Ticker symbol.
            price: Tick price.
            volume: Tick volume.
            timestamp: Tick timestamp.
        """
        symbol = symbol.upper()
        self._price_cache[symbol] = price

        tick_event = TickEvent(
            symbol=symbol,
            price=price,
            volume=volume,
            timestamp=timestamp,
        )
        await self._event_bus.publish(tick_event)

    def reset_daily_state(self) -> None:
        """Reset indicator state that is daily-scoped.

        Called by the harness at the start of each trading day.
        - VWAP resets (cumulative within day)
        - ATR, SMA carry over (rolling windows)
        - RVOL resets (relative to today's baseline)
        """
        for symbol, state in self._indicator_state.items():
            # Reset VWAP
            state.vwap_cumulative_tp_volume = 0.0
            state.vwap_cumulative_volume = 0
            state.vwap_date = ""
            state.vwap = None

            # Reset RVOL
            state.rvol_volume_samples = []
            state.rvol_baseline_volume = None
            state.rvol = None

            # Clear VWAP and RVOL from cache
            self._indicator_cache.pop((symbol, "vwap"), None)
            self._indicator_cache.pop((symbol, "rvol"), None)

            # ATR and SMA carry over - do not reset

        logger.debug("BacktestDataService daily state reset")
