"""Tests for VectorBT VWAP Reclaim parameter sweep."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from argus.backtest.vectorbt_vwap_reclaim import (
    VwapReclaimSweepConfig,
    compute_day_vwap,
    compute_qualifying_days,
    simulate_trade_exit,
    simulate_vwap_reclaim_day,
)


class TestComputeDayVwap:
    """Tests for VWAP computation."""

    def test_vwap_basic_calculation(self) -> None:
        """VWAP should be cumulative(TP × vol) / cumulative(vol)."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 101.0, 102.0],
                "low": [98.0, 99.0, 100.0],
                "close": [99.0, 100.0, 101.0],
                "volume": [1000, 1000, 1000],
            }
        )

        vwap = compute_day_vwap(day_df)

        # TP for each bar: (H+L+C)/3
        # Bar 0: (100+98+99)/3 = 99.0
        # Bar 1: (101+99+100)/3 = 100.0
        # Bar 2: (102+100+101)/3 = 101.0
        #
        # VWAP at bar 0: 99.0 * 1000 / 1000 = 99.0
        # VWAP at bar 1: (99.0*1000 + 100.0*1000) / 2000 = 99.5
        # VWAP at bar 2: (99.0*1000 + 100.0*1000 + 101.0*1000) / 3000 = 100.0

        assert len(vwap) == 3
        assert vwap.iloc[0] == pytest.approx(99.0)
        assert vwap.iloc[1] == pytest.approx(99.5)
        assert vwap.iloc[2] == pytest.approx(100.0)

    def test_vwap_volume_weighting(self) -> None:
        """Higher volume bars should have more weight on VWAP."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 102.0],
                "low": [98.0, 100.0],
                "close": [99.0, 101.0],
                "volume": [100, 900],  # Second bar has 9x volume
            }
        )

        vwap = compute_day_vwap(day_df)

        # TP bar 0: 99.0, TP bar 1: 101.0
        # VWAP at bar 1: (99.0*100 + 101.0*900) / 1000
        #             = (9900 + 90900) / 1000 = 100.8

        assert vwap.iloc[1] == pytest.approx(100.8)

    def test_vwap_handles_zero_volume(self) -> None:
        """VWAP should return NaN when cumulative volume is zero."""
        day_df = pd.DataFrame(
            {
                "high": [100.0],
                "low": [98.0],
                "close": [99.0],
                "volume": [0],
            }
        )

        vwap = compute_day_vwap(day_df)

        assert pd.isna(vwap.iloc[0])


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

    def test_gap_filter_respects_price_bounds(self) -> None:
        """Days outside price bounds should be excluded."""
        df = pd.DataFrame(
            {
                "trading_day": [date(2025, 1, 2), date(2025, 1, 3)],
                "open": [100.0, 103.0],  # 3% gap
                "close": [100.0, 103.0],
            }
        )

        # Price bounds that exclude the stock
        qualifying = compute_qualifying_days(
            df, min_gap_pct=2.0, min_price=200.0, max_price=300.0
        )

        assert len(qualifying) == 0


class TestSimulateTradeExit:
    """Tests for trade exit simulation."""

    def test_stop_loss_exit(self) -> None:
        """Trade should exit at stop when price hits stop level."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 100.5, 100.2],
                "low": [99.5, 99.0, 98.5],  # Hits stop at bar 1
                "close": [100.0, 99.5, 99.0],
                "minutes_from_midnight": [600, 601, 602],
            }
        )

        result = simulate_trade_exit(
            day_df,
            entry_bar_idx=0,
            entry_price=100.0,
            stop_price=99.0,  # Stop at 99.0
            target_price=102.0,
            time_stop_bars=10,
        )

        assert result is not None
        assert result["exit_reason"] == "stop"
        assert result["exit_price"] == 99.0
        assert result["r_multiple"] == pytest.approx(-1.0)

    def test_target_exit(self) -> None:
        """Trade should exit at target when price reaches target."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 101.0, 102.5],  # Hits target at bar 2
                "low": [99.5, 100.0, 101.0],
                "close": [100.0, 101.0, 102.0],
                "minutes_from_midnight": [600, 601, 602],
            }
        )

        result = simulate_trade_exit(
            day_df,
            entry_bar_idx=0,
            entry_price=100.0,
            stop_price=99.0,
            target_price=102.0,
            time_stop_bars=10,
        )

        assert result is not None
        assert result["exit_reason"] == "target"
        assert result["exit_price"] == 102.0
        assert result["r_multiple"] == pytest.approx(2.0)

    def test_time_stop_exit(self) -> None:
        """Trade should exit at close when time stop reached."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 100.5, 100.5, 100.6],
                "low": [99.5, 99.8, 99.7, 99.6],
                "close": [100.0, 100.2, 100.3, 100.4],
                "minutes_from_midnight": [600, 601, 602, 603],
            }
        )

        result = simulate_trade_exit(
            day_df,
            entry_bar_idx=0,
            entry_price=100.0,
            stop_price=99.0,
            target_price=103.0,  # Far target
            time_stop_bars=2,  # Time stop at bar 2
        )

        assert result is not None
        assert result["exit_reason"] == "time_stop"
        assert result["exit_price"] == 100.3  # Close at bar 2
        assert result["hold_bars"] == 2

    def test_eod_flatten(self) -> None:
        """Trade should flatten at EOD when bar is at 3:45 PM."""
        day_df = pd.DataFrame(
            {
                "high": [100.0, 100.5, 100.5],
                "low": [99.5, 99.8, 99.7],
                "close": [100.0, 100.2, 100.3],
                "minutes_from_midnight": [600, 601, 945],  # 945 = 3:45 PM
            }
        )

        result = simulate_trade_exit(
            day_df,
            entry_bar_idx=0,
            entry_price=100.0,
            stop_price=99.0,
            target_price=103.0,
            time_stop_bars=100,
        )

        assert result is not None
        assert result["exit_reason"] == "eod"
        assert result["exit_price"] == 100.3


