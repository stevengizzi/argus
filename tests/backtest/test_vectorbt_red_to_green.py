"""Tests for VectorBT Red-to-Green parameter sweep module."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from argus.backtest.vectorbt_red_to_green import (
    R2GEntryInfo,
    R2GSweepConfig,
    _compute_r2g_result,
    _compute_vwap_vectorized,
    _find_exit_vectorized,
    _precompute_r2g_entries_for_day,
    compute_gap_down_days,
    generate_report,
    run_single_symbol_sweep,
)


# ---------------------------------------------------------------------------
# Helpers: build synthetic OHLCV DataFrames
# ---------------------------------------------------------------------------


def _make_day_df(
    bars: list[dict[str, float]],
    base_minutes: int = 570,  # 9:30 AM ET
) -> pd.DataFrame:
    """Build a single-day DataFrame from a list of bar dicts.

    Each bar dict should have: open, high, low, close, volume.
    Timestamps are synthetic (minutes from midnight starting at base_minutes).
    """
    rows = []
    for i, bar in enumerate(bars):
        rows.append(
            {
                "timestamp": pd.Timestamp("2025-06-15 09:30", tz="US/Eastern")
                + pd.Timedelta(minutes=i),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar.get("volume", 100_000),
                "trading_day": date(2025, 6, 15),
                "minutes_from_midnight": base_minutes + i,
                "bar_number_in_day": i,
            }
        )
    return pd.DataFrame(rows)


def _make_gap_down_day(
    prev_close: float = 100.0,
    gap_pct: float = -0.03,
    n_bars: int = 100,
    reclaim_bar: int = 20,
) -> pd.DataFrame:
    """Create synthetic day with a gap down that reclaims prior close.

    Price opens gapped down, drifts near prior close, then reclaims it.
    Entry window bars are placed at 9:45 AM (585 minutes from midnight).

    Args:
        prev_close: Previous day close.
        gap_pct: Gap percentage (negative for gap down).
        n_bars: Total bars in the day.
        reclaim_bar: Bar index where price reclaims the level.

    Returns:
        DataFrame with synthetic OHLCV data.
    """
    day_open = prev_close * (1 + gap_pct)
    bars = []

    for i in range(n_bars):
        minutes = 570 + i  # Start at 9:30 AM ET

        if i < reclaim_bar:
            # Drift up toward prior close
            progress = i / reclaim_bar
            mid = day_open + (prev_close - day_open) * progress * 0.95
            bars.append(
                {
                    "open": mid - 0.05,
                    "high": mid + 0.10,
                    "low": mid - 0.15,
                    "close": mid,
                    "volume": 150_000,
                }
            )
        elif i == reclaim_bar:
            # Reclaim bar: close above prior close
            bars.append(
                {
                    "open": prev_close - 0.10,
                    "high": prev_close + 0.30,
                    "low": prev_close - 0.20,
                    "close": prev_close + 0.15,
                    "volume": 300_000,  # High volume on reclaim
                }
            )
        else:
            # Post-reclaim continuation
            base = prev_close + 0.15 + (i - reclaim_bar) * 0.02
            bars.append(
                {
                    "open": base - 0.05,
                    "high": base + 0.15,
                    "low": base - 0.10,
                    "close": base,
                    "volume": 120_000,
                }
            )

    rows = []
    for i, bar in enumerate(bars):
        minutes = 570 + i
        rows.append(
            {
                "timestamp": pd.Timestamp("2025-06-15 09:30", tz="US/Eastern")
                + pd.Timedelta(minutes=i),
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
                "trading_day": date(2025, 6, 15),
                "minutes_from_midnight": minutes,
                "bar_number_in_day": i,
            }
        )
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Test 1: Signal generation with gap down -> entries generated
# ---------------------------------------------------------------------------


class TestR2GSignalGenerationBasic:
    """Test that R2G signal generation produces entries for gap-down data."""

    def test_r2g_signal_generation_basic(self) -> None:
        """Synthetic OHLCV data with gap down should generate entry candidates."""
        prev_close = 100.0
        # Reclaim at bar 20 -> minutes_from_midnight = 570 + 20 = 590 (9:50 AM)
        # This is within 9:45-11:00 window
        day_df = _make_gap_down_day(
            prev_close=prev_close,
            gap_pct=-0.03,
            n_bars=100,
            reclaim_bar=20,
        )

        entries = _precompute_r2g_entries_for_day(
            day_df,
            prev_close=prev_close,
            max_gap_down_pct=0.10,
            stop_buffer_pct=0.001,
            max_chase_pct=0.003,
        )

        # Should find at least one entry (prior_close reclaim)
        assert len(entries) > 0, "Expected at least one R2G entry candidate"

        entry = entries[0]
        assert entry["gap_down_pct"] > 0, "Gap down pct should be positive (absolute)"
        assert entry["entry_price"] > 0, "Entry price should be positive"
        assert entry["level_price"] > 0, "Level price should be positive"
        assert len(entry["highs"]) > 0, "Should have post-entry price data"


# ---------------------------------------------------------------------------
# Test 2: No signals without gap
# ---------------------------------------------------------------------------


class TestR2GNoSignalsNoGap:
    """Test that no entries are generated for non-gap-down data."""

    def test_r2g_no_signals_no_gap(self) -> None:
        """Data without a gap down should produce no entries."""
        prev_close = 100.0
        # Gap UP instead of down
        day_df = _make_gap_down_day(
            prev_close=prev_close,
            gap_pct=0.02,  # Gap UP
            n_bars=50,
            reclaim_bar=15,
        )

        entries = _precompute_r2g_entries_for_day(
            day_df,
            prev_close=prev_close,
            max_gap_down_pct=0.10,
            stop_buffer_pct=0.001,
            max_chase_pct=0.003,
        )

        assert len(entries) == 0, "Gap up should produce no R2G entries"

    def test_r2g_no_signals_gap_too_large(self) -> None:
        """Gap beyond max_gap_down_pct should produce no entries."""
        prev_close = 100.0
        day_df = _make_gap_down_day(
            prev_close=prev_close,
            gap_pct=-0.15,  # 15% gap, exceeds 10% max
            n_bars=50,
            reclaim_bar=15,
        )

        entries = _precompute_r2g_entries_for_day(
            day_df,
            prev_close=prev_close,
            max_gap_down_pct=0.10,
            stop_buffer_pct=0.001,
            max_chase_pct=0.003,
        )

        assert len(entries) == 0, "Excessive gap should produce no entries"


# ---------------------------------------------------------------------------
# Test 3: Parameter grid construction
# ---------------------------------------------------------------------------


class TestParameterGridConstruction:
    """Test that parameter grid has expected combinations."""

    def test_parameter_grid_construction(self) -> None:
        """Grid should have correct number of parameter combinations."""
        config = R2GSweepConfig(
            data_dir=Path("/tmp/test"),
            symbols=["TEST"],
            start_date=date(2025, 1, 1),
            end_date=date(2025, 6, 30),
            output_dir=Path("/tmp/test_output"),
            min_gap_down_pct_list=[0.015, 0.02, 0.03, 0.04],
            level_proximity_pct_list=[0.002, 0.003, 0.005],
            volume_confirmation_multiplier_list=[1.0, 1.2, 1.5],
            time_stop_minutes_list=[15, 20, 30],
        )

        expected_combos = 4 * 3 * 3 * 3  # 108
        actual_combos = (
            len(config.min_gap_down_pct_list)
            * len(config.level_proximity_pct_list)
            * len(config.volume_confirmation_multiplier_list)
            * len(config.time_stop_minutes_list)
        )

        assert actual_combos == expected_combos, (
            f"Expected {expected_combos} combinations, got {actual_combos}"
        )


# ---------------------------------------------------------------------------
# Test 4: Walk-forward execution (sweep runs without error on synthetic data)
# ---------------------------------------------------------------------------


class TestWalkForwardExecution:
    """Test that sweep runs without error on synthetic data."""

    def test_walk_forward_execution(self, tmp_path: Path) -> None:
        """Run sweep on synthetic data - should complete without error."""
        # Build synthetic 2-day dataset
        symbol = "TSYN"
        symbol_dir = tmp_path / "data" / symbol
        symbol_dir.mkdir(parents=True)

        # Day 1: no gap (establishes prev_close)
        day1_bars = []
        for i in range(390):
            price = 100.0 + (i * 0.01)
            day1_bars.append(
                {
                    "timestamp": pd.Timestamp("2025-06-10 09:30", tz="US/Eastern")
                    + pd.Timedelta(minutes=i),
                    "open": price,
                    "high": price + 0.05,
                    "low": price - 0.05,
                    "close": price,
                    "volume": 100_000,
                }
            )

        # Day 2: gap down, reclaim at bar 20
        prev_close = day1_bars[-1]["close"]
        gap_open = prev_close * 0.97  # 3% gap down
        day2_bars = []
        for i in range(390):
            if i < 20:
                progress = i / 20
                mid = gap_open + (prev_close - gap_open) * progress * 0.95
            elif i == 20:
                mid = prev_close + 0.15
            else:
                mid = prev_close + 0.15 + (i - 20) * 0.01

            day2_bars.append(
                {
                    "timestamp": pd.Timestamp("2025-06-11 09:30", tz="US/Eastern")
                    + pd.Timedelta(minutes=i),
                    "open": mid - 0.02,
                    "high": mid + 0.10,
                    "low": mid - 0.10,
                    "close": mid,
                    "volume": 200_000 if i == 20 else 100_000,
                }
            )

        df = pd.DataFrame(day1_bars + day2_bars)
        df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

        # Run sweep
        output_dir = tmp_path / "output"
        config = R2GSweepConfig(
            data_dir=tmp_path / "data",
            symbols=[symbol],
            start_date=date(2025, 6, 10),
            end_date=date(2025, 6, 11),
            output_dir=output_dir,
            min_gap_down_pct_list=[0.02],
            level_proximity_pct_list=[0.005],
            volume_confirmation_multiplier_list=[1.0],
            time_stop_minutes_list=[20],
        )

        from argus.backtest.vectorbt_red_to_green import run_sweep

        results_df = run_sweep(config)

        # Should complete without error (may or may not find trades
        # depending on exact synthetic data alignment)
        assert isinstance(results_df, pd.DataFrame)
        assert output_dir.exists()


# ---------------------------------------------------------------------------
# Test 5: Report generation
# ---------------------------------------------------------------------------


class TestReportGeneration:
    """Test that report contains expected keys."""

    def test_report_generation(self) -> None:
        """Report should contain expected summary keys."""
        # Build a synthetic results DataFrame
        results_data = [
            {
                "symbol": "AAPL",
                "min_gap_down_pct": 0.02,
                "level_proximity_pct": 0.003,
                "volume_confirmation_multiplier": 1.2,
                "time_stop_minutes": 20,
                "total_trades": 15,
                "win_rate": 0.45,
                "total_return_pct": 2.5,
                "avg_r_multiple": 0.3,
                "max_drawdown_pct": 5.0,
                "sharpe_ratio": 1.2,
                "profit_factor": 1.4,
                "avg_hold_bars": 12.0,
                "qualifying_days": 50,
            },
            {
                "symbol": "TSLA",
                "min_gap_down_pct": 0.02,
                "level_proximity_pct": 0.003,
                "volume_confirmation_multiplier": 1.2,
                "time_stop_minutes": 20,
                "total_trades": 10,
                "win_rate": 0.50,
                "total_return_pct": 3.0,
                "avg_r_multiple": 0.4,
                "max_drawdown_pct": 4.0,
                "sharpe_ratio": 1.5,
                "profit_factor": 1.6,
                "avg_hold_bars": 10.0,
                "qualifying_days": 45,
            },
        ]
        results_df = pd.DataFrame(results_data)

        report = generate_report(results_df)

        assert "status" in report
        assert report["status"] == "validated"
        assert "total_trades" in report
        assert "sharpe_ratio" in report
        assert "win_rate" in report
        assert "profit_factor" in report
        assert "best_params" in report
        assert isinstance(report["best_params"], dict)
        assert "min_gap_down_pct" in report["best_params"]
        assert "level_proximity_pct" in report["best_params"]

    def test_report_generation_empty(self) -> None:
        """Empty results should produce no_data status."""
        report = generate_report(pd.DataFrame())
        assert report["status"] == "no_data"
        assert report["total_trades"] == 0


# ---------------------------------------------------------------------------
# Test 6: Vectorized exit detection
# ---------------------------------------------------------------------------


class TestVectorizedExit:
    """Test the vectorized exit function."""

    def test_stop_hit_first(self) -> None:
        """Stop hit on first bar should exit at stop price."""
        highs = np.array([101.0, 102.0, 103.0])
        lows = np.array([98.0, 99.0, 100.0])  # First bar low below stop
        closes = np.array([99.5, 101.0, 102.0])
        minutes = np.array([600, 601, 602])

        result = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=99.0,
            target_price=102.0,
            time_stop_bars=30,
        )

        assert result is not None
        assert result["exit_reason"] == "stop"
        assert result["exit_price"] == 99.0

    def test_target_hit(self) -> None:
        """Target hit should exit at target price."""
        highs = np.array([100.5, 101.0, 103.0])  # Target at bar 3
        lows = np.array([99.5, 100.0, 101.0])
        closes = np.array([100.2, 100.8, 102.0])
        minutes = np.array([600, 601, 602])

        result = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=99.0,
            target_price=102.5,
            time_stop_bars=30,
        )

        assert result is not None
        assert result["exit_reason"] == "target"
        assert result["exit_price"] == 102.5

    def test_time_stop(self) -> None:
        """Time stop should trigger when bars exceed limit."""
        highs = np.array([100.5, 100.5, 100.5])
        lows = np.array([99.5, 99.5, 99.5])
        closes = np.array([100.0, 100.0, 100.0])
        minutes = np.array([600, 601, 602])

        result = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=98.0,
            target_price=105.0,
            time_stop_bars=2,  # Hit at bar 2
        )

        assert result is not None
        assert result["exit_reason"] == "time_stop"
        assert result["hold_bars"] == 2


# ---------------------------------------------------------------------------
# Test 7: VWAP computation
# ---------------------------------------------------------------------------


class TestVwapComputation:
    """Test vectorized VWAP calculation."""

    def test_vwap_basic(self) -> None:
        """VWAP should be volume-weighted average of typical price."""
        high = np.array([102.0, 103.0, 104.0])
        low = np.array([98.0, 99.0, 100.0])
        close = np.array([100.0, 101.0, 102.0])
        volume = np.array([1000, 2000, 3000])

        vwap = _compute_vwap_vectorized(high, low, close, volume)

        assert len(vwap) == 3
        assert not np.isnan(vwap[0])
        # First bar VWAP = TP of first bar = (102+98+100)/3 = 100.0
        assert abs(vwap[0] - 100.0) < 0.01


# ---------------------------------------------------------------------------
# Test 8: Gap down day detection
# ---------------------------------------------------------------------------


class TestGapDownDays:
    """Test gap-down day identification."""

    def test_gap_down_detected(self) -> None:
        """Days with gap downs should be identified."""
        # Build 2-day data where day 2 gaps down
        rows = []
        for i in range(10):
            rows.append(
                {
                    "trading_day": date(2025, 6, 10),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 100_000,
                }
            )
        for i in range(10):
            rows.append(
                {
                    "trading_day": date(2025, 6, 11),
                    "open": 97.0,  # 3% gap down
                    "high": 98.0,
                    "low": 96.0,
                    "close": 97.5,
                    "volume": 100_000,
                }
            )

        df = pd.DataFrame(rows)
        gap_days = compute_gap_down_days(df, min_price=5.0, max_price=200.0)

        assert date(2025, 6, 11) in gap_days
        assert abs(gap_days[date(2025, 6, 11)] - 0.03) < 0.001

    def test_no_gap_down(self) -> None:
        """Days with gap up should not appear."""
        rows = []
        for i in range(10):
            rows.append(
                {
                    "trading_day": date(2025, 6, 10),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                    "volume": 100_000,
                }
            )
        for i in range(10):
            rows.append(
                {
                    "trading_day": date(2025, 6, 11),
                    "open": 103.0,  # Gap UP
                    "high": 104.0,
                    "low": 102.0,
                    "close": 103.5,
                    "volume": 100_000,
                }
            )

        df = pd.DataFrame(rows)
        gap_days = compute_gap_down_days(df, min_price=5.0, max_price=200.0)

        assert date(2025, 6, 11) not in gap_days
