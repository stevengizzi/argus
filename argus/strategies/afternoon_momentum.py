"""Afternoon Momentum Strategy implementation.

A consolidation breakout strategy that identifies stocks consolidating during
midday (12:00–2:00 PM) and enters on breakouts after 2:00 PM ET.

Entry logic:
1. During consolidation window (12:00–2:00 PM), track midday range
2. Confirm consolidation: range < consolidation_atr_ratio * ATR-14
3. After 2:00 PM, enter on close above consolidation_high with volume

Operates 2:00 PM – 3:30 PM ET (entry window), force close at 3:45 PM.

DEC-152: Afternoon Momentum strategy — consolidation breakout entry.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import AfternoonMomentumConfig
from argus.core.events import CandleEvent, Side, SignalEvent, TickEvent
from argus.models.strategy import (
    ExitRules,
    MarketConditionsFilter,
    ProfitTarget,
    ScannerCriteria,
)
from argus.strategies.base_strategy import BaseStrategy
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult

if TYPE_CHECKING:
    from argus.data.service import DataService

logger = logging.getLogger(__name__)

# Eastern Time zone for market hours comparisons
ET = ZoneInfo("America/New_York")


class ConsolidationState(StrEnum):
    """State machine states for Afternoon Momentum tracking."""

    WATCHING = "watching"  # Before consolidation_start_time (12:00 PM)
    ACCUMULATING = "accumulating"  # Tracking midday range, not yet consolidated
    CONSOLIDATED = "consolidated"  # Range confirmed tight, watching for breakout
    ENTERED = "entered"  # Position taken, terminal state
    REJECTED = "rejected"  # Midday range too wide, terminal state


@dataclass
class ConsolidationSymbolState:
    """Per-symbol intraday state for Afternoon Momentum tracking.

    Tracks the state machine progression and consolidation metrics for a single symbol.
    """

    # State machine
    state: ConsolidationState = ConsolidationState.WATCHING

    # Consolidation range tracking (populated during ACCUMULATING and CONSOLIDATED)
    midday_high: float | None = None
    midday_low: float | None = None
    consolidation_bars: int = 0

    # Volume tracking (all bars seen for this symbol)
    recent_volumes: list[int] = field(default_factory=list)

    # Position tracking
    position_active: bool = False


class AfternoonMomentumStrategy(BaseStrategy):
    """Afternoon Momentum Strategy.

    Consolidation breakout strategy that identifies stocks consolidating during
    midday and enters on breakouts in the afternoon session.

    State machine:
    - WATCHING: Before consolidation_start_time (12:00 PM). Ignore all candles.
    - ACCUMULATING: 12:00 PM onward. Track midday_high/midday_low. Check
      consolidation criteria each bar.
    - CONSOLIDATED: Range confirmed tight. Watch for breakout after 2:00 PM.
      Continues updating range (can transition to REJECTED if range widens).
    - ENTERED: Position taken (terminal).
    - REJECTED: Midday range too wide (terminal).

    Entry requires:
    1. State is CONSOLIDATED
    2. Time is 2:00 PM – 3:30 PM
    3. Candle close > consolidation_high
    4. Volume >= multiplier × avg
    5. Chase protection (not too far above consolidation_high)
    6. Risk per share > 0 (valid stop placement)
    7. Internal risk limits pass
    8. Position count limit not exceeded
    """

    def __init__(
        self,
        config: AfternoonMomentumConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the Afternoon Momentum strategy.

        Args:
            config: AfternoonMomentumConfig with strategy-specific parameters.
            data_service: DataService for ATR queries.
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        super().__init__(config, clock=clock)
        self._pm_config = config
        self._data_service = data_service

        # Per-symbol state
        self._symbol_state: dict[str, ConsolidationSymbolState] = {}

        # Observability: track window logging for the day
        self._logged_window_opened: bool = False
        self._logged_window_closed: bool = False
        self._signals_generated_today: int = 0

        # Parse consolidation start time
        cons_start_str = config.consolidation_start_time
        csh, csm = map(int, cons_start_str.split(":"))
        self._consolidation_start_time = time(csh, csm)

        # Parse operating window times
        earliest_str = config.operating_window.earliest_entry
        eh, em = map(int, earliest_str.split(":"))
        self._earliest_entry_time = time(eh, em)

        latest_str = config.operating_window.latest_entry
        lh, lm = map(int, latest_str.split(":"))
        self._latest_entry_time = time(lh, lm)

        # Parse force_close_time once (used in time stop calculation)
        fc_str = config.force_close_time
        fch, fcm = map(int, fc_str.split(":"))
        self._force_close_time = time(fch, fcm)

    # -------------------------------------------------------------------------
    # Symbol State Management
    # -------------------------------------------------------------------------

    def _get_symbol_state(self, symbol: str) -> ConsolidationSymbolState:
        """Get or create the state for a symbol."""
        if symbol not in self._symbol_state:
            self._symbol_state[symbol] = ConsolidationSymbolState()
        return self._symbol_state[symbol]

    # -------------------------------------------------------------------------
    # Time Calculations
    # -------------------------------------------------------------------------

    def _get_candle_time(self, candle: CandleEvent) -> time:
        """Extract Eastern Time from candle timestamp.

        Candle timestamps are stored in UTC (DEC-049). This method converts
        to Eastern Time before extracting the time component for comparison
        against market hours constants (which are defined in ET).
        """
        return candle.timestamp.astimezone(ET).time()

    def _is_in_entry_window(self, candle: CandleEvent) -> bool:
        """Check if candle is within the entry time window (2:00–3:30 PM)."""
        candle_time = self._get_candle_time(candle)
        return self._earliest_entry_time <= candle_time < self._latest_entry_time

    def _is_in_consolidation_window(self, candle: CandleEvent) -> bool:
        """Check if candle is in the consolidation tracking window (12:00 PM+)."""
        candle_time = self._get_candle_time(candle)
        return candle_time >= self._consolidation_start_time

    def _compute_effective_time_stop(self, candle: CandleEvent) -> int:
        """Compute the effective time stop in seconds.

        Uses the minimum of:
        - Configured max_hold_minutes
        - Time until force_close_time

        Args:
            candle: The entry candle (used for current time).

        Returns:
            Time stop in seconds.
        """
        configured_seconds = self._pm_config.max_hold_minutes * 60

        candle_dt = candle.timestamp.astimezone(ET)
        force_close_dt = candle_dt.replace(
            hour=self._force_close_time.hour,
            minute=self._force_close_time.minute,
            second=0,
            microsecond=0,
        )

        seconds_until_close = max(0, int((force_close_dt - candle_dt).total_seconds()))

        return min(configured_seconds, seconds_until_close)

    # -------------------------------------------------------------------------
    # Core Interface Implementation
    # -------------------------------------------------------------------------

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle and potentially emit an afternoon breakout signal.

        Args:
            event: The CandleEvent to process.

        Returns:
            SignalEvent if breakout criteria met, None otherwise.
        """
        symbol = event.symbol

        # Ignore if not in watchlist
        if symbol not in self._watchlist:
            return None

        # DEF-138 window summary tracking (FIX-19 P1-B-M02)
        self._track_symbol_evaluated()
        candle_time_et = event.timestamp.astimezone(ET).time()
        self._maybe_log_window_summary(candle_time_et)

        # Observability: Log window open/close status
        self._log_window_status(event)

        state = self._get_symbol_state(symbol)

        # Track volume for all bars
        state.recent_volumes.append(event.volume)

        # Terminal states: no more signals for this symbol today
        if state.state in (ConsolidationState.ENTERED, ConsolidationState.REJECTED):
            return None

        # Time window check — outside operating window (entry window)
        if not self._is_in_entry_window(event) and not self._is_in_consolidation_window(event):
            self.record_evaluation(
                symbol,
                EvaluationEventType.TIME_WINDOW_CHECK,
                EvaluationResult.FAIL,
                "Outside Afternoon Momentum operating window",
            )

        # Get ATR from data service
        atr: float | None = None
        if self._data_service is not None:
            atr = await self._data_service.get_indicator(symbol, "atr_14")

        if atr is None or atr <= 0:
            # No ATR available yet, stay in current state
            return None

        # State machine transitions
        signal = await self._process_state_machine(symbol, event, state, atr)
        if signal is not None:
            self._track_signal_generated()
        return signal

    def _log_window_status(self, candle: CandleEvent) -> None:
        """Log window open/close status for observability.

        Logs once per day when the entry window opens and closes.
        """
        candle_time = self._get_candle_time(candle)

        # Log window opened (first candle in entry window)
        if not self._logged_window_opened and candle_time >= self._earliest_entry_time:
            # Count consolidated symbols
            consolidated = sum(
                1 for s in self._symbol_state.values()
                if s.state == ConsolidationState.CONSOLIDATED
            )
            logger.info(
                "Afternoon Momentum: Window opened. "
                "Monitoring %d symbols for consolidation patterns. "
                "%d symbols consolidated.",
                len(self._watchlist),
                consolidated,
            )
            self._logged_window_opened = True

        # Log window closed (first candle past entry window)
        if (
            not self._logged_window_closed
            and self._logged_window_opened
            and candle_time >= self._latest_entry_time
        ):
            # Compile summary
            consolidated = sum(
                1 for s in self._symbol_state.values()
                if s.state == ConsolidationState.CONSOLIDATED
            )
            entered = sum(
                1 for s in self._symbol_state.values()
                if s.state == ConsolidationState.ENTERED
            )
            rejected = sum(
                1 for s in self._symbol_state.values()
                if s.state == ConsolidationState.REJECTED
            )
            logger.info(
                "Afternoon Momentum: Window closed. "
                "Evaluated %d symbols. "
                "Consolidated: %d. Entered: %d. Rejected: %d. Signals: %d.",
                len(self._symbol_state),
                consolidated,
                entered,
                rejected,
                self._signals_generated_today,
            )
            self._logged_window_closed = True

    async def _process_state_machine(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        atr: float,
    ) -> SignalEvent | None:
        """Process the state machine for a symbol.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.
            atr: The current ATR-14 value.

        Returns:
            SignalEvent if entry conditions are met, None otherwise.
        """
        if state.state == ConsolidationState.WATCHING:
            return self._process_watching(symbol, candle, state)

        if state.state == ConsolidationState.ACCUMULATING:
            return self._process_accumulating(symbol, candle, state, atr)

        if state.state == ConsolidationState.CONSOLIDATED:
            return await self._process_consolidated(symbol, candle, state, atr)

        return None

    def _process_watching(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
    ) -> SignalEvent | None:
        """Process a candle while in WATCHING state.

        Transitions to ACCUMULATING when consolidation window starts (12:00 PM).
        """
        if self._is_in_consolidation_window(candle):
            state.state = ConsolidationState.ACCUMULATING
            state.midday_high = candle.high
            state.midday_low = candle.low
            state.consolidation_bars = 1
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                (
                    f"State transition: {ConsolidationState.WATCHING} → "
                    f"{ConsolidationState.ACCUMULATING}"
                ),
                metadata={
                    "from_state": str(ConsolidationState.WATCHING),
                    "to_state": str(ConsolidationState.ACCUMULATING),
                    "trigger": "consolidation window started",
                },
            )
            logger.debug(
                "%s: WATCHING -> ACCUMULATING at %s (high=%.2f, low=%.2f)",
                symbol,
                self._get_candle_time(candle),
                candle.high,
                candle.low,
            )
        return None

    def _process_accumulating(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        atr: float,
    ) -> SignalEvent | None:
        """Process a candle while in ACCUMULATING state.

        Updates midday range and checks for consolidation criteria.
        Transitions to CONSOLIDATED or REJECTED based on range/ATR ratio.
        """
        # Update range tracking
        if state.midday_high is None:
            state.midday_high = candle.high
        else:
            state.midday_high = max(state.midday_high, candle.high)

        if state.midday_low is None:
            state.midday_low = candle.low
        else:
            state.midday_low = min(state.midday_low, candle.low)

        state.consolidation_bars += 1

        # Calculate consolidation ratio
        midday_range = state.midday_high - state.midday_low
        consolidation_ratio = midday_range / atr

        # Emit consolidation tracking event
        self.record_evaluation(
            symbol,
            EvaluationEventType.STATE_TRANSITION,
            EvaluationResult.INFO,
            (
                f"Consolidation tracking: {state.consolidation_bars} candles, "
                f"range={midday_range:.2f}"
            ),
            metadata={
                "consolidation_bars": state.consolidation_bars,
                "midday_range": round(midday_range, 4),
                "consolidation_ratio": round(consolidation_ratio, 4),
            },
        )

        # Check if range is too wide -> REJECTED
        if consolidation_ratio > self._pm_config.max_consolidation_atr_ratio:
            state.state = ConsolidationState.REJECTED
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                (
                    f"State transition: {ConsolidationState.ACCUMULATING} → "
                    f"{ConsolidationState.REJECTED}"
                ),
                metadata={
                    "from_state": str(ConsolidationState.ACCUMULATING),
                    "to_state": str(ConsolidationState.REJECTED),
                    "trigger": "consolidation range too wide",
                },
            )
            logger.info(
                "%s: ACCUMULATING -> REJECTED (ratio=%.2f > max=%.2f, range=%.2f, atr=%.2f)",
                symbol,
                consolidation_ratio,
                self._pm_config.max_consolidation_atr_ratio,
                midday_range,
                atr,
            )
            return None

        # Check if consolidation confirmed
        if (
            consolidation_ratio < self._pm_config.consolidation_atr_ratio
            and state.consolidation_bars >= self._pm_config.min_consolidation_bars
        ):
            state.state = ConsolidationState.CONSOLIDATED
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.PASS,
                "Consolidation established",
                metadata={
                    "from_state": str(ConsolidationState.ACCUMULATING),
                    "to_state": str(ConsolidationState.CONSOLIDATED),
                    "trigger": "range confirmed tight",
                    "consolidation_bars": state.consolidation_bars,
                    "consolidation_ratio": round(consolidation_ratio, 4),
                },
            )
            logger.info(
                "Afternoon Momentum: %s consolidation detected "
                "(%d bars, range/ATR %.2f) — watching for breakout",
                symbol,
                state.consolidation_bars,
                consolidation_ratio,
            )

        return None

    async def _process_consolidated(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        atr: float,
    ) -> SignalEvent | None:
        """Process a candle while in CONSOLIDATED state.

        Continues updating range (can transition to REJECTED if range widens).
        Checks for breakout entry after 2:00 PM.
        """
        # Save consolidation high BEFORE updating with this bar
        # The breakout check uses the PRIOR consolidation high
        consolidation_high_before = state.midday_high

        # Continue updating range even in CONSOLIDATED state
        if state.midday_high is None:
            state.midday_high = candle.high
        else:
            state.midday_high = max(state.midday_high, candle.high)

        if state.midday_low is None:
            state.midday_low = candle.low
        else:
            state.midday_low = min(state.midday_low, candle.low)

        state.consolidation_bars += 1

        # Re-check consolidation ratio (range can widen and invalidate)
        midday_range = state.midday_high - state.midday_low
        consolidation_ratio = midday_range / atr

        if consolidation_ratio > self._pm_config.max_consolidation_atr_ratio:
            state.state = ConsolidationState.REJECTED
            logger.info(
                "%s: CONSOLIDATED -> REJECTED (ratio=%.2f > max=%.2f after range widened)",
                symbol,
                consolidation_ratio,
                self._pm_config.max_consolidation_atr_ratio,
            )
            return None

        # Check breakout entry (only after entry window starts)
        if not self._is_in_entry_window(candle):
            # Not yet in entry window, keep watching
            return None

        # Check for breakout: close > consolidation_high (value BEFORE this bar)
        if consolidation_high_before is not None and candle.close > consolidation_high_before:
            return await self._check_breakout_entry(
                symbol, candle, state, consolidation_high_before, atr
            )

        return None

    async def _check_breakout_entry(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        consolidation_high: float,
        atr: float,
    ) -> SignalEvent | None:
        """Check if breakout entry conditions are met.

        Args:
            symbol: The symbol being processed.
            candle: The breakout candle.
            state: The symbol's state.
            consolidation_high: The consolidation high BEFORE this bar (for chase check).
            atr: The current ATR-14 value (passed through for pattern strength scoring).

        Returns:
            SignalEvent if all conditions pass, None otherwise.
        """
        close = candle.close

        if state.midday_low is None:
            return None

        conditions_passed: list[str] = []
        failed_condition: str | None = None

        # Condition 1/8: Price above consolidation high
        price_above = close > consolidation_high
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if price_above else EvaluationResult.FAIL,
            f"Condition 1/8: Price above consolidation high — "
            f"close={close:.2f} vs high={consolidation_high:.2f}",
            metadata={
                "condition_name": "price_above_consolidation_high",
                "value": close,
                "threshold": consolidation_high,
                "passed": price_above,
            },
        )
        if price_above:
            conditions_passed.append("price_above_consolidation_high")
        elif failed_condition is None:
            failed_condition = "price_above_consolidation_high"
        # Note: caller already verified close > consolidation_high, so this always passes

        # Condition 2/8: Volume confirmation
        avg_volume = (
            sum(state.recent_volumes) / len(state.recent_volumes)
            if state.recent_volumes
            else float(candle.volume)
        )
        required_volume = avg_volume * self._pm_config.volume_multiplier
        volume_ok = candle.volume >= required_volume
        rvol = candle.volume / avg_volume if avg_volume > 0 else 0.0
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if volume_ok else EvaluationResult.FAIL,
            f"Condition 2/8: Volume confirmation — "
            f"rvol={rvol:.1f}x, threshold={self._pm_config.volume_multiplier}x",
            metadata={
                "condition_name": "volume_confirmation",
                "value": candle.volume,
                "threshold": required_volume,
                "passed": volume_ok,
            },
        )
        if volume_ok:
            conditions_passed.append("volume_confirmation")
        elif failed_condition is None:
            failed_condition = "volume_confirmation"

        # Condition 3/8: Breakout candle body ratio
        candle_range = candle.high - candle.low
        candle_body = abs(candle.close - candle.open)
        body_ratio = candle_body / candle_range if candle_range > 0 else 0.0
        # Body ratio > 0.3 is a reasonable breakout candle (bullish body, not doji)
        body_ok = body_ratio > 0.3
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if body_ok else EvaluationResult.FAIL,
            f"Condition 3/8: Breakout candle body ratio — "
            f"ratio={body_ratio:.2f}, threshold=0.30",
            metadata={
                "condition_name": "body_ratio",
                "value": round(body_ratio, 4),
                "threshold": 0.3,
                "passed": body_ok,
            },
        )
        if body_ok:
            conditions_passed.append("body_ratio")
        elif failed_condition is None:
            failed_condition = "body_ratio"

        # Condition 4/8: Spread/range check (candle range vs ATR)
        range_atr_ratio = candle_range / atr if atr > 0 else 0.0
        spread_ok = range_atr_ratio < 2.0  # Not an extreme bar
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if spread_ok else EvaluationResult.FAIL,
            f"Condition 4/8: Spread/range check — "
            f"range/ATR={range_atr_ratio:.2f}, max=2.00",
            metadata={
                "condition_name": "spread_range",
                "value": round(range_atr_ratio, 4),
                "threshold": 2.0,
                "passed": spread_ok,
            },
        )
        if spread_ok:
            conditions_passed.append("spread_range")
        elif failed_condition is None:
            failed_condition = "spread_range"

        # Condition 5/8: Chase protection (distance from consolidation high)
        chase_limit = consolidation_high * (1 + self._pm_config.max_chase_pct)
        chase_ok = close <= chase_limit
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if chase_ok else EvaluationResult.FAIL,
            f"Condition 5/8: Distance from consolidation high — "
            f"close={close:.2f}, limit={chase_limit:.2f}",
            metadata={
                "condition_name": "chase_protection",
                "value": close,
                "threshold": chase_limit,
                "passed": chase_ok,
            },
        )
        if chase_ok:
            conditions_passed.append("chase_protection")
        elif failed_condition is None:
            failed_condition = "chase_protection"

        # Condition 6/8: Time remaining check
        in_window = self._is_in_entry_window(candle)
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if in_window else EvaluationResult.FAIL,
            f"Condition 6/8: Time remaining check — "
            f"window={self._earliest_entry_time}–{self._latest_entry_time}",
            metadata={
                "condition_name": "time_remaining",
                "passed": in_window,
            },
        )
        if in_window:
            conditions_passed.append("time_remaining")
        elif failed_condition is None:
            failed_condition = "time_remaining"

        # Condition 7/8: Internal risk limits (trend alignment proxy)
        risk_ok = self.check_internal_risk_limits()
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if risk_ok else EvaluationResult.FAIL,
            f"Condition 7/8: Trend alignment (risk limits) — "
            f"{'within limits' if risk_ok else 'limits exceeded'}",
            metadata={
                "condition_name": "trend_alignment",
                "passed": risk_ok,
            },
        )
        if risk_ok:
            conditions_passed.append("trend_alignment")
        elif failed_condition is None:
            failed_condition = "trend_alignment"

        # Condition 8/8: Consolidation quality (tightness + positions, 0 = disabled)
        max_positions = self._pm_config.risk_limits.max_concurrent_positions
        if max_positions > 0:
            active_positions = sum(
                1 for s in self._symbol_state.values() if s.position_active
            )
            positions_ok = active_positions < max_positions
        else:
            active_positions = 0
            positions_ok = True
        entry_price = close
        stop_price = state.midday_low * (1 - self._pm_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price
        valid_risk = risk_per_share > 0
        quality_ok = positions_ok and valid_risk
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if quality_ok else EvaluationResult.FAIL,
            f"Condition 8/8: Consolidation quality — "
            f"positions={active_positions}/{max_positions}, risk/share={risk_per_share:.2f}",
            metadata={
                "condition_name": "consolidation_quality",
                "value": active_positions,
                "threshold": max_positions,
                "passed": quality_ok,
            },
        )
        if quality_ok:
            conditions_passed.append("consolidation_quality")
        elif failed_condition is None:
            failed_condition = "consolidation_quality"

        # Check for failures — use original control flow logic
        if not risk_ok:
            logger.debug("%s: Breakout rejected - internal risk limits hit", symbol)
            self.record_evaluation(
                symbol,
                EvaluationEventType.SIGNAL_REJECTED,
                EvaluationResult.FAIL,
                "AfMo rejected: failed condition 7 (trend_alignment)",
                metadata={"passed": conditions_passed, "failed": failed_condition},
            )
            return None

        if not positions_ok:
            logger.debug("%s: Breakout rejected - max positions reached", symbol)
            self.record_evaluation(
                symbol,
                EvaluationEventType.SIGNAL_REJECTED,
                EvaluationResult.FAIL,
                "AfMo rejected: failed condition 8 (consolidation_quality)",
                metadata={"passed": conditions_passed, "failed": "consolidation_quality"},
            )
            return None

        if not volume_ok:
            logger.debug(
                "%s: Breakout rejected - volume %d < required %.0f",
                symbol,
                candle.volume,
                required_volume,
            )
            self.record_evaluation(
                symbol,
                EvaluationEventType.SIGNAL_REJECTED,
                EvaluationResult.FAIL,
                "AfMo rejected: failed condition 2 (volume_confirmation)",
                metadata={"passed": conditions_passed, "failed": "volume_confirmation"},
            )
            return None

        if not chase_ok:
            logger.debug(
                "%s: Breakout rejected - chase protection (close=%.2f > limit=%.2f)",
                symbol,
                close,
                chase_limit,
            )
            self.record_evaluation(
                symbol,
                EvaluationEventType.SIGNAL_REJECTED,
                EvaluationResult.FAIL,
                "AfMo rejected: failed condition 5 (chase_protection)",
                metadata={"passed": conditions_passed, "failed": "chase_protection"},
            )
            return None

        if not valid_risk:
            logger.debug(
                "%s: Breakout rejected - invalid risk (entry=%.2f, stop=%.2f)",
                symbol,
                entry_price,
                stop_price,
            )
            self.record_evaluation(
                symbol,
                EvaluationEventType.SIGNAL_REJECTED,
                EvaluationResult.FAIL,
                "AfMo rejected: failed condition 8 (consolidation_quality)",
                metadata={"passed": conditions_passed, "failed": "consolidation_quality"},
            )
            return None

        # All conditions pass — build signal
        return self._build_signal(symbol, candle, state, consolidation_high, atr)

    def _calculate_pattern_strength(
        self,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        consolidation_high: float,
        atr: float,
    ) -> tuple[float, dict]:
        """Calculate Afternoon Momentum pattern strength (0-100) and context dict.

        Scoring factors:
        - Entry condition margin (35%): average margin above threshold for 4 conditions.
        - Consolidation tightness (25%): range/ATR; tighter = better.
        - Volume surge (25%): breakout volume vs avg consolidation volume.
        - Time in window (15%): minutes remaining in operating window.

        Args:
            candle: The breakout candle.
            state: The symbol's consolidation state.
            consolidation_high: The consolidation high before the breakout bar.
            atr: The current ATR-14 value.

        Returns:
            Tuple of (pattern_strength, signal_context).
        """
        close = candle.close

        # Average volume from all bars before the current breakout candle
        if len(state.recent_volumes) > 1:
            avg_volume = sum(state.recent_volumes[:-1]) / (len(state.recent_volumes) - 1)
        else:
            avg_volume = float(candle.volume)

        # --- Entry condition margin (35%) ---
        # Average of 4 quantifiable condition credits.

        # 1. Volume margin: actual vs required. 1.0 = at threshold = 50, 1.1+ = 100.
        required_vol = avg_volume * self._pm_config.volume_multiplier
        vol_margin_ratio = candle.volume / required_vol if required_vol > 0 else 1.0
        vol_margin_credit = 50.0 + (vol_margin_ratio - 1.0) * 500.0
        vol_margin_credit = max(0.0, min(100.0, vol_margin_credit))

        # 2. Chase margin: how far below the chase limit (near breakout high = best).
        chase_limit = consolidation_high * (1.0 + self._pm_config.max_chase_pct)
        chase_range = chase_limit - consolidation_high
        chase_margin_ratio = (
            (chase_limit - close) / chase_range if chase_range > 0 else 0.5
        )
        chase_margin_credit = chase_margin_ratio * 100.0
        chase_margin_credit = max(0.0, min(100.0, chase_margin_credit))

        # 3. Consolidation quality: how far below the ATR threshold (tighter = more margin).
        if state.midday_high is not None and state.midday_low is not None and atr > 0:
            midday_range = state.midday_high - state.midday_low
            actual_ratio = midday_range / atr
            cons_quality_ratio = (
                self._pm_config.consolidation_atr_ratio / actual_ratio if actual_ratio > 0 else 1.0
            )
        else:
            cons_quality_ratio = 1.0
        # At threshold = 1.0 = 50; 2× tighter = 2.0 = 100.
        cons_margin_credit = 50.0 + (cons_quality_ratio - 1.0) * 50.0
        cons_margin_credit = max(0.0, min(100.0, cons_margin_credit))

        # 4. Risk per share margin: bigger stop distance = more conviction.
        midday_low = state.midday_low if state.midday_low is not None else close * 0.99
        stop_price_est = midday_low * (1.0 - self._pm_config.stop_buffer_pct)
        risk_pct = (close - stop_price_est) / close if close > 0 else 0.01
        # 0.3% = 50, 0.6%+ = 100. Linear.
        risk_credit = 50.0 + (risk_pct - 0.003) / 0.003 * 50.0
        risk_credit = max(0.0, min(100.0, risk_credit))

        condition_credit = (
            vol_margin_credit + chase_margin_credit + cons_margin_credit + risk_credit
        ) / 4.0

        # --- Consolidation tightness (25%) ---
        if state.midday_high is not None and state.midday_low is not None and atr > 0:
            tightness_ratio = (state.midday_high - state.midday_low) / atr
        else:
            tightness_ratio = 0.5  # neutral

        if tightness_ratio <= 0.3:
            tightness_credit = 90.0
        elif tightness_ratio <= 0.5:
            tightness_credit = 90.0 - 25.0 * (tightness_ratio - 0.3) / 0.2
        elif tightness_ratio <= 0.8:
            tightness_credit = 65.0 - 25.0 * (tightness_ratio - 0.5) / 0.3
        else:
            tightness_credit = 40.0

        # --- Volume surge (25%) ---
        # >2.0× = 85, 1.5× = 65, <1.2× = 30. Piecewise linear.
        surge_ratio = candle.volume / avg_volume if avg_volume > 0 else 1.0

        if surge_ratio < 1.2:
            surge_credit = 30.0
        elif surge_ratio <= 1.5:
            surge_credit = 30.0 + (surge_ratio - 1.2) / 0.3 * 35.0
        elif surge_ratio <= 2.0:
            surge_credit = 65.0 + (surge_ratio - 1.5) / 0.5 * 20.0
        else:
            surge_credit = 85.0

        # --- Time in window (15%) ---
        # 2:00 PM (90 min remaining) = 80, 3:00 PM (30 min) = 50, 3:15 PM (15 min) = 35.
        candle_et = candle.timestamp.astimezone(ET)
        latest_dt = candle_et.replace(
            hour=self._latest_entry_time.hour,
            minute=self._latest_entry_time.minute,
            second=0,
            microsecond=0,
        )
        minutes_remaining = max(0.0, (latest_dt - candle_et).total_seconds() / 60.0)

        if minutes_remaining >= 90.0:
            time_credit = 80.0
        elif minutes_remaining >= 30.0:
            time_credit = 80.0 - 0.5 * (90.0 - minutes_remaining)
        elif minutes_remaining >= 15.0:
            time_credit = 50.0 - (30.0 - minutes_remaining)
        else:
            time_credit = 35.0

        pattern_strength = (
            0.35 * condition_credit
            + 0.25 * tightness_credit
            + 0.25 * surge_credit
            + 0.15 * time_credit
        )
        pattern_strength = max(0.0, min(100.0, pattern_strength))

        signal_context: dict = {
            "vol_margin_ratio": round(vol_margin_ratio, 4),
            "chase_margin_ratio": round(chase_margin_ratio, 4),
            "tightness_ratio": round(tightness_ratio, 4),
            "surge_ratio": round(surge_ratio, 4),
            "minutes_remaining": round(minutes_remaining, 1),
            "condition_credit": round(condition_credit, 2),
            "tightness_credit": round(tightness_credit, 2),
            "surge_credit": round(surge_credit, 2),
            "time_credit": round(time_credit, 2),
        }

        self.record_evaluation(
            candle.symbol,
            EvaluationEventType.QUALITY_SCORED,
            EvaluationResult.INFO,
            f"Afternoon Momentum pattern strength: {pattern_strength:.1f}",
            metadata=signal_context,
        )

        return pattern_strength, signal_context

    def _build_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        consolidation_high: float,
        atr: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent for afternoon breakout entry.

        Args:
            symbol: The symbol to trade.
            candle: The breakout candle.
            state: The symbol's state (contains consolidation range).
            consolidation_high: The consolidation high BEFORE the breakout bar.
            atr: The current ATR-14 value (used for pattern strength scoring).

        Returns:
            SignalEvent with T1/T2 targets.
        """
        if state.midday_low is None:
            return None

        entry_price = candle.close
        stop_price = state.midday_low * (1 - self._pm_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price

        # Calculate targets
        t1 = entry_price + risk_per_share * self._pm_config.target_1_r
        t2 = entry_price + risk_per_share * self._pm_config.target_2_r

        # Compute dynamic time stop
        time_stop_seconds = self._compute_effective_time_stop(candle)

        # Calculate pattern strength (share_count deferred to Dynamic Sizer, Sprint 24 S6a)
        pattern_strength, signal_context = self._calculate_pattern_strength(
            candle, state, consolidation_high, atr
        )

        # Zero-R guard: suppress signals with no profit potential
        # Consistent with ORB / R2G / PatternBasedStrategy (FIX-19 P1-B-M06).
        if self._has_zero_r(symbol, entry_price, t1):
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                f"Zero R: entry={entry_price:.2f}, t1={t1:.2f}",
            )
            self._track_signal_rejected("zero_r")
            return None

        # Build signal (use consolidation_high for the rationale, not updated midday_high)
        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            share_count=0,
            rationale=(
                f"Afternoon Momentum: {symbol} broke above consolidation high "
                f"{consolidation_high:.2f} "
                f"(range: {state.midday_low:.2f}-{consolidation_high:.2f}, "
                f"{state.consolidation_bars} bars)"
            ),
            time_stop_seconds=time_stop_seconds,
            pattern_strength=pattern_strength,
            signal_context=signal_context,
            atr_value=atr,  # ATR(14) on 1-min bars per AMD-9 standardization
        )

        # Emit SIGNAL_GENERATED before state transition
        self.record_evaluation(
            symbol,
            EvaluationEventType.SIGNAL_GENERATED,
            EvaluationResult.PASS,
            f"AfMo signal: {symbol} breakout at {entry_price:.2f}",
            metadata={
                "entry": entry_price,
                "stop": stop_price,
                "t1": t1,
                "t2": t2,
                "pattern_strength": round(pattern_strength, 2),
            },
        )

        # Mark state as entered
        state.state = ConsolidationState.ENTERED
        state.position_active = True
        self._signals_generated_today += 1

        self.record_evaluation(
            symbol,
            EvaluationEventType.STATE_TRANSITION,
            EvaluationResult.INFO,
            (
                f"State transition: {ConsolidationState.CONSOLIDATED} → "
                f"{ConsolidationState.ENTERED}"
            ),
            metadata={
                "from_state": str(ConsolidationState.CONSOLIDATED),
                "to_state": str(ConsolidationState.ENTERED),
                "trigger": "signal generated — all conditions passed",
            },
        )

        logger.info(
            "%s: Afternoon breakout signal - entry=%.2f, stop=%.2f, T1=%.2f, T2=%.2f, "
            "pattern_strength=%.1f, time_stop=%ds",
            symbol,
            entry_price,
            stop_price,
            t1,
            t2,
            pattern_strength,
            time_stop_seconds,
        )

        return signal

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for Afternoon Momentum — uses candles).

        Position management is handled by Order Manager.
        """
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria for Afternoon Momentum stock selection.

        Uses same criteria as other strategies: gapping stocks with volume.
        """
        return ScannerCriteria(
            min_price=10.0,
            max_price=200.0,
            min_volume_avg_daily=1_000_000,
            min_relative_volume=2.0,
            min_gap_pct=0.02,  # 2% gap minimum
            max_results=20,
        )

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate position size using the universal risk formula.

        Includes minimum risk floor to prevent enormous positions on tight
        consolidation ranges where the stop is very close to entry.

        Shares = risk_dollars / effective_risk_per_share
        Risk dollars = allocated_capital x max_loss_per_trade_pct
        Effective risk = max(actual_risk, entry_price x 0.3%)
        """
        if entry_price <= stop_price:
            return 0  # Invalid for longs

        if self._allocated_capital <= 0:
            return 0

        risk_per_share = entry_price - stop_price

        # Apply minimum risk floor (0.3% of entry price)
        min_risk = entry_price * 0.003
        effective_risk = max(risk_per_share, min_risk)

        risk_dollars = (
            self._allocated_capital * self._pm_config.risk_limits.max_loss_per_trade_pct
        )
        shares = int(risk_dollars / effective_risk)

        return max(0, shares)

    def get_exit_rules(self) -> ExitRules:
        """Return Afternoon Momentum exit rules (T1 50%, T2 50%, time stop)."""
        return ExitRules(
            stop_type="fixed",
            stop_price_func="consolidation_low",
            targets=[
                ProfitTarget(
                    r_multiple=self._pm_config.target_1_r,
                    position_pct=0.5,  # Exit 50% at T1
                ),
                ProfitTarget(
                    r_multiple=self._pm_config.target_2_r,
                    position_pct=0.5,  # Exit remaining 50% at T2
                ),
            ],
            time_stop_minutes=self._pm_config.max_hold_minutes,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions for Afternoon Momentum activation.

        Works well in trending conditions and higher volatility where
        afternoon momentum moves are present.
        """
        default_regimes = [
            "bullish_trending",
            "bearish_trending",
            "range_bound",
            "high_volatility",
        ]
        regimes = self._config.allowed_regimes or default_regimes
        return MarketConditionsFilter(
            allowed_regimes=regimes,
            max_vix=30.0,
        )

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._symbol_state.clear()
        self._logged_window_opened = False
        self._logged_window_closed = False
        self._signals_generated_today = 0
        logger.debug("%s: Afternoon Momentum strategy daily state reset", self.strategy_id)

    def mark_position_closed(self, symbol: str) -> None:
        """Mark a position as closed (called by Order Manager).

        Args:
            symbol: The symbol whose position was closed.
        """
        state = self._symbol_state.get(symbol)
        if state is not None:
            state.position_active = False

    def set_data_service(self, data_service: DataService) -> None:
        """Set the data service for ATR queries.

        Args:
            data_service: The DataService instance.
        """
        self._data_service = data_service
