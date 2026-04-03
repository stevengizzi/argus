"""VWAP Bounce continuation pattern detection module.

Detects a pullback to VWAP from above followed by a bounce — a
continuation-side complement to VWAP Reclaim (which enters from below).
The pattern requires:
  1. A prior uptrend: price was above VWAP for >= min_prior_trend_bars
  2. An approach zone: price moves within vwap_approach_distance_pct of VWAP
  3. A VWAP touch: candle low is within vwap_touch_tolerance_pct of VWAP
     (tolerance allows for slight wicks below)
  4. A bounce: min_bounce_bars consecutive closes above VWAP with volume
     confirmation on the first bounce bar

Pure detection logic with no operating window or state management concerns.
Operating window: 10:30 AM – 15:00 ET (enforced by PatternBasedStrategy).
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class VwapBouncePattern(PatternModule):
    """Detect VWAP bounce continuation patterns.

    Pattern anatomy:
        1. Prior uptrend: >= min_prior_trend_bars bars with close > VWAP,
           average distance above VWAP >= min_price_above_vwap_pct
        2. Approach: price moves within vwap_approach_distance_pct of VWAP
           from above — confirms intentional test, not random drop
        3. Touch: candle low within vwap_touch_tolerance_pct * VWAP of VWAP
           (slight undershoot allowed — wicks through VWAP are acceptable)
        4. Bounce: min_bounce_bars consecutive closes above VWAP, first bounce
           bar volume >= min_bounce_volume_ratio * recent average volume
        5. Entry: close of the last bounce confirmation bar
        6. Stop: VWAP - ATR * stop_buffer_atr_mult

    VWAP must come from indicators["vwap"] — never computed from candle data
    because VWAP requires cumulative price * volume from market open.

    Args:
        vwap_approach_distance_pct: Distance from VWAP to start monitoring (0.5%).
        vwap_touch_tolerance_pct: How close low must get to VWAP (0.2%).
        min_bounce_bars: Consecutive bars closing above VWAP after touch.
        min_bounce_volume_ratio: First bounce bar volume / avg recent volume.
        min_prior_trend_bars: Min bars price was above VWAP before approach.
        min_price_above_vwap_pct: During prior trend, required avg distance above VWAP.
        stop_buffer_atr_mult: ATR mult for stop placement below VWAP.
        target_ratio: Target distance ratio (unused in R-multiple mode, kept for grid).
        target_1_r: First target R-multiple.
        target_2_r: Second target R-multiple.
        min_score_threshold: Min confidence to emit detection (0 = all).
    """

    def __init__(
        self,
        vwap_approach_distance_pct: float = 0.005,
        vwap_touch_tolerance_pct: float = 0.002,
        min_bounce_bars: int = 2,
        min_bounce_volume_ratio: float = 1.3,
        min_prior_trend_bars: int = 10,
        min_price_above_vwap_pct: float = 0.003,
        stop_buffer_atr_mult: float = 0.5,
        target_ratio: float = 2.0,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        min_score_threshold: float = 0.0,
    ) -> None:
        self._vwap_approach_distance_pct = vwap_approach_distance_pct
        self._vwap_touch_tolerance_pct = vwap_touch_tolerance_pct
        self._min_bounce_bars = min_bounce_bars
        self._min_bounce_volume_ratio = min_bounce_volume_ratio
        self._min_prior_trend_bars = min_prior_trend_bars
        self._min_price_above_vwap_pct = min_price_above_vwap_pct
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._min_score_threshold = min_score_threshold

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "VWAP Bounce"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 30

    @property
    def min_detection_bars(self) -> int:
        """Minimum candle count before detection is attempted."""
        return self._min_prior_trend_bars + self._min_bounce_bars + 3

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a VWAP bounce pattern in the given candle window.

        Returns the most recent qualifying approach → touch → bounce sequence,
        or None if no qualifying pattern is found.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values; must include "vwap".

        Returns:
            PatternDetection if VWAP bounce found, None otherwise.
        """
        vwap = indicators.get("vwap", 0.0)
        if not vwap or vwap <= 0.0:
            return None

        atr = indicators.get("atr", 0.0)

        if len(candles) < self.min_detection_bars:
            return None

        # Gate: require prior uptrend — enough bars above VWAP with adequate distance
        if not self._check_prior_uptrend(candles, vwap):
            return None

        return self._scan_for_bounce(candles, vwap, atr)

    def _check_prior_uptrend(self, candles: list[CandleBar], vwap: float) -> bool:
        """Verify the stock was trending above VWAP before the approach.

        Args:
            candles: Full candle window.
            vwap: Current VWAP value.

        Returns:
            True if prior uptrend conditions are met.
        """
        above_vwap_bars = [c for c in candles if c.close > vwap]
        if len(above_vwap_bars) < self._min_prior_trend_bars:
            return False

        avg_distance = (
            sum((c.close - vwap) / vwap for c in above_vwap_bars) / len(above_vwap_bars)
        )
        return avg_distance >= self._min_price_above_vwap_pct

    def _scan_for_bounce(
        self,
        candles: list[CandleBar],
        vwap: float,
        atr: float,
    ) -> PatternDetection | None:
        """Scan for the most recent qualifying touch → bounce sequence.

        Works from the most recent possible touch backward to find the
        freshest valid signal.

        Args:
            candles: Full candle window.
            vwap: Current VWAP value.
            atr: Current ATR value.

        Returns:
            PatternDetection if found, None otherwise.
        """
        n = len(candles)

        # Touch must leave room for min_bounce_bars after it
        earliest_touch = self._min_prior_trend_bars
        latest_touch = n - self._min_bounce_bars - 1

        for touch_idx in range(latest_touch, earliest_touch - 1, -1):
            touch_candle = candles[touch_idx]

            # Touch: low within tolerance of VWAP (slight undershoot OK)
            if abs(touch_candle.low - vwap) > self._vwap_touch_tolerance_pct * vwap:
                continue

            # Touch bar should not be grossly above VWAP (not a random deep wick)
            # The close should not be far above VWAP — it's a test, not a runaway bar
            if touch_candle.close > vwap * (1 + self._vwap_approach_distance_pct * 3):
                continue

            # Approach: at least one bar before touch was in approach zone
            if not self._check_approach_zone(candles, touch_idx, vwap):
                continue

            # Bounce: min_bounce_bars consecutive closes above VWAP with volume
            bounce_result = self._check_bounce(candles, touch_idx, vwap)
            if bounce_result is None:
                continue

            bounce_end_idx, bounce_volume_ratio = bounce_result

            # Entry / stop / targets
            entry_candle = candles[bounce_end_idx]
            entry_price = entry_candle.close

            stop_buffer = atr * self._stop_buffer_atr_mult if atr > 0 else vwap * 0.005
            stop_price = vwap - stop_buffer

            if stop_price >= entry_price:
                continue

            risk = entry_price - stop_price
            if risk <= 0:
                continue

            target_1 = entry_price + risk * self._target_1_r
            target_2 = entry_price + risk * self._target_2_r

            # Compute metadata fields
            prior_trend_bars = sum(1 for c in candles[:touch_idx] if c.close > vwap)
            above_bars = [c for c in candles[:touch_idx] if c.close > vwap]
            avg_above_distance = (
                sum((c.close - vwap) / vwap for c in above_bars) / len(above_bars)
                if above_bars
                else 0.0
            )
            touch_depth_pct = (touch_candle.low - vwap) / vwap  # negative = wicked below
            approach_quality = self._compute_approach_quality(candles, touch_idx, vwap)

            confidence = self._compute_confidence(
                touch_depth_pct=abs(touch_depth_pct),
                prior_trend_bars=prior_trend_bars,
                avg_above_distance=avg_above_distance,
                bounce_volume_ratio=bounce_volume_ratio,
                approach_quality=approach_quality,
            )

            if confidence < self._min_score_threshold:
                continue

            return PatternDetection(
                pattern_type="vwap_bounce",
                confidence=confidence,
                entry_price=entry_price,
                stop_price=stop_price,
                target_prices=(target_1, target_2),
                metadata={
                    "vwap_value": round(vwap, 4),
                    "prior_trend_bars": prior_trend_bars,
                    "touch_depth_pct": round(touch_depth_pct, 4),
                    "bounce_volume_ratio": round(bounce_volume_ratio, 2),
                    "approach_quality": round(approach_quality, 4),
                    "avg_above_distance": round(avg_above_distance, 4),
                    "atr": round(atr, 4) if atr > 0 else 0.0,
                },
            )

        return None

    def _check_approach_zone(
        self,
        candles: list[CandleBar],
        touch_idx: int,
        vwap: float,
    ) -> bool:
        """Verify price was approaching VWAP from above before the touch.

        Looks at up to 5 bars before the touch and checks that at least one
        bar had a close within vwap_approach_distance_pct of VWAP from above.

        Args:
            candles: Full candle window.
            touch_idx: Index of the VWAP touch bar.
            vwap: Current VWAP value.

        Returns:
            True if at least one approach-zone bar exists before the touch.
        """
        approach_lookback = 5
        approach_start = max(0, touch_idx - approach_lookback)
        approach_bars = candles[approach_start:touch_idx]

        for c in approach_bars:
            distance = (c.close - vwap) / vwap
            if 0.0 <= distance <= self._vwap_approach_distance_pct:
                return True
        return False

    def _check_bounce(
        self,
        candles: list[CandleBar],
        touch_idx: int,
        vwap: float,
    ) -> tuple[int, float] | None:
        """Verify bounce: min_bounce_bars consecutive closes above VWAP with volume.

        Args:
            candles: Full candle window.
            touch_idx: Index of the VWAP touch bar.
            vwap: Current VWAP value.

        Returns:
            (bounce_end_idx, volume_ratio) or None if bounce conditions not met.
        """
        n = len(candles)
        bounce_start = touch_idx + 1

        if bounce_start + self._min_bounce_bars > n:
            return None

        # Average volume from bars before the touch
        vol_lookback = min(10, touch_idx)
        vol_window = candles[max(0, touch_idx - vol_lookback):touch_idx]
        avg_volume = (
            sum(c.volume for c in vol_window) / len(vol_window) if vol_window else 0.0
        )

        if avg_volume <= 0:
            return None

        # All min_bounce_bars consecutive bars from bounce_start must close > VWAP
        bounce_bars = candles[bounce_start: bounce_start + self._min_bounce_bars]
        if not all(c.close > vwap for c in bounce_bars):
            return None

        # Volume confirmation on the first bounce bar
        first_bounce = bounce_bars[0]
        volume_ratio = first_bounce.volume / avg_volume
        if volume_ratio < self._min_bounce_volume_ratio:
            return None

        bounce_end_idx = bounce_start + self._min_bounce_bars - 1
        return (bounce_end_idx, volume_ratio)

    def _compute_approach_quality(
        self,
        candles: list[CandleBar],
        touch_idx: int,
        vwap: float,
    ) -> float:
        """Compute approach quality as fraction of lows rising toward VWAP.

        Higher lows during approach = bullish structure = better quality.

        Args:
            candles: Full candle window.
            touch_idx: Index of the VWAP touch bar.
            vwap: Current VWAP value.

        Returns:
            Quality score in [0.0, 1.0].
        """
        approach_lookback = 5
        approach_start = max(0, touch_idx - approach_lookback)
        approach_bars = candles[approach_start:touch_idx]

        if len(approach_bars) < 2:
            return 0.5

        lows = [c.low for c in approach_bars]
        higher_low_count = sum(1 for i in range(1, len(lows)) if lows[i] > lows[i - 1])
        return higher_low_count / (len(lows) - 1)

    def _compute_confidence(
        self,
        touch_depth_pct: float,
        prior_trend_bars: int,
        avg_above_distance: float,
        bounce_volume_ratio: float,
        approach_quality: float,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Weighting: vwap_interaction (30) / prior_trend (25) /
                   volume_profile (25) / price_structure (20).

        Args:
            touch_depth_pct: Absolute distance of touch low from VWAP as fraction.
                             Closer to 0 = cleaner touch.
            prior_trend_bars: Number of bars price was above VWAP.
            avg_above_distance: Average fractional distance above VWAP.
            bounce_volume_ratio: First bounce bar volume / recent average volume.
            approach_quality: Fraction of rising lows during approach (0–1).

        Returns:
            Confidence score 0–100.
        """
        # VWAP interaction quality (30): cleaner touch (low closer to VWAP)
        touch_tolerance = self._vwap_touch_tolerance_pct
        touch_quality = max(0.0, 1.0 - touch_depth_pct / (touch_tolerance * 2 + 1e-9))
        interaction_score = touch_quality * 30.0

        # Prior trend strength (25): more bars + greater avg distance above VWAP
        trend_count_score = min(
            1.0, prior_trend_bars / max(1, self._min_prior_trend_bars * 2)
        )
        trend_dist_score = min(
            1.0, avg_above_distance / max(1e-9, self._min_price_above_vwap_pct * 3)
        )
        trend_score = (trend_count_score * 0.5 + trend_dist_score * 0.5) * 25.0

        # Volume profile (25): higher bounce volume ratio = better
        vol_score = min(1.0, (bounce_volume_ratio - 1.0) / 1.0) * 25.0

        # Price structure (20): higher lows during approach = bullish
        structure_score = approach_quality * 20.0

        total = interaction_score + trend_score + vol_score + structure_score
        return max(0.0, min(100.0, total))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected VWAP bounce pattern (0–100).

        Components (30/25/25/20 weighting):
            - VWAP interaction quality (30): cleaner touch
            - Prior trend strength (25): more bars above VWAP + greater distance
            - Volume profile (25): bounce volume ratio
            - Price structure (20): higher lows during approach

        Args:
            detection: A previously detected VWAP bounce pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        touch_depth_pct = abs(float(meta.get("touch_depth_pct", 0.0)))
        prior_trend_bars = int(meta.get("prior_trend_bars", self._min_prior_trend_bars))
        avg_above_distance = float(meta.get("avg_above_distance", self._min_price_above_vwap_pct))
        bounce_volume_ratio = float(meta.get("bounce_volume_ratio", 1.0))
        approach_quality = float(meta.get("approach_quality", 0.5))

        return self._compute_confidence(
            touch_depth_pct=touch_depth_pct,
            prior_trend_bars=prior_trend_bars,
            avg_above_distance=avg_above_distance,
            bounce_volume_ratio=bounce_volume_ratio,
            approach_quality=approach_quality,
        )

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for VWAP Bounce pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="vwap_approach_distance_pct",
                param_type=float,
                default=self._vwap_approach_distance_pct,
                min_value=0.002,
                max_value=0.015,
                step=0.001,
                description="Distance from VWAP to start monitoring approach (fraction)",
                category="detection",
            ),
            PatternParam(
                name="vwap_touch_tolerance_pct",
                param_type=float,
                default=self._vwap_touch_tolerance_pct,
                min_value=0.001,
                max_value=0.005,
                step=0.001,
                description="How close low must get to VWAP (fraction of VWAP)",
                category="detection",
            ),
            PatternParam(
                name="min_bounce_bars",
                param_type=int,
                default=self._min_bounce_bars,
                min_value=1,
                max_value=5,
                step=1,
                description="Consecutive bars closing above VWAP after touch",
                category="detection",
            ),
            PatternParam(
                name="min_bounce_volume_ratio",
                param_type=float,
                default=self._min_bounce_volume_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.1,
                description="First bounce bar volume / avg recent volume",
                category="filtering",
            ),
            PatternParam(
                name="min_prior_trend_bars",
                param_type=int,
                default=self._min_prior_trend_bars,
                min_value=5,
                max_value=20,
                step=5,
                description="Min bars price was above VWAP before approach",
                category="detection",
            ),
            PatternParam(
                name="min_price_above_vwap_pct",
                param_type=float,
                default=self._min_price_above_vwap_pct,
                min_value=0.001,
                max_value=0.010,
                step=0.001,
                description="Required avg distance above VWAP during prior trend",
                category="detection",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop placement below VWAP",
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
