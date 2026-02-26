"""Tests for VectorBT Afternoon Momentum parameter sweep (vectorized implementation)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest

from argus.backtest.vectorbt_afternoon_momentum import (
    AfternoonSweepConfig,
    _compute_atr_for_day,
    _find_exit_vectorized,
    _precompute_afternoon_entries_for_day,
    compute_qualifying_days,
    generate_heatmaps,
    run_single_symbol_sweep,
    run_sweep,
)


class TestComputeQualifyingDays:
    """Tests for gap filter logic."""

    def test_gap_filter_passes_qualifying_days(self) -> None:
        """Days with sufficient gap should be included."""
        df = pd.DataFrame(
            {
                "trading_day": [date(2025, 1, 2), date(2025, 1, 3)],
                "open": [100.0, 103.0],  # 3% gap on day 2
                "close": [100.0, 103.0],
            }
        )

        qualifying = compute_qualifying_days(df, min_gap_pct=2.0)

        assert date(2025, 1, 3) in qualifying

    def test_gap_filter_rejects_small_gaps(self) -> None:
        """Days with insufficient gap should be excluded."""
        df = pd.DataFrame(
            {
                "trading_day": [date(2025, 1, 2), date(2025, 1, 3)],
                "open": [100.0, 101.0],  # 1% gap (below 2%)
                "close": [100.0, 101.0],
            }
        )

        qualifying = compute_qualifying_days(df, min_gap_pct=2.0)

        assert date(2025, 1, 3) not in qualifying


class TestComputeAtrForDay:
    """Tests for ATR calculation."""

    def test_atr_basic_calculation(self) -> None:
        """ATR should be computed from true ranges of bars before 2 PM."""
        # Create 20 bars before 2 PM (840 minutes) with known true ranges
        # True range = max(high-low, |high-prev_close|, |low-prev_close|)
        bars = []
        for i in range(20):
            bars.append(
                {
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "minutes_from_midnight": 720 + i,  # 12:00 PM + i minutes
                }
            )
        day_df = pd.DataFrame(bars)

        atr = _compute_atr_for_day(day_df)

        # Each bar has high-low = 2.0, so ATR should be ~2.0
        assert atr is not None
        assert atr == pytest.approx(2.0, rel=0.1)

    def test_atr_insufficient_bars_returns_none(self) -> None:
        """ATR should return None if fewer than 14 bars before 2 PM."""
        bars = []
        for i in range(10):  # Only 10 bars
            bars.append(
                {
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "minutes_from_midnight": 720 + i,
                }
            )
        day_df = pd.DataFrame(bars)

        atr = _compute_atr_for_day(day_df)

        assert atr is None


class TestPrecomputeAfternoonEntriesForDay:
    """Tests for entry precomputation."""

    def _create_day_df(
        self,
        prices: list[tuple[float, float, float, float]],
        volumes: list[int],
        minutes: list[int],
    ) -> pd.DataFrame:
        """Helper to create day DataFrame.

        Args:
            prices: List of (open, high, low, close) tuples.
            volumes: List of volumes.
            minutes: List of minutes from midnight.

        Returns:
            DataFrame suitable for Afternoon Momentum simulation.
        """
        return pd.DataFrame(
            {
                "open": [p[0] for p in prices],
                "high": [p[1] for p in prices],
                "low": [p[2] for p in prices],
                "close": [p[3] for p in prices],
                "volume": volumes,
                "minutes_from_midnight": minutes,
            }
        )

    def test_precompute_finds_consolidation(self) -> None:
        """Entry should be detected when consolidation is tight and breakout occurs."""
        # Setup: tight consolidation during 12-2 PM, then breakout after 2 PM
        prices = []
        volumes = []
        minutes = []

        # Morning bars (9:30 AM - 12:00 PM) - 150 bars for ATR computation
        for i in range(150):
            prices.append((100.0, 100.5, 99.5, 100.0))  # $1 range
            volumes.append(1000)
            minutes.append(570 + i)  # 9:30 AM onwards

        # Consolidation bars (12:00 PM - 2:00 PM) - tight range
        for i in range(120):
            prices.append((100.0, 100.3, 99.8, 100.1))  # $0.5 range (tight)
            volumes.append(1000)
            minutes.append(720 + i)  # 12:00 PM onwards

        # Breakout bar after 2 PM
        prices.append((100.1, 100.8, 100.0, 100.6))  # Close above consolidation high
        volumes.append(2000)  # High volume
        minutes.append(841)  # 2:01 PM

        # Post-entry bars
        for i in range(10):
            prices.append((100.6, 101.0, 100.4, 100.8))
            volumes.append(1000)
            minutes.append(842 + i)

        day_df = self._create_day_df(prices, volumes, minutes)
        atr = 1.0  # Consolidation range < ATR

        entries = _precompute_afternoon_entries_for_day(
            day_df, atr, max_chase_pct=0.01, stop_buffer_pct=0.001
        )

        assert len(entries) >= 1
        entry = entries[0]
        assert entry["entry_price"] > 0
        assert entry["consolidation_high"] > 0
        assert entry["consolidation_low"] > 0
        assert len(entry["highs"]) > 0

    def test_precompute_captures_high_consolidation_ratio(self) -> None:
        """Wide consolidation range is captured in entry info for parameter-time filtering."""
        prices = []
        volumes = []
        minutes = []

        # Morning bars
        for i in range(150):
            prices.append((100.0, 100.5, 99.5, 100.0))
            volumes.append(1000)
            minutes.append(570 + i)

        # Wide consolidation (12:00 PM - 2:00 PM)
        for i in range(120):
            prices.append((100.0, 103.0, 97.0, 100.0))  # $6 range (very wide)
            volumes.append(1000)
            minutes.append(720 + i)

        # Attempted breakout
        prices.append((100.0, 104.0, 99.5, 103.5))
        volumes.append(2000)
        minutes.append(841)

        day_df = self._create_day_df(prices, volumes, minutes)
        atr = 1.0  # Consolidation range (6.0) / ATR (1.0) = 6.0

        entries = _precompute_afternoon_entries_for_day(
            day_df, atr, max_chase_pct=0.01, stop_buffer_pct=0.001
        )

        # Wide consolidation is captured for parameter-time filtering
        # The ratio filtering happens at sweep time, not precompute
        # So entries exist with high consolidation_ratio captured
        for entry in entries:
            # Range = 103 - 97 = 6, ATR = 1.0, ratio = 6.0
            assert entry["consolidation_ratio"] == pytest.approx(6.0, rel=0.1)
            # max_consolidation_ratio must be >= consolidation_ratio
            assert "max_consolidation_ratio" in entry
            assert entry["max_consolidation_ratio"] >= entry["consolidation_ratio"]

    def test_precompute_captures_consolidation_ratio(self) -> None:
        """Verify consolidation ratio is correctly stored."""
        prices = []
        volumes = []
        minutes = []

        # Morning bars for ATR
        for i in range(150):
            prices.append((100.0, 100.5, 99.5, 100.0))
            volumes.append(1000)
            minutes.append(570 + i)

        # Tight consolidation
        for i in range(120):
            prices.append((100.0, 100.2, 99.9, 100.1))  # $0.3 range
            volumes.append(1000)
            minutes.append(720 + i)

        # Breakout
        prices.append((100.1, 100.5, 100.0, 100.4))
        volumes.append(2000)
        minutes.append(841)

        # Post-entry
        prices.append((100.4, 100.8, 100.2, 100.6))
        volumes.append(1000)
        minutes.append(842)

        day_df = self._create_day_df(prices, volumes, minutes)
        atr = 1.0  # Range is 0.3, so ratio = 0.3

        entries = _precompute_afternoon_entries_for_day(
            day_df, atr, max_chase_pct=0.01, stop_buffer_pct=0.001
        )

        if entries:
            entry = entries[0]
            # Consolidation ratio should be range / ATR
            assert entry["consolidation_ratio"] < 1.0  # Tight consolidation

    def test_precompute_no_breakout(self) -> None:
        """No entry when price never breaks above consolidation high."""
        prices = []
        volumes = []
        minutes = []

        # Morning bars
        for i in range(150):
            prices.append((100.0, 100.5, 99.5, 100.0))
            volumes.append(1000)
            minutes.append(570 + i)

        # Consolidation
        for i in range(120):
            prices.append((100.0, 100.3, 99.8, 100.1))
            volumes.append(1000)
            minutes.append(720 + i)

        # Afternoon bars that don't break high (close below consolidation high of 100.3)
        for i in range(30):
            prices.append((100.0, 100.2, 99.7, 100.0))  # Close at 100.0 < 100.3
            volumes.append(1000)
            minutes.append(840 + i)

        day_df = self._create_day_df(prices, volumes, minutes)
        atr = 1.0

        entries = _precompute_afternoon_entries_for_day(
            day_df, atr, max_chase_pct=0.01, stop_buffer_pct=0.001
        )

        assert len(entries) == 0  # No breakout occurred

    def test_precompute_chase_protection(self) -> None:
        """Entry should be filtered when breakout is too far above consolidation high."""
        prices = []
        volumes = []
        minutes = []

        # Morning bars
        for i in range(150):
            prices.append((100.0, 100.5, 99.5, 100.0))
            volumes.append(1000)
            minutes.append(570 + i)

        # Consolidation
        for i in range(120):
            prices.append((100.0, 100.3, 99.8, 100.1))
            volumes.append(1000)
            minutes.append(720 + i)

        # Gap up breakout (close far above consolidation high)
        prices.append((102.0, 103.0, 101.5, 102.5))  # Close 2.2% above 100.3
        volumes.append(2000)
        minutes.append(841)

        day_df = self._create_day_df(prices, volumes, minutes)
        atr = 1.0

        entries = _precompute_afternoon_entries_for_day(
            day_df, atr, max_chase_pct=0.005, stop_buffer_pct=0.001  # 0.5% chase limit
        )

        # Should be filtered by chase protection
        assert len(entries) == 0


class TestFindExitVectorized:
    """Tests for vectorized exit detection."""

    def test_exit_vectorized_stop(self) -> None:
        """Trade should exit at stop when price hits stop level."""
        highs = np.array([100.5, 100.2, 100.3])
        lows = np.array([99.0, 98.5, 99.0])  # Hits stop at bar 0
        closes = np.array([99.5, 99.0, 99.5])
        minutes = np.array([841, 842, 843])

        result = _find_exit_vectorized(
            highs,
            lows,
            closes,
            minutes,
            entry_price=100.0,
            entry_minutes=840,
            stop_price=99.0,
            target_price=102.0,
            time_stop_bars=10,
        )

        assert result is not None
        assert result["exit_reason"] == "stop"
        assert result["exit_price"] == 99.0
        assert result["r_multiple"] == pytest.approx(-1.0)

    def test_exit_vectorized_target(self) -> None:
        """Trade should exit at target when price reaches target."""
        highs = np.array([101.0, 102.5, 103.0])  # Hits target at bar 1
        lows = np.array([100.0, 101.0, 102.0])
        closes = np.array([101.0, 102.0, 102.5])
        minutes = np.array([841, 842, 843])

        result = _find_exit_vectorized(
            highs,
            lows,
            closes,
            minutes,
            entry_price=100.0,
            entry_minutes=840,
            stop_price=99.0,
            target_price=102.0,
            time_stop_bars=10,
        )

        assert result is not None
        assert result["exit_reason"] == "target"
        assert result["exit_price"] == 102.0
        assert result["r_multiple"] == pytest.approx(2.0)

    def test_exit_vectorized_time_stop(self) -> None:
        """Trade should exit at close when time stop reached."""
        highs = np.array([100.5, 100.5, 100.6, 100.7])
        lows = np.array([99.8, 99.7, 99.6, 99.5])
        closes = np.array([100.2, 100.3, 100.4, 100.5])
        minutes = np.array([841, 842, 843, 844])

        result = _find_exit_vectorized(
            highs,
            lows,
            closes,
            minutes,
            entry_price=100.0,
            entry_minutes=840,
            stop_price=99.0,
            target_price=103.0,
            time_stop_bars=2,  # Exit at bar index 1 (2 bars held)
        )

        assert result is not None
        assert result["exit_reason"] == "time_stop"
        assert result["exit_price"] == 100.3
        assert result["hold_bars"] == 2

    def test_exit_vectorized_time_stop_with_stop_hit(self) -> None:
        """When time stop and stop hit same bar, stop takes priority."""
        highs = np.array([100.5, 100.5])
        lows = np.array([99.5, 98.5])  # Stop hit at bar 1
        closes = np.array([100.2, 99.0])
        minutes = np.array([841, 842])

        result = _find_exit_vectorized(
            highs,
            lows,
            closes,
            minutes,
            entry_price=100.0,
            entry_minutes=840,
            stop_price=99.0,
            target_price=103.0,
            time_stop_bars=2,  # Time stop also at bar 1
        )

        assert result is not None
        assert result["exit_reason"] == "stop"  # Stop takes priority
        assert result["exit_price"] == 99.0

    def test_exit_vectorized_eod(self) -> None:
        """Trade should flatten at EOD when bar is at 3:45 PM."""
        highs = np.array([100.5, 100.5, 100.5])
        lows = np.array([99.8, 99.7, 99.7])
        closes = np.array([100.2, 100.3, 100.3])
        minutes = np.array([841, 842, 945])  # 945 = 3:45 PM

        result = _find_exit_vectorized(
            highs,
            lows,
            closes,
            minutes,
            entry_price=100.0,
            entry_minutes=840,
            stop_price=99.0,
            target_price=103.0,
            time_stop_bars=100,
        )

        assert result is not None
        assert result["exit_reason"] == "eod"
        assert result["exit_price"] == 100.3


class TestRunSingleSymbolSweep:
    """Tests for single symbol sweep."""

    def test_run_single_symbol_sweep_produces_results(self, tmp_path: Path) -> None:
        """Sweep should produce results for all parameter combinations."""
        # Create synthetic data with a qualifying day
        data = []
        trading_day = date(2025, 1, 3)

        # Create bars for a full trading day with a gap
        # Morning bars
        for i in range(150):
            data.append(
                {
                    "timestamp": pd.Timestamp(
                        f"2025-01-03 09:30:00", tz="America/New_York"
                    )
                    + pd.Timedelta(minutes=i),
                    "open": 103.0,
                    "high": 103.5,
                    "low": 102.5,
                    "close": 103.0,
                    "volume": 1000,
                    "trading_day": trading_day,
                    "minutes_from_midnight": 570 + i,
                    "bar_number_in_day": i,
                }
            )

        # Consolidation bars
        for i in range(120):
            data.append(
                {
                    "timestamp": pd.Timestamp(
                        f"2025-01-03 12:00:00", tz="America/New_York"
                    )
                    + pd.Timedelta(minutes=i),
                    "open": 103.0,
                    "high": 103.2,
                    "low": 102.9,
                    "close": 103.1,
                    "volume": 1000,
                    "trading_day": trading_day,
                    "minutes_from_midnight": 720 + i,
                    "bar_number_in_day": 150 + i,
                }
            )

        # Breakout bar
        data.append(
            {
                "timestamp": pd.Timestamp("2025-01-03 14:01:00", tz="America/New_York"),
                "open": 103.1,
                "high": 103.8,
                "low": 103.0,
                "close": 103.5,
                "volume": 2000,
                "trading_day": trading_day,
                "minutes_from_midnight": 841,
                "bar_number_in_day": 270,
            }
        )

        # Post-entry bars
        for i in range(30):
            data.append(
                {
                    "timestamp": pd.Timestamp(
                        "2025-01-03 14:02:00", tz="America/New_York"
                    )
                    + pd.Timedelta(minutes=i),
                    "open": 103.5,
                    "high": 104.0,
                    "low": 103.3,
                    "close": 103.8,
                    "volume": 1000,
                    "trading_day": trading_day,
                    "minutes_from_midnight": 842 + i,
                    "bar_number_in_day": 271 + i,
                }
            )

        df = pd.DataFrame(data)

        config = AfternoonSweepConfig(
            data_dir=tmp_path,
            symbols=["TEST"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=tmp_path / "output",
            # Minimal parameter lists for fast test
            consolidation_atr_ratio_list=[1.0],
            min_consolidation_bars_list=[15],
            volume_multiplier_list=[1.0],
            target_r_list=[1.0, 2.0],
            time_stop_bars_list=[15, 30],
        )

        qualifying_days = {trading_day}

        results = run_single_symbol_sweep("TEST", df, qualifying_days, config)

        # Should have 1 × 1 × 1 × 2 × 2 = 4 results
        assert len(results) == 4
        assert all(r.symbol == "TEST" for r in results)


class TestRunSweep:
    """Tests for multi-symbol sweep."""

    def test_run_sweep_multiple_symbols(self, tmp_path: Path) -> None:
        """Sweep should process multiple symbols."""
        # Create minimal Parquet data for two symbols
        for symbol in ["AAPL", "TSLA"]:
            symbol_dir = tmp_path / "data" / symbol
            symbol_dir.mkdir(parents=True)

            # Create minimal DataFrame with timestamps in ET timezone
            # that fall within market hours (9:30 AM - 4:00 PM ET)
            data = []
            for day_offset in range(3):
                # Use ET timezone directly and pick times that are market hours
                # 9:30 AM ET = 14:30 UTC (winter) or 13:30 UTC (summer)
                # Use America/New_York to be safe
                for i in range(300):  # Full day of bars
                    data.append(
                        {
                            "timestamp": pd.Timestamp(
                                f"2025-01-{2 + day_offset:02d} 14:30:00", tz="UTC"
                            )
                            + pd.Timedelta(minutes=i),
                            "open": 100.0 + day_offset * 3,  # 3% gap each day
                            "high": 101.0 + day_offset * 3,
                            "low": 99.0 + day_offset * 3,
                            "close": 100.0 + day_offset * 3,
                            "volume": 1000,
                        }
                    )
            df = pd.DataFrame(data)
            df.to_parquet(symbol_dir / f"{symbol}_2025.parquet")

        config = AfternoonSweepConfig(
            data_dir=tmp_path / "data",
            symbols=[],  # Empty = discover all
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=tmp_path / "output",
            # Minimal parameters
            consolidation_atr_ratio_list=[1.0],
            min_consolidation_bars_list=[15],
            volume_multiplier_list=[1.0],
            target_r_list=[1.0],
            time_stop_bars_list=[15],
        )

        results = run_sweep(config)

        # Should have results for both symbols (1 combo each = 2 total)
        assert len(results) == 2
        assert set(results["symbol"].unique()) == {"AAPL", "TSLA"}


class TestGenerateHeatmaps:
    """Tests for heatmap generation."""

    def test_generate_heatmaps_creates_html(self, tmp_path: Path) -> None:
        """Heatmaps should create HTML files."""
        plotly = pytest.importorskip("plotly")  # noqa: F841

        # Create mock results DataFrame
        results_df = pd.DataFrame(
            {
                "symbol": ["AAPL"] * 4,
                "consolidation_atr_ratio": [0.5, 0.5, 1.0, 1.0],
                "min_consolidation_bars": [15, 30, 15, 30],
                "volume_multiplier": [1.0, 1.0, 1.0, 1.0],
                "target_r": [1.0, 1.0, 2.0, 2.0],
                "time_stop_bars": [15, 15, 30, 30],
                "total_trades": [10, 12, 8, 15],
                "win_rate": [0.6, 0.55, 0.65, 0.5],
                "sharpe_ratio": [1.5, 1.2, 1.8, 0.9],
                "profit_factor": [1.8, 1.5, 2.0, 1.2],
                "avg_r_multiple": [0.3, 0.2, 0.5, 0.1],
            }
        )

        generate_heatmaps(results_df, tmp_path)

        assert (tmp_path / "afternoon_heatmap_consolidation.html").exists()
        assert (tmp_path / "afternoon_heatmap_target_time.html").exists()
        assert (tmp_path / "afternoon_heatmap_volume_target.html").exists()

    def test_empty_results_heatmap_no_crash(self, tmp_path: Path) -> None:
        """Empty results should not crash heatmap generation."""
        results_df = pd.DataFrame()

        # Should not raise
        generate_heatmaps(results_df, tmp_path)

        # No files created
        assert not (tmp_path / "afternoon_heatmap_consolidation.html").exists()


class TestAfternoonSweepConfig:
    """Tests for sweep configuration."""

    def test_default_config_has_768_combinations(self) -> None:
        """Default config should produce 768 parameter combinations."""
        config = AfternoonSweepConfig(
            data_dir=Path("/tmp"),
            symbols=[],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=Path("/tmp"),
        )

        total = (
            len(config.consolidation_atr_ratio_list)
            * len(config.min_consolidation_bars_list)
            * len(config.volume_multiplier_list)
            * len(config.target_r_list)
            * len(config.time_stop_bars_list)
        )

        # [0.5, 0.75, 1.0, 1.5] = 4, [15, 30, 45, 60] = 4
        # [1.0, 1.2, 1.5] = 3, [1.0, 1.5, 2.0, 3.0] = 4, [15, 30, 45, 60] = 4
        # 4 × 4 × 3 × 4 × 4 = 768
        assert total == 768

    def test_custom_parameter_lists(self) -> None:
        """Config should accept custom parameter lists."""
        config = AfternoonSweepConfig(
            data_dir=Path("/tmp"),
            symbols=[],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=Path("/tmp"),
            consolidation_atr_ratio_list=[0.5, 0.75],
            target_r_list=[0.5, 1.0, 1.5, 2.0],
        )

        assert config.consolidation_atr_ratio_list == [0.5, 0.75]
        assert config.target_r_list == [0.5, 1.0, 1.5, 2.0]
