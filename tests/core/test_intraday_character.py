"""Tests for IntradayCharacterDetector (Sprint 27.6 S5)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from argus.core.config import IntradayConfig
from argus.core.events import CandleEvent
from argus.core.intraday_character import IntradayCharacterDetector

_ET = ZoneInfo("America/New_York")


def _make_config(**overrides: object) -> IntradayConfig:
    """Create an IntradayConfig with optional overrides."""
    return IntradayConfig(**overrides)  # type: ignore[arg-type]


def _make_candle(
    et_hour: int,
    et_minute: int,
    open_: float,
    high: float,
    low: float,
    close: float,
    volume: int = 100_000,
    symbol: str = "SPY",
) -> CandleEvent:
    """Create a CandleEvent at a given ET time on a fixed date."""
    et_dt = datetime(2026, 3, 25, et_hour, et_minute, tzinfo=_ET)
    utc_dt = et_dt.astimezone(UTC)
    return CandleEvent(
        timestamp=utc_dt,
        symbol=symbol,
        timeframe="1m",
        open=open_,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def _make_bars_trending_up(
    start_price: float, count: int, start_minute: int = 30
) -> list[CandleEvent]:
    """Generate a series of candles trending up from 9:{start_minute}."""
    bars: list[CandleEvent] = []
    price = start_price
    for i in range(count):
        minute = start_minute + i
        hour = 9 + minute // 60
        minute = minute % 60
        bars.append(
            _make_candle(
                hour, minute,
                open_=price, high=price + 0.30, low=price - 0.05,
                close=price + 0.25, volume=200_000,
            )
        )
        price += 0.25
    return bars


class TestConstruction:
    """Test construction with config."""

    def test_construction_with_default_config(self) -> None:
        config = _make_config()
        detector = IntradayCharacterDetector(config)
        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] is None
        assert snapshot["intraday_character"] is None

    def test_construction_with_custom_config(self) -> None:
        config = _make_config(
            min_spy_bars=5,
            drive_strength_trending=0.6,
            classification_times=["09:40", "10:15"],
        )
        detector = IntradayCharacterDetector(config)
        assert detector._config.min_spy_bars == 5
        assert detector._config.drive_strength_trending == 0.6


class TestClassifyTrending:
    """Test trending classification: strong open, sustained drift, few direction changes."""

    def test_classify_trending(self) -> None:
        config = _make_config(min_spy_bars=3, classification_times=["09:35"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        # Generate upward trending bars from 9:30 to 9:35
        bars = _make_bars_trending_up(start_price=500.0, count=6, start_minute=30)
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] == "trending"


class TestClassifyBreakout:
    """Test breakout classification: wide range + strong drive."""

    def test_classify_breakout(self) -> None:
        config = _make_config(
            min_spy_bars=3,
            classification_times=["09:35"],
            range_ratio_breakout=1.2,
            drive_strength_breakout=0.5,
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(1.0)  # Small prior range → high ratio

        # Big move: open 500, close 502 = drive 1.0, range 3.0/1.0 = 3.0
        bars = [
            _make_candle(9, 30, 500.0, 502.5, 499.5, 501.0, 300_000),
            _make_candle(9, 31, 501.0, 503.0, 500.5, 502.0, 300_000),
            _make_candle(9, 32, 502.0, 503.5, 501.5, 502.5, 300_000),
            _make_candle(9, 33, 502.5, 503.5, 502.0, 503.0, 300_000),
            _make_candle(9, 34, 503.0, 503.5, 502.5, 503.0, 300_000),
            _make_candle(9, 35, 503.0, 503.5, 502.5, 503.0, 300_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] == "breakout"


class TestClassifyReversal:
    """Test reversal classification: strong open + VWAP cross."""

    def test_classify_reversal(self) -> None:
        config = _make_config(
            min_spy_bars=3,
            classification_times=["09:48"],
            drive_strength_reversal=0.3,
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(25.0)  # Large prior range to keep ratio < 1.2

        # Bars: strong up for 8 bars, then sharp reversal down for 10 bars.
        # This ensures 5-bar direction flips: bars 0-7 rise, then bars 8+
        # drop below where they were 5 bars prior → direction change at ~bar 13.
        bars = [
            # Strong up move (bars 0-7)
            _make_candle(9, 30, 500.0, 501.5, 499.5, 501.0, 500_000),
            _make_candle(9, 31, 501.0, 502.0, 500.5, 502.0, 500_000),
            _make_candle(9, 32, 502.0, 503.0, 501.5, 503.0, 500_000),
            _make_candle(9, 33, 503.0, 504.0, 502.5, 504.0, 500_000),
            _make_candle(9, 34, 504.0, 505.0, 503.5, 505.0, 500_000),
            _make_candle(9, 35, 505.0, 506.0, 504.5, 506.0, 500_000),
            _make_candle(9, 36, 506.0, 507.0, 505.5, 507.0, 500_000),
            _make_candle(9, 37, 507.0, 508.0, 506.5, 508.0, 500_000),
            # Sharp reversal down (bars 8-17)
            _make_candle(9, 38, 508.0, 508.5, 505.0, 505.0, 800_000),
            _make_candle(9, 39, 505.0, 505.5, 503.0, 503.0, 800_000),
            _make_candle(9, 40, 503.0, 503.5, 501.0, 501.0, 800_000),
            _make_candle(9, 41, 501.0, 501.5, 499.0, 499.0, 800_000),
            _make_candle(9, 42, 499.0, 499.5, 497.0, 497.0, 800_000),
            _make_candle(9, 43, 497.0, 497.5, 495.0, 495.0, 800_000),
            _make_candle(9, 44, 495.0, 495.5, 493.0, 493.0, 800_000),
            _make_candle(9, 45, 493.0, 493.5, 491.0, 491.0, 800_000),
            _make_candle(9, 46, 491.0, 491.5, 489.0, 489.0, 800_000),
            _make_candle(9, 47, 489.0, 489.5, 487.0, 487.0, 800_000),
            _make_candle(9, 48, 487.0, 487.5, 485.0, 485.0, 800_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        # Drive = abs(485.0 - 500.0) / 2.0 = 7.5 → clamped to 1.0 ≥ 0.3
        # Direction changes: bars 5-7 rising vs 5-bar-ago, bars 13+ falling
        #   vs 5-bar-ago (which was rising) → at least 1 flip
        # VWAP slope: early bars up, overall slope down → flipped
        assert snapshot["intraday_character"] == "reversal"


class TestClassifyChoppy:
    """Test choppy classification: oscillating, many direction changes."""

    def test_classify_choppy(self) -> None:
        config = _make_config(
            min_spy_bars=3,
            classification_times=["09:42"],
            drive_strength_trending=0.4,
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(5.0)  # Large ATR → small drive strength
        detector.set_prior_day_range(10.0)  # Large range → small ratio

        # Oscillating bars: up, down, up, down...
        price = 500.0
        bars: list[CandleEvent] = []
        for i in range(13):
            minute = 30 + i
            hour = 9 + minute // 60
            minute = minute % 60
            delta = 0.10 if i % 2 == 0 else -0.10
            bars.append(
                _make_candle(
                    hour, minute,
                    price, price + 0.15, price - 0.15, price + delta,
                    volume=100_000,
                )
            )
            price += delta

        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] == "choppy"


class TestPriorityOrdering:
    """Verify breakout > reversal > trending > choppy when conditions overlap."""

    def test_breakout_beats_trending(self) -> None:
        """When both breakout and trending conditions are met, breakout wins."""
        config = _make_config(
            min_spy_bars=3,
            classification_times=["09:35"],
            range_ratio_breakout=1.2,
            drive_strength_breakout=0.5,
            drive_strength_trending=0.4,
            vwap_slope_trending=0.0001,
            max_direction_changes_trending=5,
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(1.0)

        # Strong trending up with wide range — meets both breakout and trending
        bars = _make_bars_trending_up(500.0, 6, start_minute=30)
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] == "breakout"


class TestPreMarket:
    """Test behavior before first classification time."""

    def test_pre_market_all_none(self) -> None:
        config = _make_config(
            min_spy_bars=3,
            classification_times=["09:35"],
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        # Only send bars at 9:30-9:33 (before 9:35 classification time)
        bars = [
            _make_candle(9, 30, 500.0, 500.5, 499.5, 500.2, 100_000),
            _make_candle(9, 31, 500.2, 500.7, 499.8, 500.4, 100_000),
            _make_candle(9, 32, 500.4, 500.9, 500.0, 500.5, 100_000),
            _make_candle(9, 33, 500.5, 501.0, 500.1, 500.6, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] is None
        assert snapshot["first_30min_range_ratio"] is None
        assert snapshot["vwap_slope"] is None
        assert snapshot["direction_change_count"] is None
        assert snapshot["intraday_character"] is None


class TestInsufficientBars:
    """Test None when insufficient bars at classification time."""

    def test_insufficient_bars_returns_none(self) -> None:
        config = _make_config(
            min_spy_bars=5,
            classification_times=["09:35"],
        )
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        # Only 2 bars, but at classification time
        bars = [
            _make_candle(9, 34, 500.0, 500.5, 499.5, 500.2, 100_000),
            _make_candle(9, 35, 500.2, 500.7, 499.8, 500.4, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] is None


class TestOpeningDriveStrength:
    """Test opening_drive_strength computation and clamping."""

    def test_drive_strength_basic(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(4.0)
        detector.set_prior_day_range(10.0)

        # open=500, close=502 → abs(2)/4.0 = 0.5
        bars = [
            _make_candle(9, 30, 500.0, 502.5, 499.5, 501.0, 100_000),
            _make_candle(9, 31, 501.0, 503.0, 500.5, 502.0, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] is not None
        assert abs(snapshot["opening_drive_strength"] - 0.5) < 0.01

    def test_drive_strength_clamped_at_1(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(0.5)  # Very small ATR → drive > 1.0

        bars = [
            _make_candle(9, 30, 500.0, 503.0, 499.0, 502.0, 100_000),
            _make_candle(9, 31, 502.0, 504.0, 501.0, 503.0, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] == 1.0

    def test_drive_strength_none_without_atr(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        # No set_atr_20 call

        bars = [
            _make_candle(9, 30, 500.0, 501.0, 499.5, 500.5, 100_000),
            _make_candle(9, 31, 500.5, 501.5, 500.0, 501.0, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] is None


class TestFirst30minRangeRatio:
    """Test first_30min_range_ratio computation."""

    def test_range_ratio_basic(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(2.0)

        # Bars: high=503, low=499 → range=4, ratio=4/2=2.0
        bars = [
            _make_candle(9, 30, 500.0, 503.0, 499.0, 501.0, 100_000),
            _make_candle(9, 31, 501.0, 502.0, 500.0, 501.5, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["first_30min_range_ratio"] is not None
        assert abs(snapshot["first_30min_range_ratio"] - 2.0) < 0.01

    def test_range_ratio_none_without_prior_range(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        # No set_prior_day_range call

        bars = [
            _make_candle(9, 30, 500.0, 503.0, 499.0, 501.0, 100_000),
            _make_candle(9, 31, 501.0, 502.0, 500.0, 501.5, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["first_30min_range_ratio"] is None


class TestVwapSlope:
    """Test vwap_slope computation."""

    def test_vwap_slope_positive_for_uptrend(self) -> None:
        config = _make_config(min_spy_bars=3, classification_times=["09:35"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(10.0)

        bars = _make_bars_trending_up(500.0, 6, start_minute=30)
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["vwap_slope"] is not None
        assert snapshot["vwap_slope"] > 0


class TestDirectionChangeCount:
    """Test direction_change_count computation."""

    def test_direction_changes_zero_for_steady_trend(self) -> None:
        config = _make_config(min_spy_bars=3, classification_times=["09:40"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(10.0)

        # Steadily rising: close[i] > close[i-5] for all i > 5
        bars = _make_bars_trending_up(500.0, 11, start_minute=30)
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["direction_change_count"] == 0

    def test_direction_changes_counted_for_oscillation(self) -> None:
        config = _make_config(min_spy_bars=3, classification_times=["09:42"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(10.0)

        # Create bars that oscillate with 5-bar lookback flips
        # Up for 6 bars, then down for 6 bars → at least 1 direction change
        price = 500.0
        bars: list[CandleEvent] = []
        for i in range(13):
            minute = 30 + i
            hour = 9 + minute // 60
            minute_val = minute % 60
            if i < 6:
                close = price + 0.3
                price = close
            else:
                close = price - 0.3
                price = close
            bars.append(
                _make_candle(hour, minute_val, price - 0.1, price + 0.2,
                             price - 0.2, close, 100_000)
            )

        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["direction_change_count"] is not None
        assert snapshot["direction_change_count"] >= 1


class TestReset:
    """Test reset clears all state."""

    def test_reset_clears_state(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        bars = [
            _make_candle(9, 30, 500.0, 501.0, 499.0, 500.5, 100_000),
            _make_candle(9, 31, 500.5, 501.5, 500.0, 501.0, 100_000),
        ]
        for bar in bars:
            detector.on_candle(bar)

        # Verify something was classified
        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] is not None

        # Reset and verify all None
        detector.reset()
        snapshot = detector.get_intraday_snapshot()
        assert snapshot["opening_drive_strength"] is None
        assert snapshot["first_30min_range_ratio"] is None
        assert snapshot["vwap_slope"] is None
        assert snapshot["direction_change_count"] is None
        assert snapshot["intraday_character"] is None


class TestSPYFiltering:
    """Test that non-SPY symbols are ignored."""

    def test_non_spy_candle_ignored(self) -> None:
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config)
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        # Send AAPL candles — should be ignored
        bars = [
            _make_candle(9, 30, 500.0, 501.0, 499.0, 500.5, 100_000, symbol="AAPL"),
            _make_candle(9, 31, 500.5, 501.5, 500.0, 501.0, 100_000, symbol="AAPL"),
        ]
        for bar in bars:
            detector.on_candle(bar)

        snapshot = detector.get_intraday_snapshot()
        assert snapshot["intraday_character"] is None
        assert len(detector._bars) == 0


class TestConfigurability:
    """Verify configurability of spy_symbol and first_bar_minutes."""

    def test_custom_spy_symbol_filters_correctly(self) -> None:
        """on_candle ignores non-matching symbols when spy_symbol is custom."""
        config = _make_config(min_spy_bars=2, classification_times=["09:31"])
        detector = IntradayCharacterDetector(config, spy_symbol="QQQ")
        detector.set_atr_20(2.0)
        detector.set_prior_day_range(3.0)

        # SPY candles should be ignored when spy_symbol is "QQQ"
        spy_bars = [
            _make_candle(9, 30, 500.0, 501.0, 499.0, 500.5, 100_000, symbol="SPY"),
            _make_candle(9, 31, 500.5, 501.5, 500.0, 501.0, 100_000, symbol="SPY"),
        ]
        for bar in spy_bars:
            detector.on_candle(bar)

        assert len(detector._bars) == 0
        assert detector.get_intraday_snapshot()["intraday_character"] is None

        # QQQ candles should be accepted
        qqq_bars = [
            _make_candle(9, 30, 500.0, 501.0, 499.0, 500.5, 100_000, symbol="QQQ"),
            _make_candle(9, 31, 500.5, 501.5, 500.0, 501.0, 100_000, symbol="QQQ"),
        ]
        for bar in qqq_bars:
            detector.on_candle(bar)

        assert len(detector._bars) == 2
        assert detector.get_intraday_snapshot()["intraday_character"] is not None

    def test_first_bar_minutes_config_affects_direction_count(self) -> None:
        """Direction change count uses first_bar_minutes from config, not hardcoded 5.

        12 bars with pattern: 3 up, 3 down, 3 up, 3 down (±1.0 each).
        Lookback=3 sees 3 direction flips; lookback=5 sees 2.
        """
        config_3 = _make_config(
            min_spy_bars=3,
            first_bar_minutes=3,
            classification_times=["09:41"],
        )
        config_5 = _make_config(
            min_spy_bars=3,
            first_bar_minutes=5,
            classification_times=["09:41"],
        )
        detector_3 = IntradayCharacterDetector(config_3)
        detector_5 = IntradayCharacterDetector(config_5)

        for det in (detector_3, detector_5):
            det.set_atr_20(2.0)
            det.set_prior_day_range(10.0)

        # 12 bars: 3 up (+1), 3 down (-1), 3 up (+1), 3 down (-1)
        # Closes: 501, 502, 503, 502, 501, 500, 501, 502, 503, 502, 501, 500
        price = 500.0
        deltas = [1.0] * 3 + [-1.0] * 3 + [1.0] * 3 + [-1.0] * 3
        bars: list[CandleEvent] = []
        for i, delta in enumerate(deltas):
            close = price + delta
            minute = 30 + i
            bars.append(
                _make_candle(
                    9, minute,
                    price, price + 0.5, price - 0.5, close, 200_000,
                )
            )
            price = close

        for bar in bars:
            detector_3.on_candle(bar)
            detector_5.on_candle(bar)

        snap_3 = detector_3.get_intraday_snapshot()
        snap_5 = detector_5.get_intraday_snapshot()

        assert snap_3["direction_change_count"] == 3
        assert snap_5["direction_change_count"] == 2
