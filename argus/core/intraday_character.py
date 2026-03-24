"""Intraday character detection for the regime intelligence subsystem.

Classifies intraday market character from SPY 1-minute candles at configurable
timestamps. Produces intermediate metrics (opening drive strength, range ratio,
VWAP slope, direction change count) and a categorical classification:
breakout, reversal, trending, or choppy.

Sprint 27.6, Session 5.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import time
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import numpy as np

if TYPE_CHECKING:
    from argus.core.config import IntradayConfig
    from argus.core.events import CandleEvent

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


@dataclass
class _BarRecord:
    """Internal representation of a single accumulated SPY bar."""

    timestamp_et: time
    open: float
    high: float
    low: float
    close: float
    volume: int


class IntradayCharacterDetector:
    """Classifies intraday market character from SPY 1-minute candles.

    Accumulates SPY bars and runs classification at configurable ET timestamps.
    All thresholds are read from IntradayConfig — nothing is hardcoded.

    Classification priority (first match wins):
        1. Breakout — wide range + strong opening drive
        2. Reversal — strong open + direction change + VWAP slope flip
        3. Trending — sustained drift, few direction changes, meaningful VWAP slope
        4. Choppy — default fallback

    Args:
        config: IntradayConfig with all threshold fields.
    """

    def __init__(self, config: IntradayConfig, spy_symbol: str = "SPY") -> None:
        """Initialize detector with configuration.

        Args:
            config: IntradayConfig containing thresholds and classification times.
            spy_symbol: Symbol to filter for (default "SPY"). Sourced from
                OrchestratorConfig.spy_symbol at wiring time.
        """
        self._config = config
        self._spy_symbol = spy_symbol
        self._classification_times = [
            time(int(t.split(":")[0]), int(t.split(":")[1]))
            for t in config.classification_times
        ]
        self._bars: list[_BarRecord] = []
        self._prior_day_range: float | None = None
        self._atr_20: float | None = None
        self._classified: bool = False

        # Snapshot fields
        self._opening_drive_strength: float | None = None
        self._first_30min_range_ratio: float | None = None
        self._vwap_slope: float | None = None
        self._direction_change_count: int | None = None
        self._intraday_character: str | None = None

    def on_candle(self, event: CandleEvent) -> None:
        """Accept a candle event. Only SPY candles are processed.

        Accumulates bars and triggers classification at configured ET timestamps.

        Args:
            event: CandleEvent from the Event Bus.
        """
        if event.symbol != self._spy_symbol:
            return

        bar_time_et = event.timestamp.astimezone(_ET).time()

        self._bars.append(
            _BarRecord(
                timestamp_et=bar_time_et,
                open=event.open,
                high=event.high,
                low=event.low,
                close=event.close,
                volume=event.volume,
            )
        )

        # Check if this bar's time matches any classification time
        for ct in self._classification_times:
            if bar_time_et >= ct and not self._classified:
                self._run_classification()
                break

    def get_intraday_snapshot(self) -> dict[str, float | int | str | None]:
        """Return current intraday metrics and classification.

        Returns:
            Dictionary with all intermediate metrics and character classification.
            Values are None until sufficient data and a classification time is reached.
        """
        return {
            "opening_drive_strength": self._opening_drive_strength,
            "first_30min_range_ratio": self._first_30min_range_ratio,
            "vwap_slope": self._vwap_slope,
            "direction_change_count": self._direction_change_count,
            "intraday_character": self._intraday_character,
        }

    def set_prior_day_range(self, range_value: float) -> None:
        """Set the prior day's full range for ratio computation.

        Args:
            range_value: Prior day high - low range in dollars.
        """
        self._prior_day_range = range_value

    def set_atr_20(self, atr_value: float) -> None:
        """Set the 20-day ATR for drive strength normalization.

        Args:
            atr_value: 20-day average true range in dollars.
        """
        self._atr_20 = atr_value

    def reset(self) -> None:
        """Clear all state for a new trading day."""
        self._bars.clear()
        self._prior_day_range = None
        self._atr_20 = None
        self._classified = False
        self._opening_drive_strength = None
        self._first_30min_range_ratio = None
        self._vwap_slope = None
        self._direction_change_count = None
        self._intraday_character = None

    # ------------------------------------------------------------------
    # Internal classification logic
    # ------------------------------------------------------------------

    def _run_classification(self) -> None:
        """Run classification on accumulated bars.

        If fewer than min_spy_bars candles are available, all metrics remain None
        and classification is not marked complete (will retry at next time).
        """
        if len(self._bars) < self._config.min_spy_bars:
            logger.debug(
                "Insufficient bars for classification: %d < %d",
                len(self._bars),
                self._config.min_spy_bars,
            )
            return

        # Compute intermediate metrics
        self._opening_drive_strength = self._compute_opening_drive_strength()
        self._first_30min_range_ratio = self._compute_first_30min_range_ratio()
        self._vwap_slope = self._compute_vwap_slope()
        self._direction_change_count = self._compute_direction_change_count()

        # Classify using priority rules
        self._intraday_character = self._classify_character()
        self._classified = True

        logger.info(
            "Intraday character classified: %s (drive=%.3f, range_ratio=%.3f, "
            "vwap_slope=%.6f, dir_changes=%d)",
            self._intraday_character,
            self._opening_drive_strength or 0.0,
            self._first_30min_range_ratio or 0.0,
            self._vwap_slope or 0.0,
            self._direction_change_count or 0,
        )

    def _compute_opening_drive_strength(self) -> float | None:
        """Compute opening drive strength: abs(close_at_N - open_930) / atr_20.

        Clamped to [0.0, 1.0]. Returns None if ATR is not set or zero.
        """
        if self._atr_20 is None or self._atr_20 <= 0:
            return None

        open_930 = self._bars[0].open
        latest_close = self._bars[-1].close

        raw = abs(latest_close - open_930) / self._atr_20
        return min(max(raw, 0.0), 1.0)

    def _compute_first_30min_range_ratio(self) -> float | None:
        """Compute range of accumulated bars / prior day range.

        Returns None if prior day range is not set or zero.
        """
        if self._prior_day_range is None or self._prior_day_range <= 0:
            return None

        high_30 = max(bar.high for bar in self._bars)
        low_30 = min(bar.low for bar in self._bars)

        return (high_30 - low_30) / self._prior_day_range

    def _compute_vwap_slope(self) -> float | None:
        """Compute VWAP slope via linear regression, normalized by price.

        VWAP is computed cumulatively across accumulated bars. The slope of
        a linear regression over the VWAP series is then normalized by the
        mean price to produce a dimensionless rate.

        Returns None if fewer than 2 bars.
        """
        if len(self._bars) < 2:
            return None

        # Compute cumulative VWAP
        cum_volume = 0.0
        cum_tp_volume = 0.0
        vwap_series: list[float] = []

        for bar in self._bars:
            typical_price = (bar.high + bar.low + bar.close) / 3.0
            cum_tp_volume += typical_price * bar.volume
            cum_volume += bar.volume
            if cum_volume > 0:
                vwap_series.append(cum_tp_volume / cum_volume)
            else:
                vwap_series.append(typical_price)

        # Linear regression slope: y = VWAP, x = bar index
        x = np.arange(len(vwap_series), dtype=np.float64)
        y = np.array(vwap_series, dtype=np.float64)

        # slope = cov(x,y) / var(x)
        x_mean = x.mean()
        y_mean = y.mean()
        var_x = ((x - x_mean) ** 2).sum()
        if var_x == 0:
            return 0.0

        slope = ((x - x_mean) * (y - y_mean)).sum() / var_x

        # Normalize by mean price
        mean_price = y_mean if y_mean > 0 else 1.0
        return float(slope / mean_price)

    def _compute_direction_change_count(self) -> int:
        """Count N-bar close direction flips (N = first_bar_minutes from config).

        Compares close[i] vs close[i-N] for each bar to determine direction,
        then counts how many times direction flips from positive to negative
        or vice versa.
        """
        lookback = self._config.first_bar_minutes
        if len(self._bars) <= lookback:
            return 0

        directions: list[int] = []
        for i in range(lookback, len(self._bars)):
            diff = self._bars[i].close - self._bars[i - lookback].close
            if diff > 0:
                directions.append(1)
            elif diff < 0:
                directions.append(-1)
            # Skip zero-diff bars (no direction)

        changes = 0
        for i in range(1, len(directions)):
            if directions[i] != directions[i - 1]:
                changes += 1

        return changes

    def _classify_character(self) -> str:
        """Apply priority classification rules. First match wins.

        Priority: Breakout > Reversal > Trending > Choppy.
        """
        drive = self._opening_drive_strength
        range_ratio = self._first_30min_range_ratio
        slope = self._vwap_slope
        dir_changes = self._direction_change_count

        # Breakout: wide range + strong drive
        if (
            range_ratio is not None
            and drive is not None
            and range_ratio >= self._config.range_ratio_breakout
            and drive >= self._config.drive_strength_breakout
        ):
            return "breakout"

        # Reversal: strong open + direction change + VWAP slope flip
        if (
            drive is not None
            and dir_changes is not None
            and slope is not None
            and drive >= self._config.drive_strength_reversal
            and dir_changes >= 1
            and self._vwap_slope_flipped()
        ):
            return "reversal"

        # Trending: sustained drift, few direction changes, meaningful slope
        if (
            drive is not None
            and dir_changes is not None
            and slope is not None
            and drive >= self._config.drive_strength_trending
            and dir_changes <= self._config.max_direction_changes_trending
            and abs(slope) >= self._config.vwap_slope_trending
        ):
            return "trending"

        # Choppy: default
        return "choppy"

    def _vwap_slope_flipped(self) -> bool:
        """Check if VWAP slope sign flipped vs first N bars (N = first_bar_minutes).

        Computes VWAP slope over first N bars, then checks if the overall
        VWAP slope has the opposite sign.
        """
        lookback = self._config.first_bar_minutes
        if len(self._bars) < lookback + 1 or self._vwap_slope is None:
            return False

        # Compute VWAP for first N bars
        cum_volume = 0.0
        cum_tp_volume = 0.0
        early_vwaps: list[float] = []

        for bar in self._bars[:lookback]:
            tp = (bar.high + bar.low + bar.close) / 3.0
            cum_tp_volume += tp * bar.volume
            cum_volume += bar.volume
            if cum_volume > 0:
                early_vwaps.append(cum_tp_volume / cum_volume)
            else:
                early_vwaps.append(tp)

        if len(early_vwaps) < 2:
            return False

        # Simple slope: last - first
        early_slope = early_vwaps[-1] - early_vwaps[0]

        # Check sign flip: opposite signs means a flip
        if early_slope > 0 and self._vwap_slope < 0:
            return True
        if early_slope < 0 and self._vwap_slope > 0:
            return True

        return False
