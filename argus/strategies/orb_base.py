"""ORB Base Strategy - shared logic for ORB strategy variants.

Extracts common opening-range formation and breakout detection logic used by
OrbBreakoutStrategy (swing targets) and OrbScalpStrategy (scalp targets).

Both strategies:
1. Form an opening range during the first N minutes
2. Validate range size against ATR bounds
3. Detect breakouts with volume/VWAP/chase protection
4. Differ in targets, hold time, and exit rules

DEC-120: ORBBase extraction for shared OR formation + breakout detection.
"""

from __future__ import annotations

import logging
from abc import abstractmethod
from dataclasses import dataclass, field
from datetime import time
from typing import TYPE_CHECKING, Protocol, runtime_checkable
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import OperatingWindow, StrategyRiskLimits
from argus.core.events import CandleEvent, SignalEvent, TickEvent
from argus.models.strategy import ScannerCriteria
from argus.strategies.base_strategy import BaseStrategy

if TYPE_CHECKING:
    from argus.data.service import DataService

logger = logging.getLogger(__name__)

# Eastern Time zone for market hours comparisons
ET = ZoneInfo("America/New_York")


@runtime_checkable
class OrbConfigProtocol(Protocol):
    """Protocol for ORB strategy configs.

    Both OrbBreakoutConfig and OrbScalpConfig must provide these fields.
    Using a Protocol allows OrbBaseStrategy to accept either config type
    without coupling to concrete implementations.
    """

    strategy_id: str
    name: str
    version: str
    orb_window_minutes: int
    min_range_atr_ratio: float
    max_range_atr_ratio: float
    chase_protection_pct: float
    breakout_volume_multiplier: float
    volume_threshold_rvol: float
    operating_window: OperatingWindow
    risk_limits: StrategyRiskLimits


@dataclass
class OrbSymbolState:
    """Per-symbol intraday state for ORB strategies.

    Tracks opening range formation and breakout detection for a single symbol.
    Shared by OrbBreakoutStrategy and OrbScalpStrategy.
    """

    # Opening range formation
    or_candles: list[CandleEvent] = field(default_factory=list)
    or_high: float | None = None
    or_low: float | None = None
    or_midpoint: float | None = None
    or_complete: bool = False
    or_valid: bool = False
    or_avg_volume: float = 0.0
    or_rejection_reason: str | None = None

    # Breakout tracking
    breakout_triggered: bool = False
    position_active: bool = False


