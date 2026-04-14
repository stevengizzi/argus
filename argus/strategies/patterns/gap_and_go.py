"""Gap-and-Go continuation pattern detection module.

Detects gap-up continuations — stocks gapping up on high relative volume
that maintain momentum after the open. This is the first pattern to use
the ``set_reference_data()`` hook for prior close data.

Pattern anatomy:
    1. Gap: opening price gaps up >= min_gap_percent above prior close
    2. Volume: first N bars show elevated relative volume
    3. VWAP hold: price stays above VWAP for most of the check window
    4. Entry: first pullback re-entry or direct breakout above 5-min high
    5. Stop: below VWAP or first 5-min low (whichever is tighter)
    6. Target: gap size × target_ratio from entry

Pure detection logic with no operating window or state management concerns.
"""

from __future__ import annotations

from typing import Any

from argus.strategies.patterns.base import (
    CandleBar,
    PatternDetection,
    PatternModule,
    PatternParam,
)


class GapAndGoPattern(PatternModule):
    """Detect gap-and-go continuation patterns.

    Args:
        min_gap_percent: Minimum gap-up as percentage (e.g. 3.0 = 3%).
        min_relative_volume: Min avg volume of first bars vs prior day avg.
        volume_check_bars: Number of opening bars to check for volume.
        min_vwap_hold_bars: Min bars price must stay above VWAP.
        vwap_check_window: Number of bars in which to check VWAP hold.
        entry_mode: "first_pullback" or "direct_breakout".
        stop_mode: "tighter" (min of VWAP/5-min low), "vwap", or "five_min_low".
        target_ratio: Gap size multiplier for target from entry.
        prior_day_avg_volume: Override for prior day average volume (0 = use proxy).
        min_score_threshold: Minimum score to emit detection.
        gap_atr_cap: Gap size in ATR terms that earns maximum score credit.
        volume_score_cap: Volume ratio that earns maximum volume score credit.
        vwap_hold_score_divisor: Divisor for VWAP hold bars score normalization.
        catalyst_base_score: Base catalyst score when no quality data available.
    """

    def __init__(
        self,
        min_gap_percent: float = 3.0,
        min_relative_volume: float = 2.0,
        volume_check_bars: int = 5,
        min_vwap_hold_bars: int = 3,
        vwap_check_window: int = 8,
        entry_mode: str = "first_pullback",
        stop_mode: str = "tighter",
        target_ratio: float = 1.0,
        prior_day_avg_volume: float = 0.0,
        min_score_threshold: float = 0.0,
        gap_atr_cap: float = 5.0,
        volume_score_cap: float = 5.0,
        vwap_hold_score_divisor: float = 8.0,
        catalyst_base_score: float = 10.0,
        min_risk_per_share: float = 0.10,
    ) -> None:
        self._min_gap_percent = min_gap_percent
        self._min_relative_volume = min_relative_volume
        self._volume_check_bars = volume_check_bars
        self._min_vwap_hold_bars = min_vwap_hold_bars
        self._vwap_check_window = vwap_check_window
        self._entry_mode = entry_mode
        self._stop_mode = stop_mode
        self._target_ratio = target_ratio
        self._prior_day_avg_volume = prior_day_avg_volume
        self._min_score_threshold = min_score_threshold
        self._gap_atr_cap = gap_atr_cap
        self._volume_score_cap = volume_score_cap
        self._vwap_hold_score_divisor = vwap_hold_score_divisor
        self._catalyst_base_score = catalyst_base_score
        self._min_risk_per_share = min_risk_per_share

        # Prior closes populated via set_reference_data()
        self._prior_closes: dict[str, float] = {}

    @property
    def name(self) -> str:
        """Human-readable name of the pattern."""
        return "Gap-and-Go"

    @property
    def lookback_bars(self) -> int:
        """Number of recent candles needed for detection."""
        return 15

    def set_reference_data(self, data: dict[str, Any]) -> None:
        """Receive reference data from Universe Manager.

        Extracts ``prior_closes`` dict mapping symbol → prior close price.
        Handles missing key gracefully by storing empty dict.

        Args:
            data: Reference data dict with optional ``prior_closes`` key.
        """
        self._prior_closes = data.get("prior_closes", {})

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        """Detect a gap-and-go pattern in the given candle window.

        Args:
            candles: Recent candle history (most recent last).
            indicators: Current indicator values (vwap, atr, rvol, etc.).

        Returns:
            PatternDetection if gap-and-go found, None otherwise.
        """
        if len(candles) < 2:
            return None

        first_candle = candles[0]

        # --- Gap calculation ---
        # Prior close must be set via set_reference_data().
        # Resolve prior close: check indicators["symbol"] first (explicit),
        # then fall back to matching against all known prior closes.
        prior_close: float | None = None
        symbol_key = str(indicators.get("symbol", ""))
        if symbol_key and symbol_key in self._prior_closes:
            prior_close = self._prior_closes[symbol_key]
        elif self._prior_closes:
            # Single-symbol optimization: if only one prior close stored, use it
            if len(self._prior_closes) == 1:
                prior_close = next(iter(self._prior_closes.values()))
            else:
                # Match first candle open against prior closes to find best gap
                prior_close = self._find_matching_prior_close(first_candle.open)

        if prior_close is None or prior_close <= 0:
            return None

        gap_percent = (first_candle.open - prior_close) / prior_close * 100
        if gap_percent < self._min_gap_percent:
            return None

        gap_size = first_candle.open - prior_close

        # --- Volume confirmation ---
        vol_check_count = min(self._volume_check_bars, len(candles))
        vol_bars = candles[:vol_check_count]
        avg_open_volume = sum(c.volume for c in vol_bars) / vol_check_count

        # Use prior day avg volume or 20-bar rolling proxy
        ref_volume = self._prior_day_avg_volume
        if ref_volume <= 0:
            ref_volume = float(indicators.get("prior_day_avg_volume", 0))
        if ref_volume <= 0:
            # Proxy: 20-bar rolling average from available candles
            all_volumes = [c.volume for c in candles]
            if all_volumes:
                ref_volume = sum(all_volumes) / len(all_volumes)
        if ref_volume <= 0:
            return None

        volume_ratio = avg_open_volume / ref_volume
        if volume_ratio < self._min_relative_volume:
            return None

        # --- VWAP hold ---
        vwap = indicators.get("vwap")
        check_window = min(self._vwap_check_window, len(candles))
        vwap_bars = candles[:check_window]
        if vwap is not None and vwap > 0:
            bars_above_vwap = sum(1 for c in vwap_bars if c.close > vwap)
        else:
            # Without VWAP, use first candle open as proxy
            bars_above_vwap = sum(
                1 for c in vwap_bars if c.close > first_candle.open
            )

        if bars_above_vwap < self._min_vwap_hold_bars:
            return None

        # --- Entry detection ---
        if self._entry_mode == "first_pullback":
            entry_result = self._detect_first_pullback(candles)
        elif self._entry_mode == "direct_breakout":
            entry_result = self._detect_direct_breakout(candles)
        else:
            return None

        if entry_result is None:
            return None

        entry_price, entry_idx = entry_result

        # --- Stop calculation ---
        five_min_count = min(5, len(candles))
        five_min_low = min(c.low for c in candles[:five_min_count])

        if self._stop_mode == "vwap":
            stop_price = vwap if vwap is not None and vwap > 0 else five_min_low
        elif self._stop_mode == "five_min_low":
            stop_price = five_min_low
        else:
            # "tighter" — whichever is closer to (but below) entry
            if vwap is not None and vwap > 0:
                stop_price = max(vwap, five_min_low)
            else:
                stop_price = five_min_low

        # Stop must be below entry
        if stop_price >= entry_price:
            stop_price = five_min_low
        if stop_price >= entry_price:
            return None

        # Minimum risk guard — prevent degenerate R-multiples (DEF-152)
        risk_per_share = entry_price - stop_price
        if risk_per_share < self._min_risk_per_share:
            return None

        # ATR-relative minimum: risk must be at least 10% of ATR
        atr = indicators.get("atr", 0.0)
        if atr > 0 and risk_per_share < atr * 0.1:
            return None

        # --- Target ---
        target_price = entry_price + gap_size * self._target_ratio

        # Confidence based on gap quality
        confidence = min(gap_percent / 10.0, 1.0) * 50 + min(volume_ratio / 5.0, 1.0) * 50

        # Min score threshold filter
        if self._min_score_threshold > 0 and confidence < self._min_score_threshold:
            return None

        return PatternDetection(
            pattern_type="gap_and_go",
            confidence=confidence,
            entry_price=entry_price,
            stop_price=stop_price,
            target_prices=(target_price,),
            metadata={
                "gap_percent": round(gap_percent, 2),
                "gap_size": round(gap_size, 4),
                "volume_ratio": round(volume_ratio, 2),
                "bars_above_vwap": bars_above_vwap,
                "vwap_check_window": check_window,
                "entry_mode": self._entry_mode,
                "entry_bar_index": entry_idx,
                "five_min_low": round(five_min_low, 4),
                "prior_close": round(prior_close, 4),
                "has_catalyst": bool(indicators.get("has_catalyst", False)),
            },
        )

    def _find_matching_prior_close(self, open_price: float) -> float | None:
        """Find the prior close that produces a qualifying gap for this open.

        When the symbol is not explicitly provided via indicators, this
        method searches all known prior closes to find one that produces
        a gap >= min_gap_percent.  If exactly one match is found it is
        returned; otherwise returns None (ambiguous or no match).

        Args:
            open_price: First candle open price.

        Returns:
            Matching prior close price, or None.
        """
        matches: list[float] = []
        for pc in self._prior_closes.values():
            if pc <= 0:
                continue
            gap_pct = (open_price - pc) / pc * 100
            if gap_pct >= self._min_gap_percent:
                matches.append(pc)

        if len(matches) == 1:
            return matches[0]
        return None

    def _detect_first_pullback(
        self, candles: list[CandleBar]
    ) -> tuple[float, int] | None:
        """Detect first-pullback entry.

        Wait for first pullback (close < prior bar close), then re-entry
        when a subsequent bar closes above the pullback high.

        Args:
            candles: Candle window (most recent last).

        Returns:
            (entry_price, bar_index) or None.
        """
        if len(candles) < 3:
            return None

        # Find first pullback bar (close < prior bar close)
        pullback_idx: int | None = None
        for i in range(1, len(candles)):
            if candles[i].close < candles[i - 1].close:
                pullback_idx = i
                break

        if pullback_idx is None:
            return None

        pullback_high = candles[pullback_idx].high

        # Find re-entry: subsequent bar closes above pullback high
        for i in range(pullback_idx + 1, len(candles)):
            if candles[i].close > pullback_high:
                return candles[i].close, i

        return None

    def _detect_direct_breakout(
        self, candles: list[CandleBar]
    ) -> tuple[float, int] | None:
        """Detect direct-breakout entry.

        Enter when price breaks above the first 5-minute high.

        Args:
            candles: Candle window (most recent last).

        Returns:
            (entry_price, bar_index) or None.
        """
        five_min_count = min(5, len(candles))
        if five_min_count < 1:
            return None

        five_min_high = max(c.high for c in candles[:five_min_count])

        # Look for breakout after the initial 5-min window
        for i in range(five_min_count, len(candles)):
            if candles[i].close > five_min_high:
                return candles[i].close, i

        return None

    def score(self, detection: PatternDetection) -> float:
        """Score a detected gap-and-go pattern (0-100).

        Components:
            - Gap size relative to ATR (30): larger gap in ATR = higher
            - Volume ratio (30): higher relative volume = higher
            - VWAP hold (20): more bars above VWAP = higher
            - Catalyst presence (20): catalyst present = higher

        Args:
            detection: A previously detected gap-and-go pattern.

        Returns:
            Quality score between 0 and 100.
        """
        meta = detection.metadata

        # Gap size in ATR terms (0-30)
        gap_percent = float(meta.get("gap_percent", 0))
        gap_atr_ratio = gap_percent / max(self._gap_atr_cap, 0.01)
        gap_score = min(gap_atr_ratio, 1.0) * 30

        # Volume ratio (0-30)
        vol_ratio = float(meta.get("volume_ratio", 1.0))
        vol_score = min(vol_ratio / max(self._volume_score_cap, 0.01), 1.0) * 30

        # VWAP hold bars (0-20)
        bars_above = float(meta.get("bars_above_vwap", 0))
        vwap_score = min(bars_above / max(self._vwap_hold_score_divisor, 0.01), 1.0) * 20

        # Catalyst presence (0-20)
        has_catalyst = bool(meta.get("has_catalyst", False))
        catalyst_score = 20.0 if has_catalyst else self._catalyst_base_score

        total = gap_score + vol_score + vwap_score + catalyst_score
        return max(0.0, min(100.0, total))

    def get_default_params(self) -> list[PatternParam]:
        """Return structured parameter metadata for Gap-and-Go pattern.

        Returns:
            List of PatternParam describing each tunable parameter.
        """
        return [
            PatternParam(
                name="min_gap_percent",
                param_type=float,
                default=self._min_gap_percent,
                min_value=1.0,
                max_value=10.0,
                step=1.0,
                description="Minimum gap-up percentage to qualify",
                category="detection",
            ),
            PatternParam(
                name="min_relative_volume",
                param_type=float,
                default=self._min_relative_volume,
                min_value=1.0,
                max_value=5.0,
                step=0.5,
                description="Min avg volume of first bars vs prior day",
                category="filtering",
            ),
            PatternParam(
                name="volume_check_bars",
                param_type=int,
                default=self._volume_check_bars,
                min_value=2,
                max_value=10,
                step=1,
                description="Number of opening bars to check for volume",
                category="filtering",
            ),
            PatternParam(
                name="min_vwap_hold_bars",
                param_type=int,
                default=self._min_vwap_hold_bars,
                min_value=1,
                max_value=10,
                step=1,
                description="Min bars price must stay above VWAP",
                category="detection",
            ),
            PatternParam(
                name="vwap_check_window",
                param_type=int,
                default=self._vwap_check_window,
                min_value=3,
                max_value=15,
                step=1,
                description="Number of bars in VWAP hold check window",
                category="detection",
            ),
            PatternParam(
                name="entry_mode",
                param_type=str,
                default=self._entry_mode,
                min_value=None,
                max_value=None,
                step=None,
                description=(
                    'Entry mode: "first_pullback" (wait for pullback re-entry) '
                    'or "direct_breakout" (break above 5-min high)'
                ),
                category="detection",
            ),
            PatternParam(
                name="stop_mode",
                param_type=str,
                default=self._stop_mode,
                min_value=None,
                max_value=None,
                step=None,
                description=(
                    'Stop mode: "tighter" (min of VWAP/5-min low), '
                    '"vwap", or "five_min_low"'
                ),
                category="detection",
            ),
            PatternParam(
                name="target_ratio",
                param_type=float,
                default=self._target_ratio,
                min_value=0.5,
                max_value=3.0,
                step=0.5,
                description="Gap size multiplier for target from entry",
                category="trade",
            ),
            PatternParam(
                name="prior_day_avg_volume",
                param_type=float,
                default=self._prior_day_avg_volume,
                min_value=0.0,
                max_value=10_000_000.0,
                step=100_000.0,
                description="Override for prior day avg volume (0 = use proxy)",
                category="filtering",
            ),
            PatternParam(
                name="min_score_threshold",
                param_type=float,
                default=self._min_score_threshold,
                min_value=0.0,
                max_value=40.0,
                step=10.0,
                description="Minimum score to emit detection",
                category="filtering",
            ),
            PatternParam(
                name="gap_atr_cap",
                param_type=float,
                default=self._gap_atr_cap,
                min_value=2.0,
                max_value=10.0,
                step=1.0,
                description="Gap pct cap for maximum gap score credit",
                category="scoring",
            ),
            PatternParam(
                name="volume_score_cap",
                param_type=float,
                default=self._volume_score_cap,
                min_value=2.0,
                max_value=10.0,
                step=1.0,
                description="Volume ratio cap for maximum volume score",
                category="scoring",
            ),
            PatternParam(
                name="vwap_hold_score_divisor",
                param_type=float,
                default=self._vwap_hold_score_divisor,
                min_value=3.0,
                max_value=15.0,
                step=1.0,
                description="Divisor for VWAP hold bars score normalization",
                category="scoring",
            ),
            PatternParam(
                name="catalyst_base_score",
                param_type=float,
                default=self._catalyst_base_score,
                min_value=0.0,
                max_value=20.0,
                step=5.0,
                description="Base catalyst score when no quality data available",
                category="scoring",
            ),
            PatternParam(
                name="min_risk_per_share",
                param_type=float,
                default=self._min_risk_per_share,
                min_value=0.05,
                max_value=0.50,
                step=0.05,
                description="Minimum absolute risk (entry - stop) to emit signal",
                category="filtering",
            ),
        ]
