"""Generic strategy wrapper for PatternModule implementations.

PatternBasedStrategy handles all BaseStrategy contract requirements
(operating window, state management, signal generation, telemetry)
while delegating pattern detection to the wrapped PatternModule.

This keeps pattern modules pure — they detect and score patterns,
nothing more. The wrapper handles everything else.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import StrategyConfig
from argus.core.events import CandleEvent, Side, SignalEvent, TickEvent
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
)
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.data.service import DataService

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")


def candle_event_to_bar(event: CandleEvent) -> CandleBar:
    """Convert a CandleEvent to a CandleBar for pattern detection.

    Args:
        event: The CandleEvent from the Event Bus.

    Returns:
        CandleBar with the same OHLCV data.
    """
    return CandleBar(
        timestamp=event.timestamp,
        open=event.open,
        high=event.high,
        low=event.low,
        close=event.close,
        volume=float(event.volume),
    )


class PatternBasedStrategy(BaseStrategy):
    """Generic strategy wrapper for PatternModule implementations.

    Handles all BaseStrategy contract requirements:
    - Operating window enforcement
    - Per-symbol candle window management
    - Signal generation from PatternDetection
    - Evaluation telemetry
    - Daily state management

    Pattern detection is delegated to the wrapped PatternModule.
    """

    def __init__(
        self,
        pattern: PatternModule,
        config: StrategyConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the pattern-based strategy wrapper.

        Args:
            pattern: The PatternModule to wrap.
            config: Strategy configuration loaded from YAML.
            data_service: DataService for indicator queries.
            clock: Clock for time access. Defaults to SystemClock().
        """
        super().__init__(config, clock=clock)
        self._pattern = pattern
        self._data_service = data_service
        self._candle_windows: dict[str, deque[CandleBar]] = {}
        self._last_score: float = 50.0
        self._last_context: dict[str, object] = {}

        # Parse operating window times
        earliest_str = config.operating_window.earliest_entry
        eh, em = map(int, earliest_str.split(":"))
        self._earliest_entry_time = time(eh, em)

        latest_str = config.operating_window.latest_entry
        lh, lm = map(int, latest_str.split(":"))
        self._latest_entry_time = time(lh, lm)

    def _get_candle_window(self, symbol: str) -> deque[CandleBar]:
        """Get or create the candle window deque for a symbol.

        Args:
            symbol: The ticker symbol.

        Returns:
            A deque with maxlen=pattern.lookback_bars.
        """
        if symbol not in self._candle_windows:
            self._candle_windows[symbol] = deque(maxlen=self._pattern.lookback_bars)
        return self._candle_windows[symbol]

    def _is_in_entry_window(self, event: CandleEvent) -> bool:
        """Check if candle is within the operating window.

        Args:
            event: The candle event to check.

        Returns:
            True if within the entry window.
        """
        candle_time = event.timestamp.astimezone(ET).time()
        return self._earliest_entry_time <= candle_time < self._latest_entry_time

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle and potentially emit a pattern-based signal.

        Args:
            event: The CandleEvent to process.

        Returns:
            SignalEvent if pattern detected and all conditions met, None otherwise.
        """
        symbol = event.symbol

        # Check watchlist
        if symbol not in self._watchlist:
            return None

        # Check operating window
        if not self._is_in_entry_window(event):
            self.record_evaluation(
                symbol,
                EvaluationEventType.TIME_WINDOW_CHECK,
                EvaluationResult.FAIL,
                f"Outside operating window "
                f"({self._earliest_entry_time}–{self._latest_entry_time})",
            )
            return None

        # Check internal risk limits
        if not self.check_internal_risk_limits():
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Internal risk limits hit",
            )
            return None

        # Append candle to per-symbol window
        bar = candle_event_to_bar(event)
        window = self._get_candle_window(symbol)
        window.append(bar)

        # Need full lookback before detecting
        if len(window) < self._pattern.lookback_bars:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                f"Insufficient history ({len(window)}/{self._pattern.lookback_bars})",
            )
            return None

        # Build indicators from data service
        indicators: dict[str, float] = {}
        if self._data_service is not None:
            for name in ("vwap", "atr", "rvol"):
                value = await self._data_service.get_indicator(symbol, name)
                if value is not None:
                    indicators[name] = value

        # Run pattern detection
        detection = self._pattern.detect(list(window), indicators)

        if detection is None:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                f"No {self._pattern.name} pattern detected",
            )
            return None

        # Score the detection
        score = self._pattern.score(detection)
        score = max(0.0, min(100.0, score))
        self._last_score = score
        self._last_context = dict(detection.metadata)

        # Build target prices
        target_prices = detection.target_prices
        if not target_prices:
            risk_per_share = detection.entry_price - detection.stop_price
            if risk_per_share > 0:
                t1_r = getattr(self._config, "target_1_r", 1.0)
                t2_r = getattr(self._config, "target_2_r", 2.0)
                t1 = detection.entry_price + risk_per_share * t1_r
                t2 = detection.entry_price + risk_per_share * t2_r
                target_prices = (t1, t2)

        # Build time stop
        time_stop_seconds: int | None = None
        time_stop_minutes = getattr(self._config, "time_stop_minutes", None)
        if time_stop_minutes is not None:
            time_stop_seconds = int(time_stop_minutes) * 60

        # Build signal
        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=detection.entry_price,
            stop_price=detection.stop_price,
            target_prices=target_prices,
            share_count=0,
            rationale=(
                f"{self._pattern.name}: {symbol} detected at "
                f"{detection.entry_price:.2f} "
                f"(confidence={detection.confidence:.1f}, "
                f"score={score:.1f})"
            ),
            time_stop_seconds=time_stop_seconds,
            pattern_strength=score,
            signal_context=self._last_context,
        )

        self.record_evaluation(
            symbol,
            EvaluationEventType.SIGNAL_GENERATED,
            EvaluationResult.PASS,
            f"{self._pattern.name} signal: {symbol} entry at "
            f"{detection.entry_price:.2f}, score={score:.1f}",
            metadata={
                "entry": detection.entry_price,
                "stop": detection.stop_price,
                "pattern_strength": round(score, 2),
                "confidence": round(detection.confidence, 2),
            },
        )

        logger.info(
            "%s: %s pattern signal - entry=%.2f, stop=%.2f, score=%.1f",
            symbol,
            self._pattern.name,
            detection.entry_price,
            detection.stop_price,
            score,
        )

        return signal

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for pattern strategies V1).

        Position management is handled by Order Manager.
        """

    def _calculate_pattern_strength(self) -> tuple[float, dict[str, object]]:
        """Return cached score and context from the last on_candle detection.

        Returns:
            Tuple of (pattern_strength, signal_context).
        """
        return self._last_score, self._last_context

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria from config defaults.

        Returns:
            ScannerCriteria with basic price and volume filters.
        """
        uf = self._config.universe_filter
        return ScannerCriteria(
            min_price=uf.min_price if uf and uf.min_price else 10.0,
            max_price=uf.max_price if uf and uf.max_price else 200.0,
            min_volume_avg_daily=uf.min_avg_volume if uf and uf.min_avg_volume else 1_000_000,
            max_results=20,
        )

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Return 0 — Quality Engine handles position sizing (DEC-330).

        Args:
            entry_price: Expected entry price.
            stop_price: Stop loss price.

        Returns:
            Always 0.
        """
        return 0

    def get_exit_rules(self) -> ExitRules:
        """Return exit rules built from config.

        Returns:
            ExitRules with fixed stop, R-multiple targets, and time stop.
        """
        t1_r = getattr(self._config, "target_1_r", 1.0)
        t2_r = getattr(self._config, "target_2_r", 2.0)
        time_stop = getattr(self._config, "time_stop_minutes", None)

        return ExitRules(
            stop_type="fixed",
            stop_price_func="pattern_stop",
            targets=[
                ProfitTarget(r_multiple=t1_r, position_pct=0.5),
                ProfitTarget(r_multiple=t2_r, position_pct=0.5),
            ],
            time_stop_minutes=time_stop,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions filter with sensible defaults.

        Returns:
            MarketConditionsFilter allowing bullish and range-bound regimes.
        """
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "bearish_trending", "range_bound"],
            max_vix=35.0,
        )

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._candle_windows.clear()
        self._last_score = 50.0
        self._last_context = {}
        logger.debug(
            "%s: PatternBasedStrategy daily state reset", self.strategy_id
        )

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from database after mid-day restart.

        Args:
            trade_logger: TradeLogger instance for database queries.
        """
        await super().reconstruct_state(trade_logger)
