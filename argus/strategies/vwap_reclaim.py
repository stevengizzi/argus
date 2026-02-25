"""VWAP Reclaim Strategy implementation.

A mean-reversion strategy that buys stocks reclaiming VWAP after a pullback.
This is ARGUS's first mean-reversion strategy.

Entry logic:
1. Stock must be above VWAP at some point after market open
2. Stock pulls back below VWAP (minimum pullback depth and duration)
3. Stock reclaims VWAP with volume confirmation
4. Entry on candle CLOSE above VWAP

Operates 10:00 AM – 12:00 PM ET.

DEC-136: VWAP Reclaim strategy — mean-reversion entry on VWAP reclaim.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import VwapReclaimConfig
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


class VwapState(StrEnum):
    """State machine states for VWAP Reclaim tracking."""

    WATCHING = "watching"  # Initial state, waiting to see price vs VWAP
    ABOVE_VWAP = "above_vwap"  # Price is above VWAP (no pullback yet)
    BELOW_VWAP = "below_vwap"  # Price pulled back below VWAP, tracking
    ENTERED = "entered"  # Position taken, terminal state
    EXHAUSTED = "exhausted"  # Pullback too deep, terminal state


@dataclass
class VwapSymbolState:
    """Per-symbol intraday state for VWAP Reclaim tracking.

    Tracks the state machine progression and pullback metrics for a single symbol.
    """

    # State machine
    state: VwapState = VwapState.WATCHING

    # Pullback tracking (populated when state is BELOW_VWAP)
    pullback_low: float | None = None
    bars_below_vwap: int = 0

    # Volume tracking (all bars seen for this symbol)
    recent_volumes: list[int] = field(default_factory=list)

    # Position tracking
    position_active: bool = False


class VwapReclaimStrategy(BaseStrategy):
    """VWAP Reclaim Strategy.

    Mean-reversion strategy that enters long when a stock reclaims VWAP
    after a pullback. Designed for the late-morning consolidation period.

    State machine:
    - WATCHING: Initial state, watching for price position relative to VWAP
    - ABOVE_VWAP: Price is above VWAP (prerequisite for pullback)
    - BELOW_VWAP: Price has pulled back below VWAP, tracking for reclaim
    - ENTERED: Position taken (terminal)
    - EXHAUSTED: Pullback exceeded max depth (terminal)

    Entry requires:
    1. State is BELOW_VWAP
    2. Candle closes above VWAP (the reclaim)
    3. Pullback depth >= min_pullback_pct
    4. Duration >= min_pullback_bars
    5. Volume confirmation on reclaim candle
    6. Chase protection (not too far above VWAP)
    7. Time window check
    8. Internal risk limits pass
    9. Position count limit not exceeded
    """

    def __init__(
        self,
        config: VwapReclaimConfig,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the VWAP Reclaim strategy.

        Args:
            config: VwapReclaimConfig with VWAP-specific parameters.
            data_service: DataService for VWAP queries.
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        super().__init__(config, clock=clock)
        self._vwap_config = config
        self._data_service = data_service

        # Per-symbol state
        self._symbol_state: dict[str, VwapSymbolState] = {}

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

    def _get_symbol_state(self, symbol: str) -> VwapSymbolState:
        """Get or create the state for a symbol."""
        if symbol not in self._symbol_state:
            self._symbol_state[symbol] = VwapSymbolState()
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
        """Check if candle is within the entry time window."""
        candle_time = self._get_candle_time(candle)
        return self._earliest_entry_time <= candle_time < self._latest_entry_time

    # -------------------------------------------------------------------------
    # Core Interface Implementation
    # -------------------------------------------------------------------------

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle and potentially emit a VWAP reclaim signal.

        Args:
            event: The CandleEvent to process.

        Returns:
            SignalEvent if reclaim criteria met, None otherwise.
        """
        symbol = event.symbol

        # Ignore if not in watchlist
        if symbol not in self._watchlist:
            return None

        state = self._get_symbol_state(symbol)

        # Track volume for all bars
        state.recent_volumes.append(event.volume)

        # Terminal states: no more signals for this symbol today
        if state.state in (VwapState.ENTERED, VwapState.EXHAUSTED):
            return None

        # Get VWAP from data service
        vwap: float | None = None
        if self._data_service is not None:
            vwap = await self._data_service.get_indicator(symbol, "vwap")

        if vwap is None or vwap <= 0:
            # No VWAP available, stay in watching
            return None

        # State machine transitions
        return await self._process_state_machine(symbol, event, state, vwap)

    async def _process_state_machine(
        self,
        symbol: str,
        candle: CandleEvent,
        state: VwapSymbolState,
        vwap: float,
    ) -> SignalEvent | None:
        """Process the state machine for a symbol.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.
            vwap: The current VWAP value.

        Returns:
            SignalEvent if entry conditions are met, None otherwise.
        """
        close = candle.close

        if state.state == VwapState.WATCHING:
            # Transition to ABOVE_VWAP when close > VWAP
            if close > vwap:
                state.state = VwapState.ABOVE_VWAP
                logger.debug(
                    "%s: WATCHING → ABOVE_VWAP (close=%.2f > vwap=%.2f)",
                    symbol,
                    close,
                    vwap,
                )
            return None

        if state.state == VwapState.ABOVE_VWAP:
            if close < vwap:
                # Start tracking pullback
                state.state = VwapState.BELOW_VWAP
                state.pullback_low = candle.low
                state.bars_below_vwap = 1
                logger.debug(
                    "%s: ABOVE_VWAP → BELOW_VWAP (close=%.2f < vwap=%.2f, low=%.2f)",
                    symbol,
                    close,
                    vwap,
                    candle.low,
                )
            return None

        if state.state == VwapState.BELOW_VWAP:
            return await self._process_below_vwap(symbol, candle, state, vwap)

        return None

    async def _process_below_vwap(
        self,
        symbol: str,
        candle: CandleEvent,
        state: VwapSymbolState,
        vwap: float,
    ) -> SignalEvent | None:
        """Process a candle while in BELOW_VWAP state.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.
            vwap: The current VWAP value.

        Returns:
            SignalEvent if entry conditions are met, None otherwise.
        """
        close = candle.close

        # Update pullback tracking
        if state.pullback_low is None:
            state.pullback_low = candle.low
        else:
            state.pullback_low = min(state.pullback_low, candle.low)

        # Check if pullback is too deep → EXHAUSTED
        pullback_depth = (vwap - state.pullback_low) / vwap
        if pullback_depth > self._vwap_config.max_pullback_pct:
            state.state = VwapState.EXHAUSTED
            logger.info(
                "%s: BELOW_VWAP → EXHAUSTED (pullback %.2f%% > max %.2f%%)",
                symbol,
                pullback_depth * 100,
                self._vwap_config.max_pullback_pct * 100,
            )
            return None

        if close < vwap:
            # Still below VWAP, increment bar count
            state.bars_below_vwap += 1
            return None

        # Close is above VWAP — potential reclaim
        if close > vwap:
            # Check all entry conditions
            return await self._check_reclaim_entry(symbol, candle, state, vwap)

        return None

    async def _check_reclaim_entry(
        self,
        symbol: str,
        candle: CandleEvent,
        state: VwapSymbolState,
        vwap: float,
    ) -> SignalEvent | None:
        """Check if VWAP reclaim entry conditions are met.

        Args:
            symbol: The symbol being processed.
            candle: The reclaim candle.
            state: The symbol's state.
            vwap: The current VWAP value.

        Returns:
            SignalEvent if all conditions pass, None otherwise.
        """
        close = candle.close

        # Condition met: close > VWAP (already checked by caller)

        # Check conditions — return None for any failure, transition to ABOVE_VWAP

        # 1. Time window check
        if not self._is_in_entry_window(candle):
            # Reclaim but outside time window — allow retry by going back to ABOVE_VWAP
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Reclaim outside time window, reset to ABOVE_VWAP", symbol)
            return None

        # 2. Internal risk limits
        if not self.check_internal_risk_limits():
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Internal risk limits hit, reset to ABOVE_VWAP", symbol)
            return None

        # 3. Concurrent positions check
        active_positions = sum(1 for s in self._symbol_state.values() if s.position_active)
        max_positions = self._vwap_config.risk_limits.max_concurrent_positions
        if active_positions >= max_positions:
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Max positions reached, reset to ABOVE_VWAP", symbol)
            return None

        # 4. Pullback depth check (minimum pullback required)
        if state.pullback_low is None:
            return None
        pullback_depth = (vwap - state.pullback_low) / vwap
        if pullback_depth < self._vwap_config.min_pullback_pct:
            # Reclaim but pullback not deep enough — reset and allow retry
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug(
                "%s: Pullback %.2f%% < min %.2f%%, reset to ABOVE_VWAP",
                symbol,
                pullback_depth * 100,
                self._vwap_config.min_pullback_pct * 100,
            )
            return None

        # 5. Minimum pullback bars check
        if state.bars_below_vwap < self._vwap_config.min_pullback_bars:
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug(
                "%s: Pullback bars %d < min %d, reset to ABOVE_VWAP",
                symbol,
                state.bars_below_vwap,
                self._vwap_config.min_pullback_bars,
            )
            return None

        # 6. Volume confirmation on reclaim candle
        if state.recent_volumes:
            avg_volume = sum(state.recent_volumes) / len(state.recent_volumes)
            required_volume = avg_volume * self._vwap_config.volume_confirmation_multiplier
            if candle.volume < required_volume:
                state.state = VwapState.ABOVE_VWAP
                state.bars_below_vwap = 0
                state.pullback_low = None
                logger.debug(
                    "%s: Volume %d < required %.0f, reset to ABOVE_VWAP",
                    symbol,
                    candle.volume,
                    required_volume,
                )
                return None

        # 7. Chase protection: not too far above VWAP
        chase_limit = vwap * (1 + self._vwap_config.max_chase_above_vwap_pct)
        if close > chase_limit:
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug(
                "%s: Chase protection: close %.2f > limit %.2f, reset to ABOVE_VWAP",
                symbol,
                close,
                chase_limit,
            )
            return None

        # All conditions pass — build signal
        return self._build_signal(symbol, candle, state, vwap)

    def _build_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: VwapSymbolState,
        vwap: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent for VWAP reclaim entry.

        Args:
            symbol: The symbol to trade.
            candle: The reclaim candle.
            state: The symbol's state (contains pullback_low).
            vwap: The current VWAP value.

        Returns:
            SignalEvent with T1/T2 targets, or None if position size is 0.
        """
        if state.pullback_low is None:
            return None

        entry_price = candle.close
        stop_price = state.pullback_low * (1 - self._vwap_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price

        # Calculate targets
        t1 = entry_price + risk_per_share * self._vwap_config.target_1_r
        t2 = entry_price + risk_per_share * self._vwap_config.target_2_r

        # Calculate position size
        shares = self.calculate_position_size(entry_price, stop_price)
        if shares <= 0:
            logger.warning("%s: Position size calculation returned 0", symbol)
            return None

        # Build signal
        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            share_count=shares,
            rationale=(
                f"VWAP Reclaim: {symbol} reclaimed VWAP {vwap:.2f} after pullback to "
                f"{state.pullback_low:.2f} ({state.bars_below_vwap} bars below)"
            ),
            time_stop_seconds=self._vwap_config.time_stop_minutes * 60,
        )

        # Mark state as entered
        state.state = VwapState.ENTERED
        state.position_active = True

        logger.info(
            "%s: VWAP reclaim signal - entry=%.2f, stop=%.2f, T1=%.2f, T2=%.2f, "
            "shares=%d, time_stop=%dm",
            symbol,
            entry_price,
            stop_price,
            t1,
            t2,
            shares,
            self._vwap_config.time_stop_minutes,
        )

        return signal

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for VWAP Reclaim — uses candles).

        Position management is handled by Order Manager.
        """
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria for VWAP Reclaim stock selection.

        Same criteria as ORB strategies: gapping stocks with volume.
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

        Includes minimum risk floor to prevent enormous positions on shallow
        pullbacks where the stop is very close to entry.

        Shares = risk_dollars / effective_risk_per_share
        Risk dollars = allocated_capital × max_loss_per_trade_pct
        Effective risk = max(actual_risk, entry_price × 0.3%)
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
            self._allocated_capital * self._vwap_config.risk_limits.max_loss_per_trade_pct
        )
        shares = int(risk_dollars / effective_risk)

        return max(0, shares)

    def get_exit_rules(self) -> ExitRules:
        """Return VWAP Reclaim exit rules (T1 50%, T2 50%, time stop)."""
        return ExitRules(
            stop_type="fixed",
            stop_price_func="pullback_low",
            targets=[
                ProfitTarget(
                    r_multiple=self._vwap_config.target_1_r,
                    position_pct=0.5,  # Exit 50% at T1
                ),
                ProfitTarget(
                    r_multiple=self._vwap_config.target_2_r,
                    position_pct=0.5,  # Exit remaining 50% at T2
                ),
            ],
            time_stop_minutes=self._vwap_config.time_stop_minutes,
        )

    def get_market_conditions_filter(self) -> MarketConditionsFilter:
        """Return market conditions for VWAP Reclaim activation.

        Works well in trending and range-bound conditions where mean-reversion
        patterns are present.
        """
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "range_bound", "high_volatility"],
            max_vix=35.0,
        )

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._symbol_state.clear()
        logger.debug("%s: VWAP Reclaim strategy daily state reset", self.strategy_id)

    def mark_position_closed(self, symbol: str) -> None:
        """Mark a position as closed (called by Order Manager).

        Args:
            symbol: The symbol whose position was closed.
        """
        state = self._symbol_state.get(symbol)
        if state is not None:
            state.position_active = False

    def set_data_service(self, data_service: DataService) -> None:
        """Set the data service for VWAP queries.

        Args:
            data_service: The DataService instance.
        """
        self._data_service = data_service
