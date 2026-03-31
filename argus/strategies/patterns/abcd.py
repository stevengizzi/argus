"""ABCD harmonic pattern detection module.

Detects ABCD patterns: a measured-move structure where the CD leg
mirrors the AB leg with Fibonacci retracement at B and C points.
Pure detection logic with no operating window or state management.

Pattern anatomy (bullish):
    1. A: swing low — starting point
    2. B: swing high — first impulse leg completes
    3. C: higher low — BC retraces 38.2–61.8% of AB
    4. D: completion — CD leg approximates AB in price and time
    Entry: at D completion zone
    Stop: below C minus ATR buffer
    Target: D + (B - A) * Fibonacci extension
"""

from __future__ import annotations

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class ABCDPattern(PatternModule):
    """Detect ABCD harmonic patterns.

    Args:
        swing_lookback: Bars on each side required for swing point.
        min_swing_atr_mult: Minimum swing size as multiple of ATR.
        fib_b_min: Minimum BC retracement of AB (e.g. 0.382).
        fib_b_max: Maximum BC retracement of AB (e.g. 0.618).
        fib_c_min: Unused in V1 (reserved for CD extension lower bound).
        fib_c_max: Unused in V1 (reserved for CD extension upper bound).
        leg_price_ratio_min: Minimum CD/AB price ratio.
        leg_price_ratio_max: Maximum CD/AB price ratio.
        leg_time_ratio_min: Minimum CD/AB time ratio.
        leg_time_ratio_max: Maximum CD/AB time ratio.
        completion_tolerance_percent: D-zone tolerance as percentage.
        stop_buffer_atr_mult: ATR multiple below C for stop placement.
        target_extension: Fibonacci extension for target from D.
    """

    def __init__(
        self,
        swing_lookback: int = 5,
        min_swing_atr_mult: float = 0.5,
        fib_b_min: float = 0.382,
        fib_b_max: float = 0.618,
        fib_c_min: float = 0.500,
        fib_c_max: float = 0.786,
        leg_price_ratio_min: float = 0.8,
        leg_price_ratio_max: float = 1.2,
        leg_time_ratio_min: float = 0.5,
        leg_time_ratio_max: float = 2.0,
        completion_tolerance_percent: float = 1.0,
        stop_buffer_atr_mult: float = 0.5,
        target_extension: float = 1.272,
    ) -> None:
        self._swing_lookback = swing_lookback
        self._min_swing_atr_mult = min_swing_atr_mult
        self._fib_b_min = fib_b_min
        self._fib_b_max = fib_b_max
        self._fib_c_min = fib_c_min
        self._fib_c_max = fib_c_max
        self._leg_price_ratio_min = leg_price_ratio_min
        self._leg_price_ratio_max = leg_price_ratio_max
        self._leg_time_ratio_min = leg_time_ratio_min
        self._leg_time_ratio_max = leg_time_ratio_max
        self._completion_tolerance_percent = completion_tolerance_percent
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_extension = target_extension

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "abcd"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 60

    # ------------------------------------------------------------------
    # Swing detection helpers
    # ------------------------------------------------------------------

    def _calculate_atr(self, candles: list[CandleBar], period: int = 14) -> float:
        """Calculate Average True Range over the candle window.

        Args:
            candles: Candle history.
            period: ATR lookback period.

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

        lookback = min(period, len(true_ranges))
        return sum(true_ranges[-lookback:]) / lookback

    def _find_swing_highs(
        self,
        candles: list[CandleBar],
        atr: float,
    ) -> list[tuple[int, float]]:
        """Find swing high points in the candle window.

        A swing high has a high greater than the highs of swing_lookback
        candles on each side, and meets the minimum ATR size requirement.

        Args:
            candles: Candle history.
            atr: Current ATR for minimum swing size filtering.

        Returns:
            List of (index, price) tuples, chronologically ordered.
        """
        lookback = self._swing_lookback
        swings: list[tuple[int, float]] = []

        for i in range(lookback, len(candles) - lookback):
            high = candles[i].high
            left = candles[i - lookback : i]
            right = candles[i + 1 : i + 1 + lookback]

            if all(high > c.high for c in left) and all(
                high > c.high for c in right
            ):
                # Check minimum swing size vs neighboring lows
                neighbor_lows = [c.low for c in left + right]
                min_neighbor_low = min(neighbor_lows)
                swing_size = high - min_neighbor_low

                if atr <= 0 or swing_size >= self._min_swing_atr_mult * atr:
                    swings.append((i, high))

        return swings

    def _find_swing_lows(
        self,
        candles: list[CandleBar],
        atr: float,
    ) -> list[tuple[int, float]]:
        """Find swing low points in the candle window.

        A swing low has a low less than the lows of swing_lookback
        candles on each side, and meets the minimum ATR size requirement.

        Args:
            candles: Candle history.
            atr: Current ATR for minimum swing size filtering.

        Returns:
            List of (index, price) tuples, chronologically ordered.
        """
        lookback = self._swing_lookback
        swings: list[tuple[int, float]] = []

        for i in range(lookback, len(candles) - lookback):
            low = candles[i].low
            left = candles[i - lookback : i]
            right = candles[i + 1 : i + 1 + lookback]

            if all(low < c.low for c in left) and all(
                low < c.low for c in right
            ):
                # Check minimum swing size vs neighboring highs
                neighbor_highs = [c.high for c in left + right]
                max_neighbor_high = max(neighbor_highs)
                swing_size = max_neighbor_high - low

                if atr <= 0 or swing_size >= self._min_swing_atr_mult * atr:
                    swings.append((i, low))

        return swings

    # ------------------------------------------------------------------
    # Core detection
    # ------------------------------------------------------------------

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a complete ABCD pattern in the candle window.

        Scans for the most recent valid bullish ABCD: A(low) → B(high)
        → C(higher low) → D(completion zone). Returns None for
        incomplete or invalid patterns.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (atr used if available).

        Returns:
            PatternDetection if complete ABCD found, None otherwise.
        """
        if len(candles) < self.lookback_bars:
            return None

        atr = indicators.get("atr", 0.0)
        if atr <= 0:
            atr = self._calculate_atr(candles)
        if atr <= 0:
            return None

        swing_lows = self._find_swing_lows(candles, atr)
        swing_highs = self._find_swing_highs(candles, atr)

        if len(swing_lows) < 2 or not swing_highs:
            return None

        current_price = candles[-1].close
        best_detection: PatternDetection | None = None

        # Iterate swing lows in reverse (most recent first) to find A
        for a_idx_rev in range(len(swing_lows) - 1, -1, -1):
            a_index, a_price = swing_lows[a_idx_rev]

            # Find B: next swing high after A, B > A
            b_candidates = [
                (bi, bp) for bi, bp in swing_highs if bi > a_index and bp > a_price
            ]
            if not b_candidates:
                continue

            for b_index, b_price in b_candidates:
                ab_height = b_price - a_price
                if ab_height <= 0:
                    continue

                # Find C: next swing low after B, C > A (higher low)
                c_candidates = [
                    (ci, cp)
                    for ci, cp in swing_lows
                    if ci > b_index and cp > a_price and cp < b_price
                ]
                if not c_candidates:
                    continue

                for c_index, c_price in c_candidates:
                    detection = self._validate_abcd(
                        candles,
                        a_index, a_price,
                        b_index, b_price,
                        c_index, c_price,
                        ab_height, atr, current_price,
                    )
                    if detection is not None:
                        # Most recent pattern wins — if we already have
                        # one, compare by A index (higher = more recent)
                        if best_detection is None:
                            best_detection = detection
                        else:
                            existing_a = int(
                                best_detection.metadata.get("a_index", -1)
                            )
                            if a_index > existing_a:
                                best_detection = detection

        return best_detection

    def _validate_abcd(
        self,
        candles: list[CandleBar],
        a_index: int,
        a_price: float,
        b_index: int,
        b_price: float,
        c_index: int,
        c_price: float,
        ab_height: float,
        atr: float,
        current_price: float,
    ) -> PatternDetection | None:
        """Validate Fibonacci, leg ratios, and completion zone.

        Args:
            candles: Full candle window.
            a_index: Index of A point in candles.
            a_price: Price at A.
            b_index: Index of B point.
            b_price: Price at B.
            c_index: Index of C point.
            c_price: Price at C.
            ab_height: B - A price distance.
            atr: ATR value.
            current_price: Most recent close price.

        Returns:
            PatternDetection if all checks pass, None otherwise.
        """
        # --- BC retracement check ---
        # Retracement = how much of AB was given back: (B - C) / (B - A)
        bc_retracement = (b_price - c_price) / ab_height
        if bc_retracement < self._fib_b_min or bc_retracement > self._fib_b_max:
            return None

        # --- Projected D point ---
        # Measured move: D = C + AB height (AB=CD)
        projected_d = c_price + ab_height

        # --- Completion zone check ---
        tolerance = projected_d * (self._completion_tolerance_percent / 100.0)
        if abs(current_price - projected_d) > tolerance:
            return None

        # --- Leg price ratio: CD/AB ---
        cd_height = current_price - c_price
        price_ratio = cd_height / ab_height if ab_height > 0 else 0.0
        if (
            price_ratio < self._leg_price_ratio_min
            or price_ratio > self._leg_price_ratio_max
        ):
            return None

        # --- Leg time ratio: CD_bars / AB_bars ---
        ab_bars = b_index - a_index
        cd_bars = len(candles) - 1 - c_index
        if ab_bars <= 0:
            return None
        time_ratio = cd_bars / ab_bars
        if (
            time_ratio < self._leg_time_ratio_min
            or time_ratio > self._leg_time_ratio_max
        ):
            return None

        # --- Build detection ---
        entry_price = current_price
        stop_price = c_price - self._stop_buffer_atr_mult * atr
        target_price = entry_price + ab_height * self._target_extension

        return PatternDetection(
            pattern_type="abcd",
            confidence=0.0,  # Populated by score()
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_price,),
            metadata={
                "a_index": a_index,
                "a_price": round(a_price, 4),
                "b_price": round(b_price, 4),
                "c_price": round(c_price, 4),
                "projected_d": round(projected_d, 4),
                "bc_retracement": round(bc_retracement, 4),
                "price_ratio": round(price_ratio, 4),
                "time_ratio": round(time_ratio, 4),
                "ab_bars": ab_bars,
                "cd_bars": cd_bars,
                "ab_height": round(ab_height, 4),
                "atr": round(atr, 4),
            },
        )

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    def score(self, detection: PatternDetection) -> float:
        """Score a detected ABCD pattern (0-100).

        Weights:
            - Fibonacci precision (35): closeness to ideal retracement
            - Leg symmetry (25): CD/AB ratio closeness to 1.0
            - Volume pattern (20): CD volume expansion vs BC
            - Trend context (20): ABCD aligned with higher-TF trend

        Args:
            detection: A previously detected ABCD pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        # --- Fibonacci precision (0-35) ---
        bc_ret = float(meta.get("bc_retracement", 0.5))
        # Ideal BC retracement is 0.618 — closer = better
        ideal_bc = 0.618
        bc_distance = abs(bc_ret - ideal_bc)
        # Max distance within valid range is ~0.236 (0.618-0.382)
        max_bc_distance = 0.236
        bc_precision = max(0.0, 1.0 - bc_distance / max_bc_distance)
        # Scale: perfect = 35, boundary = ~15
        fib_score = 15.0 + bc_precision * 20.0

        # --- Leg symmetry (0-25) ---
        price_ratio = float(meta.get("price_ratio", 1.0))
        time_ratio = float(meta.get("time_ratio", 1.0))
        # Perfect = 1.0, deviation penalized
        price_dev = abs(price_ratio - 1.0)
        time_dev = abs(time_ratio - 1.0)
        # Max deviation within valid range is 0.2 for price, 1.0 for time
        price_sym = max(0.0, 1.0 - price_dev / 0.2)
        time_sym = max(0.0, 1.0 - time_dev / 1.0)
        symmetry_score = (price_sym * 0.6 + time_sym * 0.4) * 25.0

        # --- Volume pattern (0-20) ---
        volume_ratio = float(meta.get("cd_bc_volume_ratio", 1.0))
        if volume_ratio >= 1.2:
            vol_score = 20.0
        elif volume_ratio >= 1.0:
            vol_score = 10.0 + (volume_ratio - 1.0) / 0.2 * 10.0
        else:
            vol_score = max(0.0, volume_ratio / 1.0 * 10.0)

        # --- Trend context (0-20) ---
        trend_aligned = float(meta.get("trend_aligned", 0.5))
        trend_score = trend_aligned * 20.0

        total = fib_score + symmetry_score + vol_score + trend_score
        return max(0.0, min(100.0, total))

    # ------------------------------------------------------------------
    # Default parameters
    # ------------------------------------------------------------------

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for ABCD pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="swing_lookback",
                param_type=int,
                default=self._swing_lookback,
                min_value=3,
                max_value=10,
                step=1,
                description="Bars on each side required for swing point",
                category="detection",
            ),
            PatternParam(
                name="min_swing_atr_mult",
                param_type=float,
                default=self._min_swing_atr_mult,
                min_value=0.3,
                max_value=1.0,
                step=0.1,
                description="Minimum swing size as multiple of ATR",
                category="detection",
            ),
            PatternParam(
                name="fib_b_min",
                param_type=float,
                default=self._fib_b_min,
                min_value=0.300,
                max_value=0.500,
                step=0.05,
                description="Minimum BC retracement of AB leg",
                category="fibonacci",
            ),
            PatternParam(
                name="fib_b_max",
                param_type=float,
                default=self._fib_b_max,
                min_value=0.500,
                max_value=0.750,
                step=0.05,
                description="Maximum BC retracement of AB leg",
                category="fibonacci",
            ),
            PatternParam(
                name="fib_c_min",
                param_type=float,
                default=self._fib_c_min,
                min_value=0.500,
                max_value=0.700,
                step=0.05,
                description="Minimum CD extension lower bound (reserved)",
                category="fibonacci",
            ),
            PatternParam(
                name="fib_c_max",
                param_type=float,
                default=self._fib_c_max,
                min_value=0.700,
                max_value=0.900,
                step=0.05,
                description="Maximum CD extension upper bound (reserved)",
                category="fibonacci",
            ),
            PatternParam(
                name="leg_price_ratio_min",
                param_type=float,
                default=self._leg_price_ratio_min,
                min_value=0.6,
                max_value=0.9,
                step=0.05,
                description="Minimum CD/AB price ratio",
                category="leg_ratios",
            ),
            PatternParam(
                name="leg_price_ratio_max",
                param_type=float,
                default=self._leg_price_ratio_max,
                min_value=1.1,
                max_value=1.5,
                step=0.05,
                description="Maximum CD/AB price ratio",
                category="leg_ratios",
            ),
            PatternParam(
                name="leg_time_ratio_min",
                param_type=float,
                default=self._leg_time_ratio_min,
                min_value=0.3,
                max_value=0.8,
                step=0.1,
                description="Minimum CD/AB time (bars) ratio",
                category="leg_ratios",
            ),
            PatternParam(
                name="leg_time_ratio_max",
                param_type=float,
                default=self._leg_time_ratio_max,
                min_value=1.5,
                max_value=3.0,
                step=0.5,
                description="Maximum CD/AB time (bars) ratio",
                category="leg_ratios",
            ),
            PatternParam(
                name="completion_tolerance_percent",
                param_type=float,
                default=self._completion_tolerance_percent,
                min_value=0.5,
                max_value=3.0,
                step=0.5,
                description="D-zone tolerance as percentage of projected D price",
                category="completion",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.3,
                max_value=1.5,
                step=0.1,
                description="ATR multiple below C for stop placement",
                category="trade",
            ),
            PatternParam(
                name="target_extension",
                param_type=float,
                default=self._target_extension,
                min_value=1.0,
                max_value=1.618,
                step=0.1,
                description="Fibonacci extension multiplier for target from D",
                category="trade",
            ),
        ]
