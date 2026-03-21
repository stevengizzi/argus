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

        Used as pattern_strength input to Quality Engine.

        Args:
            detection: A previously detected pattern.

        Returns:
            Quality score between 0 and 100.
        """

    @abstractmethod
    def get_default_params(self) -> dict[str, object]:
        """Return default parameter values for this pattern.

        Used by Pattern Library UI and future BacktestEngine.

        Returns:
            Dictionary of parameter names to default values.
        """
