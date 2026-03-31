"""High-of-Day Break pattern detection module.

Detects high-of-day breakout continuations — stocks consolidating near
their session high then breaking out with volume. Primary midday coverage
provider (10:00–15:30 window). Pure detection logic with no operating
window or state management concerns.
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class HODBreakPattern(PatternModule):
    """Detect high-of-day breakout continuation patterns.

    Pattern anatomy:
        1. HOD tracking: dynamic high-of-day across all candles, counting
           touches within proximity.
        2. Consolidation: recent bars stay near HOD with a tight range
           relative to ATR.
        3. Breakout: price closes above HOD by a margin AND holds above
           for min_hold_bars consecutive bars.
        4. Volume: breakout bar volume exceeds average consolidation volume.

    Args:
        hod_proximity_percent: Fraction of HOD for a candle high to be
            considered a "touch" (e.g. 0.003 = 0.3%).
        consolidation_min_bars: Minimum candles in consolidation zone.
        consolidation_max_range_atr: Max consolidation range as ATR multiple.
        breakout_margin_percent: Min close excess above HOD (e.g. 0.001 = 0.1%).
        min_hold_bars: Consecutive bars above HOD before detection fires.
        min_breakout_volume_ratio: Breakout volume vs avg consolidation volume.
        stop_buffer_atr_mult: ATR multiplier for stop below consolidation low.
        target_ratio: Measured move multiplier for target from breakout point.
        target_1_r: First target as R-multiple of risk.
        target_2_r: Second target as R-multiple of risk.
        vwap_extended_pct: VWAP distance above which score degrades (default 0.05).
    """

    def __init__(
        self,
        hod_proximity_percent: float = 0.003,
        consolidation_min_bars: int = 5,
        consolidation_max_range_atr: float = 0.8,
        breakout_margin_percent: float = 0.001,
        min_hold_bars: int = 2,
        min_breakout_volume_ratio: float = 1.5,
        stop_buffer_atr_mult: float = 0.5,
        target_ratio: float = 2.0,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        vwap_extended_pct: float = 0.05,
    ) -> None:
        self._hod_proximity_percent = hod_proximity_percent
        self._consolidation_min_bars = consolidation_min_bars
        self._consolidation_max_range_atr = consolidation_max_range_atr
        self._breakout_margin_percent = breakout_margin_percent
        self._min_hold_bars = min_hold_bars
        self._min_breakout_volume_ratio = min_breakout_volume_ratio
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._vwap_extended_pct = vwap_extended_pct

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "HOD Break"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 60

    def _compute_atr(self, candles: list[CandleBar]) -> float:
        """Compute Average True Range from candle data.

        Uses the standard ATR(14) formula across candle ranges. Falls back
        to a simple high-low average when fewer than 14 candles available.

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

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect an HOD breakout continuation pattern.

        Scans candles for dynamic HOD, validates consolidation near HOD,
        then confirms a breakout held for min_hold_bars consecutive bars.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (vwap, atr used if available).

        Returns:
            PatternDetection if HOD break found, None otherwise.
        """
        min_required = self._consolidation_min_bars + self._min_hold_bars + 1
        if len(candles) < min_required:
            return None

        # --- Dynamic HOD tracking ---
        hod = candles[0].high
        hod_touch_count = 0

        for candle in candles:
            if candle.high > hod:
                hod = candle.high
            proximity_threshold = hod * self._hod_proximity_percent
            if abs(candle.high - hod) <= proximity_threshold:
                hod_touch_count += 1

        if hod <= 0:
            return None

        # --- ATR computation ---
        atr = indicators.get("atr", 0.0)
        if atr <= 0:
            atr = self._compute_atr(candles)
        if atr <= 0:
            return None

        # --- Consolidation detection near HOD ---
        consol_end = len(candles) - self._min_hold_bars
        consol_start = consol_end - self._consolidation_min_bars
        if consol_start < 0:
            return None

        consol_candles = candles[consol_start:consol_end]

        # Consolidation range check
        consol_high = max(c.high for c in consol_candles)
        consol_low = min(c.low for c in consol_candles)
        consol_range = consol_high - consol_low

        if consol_range > self._consolidation_max_range_atr * atr:
            return None

        # At least half of consolidation bars must have highs near HOD
        # Use the HOD as it was at the END of consolidation (consol_end - 1)
        hod_at_consol = max(c.high for c in candles[:consol_end])
        proximity_threshold = hod_at_consol * self._hod_proximity_percent
        near_hod_count = sum(
            1
            for c in consol_candles
            if abs(c.high - hod_at_consol) <= proximity_threshold
        )
        required_near_hod = max(1, self._consolidation_min_bars // 2)
        if near_hod_count < required_near_hod:
            return None

        # --- Breakout confirmation with hold duration ---
        hold_candles = candles[consol_end:]
        if len(hold_candles) < self._min_hold_bars:
            return None

        breakout_threshold = hod_at_consol * (1.0 + self._breakout_margin_percent)

        # ALL hold bars must close above HOD
        for bar in hold_candles[: self._min_hold_bars]:
            if bar.close < breakout_threshold:
                return None

        # The confirmation candle is the last hold bar
        confirm_candle = hold_candles[self._min_hold_bars - 1]

        # --- Volume confirmation ---
        avg_consol_volume = sum(c.volume for c in consol_candles) / len(
            consol_candles
        )
        if avg_consol_volume <= 0:
            return None

        # Use the first hold bar (the breakout bar) for volume check
        breakout_bar = hold_candles[0]
        volume_ratio = breakout_bar.volume / avg_consol_volume
        if volume_ratio < self._min_breakout_volume_ratio:
            return None

        # --- Build detection ---
        entry_price = confirm_candle.close
        stop_price = consol_low - self._stop_buffer_atr_mult * atr

        # Measured move target
        measured_target = entry_price + consol_range * self._target_ratio

        # R-multiple targets
        risk = entry_price - stop_price
        if risk <= 0:
            return None

        t1 = entry_price + risk * self._target_1_r
        t2 = entry_price + risk * self._target_2_r

        # Use whichever target set is larger
        target_prices = (max(t1, measured_target), t2)

        # VWAP distance for metadata
        vwap = indicators.get("vwap", 0.0)
        vwap_distance_pct = 0.0
        if vwap > 0:
            vwap_distance_pct = (entry_price - vwap) / vwap

        confidence = self._compute_confidence(
            consol_range=consol_range,
            atr=atr,
            consol_bars=len(consol_candles),
            volume_ratio=volume_ratio,
            hod_touch_count=hod_touch_count,
            vwap_distance_pct=vwap_distance_pct,
        )

        return PatternDetection(
            pattern_type="hod_break",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=target_prices,
            metadata={
                "hod": round(hod, 4),
                "hod_touch_count": hod_touch_count,
                "consolidation_range": round(consol_range, 4),
                "consolidation_bars": len(consol_candles),
                "consolidation_low": round(consol_low, 4),
                "consolidation_range_atr_ratio": round(
                    consol_range / atr if atr > 0 else 0.0, 4
                ),
                "breakout_volume_ratio": round(volume_ratio, 2),
                "vwap_distance_pct": round(vwap_distance_pct, 4),
                "hold_bars": self._min_hold_bars,
                "atr": round(atr, 4),
            },
        )

    def _compute_confidence(
        self,
        consol_range: float,
        atr: float,
        consol_bars: int,
        volume_ratio: float,
        hod_touch_count: int,
        vwap_distance_pct: float,
    ) -> float:
        """Compute detection confidence (0-100).

        Uses equal 25/25/25/25 weights for detection confidence.
        This differs from score() which uses spec-mandated 30/25/25/20
        weights for quality scoring. The distinction is intentional —
        confidence measures detection reliability, score measures setup
        quality for the Quality Engine.

        Args:
            consol_range: Consolidation price range.
            atr: Average True Range.
            consol_bars: Number of consolidation bars.
            volume_ratio: Breakout volume / avg consolidation volume.
            hod_touch_count: Number of HOD touches.
            vwap_distance_pct: Distance from VWAP as fraction.

        Returns:
            Confidence score 0–100.
        """
        # Tighter consolidation = higher (0-25)
        if atr > 0:
            range_ratio = consol_range / atr
            consol_score = max(0.0, 1.0 - range_ratio / self._consolidation_max_range_atr) * 25
        else:
            consol_score = 0.0

        # Volume spike (0-25)
        vol_score = min((volume_ratio - 1.0) / 2.0, 1.0) * 25

        # HOD touches (0-25): more touches = stronger resistance broken
        touch_score = min((hod_touch_count - 1) / 5.0, 1.0) * 25

        # VWAP distance (0-25): closer to VWAP = healthier
        if vwap_distance_pct <= 0.02:
            vwap_score = 25.0
        elif vwap_distance_pct >= self._vwap_extended_pct:
            vwap_score = 5.0
        else:
            # Linear interpolation between 2% and 5%
            frac = (vwap_distance_pct - 0.02) / (self._vwap_extended_pct - 0.02)
            vwap_score = 25.0 - frac * 20.0

        return max(0.0, min(100.0, consol_score + vol_score + touch_score + vwap_score))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected HOD break pattern (0–100).

        Components:
            - Consolidation quality (30): tighter range + longer duration
            - Breakout volume (25): higher volume ratio
            - Prior HOD tests (25): more touches before breakout
            - VWAP distance (20): not too extended from VWAP

        Args:
            detection: A previously detected HOD break pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        # Consolidation quality (0-30): tighter and longer = better
        range_atr_ratio = float(meta.get("consolidation_range_atr_ratio", 0.5))
        consol_bars = int(meta.get("consolidation_bars", self._consolidation_min_bars))
        tightness = max(0.0, 1.0 - range_atr_ratio / self._consolidation_max_range_atr)
        # Bonus for longer consolidation (beyond minimum)
        duration_bonus = min((consol_bars - self._consolidation_min_bars) / 10.0, 0.5)
        consol_score = (tightness + duration_bonus) / 1.5 * 30

        # Breakout volume (0-25)
        vol_ratio = float(meta.get("breakout_volume_ratio", 1.0))
        vol_score = min((vol_ratio - 1.0) / 2.0, 1.0) * 25

        # HOD touches (0-25): more touches = stronger resistance broken
        touches = int(meta.get("hod_touch_count", 1))
        touch_score = min((touches - 1) / 5.0, 1.0) * 25

        # VWAP distance (0-20): closer = healthier
        vwap_dist = float(meta.get("vwap_distance_pct", 0.0))
        if vwap_dist <= 0.02:
            vwap_score = 20.0
        elif vwap_dist >= self._vwap_extended_pct:
            vwap_score = 4.0
        else:
            frac = (vwap_dist - 0.02) / (self._vwap_extended_pct - 0.02)
            vwap_score = 20.0 - frac * 16.0

        total = consol_score + vol_score + touch_score + vwap_score
        return max(0.0, min(100.0, total))

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for HOD Break pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="hod_proximity_percent",
                param_type=float,
                default=self._hod_proximity_percent,
                min_value=0.001,
                max_value=0.005,
                step=0.001,
                description="Fraction of HOD for a touch (e.g. 0.003 = 0.3%)",
                category="detection",
            ),
            PatternParam(
                name="consolidation_min_bars",
                param_type=int,
                default=self._consolidation_min_bars,
                min_value=3,
                max_value=15,
                step=2,
                description="Minimum candles in consolidation zone near HOD",
                category="detection",
            ),
            PatternParam(
                name="consolidation_max_range_atr",
                param_type=float,
                default=self._consolidation_max_range_atr,
                min_value=0.4,
                max_value=1.5,
                step=0.2,
                description="Max consolidation range as ATR multiple",
                category="detection",
            ),
            PatternParam(
                name="breakout_margin_percent",
                param_type=float,
                default=self._breakout_margin_percent,
                min_value=0.0005,
                max_value=0.003,
                step=0.0005,
                description="Min close excess above HOD for breakout (fraction)",
                category="detection",
            ),
            PatternParam(
                name="min_hold_bars",
                param_type=int,
                default=self._min_hold_bars,
                min_value=1,
                max_value=5,
                step=1,
                description="Consecutive bars above HOD before detection fires",
                category="detection",
            ),
            PatternParam(
                name="min_breakout_volume_ratio",
                param_type=float,
                default=self._min_breakout_volume_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.25,
                description="Required breakout volume vs avg consolidation volume",
                category="filtering",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.2,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop below consolidation low",
                category="trade",
            ),
            PatternParam(
                name="target_ratio",
                param_type=float,
                default=self._target_ratio,
                min_value=1.0,
                max_value=4.0,
                step=0.5,
                description="Measured move multiplier (consol range x ratio)",
                category="trade",
            ),
            PatternParam(
                name="target_1_r",
                param_type=float,
                default=self._target_1_r,
                min_value=0.5,
                max_value=2.0,
                step=0.5,
                description="First target as R-multiple of risk",
                category="trade",
            ),
            PatternParam(
                name="target_2_r",
                param_type=float,
                default=self._target_2_r,
                min_value=1.0,
                max_value=4.0,
                step=1.0,
                description="Second target as R-multiple of risk",
                category="trade",
            ),
            PatternParam(
                name="vwap_extended_pct",
                param_type=float,
                default=self._vwap_extended_pct,
                min_value=0.03,
                max_value=0.10,
                step=0.01,
                description="VWAP distance above which score degrades to minimum",
                category="scoring",
            ),
        ]
