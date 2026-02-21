"""Tests for IndicatorEngine — shared indicator computation logic.

These tests verify the engine in isolation, forming the canonical specification
for indicator behavior. The engine must match the existing DataService
implementations exactly.
"""

from datetime import date

import pytest

from argus.data.indicator_engine import IndicatorEngine, IndicatorValues


class TestIndicatorValues:
    """Tests for the IndicatorValues dataclass."""

    def test_default_values_are_none(self) -> None:
        """All indicator values default to None."""
        values = IndicatorValues()
        assert values.vwap is None
        assert values.atr_14 is None
        assert values.sma_9 is None
        assert values.sma_20 is None
        assert values.sma_50 is None
        assert values.rvol is None

    def test_as_dict_format(self) -> None:
        """as_dict() returns correct key-value structure."""
        values = IndicatorValues(vwap=100.5, atr_14=2.3, sma_9=99.0)
        result = values.as_dict()

        assert result["vwap"] == 100.5
        assert result["atr_14"] == 2.3
        assert result["sma_9"] == 99.0
        assert result["sma_20"] is None
        assert result["sma_50"] is None
        assert result["rvol"] is None

    def test_as_dict_keys(self) -> None:
        """as_dict() returns all expected indicator keys."""
        values = IndicatorValues()
        result = values.as_dict()

        expected_keys = {"vwap", "atr_14", "sma_9", "sma_20", "sma_50", "rvol"}
        assert set(result.keys()) == expected_keys


class TestVWAP:
    """Tests for VWAP computation."""

    def test_vwap_basic_computation(self) -> None:
        """VWAP is computed as cumulative(TP * vol) / cumulative(vol)."""
        engine = IndicatorEngine(symbol="TEST")

        # First bar: H=102, L=98, C=100, V=1000
        # TP = (102 + 98 + 100) / 3 = 100
        # VWAP = (100 * 1000) / 1000 = 100
        values = engine.update(99.0, 102.0, 98.0, 100.0, 1000)
        assert values.vwap == pytest.approx(100.0)

        # Second bar: H=105, L=101, C=103, V=2000
        # TP = (105 + 101 + 103) / 3 = 103
        # Cumulative: (100*1000 + 103*2000) / (1000 + 2000) = 306000/3000 = 102
        values = engine.update(101.0, 105.0, 101.0, 103.0, 2000)
        assert values.vwap == pytest.approx(102.0)

    def test_vwap_zero_volume_bar(self) -> None:
        """Zero-volume bars still update VWAP (matches existing behavior)."""
        engine = IndicatorEngine(symbol="TEST")

        # First bar with volume
        values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert values.vwap == pytest.approx(100.0)

        # Zero-volume bar — still includes TP * 0 = 0 contribution
        values = engine.update(101.0, 103.0, 99.0, 101.0, 0)
        # VWAP unchanged since no volume added
        assert values.vwap == pytest.approx(100.0)

    def test_vwap_resets_on_daily_reset(self) -> None:
        """VWAP resets to None after reset_daily()."""
        engine = IndicatorEngine(symbol="TEST")

        engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert engine.vwap is not None

        engine.reset_daily()
        assert engine.vwap is None

        # New bar after reset
        values = engine.update(105.0, 107.0, 103.0, 106.0, 500)
        # TP = (107 + 103 + 106) / 3 = 105.333...
        expected_tp = (107 + 103 + 106) / 3
        assert values.vwap == pytest.approx(expected_tp)


