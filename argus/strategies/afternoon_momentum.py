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

        # Parse force_close_time
        fc_parts = self._pm_config.force_close_time.split(":")
        fc_h, fc_m = int(fc_parts[0]), int(fc_parts[1])

        candle_dt = candle.timestamp.astimezone(ET)
        force_close_dt = candle_dt.replace(hour=fc_h, minute=fc_m, second=0, microsecond=0)

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

        state = self._get_symbol_state(symbol)

        # Track volume for all bars
        state.recent_volumes.append(event.volume)

        # Terminal states: no more signals for this symbol today
        if state.state in (ConsolidationState.ENTERED, ConsolidationState.REJECTED):
            return None

        # Get ATR from data service
        atr: float | None = None
        if self._data_service is not None:
            atr = await self._data_service.get_indicator(symbol, "atr_14")

        if atr is None or atr <= 0:
            # No ATR available yet, stay in current state
            return None

        # State machine transitions
        return await self._process_state_machine(symbol, event, state, atr)

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

        # Check if range is too wide -> REJECTED
        if consolidation_ratio > self._pm_config.max_consolidation_atr_ratio:
            state.state = ConsolidationState.REJECTED
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
            logger.debug(
                "%s: ACCUMULATING -> CONSOLIDATED (ratio=%.2f < threshold=%.2f, bars=%d)",
                symbol,
                consolidation_ratio,
                self._pm_config.consolidation_atr_ratio,
                state.consolidation_bars,
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
                symbol, candle, state, consolidation_high_before
            )

        return None

    async def _check_breakout_entry(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        consolidation_high: float,
    ) -> SignalEvent | None:
        """Check if breakout entry conditions are met.

        Args:
            symbol: The symbol being processed.
            candle: The breakout candle.
            state: The symbol's state.
            consolidation_high: The consolidation high BEFORE this bar (for chase check).

        Returns:
            SignalEvent if all conditions pass, None otherwise.
        """
        close = candle.close

        if state.midday_low is None:
            return None

        # 1. Internal risk limits check
        if not self.check_internal_risk_limits():
            logger.debug("%s: Breakout rejected - internal risk limits hit", symbol)
            return None

        # 2. Concurrent positions check
        active_positions = sum(1 for s in self._symbol_state.values() if s.position_active)
        max_positions = self._pm_config.risk_limits.max_concurrent_positions
        if active_positions >= max_positions:
            logger.debug("%s: Breakout rejected - max positions reached", symbol)
            return None

        # 3. Volume confirmation
        if state.recent_volumes:
            avg_volume = sum(state.recent_volumes) / len(state.recent_volumes)
            required_volume = avg_volume * self._pm_config.volume_multiplier
            if candle.volume < required_volume:
                logger.debug(
                    "%s: Breakout rejected - volume %d < required %.0f",
                    symbol,
                    candle.volume,
                    required_volume,
                )
                return None

        # 4. Chase protection: not too far above consolidation_high
        chase_limit = consolidation_high * (1 + self._pm_config.max_chase_pct)
        if close > chase_limit:
            logger.debug(
                "%s: Breakout rejected - chase protection (close=%.2f > limit=%.2f)",
                symbol,
                close,
                chase_limit,
            )
            return None

        # 5. Valid risk per share (stop below consolidation_low)
        entry_price = close
        stop_price = state.midday_low * (1 - self._pm_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price

        if risk_per_share <= 0:
            logger.debug(
                "%s: Breakout rejected - invalid risk (entry=%.2f, stop=%.2f)",
                symbol,
                entry_price,
                stop_price,
            )
            return None

        # All conditions pass — build signal
        return self._build_signal(symbol, candle, state, consolidation_high)

    def _build_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: ConsolidationSymbolState,
        consolidation_high: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent for afternoon breakout entry.

        Args:
            symbol: The symbol to trade.
            candle: The breakout candle.
            state: The symbol's state (contains consolidation range).
            consolidation_high: The consolidation high BEFORE the breakout bar.

        Returns:
            SignalEvent with T1/T2 targets, or None if position size is 0.
        """
        if state.midday_low is None:
            return None

        entry_price = candle.close
        stop_price = state.midday_low * (1 - self._pm_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price

        # Calculate targets
        t1 = entry_price + risk_per_share * self._pm_config.target_1_r
        t2 = entry_price + risk_per_share * self._pm_config.target_2_r

        # Calculate position size
        shares = self.calculate_position_size(entry_price, stop_price)
        if shares <= 0:
            logger.warning("%s: Position size calculation returned 0", symbol)
            return None

        # Compute dynamic time stop
        time_stop_seconds = self._compute_effective_time_stop(candle)

        # Build signal (use consolidation_high for the rationale, not updated midday_high)
        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            share_count=shares,
            rationale=(
                f"Afternoon Momentum: {symbol} broke above consolidation high "
                f"{consolidation_high:.2f} (range: {state.midday_low:.2f}-{consolidation_high:.2f}, "
                f"{state.consolidation_bars} bars)"
            ),
            time_stop_seconds=time_stop_seconds,
        )

        # Mark state as entered
        state.state = ConsolidationState.ENTERED
        state.position_active = True

        logger.info(
            "%s: Afternoon breakout signal - entry=%.2f, stop=%.2f, T1=%.2f, T2=%.2f, "
            "shares=%d, time_stop=%ds",
            symbol,
            entry_price,
            stop_price,
            t1,
            t2,
            shares,
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
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "high_volatility"],
            max_vix=30.0,
        )

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._symbol_state.clear()
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
