"""Pre-Market High Break pattern detection module.

Detects breakouts above the pre-market session high. The PM high is computed
from extended-hours candles already present in PatternBasedStrategy's candle
deque (EQUS.MINI delivers 4:00 AM -- 9:30 AM ET candles, and Sprint 27.65's
fix accumulates bars before the operating window check).

Pattern anatomy:
    1. PM high: maximum high across pre-market candles (before 9:30 AM ET)
    2. Volume: PM session must have sufficient volume for a meaningful level
    3. Breakout: market-hours bar closes above PM high with volume confirmation
    4. Hold: price stays above PM high for min_hold_bars consecutive bars
    5. Entry: at breakout confirmation (after hold bars)
    6. Stop: below PM high minus stop_buffer_atr_mult x ATR
    7. Target: PM range x target_ratio above PM high

Pure detection logic with no operating window or state management concerns.
"""

from __future__ import annotations

from typing import Any
from zoneinfo import ZoneInfo

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)

_ET = ZoneInfo("America/New_York")


class PreMarketHighBreakPattern(PatternModule):
    """Detect pre-market high breakout patterns.

    Args:
        min_pm_candles: Minimum pre-market candles required for valid PM high.
        min_pm_volume: Minimum total PM volume for detection-level check.
        breakout_margin_percent: Min close excess above PM high (e.g. 0.0015 = 0.15%).
        min_breakout_volume_ratio: Breakout bar volume vs avg PM bar volume.
        min_hold_bars: Consecutive bars above PM high before detection fires.
        pm_high_proximity_percent: Fraction of PM high for a candle to count
            as a "touch" (e.g. 0.002 = 0.2%).
        stop_buffer_atr_mult: ATR multiplier for stop below PM high.
        target_ratio: PM range multiplier for target above PM high.
        target_1_r: First target as R-multiple of risk.
        target_2_r: Second target as R-multiple of risk.
        min_score_threshold: Minimum score to emit detection.
        vwap_extended_pct: VWAP distance above which score degrades.
        gap_up_bonus_pct: Gap-up threshold for maximum gap context score.
    """

    def __init__(
        self,
        min_pm_candles: int = 3,
        min_pm_volume: float = 10_000.0,
        breakout_margin_percent: float = 0.0015,
        min_breakout_volume_ratio: float = 1.5,
        min_hold_bars: int = 2,
        pm_high_proximity_percent: float = 0.002,
        stop_buffer_atr_mult: float = 0.5,
        target_ratio: float = 1.5,
        target_1_r: float = 1.0,
        target_2_r: float = 2.0,
        min_score_threshold: float = 0.0,
        vwap_extended_pct: float = 0.05,
        gap_up_bonus_pct: float = 1.0,
    ) -> None:
        self._min_pm_candles = min_pm_candles
        self._min_pm_volume = min_pm_volume
        self._breakout_margin_percent = breakout_margin_percent
        self._min_breakout_volume_ratio = min_breakout_volume_ratio
        self._min_hold_bars = min_hold_bars
        self._pm_high_proximity_percent = pm_high_proximity_percent
        self._stop_buffer_atr_mult = stop_buffer_atr_mult
        self._target_ratio = target_ratio
        self._target_1_r = target_1_r
        self._target_2_r = target_2_r
        self._min_score_threshold = min_score_threshold
        self._vwap_extended_pct = vwap_extended_pct
        self._gap_up_bonus_pct = gap_up_bonus_pct

        # Prior closes populated via set_reference_data()
        self._prior_closes: dict[str, float] = {}

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Pre-Market High Break"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection.

        Includes pre-market candles in deque plus first few market-hours bars.
        """
        return 30

    def set_reference_data(self, data: dict[str, Any]) -> None:
        """Receive reference data from Universe Manager.

        Extracts ``prior_closes`` dict mapping symbol -> prior close price
        for gap context scoring. Handles missing key gracefully.

        Args:
            data: Reference data dict with optional ``prior_closes`` key.
        """
        self._prior_closes = data.get("prior_closes", {})

    def _split_pm_and_market(
        self, candles: list[CandleBar]
    ) -> tuple[list[CandleBar], list[CandleBar]]:
        """Split candles into pre-market and market-hours groups.

        Pre-market: timestamp in ET where hour < 9 or (hour == 9 and minute < 30).
        Market hours: everything else.

        Args:
            candles: Full candle list (oldest first).

        Returns:
            Tuple of (pre_market_candles, market_candles).
        """
        pm_candles: list[CandleBar] = []
        market_candles: list[CandleBar] = []

        for candle in candles:
            et_time = candle.timestamp.astimezone(_ET).time()
            if et_time.hour < 9 or (et_time.hour == 9 and et_time.minute < 30):
                pm_candles.append(candle)
            else:
                market_candles.append(candle)

        return pm_candles, market_candles

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

    def _compute_pm_quality(
        self, pm_candles: list[CandleBar], pm_high: float
    ) -> tuple[int, int]:
        """Assess PM high quality by counting touches and establishment duration.

        Args:
            pm_candles: Pre-market candle bars.
            pm_high: The computed PM high price.

        Returns:
            Tuple of (touch_count, establishment_bars) where establishment_bars
            is the number of bars from first touch of PM high to the last PM bar.
        """
        threshold = pm_high * self._pm_high_proximity_percent
        touch_count = 0
        first_touch_idx: int | None = None

        for i, candle in enumerate(pm_candles):
            if abs(candle.high - pm_high) <= threshold:
                touch_count += 1
                if first_touch_idx is None:
                    first_touch_idx = i

        establishment_bars = 0
        if first_touch_idx is not None:
            establishment_bars = len(pm_candles) - first_touch_idx

        return touch_count, establishment_bars

    def _resolve_prior_close(self, indicators: dict[str, float]) -> float | None:
        """Resolve prior close price from indicators or stored reference data.

        Args:
            indicators: Current indicator dict (may contain "symbol" key).

        Returns:
            Prior close price or None if unavailable.
        """
        if not self._prior_closes:
            return None

        symbol_key = str(indicators.get("symbol", ""))
        if symbol_key and symbol_key in self._prior_closes:
            return self._prior_closes[symbol_key]

        # Single-symbol optimization
        if len(self._prior_closes) == 1:
            return next(iter(self._prior_closes.values()))

        return None

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a pre-market high breakout pattern.

        Scans candles for PM bars, computes PM high, then checks for a
        breakout above PM high with volume and hold-duration confirmation.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (vwap, atr, symbol, etc.).

        Returns:
            PatternDetection if PM high break found, None otherwise.
        """
        pm_candles, market_candles = self._split_pm_and_market(candles)

        # --- PM high validation ---
        if len(pm_candles) < self._min_pm_candles:
            return None

        pm_volume = sum(c.volume for c in pm_candles)
        if pm_volume < self._min_pm_volume:
            return None

        pm_high = max(c.high for c in pm_candles)
        pm_low = min(c.low for c in pm_candles)
        if pm_high <= 0:
            return None

        pm_range = pm_high - pm_low

        # Need enough market bars for breakout + hold
        if len(market_candles) < self._min_hold_bars:
            return None

        # --- Breakout detection with hold confirmation ---
        breakout_threshold = pm_high * (1.0 + self._breakout_margin_percent)
        avg_pm_bar_volume = pm_volume / len(pm_candles)

        # Find first bar that closes above breakout threshold
        breakout_idx: int | None = None
        for i, bar in enumerate(market_candles):
            if bar.close >= breakout_threshold:
                # Volume confirmation on breakout bar
                if avg_pm_bar_volume > 0:
                    vol_ratio = bar.volume / avg_pm_bar_volume
                    if vol_ratio < self._min_breakout_volume_ratio:
                        continue
                breakout_idx = i
                break

        if breakout_idx is None:
            return None

        # Hold confirmation: min_hold_bars consecutive bars above PM high
        hold_start = breakout_idx
        hold_end = hold_start + self._min_hold_bars
        if hold_end > len(market_candles):
            return None

        for bar in market_candles[hold_start:hold_end]:
            if bar.close < pm_high:
                return None

        # --- Volume ratio for metadata ---
        breakout_bar = market_candles[breakout_idx]
        volume_ratio = (
            breakout_bar.volume / avg_pm_bar_volume
            if avg_pm_bar_volume > 0
            else 0.0
        )

        # --- ATR computation ---
        atr = indicators.get("atr", 0.0)
        if atr <= 0:
            atr = self._compute_atr(candles)
        if atr <= 0:
            return None

        # --- PM high quality ---
        touch_count, establishment_bars = self._compute_pm_quality(
            pm_candles, pm_high
        )

        # --- Gap context ---
        prior_close = self._resolve_prior_close(indicators)
        gap_percent = 0.0
        if prior_close is not None and prior_close > 0:
            gap_percent = (pm_candles[0].open - prior_close) / prior_close * 100

        # --- Entry, stop, target ---
        confirm_candle = market_candles[hold_end - 1]
        entry_price = confirm_candle.close
        stop_price = pm_high - self._stop_buffer_atr_mult * atr

        # Measured move target: PM range x ratio above PM high
        measured_target = pm_high + pm_range * self._target_ratio

        # R-multiple targets
        risk = entry_price - stop_price
        if risk <= 0:
            return None

        t1 = entry_price + risk * self._target_1_r
        t2 = entry_price + risk * self._target_2_r
        target_prices = (max(t1, measured_target), t2)

        # VWAP distance for metadata
        vwap = indicators.get("vwap", 0.0)
        vwap_distance_pct = 0.0
        if vwap > 0:
            vwap_distance_pct = (entry_price - vwap) / vwap

        # Confidence from detect (used for pre-score threshold check)
        confidence = self._compute_confidence(
            touch_count=touch_count,
            establishment_bars=establishment_bars,
            volume_ratio=volume_ratio,
            gap_percent=gap_percent,
            vwap_distance_pct=vwap_distance_pct,
        )

        if self._min_score_threshold > 0 and confidence < self._min_score_threshold:
            return None

        return PatternDetection(
            pattern_type="premarket_high_break",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=target_prices,
            metadata={
                "pm_high": round(pm_high, 4),
                "pm_low": round(pm_low, 4),
                "pm_range": round(pm_range, 4),
                "pm_candle_count": len(pm_candles),
                "pm_volume": round(pm_volume, 0),
                "pm_high_touch_count": touch_count,
                "pm_high_establishment_bars": establishment_bars,
                "breakout_volume_ratio": round(volume_ratio, 2),
                "gap_percent": round(gap_percent, 2),
                "vwap_distance_pct": round(vwap_distance_pct, 4),
                "hold_bars": self._min_hold_bars,
                "atr": round(atr, 4),
                "prior_close": round(prior_close, 4) if prior_close else None,
            },
        )

    def _compute_confidence(
        self,
        touch_count: int,
        establishment_bars: int,
        volume_ratio: float,
        gap_percent: float,
        vwap_distance_pct: float,
    ) -> float:
        """Compute detection confidence from pattern quality metrics.

        Args:
            touch_count: Number of PM candles touching PM high.
            establishment_bars: Bars from first PM high touch to market open.
            volume_ratio: Breakout volume / avg PM bar volume.
            gap_percent: Gap from prior close as percentage.
            vwap_distance_pct: Distance from VWAP as fraction.

        Returns:
            Confidence score 0-100.
        """
        # PM high quality (0-30): touches + establishment
        touch_score = min(touch_count / 5.0, 1.0) * 20
        estab_score = min(establishment_bars / 10.0, 1.0) * 10
        pm_quality_score = touch_score + estab_score

        # Volume (0-25)
        vol_score = min((volume_ratio - 1.0) / 2.0, 1.0) * 25 if volume_ratio > 1.0 else 0.0

        # Gap context (0-25)
        if gap_percent >= self._gap_up_bonus_pct:
            gap_score = 25.0
        elif gap_percent > 0:
            gap_score = 15.0 + (gap_percent / self._gap_up_bonus_pct) * 10.0
        elif gap_percent > -1.0:
            gap_score = 10.0
        else:
            gap_score = 5.0

        # VWAP distance (0-20)
        if vwap_distance_pct <= 0.02:
            vwap_score = 20.0
        elif vwap_distance_pct >= self._vwap_extended_pct:
            vwap_score = 4.0
        else:
            frac = (vwap_distance_pct - 0.02) / (self._vwap_extended_pct - 0.02)
            vwap_score = 20.0 - frac * 16.0

        return max(
            0.0,
            min(100.0, pm_quality_score + vol_score + gap_score + vwap_score),
        )

    def score(self, detection: PatternDetection) -> float:
        """Score a detected pre-market high break pattern (0-100).

        Delegates to _compute_confidence() to maintain a single scoring
        formula. Components (30/25/25/20 weighting):
            - PM high quality (30): more touches + longer establishment
            - Breakout volume (25): higher volume ratio
            - Gap context (25): gap up > flat > gap down
            - VWAP distance (20): closer to VWAP = healthier

        Args:
            detection: A previously detected PM high break pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata
        return self._compute_confidence(
            touch_count=int(meta.get("pm_high_touch_count", 1)),
            establishment_bars=int(meta.get("pm_high_establishment_bars", 0)),
            volume_ratio=float(meta.get("breakout_volume_ratio", 1.0)),
            gap_percent=float(meta.get("gap_percent", 0.0)),
            vwap_distance_pct=float(meta.get("vwap_distance_pct", 0.0)),
        )

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for PM High Break pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="min_pm_candles",
                param_type=int,
                default=self._min_pm_candles,
                min_value=1,
                max_value=10,
                step=1,
                description="Minimum pre-market candles for valid PM high",
                category="detection",
            ),
            PatternParam(
                name="min_pm_volume",
                param_type=float,
                default=self._min_pm_volume,
                min_value=1_000.0,
                max_value=100_000.0,
                step=5_000.0,
                description="Minimum total PM volume for detection",
                category="filtering",
            ),
            PatternParam(
                name="breakout_margin_percent",
                param_type=float,
                default=self._breakout_margin_percent,
                min_value=0.0005,
                max_value=0.005,
                step=0.0005,
                description="Min close excess above PM high (fraction, e.g. 0.0015 = 0.15%)",
                category="detection",
            ),
            PatternParam(
                name="min_breakout_volume_ratio",
                param_type=float,
                default=self._min_breakout_volume_ratio,
                min_value=1.0,
                max_value=3.0,
                step=0.25,
                description="Required breakout bar volume vs avg PM bar volume",
                category="filtering",
            ),
            PatternParam(
                name="min_hold_bars",
                param_type=int,
                default=self._min_hold_bars,
                min_value=1,
                max_value=5,
                step=1,
                description="Consecutive bars above PM high before detection fires",
                category="detection",
            ),
            PatternParam(
                name="pm_high_proximity_percent",
                param_type=float,
                default=self._pm_high_proximity_percent,
                min_value=0.001,
                max_value=0.005,
                step=0.001,
                description="Fraction of PM high for a touch (e.g. 0.002 = 0.2%)",
                category="detection",
            ),
            PatternParam(
                name="stop_buffer_atr_mult",
                param_type=float,
                default=self._stop_buffer_atr_mult,
                min_value=0.2,
                max_value=1.0,
                step=0.1,
                description="ATR multiplier for stop below PM high",
                category="trade",
            ),
            PatternParam(
                name="target_ratio",
                param_type=float,
                default=self._target_ratio,
                min_value=0.5,
                max_value=3.0,
                step=0.5,
                description="PM range multiplier for target above PM high",
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
                name="vwap_extended_pct",
                param_type=float,
                default=self._vwap_extended_pct,
                min_value=0.03,
                max_value=0.10,
                step=0.01,
                description="VWAP distance above which score degrades to minimum",
                category="scoring",
            ),
            PatternParam(
                name="gap_up_bonus_pct",
                param_type=float,
                default=self._gap_up_bonus_pct,
                min_value=0.5,
                max_value=3.0,
                step=0.5,
                description="Gap-up percent threshold for maximum gap context score",
                category="scoring",
            ),
        ]
