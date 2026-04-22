"""Micro Pullback continuation pattern detection module.

Detects the first shallow pullback to a short-term EMA after a strong
impulsive move — a momentum continuation entry. The pattern requires:
  1. A strong impulse move (>=min_impulse_percent over min_impulse_bars)
  2. A shallow pullback into the EMA zone (within pullback_tolerance_atr of EMA)
  3. A bounce candle closing above EMA with volume confirmation

Pure detection logic with no operating window or state management concerns.
Operating window: 10:00 AM – 14:00 ET (enforced by PatternBasedStrategy).
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class MicroPullbackPattern(PatternModule):
    """Detect micro pullback continuation patterns.

    Pattern anatomy:
        1. Impulse: price moves >= min_impulse_percent over min_impulse_bars
           to max_impulse_bars candles
        2. Pullback: within max_pullback_bars, price dips into EMA zone
           (candle low within pullback_tolerance_atr * ATR of the EMA)
        3. Bounce: a candle closes above EMA with volume >=
           min_bounce_volume_ratio * recent average volume
        4. Entry: close of the bounce candle
        5. Stop: pullback low minus ATR buffer

    Args:
        ema_period: EMA lookback period.
        min_impulse_percent: Minimum impulse move as fraction (e.g. 0.02 = 2%).
        min_impulse_bars: Minimum bars for the impulse.
        max_impulse_bars: Maximum bars to look back for impulse.
        max_pullback_bars: Maximum bars for pullback to complete.
        pullback_tolerance_atr: How close to EMA (in ATR multiples) counts as a touch.
        min_bounce_volume_ratio: Bounce bar volume / avg recent volume.
        stop_buffer_atr_mult: ATR multiplier for stop below pullback low.
        target_ratio: Target distance as ratio of risk.
        target_1_r: First target R-multiple.
        target_2_r: Second target R-multiple.
        min_score_threshold: Minimum confidence to emit detection (0 = all).
    """

    def __init__(
        self,
        ema_period: int = 9,
        min_impulse_percent: float = 0.02,
        min_impulse_bars: int = 3,
        max_impulse_bars: int = 15,
        max_pullback_bars: int = 5,
        pullback_tolerance_atr: float = 0.3,
        min_bounce_volume_ratio: float = 1.2,
        stop_buffer_atr_mult: float = 0.5,
        target_ratio: float = 2.0,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        min_score_threshold: float = 0.0,
    ) -> None:
        self._ema_period = ema_period
        self._min_impulse_percent = min_impulse_percent
        self._min_impulse_bars = min_impulse_bars
        self._max_impulse_bars = max_impulse_bars
        self._max_pullback_bars = max_pullback_bars
        self._pullback_tolerance_atr = pullback_tolerance_atr
        self._min_bounce_volume_ratio = min_bounce_volume_ratio
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._min_score_threshold = min_score_threshold

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Micro Pullback"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection.

        30 bars covers the EMA-9 warm-up plus sufficient history to
        identify the prior leg, pullback-depth, and bounce confirmation
        (FIX-19 P1-B-C03).
        """
        return 30

    def _compute_ema(self, closes: list[float]) -> list[float]:
        """Compute EMA series from a list of closes.

        Uses standard exponential smoothing with multiplier = 2 / (period + 1).
        The first EMA value is seeded as the SMA of the first `ema_period` closes.

        Args:
            closes: List of close prices (oldest first).

        Returns:
            List of EMA values the same length as closes.
            Values before index ema_period-1 are set to closes[0] (seed).
        """
        period = self._ema_period
        if len(closes) < period:
            return list(closes)

        multiplier = 2.0 / (period + 1)
        ema_values: list[float] = []

        # Seed: SMA of first `period` values
        seed = sum(closes[:period]) / period
        for i in range(period - 1):
            ema_values.append(closes[i])  # pre-seed placeholder (not used in detection)
        ema_values.append(seed)

        for close in closes[period:]:
            prev_ema = ema_values[-1]
            ema_values.append((close - prev_ema) * multiplier + prev_ema)

        return ema_values

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a micro pullback pattern in the given candle window.

        Searches for an impulse → pullback → bounce sequence. Returns the
        most recent qualifying pattern or None.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (atr, vwap used if available).

        Returns:
            PatternDetection if micro pullback found, None otherwise.
        """
        # Need EMA warmup + at least min_impulse_bars impulse + max_pullback_bars pullback + 1 bounce.
        # max_impulse_bars is a lookahead window used during scanning, not a bar floor.
        min_required = self._ema_period + self._min_impulse_bars + self._max_pullback_bars + 1
        if len(candles) < min_required:
            return None

        atr = indicators.get("atr", 0.0)
        vwap = indicators.get("vwap", 0.0)

        closes = [c.close for c in candles]
        ema_values = self._compute_ema(closes)

        return self._scan_for_pattern(candles, ema_values, atr, vwap)

    def _scan_for_pattern(
        self,
        candles: list[CandleBar],
        ema_values: list[float],
        atr: float,
        vwap: float,
    ) -> PatternDetection | None:
        """Scan for the most recent qualifying impulse → pullback → bounce.

        Starts from the most recent position and works backwards so the
        freshest valid signal is returned.

        Args:
            candles: Full candle window.
            ema_values: Precomputed EMA series (same length as candles).
            atr: Current ATR value.
            vwap: Current VWAP value.

        Returns:
            PatternDetection if found, None otherwise.
        """
        n = len(candles)

        # The bounce bar must be the last candle (most recent)
        # Scan backwards: the bounce is at index (n-1), pullback starts
        # somewhere before that, impulse ends before the pullback.
        # We try each possible pullback-start → bounce sequence.
        for pullback_start in range(n - self._max_pullback_bars - 1, n - 1):
            if pullback_start < self._ema_period + self._min_impulse_bars:
                continue

            result = self._try_bounce_at(
                candles, ema_values, pullback_start, atr, vwap
            )
            if result is not None:
                return result

        return None

    def _try_bounce_at(
        self,
        candles: list[CandleBar],
        ema_values: list[float],
        pullback_start: int,
        atr: float,
        vwap: float,
    ) -> PatternDetection | None:
        """Try to find impulse → pullback → bounce with pullback starting at pullback_start.

        Args:
            candles: Full candle window.
            ema_values: Precomputed EMA series.
            pullback_start: Index where pullback phase begins.
            atr: Current ATR value.
            vwap: Current VWAP value.

        Returns:
            PatternDetection if valid pattern found, None otherwise.
        """
        n = len(candles)

        # --- Find the impulse that precedes pullback_start ---
        impulse_result = self._find_impulse(candles, pullback_start)
        if impulse_result is None:
            return None
        impulse_start, impulse_end, impulse_low, impulse_high, impulse_bars = impulse_result

        # --- Find pullback to EMA zone ---
        pullback_result = self._find_pullback_to_ema(
            candles, ema_values, pullback_start, atr
        )
        if pullback_result is None:
            return None
        pullback_low, pullback_low_idx, ema_at_pullback = pullback_result

        # --- Find bounce: candle after pullback_low that closes above EMA ---
        bounce_result = self._find_bounce(
            candles, ema_values, pullback_low_idx
        )
        if bounce_result is None:
            return None
        bounce_idx, bounce_volume_ratio = bounce_result

        # Bounce must be within max_pullback_bars of pullback_start
        if bounce_idx - pullback_start > self._max_pullback_bars:
            return None

        # --- Entry / stop / targets ---
        bounce_candle = candles[bounce_idx]
        entry_price = bounce_candle.close

        stop_buffer = atr * self._stop_buffer_atr_mult if atr > 0 else entry_price * 0.005
        stop_price = pullback_low - stop_buffer

        if stop_price >= entry_price:
            return None

        risk = entry_price - stop_price
        if risk <= 0:
            return None

        target_1 = entry_price + risk * self._target_1_r
        target_2 = entry_price + risk * self._target_2_r

        # --- Impulse metrics ---
        impulse_percent = (impulse_high - impulse_low) / impulse_low if impulse_low > 0 else 0.0
        pullback_depth = (impulse_high - pullback_low) / (impulse_high - impulse_low) if (impulse_high - impulse_low) > 0 else 0.0

        confidence = self._compute_confidence(
            impulse_percent=impulse_percent,
            impulse_bars=impulse_bars,
            pullback_depth=pullback_depth,
            ema_distance_atr=(abs(pullback_low - ema_at_pullback) / atr) if atr > 0 else 0.5,
            bounce_volume_ratio=bounce_volume_ratio,
            vwap=vwap,
            entry_price=entry_price,
        )

        if confidence < self._min_score_threshold:
            return None

        return PatternDetection(
            pattern_type="micro_pullback",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_1, target_2),
            metadata={
                "impulse_percent": round(impulse_percent, 4),
                "impulse_bars": impulse_bars,
                "pullback_depth": round(pullback_depth, 4),
                "ema_value": round(ema_at_pullback, 4),
                "pullback_low": round(pullback_low, 4),
                "bounce_volume_ratio": round(bounce_volume_ratio, 2),
                "atr": round(atr, 4) if atr > 0 else 0.0,
                "vwap": round(vwap, 4) if vwap > 0 else 0.0,
            },
        )

    def _find_impulse(
        self,
        candles: list[CandleBar],
        before_idx: int,
    ) -> tuple[int, int, float, float, int] | None:
        """Find a qualifying impulse that ends at or before before_idx.

        Scans windows of size [min_impulse_bars, max_impulse_bars] ending
        at before_idx-1 and checks if the move from window low to window high
        qualifies as an impulse.

        Args:
            candles: Full candle window.
            before_idx: Impulse must end strictly before this index.

        Returns:
            (start_idx, end_idx, low, high, bar_count) or None.
        """
        for window_size in range(
            self._min_impulse_bars, self._max_impulse_bars + 1
        ):
            end_idx = before_idx - 1
            start_idx = end_idx - window_size + 1
            if start_idx < 0:
                break

            window = candles[start_idx : end_idx + 1]
            low = min(c.low for c in window)
            high = max(c.high for c in window)

            if low <= 0:
                continue

            move = (high - low) / low
            if move >= self._min_impulse_percent:
                return (start_idx, end_idx, low, high, window_size)

        return None

    def _find_pullback_to_ema(
        self,
        candles: list[CandleBar],
        ema_values: list[float],
        pullback_start: int,
        atr: float,
    ) -> tuple[float, int, float] | None:
        """Find the lowest candle in the pullback window that touches the EMA zone.

        Args:
            candles: Full candle window.
            ema_values: Precomputed EMA series.
            pullback_start: Index where pullback phase begins.
            atr: Current ATR value.

        Returns:
            (pullback_low, pullback_low_idx, ema_at_that_bar) or None.
        """
        n = len(candles)
        end_idx = min(pullback_start + self._max_pullback_bars, n - 1)

        # ATR-tolerance for EMA proximity check
        tolerance = atr * self._pullback_tolerance_atr if atr > 0 else 0.0

        best_low: float | None = None
        best_idx: int = pullback_start
        best_ema: float = ema_values[pullback_start]

        for idx in range(pullback_start, end_idx + 1):
            candle = candles[idx]
            ema_val = ema_values[idx]

            if tolerance > 0:
                ema_proximity = abs(candle.low - ema_val) <= tolerance
            else:
                # Fallback: low must be within 1% of EMA
                ema_proximity = (
                    abs(candle.low - ema_val) / ema_val < 0.01
                    if ema_val > 0
                    else False
                )

            if ema_proximity:
                if best_low is None or candle.low < best_low:
                    best_low = candle.low
                    best_idx = idx
                    best_ema = ema_val

        if best_low is None:
            return None

        return (best_low, best_idx, best_ema)

    def _find_bounce(
        self,
        candles: list[CandleBar],
        ema_values: list[float],
        pullback_low_idx: int,
    ) -> tuple[int, float] | None:
        """Find the first bounce candle after the pullback low.

        A bounce candle closes above the EMA and has volume above the
        recent average by at least min_bounce_volume_ratio.

        Args:
            candles: Full candle window.
            ema_values: Precomputed EMA series.
            pullback_low_idx: Index of the pullback low bar.

        Returns:
            (bounce_idx, volume_ratio) or None.
        """
        n = len(candles)
        bounce_start = pullback_low_idx + 1

        if bounce_start >= n:
            return None

        # Average volume over recent N bars for comparison
        vol_lookback = min(10, pullback_low_idx)
        vol_window = candles[pullback_low_idx - vol_lookback : pullback_low_idx]
        avg_volume = (
            sum(c.volume for c in vol_window) / len(vol_window)
            if vol_window
            else 0.0
        )

        if avg_volume <= 0:
            return None

        for idx in range(bounce_start, n):
            candle = candles[idx]
            ema_val = ema_values[idx]

            closes_above_ema = candle.close > ema_val
            volume_ratio = candle.volume / avg_volume if avg_volume > 0 else 0.0
            volume_ok = volume_ratio >= self._min_bounce_volume_ratio

            if closes_above_ema and volume_ok:
                return (idx, volume_ratio)

        return None

    def _compute_confidence(
        self,
        impulse_percent: float,
        impulse_bars: int,
        pullback_depth: float,
        ema_distance_atr: float,
        bounce_volume_ratio: float,
        vwap: float,
        entry_price: float,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Weighting: impulse_strength (30) / pullback_quality (25) /
                   volume_profile (25) / trend_context (20).

        Args:
            impulse_percent: Impulse move as fraction of low price.
            impulse_bars: Number of bars in impulse (fewer = faster).
            pullback_depth: Pullback depth as fraction of impulse range.
            ema_distance_atr: Distance of pullback low from EMA in ATR units.
            bounce_volume_ratio: Bounce volume / recent average volume.
            vwap: Current VWAP (0 if unavailable).
            entry_price: Entry price.

        Returns:
            Confidence score 0–100.
        """
        # Impulse strength (30): larger % move + faster completion (fewer bars)
        impulse_magnitude = min(impulse_percent / 0.05, 1.0)  # 5% = max
        speed_score = max(
            0.0, 1.0 - (impulse_bars - self._min_impulse_bars) / max(1, self._max_impulse_bars - self._min_impulse_bars)
        )
        impulse_score = (impulse_magnitude * 0.6 + speed_score * 0.4) * 30

        # Pullback quality (25): shallower pullback + clean EMA touch
        # Ideal pullback is shallow (< 50% of impulse range) and close to EMA
        shallow_score = max(0.0, 1.0 - pullback_depth / 0.8)  # 0% retrace = max
        ema_touch_score = max(0.0, 1.0 - ema_distance_atr)  # 0 ATR distance = max
        pullback_score = (shallow_score * 0.5 + ema_touch_score * 0.5) * 25

        # Volume profile (25): higher bounce volume ratio = better
        vol_score = min((bounce_volume_ratio - 1.0) / 1.0, 1.0) * 25

        # Trend context (20): price above VWAP = bullish, below = less confident
        if vwap > 0:
            if entry_price >= vwap:
                trend_score = 20.0
            elif entry_price >= vwap * 0.99:
                trend_score = 12.0
            else:
                trend_score = 5.0
        else:
            trend_score = 10.0  # neutral when VWAP unavailable

        total = impulse_score + pullback_score + vol_score + trend_score
        return max(0.0, min(100.0, total))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected micro pullback pattern (0–100).

        Components (30/25/25/20 weighting):
            - Impulse strength (30): larger % move + faster completion
            - Pullback quality (25): shallower pullback + clean EMA touch
            - Volume profile (25): higher bounce volume ratio
            - Trend context (20): price position relative to VWAP

        Args:
            detection: A previously detected micro pullback pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        impulse_percent = float(meta.get("impulse_percent", 0))
        impulse_bars = int(meta.get("impulse_bars", self._max_impulse_bars))
        pullback_depth = float(meta.get("pullback_depth", 0.5))
        atr = float(meta.get("atr", 0))
        ema_value = float(meta.get("ema_value", 0))
        pullback_low = float(meta.get("pullback_low", 0))
        bounce_volume_ratio = float(meta.get("bounce_volume_ratio", 1.0))
        vwap = float(meta.get("vwap", 0))

        ema_distance_atr = (
            abs(pullback_low - ema_value) / atr if atr > 0 else 0.5
        )

        return self._compute_confidence(
            impulse_percent=impulse_percent,
            impulse_bars=impulse_bars,
            pullback_depth=pullback_depth,
            ema_distance_atr=ema_distance_atr,
            bounce_volume_ratio=bounce_volume_ratio,
            vwap=vwap,
            entry_price=detection.entry_price,
        )

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for Micro Pullback pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="ema_period",
                param_type=int,
                default=self._ema_period,
                min_value=5,
                max_value=21,
                step=2,
                description="EMA lookback period",
                category="detection",
            ),
            PatternParam(
                name="min_impulse_percent",
                param_type=float,
                default=self._min_impulse_percent,
                min_value=0.01,
                max_value=0.06,
                step=0.01,
                description="Minimum impulse move as fraction of price",
                category="detection",
            ),
            PatternParam(
                name="min_impulse_bars",
                param_type=int,
                default=self._min_impulse_bars,
                min_value=2,
                max_value=8,
                step=1,
                description="Minimum bars for the impulse",
                category="detection",
            ),
            PatternParam(
                name="max_impulse_bars",
                param_type=int,
                default=self._max_impulse_bars,
                min_value=5,
                max_value=20,
                step=5,
                description="Maximum bars to look back for impulse",
                category="detection",
            ),
            PatternParam(
                name="max_pullback_bars",
                param_type=int,
                default=self._max_pullback_bars,
                min_value=2,
                max_value=10,
                step=1,
                description="Maximum bars for pullback to complete",
                category="detection",
            ),
            PatternParam(
                name="pullback_tolerance_atr",
                param_type=float,
                default=self._pullback_tolerance_atr,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="EMA proximity in ATR multiples for pullback touch",
                category="detection",
            ),
            PatternParam(
                name="min_bounce_volume_ratio",
                param_type=float,
                default=self._min_bounce_volume_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.2,
                description="Bounce bar volume / avg recent volume",
                category="filtering",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop below pullback low",
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
