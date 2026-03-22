"""Bull Flag continuation pattern detection module.

Detects bull flag patterns: a strong upward move (pole) followed by a
tight consolidation (flag), then a breakout on volume. Pure detection
logic with no operating window or state management concerns.
"""

from __future__ import annotations

from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule


class BullFlagPattern(PatternModule):
    """Detect bull flag continuation patterns.

    Pattern anatomy:
        1. Pole: pole_min_bars+ candles with net upward move >= pole_min_move_pct
        2. Flag: <= flag_max_bars candles, retracement <= flag_max_retrace_pct of pole
        3. Breakout: latest candle closes above flag high with volume spike

    Args:
        pole_min_bars: Minimum candles for pole.
        pole_min_move_pct: Minimum pole move as fraction (e.g. 0.03 = 3%).
        flag_max_bars: Maximum candles in flag consolidation.
        flag_max_retrace_pct: Max retracement of pole height (e.g. 0.50 = 50%).
        breakout_volume_multiplier: Breakout volume vs avg flag volume.
    """

    def __init__(
        self,
        pole_min_bars: int = 5,
        pole_min_move_pct: float = 0.03,
        flag_max_bars: int = 20,
        flag_max_retrace_pct: float = 0.50,
        breakout_volume_multiplier: float = 1.3,
    ) -> None:
        self._pole_min_bars = pole_min_bars
        self._pole_min_move_pct = pole_min_move_pct
        self._flag_max_bars = flag_max_bars
        self._flag_max_retrace_pct = flag_max_retrace_pct
        self._breakout_volume_multiplier = breakout_volume_multiplier

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Bull Flag"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return self._pole_min_bars + self._flag_max_bars + 5

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a bull flag pattern in the given candle window.

        Scans backwards from the breakout candle to find pole, then flag,
        then confirms breakout on the most recent candle.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (unused in V1).

        Returns:
            PatternDetection if bull flag found, None otherwise.
        """
        if len(candles) < self._pole_min_bars + 2:
            return None

        breakout_candle = candles[-1]

        # Try different flag lengths, shortest first (tighter flags are better)
        for flag_len in range(1, min(self._flag_max_bars + 1, len(candles) - self._pole_min_bars)):
            result = self._try_flag_length(candles, flag_len, breakout_candle)
            if result is not None:
                return result

        return None

    def _try_flag_length(
        self,
        candles: list[CandleBar],
        flag_len: int,
        breakout_candle: CandleBar,
    ) -> PatternDetection | None:
        """Attempt detection with a specific flag length.

        Args:
            candles: Full candle window.
            flag_len: Number of candles to consider as flag.
            breakout_candle: The most recent candle (potential breakout).

        Returns:
            PatternDetection if valid pattern found at this flag length.
        """
        # Flag candles are between pole and breakout
        flag_end_idx = len(candles) - 1  # breakout candle index
        flag_start_idx = flag_end_idx - flag_len
        pole_end_idx = flag_start_idx  # pole ends where flag starts

        if pole_end_idx < self._pole_min_bars:
            return None

        # --- Pole validation ---
        pole_candles = candles[pole_end_idx - self._pole_min_bars : pole_end_idx]
        pole_high = max(c.high for c in pole_candles)
        pole_low = min(c.low for c in pole_candles)

        if pole_low <= 0:
            return None

        pole_move_pct = (pole_high - pole_low) / pole_low
        if pole_move_pct < self._pole_min_move_pct:
            return None

        pole_height = pole_high - pole_low

        # --- Flag validation ---
        flag_candles = candles[flag_start_idx:flag_end_idx]
        if not flag_candles:
            return None

        flag_high = max(c.high for c in flag_candles)
        flag_low = min(c.low for c in flag_candles)

        # Retracement: how far price pulled back from pole high
        retrace_from_pole_high = pole_high - flag_low
        if pole_height <= 0:
            return None

        retrace_pct = retrace_from_pole_high / pole_height
        if retrace_pct > self._flag_max_retrace_pct:
            return None

        # --- Breakout validation ---
        # Breakout candle must close above flag high
        if breakout_candle.close <= flag_high:
            return None

        # Volume check: breakout volume >= multiplier * avg flag volume
        avg_flag_volume = sum(c.volume for c in flag_candles) / len(flag_candles)
        if avg_flag_volume > 0:
            if breakout_candle.volume < self._breakout_volume_multiplier * avg_flag_volume:
                return None
        else:
            return None

        # --- Build detection ---
        entry_price = breakout_candle.close
        stop_price = flag_low
        # Measured move: pole height projected above breakout
        target_price = entry_price + pole_height

        # Confidence based on pattern quality metrics
        confidence = self._compute_confidence(
            pole_move_pct, retrace_pct, flag_len,
            breakout_candle, flag_high, avg_flag_volume,
        )

        return PatternDetection(
            pattern_type="bull_flag",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_price,),
            metadata={
                "pole_height": round(pole_height, 4),
                "pole_move_pct": round(pole_move_pct, 4),
                "pole_bars": self._pole_min_bars,
                "flag_bars": flag_len,
                "flag_high": round(flag_high, 4),
                "flag_low": round(flag_low, 4),
                "retrace_pct": round(retrace_pct, 4),
                "breakout_volume_ratio": round(
                    breakout_candle.volume / avg_flag_volume, 2
                ),
            },
        )

    def _compute_confidence(
        self,
        pole_move_pct: float,
        retrace_pct: float,
        flag_len: int,
        breakout_candle: CandleBar,
        flag_high: float,
        avg_flag_volume: float,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Args:
            pole_move_pct: Pole move as a fraction.
            retrace_pct: Flag retracement as fraction of pole height.
            flag_len: Number of flag candles.
            breakout_candle: The breakout candle.
            flag_high: Highest price during flag.
            avg_flag_volume: Average volume during flag.

        Returns:
            Confidence score 0-100.
        """
        # Pole strength: larger moves are better (up to ~10% = max credit)
        pole_score = min(pole_move_pct / 0.10, 1.0) * 25

        # Flag tightness: lower retrace is better
        tightness_score = (1.0 - retrace_pct / self._flag_max_retrace_pct) * 25

        # Volume spike: higher breakout volume relative to flag
        vol_ratio = breakout_candle.volume / avg_flag_volume if avg_flag_volume > 0 else 1.0
        vol_score = min((vol_ratio - 1.0) / 2.0, 1.0) * 25

        # Breakout quality: how far above flag high
        if flag_high > 0:
            breakout_excess = (breakout_candle.close - flag_high) / flag_high
            bo_score = min(breakout_excess / 0.02, 1.0) * 25
        else:
            bo_score = 0.0

        return max(0.0, min(100.0, pole_score + tightness_score + vol_score + bo_score))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected bull flag pattern (0-100).

        Components:
            - Pole strength: larger pole moves score higher (up to 30 pts)
            - Flag tightness: tighter retracement scores higher (up to 30 pts)
            - Volume profile: declining flag vol + spike on breakout (up to 25 pts)
            - Breakout quality: close near high of breakout candle (up to 15 pts)

        Args:
            detection: A previously detected bull flag pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        # Pole strength (0-30): larger moves score higher
        pole_move = float(meta.get("pole_move_pct", 0))
        pole_score = min(pole_move / 0.10, 1.0) * 30

        # Flag tightness (0-30): lower retrace is better
        retrace = float(meta.get("retrace_pct", self._flag_max_retrace_pct))
        tightness_score = (1.0 - retrace / self._flag_max_retrace_pct) * 30

        # Volume profile (0-25): higher breakout volume ratio is better
        vol_ratio = float(meta.get("breakout_volume_ratio", 1.0))
        vol_score = min((vol_ratio - 1.0) / 2.0, 1.0) * 25

        # Breakout quality (0-15): close near high of candle
        # Use entry vs flag_high spread as proxy
        flag_high = float(meta.get("flag_high", detection.entry_price))
        if flag_high > 0:
            breakout_excess = (detection.entry_price - flag_high) / flag_high
            bo_score = min(breakout_excess / 0.02, 1.0) * 15
        else:
            bo_score = 0.0

        total = pole_score + tightness_score + vol_score + bo_score
        return max(0.0, min(100.0, total))

    def get_default_params(self) -> dict[str, object]:
        """Return default parameter values for Bull Flag pattern.

        Returns:
            Dictionary of parameter names to default values.
        """
        return {
            "pole_min_bars": self._pole_min_bars,
            "pole_min_move_pct": self._pole_min_move_pct,
            "flag_max_bars": self._flag_max_bars,
            "flag_max_retrace_pct": self._flag_max_retrace_pct,
            "breakout_volume_multiplier": self._breakout_volume_multiplier,
        }
