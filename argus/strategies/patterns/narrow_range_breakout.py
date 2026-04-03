"""Narrow Range Breakout pattern detection module.

Detects consolidation via progressively narrowing bar ranges. After
min_narrowing_bars of range contraction within a tight ATR band, a
breakout candle closes above the consolidation high with a volume surge.

The pattern is purely about volatility compression → expansion. It is
distinct from:
  - HOD Break (requires session high proximity)
  - Flat-Top (requires flat resistance)
  NRB only requires that consecutive bar ranges shrink, then expand.

Long-only: downward breakouts (close below consolidation low) are rejected.
Operating window: 10:00 AM – 15:00 ET (enforced by PatternBasedStrategy).
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class NarrowRangeBreakoutPattern(PatternModule):
    """Detect volatility-compression breakout patterns.

    Pattern anatomy:
        1. Narrowing sequence: within the most recent nr_lookback bars (excluding
           the breakout bar), find the longest consecutive run where
           range(i) ≤ range(i-1) × range_decay_tolerance.  The run must end at
           the bar immediately before the breakout bar.
        2. Consolidation quality: max(highs) − min(lows) of the narrowing bars
           must not exceed consolidation_max_range_atr × ATR.
        3. Breakout bar (candles[-1]): close > consolidation_high + margin.
        4. Volume confirmation: breakout bar volume ≥ min_breakout_volume_ratio
           × average volume of the narrowing bars.
        5. Entry: close of the breakout bar.
        6. Stop: consolidation_low − ATR × stop_buffer_atr_mult.

    ATR is taken from indicators["atr"] when available; falls back to a
    self-contained ATR(14) computation (matches PMH / HOD Break patterns).

    Args:
        nr_lookback: Bars to scan for narrowing range sequence (excludes breakout bar).
        min_narrowing_bars: Min consecutive bars with decreasing range.
        range_decay_tolerance: range(i) ≤ range(i-1) × tolerance (5% noise allowed).
        breakout_margin_percent: Min close excess above consolidation high.
        min_breakout_volume_ratio: Breakout bar volume / avg consolidation volume.
        consolidation_max_range_atr: Max overall consolidation range as ATR multiple.
        stop_buffer_atr_mult: ATR mult for stop below consolidation low.
        target_ratio: Target distance ratio (kept for sweep grid compatibility).
        target_1_r: First target R-multiple.
        target_2_r: Second target R-multiple.
        min_score_threshold: Min confidence to emit detection (0 = all).
    """

    def __init__(
        self,
        nr_lookback: int = 7,
        min_narrowing_bars: int = 3,
        range_decay_tolerance: float = 1.05,
        breakout_margin_percent: float = 0.001,
        min_breakout_volume_ratio: float = 1.5,
        consolidation_max_range_atr: float = 0.8,
        stop_buffer_atr_mult: float = 0.5,
        target_ratio: float = 2.0,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        min_score_threshold: float = 0.0,
    ) -> None:
        self._nr_lookback = nr_lookback
        self._min_narrowing_bars = min_narrowing_bars
        self._range_decay_tolerance = range_decay_tolerance
        self._breakout_margin_percent = breakout_margin_percent
        self._min_breakout_volume_ratio = min_breakout_volume_ratio
        self._consolidation_max_range_atr = consolidation_max_range_atr
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._min_score_threshold = min_score_threshold

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Narrow Range Breakout"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 20

    @property
    def min_detection_bars(self) -> int:
        """Minimum candle count before detection is attempted.

        Only min_narrowing_bars + 1 (breakout bar) are strictly required.
        lookback_bars=20 is the deque capacity; detection begins once the
        minimum viable window is available.
        """
        return self._min_narrowing_bars + 1

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a narrow range breakout pattern in the given candle window.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values; "atr" used when available.

        Returns:
            PatternDetection if pattern found, None otherwise.
        """
        atr = indicators.get("atr", 0.0)
        if atr <= 0:
            atr = self._compute_atr(candles)
        if atr <= 0:
            return None

        if len(candles) < self.min_detection_bars:
            return None

        # Breakout bar: the most recent candle
        breakout_bar = candles[-1]

        # Narrowing window: the previous nr_lookback bars (excluding breakout bar)
        window_start = max(0, len(candles) - self._nr_lookback - 1)
        window = candles[window_start:-1]

        if len(window) < self._min_narrowing_bars:
            return None

        # Find longest consecutive narrowing run ending at window[-1]
        longest_run = self._find_narrowing_run_length(window)
        if longest_run < self._min_narrowing_bars:
            return None

        # Consolidation zone: the narrowing bars (ending at window[-1])
        narrowing_bars = window[-longest_run:]
        consolidation_high = max(c.high for c in narrowing_bars)
        consolidation_low = min(c.low for c in narrowing_bars)
        consol_range = consolidation_high - consolidation_low

        # Validate consolidation tightness
        if consol_range > self._consolidation_max_range_atr * atr:
            return None

        # Long-only gate: reject downward breakout
        if breakout_bar.close < consolidation_low:
            return None

        # Breakout confirmation: close must clear consolidation high by margin
        min_breakout_price = consolidation_high * (1.0 + self._breakout_margin_percent)
        if breakout_bar.close <= min_breakout_price:
            return None

        # Volume confirmation: breakout bar vs avg consolidation volume
        avg_consol_volume = sum(c.volume for c in narrowing_bars) / len(narrowing_bars)
        if avg_consol_volume <= 0:
            return None

        breakout_volume_ratio = breakout_bar.volume / avg_consol_volume
        if breakout_volume_ratio < self._min_breakout_volume_ratio:
            return None

        # Entry, stop, targets
        entry_price = breakout_bar.close
        stop_price = consolidation_low - atr * self._stop_buffer_atr_mult

        if stop_price >= entry_price:
            return None

        risk = entry_price - stop_price
        if risk <= 0:
            return None

        target_1 = entry_price + risk * self._target_1_r
        target_2 = entry_price + risk * self._target_2_r

        consolidation_range_atr_ratio = consol_range / atr
        breakout_margin = (breakout_bar.close - consolidation_high) / max(consolidation_high, 1e-9)

        confidence = self._compute_confidence(
            narrowing_bar_count=longest_run,
            consolidation_range_atr_ratio=consolidation_range_atr_ratio,
            breakout_margin=breakout_margin,
            breakout_volume_ratio=breakout_volume_ratio,
        )

        if confidence < self._min_score_threshold:
            return None

        return PatternDetection(
            pattern_type="narrow_range_breakout",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_1, target_2),
            metadata={
                "narrowing_bar_count": longest_run,
                "consolidation_range": round(consol_range, 4),
                "consolidation_range_atr_ratio": round(consolidation_range_atr_ratio, 4),
                "breakout_margin": round(breakout_margin, 4),
                "breakout_volume_ratio": round(breakout_volume_ratio, 2),
                "consolidation_high": round(consolidation_high, 4),
                "consolidation_low": round(consolidation_low, 4),
                "atr": round(atr, 4),
            },
        )

    def _find_narrowing_run_length(self, window: list[CandleBar]) -> int:
        """Count consecutive bars of narrowing range ending at window[-1].

        Traverses backward from the last bar, checking that each bar's range
        is ≤ the preceding bar's range × range_decay_tolerance.  Returns the
        run length (at minimum 1 for the last bar alone).

        Args:
            window: Candle bars (oldest first) excluding the breakout bar.

        Returns:
            Length of the narrowing run ending at the last window bar.
        """
        if len(window) < 2:
            return len(window)

        ranges = [c.high - c.low for c in window]
        n = len(ranges)
        run_length = 1

        for i in range(n - 1, 0, -1):
            if ranges[i] <= ranges[i - 1] * self._range_decay_tolerance:
                run_length += 1
            else:
                break

        return run_length

    def _compute_atr(self, candles: list[CandleBar]) -> float:
        """Compute Average True Range from candle data.

        Uses the standard ATR(14) formula. Falls back to simple high-low
        average when fewer than 14 candles available.

        Args:
            candles: Candle bars for ATR computation.

        Returns:
            ATR value, or 0.0 if insufficient data.
        """
        if len(candles) < 2:
            return 0.0

        true_ranges: list[float] = []
        for i in range(1, len(candles)):
            high_low = candles[i].high - candles[i].low
            high_prev_close = abs(candles[i].high - candles[i - 1].close)
            low_prev_close = abs(candles[i].low - candles[i - 1].close)
            true_ranges.append(max(high_low, high_prev_close, low_prev_close))

        if not true_ranges:
            return 0.0

        period = min(14, len(true_ranges))
        return sum(true_ranges[-period:]) / period

    def _compute_confidence(
        self,
        narrowing_bar_count: int,
        consolidation_range_atr_ratio: float,
        breakout_margin: float,
        breakout_volume_ratio: float,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Weighting: consolidation_quality (30) / breakout_strength (25) /
                   volume_profile (25) / range_context (20).

        Args:
            narrowing_bar_count: Number of consecutive narrowing bars.
            consolidation_range_atr_ratio: Consolidation range / ATR (lower = tighter).
            breakout_margin: Fractional excess of close above consolidation high.
            breakout_volume_ratio: Breakout bar volume / avg consolidation volume.

        Returns:
            Confidence score 0–100.
        """
        max_atr_ratio = max(self._consolidation_max_range_atr, 1e-9)

        # Tightness score: lower range/ATR ratio = tighter consolidation = better
        tightness = max(0.0, 1.0 - consolidation_range_atr_ratio / max_atr_ratio)

        # Consolidation quality (30): more narrowing bars + tighter range
        max_extra_bars = max(1, self._nr_lookback - self._min_narrowing_bars)
        count_score = min(1.0, (narrowing_bar_count - self._min_narrowing_bars) / max_extra_bars)
        consol_quality_score = (count_score * 0.5 + tightness * 0.5) * 30.0

        # Breakout strength (25): margin above consolidation high
        max_margin = self._breakout_margin_percent * 10.0
        margin_score = min(1.0, breakout_margin / max(max_margin, 1e-9))
        breakout_strength_score = margin_score * 25.0

        # Volume profile (25): higher breakout-vs-consolidation volume ratio
        vol_excess = breakout_volume_ratio - self._min_breakout_volume_ratio
        vol_score = min(1.0, vol_excess / max(self._min_breakout_volume_ratio, 1e-9))
        volume_profile_score = max(0.0, vol_score) * 25.0

        # Range context (20): overall consolidation tightness relative to ATR
        range_context_score = tightness * 20.0

        total = consol_quality_score + breakout_strength_score + volume_profile_score + range_context_score
        return max(0.0, min(100.0, total))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected narrow range breakout pattern (0–100).

        Components (30/25/25/20 weighting):
            - Consolidation quality (30): more narrowing bars + tighter range
            - Breakout strength (25): margin above consolidation high
            - Volume profile (25): breakout volume ratio vs consolidation avg
            - Range context (20): overall consolidation range / ATR

        Args:
            detection: A previously detected narrow range breakout pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        narrowing_bar_count = int(meta.get("narrowing_bar_count", self._min_narrowing_bars))
        consolidation_range_atr_ratio = float(meta.get("consolidation_range_atr_ratio", 0.5))
        breakout_margin = float(meta.get("breakout_margin", self._breakout_margin_percent))
        breakout_volume_ratio = float(meta.get("breakout_volume_ratio", self._min_breakout_volume_ratio))

        return self._compute_confidence(
            narrowing_bar_count=narrowing_bar_count,
            consolidation_range_atr_ratio=consolidation_range_atr_ratio,
            breakout_margin=breakout_margin,
            breakout_volume_ratio=breakout_volume_ratio,
        )

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for Narrow Range Breakout pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="nr_lookback",
                param_type=int,
                default=self._nr_lookback,
                min_value=4,
                max_value=15,
                step=1,
                description="Bars to scan for narrowing range sequence (excludes breakout bar)",
                category="detection",
            ),
            PatternParam(
                name="min_narrowing_bars",
                param_type=int,
                default=self._min_narrowing_bars,
                min_value=2,
                max_value=7,
                step=1,
                description="Min consecutive bars with decreasing range",
                category="detection",
            ),
            PatternParam(
                name="range_decay_tolerance",
                param_type=float,
                default=self._range_decay_tolerance,
                min_value=1.0,
                max_value=1.15,
                step=0.01,
                description="range(i) ≤ range(i-1) × tolerance (5% noise allowed)",
                category="detection",
            ),
            PatternParam(
                name="breakout_margin_percent",
                param_type=float,
                default=self._breakout_margin_percent,
                min_value=0.0005,
                max_value=0.005,
                step=0.0005,
                description="Min close excess above consolidation high (fraction)",
                category="detection",
            ),
            PatternParam(
                name="min_breakout_volume_ratio",
                param_type=float,
                default=self._min_breakout_volume_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.25,
                description="Breakout bar volume / avg consolidation volume",
                category="filtering",
            ),
            PatternParam(
                name="consolidation_max_range_atr",
                param_type=float,
                default=self._consolidation_max_range_atr,
                min_value=0.3,
                max_value=1.5,
                step=0.1,
                description="Max overall consolidation range as ATR multiple",
                category="detection",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop placement below consolidation low",
                category="trade",
            ),
            PatternParam(
                name="target_ratio",
                param_type=float,
                default=self._target_ratio,
                min_value=1.0,
                max_value=4.0,
                step=0.5,
                description="Target distance as ratio of risk",
                category="trade",
            ),
            PatternParam(
                name="target_1_r",
                param_type=float,
                default=self._target_1_r,
                min_value=0.5,
                max_value=3.0,
                step=0.5,
                description="First target R-multiple",
                category="trade",
            ),
            PatternParam(
                name="target_2_r",
                param_type=float,
                default=self._target_2_r,
                min_value=1.0,
                max_value=4.0,
                step=0.5,
                description="Second target R-multiple",
                category="trade",
            ),
            PatternParam(
                name="min_score_threshold",
                param_type=float,
                default=self._min_score_threshold,
                min_value=0.0,
                max_value=60.0,
                step=10.0,
                description="Minimum confidence to emit detection",
                category="scoring",
            ),
        ]
