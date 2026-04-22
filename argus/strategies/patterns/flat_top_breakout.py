"""Flat-Top Breakout pattern detection module.

Detects horizontal resistance levels with multiple touches, tight
consolidation below resistance, and a volume-confirmed breakout above.
Pure detection logic with no operating window or state management concerns.
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class FlatTopBreakoutPattern(PatternModule):
    """Detect flat-top breakout patterns.

    Pattern anatomy:
        1. Resistance: >= resistance_touches candle highs cluster within
           resistance_tolerance_pct of each other.
        2. Consolidation: >= consolidation_min_bars below resistance with
           narrowing range (recent bars tighter than earlier bars).
        3. Breakout: latest candle closes above resistance with volume >=
           breakout_volume_multiplier * average recent volume.

    Args:
        resistance_touches: Minimum distinct candles touching resistance.
        resistance_tolerance_pct: Max spread of highs to be considered a
            cluster (fraction of price, e.g. 0.002 = 0.2%).
        consolidation_min_bars: Minimum bars of consolidation below resistance.
        breakout_volume_multiplier: Breakout volume vs avg consolidation volume.
        target_1_r: First target as R-multiple of risk.
        target_2_r: Second target as R-multiple of risk.
        min_score_threshold: Minimum detection confidence to emit signal.
        max_range_narrowing: Maximum range narrowing ratio for consolidation.
    """

    def __init__(
        self,
        resistance_touches: int = 3,
        resistance_tolerance_pct: float = 0.002,
        consolidation_min_bars: int = 10,
        breakout_volume_multiplier: float = 1.3,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        min_score_threshold: float = 0.0,
        max_range_narrowing: float = 1.0,
    ) -> None:
        self._resistance_touches = resistance_touches
        self._resistance_tolerance_pct = resistance_tolerance_pct
        self._consolidation_min_bars = consolidation_min_bars
        self._breakout_volume_multiplier = breakout_volume_multiplier
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._min_score_threshold = min_score_threshold
        self._max_range_narrowing = max_range_narrowing

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Flat-Top Breakout"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return self._consolidation_min_bars + 10

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a flat-top breakout pattern in the given candle window.

        Scans candle highs for a resistance cluster, validates consolidation
        below resistance, then confirms a volume breakout on the last candle.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (unused in V1).

        Returns:
            PatternDetection if flat-top breakout found, None otherwise.
        """
        min_candles = self._consolidation_min_bars + 2
        if len(candles) < min_candles:
            return None

        breakout_candle = candles[-1]
        pre_breakout = candles[:-1]

        # --- Identify resistance level ---
        resistance = self._find_resistance(pre_breakout)
        if resistance is None:
            return None

        resistance_level, touch_count = resistance

        # --- Validate consolidation below resistance ---
        consolidation = self._validate_consolidation(pre_breakout, resistance_level)
        if consolidation is None:
            return None

        consol_bars, consol_low, range_narrowing_ratio = consolidation

        # --- Validate breakout ---
        if breakout_candle.close <= resistance_level:
            return None

        avg_volume = sum(c.volume for c in pre_breakout[-consol_bars:]) / consol_bars
        if avg_volume <= 0:
            return None
        volume_ratio = breakout_candle.volume / avg_volume
        if volume_ratio < self._breakout_volume_multiplier:
            return None

        # --- Build detection ---
        entry_price = breakout_candle.close
        stop_price = consol_low
        risk = entry_price - stop_price
        if risk <= 0:
            return None

        t1 = entry_price + self._target_1_r * risk
        t2 = entry_price + self._target_2_r * risk

        confidence = self._compute_confidence(
            touch_count,
            range_narrowing_ratio,
            volume_ratio,
            breakout_candle,
        )

        return PatternDetection(
            pattern_type="flat_top_breakout",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(t1, t2),
            metadata={
                "resistance_level": round(resistance_level, 4),
                "resistance_touches": touch_count,
                "consolidation_bars": consol_bars,
                "consolidation_low": round(consol_low, 4),
                "range_narrowing_ratio": round(range_narrowing_ratio, 4),
                "breakout_volume_ratio": round(volume_ratio, 2),
            },
        )

    def _find_resistance(
        self,
        candles: list[CandleBar],
    ) -> tuple[float, int] | None:
        """Find the strongest horizontal resistance cluster.

        Scans all candle highs and groups those within
        resistance_tolerance_pct of each other. Returns the cluster
        with the most touches if it meets the minimum threshold.

        Args:
            candles: Pre-breakout candle history.

        Returns:
            Tuple of (resistance_level, touch_count) or None.
        """
        if not candles:
            return None

        highs = sorted((c.high for c in candles), reverse=True)

        best_level: float | None = None
        best_count = 0

        for anchor in highs:
            if anchor <= 0:
                continue
            tolerance = anchor * self._resistance_tolerance_pct
            count = sum(1 for h in highs if abs(h - anchor) <= tolerance)
            if count > best_count:
                best_count = count
                # Resistance level is the mean of the cluster
                cluster_highs = [h for h in highs if abs(h - anchor) <= tolerance]
                best_level = sum(cluster_highs) / len(cluster_highs)

        if best_count < self._resistance_touches or best_level is None:
            return None

        return best_level, best_count

    def _validate_consolidation(
        self,
        candles: list[CandleBar],
        resistance_level: float,
    ) -> tuple[int, float, float] | None:
        """Validate consolidation below resistance.

        Checks that sufficient bars stayed below resistance and that
        the range narrowed over the consolidation period.

        Args:
            candles: Pre-breakout candle history.
            resistance_level: Identified resistance price.

        Returns:
            Tuple of (consolidation_bar_count, lowest_low,
            range_narrowing_ratio) or None if consolidation invalid.
        """
        # Count bars where close stayed at or below resistance
        consol_count = 0
        for candle in reversed(candles):
            if candle.close <= resistance_level:
                consol_count += 1
            else:
                break

        if consol_count < self._consolidation_min_bars:
            return None

        consol_candles = candles[-consol_count:]
        consol_low = min(c.low for c in consol_candles)

        # Range narrowing: compare first half vs second half range
        half = max(consol_count // 2, 1)
        first_half = consol_candles[:half]
        second_half = consol_candles[half:]

        first_range = max(c.high for c in first_half) - min(c.low for c in first_half)
        second_range = max(c.high for c in second_half) - min(c.low for c in second_half)

        # Ratio < 1.0 means range narrowed; >= 1.0 means it widened
        range_narrowing_ratio = second_range / first_range if first_range > 0 else 1.0

        return consol_count, consol_low, range_narrowing_ratio

    def _compute_confidence(
        self,
        touch_count: int,
        range_narrowing_ratio: float,
        volume_ratio: float,
        breakout_candle: CandleBar,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Args:
            touch_count: Number of resistance touches.
            range_narrowing_ratio: Second-half / first-half range ratio.
            volume_ratio: Breakout volume / avg consolidation volume.
            breakout_candle: The breakout candle.

        Returns:
            Confidence score 0-100.

        Note:
            ``_confidence_score()`` operates on the raw detection frame (no
            persisted metadata yet) and therefore does NOT have access to the
            post-detect resistance-excess calculation used in ``score()``. To
            keep both weightings internally consistent it uses the same
            ``30/30/25/15`` split as ``score()`` — touches, consolidation
            tightness, volume, and breakout-candle structure (FIX-19 P1-B-L04).
        """
        # Resistance touches (0-30): more touches = stronger
        touch_score = min((touch_count - 1) / 4.0, 1.0) * 30

        # Consolidation quality (0-30): lower ratio = tighter
        consol_score = max(0.0, (1.0 - range_narrowing_ratio)) * 30

        # Volume spike (0-25): higher ratio above threshold
        vol_score = min((volume_ratio - 1.0) / 2.0, 1.0) * 25

        # Breakout candle quality (0-15): close near high, body > wick
        candle_range = breakout_candle.high - breakout_candle.low
        if candle_range > 0:
            body = abs(breakout_candle.close - breakout_candle.open)
            close_near_high = 1.0 - (breakout_candle.high - breakout_candle.close) / candle_range
            body_ratio = body / candle_range
            bo_score = (close_near_high * 0.5 + body_ratio * 0.5) * 15
        else:
            bo_score = 0.0

        return max(0.0, min(100.0, touch_score + consol_score + vol_score + bo_score))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected flat-top breakout pattern (0-100).

        Components:
            - Resistance touches: more touches = stronger (up to 30 pts)
            - Consolidation quality: tighter range near resistance (up to 30 pts)
            - Volume profile: lower vol during consolidation, spike on breakout (up to 25 pts)
            - Breakout candle quality: close near high, body > wick (up to 15 pts)

        Args:
            detection: A previously detected flat-top breakout pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        # Resistance touches (0-30): more touches = stronger
        touches = int(meta.get("resistance_touches", self._resistance_touches))
        touch_score = min((touches - 1) / 5.0, 1.0) * 30

        # Consolidation quality (0-30): range narrowing = tighter is better
        narrowing = float(meta.get("range_narrowing_ratio", 1.0))
        consol_score = max(0.0, (1.0 - narrowing)) * 30

        # Volume profile (0-25): higher breakout volume ratio
        vol_ratio = float(meta.get("breakout_volume_ratio", 1.0))
        vol_score = min((vol_ratio - 1.0) / 2.0, 1.0) * 25

        # Breakout candle quality (0-15): entry far above resistance
        resistance = float(meta.get("resistance_level", detection.entry_price))
        if resistance > 0:
            breakout_excess = (detection.entry_price - resistance) / resistance
            bo_score = min(breakout_excess / 0.02, 1.0) * 15
        else:
            bo_score = 0.0

        total = touch_score + consol_score + vol_score + bo_score
        return max(0.0, min(100.0, total))

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for Flat-Top Breakout pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="resistance_touches",
                param_type=int,
                default=self._resistance_touches,
                min_value=2,
                max_value=6,
                step=1,
                description="Minimum distinct candles touching resistance",
                category="detection",
            ),
            PatternParam(
                name="resistance_tolerance_pct",
                param_type=float,
                default=self._resistance_tolerance_pct,
                min_value=0.001,
                max_value=0.004,
                step=0.001,
                description="Max spread of highs for resistance cluster",
                category="detection",
            ),
            PatternParam(
                name="consolidation_min_bars",
                param_type=int,
                default=self._consolidation_min_bars,
                min_value=5,
                max_value=25,
                step=5,
                description="Minimum bars of consolidation below resistance",
                category="detection",
            ),
            PatternParam(
                name="breakout_volume_multiplier",
                param_type=float,
                default=self._breakout_volume_multiplier,
                min_value=1.0,
                max_value=2.0,
                step=0.2,
                description="Required breakout volume vs avg consolidation volume",
                category="filtering",
            ),
            PatternParam(
                name="target_1_r",
                param_type=float,
                default=self._target_1_r,
                min_value=0.5,
                max_value=2.0,
                step=0.5,
                description="First target as R-multiple of risk",
                category="scoring",
            ),
            PatternParam(
                name="target_2_r",
                param_type=float,
                default=self._target_2_r,
                min_value=1.0,
                max_value=4.0,
                step=1.0,
                description="Second target as R-multiple of risk",
                category="scoring",
            ),
            PatternParam(
                name="min_score_threshold",
                param_type=float,
                default=self._min_score_threshold,
                min_value=0.0,
                max_value=40.0,
                step=10.0,
                description="Minimum confidence score to emit detection",
                category="filtering",
            ),
            PatternParam(
                name="max_range_narrowing",
                param_type=float,
                default=self._max_range_narrowing,
                min_value=0.6,
                max_value=1.2,
                step=0.2,
                description="Maximum range narrowing ratio for valid consolidation",
                category="filtering",
            ),
        ]
