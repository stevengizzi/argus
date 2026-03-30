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
Sprint 26, Session 3: Entry/exit/pattern strength completion.
"""

from __future__ import annotations

import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import time
from enum import StrEnum
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

from argus.core.clock import Clock
from argus.core.config import RedToGreenConfig
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
    from argus.analytics.trade_logger import TradeLogger
    from argus.data.fmp_reference import SymbolReferenceData
    from argus.data.service import DataService

logger = logging.getLogger(__name__)

# Eastern Time zone for market hours comparisons
ET = ZoneInfo("America/New_York")


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
    recent_volumes: deque[int] = field(default_factory=lambda: deque(maxlen=50))


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

    Entry requires:
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

        # Track volume for all bars
        state.recent_volumes.append(event.volume)

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
            self.record_evaluation(
                symbol,
                EvaluationEventType.CONDITION_CHECK,
                EvaluationResult.FAIL,
                "No prior_close data — cannot compute gap",
                metadata={"condition_name": "prior_close_available", "passed": False},
            )
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

        # Identify candidate levels sorted by proximity
        levels = self._identify_key_levels(symbol, candle, state)

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

    def _identify_key_levels(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
    ) -> list[tuple[KeyLevelType, float]]:
        """Identify candidate key levels sorted by proximity to current price.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.

        Returns:
            List of (level_type, level_price) sorted by proximity to close.
        """
        levels: list[tuple[KeyLevelType, float]] = []

        if state.prior_close > 0:
            levels.append((KeyLevelType.PRIOR_CLOSE, state.prior_close))
        if state.premarket_low > 0:
            levels.append((KeyLevelType.PREMARKET_LOW, state.premarket_low))

        # VWAP from data service (synchronous access via cached indicator)
        if self._data_service is not None:
            try:
                vwap = self._data_service.get_indicator_sync(symbol, "vwap")
                if vwap is not None and vwap > 0:
                    levels.append((KeyLevelType.VWAP, vwap))
            except AttributeError:
                # data_service may not have get_indicator_sync — graceful skip
                pass

        close = candle.close
        levels.sort(key=lambda lv: abs(close - lv[1]) / lv[1] if lv[1] > 0 else float("inf"))

        return levels

    def _handle_testing_level(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
    ) -> tuple[RedToGreenState, SignalEvent | None]:
        """Handle TESTING_LEVEL state — check if level holds and entry criteria met.

        Evaluates operating window, level proximity, volume confirmation,
        and chase protection. Generates SignalEvent on confirmed hold.

        Args:
            symbol: The symbol being processed.
            candle: The current candle.
            state: The symbol's state.

        Returns:
            Tuple of (new_state, signal_or_none).
        """
        close = candle.close
        level_price = state.current_level_price
        proximity_pct = self._r2g_config.level_proximity_pct

        # --- Check if price dropped significantly below level (level failed) ---
        if level_price > 0:
            drop_pct = (level_price - close) / level_price
            if drop_pct > proximity_pct * 3:
                self.record_evaluation(
                    symbol,
                    EvaluationEventType.STATE_TRANSITION,
                    EvaluationResult.INFO,
                    f"Level failed: price dropped {drop_pct * 100:.2f}% below "
                    f"{state.current_level_type} @ {level_price:.2f}",
                    metadata={
                        "drop_pct": round(drop_pct, 6),
                        "level_type": str(state.current_level_type),
                        "level_price": level_price,
                    },
                )

                # Check if we can retry with another level
                if state.level_attempts < self._r2g_config.max_level_attempts:
                    logger.debug(
                        "%s: Level failed, returning to GAP_DOWN_CONFIRMED "
                        "(attempt %d/%d)",
                        symbol,
                        state.level_attempts,
                        self._r2g_config.max_level_attempts,
                    )
                    self.record_evaluation(
                        symbol,
                        EvaluationEventType.STATE_TRANSITION,
                        EvaluationResult.INFO,
                        f"State transition: {RedToGreenState.TESTING_LEVEL} → "
                        f"{RedToGreenState.GAP_DOWN_CONFIRMED}",
                        metadata={
                            "from_state": str(RedToGreenState.TESTING_LEVEL),
                            "to_state": str(RedToGreenState.GAP_DOWN_CONFIRMED),
                            "trigger": "level failed — retry available",
                        },
                    )
                    state.level_test_bars = 0
                    return (RedToGreenState.GAP_DOWN_CONFIRMED, None)

                state.exhaustion_reason = (
                    f"Level failed and max attempts "
                    f"({self._r2g_config.max_level_attempts}) reached"
                )
                logger.info(
                    "%s: TESTING_LEVEL → EXHAUSTED (%s)",
                    symbol,
                    state.exhaustion_reason,
                )
                self.record_evaluation(
                    symbol,
                    EvaluationEventType.STATE_TRANSITION,
                    EvaluationResult.INFO,
                    f"State transition: {RedToGreenState.TESTING_LEVEL} → "
                    f"{RedToGreenState.EXHAUSTED}",
                    metadata={
                        "from_state": str(RedToGreenState.TESTING_LEVEL),
                        "to_state": str(RedToGreenState.EXHAUSTED),
                        "trigger": state.exhaustion_reason,
                    },
                )
                return (RedToGreenState.EXHAUSTED, None)

        # --- Count level test bars (price within proximity of level) ---
        if level_price > 0:
            distance_pct = abs(close - level_price) / level_price
            if distance_pct <= proximity_pct:
                state.level_test_bars += 1

        # --- Check entry conditions ---
        conditions_passed: list[str] = []
        conditions_total = 5

        # Condition 1/5: Operating window
        in_window = self._is_in_entry_window(candle)
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if in_window else EvaluationResult.FAIL,
            f"Condition 1/5: Operating window — "
            f"{'PASS' if in_window else 'FAIL'} "
            f"(window={self._earliest_entry_time}–{self._latest_entry_time})",
            metadata={"condition_name": "operating_window", "passed": in_window},
        )
        if in_window:
            conditions_passed.append("operating_window")
        else:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Entry rejected: outside operating window",
                metadata={
                    "conditions_passed": len(conditions_passed),
                    "conditions_total": conditions_total,
                },
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        # Condition 2/5: Minimum level test bars
        bars_ok = state.level_test_bars >= self._r2g_config.min_level_test_bars
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if bars_ok else EvaluationResult.FAIL,
            f"Condition 2/5: Level test bars — "
            f"{'PASS' if bars_ok else 'FAIL'} "
            f"({state.level_test_bars}/{self._r2g_config.min_level_test_bars})",
            metadata={
                "condition_name": "level_test_bars",
                "value": state.level_test_bars,
                "threshold": self._r2g_config.min_level_test_bars,
                "passed": bars_ok,
            },
        )
        if bars_ok:
            conditions_passed.append("level_test_bars")
        else:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Entry rejected: insufficient level test bars",
                metadata={
                    "conditions_passed": len(conditions_passed),
                    "conditions_total": conditions_total,
                },
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        # Condition 3/5: Candle closes above key level
        closes_above = close > level_price
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if closes_above else EvaluationResult.FAIL,
            f"Condition 3/5: Close above level — "
            f"{'PASS' if closes_above else 'FAIL'} "
            f"(close={close:.2f}, level={level_price:.2f})",
            metadata={
                "condition_name": "close_above_level",
                "value": close,
                "threshold": level_price,
                "passed": closes_above,
            },
        )
        if closes_above:
            conditions_passed.append("close_above_level")
        else:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Entry rejected: close not above level",
                metadata={
                    "conditions_passed": len(conditions_passed),
                    "conditions_total": conditions_total,
                },
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        # Condition 4/5: Volume confirmation
        avg_volume = (
            sum(state.recent_volumes) / len(state.recent_volumes)
            if state.recent_volumes
            else float(candle.volume)
        )
        required_volume = avg_volume * self._r2g_config.volume_confirmation_multiplier
        volume_ratio = candle.volume / avg_volume if avg_volume > 0 else 0.0
        volume_ok = candle.volume >= required_volume
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if volume_ok else EvaluationResult.FAIL,
            f"Condition 4/5: Volume confirmation — "
            f"{'PASS' if volume_ok else 'FAIL'} "
            f"(rvol={volume_ratio:.1f}x, threshold="
            f"{self._r2g_config.volume_confirmation_multiplier}x)",
            metadata={
                "condition_name": "volume_confirmation",
                "value": candle.volume,
                "threshold": required_volume,
                "volume_ratio": round(volume_ratio, 4),
                "passed": volume_ok,
            },
        )
        if volume_ok:
            conditions_passed.append("volume_confirmation")
        else:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Entry rejected: insufficient volume",
                metadata={
                    "conditions_passed": len(conditions_passed),
                    "conditions_total": conditions_total,
                },
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        # Condition 5/5: Chase guard
        chase_limit = level_price * (1 + self._r2g_config.max_chase_pct)
        chase_ok = close <= chase_limit
        self.record_evaluation(
            symbol,
            EvaluationEventType.CONDITION_CHECK,
            EvaluationResult.PASS if chase_ok else EvaluationResult.FAIL,
            f"Condition 5/5: Chase guard — "
            f"{'PASS' if chase_ok else 'FAIL'} "
            f"(close={close:.2f}, limit={chase_limit:.2f})",
            metadata={
                "condition_name": "chase_guard",
                "value": close,
                "threshold": chase_limit,
                "passed": chase_ok,
            },
        )
        if chase_ok:
            conditions_passed.append("chase_guard")
        else:
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                "Entry rejected: chase protection triggered",
                metadata={
                    "conditions_passed": len(conditions_passed),
                    "conditions_total": conditions_total,
                },
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        # All conditions pass — emit entry evaluation
        self.record_evaluation(
            symbol,
            EvaluationEventType.ENTRY_EVALUATION,
            EvaluationResult.PASS,
            f"All {conditions_total} entry conditions passed",
            metadata={
                "conditions_passed": len(conditions_passed),
                "conditions_total": conditions_total,
                "passed_conditions": conditions_passed,
            },
        )

        # Concurrent positions check (0 = disabled)
        max_positions = self._r2g_config.risk_limits.max_concurrent_positions
        if max_positions > 0:
            active_positions = sum(
                1
                for s in self._symbol_states.values()
                if s.state == RedToGreenState.ENTERED
            )
            if active_positions >= max_positions:
                self.record_evaluation(
                    symbol,
                    EvaluationEventType.ENTRY_EVALUATION,
                    EvaluationResult.FAIL,
                    f"Concurrent position limit: {active_positions}/{max_positions}",
                )
                return (RedToGreenState.TESTING_LEVEL, None)

        # Build signal
        return self._build_signal(symbol, candle, state, volume_ratio)

    def _calculate_pattern_strength(
        self,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
        level_type: KeyLevelType,
        volume_ratio: float,
    ) -> tuple[float, dict[str, object]]:
        """Calculate Red-to-Green pattern strength (0–100) and context dict.

        Scoring components (weighted):
        - Level type quality (base points): VWAP=35, PRIOR_CLOSE=30, PREMARKET_LOW=25
        - Volume ratio: (volume_ratio / volume_confirmation_multiplier) × 25, cap 25
        - Gap magnitude: smaller gaps (2–4%) score higher than large (8–10%), up to 20
        - Level test quality: more test bars = stronger, up to 20

        Args:
            candle: The entry candle.
            state: The symbol's state.
            level_type: The type of key level being reclaimed.
            volume_ratio: Ratio of candle volume to average volume.

        Returns:
            Tuple of (pattern_strength 0–100, signal_context dict).
        """
        # --- Level type quality (base points) ---
        level_base_points: dict[KeyLevelType, float] = {
            KeyLevelType.VWAP: 35.0,
            KeyLevelType.PRIOR_CLOSE: 30.0,
            KeyLevelType.PREMARKET_LOW: 25.0,
        }
        level_credit = level_base_points.get(level_type, 25.0)

        # --- Volume ratio (up to 25 points) ---
        multiplier = self._r2g_config.volume_confirmation_multiplier
        volume_credit = (volume_ratio / multiplier) * 25.0 if multiplier > 0 else 12.5
        volume_credit = min(25.0, volume_credit)

        # --- Gap magnitude (up to 20 points) ---
        # Smaller gaps (2–4%) score higher; large gaps (8–10%) score lower
        abs_gap = abs(state.gap_pct)
        if abs_gap <= 0.04:
            gap_credit = 20.0
        elif abs_gap <= 0.06:
            gap_credit = 20.0 - (abs_gap - 0.04) / 0.02 * 5.0
        elif abs_gap <= 0.08:
            gap_credit = 15.0 - (abs_gap - 0.06) / 0.02 * 5.0
        else:
            gap_credit = 10.0

        # --- Level test quality (up to 20 points) ---
        # More bars testing = stronger confirmation
        min_bars = self._r2g_config.min_level_test_bars
        test_ratio = state.level_test_bars / min_bars if min_bars > 0 else 1.0
        level_test_credit = min(20.0, test_ratio * 10.0)

        pattern_strength = level_credit + volume_credit + gap_credit + level_test_credit
        pattern_strength = max(0.0, min(100.0, pattern_strength))

        signal_context: dict[str, object] = {
            "level_type": str(level_type),
            "level_price": state.current_level_price,
            "level_credit": round(level_credit, 2),
            "volume_ratio": round(volume_ratio, 4),
            "volume_credit": round(volume_credit, 2),
            "gap_pct": round(abs_gap, 6),
            "gap_credit": round(gap_credit, 2),
            "level_test_bars": state.level_test_bars,
            "level_test_credit": round(level_test_credit, 2),
            "level_attempts": state.level_attempts,
        }

        self.record_evaluation(
            candle.symbol,
            EvaluationEventType.QUALITY_SCORED,
            EvaluationResult.INFO,
            f"R2G pattern strength: {pattern_strength:.1f}",
            metadata=signal_context,
        )

        return pattern_strength, signal_context

    def _build_signal(
        self,
        symbol: str,
        candle: CandleEvent,
        state: RedToGreenSymbolState,
        volume_ratio: float,
    ) -> tuple[RedToGreenState, SignalEvent | None]:
        """Build a SignalEvent for R2G entry.

        Args:
            symbol: The symbol to trade.
            candle: The entry candle.
            state: The symbol's state.
            volume_ratio: Ratio of candle volume to average volume.

        Returns:
            Tuple of (ENTERED state, SignalEvent).
        """
        level_type = state.current_level_type or KeyLevelType.PRIOR_CLOSE
        level_price = state.current_level_price

        entry_price = candle.close
        stop_price = level_price - (level_price * self._r2g_config.stop_buffer_pct)
        risk_per_share = entry_price - stop_price

        if risk_per_share <= 0:
            logger.warning(
                "%s: Invalid risk (entry=%.2f, stop=%.2f), skipping signal",
                symbol,
                entry_price,
                stop_price,
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        t1 = entry_price + 1.0 * risk_per_share
        t2 = entry_price + 2.0 * risk_per_share

        # Zero-R guard: suppress signals with no profit potential
        if self._has_zero_r(symbol, entry_price, t1):
            self.record_evaluation(
                symbol,
                EvaluationEventType.ENTRY_EVALUATION,
                EvaluationResult.FAIL,
                f"Zero R: entry={entry_price:.2f}, target={t1:.2f}",
            )
            return (RedToGreenState.TESTING_LEVEL, None)

        pattern_strength, signal_context = self._calculate_pattern_strength(
            candle, state, level_type, volume_ratio,
        )

        signal = SignalEvent(
            strategy_id=self.strategy_id,
            symbol=symbol,
            side=Side.LONG,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            share_count=0,
            pattern_strength=pattern_strength,
            signal_context=signal_context,
            time_stop_seconds=self._r2g_config.time_stop_minutes * 60,
            rationale=f"R2G: {level_type.value} reclaim on {symbol}",
            atr_value=None,  # No async IndicatorEngine access in sync _build_signal — trail falls back to percent mode
        )

        self.record_evaluation(
            symbol,
            EvaluationEventType.SIGNAL_GENERATED,
            EvaluationResult.PASS,
            f"R2G signal: {symbol} entry at {entry_price:.2f}",
            metadata={
                "entry": entry_price,
                "stop": stop_price,
                "t1": t1,
                "t2": t2,
                "pattern_strength": round(pattern_strength, 2),
            },
        )

        self.record_evaluation(
            symbol,
            EvaluationEventType.STATE_TRANSITION,
            EvaluationResult.INFO,
            f"State transition: {RedToGreenState.TESTING_LEVEL} → "
            f"{RedToGreenState.ENTERED}",
            metadata={
                "from_state": str(RedToGreenState.TESTING_LEVEL),
                "to_state": str(RedToGreenState.ENTERED),
                "trigger": "signal generated — all conditions passed",
            },
        )

        logger.info(
            "%s: R2G signal - entry=%.2f, stop=%.2f, T1=%.2f, T2=%.2f, "
            "pattern_strength=%.1f, level=%s",
            symbol,
            entry_price,
            stop_price,
            t1,
            t2,
            pattern_strength,
            level_type,
        )

        return (RedToGreenState.ENTERED, signal)

    async def on_tick(self, event: TickEvent) -> None:
        """Process a tick event (no-op for R2G V1 — uses candles).

        Position management is handled by Order Manager.
        """
        pass

    def get_scanner_criteria(self) -> ScannerCriteria:
        """Return scanner criteria for Red-to-Green stock selection.

        Scans for gap-down stocks with sufficient volume and price range.
        Uses negative min_gap_pct to indicate gap-down requirement.

        Returns:
            ScannerCriteria targeting gap-down stocks.
        """
        uf = self._r2g_config.universe_filter
        return ScannerCriteria(
            min_price=uf.min_price if uf else 5.0,
            max_price=uf.max_price if uf else 200.0,
            min_volume_avg_daily=uf.min_avg_volume if uf else 500_000,
            min_gap_pct=-self._r2g_config.min_gap_down_pct,
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

        Stop placed below the key level with a buffer. Targets at configured
        R-multiples.

        Returns:
            ExitRules with R2G-specific targets and time stop.
        """
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

        R2G works in bullish trending (gap-down reversal in strong market)
        and range-bound conditions. Avoid extreme volatility environments.

        Returns:
            MarketConditionsFilter with allowed regimes.
        """
        return MarketConditionsFilter(
            allowed_regimes=["bullish_trending", "bearish_trending", "range_bound"],
            max_vix=35.0,
        )

    # -------------------------------------------------------------------------
    # Prior Close Initialization
    # -------------------------------------------------------------------------

    def initialize_prior_closes(
        self,
        reference_data: dict[str, SymbolReferenceData],
    ) -> int:
        """Populate prior_close for watchlist symbols from cached reference data.

        Uses the Universe Manager's already-cached FMP reference data
        (SymbolReferenceData.prev_close) — zero additional API calls.

        Args:
            reference_data: Mapping of symbol → SymbolReferenceData from
                the Universe Manager's reference cache.

        Returns:
            Number of symbols successfully initialized.
        """
        initialized = 0
        for symbol in self._watchlist:
            ref = reference_data.get(symbol)
            if ref is None or ref.prev_close is None or ref.prev_close <= 0:
                continue
            state = self._get_symbol_state(symbol)
            state.prior_close = ref.prev_close
            initialized += 1

        if initialized > 0:
            logger.info(
                "%s: Initialized prior_close for %d/%d watchlist symbols",
                self.strategy_id,
                initialized,
                len(self._watchlist),
            )
        else:
            logger.warning(
                "%s: Could not initialize prior_close for any of %d symbols",
                self.strategy_id,
                len(self._watchlist),
            )

        return initialized

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

        Queries today's completed trades for this strategy. Symbols with
        completed trades are marked EXHAUSTED (already traded today).
        Open positions are tracked by Order Manager, not TradeLogger;
        the orchestrator's position reconciliation handles ENTERED state.

        Args:
            trade_logger: TradeLogger instance for database queries.
        """
        await super().reconstruct_state(trade_logger)

        today = self._clock.today()
        my_trades = await trade_logger.get_trades_by_date(
            today, strategy_id=self.strategy_id
        )

        for trade in my_trades:
            symbol = trade.symbol
            state = self._get_symbol_state(symbol)
            state.state = RedToGreenState.EXHAUSTED
            state.exhaustion_reason = "already traded today (reconstructed)"

        if my_trades:
            symbols = [t.symbol for t in my_trades]
            logger.info(
                "%s: Reconstructed %d traded symbols as EXHAUSTED: %s",
                self.strategy_id,
                len(symbols),
                ", ".join(symbols),
            )

    def set_data_service(self, data_service: DataService) -> None:
        """Set the data service for indicator queries.

        Args:
            data_service: The DataService instance.
        """
        self._data_service = data_service
