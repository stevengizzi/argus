"""PatternModule ABC, CandleBar, and PatternDetection dataclasses.

These are the foundational types for the pattern detection system.
PatternModule defines the interface; CandleBar and PatternDetection are
the data containers that flow through it.

CandleBar is intentionally independent of argus.core.events.CandleEvent —
pattern modules are pure detection logic with no Event Bus coupling.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class CandleBar:
    """Immutable OHLCV candle bar for pattern detection.

    Independent of CandleEvent — patterns operate on plain candle data
    without Event Bus coupling.

    Attributes:
        timestamp: Bar timestamp.
        open: Opening price.
        high: High price.
        low: Low price.
        close: Closing price.
        volume: Bar volume.
    """

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class PatternDetection:
    """Result of a successful pattern detection.

    Returned by PatternModule.detect() when a pattern is identified.
    Contains the pattern type, confidence score, entry/stop prices,
    optional pattern-derived targets, and arbitrary metadata.

    Attributes:
        pattern_type: Identifier for the pattern (e.g., "bull_flag").
        confidence: Detection confidence score (0–100).
        entry_price: Suggested entry price.
        stop_price: Suggested stop-loss price.
        target_prices: Pattern-derived profit targets (optional).
        metadata: Pattern-specific context for logging and diagnostics.
    """

    pattern_type: str
    confidence: float
    entry_price: float
    stop_price: float
    target_prices: tuple[float, ...] = ()
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class PatternParam:
    """Structured parameter metadata for pattern modules.

    Provides type, range, and description metadata for parameter grid
    generation, UI display, and sweep automation.

    Attributes:
        name: Parameter name matching the constructor kwarg.
        param_type: Python type (int, float, bool).
        default: Default value for this parameter.
        min_value: Numeric range minimum (None for non-numeric).
        max_value: Numeric range maximum (None for non-numeric).
        step: Grid step size for parameter sweeps (None for non-numeric).
        description: Human-readable description.
        category: Grouping label (detection, scoring, filtering).
    """

    name: str
    param_type: type
    default: Any
    min_value: float | None = None
    max_value: float | None = None
    step: float | None = None
    description: str = ""
    category: str = ""


class PatternModule(ABC):
    """Abstract base class for pattern detection modules.

    Patterns are pure detection logic — they identify chart patterns
    in candle data and score them. They do NOT handle:
    - Operating windows (PatternBasedStrategy handles)
    - Position sizing (Quality Engine + Sizer handles)
    - State management (PatternBasedStrategy handles)
    - Signal generation (PatternBasedStrategy handles)
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name of the pattern."""

    @property
    @abstractmethod
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection.

        PatternBasedStrategy maintains this window per symbol.
        """

    @abstractmethod
    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a pattern in the given candle window.

        Args:
            candles: Recent candle history (most recent last),
                     length <= lookback_bars.
            indicators: Current indicator values (vwap, atr, rvol, etc.)

        Returns:
            PatternDetection if pattern found, None otherwise.
        """

    @abstractmethod
    def score(self, detection: PatternDetection) -> float:
        """Score the quality of a detected pattern (0–100).

        Used as ``pattern_strength`` input to the Quality Engine.

        Scoring-weight convention is deliberately *per-pattern* — different
        patterns warrant different component weightings (FIX-19 P1-B-C04).
        Current splits in use (see each pattern's ``score()`` docstring for
        the authoritative list):

        - ``30/30/25/15`` — BullFlag, FlatTopBreakout, HodBreak
        - ``30/30/20/20`` — GapAndGo
        - ``30/25/25/20`` — MicroPullback, NarrowRangeBreakout, VwapBounce,
          DipAndRip, PreMarketHighBreak
        - ``35/25/20/20`` — ABCD

        Args:
            detection: A previously detected pattern.

        Returns:
            Quality score between 0 and 100.
        """

    @abstractmethod
    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for this pattern.

        Used by Pattern Library UI, BacktestEngine sweep grid generation,
        and parameter documentation.

        Returns:
            List of PatternParam describing each tunable parameter.
        """

    @property
    def min_detection_bars(self) -> int:
        """Minimum candle count before detection is attempted.

        Defaults to lookback_bars for backward compatibility. Override in
        patterns that need a large deque (for historical context) but can
        begin detection with fewer bars.

        PatternBasedStrategy uses lookback_bars for deque maxlen (storage
        capacity) and min_detection_bars for the detection-eligibility check.
        """
        return self.lookback_bars

    def set_reference_data(self, data: dict[str, Any]) -> None:
        """Receive reference data from Universe Manager (prior closes, etc.).

        Default no-op. Override in patterns that need external reference data
        such as prior close prices for gap calculations.

        Args:
            data: Reference data dict. Expected keys include
                  ``prior_closes: dict[str, float]`` when available.
        """