class TestATR:
    """Tests for ATR(14) computation with Wilder's smoothing."""

    def test_atr_returns_none_until_14_bars(self) -> None:
        """ATR returns None until 14 true range values are calculated."""
        engine = IndicatorEngine(symbol="TEST")

        # First bar — no previous close, no TR
        values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert values.atr_14 is None

        # Bars 2-14 (13 more bars = 13 TRs, still not enough)
        for _ in range(13):
            values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert values.atr_14 is None

        # Bar 15 — now we have 14 TRs
        values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert values.atr_14 is not None

    def test_atr_wilder_smoothing_correctness(self) -> None:
        """ATR uses Wilder's smoothing after initial SMA."""
        engine = IndicatorEngine(symbol="TEST")

        # Feed 15 bars with constant TR=4 (H-L)
        # Bar 1: no TR (no prev_close)
        engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        # Bars 2-15: TR = 4 each
        for _ in range(14):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        # Initial ATR = average of 14 TRs of 4 each = 4.0
        assert engine.atr_14 == pytest.approx(4.0)

        # Bar 16: TR = 8 (H=106, L=98)
        values = engine.update(100.0, 106.0, 98.0, 102.0, 1000)
        # Wilder's: ATR = (4.0 * 13 + 8) / 14 = (52 + 8) / 14 = 60/14 ≈ 4.286
        assert values.atr_14 == pytest.approx(60 / 14)

    def test_atr_carries_across_daily_reset(self) -> None:
        """ATR state carries over after reset_daily()."""
        engine = IndicatorEngine(symbol="TEST")

        # Build up ATR
        engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        for _ in range(14):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        atr_before = engine.atr_14
        assert atr_before is not None

        engine.reset_daily()

        # ATR should still be present
        assert engine.atr_14 == atr_before

        # Next bar continues with Wilder's smoothing
        values = engine.update(100.0, 106.0, 98.0, 102.0, 1000)
        assert values.atr_14 is not None
        assert values.atr_14 != atr_before  # Changed due to new TR

    def test_prev_close_used_for_true_range(self) -> None:
        """True Range includes gaps from previous close."""
        engine = IndicatorEngine(symbol="TEST")

        # First bar: close = 100
        engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        # Second bar: gaps up, H=110, L=108, C=109
        # TR = max(110-108=2, |110-100|=10, |108-100|=8) = 10
        engine.update(108.0, 110.0, 108.0, 109.0, 1000)

        # Feed more bars to get ATR
        for _ in range(13):
            engine.update(109.0, 111.0, 107.0, 109.0, 1000)  # TR = 4 each

        # ATR = (10 + 4*13) / 14 = 62/14 ≈ 4.43
        assert engine.atr_14 == pytest.approx(62 / 14)


class TestSMA:
    """Tests for Simple Moving Averages."""

    def test_sma_9_basic(self) -> None:
        """SMA(9) is simple average of last 9 closes."""
        engine = IndicatorEngine(symbol="TEST")

        # Feed 9 bars with closes 1-9
        for i in range(1, 10):
            values = engine.update(float(i), float(i + 1), float(i - 1), float(i), 1000)

        # SMA(9) = (1+2+3+4+5+6+7+8+9) / 9 = 45/9 = 5
        assert values.sma_9 == pytest.approx(5.0)

    def test_sma_20_basic(self) -> None:
        """SMA(20) is simple average of last 20 closes."""
        engine = IndicatorEngine(symbol="TEST")

        # Feed 20 bars with closes 1-20
        for i in range(1, 21):
            values = engine.update(float(i), float(i + 1), float(i - 1), float(i), 1000)

        # SMA(20) = (1+2+...+20) / 20 = 210/20 = 10.5
        assert values.sma_20 == pytest.approx(10.5)

    def test_sma_50_returns_none_until_50_bars(self) -> None:
        """SMA(50) returns None until 50 bars processed."""
        engine = IndicatorEngine(symbol="TEST")

        for _ in range(49):
            values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert values.sma_50 is None

        values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert values.sma_50 is not None

    def test_sma_carries_across_daily_reset(self) -> None:
        """SMA state carries over after reset_daily()."""
        engine = IndicatorEngine(symbol="TEST")

        # Build up SMA
        for _ in range(10):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        sma_before = engine.sma_9
        assert sma_before is not None

        engine.reset_daily()

        # SMA should still be present
        assert engine.sma_9 == sma_before


class TestRVOL:
    """Tests for Relative Volume computation."""

    def test_rvol_returns_none_without_baseline(self) -> None:
        """RVOL returns None until 20 bars establish baseline."""
        engine = IndicatorEngine(symbol="TEST")

        for _ in range(19):
            values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert values.rvol is None

    def test_rvol_builds_baseline_after_20_bars(self) -> None:
        """RVOL becomes available after 20 bars establish baseline."""
        engine = IndicatorEngine(symbol="TEST")

        # 20 bars with volume 1000 each
        for _ in range(20):
            values = engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        # Baseline = 1000, cumulative = 20000, expected = 1000 * 20 = 20000
        # RVOL = 20000 / 20000 = 1.0
        assert values.rvol == pytest.approx(1.0)

    def test_rvol_reflects_volume_changes(self) -> None:
        """RVOL increases when volume exceeds baseline."""
        engine = IndicatorEngine(symbol="TEST")

        # First 20 bars: 1000 volume each (baseline = 1000)
        for _ in range(20):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        # Bar 21: 2000 volume (double)
        values = engine.update(100.0, 102.0, 98.0, 100.0, 2000)

        # cumulative = 20000 + 2000 = 22000
        # expected = 1000 * 21 = 21000
        # RVOL = 22000 / 21000 ≈ 1.048
        assert values.rvol == pytest.approx(22000 / 21000)

    def test_rvol_resets_cumulative_on_daily_reset(self) -> None:
        """RVOL baseline and samples reset on daily reset."""
        engine = IndicatorEngine(symbol="TEST")

        # Build up RVOL
        for _ in range(25):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert engine.rvol is not None

        engine.reset_daily()

        assert engine.rvol is None

        # Need 20 more bars to rebuild baseline
        for _ in range(19):
            values = engine.update(100.0, 102.0, 98.0, 100.0, 2000)
        assert values.rvol is None

        values = engine.update(100.0, 102.0, 98.0, 100.0, 2000)
        # New baseline = 2000, RVOL = 1.0
        assert values.rvol == pytest.approx(1.0)


