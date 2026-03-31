"""Dip-and-Rip momentum reversal pattern detection module.

Detects sharp intraday dips followed by rapid recoveries — a momentum
reversal play. The pattern requires:
  1. A sharp price dip from a rolling high
  2. A rapid recovery (faster than the dip)
  3. Volume confirmation on the recovery
  4. Optional level interaction scoring (VWAP / round numbers)

Pure detection logic with no operating window or state management concerns.
"""

from __future__ import annotations

import math
from zoneinfo import ZoneInfo

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)

_ET = ZoneInfo("America/New_York")

# Earliest time (ET) for valid dip detection — differentiates from R2G
_EARLIEST_DIP_TIME_HOUR = 9
_EARLIEST_DIP_TIME_MINUTE = 35


class DipAndRipPattern(PatternModule):
    """Detect dip-and-rip momentum reversal patterns.

    Pattern anatomy:
        1. Dip: price drops >= min_dip_percent from rolling high within
           max_dip_bars candles
        2. Recovery: price recovers >= min_recovery_percent of the dip
           within max_recovery_bars, faster than the dip
        3. Volume: recovery bars have higher volume than dip bars
        4. Entry: close above entry_threshold_percent of dip range
        5. Stop: below dip low minus ATR buffer

    Args:
        dip_lookback: Bars to look back for rolling high.
        min_dip_percent: Minimum dip as fraction (e.g. 0.02 = 2%).
        max_dip_bars: Maximum bars for the dip to complete.
        min_recovery_percent: Minimum recovery of dip range (e.g. 0.50 = 50%).
        max_recovery_bars: Maximum bars for recovery to complete.
        max_recovery_ratio: Recovery bars must be <= dip_bars * this ratio.
        entry_threshold_percent: Close must be above this fraction of dip range.
        min_recovery_volume_ratio: Recovery avg volume / dip avg volume.
        stop_buffer_atr_mult: ATR multiplier for stop buffer below dip low.
        target_ratio: Target = dip range * this ratio from dip low.
    """

    def __init__(
        self,
        dip_lookback: int = 10,
        min_dip_percent: float = 0.02,
        max_dip_bars: int = 5,
        min_recovery_percent: float = 0.50,
        max_recovery_bars: int = 8,
        max_recovery_ratio: float = 1.5,
        entry_threshold_percent: float = 0.60,
        min_recovery_volume_ratio: float = 1.3,
        stop_buffer_atr_mult: float = 0.3,
        target_ratio: float = 1.5,
    ) -> None:
        self._dip_lookback = dip_lookback
        self._min_dip_percent = min_dip_percent
        self._max_dip_bars = max_dip_bars
        self._min_recovery_percent = min_recovery_percent
        self._max_recovery_bars = max_recovery_bars
        self._max_recovery_ratio = max_recovery_ratio
        self._entry_threshold_percent = entry_threshold_percent
        self._min_recovery_volume_ratio = min_recovery_volume_ratio
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "dip_and_rip"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 30

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a dip-and-rip pattern in the given candle window.

        Scans recent candles for a sharp dip from a rolling high, validates
        recovery speed and volume, then builds entry/stop/target levels.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (vwap, atr used if available).

        Returns:
            PatternDetection if dip-and-rip found, None otherwise.
        """
        min_bars = self._dip_lookback + self._max_dip_bars + 1
        if len(candles) < min_bars:
            return None

        # Scan backwards for a qualifying dip + recovery
        # We look for the dip starting after the lookback window
        best_detection = self._scan_for_pattern(candles, indicators)
        return best_detection

    def _scan_for_pattern(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Scan candles for the most recent qualifying dip-and-rip.

        Args:
            candles: Full candle window.
            indicators: Current indicator values.

        Returns:
            PatternDetection if found, None otherwise.
        """
        n = len(candles)

        # We need room for: lookback + dip + recovery
        # Scan possible dip-start positions
        earliest_dip_start = self._dip_lookback
        latest_dip_start = n - 2  # need at least 1 bar for recovery

        for dip_start_idx in range(latest_dip_start, earliest_dip_start - 1, -1):
            result = self._try_dip_at(candles, dip_start_idx, indicators)
            if result is not None:
                return result

        return None

    def _try_dip_at(
        self,
        candles: list[CandleBar],
        dip_start_idx: int,
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Try to find a valid dip-and-rip starting at the given index.

        Args:
            candles: Full candle window.
            dip_start_idx: Index where the dip begins.
            indicators: Current indicator values.

        Returns:
            PatternDetection if valid pattern found, None otherwise.
        """
        n = len(candles)

        # --- Rolling high from lookback window ---
        lookback_start = max(0, dip_start_idx - self._dip_lookback)
        lookback_candles = candles[lookback_start:dip_start_idx]
        if not lookback_candles:
            return None

        rolling_high = max(c.high for c in lookback_candles)
        if rolling_high <= 0:
            return None

        # --- Find the dip low within max_dip_bars ---
        dip_end_limit = min(dip_start_idx + self._max_dip_bars, n)
        dip_candles = candles[dip_start_idx:dip_end_limit]
        if not dip_candles:
            return None

        # Find the lowest low in the dip window
        dip_low = min(c.low for c in dip_candles)
        dip_low_idx = dip_start_idx + next(
            i for i, c in enumerate(dip_candles) if c.low == dip_low
        )

        # Validate dip magnitude
        dip_amount = rolling_high - dip_low
        dip_percent = dip_amount / rolling_high
        if dip_percent < self._min_dip_percent:
            return None

        # Reject dips before 9:35 AM ET (R2G differentiation)
        dip_time = candles[dip_low_idx].timestamp.astimezone(_ET)
        if (
            dip_time.hour < _EARLIEST_DIP_TIME_HOUR
            or (
                dip_time.hour == _EARLIEST_DIP_TIME_HOUR
                and dip_time.minute < _EARLIEST_DIP_TIME_MINUTE
            )
        ):
            return None

        dip_bars_count = dip_low_idx - dip_start_idx + 1

        # --- Validate recovery ---
        recovery_start = dip_low_idx + 1
        recovery_end_limit = min(
            recovery_start + self._max_recovery_bars, n
        )
        if recovery_start >= n:
            return None

        recovery_candles = candles[recovery_start:recovery_end_limit]
        if not recovery_candles:
            return None

        # Find recovery high
        recovery_high = max(c.high for c in recovery_candles)
        recovery_amount = recovery_high - dip_low
        dip_range = rolling_high - dip_low

        if dip_range <= 0:
            return None

        recovery_percent = recovery_amount / dip_range
        if recovery_percent < self._min_recovery_percent:
            return None

        # Recovery velocity: must be faster than dip
        recovery_high_idx = recovery_start + next(
            i for i, c in enumerate(recovery_candles) if c.high == recovery_high
        )
        recovery_bars_count = recovery_high_idx - dip_low_idx
        if recovery_bars_count <= 0:
            return None

        max_allowed_recovery_bars = max(
            1, math.ceil(dip_bars_count * self._max_recovery_ratio)
        )
        if recovery_bars_count > max_allowed_recovery_bars:
            return None

        # --- Volume confirmation ---
        dip_volume_candles = candles[dip_start_idx : dip_low_idx + 1]
        avg_dip_volume = (
            sum(c.volume for c in dip_volume_candles) / len(dip_volume_candles)
            if dip_volume_candles
            else 0
        )
        recovery_vol_candles = candles[recovery_start : recovery_high_idx + 1]
        avg_recovery_volume = (
            sum(c.volume for c in recovery_vol_candles) / len(recovery_vol_candles)
            if recovery_vol_candles
            else 0
        )

        if avg_dip_volume <= 0:
            return None

        volume_ratio = avg_recovery_volume / avg_dip_volume
        if volume_ratio < self._min_recovery_volume_ratio:
            return None

        # --- Entry confirmation ---
        latest_candle = candles[-1]
        entry_threshold = dip_low + dip_range * self._entry_threshold_percent
        if latest_candle.close < entry_threshold:
            return None

        # --- Build entry/stop/target ---
        atr = indicators.get("atr", 0.0)
        stop_buffer = atr * self._stop_buffer_atr_mult if atr > 0 else dip_range * 0.1
        stop_price = dip_low - stop_buffer
        entry_price = latest_candle.close
        target_price = dip_low + dip_range * self._target_ratio

        # --- Level interaction scoring (optional) ---
        vwap = indicators.get("vwap", 0.0)
        level_interaction = self._check_level_interaction(dip_low, vwap)

        confidence = self._compute_confidence(
            dip_percent=dip_percent,
            dip_bars_count=dip_bars_count,
            recovery_percent=recovery_percent,
            recovery_bars_count=recovery_bars_count,
            volume_ratio=volume_ratio,
            level_interaction=level_interaction,
        )

        return PatternDetection(
            pattern_type="dip_and_rip",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_price,),
            metadata={
                "rolling_high": round(rolling_high, 4),
                "dip_low": round(dip_low, 4),
                "dip_percent": round(dip_percent, 4),
                "dip_bars": dip_bars_count,
                "recovery_percent": round(recovery_percent, 4),
                "recovery_bars": recovery_bars_count,
                "volume_ratio": round(volume_ratio, 2),
                "level_interaction": level_interaction,
                "dip_range": round(dip_range, 4),
                "atr": round(atr, 4) if atr > 0 else 0.0,
            },
        )

    def _check_level_interaction(
        self, dip_low: float, vwap: float
    ) -> str:
        """Check if the dip found support at a key level.

        Args:
            dip_low: The low price of the dip.
            vwap: Current VWAP value (0 if unavailable).

        Returns:
            Level interaction type: "vwap", "round_number", or "none".
        """
        # VWAP support: dip low within 0.5% of VWAP
        if vwap > 0:
            vwap_distance = abs(dip_low - vwap) / vwap
            if vwap_distance < 0.005:
                return "vwap"

        # Round number support: dip low within 0.5% of a whole dollar
        nearest_round = round(dip_low)
        if nearest_round > 0:
            round_distance = abs(dip_low - nearest_round) / nearest_round
            if round_distance < 0.005:
                return "round_number"

        return "none"

    def _compute_confidence(
        self,
        dip_percent: float,
        dip_bars_count: int,
        recovery_percent: float,
        recovery_bars_count: int,
        volume_ratio: float,
        level_interaction: str,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Args:
            dip_percent: Dip magnitude as fraction.
            dip_bars_count: Number of bars in the dip.
            recovery_percent: Recovery as fraction of dip range.
            recovery_bars_count: Number of bars in recovery.
            volume_ratio: Recovery volume / dip volume.
            level_interaction: Level type ("vwap", "round_number", "none").

        Returns:
            Confidence score 0-100.
        """
        # Dip severity/speed (30): deeper + faster = better
        depth_score = min(dip_percent / 0.05, 1.0)  # 5% dip = max
        speed_score = max(0.0, 1.0 - (dip_bars_count - 1) / self._max_dip_bars)
        dip_score = (depth_score * 0.6 + speed_score * 0.4) * 30

        # Recovery velocity (25): faster recovery = better
        recovery_speed = max(
            0.0, 1.0 - (recovery_bars_count - 1) / self._max_recovery_bars
        )
        recovery_magnitude = min(recovery_percent / 1.0, 1.0)
        recovery_score = (recovery_speed * 0.6 + recovery_magnitude * 0.4) * 25

        # Volume profile (25): higher ratio = better
        vol_score = min((volume_ratio - 1.0) / 1.0, 1.0) * 25

        # Level interaction (20): vwap=full, round_number=partial, none=base
        if level_interaction == "vwap":
            level_score = 20.0
        elif level_interaction == "round_number":
            level_score = 12.0
        else:
            level_score = 5.0

        total = dip_score + recovery_score + vol_score + level_score
        return max(0.0, min(100.0, total))

    def score(self, detection: PatternDetection) -> float:
        """Score a detected dip-and-rip pattern (0-100).

        Components (30/25/25/20 weighting):
            - Dip severity/speed (30): deeper + faster dip = higher
            - Recovery velocity (25): faster recovery = higher
            - Volume profile (25): higher recovery volume ratio = higher
            - Level interaction (20): dip at VWAP/support = higher

        Args:
            detection: A previously detected dip-and-rip pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        dip_percent = float(meta.get("dip_percent", 0))
        dip_bars = int(meta.get("dip_bars", self._max_dip_bars))
        recovery_percent = float(meta.get("recovery_percent", 0))
        recovery_bars = int(meta.get("recovery_bars", self._max_recovery_bars))
        volume_ratio = float(meta.get("volume_ratio", 1.0))
        level_interaction = str(meta.get("level_interaction", "none"))

        return self._compute_confidence(
            dip_percent=dip_percent,
            dip_bars_count=dip_bars,
            recovery_percent=recovery_percent,
            recovery_bars_count=recovery_bars,
            volume_ratio=volume_ratio,
            level_interaction=level_interaction,
        )

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for Dip-and-Rip pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="dip_lookback",
                param_type=int,
                default=self._dip_lookback,
                min_value=5,
                max_value=20,
                step=5,
                description="Bars to look back for rolling high",
                category="detection",
            ),
            PatternParam(
                name="min_dip_percent",
                param_type=float,
                default=self._min_dip_percent,
                min_value=0.01,
                max_value=0.05,
                step=0.005,
                description="Minimum dip as fraction of rolling high",
                category="detection",
            ),
            PatternParam(
                name="max_dip_bars",
                param_type=int,
                default=self._max_dip_bars,
                min_value=2,
                max_value=10,
                step=1,
                description="Maximum bars for the dip to complete",
                category="detection",
            ),
            PatternParam(
                name="min_recovery_percent",
                param_type=float,
                default=self._min_recovery_percent,
                min_value=0.30,
                max_value=0.80,
                step=0.10,
                description="Minimum recovery as fraction of dip range",
                category="detection",
            ),
            PatternParam(
                name="max_recovery_bars",
                param_type=int,
                default=self._max_recovery_bars,
                min_value=3,
                max_value=15,
                step=1,
                description="Maximum bars for recovery to complete",
                category="detection",
            ),
            PatternParam(
                name="max_recovery_ratio",
                param_type=float,
                default=self._max_recovery_ratio,
                min_value=1.0,
                max_value=2.5,
                step=0.25,
                description="Max recovery_bars / dip_bars ratio (velocity check)",
                category="detection",
            ),
            PatternParam(
                name="entry_threshold_percent",
                param_type=float,
                default=self._entry_threshold_percent,
                min_value=0.40,
                max_value=0.80,
                step=0.10,
                description="Close must be above this fraction of dip range from low",
                category="detection",
            ),
            PatternParam(
                name="min_recovery_volume_ratio",
                param_type=float,
                default=self._min_recovery_volume_ratio,
                min_value=1.0,
                max_value=2.5,
                step=0.1,
                description="Required recovery avg volume / dip avg volume",
                category="filtering",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.1,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop buffer below dip low",
                category="detection",
            ),
            PatternParam(
                name="target_ratio",
                param_type=float,
                default=self._target_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.25,
                description="Target = dip range * this ratio from dip low",
                category="detection",
            ),
        ]