class TestSimulateVwapReclaimDay:
    """Tests for the VWAP Reclaim state machine simulation."""

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
            DataFrame suitable for VWAP Reclaim simulation.
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

    def test_basic_reclaim_entry(self) -> None:
        """State machine should generate entry on valid VWAP reclaim."""
        # Setup: price above VWAP, pulls below, then reclaims
        # VWAP computation: we need to construct prices that give us
        # a clear above → below → reclaim pattern

        prices = [
            # (open, high, low, close)
            (100.0, 101.0, 99.0, 100.0),  # Bar 0: watching
            (100.5, 102.0, 100.0, 101.5),  # Bar 1: above VWAP
            (101.0, 101.5, 99.0, 99.5),  # Bar 2: below VWAP
            (99.0, 99.5, 98.5, 98.8),  # Bar 3: still below
            (98.5, 99.0, 98.0, 98.5),  # Bar 4: still below (3 bars now)
            (99.0, 101.5, 98.5, 101.0),  # Bar 5: reclaim with volume
            (101.0, 101.5, 100.5, 101.2),  # Bar 6: post-entry
            (101.2, 102.5, 101.0, 102.0),  # Bar 7: hits target
        ]
        volumes = [1000] * 8
        volumes[5] = 2000  # High volume on reclaim bar
        minutes = [600, 601, 602, 603, 604, 605, 606, 607]  # All in 10-12 window

        day_df = self._create_day_df(prices, volumes, minutes)
        vwap = compute_day_vwap(day_df)

        trades = simulate_vwap_reclaim_day(
            day_df,
            vwap,
            min_pullback_pct=0.001,  # Very small min
            max_pullback_pct=0.03,  # Large max
            min_pullback_bars=3,
            volume_multiplier=1.0,  # Relaxed volume requirement
            max_chase_above_vwap_pct=0.02,
            stop_buffer_pct=0.001,
            target_r=1.0,
            time_stop_bars=30,
        )

        # Should have one trade
        assert len(trades) == 1
        trade = trades[0]
        # Should exit at target or stop based on subsequent price action
        assert trade["exit_reason"] in ("target", "stop", "time_stop", "eod")

    def test_no_entry_outside_time_window(self) -> None:
        """No entry should occur outside 10 AM - 12 PM window."""
        prices = [
            (100.0, 101.0, 99.0, 101.0),  # Above VWAP
            (100.5, 101.0, 98.5, 99.0),  # Below VWAP
            (99.0, 99.5, 98.0, 98.5),  # Still below
            (98.5, 99.0, 98.0, 98.5),  # Still below
            (98.5, 101.0, 98.0, 100.5),  # Reclaim
        ]
        volumes = [1000, 1000, 1000, 1000, 2000]
        # All bars before 10 AM (minutes < 600)
        minutes = [570, 571, 572, 573, 574]  # 9:30-9:34 AM

        day_df = self._create_day_df(prices, volumes, minutes)
        vwap = compute_day_vwap(day_df)

        trades = simulate_vwap_reclaim_day(
            day_df,
            vwap,
            min_pullback_pct=0.001,
            max_pullback_pct=0.05,
            min_pullback_bars=2,
            volume_multiplier=1.0,
            max_chase_above_vwap_pct=0.02,
            stop_buffer_pct=0.001,
            target_r=1.0,
            time_stop_bars=30,
        )

        assert len(trades) == 0

    def test_exhausted_state_on_deep_pullback(self) -> None:
        """State machine should transition to EXHAUSTED on deep pullback."""
        prices = [
            (100.0, 101.0, 99.0, 101.0),  # Above VWAP
            (100.5, 101.0, 95.0, 96.0),  # Deep pullback below VWAP (5%+)
            (96.0, 102.0, 95.5, 101.0),  # Attempted reclaim
        ]
        volumes = [1000, 1000, 2000]
        minutes = [600, 601, 602]

        day_df = self._create_day_df(prices, volumes, minutes)
        vwap = compute_day_vwap(day_df)

        trades = simulate_vwap_reclaim_day(
            day_df,
            vwap,
            min_pullback_pct=0.001,
            max_pullback_pct=0.02,  # 2% max - the pullback exceeds this
            min_pullback_bars=1,
            volume_multiplier=1.0,
            max_chase_above_vwap_pct=0.02,
            stop_buffer_pct=0.001,
            target_r=1.0,
            time_stop_bars=30,
        )

        # Should transition to EXHAUSTED, no trade
        assert len(trades) == 0

    def test_insufficient_pullback_bars_resets_state(self) -> None:
        """Reclaim with too few bars below VWAP should reset to ABOVE_VWAP."""
        prices = [
            (100.0, 101.0, 99.0, 101.0),  # Above VWAP
            (100.5, 101.0, 98.5, 99.0),  # Below VWAP (1 bar)
            (99.0, 101.5, 98.5, 101.0),  # Reclaim but only 1 bar below
            (101.0, 102.0, 100.5, 101.5),  # Continues above
        ]
        volumes = [1000, 1000, 2000, 1000]
        minutes = [600, 601, 602, 603]

        day_df = self._create_day_df(prices, volumes, minutes)
        vwap = compute_day_vwap(day_df)

        trades = simulate_vwap_reclaim_day(
            day_df,
            vwap,
            min_pullback_pct=0.001,
            max_pullback_pct=0.05,
            min_pullback_bars=5,  # Require 5 bars below
            volume_multiplier=1.0,
            max_chase_above_vwap_pct=0.02,
            stop_buffer_pct=0.001,
            target_r=1.0,
            time_stop_bars=30,
        )

        # Should not enter due to insufficient bars
        assert len(trades) == 0


class TestVwapReclaimSweepConfig:
    """Tests for sweep configuration."""

    def test_default_config_has_768_combinations(self) -> None:
        """Default config should produce 768 parameter combinations."""
        config = VwapReclaimSweepConfig(
            data_dir=Path("/tmp"),
            symbols=[],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=Path("/tmp"),
        )

        total = (
            len(config.min_pullback_pct_list)
            * len(config.min_pullback_bars_list)
            * len(config.volume_multiplier_list)
            * len(config.target_r_list)
            * len(config.time_stop_bars_list)
        )

        # 4 × 4 × 4 × 3 × 4 = 768
        assert total == 768

    def test_custom_parameter_lists(self) -> None:
        """Config should accept custom parameter lists."""
        config = VwapReclaimSweepConfig(
            data_dir=Path("/tmp"),
            symbols=[],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 1, 31),
            output_dir=Path("/tmp"),
            min_pullback_pct_list=[0.002, 0.003],
            target_r_list=[0.5, 1.0, 1.5, 2.0],
        )

        assert config.min_pullback_pct_list == [0.002, 0.003]
        assert config.target_r_list == [0.5, 1.0, 1.5, 2.0]