class TestDailyReset:
    """Tests for automatic and manual daily reset."""

    def test_auto_daily_reset_on_date_change(self) -> None:
        """Engine auto-resets when timestamp_date changes."""
        engine = IndicatorEngine(symbol="TEST")

        # Day 1 bars
        engine.update(100.0, 102.0, 98.0, 100.0, 1000, timestamp_date="2025-01-01")
        engine.update(100.0, 102.0, 98.0, 100.0, 1000, timestamp_date="2025-01-01")

        vwap_day1 = engine.vwap
        assert vwap_day1 is not None

        # Day 2 — should trigger reset
        values = engine.update(105.0, 107.0, 103.0, 106.0, 500, timestamp_date="2025-01-02")

        # VWAP should be recalculated from just this bar
        expected_tp = (107 + 103 + 106) / 3
        assert values.vwap == pytest.approx(expected_tp)

    def test_auto_daily_reset_with_date_object(self) -> None:
        """Engine accepts date objects for timestamp_date."""
        engine = IndicatorEngine(symbol="TEST")

        engine.update(100.0, 102.0, 98.0, 100.0, 1000, timestamp_date=date(2025, 1, 1))
        engine.update(100.0, 102.0, 98.0, 100.0, 1000, timestamp_date=date(2025, 1, 2))

        # Should have reset between days
        assert engine.bar_count == 2

    def test_manual_reset_daily(self) -> None:
        """reset_daily() clears VWAP and RVOL state."""
        engine = IndicatorEngine(symbol="TEST")

        for _ in range(25):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert engine.vwap is not None
        assert engine.rvol is not None

        engine.reset_daily()

        assert engine.vwap is None
        assert engine.rvol is None
        # ATR and SMA should persist
        assert engine.atr_14 is not None  # Had 25 bars > 14


class TestGetCurrentValues:
    """Tests for get_current_values() method."""

    def test_get_current_values_returns_indicator_values(self) -> None:
        """get_current_values() returns IndicatorValues with cached state."""
        engine = IndicatorEngine(symbol="TEST")

        for _ in range(50):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        values = engine.get_current_values()

        assert isinstance(values, IndicatorValues)
        assert values.vwap is not None
        assert values.atr_14 is not None
        assert values.sma_9 is not None
        assert values.sma_20 is not None
        assert values.sma_50 is not None
        assert values.rvol is not None

    def test_get_current_values_after_warmup(self) -> None:
        """get_current_values() is useful after feeding historical bars."""
        engine = IndicatorEngine(symbol="TEST")

        # Simulate warm-up
        for _ in range(60):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        values = engine.get_current_values()

        # All indicators should be populated
        assert all(v is not None for v in values.as_dict().values())


class TestWarmUp:
    """Tests for warm_up() convenience method."""

    def test_warm_up_with_bar_dicts(self) -> None:
        """warm_up() processes a list of bar dictionaries."""
        engine = IndicatorEngine(symbol="TEST")

        bars = [
            {
                "timestamp": "2025-01-01 09:30:00",
                "open": 100.0,
                "high": 102.0,
                "low": 98.0,
                "close": 100.0,
                "volume": 1000,
            },
            {
                "timestamp": "2025-01-01 09:31:00",
                "open": 100.0,
                "high": 103.0,
                "low": 99.0,
                "close": 101.0,
                "volume": 1500,
            },
        ]

        engine.warm_up(bars)

        assert engine.bar_count == 2
        assert engine.vwap is not None


class TestBarCount:
    """Tests for bar_count property."""

    def test_bar_count_increments(self) -> None:
        """bar_count increases with each update()."""
        engine = IndicatorEngine(symbol="TEST")

        assert engine.bar_count == 0

        engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert engine.bar_count == 1

        engine.update(100.0, 102.0, 98.0, 100.0, 1000)
        assert engine.bar_count == 2

    def test_bar_count_not_reset_by_daily_reset(self) -> None:
        """bar_count is cumulative and not reset by reset_daily()."""
        engine = IndicatorEngine(symbol="TEST")

        for _ in range(10):
            engine.update(100.0, 102.0, 98.0, 100.0, 1000)

        assert engine.bar_count == 10

        engine.reset_daily()

        assert engine.bar_count == 10


class TestSymbolProperty:
    """Tests for symbol property."""

    def test_symbol_stored_correctly(self) -> None:
        """Engine stores the symbol it was initialized with."""
        engine = IndicatorEngine(symbol="AAPL")
        assert engine.symbol == "AAPL"
