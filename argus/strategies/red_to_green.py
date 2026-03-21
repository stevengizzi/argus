"""Red-to-Green Strategy implementation.

A gap-down reversal strategy that enters long when price tests and holds
a key support level (VWAP, premarket low, prior close) after a gap down.

Entry logic:
1. Stock gaps down between min_gap_down_pct and max_gap_down_pct
2. Price approaches a key support level (VWAP, premarket low, prior close)
3. Price tests the level for min_level_test_bars with volume confirmation
4. Entry on confirmed hold with stop below the level

Operates 9:45 AM – 11:00 AM ET.

Sprint 26, Session 2: Skeleton + state machine.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import time
from enum import StrEnum
from typing import TYPE_CHECKING

from argus.core.clock import Clock
from argus.core.config import RedToGreenConfig
from argus.core.events import CandleEvent, SignalEvent, TickEvent
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
)
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult

if TYPE_CHECKING:
    from argus.analytics.trade_logger import TradeLogger
    from argus.data.service import DataService

logger = logging.getLogger(__name__)


class RedToGreenState(StrEnum):
    """State machine states for Red-to-Green tracking."""

    WATCHING = "watching"  # Initial, waiting for gap confirmation
    GAP_DOWN_CONFIRMED = "gap_down_confirmed"  # Gapped down, looking for key levels
    TESTING_LEVEL = "testing_level"  # Price approaching/testing a key support level
    ENTERED = "entered"  # Position taken (terminal)
    EXHAUSTED = "exhausted"  # Gave up (terminal)


class KeyLevelType(StrEnum):
    """Types of key support levels for Red-to-Green."""

    VWAP = "vwap"
    PREMARKET_LOW = "premarket_low"
    PRIOR_CLOSE = "prior_close"


@dataclass
class RedToGreenSymbolState:
    """Per-symbol intraday state for Red-to-Green tracking.

    Tracks the state machine progression, gap metrics, and level testing
    for a single symbol.
    """

    state: RedToGreenState = RedToGreenState.WATCHING
    gap_pct: float = 0.0
    current_level_type: KeyLevelType | None = None
    current_level_price: float = 0.0
    level_test_bars: int = 0
    level_attempts: int = 0
    premarket_low: float = 0.0
    prior_close: float = 0.0
    exhaustion_reason: str = ""


class RedToGreenStrategy(BaseStrategy):
    """Red-to-Green Strategy.

    Gap-down reversal strategy that enters long when price tests and holds
    a key support level after a gap down.

    State machine:
    - WATCHING: Initial state, waiting for gap confirmation
    - GAP_DOWN_CONFIRMED: Stock gapped down, looking for key levels
    - TESTING_LEVEL: Price approaching/testing a key support level
    - ENTERED: Position taken (terminal)
    - EXHAUSTED: Gave up — gap too large, max attempts, window expired (terminal)

    Entry requires (full implementation in S3):
    1. State is TESTING_LEVEL
    2. Price holds at level for min_level_test_bars
    3. Volume confirmation on hold candle
    4. Chase protection
    5. Time window check
    6. Internal risk limits pass
    """

    def __init__(
        self,
        config: RedToGreenConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the Red-to-Green strategy.

        Args:
            config: RedToGreenConfig with R2G-specific parameters.
            data_service: DataService for VWAP queries.
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        super().__init__(config, clock=clock)
        self._r2g_config = config
        self._data_service = data_service

        # Per-symbol state
        self._symbol_states: dict[str, RedToGreenSymbolState] = {}

        # Parse operating window times
        earliest_str = config.operating_window.earliest_entry
        eh, em = map(int, earliest_str.split(":"))
        self._earliest_entry_time = time(eh, em)

        latest_str = config.operating_window.latest_entry
        lh, lm = map(int, latest_str.split(":"))
        self._latest_entry_time = time(lh, lm)

    # -------------------------------------------------------------------------
    # Symbol State Management
    # -------------------------------------------------------------------------

    def _get_symbol_state(self, symbol: str) -> RedToGreenSymbolState:
        """Get or create the state for a symbol."""
        if symbol not in self._symbol_states:
            self._symbol_states[symbol] = RedToGreenSymbolState()
        return self._symbol_states[symbol]

    # -------------------------------------------------------------------------
    # Core Interface Implementation
    # -------------------------------------------------------------------------

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle and potentially emit a Red-to-Green signal.

        Args:
            event: The CandleEvent to process.

        Returns:
            SignalEvent if entry criteria met, None otherwise.
        """
        symbol = event.symbol

        # Ignore if not in watchlist
        if symbol not in self._watchlist:
            return None

        state = self._get_symbol_state(symbol)

        # Terminal states: no more signals for this symbol today
        if state.state in (RedToGreenState.ENTERED, RedToGreenState.EXHAUSTED):
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"Symbol in terminal state: {state.state}",
            )
            return None

        # Route to state handlers
        if state.state == RedToGreenState.WATCHING:
            new_state = self._handle_watching(symbol, event, state)
            state.state = new_state
            return None

        if state.state == RedToGreenState.GAP_DOWN_CONFIRMED:
            new_state = self._handle_gap_confirmed(symbol, event, state)
            state.state = new_state
            return None

        if state.state == RedToGreenState.TESTING_LEVEL:
            new_state, signal = self._handle_testing_level(symbol, event, state)
            state.state = new_state
            return signal

        return None

    def _handle_watching(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
    ) -> RedToGreenState:
        """Handle WATCHING state — check if gap qualifies.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.

        Returns:
            The new state after evaluation.
        """
        if state.prior_close <= 0:
            return RedToGreenState.WATCHING

        gap_pct = (candle.open - state.prior_close) / state.prior_close

        # Gap must be negative (gap down)
        if gap_pct >= 0:
            self.record_evaluation(
                symbol,
                EvaluationEventType.CONDITION_CHECK,
                EvaluationResult.FAIL,
                f"No gap down: gap_pct={gap_pct * 100:.2f}%",
                metadata={"gap_pct": round(gap_pct, 6)},
            )
            return RedToGreenState.WATCHING

        abs_gap = abs(gap_pct)

        # Gap too large → EXHAUSTED
        if abs_gap > self._r2g_config.max_gap_down_pct:
            state.gap_pct = gap_pct
            state.exhaustion_reason = (
                f"Gap {abs_gap * 100:.2f}% exceeds max "
                f"{self._r2g_config.max_gap_down_pct * 100:.1f}%"
            )
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"State transition: {RedToGreenState.WATCHING} → "
                f"{RedToGreenState.EXHAUSTED}",
                metadata={
                    "from_state": str(RedToGreenState.WATCHING),
                    "to_state": str(RedToGreenState.EXHAUSTED),
                    "trigger": state.exhaustion_reason,
                },
            )
            logger.info(
                "%s: WATCHING → EXHAUSTED (%s)",
                symbol,
                state.exhaustion_reason,
            )
            return RedToGreenState.EXHAUSTED

        # Gap qualifies → GAP_DOWN_CONFIRMED
        if abs_gap >= self._r2g_config.min_gap_down_pct:
            state.gap_pct = gap_pct
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"State transition: {RedToGreenState.WATCHING} → "
                f"{RedToGreenState.GAP_DOWN_CONFIRMED}",
                metadata={
                    "from_state": str(RedToGreenState.WATCHING),
                    "to_state": str(RedToGreenState.GAP_DOWN_CONFIRMED),
                    "trigger": f"gap down {abs_gap * 100:.2f}% confirmed",
                    "gap_pct": round(gap_pct, 6),
                },
            )
            logger.debug(
                "%s: WATCHING → GAP_DOWN_CONFIRMED (gap=%.2f%%)",
                symbol,
                gap_pct * 100,
            )
            return RedToGreenState.GAP_DOWN_CONFIRMED

        # Gap too small — stay watching
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.FAIL,
            f"Gap {abs_gap * 100:.2f}% below min "
            f"{self._r2g_config.min_gap_down_pct * 100:.1f}%",
            metadata={"gap_pct": round(gap_pct, 6)},
        )
        return RedToGreenState.WATCHING

    def _handle_gap_confirmed(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
    ) -> RedToGreenState:
        """Handle GAP_DOWN_CONFIRMED state — identify nearest key level.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.

        Returns:
            The new state after evaluation.
        """
        # Check max level attempts
        if state.level_attempts >= self._r2g_config.max_level_attempts:
            state.exhaustion_reason = (
                f"Max level attempts ({self._r2g_config.max_level_attempts}) reached"
            )
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"State transition: {RedToGreenState.GAP_DOWN_CONFIRMED} → "
                f"{RedToGreenState.EXHAUSTED}",
                metadata={
                    "from_state": str(RedToGreenState.GAP_DOWN_CONFIRMED),
                    "to_state": str(RedToGreenState.EXHAUSTED),
                    "trigger": state.exhaustion_reason,
                },
            )
            logger.info(
                "%s: GAP_DOWN_CONFIRMED → EXHAUSTED (%s)",
                symbol,
                state.exhaustion_reason,
            )
            return RedToGreenState.EXHAUSTED

        # Build list of candidate levels
        levels: list[tuple[KeyLevelType, float]] = []

        if state.prior_close > 0:
            levels.append((KeyLevelType.PRIOR_CLOSE, state.prior_close))
        if state.premarket_low > 0:
            levels.append((KeyLevelType.PREMARKET_LOW, state.premarket_low))

        # VWAP from data service — synchronous check not available in on_candle,
        # so we skip VWAP for now (populated in S3 when data_service is wired)

        if not levels:
            return RedToGreenState.GAP_DOWN_CONFIRMED

        # Find nearest level within proximity threshold
        close = candle.close
        proximity_threshold = self._r2g_config.level_proximity_pct

        nearest_level: tuple[KeyLevelType, float] | None = None
        nearest_distance = float("inf")

        for level_type, level_price in levels:
            if level_price <= 0:
                continue
            distance_pct = abs(close - level_price) / level_price
            if distance_pct < nearest_distance:
                nearest_distance = distance_pct
                nearest_level = (level_type, level_price)

        if nearest_level is not None and nearest_distance <= proximity_threshold:
            state.current_level_type = nearest_level[0]
            state.current_level_price = nearest_level[1]
            state.level_test_bars = 1
            state.level_attempts += 1

            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"State transition: {RedToGreenState.GAP_DOWN_CONFIRMED} → "
                f"{RedToGreenState.TESTING_LEVEL}",
                metadata={
                    "from_state": str(RedToGreenState.GAP_DOWN_CONFIRMED),
                    "to_state": str(RedToGreenState.TESTING_LEVEL),
                    "trigger": (
                        f"price near {nearest_level[0]} "
                        f"({nearest_distance * 100:.3f}% away)"
                    ),
                    "level_type": str(nearest_level[0]),
                    "level_price": nearest_level[1],
                    "attempt": state.level_attempts,
                },
            )
            logger.debug(
                "%s: GAP_DOWN_CONFIRMED → TESTING_LEVEL "
                "(level=%s @ %.2f, distance=%.3f%%)",
                symbol,
                nearest_level[0],
                nearest_level[1],
                nearest_distance * 100,
            )
            return RedToGreenState.TESTING_LEVEL

        return RedToGreenState.GAP_DOWN_CONFIRMED

    def _handle_testing_level(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
    ) -> tuple[RedToGreenState, SignalEvent | None]:
        """Handle TESTING_LEVEL state — check if level holds.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.

        Returns:
            Tuple of (new_state, signal_or_none).
        """
        # TODO: Sprint 26 S3 — full entry logic with volume confirmation,
        # chase protection, and signal generation.
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.INFO,
            f"TESTING_LEVEL stub: level={state.current_level_type} "
            f"@ {state.current_level_price:.2f}, bars={state.level_test_bars}",
            metadata={
                "level_type": str(state.current_level_type),
                "level_price": state.current_level_price,
                "test_bars": state.level_test_bars,
            },
        )
        state.level_test_bars += 1
        return (RedToGreenState.TESTING_LEVEL, None)

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for R2G V1 — uses candles).

        Position management is handled by Order Manager.
        """
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria for Red-to-Green stock selection.

        Returns:
            Basic scanner criteria. Full implementation in S3.
        """
        # TODO: Sprint 26 S3 — refine criteria for gap-down stocks
        uf = self._r2g_config.universe_filter
        return ScannerCriteria(
            min_price=uf.min_price if uf else 5.0,
            max_price=uf.max_price if uf else 200.0,
            min_volume_avg_daily=uf.min_avg_volume if uf else 500_000,
            max_results=20,
        )

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate position size — returns 0 (Quality Engine handles sizing).

        Args:
            entry_price: Expected entry price.
            stop_price: Stop loss price.

        Returns:
            Always 0 — sizing delegated to Dynamic Position Sizer.
        """
        return 0

    def get_exit_rules(self) -> ExitRules:
        """Return Red-to-Green exit rules (T1 50%, T2 50%, time stop).

        Returns:
            ExitRules with R2G-specific targets and time stop.
        """
        # TODO: Sprint 26 S3 — finalize exit rules
        return ExitRules(
            stop_type="fixed",
            stop_price_func="level_low",
            targets=[
                ProfitTarget(
                    r_multiple=self._r2g_config.target_1_r,
                    position_pct=0.5,
                ),
                ProfitTarget(
                    r_multiple=self._r2g_config.target_2_r,
                    position_pct=0.5,
                ),
            ],
            time_stop_minutes=self._r2g_config.time_stop_minutes,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions for Red-to-Green activation.

        Returns:
            MarketConditionsFilter with allowed regimes.
        """
        # TODO: Sprint 26 S3 — refine regime filters
        return MarketConditionsFilter(
            allowed_regimes=["bearish_trending", "range_bound", "high_volatility"],
            max_vix=35.0,
        )

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._symbol_states.clear()
        logger.debug(
            "%s: Red-to-Green strategy daily state reset", self.strategy_id
        )

    async def reconstruct_state(self, trade_logger: TradeLogger) -> None:
        """Reconstruct intraday state from database after mid-day restart.

        Args:
            trade_logger: TradeLogger instance for database queries.
        """
        # TODO: Sprint 26 S3 — full state reconstruction
        await super().reconstruct_state(trade_logger)

    def set_data_service(self, data_service: DataService) -> None:
        """Set the data service for indicator queries.

        Args:
            data_service: The DataService instance.
        """
        self._data_service = data_service
