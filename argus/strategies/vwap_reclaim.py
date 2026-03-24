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
from argus.strategies.telemetry import EvaluationEventType, EvaluationResult

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

    # Transition counter: incremented each time we enter BELOW_VWAP state
    # (includes first entry and any re-entries after resets)
    below_vwap_entries: int = 0


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
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"Symbol in terminal state: {state.state}",
            )
            return None

        # Time window check — outside operating window
        if not self._is_in_entry_window(event):
            self.record_evaluation(
                symbol,
                EvaluationEventType.TIME_WINDOW_CHECK,
                EvaluationResult.FAIL,
                "Outside VWAP Reclaim operating window",
            )

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

        # Emit VWAP distance for every candle in the state machine
        vwap_distance = close - vwap
        vwap_distance_pct = vwap_distance / vwap if vwap > 0 else 0.0
        self.record_evaluation(
            symbol,
            EvaluationEventType.INDICATOR_STATUS,
            EvaluationResult.INFO,
            f"VWAP distance: {vwap_distance:.4f} ({vwap_distance_pct * 100:.2f}%)",
            metadata={"vwap": vwap, "price": close, "distance_pct": round(vwap_distance_pct, 6)},
        )

        if state.state == VwapState.WATCHING:
            # Transition to ABOVE_VWAP when close > VWAP
            if close > vwap:
                state.state = VwapState.ABOVE_VWAP
                self.record_evaluation(
                    symbol,
                    EvaluationEventType.STATE_TRANSITION,
                    EvaluationResult.INFO,
                    f"State transition: {VwapState.WATCHING} → {VwapState.ABOVE_VWAP}",
                    metadata={
                        "from_state": str(VwapState.WATCHING),
                        "to_state": str(VwapState.ABOVE_VWAP),
                        "trigger": "price crossed above VWAP",
                    },
                )
                logger.debug(
                    "%s: WATCHING → ABOVE_VWAP (close=%.2f > vwap=%.2f)",
                    symbol,
                    close,
                    vwap,
                )
            return None

        if state.state == VwapState.ABOVE_VWAP:
            # Note: Uses <= (not <) to match VectorBT sweep behavior.
            # When close == VWAP exactly, we begin pullback tracking.
            # See DEC-148.
            if close <= vwap:
                # Start tracking pullback
                state.state = VwapState.BELOW_VWAP
                state.pullback_low = candle.low
                state.bars_below_vwap = 1
                state.below_vwap_entries += 1
                self.record_evaluation(
                    symbol,
                    EvaluationEventType.STATE_TRANSITION,
                    EvaluationResult.INFO,
                    f"State transition: {VwapState.ABOVE_VWAP} → {VwapState.BELOW_VWAP}",
                    metadata={
                        "from_state": str(VwapState.ABOVE_VWAP),
                        "to_state": str(VwapState.BELOW_VWAP),
                        "trigger": "price pulled back below VWAP",
                    },
                )
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
            self.record_evaluation(
                symbol,
                EvaluationEventType.STATE_TRANSITION,
                EvaluationResult.INFO,
                f"State transition: {VwapState.BELOW_VWAP} → {VwapState.EXHAUSTED}",
                metadata={
                    "from_state": str(VwapState.BELOW_VWAP),
                    "to_state": str(VwapState.EXHAUSTED),
                    "trigger": "exhaustion — pullback too deep",
                },
            )
            logger.info(
                "%s: BELOW_VWAP → EXHAUSTED (pullback %.2f%% > max %.2f%%)",
                symbol,
                pullback_depth * 100,
                self._vwap_config.max_pullback_pct * 100,
            )
            return None

        if close <= vwap:
            # Still at or below VWAP, increment bar count
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
        in_window = self._is_in_entry_window(candle)
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if in_window else EvaluationResult.FAIL,
            f"Time window: {'PASS' if in_window else 'FAIL'} "
            f"(window={self._earliest_entry_time}–{self._latest_entry_time})",
            metadata={"condition_name": "time_window", "passed": in_window},
        )
        if not in_window:
            # Reclaim but outside time window — allow retry by going back to ABOVE_VWAP
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Reclaim outside time window, reset to ABOVE_VWAP", symbol)
            return None

        # 2. Internal risk limits
        risk_ok = self.check_internal_risk_limits()
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if risk_ok else EvaluationResult.FAIL,
            f"Internal risk limits: {'PASS' if risk_ok else 'FAIL'}",
            metadata={"condition_name": "internal_risk_limits", "passed": risk_ok},
        )
        if not risk_ok:
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Internal risk limits hit, reset to ABOVE_VWAP", symbol)
            return None

        # 3. Concurrent positions check (0 = disabled)
        max_positions = self._vwap_config.risk_limits.max_concurrent_positions
        if max_positions > 0:
            active_positions = sum(
                1 for s in self._symbol_state.values() if s.position_active
            )
            positions_ok = active_positions < max_positions
        else:
            active_positions = 0
            positions_ok = True
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if positions_ok else EvaluationResult.FAIL,
            f"Concurrent positions: {'PASS' if positions_ok else 'FAIL'} "
            f"({active_positions}/{max_positions})",
            metadata={
                "condition_name": "concurrent_positions",
                "value": active_positions,
                "threshold": max_positions,
                "passed": positions_ok,
            },
        )
        if not positions_ok:
            state.state = VwapState.ABOVE_VWAP
            state.bars_below_vwap = 0
            state.pullback_low = None
            logger.debug("%s: Max positions reached, reset to ABOVE_VWAP", symbol)
            return None

        # 4. Pullback depth check (minimum pullback required)
        if state.pullback_low is None:
            return None
        pullback_depth = (vwap - state.pullback_low) / vwap
        depth_ok = pullback_depth >= self._vwap_config.min_pullback_pct
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if depth_ok else EvaluationResult.FAIL,
            f"Pullback depth: {'PASS' if depth_ok else 'FAIL'} "
            f"({pullback_depth * 100:.2f}% vs min {self._vwap_config.min_pullback_pct * 100:.2f}%)",
            metadata={
                "condition_name": "pullback_depth",
                "value": round(pullback_depth, 6),
                "threshold": self._vwap_config.min_pullback_pct,
                "passed": depth_ok,
            },
        )
        if not depth_ok:
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
        bars_ok = state.bars_below_vwap >= self._vwap_config.min_pullback_bars
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if bars_ok else EvaluationResult.FAIL,
            f"Pullback bars: {'PASS' if bars_ok else 'FAIL'} "
            f"({state.bars_below_vwap} vs min {self._vwap_config.min_pullback_bars})",
            metadata={
                "condition_name": "pullback_bars",
                "value": state.bars_below_vwap,
                "threshold": self._vwap_config.min_pullback_bars,
                "passed": bars_ok,
            },
        )
        if not bars_ok:
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
            rvol = candle.volume / avg_volume if avg_volume > 0 else 0.0
            volume_ok = candle.volume >= required_volume
            self.record_evaluation(
                symbol,
                EvaluationEventType.CONDITION_CHECK,
                EvaluationResult.PASS if volume_ok else EvaluationResult.FAIL,
                f"Volume confirmation: {'PASS' if volume_ok else 'FAIL'} "
                f"(rvol={rvol:.1f}x, threshold="
                f"{self._vwap_config.volume_confirmation_multiplier}x)",
                metadata={
                    "condition_name": "volume_confirmation",
                    "value": candle.volume,
                    "threshold": required_volume,
                    "passed": volume_ok,
                },
            )
            if not volume_ok:
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
        chase_ok = close <= chase_limit
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if chase_ok else EvaluationResult.FAIL,
            f"Chase protection: {'PASS' if chase_ok else 'FAIL'} "
            f"(close={close:.2f}, limit={chase_limit:.2f})",
            metadata={
                "condition_name": "chase_protection",
                "value": close,
                "threshold": chase_limit,
                "passed": chase_ok,
            },
        )
        if not chase_ok:
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

    def _calculate_pattern_strength(
        self,
        candle: CandleEvent,
        state: VwapSymbolState,
        vwap: float,
    ) -> tuple[float, dict]:
        """Calculate VWAP Reclaim pattern strength (0-100) and context dict.

        Scoring factors:
        - State machine path quality (30%): clean path scores highest.
        - Pullback depth (25%): parabolic curve peaking at 0.4× of max_pullback_pct.
        - Reclaim volume (25%): reclaim candle vs avg pullback window volume.
        - Distance to VWAP (20%): tighter to VWAP at reclaim = better.

        Args:
            candle: The reclaim candle.
            state: The symbol's VWAP state.
            vwap: The current VWAP value.

        Returns:
            Tuple of (pattern_strength, signal_context).
        """
        # --- State machine path quality (30%) ---
        # Clean first-attempt path = 85. Each additional BELOW_VWAP entry reduces quality.
        below_vwap_entries = state.below_vwap_entries
        if below_vwap_entries <= 1:
            path_credit = 85.0
            path_quality = "clean"
        elif below_vwap_entries == 2:
            path_credit = 60.0
            path_quality = "retested"
        elif below_vwap_entries == 3:
            path_credit = 50.0
            path_quality = "choppy"
        else:
            path_credit = 40.0
            path_quality = "extended"

        # --- Pullback depth (25%) ---
        # Normalized by max_pullback_pct. Optimal 0.3-0.5× = 80. Parabolic peak at 0.4×.
        if state.pullback_low is not None and vwap > 0 and self._vwap_config.max_pullback_pct > 0:
            raw_depth = (vwap - state.pullback_low) / vwap
            pullback_depth_ratio = raw_depth / self._vwap_config.max_pullback_pct
        else:
            pullback_depth_ratio = 0.4  # neutral

        depth_credit = 80.0 - 1125.0 * (pullback_depth_ratio - 0.4) ** 2
        depth_credit = max(35.0, min(80.0, depth_credit))

        # --- Reclaim volume (25%) ---
        # Ratio = reclaim candle volume / avg pullback window volume.
        # >1.5× = 80, 1.0× = 50, <0.8× = 30. Piecewise linear.
        if state.bars_below_vwap > 0 and len(state.recent_volumes) > state.bars_below_vwap:
            pullback_vols = state.recent_volumes[-(state.bars_below_vwap + 1):-1]
        else:
            pullback_vols = state.recent_volumes[:-1] if len(state.recent_volumes) > 1 else []

        avg_pullback_volume = (
            sum(pullback_vols) / len(pullback_vols) if pullback_vols else float(candle.volume)
        )
        reclaim_volume_ratio = (
            candle.volume / avg_pullback_volume if avg_pullback_volume > 0 else 1.0
        )

        if reclaim_volume_ratio < 0.8:
            volume_credit = 30.0
        elif reclaim_volume_ratio <= 1.0:
            volume_credit = 30.0 + (reclaim_volume_ratio - 0.8) / 0.2 * 20.0
        elif reclaim_volume_ratio <= 1.5:
            volume_credit = 50.0 + (reclaim_volume_ratio - 1.0) / 0.5 * 30.0
        else:
            volume_credit = 80.0

        # --- Distance to VWAP (20%) ---
        # At VWAP = 90, 0.5% away = 60, >1% away = 40. Piecewise linear.
        vwap_distance_pct = (candle.close - vwap) / vwap if vwap > 0 else 0.0

        if vwap_distance_pct <= 0.0:
            distance_credit = 90.0
        elif vwap_distance_pct <= 0.005:
            distance_credit = 90.0 - 6000.0 * vwap_distance_pct
        elif vwap_distance_pct <= 0.01:
            distance_credit = 60.0 - 4000.0 * (vwap_distance_pct - 0.005)
        else:
            distance_credit = 40.0

        pattern_strength = (
            0.30 * path_credit
            + 0.25 * depth_credit
            + 0.25 * volume_credit
            + 0.20 * distance_credit
        )
        pattern_strength = max(0.0, min(100.0, pattern_strength))

        signal_context: dict = {
            "path_quality": path_quality,
            "pullback_depth_ratio": round(pullback_depth_ratio, 4),
            "reclaim_volume_ratio": round(reclaim_volume_ratio, 4),
            "vwap_distance_pct": round(vwap_distance_pct, 6),
            "path_credit": round(path_credit, 2),
            "depth_credit": round(depth_credit, 2),
            "volume_credit": round(volume_credit, 2),
            "distance_credit": round(distance_credit, 2),
        }

        self.record_evaluation(
            candle.symbol,
            EvaluationEventType.QUALITY_SCORED,
            EvaluationResult.INFO,
            f"VWAP Reclaim pattern strength: {pattern_strength:.1f}",
            metadata=signal_context,
        )

        return pattern_strength, signal_context

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

        # Calculate pattern strength (share_count deferred to Dynamic Sizer, Sprint 24 S6a)
        pattern_strength, signal_context = self._calculate_pattern_strength(candle, state, vwap)

        # Build signal
        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            share_count=0,
            rationale=(
                f"VWAP Reclaim: {symbol} reclaimed VWAP {vwap:.2f} after pullback to "
                f"{state.pullback_low:.2f} ({state.bars_below_vwap} bars below)"
            ),
            time_stop_seconds=self._vwap_config.time_stop_minutes * 60,
            pattern_strength=pattern_strength,
            signal_context=signal_context,
        )

        # Emit SIGNAL_GENERATED before state transition
        self.record_evaluation(
            symbol,
            EvaluationEventType.SIGNAL_GENERATED,
            EvaluationResult.PASS,
            f"VWAP Reclaim signal: {symbol} entry at {entry_price:.2f}",
            metadata={
                "entry": entry_price,
                "stop": stop_price,
                "t1": t1,
                "t2": t2,
                "pattern_strength": round(pattern_strength, 2),
            },
        )

        # Mark state as entered
        state.state = VwapState.ENTERED
        state.position_active = True

        self.record_evaluation(
            symbol,
            EvaluationEventType.STATE_TRANSITION,
            EvaluationResult.INFO,
            f"State transition: {VwapState.BELOW_VWAP} → {VwapState.ENTERED}",
            metadata={
                "from_state": str(VwapState.BELOW_VWAP),
                "to_state": str(VwapState.ENTERED),
                "trigger": "signal generated — all conditions passed",
            },
        )

        logger.info(
            "%s: VWAP reclaim signal - entry=%.2f, stop=%.2f, T1=%.2f, T2=%.2f, "
            "pattern_strength=%.1f",
            symbol,
            entry_price,
            stop_price,
            t1,
            t2,
            pattern_strength,
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
            allowed_regimes=["bullish_trending", "bearish_trending", "range_bound", "high_volatility"],
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