class OrbBaseStrategy(BaseStrategy):
    """Abstract base class for ORB strategy variants.

    Provides shared logic for:
    - Opening range formation during configurable window
    - OR validation against ATR bounds
    - Breakout detection with volume/VWAP/chase protection
    - Position size calculation using universal risk formula

    Subclasses must implement:
    - _build_breakout_signal(): Build the SignalEvent with strategy-specific targets
    - get_exit_rules(): Define exit behavior (targets, time stops)
    - get_market_conditions_filter(): Define regime conditions
    """

    def __init__(
        self,
        config: OrbConfigProtocol,
        data_service: DataService | None = None,
        clock: Clock | None = None,
    ) -> None:
        """Initialize the ORB base strategy.

        Args:
            config: Config with ORB-specific fields (OrbBreakoutConfig or OrbScalpConfig).
            data_service: DataService for indicator queries (VWAP, ATR).
            clock: Clock for time access. Defaults to SystemClock() if not provided.
        """
        # BaseStrategy expects StrategyConfig, but OrbConfigProtocol is a structural
        # subtype. Use type: ignore to satisfy the type checker.
        super().__init__(config, clock=clock)  # type: ignore[arg-type]
        self._orb_config: OrbConfigProtocol = config
        self._data_service = data_service

        # Per-symbol state
        self._symbol_state: dict[str, OrbSymbolState] = {}

        # Market open time (9:30 AM ET as default)
        self._market_open = time(9, 30)

        # OR window end time (calculated from orb_window_minutes)
        or_minutes = self._orb_config.orb_window_minutes
        or_end_hour = 9 + (30 + or_minutes) // 60
        or_end_minute = (30 + or_minutes) % 60
        self._or_end_time = time(or_end_hour, or_end_minute)

        # Latest entry time from config
        latest_str = self._orb_config.operating_window.latest_entry
        h, m = map(int, latest_str.split(":"))
        self._latest_entry_time = time(h, m)

    # -------------------------------------------------------------------------
    # Symbol State Management
    # -------------------------------------------------------------------------

    def _get_symbol_state(self, symbol: str) -> OrbSymbolState:
        """Get or create the state for a symbol."""
        if symbol not in self._symbol_state:
            self._symbol_state[symbol] = OrbSymbolState()
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

    def _is_in_or_window(self, candle: CandleEvent) -> bool:
        """Check if candle is within the opening range window."""
        candle_time = self._get_candle_time(candle)
        return self._market_open <= candle_time < self._or_end_time

    def _is_past_or_window(self, candle: CandleEvent) -> bool:
        """Check if candle is after the OR window."""
        return self._get_candle_time(candle) >= self._or_end_time

    def _is_before_latest_entry(self, candle: CandleEvent) -> bool:
        """Check if candle is before latest entry time."""
        return self._get_candle_time(candle) < self._latest_entry_time

    # -------------------------------------------------------------------------
    # Opening Range Formation
    # -------------------------------------------------------------------------

    async def _finalize_opening_range(self, symbol: str, state: OrbSymbolState) -> None:
        """Finalize the opening range and validate it."""
        if not state.or_candles:
            state.or_valid = False
            state.or_rejection_reason = "No candles in OR window"
            state.or_complete = True
            return

        # Calculate OR high, low, midpoint
        state.or_high = max(c.high for c in state.or_candles)
        state.or_low = min(c.low for c in state.or_candles)
        state.or_midpoint = (state.or_high + state.or_low) / 2

        # Calculate average volume during OR
        total_volume = sum(c.volume for c in state.or_candles)
        state.or_avg_volume = total_volume / len(state.or_candles)

        # Validate range size against ATR bounds
        range_size = state.or_high - state.or_low

        # Get ATR from data service
        atr: float | None = None
        if self._data_service is not None:
            atr = await self._data_service.get_indicator(symbol, "atr_14")

        if atr is not None and atr > 0:
            range_to_atr = range_size / atr

            if range_to_atr < self._orb_config.min_range_atr_ratio:
                state.or_valid = False
                state.or_rejection_reason = (
                    f"Range too tight: {range_to_atr:.2f} < {self._orb_config.min_range_atr_ratio}"
                )
                logger.info("%s: ORB rejected - %s", symbol, state.or_rejection_reason)
            elif range_to_atr > self._orb_config.max_range_atr_ratio:
                state.or_valid = False
                state.or_rejection_reason = (
                    f"Range too wide: {range_to_atr:.2f} > {self._orb_config.max_range_atr_ratio}"
                )
                logger.info("%s: ORB rejected - %s", symbol, state.or_rejection_reason)
            else:
                state.or_valid = True
                logger.info(
                    "%s: OR formed - high=%.2f, low=%.2f, mid=%.2f, range/ATR=%.2f",
                    symbol,
                    state.or_high,
                    state.or_low,
                    state.or_midpoint,
                    range_to_atr,
                )
        else:
            # No ATR available, accept the range
            state.or_valid = True
            logger.info(
                "%s: OR formed (no ATR validation) - high=%.2f, low=%.2f, mid=%.2f",
                symbol,
                state.or_high,
                state.or_low,
                state.or_midpoint,
            )

        state.or_complete = True

    # -------------------------------------------------------------------------
    # Breakout Detection
    # -------------------------------------------------------------------------

    async def _check_breakout_conditions(
        self, symbol: str, candle: CandleEvent, state: OrbSymbolState
    ) -> SignalEvent | None:
        """Check if breakout conditions are met and return SignalEvent if so.

        Verifies:
        1. Candle closes above OR high
        2. Volume exceeds threshold (OR avg × multiplier)
        3. Price above VWAP
        4. Chase protection (not too far above OR high)

        If all conditions pass, delegates to _build_breakout_signal() for
        strategy-specific signal construction.
        """
        # Must have valid OR
        if state.or_high is None or state.or_midpoint is None:
            return None

        # 1. Candle must CLOSE above OR high (not just wick)
        if candle.close <= state.or_high:
            return None

        # 2. Volume check: breakout candle volume > multiplier × OR avg volume
        volume_threshold = state.or_avg_volume * self._orb_config.breakout_volume_multiplier
        if candle.volume < volume_threshold:
            logger.debug(
                "%s: Volume too low for breakout: %d < %.0f",
                symbol,
                candle.volume,
                volume_threshold,
            )
            return None

        # 3. VWAP check: price must be above VWAP
        if self._data_service is not None:
            vwap = await self._data_service.get_indicator(symbol, "vwap")
            if vwap is not None and candle.close < vwap:
                logger.debug(
                    "%s: Below VWAP for breakout: %.2f < %.2f",
                    symbol,
                    candle.close,
                    vwap,
                )
                return None

        # 4. Chase protection: price hasn't moved too far from OR high
        chase_limit = state.or_high * (1 + self._orb_config.chase_protection_pct)
        if candle.close > chase_limit:
            logger.debug(
                "%s: Chase protection triggered: %.2f > %.2f",
                symbol,
                candle.close,
                chase_limit,
            )
            return None

        # All conditions met! Delegate to subclass for signal construction
        return await self._build_breakout_signal(symbol, candle, state, volume_threshold)

    @abstractmethod
    async def _build_breakout_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: OrbSymbolState,
        volume_threshold: float,
    ) -> SignalEvent | None:
        """Build a SignalEvent with strategy-specific targets.

        Called by _check_breakout_conditions() when all breakout criteria are met.
        Subclasses implement this to define their own entry/target/stop configuration.

        Args:
            symbol: The symbol that triggered the breakout.
            candle: The breakout candle.
            state: The symbol's ORB state (contains OR high/low/midpoint).
            volume_threshold: The volume threshold that was exceeded.

        Returns:
            SignalEvent with strategy-specific configuration, or None if
            additional strategy-specific checks fail (e.g., position size = 0).
        """

    # -------------------------------------------------------------------------
    # Core Interface Implementation
    # -------------------------------------------------------------------------

    async def on_candle(self, event: CandleEvent) -> SignalEvent | None:
        """Process a candle and potentially emit a breakout signal.

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

        # Phase 1: Opening Range Formation
        if not state.or_complete:
            if self._is_in_or_window(event):
                # Accumulate candles during OR window
                state.or_candles.append(event)
                return None
            elif self._is_past_or_window(event) and not state.or_complete:
                # First candle after OR window - finalize the range
                await self._finalize_opening_range(symbol, state)

        # Phase 2: Breakout Detection
        if state.or_complete and state.or_valid and not state.breakout_triggered:
            # Check time window
            if not self._is_before_latest_entry(event):
                return None

            # Check internal risk limits
            if not self.check_internal_risk_limits():
                return None

            # Check concurrent positions
            active_positions = sum(1 for s in self._symbol_state.values() if s.position_active)
            max_positions = self._orb_config.risk_limits.max_concurrent_positions
            if active_positions >= max_positions:
                return None

            # Check breakout conditions
            return await self._check_breakout_conditions(symbol, event, state)

        return None

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for ORB - uses candles).

        Position management is handled by Order Manager.
        """
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria for ORB stock selection."""
        return ScannerCriteria(
            min_price=10.0,
            max_price=200.0,
            min_volume_avg_daily=1_000_000,
            min_relative_volume=self._orb_config.volume_threshold_rvol,
            min_gap_pct=0.02,  # 2% gap minimum
            max_results=20,
        )

    def calculate_position_size(self, entry_price: float, stop_price: float) -> int:
        """Calculate position size using the universal risk formula.

        Shares = risk_dollars / risk_per_share
        Risk dollars = allocated_capital × max_loss_per_trade_pct
        """
        if entry_price <= stop_price:
            return 0  # Invalid for longs

        if self._allocated_capital <= 0:
            return 0

        risk_per_share = entry_price - stop_price
        risk_dollars = self._allocated_capital * self._orb_config.risk_limits.max_loss_per_trade_pct
        shares = int(risk_dollars / risk_per_share)

        return max(0, shares)

    # -------------------------------------------------------------------------
    # State Management
    # -------------------------------------------------------------------------

    def reset_daily_state(self) -> None:
        """Reset all intraday state for a new trading day."""
        super().reset_daily_state()
        self._symbol_state.clear()
        logger.debug("%s: ORB strategy daily state reset", self.strategy_id)

    def mark_position_closed(self, symbol: str) -> None:
        """Mark a position as closed (called by Order Manager).

        Args:
            symbol: The symbol whose position was closed.
        """
        state = self._symbol_state.get(symbol)
        if state is not None:
            state.position_active = False

    def set_data_service(self, data_service: DataService) -> None:
        """Set the data service for indicator queries.

        Args:
            data_service: The DataService instance.
        """
        self._data_service = data_service
