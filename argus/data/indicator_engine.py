"""IndicatorEngine — Shared indicator computation for all DataServices.

Extracts common indicator logic from ReplayDataService, BacktestDataService,
AlpacaDataService, and DatabentoDataService into a single reusable engine.

Decision reference: DEF-013 (IndicatorEngine extraction)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date

logger = logging.getLogger(__name__)


@dataclass
class IndicatorValues:
    """Computed indicator values for a single bar update.

    None means the indicator doesn't have enough data yet
    (e.g., SMA-50 before 50 bars, ATR before 14 bars).
    """

    vwap: float | None = None
    atr_14: float | None = None
    sma_9: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    rvol: float | None = None

    def as_dict(self) -> dict[str, float | None]:
        """Return as {indicator_name: value} dict for cache/event iteration."""
        return {
            "vwap": self.vwap,
            "atr_14": self.atr_14,
            "sma_9": self.sma_9,
            "sma_20": self.sma_20,
            "sma_50": self.sma_50,
            "rvol": self.rvol,
        }


class IndicatorEngine:
    """Stateful indicator computation engine for a single symbol.

    Maintains rolling state for all V1 indicators:
    - VWAP: Cumulative typical_price * volume / cumulative volume (daily reset)
    - ATR(14): Wilder's smoothing (exponential) of True Range
    - SMA(9/20/50): Simple moving averages of close prices
    - RVOL: Relative volume vs. first 20 bars of day baseline (daily reset)

    Usage:
        engine = IndicatorEngine(symbol="AAPL")
        values = engine.update(open_, high, low, close, volume, timestamp_date)
        # values.vwap, values.atr_14, etc.

        # At day boundary (or call reset_daily() manually):
        engine.reset_daily()

    Thread safety: NOT thread-safe. Each DataService should own its
    own engine instances and call them from a single thread/task.

    Args:
        symbol: The ticker symbol this engine computes indicators for.
    """

    def __init__(self, symbol: str) -> None:
        """Initialize the indicator engine for a symbol.

        Args:
            symbol: The ticker symbol this engine tracks.
        """
        self.symbol = symbol

        # --- VWAP state (daily reset) ---
        self._vwap_cum_tp_vol: float = 0.0  # cumulative(typical_price * volume)
        self._vwap_cum_vol: int = 0  # cumulative(volume)
        self._vwap_value: float | None = None

        # --- ATR(14) state (carries across days) ---
        self._atr_period: int = 14
        self._atr_value: float | None = None
        self._atr_tr_history: list[float] = []
        self._prev_close: float | None = None

        # --- SMA state (carries across days) ---
        self._close_history: list[float] = []

        # --- RVOL state (daily reset) ---
        # Uses first 20 bars of the day as baseline (matches existing behavior)
        self._rvol_volume_samples: list[int] = []
        self._rvol_baseline_volume: float | None = None
        self._rvol_value: float | None = None

        # --- Date tracking for auto-reset ---
        self._current_date: date | str | None = None

        # --- Bar count (for diagnostics) ---
        self._total_bars: int = 0

    def update(
        self,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        timestamp_date: date | str | None = None,
    ) -> IndicatorValues:
        """Process a new 1-minute bar and return updated indicator values.

        Args:
            open_: Bar open price (unused but included for API completeness).
            high: Bar high price.
            low: Bar low price.
            close: Bar close price.
            volume: Bar volume.
            timestamp_date: Date of this bar (date object or 'YYYY-MM-DD' string).
                Used for automatic daily reset detection. If None, caller must
                manage reset_daily() manually.

        Returns:
            IndicatorValues with current values (None if insufficient data).
        """
        # Normalize timestamp_date to string for comparison (matches existing behavior)
        date_str: str | None = None
        if timestamp_date is not None:
            if isinstance(timestamp_date, date):
                date_str = timestamp_date.strftime("%Y-%m-%d")
            else:
                date_str = timestamp_date

        # Auto-detect day boundary if timestamp_date provided
        if (
            date_str is not None
            and self._current_date is not None
            and date_str != self._current_date
        ):
            self._do_daily_reset()
        if date_str is not None:
            self._current_date = date_str

        self._total_bars += 1

        # --- VWAP ---
        vwap = self._update_vwap(high, low, close, volume)

        # --- ATR(14) ---
        atr_14 = self._update_atr(high, low, close)

        # --- SMAs ---
        self._close_history.append(close)
        sma_9 = self._compute_sma(9)
        sma_20 = self._compute_sma(20)
        sma_50 = self._compute_sma(50)

        # --- RVOL ---
        rvol = self._update_rvol(volume)

        # Update prev_close for next bar's TR calculation
        self._prev_close = close

        return IndicatorValues(
            vwap=vwap,
            atr_14=atr_14,
            sma_9=sma_9,
            sma_20=sma_20,
            sma_50=sma_50,
            rvol=rvol,
        )

    def reset_daily(self) -> None:
        """Reset daily-scoped indicators. Call at market open / day boundary.

        Resets: VWAP accumulators, RVOL baseline + samples
        Preserves: ATR (rolling), SMA (rolling), prev_close
        """
        self._do_daily_reset()

    def _do_daily_reset(self) -> None:
        """Internal daily reset implementation.

        Resets VWAP and RVOL state. ATR and SMA carry over.
        """
        # Reset VWAP
        self._vwap_cum_tp_vol = 0.0
        self._vwap_cum_vol = 0
        self._vwap_value = None

        # Reset RVOL (including baseline — it's recalculated from first 20 bars)
        self._rvol_volume_samples = []
        self._rvol_baseline_volume = None
        self._rvol_value = None

    def _update_vwap(self, high: float, low: float, close: float, volume: int) -> float | None:
        """Cumulative VWAP: sum(TP * vol) / sum(vol). TP = (H+L+C)/3.

        Args:
            high: Bar high price.
            low: Bar low price.
            close: Bar close price.
            volume: Bar volume.

        Returns:
            Current VWAP value, or None if no volume yet.
        """
        typical_price = (high + low + close) / 3.0
        self._vwap_cum_tp_vol += typical_price * volume
        self._vwap_cum_vol += volume

        if self._vwap_cum_vol > 0:
            self._vwap_value = self._vwap_cum_tp_vol / self._vwap_cum_vol
            return self._vwap_value

        return None

    def _update_atr(self, high: float, low: float, close: float) -> float | None:
        """ATR(14) using Wilder's smoothing.

        True Range = max(H-L, |H-prevC|, |L-prevC|).
        First ATR = simple average of first 14 TRs.
        Subsequent: ATR = (prev_ATR * 13 + TR) / 14 (Wilder's smoothing).

        Args:
            high: Bar high price.
            low: Bar low price.
            close: Bar close price.

        Returns:
            Current ATR(14) value, or None if fewer than 14 bars processed.
        """
        if self._prev_close is not None:
            true_range = max(
                high - low,
                abs(high - self._prev_close),
                abs(low - self._prev_close),
            )
            self._atr_tr_history.append(true_range)

            if len(self._atr_tr_history) >= self._atr_period:
                if self._atr_value is None:
                    # First ATR: simple average of last 14 TRs
                    self._atr_value = (
                        sum(self._atr_tr_history[-self._atr_period :]) / self._atr_period
                    )
                else:
                    # Wilder's smoothing: ATR = ((ATR_prev * 13) + TR) / 14
                    self._atr_value = (
                        self._atr_value * (self._atr_period - 1) + true_range
                    ) / self._atr_period

                return self._atr_value

        return None

    def _compute_sma(self, period: int) -> float | None:
        """SMA of close prices over `period` bars.

        Args:
            period: Number of bars for the moving average.

        Returns:
            SMA value, or None if fewer than `period` bars in history.
        """
        if len(self._close_history) < period:
            return None
        # Use the last `period` values from the history
        return sum(self._close_history[-period:]) / period

    def _update_rvol(self, volume: int) -> float | None:
        """Relative Volume: cumulative avg volume today / baseline avg volume.

        Baseline is computed from the first 20 bars of the day.
        RVOL = cumulative_volume / (baseline_avg_volume * bar_count).

        Args:
            volume: Bar volume.

        Returns:
            Current RVOL value, or None if baseline not yet established.
        """
        self._rvol_volume_samples.append(volume)

        if len(self._rvol_volume_samples) >= 20:
            if self._rvol_baseline_volume is None:
                # Set baseline from first 20 candles
                self._rvol_baseline_volume = sum(self._rvol_volume_samples[:20]) / 20

            if self._rvol_baseline_volume > 0:
                # RVOL = current cumulative volume / expected cumulative volume
                cumulative_volume = sum(self._rvol_volume_samples)
                expected_volume = self._rvol_baseline_volume * len(self._rvol_volume_samples)
                self._rvol_value = cumulative_volume / expected_volume
                return self._rvol_value

        return None

    @property
    def bar_count(self) -> int:
        """Total bars processed by this engine."""
        return self._total_bars

    @property
    def vwap(self) -> float | None:
        """Current VWAP value."""
        return self._vwap_value

    @property
    def atr_14(self) -> float | None:
        """Current ATR(14) value."""
        return self._atr_value

    @property
    def sma_9(self) -> float | None:
        """Current SMA(9) value."""
        return self._compute_sma(9)

    @property
    def sma_20(self) -> float | None:
        """Current SMA(20) value."""
        return self._compute_sma(20)

    @property
    def sma_50(self) -> float | None:
        """Current SMA(50) value."""
        return self._compute_sma(50)

    @property
    def rvol(self) -> float | None:
        """Current RVOL value."""
        return self._rvol_value

    def get_current_values(self) -> IndicatorValues:
        """Return the most recently computed indicator values.

        Useful for warm-up — after feeding historical bars, the caller
        can read the current state without needing to process another bar.

        Returns:
            IndicatorValues with current cached values.
        """
        return IndicatorValues(
            vwap=self._vwap_value,
            atr_14=self._atr_value,
            sma_9=self._compute_sma(9),
            sma_20=self._compute_sma(20),
            sma_50=self._compute_sma(50),
            rvol=self._rvol_value,
        )

    def warm_up(self, bars: list[dict]) -> None:
        """Feed historical bars to seed indicator state.

        Iterates through bar dicts (expected keys: open, high, low, close,
        volume, timestamp) and calls update() for each.

        Args:
            bars: List of bar dictionaries with OHLCV data.
        """
        for bar in bars:
            timestamp = bar.get("timestamp")
            timestamp_date = None
            if timestamp is not None:
                if hasattr(timestamp, "strftime"):
                    timestamp_date = timestamp.strftime("%Y-%m-%d")
                elif hasattr(timestamp, "date"):
                    timestamp_date = timestamp.date()

            self.update(
                open_=bar["open"],
                high=bar["high"],
                low=bar["low"],
                close=bar["close"],
                volume=int(bar["volume"]),
                timestamp_date=timestamp_date,
            )
