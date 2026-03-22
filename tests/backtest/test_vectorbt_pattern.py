"""Tests for the generic PatternBacktester.

Validates sliding-window detection, CandleBar conversion, parameter grid
generation, and walk-forward execution using mock and real pattern modules.
"""

from __future__ import annotations

from datetime import datetime, date
from pathlib import Path
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest
import yaml

from argus.backtest.vectorbt_pattern import (
    PatternBacktester,
    PatternSweepResult,
    PatternTradeInfo,
    _compute_metrics,
    _find_exit_vectorized,
    df_window_to_candle_bars,
    ohlcv_row_to_candle_bar,
)
from argus.strategies.patterns.base import CandleBar, PatternDetection, PatternModule
from argus.strategies.patterns.bull_flag import BullFlagPattern
from argus.strategies.patterns.flat_top_breakout import FlatTopBreakoutPattern

ET = ZoneInfo("America/New_York")


# --- Helpers ---


def _make_day_df(
    n_bars: int = 60,
    base_price: float = 100.0,
    base_volume: float = 10000.0,
    day: date | None = None,
    start_minute: int = 570,  # 9:30 AM
) -> pd.DataFrame:
    """Create a synthetic single-day OHLCV DataFrame.

    Generates bars with slight upward drift and random-ish variation
    suitable for pattern detection tests.
    """
    if day is None:
        day = date(2025, 6, 15)

    rows = []
    price = base_price
    for i in range(n_bars):
        ts = datetime(day.year, day.month, day.day, 9, 30, tzinfo=ET) + pd.Timedelta(minutes=i)
        # Slight upward drift
        open_p = price
        high_p = price + 0.5
        low_p = price - 0.3
        close_p = price + 0.1
        vol = base_volume + i * 100

        rows.append({
            "timestamp": ts,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol,
            "trading_day": day,
            "minutes_from_midnight": start_minute + i,
        })
        price = close_p

    return pd.DataFrame(rows)


def _make_config_file(tmp_path: Path, config: dict[str, object]) -> Path:
    """Write a strategy config YAML to a temp file."""
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(config, f)
    return config_path


class MockPattern(PatternModule):
    """Mock pattern that detects on every bar for testing."""

    def __init__(
        self,
        lookback: int = 5,
        min_price: float = 50.0,
    ) -> None:
        self._lookback = lookback
        self._min_price = min_price

    @property
    def name(self) -> str:
        return "Mock Pattern"

    @property
    def lookback_bars(self) -> int:
        return self._lookback

    def detect(
        self,
        candles: list[CandleBar],
        indicators: dict[str, float],
    ) -> PatternDetection | None:
        if not candles:
            return None
        last = candles[-1]
        if last.close < self._min_price:
            return None
        return PatternDetection(
            pattern_type="mock",
            confidence=75.0,
            entry_price=last.close,
            stop_price=last.low,
            target_prices=(last.close + 1.0,),
            metadata={"test": True},
        )

    def score(self, detection: PatternDetection) -> float:
        return detection.confidence

    def get_default_params(self) -> dict[str, object]:
        return {
            "lookback": self._lookback,
            "min_price": self._min_price,
        }


# --- Tests ---


class TestCandleBarConversion:
    """Test OHLCV row → CandleBar conversion."""

    def test_single_row_conversion(self) -> None:
        """ohlcv_row_to_candle_bar produces correct CandleBar fields."""
        ts = datetime(2025, 6, 15, 10, 30, tzinfo=ET)
        bar = ohlcv_row_to_candle_bar(ts, 100.0, 101.5, 99.5, 101.0, 50000.0)

        assert bar.timestamp == ts
        assert bar.open == 100.0
        assert bar.high == 101.5
        assert bar.low == 99.5
        assert bar.close == 101.0
        assert bar.volume == 50000.0

    def test_df_window_to_candle_bars_correct_count(self) -> None:
        """df_window_to_candle_bars returns exact count of bars requested."""
        df = _make_day_df(n_bars=20)
        candles = df_window_to_candle_bars(df, start_idx=5, count=10)

        assert len(candles) == 10

    def test_df_window_preserves_order(self) -> None:
        """CandleBars are chronologically ordered matching DataFrame rows."""
        df = _make_day_df(n_bars=10)
        candles = df_window_to_candle_bars(df, start_idx=0, count=5)

        for i in range(len(candles) - 1):
            assert candles[i].timestamp < candles[i + 1].timestamp

    def test_df_window_clamps_at_end(self) -> None:
        """Requesting beyond DataFrame end returns available bars only."""
        df = _make_day_df(n_bars=10)
        candles = df_window_to_candle_bars(df, start_idx=8, count=10)

        assert len(candles) == 2


class TestSlidingWindowSize:
    """Test that the sliding window uses pattern.lookback_bars correctly."""

    def test_window_matches_lookback_bars(self, tmp_path: Path) -> None:
        """generate_signals creates windows of exactly lookback_bars + 1 candles."""
        lookback = 7
        pattern = MockPattern(lookback=lookback)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0, "time_stop_minutes": 30})
        backtester = PatternBacktester(pattern, config_path)

        df = _make_day_df(n_bars=20)

        # Spy on detect calls to verify window size
        original_detect = pattern.detect
        window_sizes: list[int] = []

        def spy_detect(candles: list[CandleBar], indicators: dict[str, float]) -> PatternDetection | None:
            window_sizes.append(len(candles))
            return original_detect(candles, indicators)

        pattern.detect = spy_detect  # type: ignore[assignment]

        backtester.generate_signals(df, pattern)

        # The window should be lookback + 1 (lookback history + current bar)
        assert len(window_sizes) > 0
        assert all(size == lookback + 1 for size in window_sizes)

    def test_insufficient_bars_returns_empty(self, tmp_path: Path) -> None:
        """generate_signals returns empty when data is shorter than lookback."""
        pattern = MockPattern(lookback=50)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0, "time_stop_minutes": 30})
        backtester = PatternBacktester(pattern, config_path)

        df = _make_day_df(n_bars=10)
        candidates = backtester.generate_signals(df, pattern)

        assert candidates == []


class TestGenericBacktesterWithMockPattern:
    """Test PatternBacktester with a mock PatternModule."""

    def test_generates_signals_from_mock(self, tmp_path: Path) -> None:
        """Mock pattern that always detects produces entry candidates."""
        pattern = MockPattern(lookback=3)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0, "time_stop_minutes": 30})
        backtester = PatternBacktester(pattern, config_path)

        df = _make_day_df(n_bars=30)
        candidates = backtester.generate_signals(df, pattern)

        # MockPattern detects on every bar, but one entry per day
        assert len(candidates) == 1
        assert candidates[0].detection.pattern_type == "mock"
        assert candidates[0].score == 75.0

    def test_sweep_returns_results(self, tmp_path: Path) -> None:
        """run_sweep produces a non-empty DataFrame with expected columns."""
        pattern = MockPattern(lookback=3)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0, "time_stop_minutes": 30})
        backtester = PatternBacktester(pattern, config_path)

        df = _make_day_df(n_bars=30)
        results = backtester.run_sweep(df)

        assert not results.empty
        assert "total_trades" in results.columns
        assert "sharpe_ratio" in results.columns
        assert "win_rate" in results.columns
        assert "pattern" in results.columns
        assert all(results["pattern"] == "Mock Pattern")

    def test_sweep_has_multiple_param_combos(self, tmp_path: Path) -> None:
        """run_sweep tests multiple parameter combinations."""
        pattern = MockPattern(lookback=3, min_price=50.0)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0, "time_stop_minutes": 30})
        backtester = PatternBacktester(pattern, config_path)

        grid = backtester.build_parameter_grid()
        # 2 params (lookback, min_price), each with ~5 variations = 25 combos
        assert len(grid) > 1

        df = _make_day_df(n_bars=30)
        results = backtester.run_sweep(df)
        assert len(results) > 1


class TestParameterGridFromDefaults:
    """Test parameter grid generation from get_default_params."""

    def test_grid_includes_defaults(self, tmp_path: Path) -> None:
        """The default parameter values are included in the grid."""
        pattern = MockPattern(lookback=5, min_price=50.0)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0})
        backtester = PatternBacktester(pattern, config_path)

        grid = backtester.build_parameter_grid()
        defaults = pattern.get_default_params()

        # Check that exact defaults appear in at least one combo
        has_defaults = any(
            combo["lookback"] == defaults["lookback"]
            and combo["min_price"] == defaults["min_price"]
            for combo in grid
        )
        assert has_defaults

    def test_grid_creates_variations(self, tmp_path: Path) -> None:
        """Grid contains ±20% and ±40% variations for numeric params."""
        pattern = MockPattern(lookback=10, min_price=100.0)
        config_path = _make_config_file(tmp_path, {"target_1_r": 1.0})
        backtester = PatternBacktester(pattern, config_path)

        grid = backtester.build_parameter_grid()

        # Extract unique lookback values
        lookback_values = sorted({combo["lookback"] for combo in grid})
        # Should have ~5 values: 6, 8, 10, 12, 14
        assert len(lookback_values) == 5
        assert 10 in lookback_values  # default
        assert 6 in lookback_values   # 10 * 0.6
        assert 14 in lookback_values  # 10 * 1.4

        # Extract unique min_price values
        price_values = sorted({combo["min_price"] for combo in grid})
        assert len(price_values) == 5
        assert 100.0 in price_values
        assert 60.0 in price_values   # 100 * 0.6
        assert 140.0 in price_values  # 100 * 1.4

    def test_grid_with_bull_flag_params(self, tmp_path: Path) -> None:
        """Bull Flag pattern produces a valid parameter grid."""
        pattern = BullFlagPattern()
        config_path = _make_config_file(tmp_path, {
            "target_1_r": 1.0,
            "time_stop_minutes": 30,
        })
        backtester = PatternBacktester(pattern, config_path)

        grid = backtester.build_parameter_grid()

        # BullFlagPattern has 5 params, each with ~5 variations
        assert len(grid) > 10
        # All combos should have the expected keys
        expected_keys = {
            "pole_min_bars",
            "pole_min_move_pct",
            "flag_max_bars",
            "flag_max_retrace_pct",
            "breakout_volume_multiplier",
        }
        for combo in grid:
            assert set(combo.keys()) == expected_keys

    def test_grid_with_flat_top_params(self, tmp_path: Path) -> None:
        """Flat-Top Breakout pattern produces a valid parameter grid."""
        pattern = FlatTopBreakoutPattern()
        config_path = _make_config_file(tmp_path, {
            "target_1_r": 1.0,
            "time_stop_minutes": 30,
        })
        backtester = PatternBacktester(pattern, config_path)

        grid = backtester.build_parameter_grid()

        assert len(grid) > 10
        expected_keys = {
            "resistance_touches",
            "resistance_tolerance_pct",
            "consolidation_min_bars",
            "breakout_volume_multiplier",
            "target_1_r",
            "target_2_r",
        }
        for combo in grid:
            assert set(combo.keys()) == expected_keys


def _create_synthetic_parquet(
    data_dir: Path,
    symbol: str,
    start: date,
    end: date,
    bars_per_day: int = 30,
) -> None:
    """Create synthetic Parquet data for walk-forward tests.

    Uses minimal bars per day to keep tests fast while covering
    enough trading days for walk-forward windows.
    """
    symbol_dir = data_dir / symbol
    symbol_dir.mkdir(parents=True, exist_ok=True)

    all_rows = []
    current = start
    price = 100.0

    while current <= end:
        if current.weekday() < 5:
            for minute in range(bars_per_day):
                ts = pd.Timestamp(
                    year=current.year,
                    month=current.month,
                    day=current.day,
                    hour=9,
                    minute=30,
                    tz=ET,
                ) + pd.Timedelta(minutes=minute)

                open_p = price
                high_p = price + 0.5
                low_p = price - 0.3
                close_p = price + 0.1
                vol = 10000.0

                all_rows.append({
                    "timestamp": ts,
                    "open": open_p,
                    "high": high_p,
                    "low": max(low_p, 1.0),
                    "close": close_p,
                    "volume": vol,
                })
                price = close_p

        current = current + pd.Timedelta(days=1)

    df = pd.DataFrame(all_rows)
    parquet_path = symbol_dir / f"{symbol}_2025.parquet"
    df.to_parquet(parquet_path, index=False)


class TestBullFlagWalkForward:
    """Test walk-forward with BullFlagPattern (mock data, smoke test)."""

    def test_walk_forward_runs_without_error(self, tmp_path: Path) -> None:
        """Walk-forward completes and returns expected structure (mock data).

        Uses MockPattern (2 params = 25 combos) for speed. The real
        BullFlagPattern grid (5 params = 3125 combos) is validated by
        the grid tests above; this tests the walk-forward plumbing.
        """
        config_path = _make_config_file(tmp_path, {
            "target_1_r": 1.0,
            "time_stop_minutes": 30,
        })

        # Use MockPattern for speed (small grid), proving the generic
        # backtester works with any PatternModule through walk-forward
        pattern = MockPattern(lookback=3)
        backtester = PatternBacktester(pattern, config_path)

        start = date(2025, 1, 1)
        end = date(2025, 8, 31)
        _create_synthetic_parquet(tmp_path / "data", "MOCK", start, end, bars_per_day=15)

        result = backtester.run_walk_forward(
            data_dir=tmp_path / "data",
            symbols=["MOCK"],
            start_date=start,
            end_date=end,
            in_sample_months=3,
            out_of_sample_months=2,
            step_months=2,
            min_trades=1,
        )

        assert "status" in result
        assert result["status"] in ("validated", "exploration", "no_data")
        assert "avg_wfe_sharpe" in result
        assert "windows" in result
        assert isinstance(result["windows"], list)
        assert result["total_windows"] >= 1


class TestFlatTopWalkForward:
    """Test walk-forward with FlatTopBreakoutPattern (mock data, smoke test)."""

    def test_walk_forward_runs_without_error(self, tmp_path: Path) -> None:
        """Walk-forward completes and returns expected structure (mock data).

        Uses MockPattern for speed. Tests the walk-forward plumbing is
        generic across any PatternModule, independent of specific pattern
        parameters.
        """
        config_path = _make_config_file(tmp_path, {
            "target_1_r": 1.0,
            "time_stop_minutes": 30,
        })

        pattern = MockPattern(lookback=3)
        backtester = PatternBacktester(pattern, config_path)

        start = date(2025, 1, 1)
        end = date(2025, 8, 31)
        _create_synthetic_parquet(tmp_path / "data", "MOCK", start, end, bars_per_day=15)

        result = backtester.run_walk_forward(
            data_dir=tmp_path / "data",
            symbols=["MOCK"],
            start_date=start,
            end_date=end,
            in_sample_months=3,
            out_of_sample_months=2,
            step_months=2,
            min_trades=1,
        )

        assert "status" in result
        assert result["status"] in ("validated", "exploration", "no_data")
        assert "avg_wfe_sharpe" in result
        assert "windows" in result
        assert isinstance(result["windows"], list)


class TestVectorizedExitDetection:
    """Test the vectorized exit detection logic."""

    def test_stop_loss_hit(self) -> None:
        """Stop loss is detected when low breaches stop price."""
        highs = np.array([101.0, 102.0, 103.0])
        lows = np.array([99.0, 98.0, 97.0])
        closes = np.array([100.5, 99.5, 98.5])
        minutes = np.array([600, 601, 602])

        trade = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=99.5,
            target_price=105.0,
            time_stop_bars=100,
        )

        assert trade is not None
        assert trade.exit_reason == "stop"
        assert trade.exit_price == 99.5

    def test_target_hit(self) -> None:
        """Target is detected when high reaches target price."""
        highs = np.array([101.0, 103.0, 106.0])
        lows = np.array([99.5, 100.0, 101.0])
        closes = np.array([100.5, 102.0, 105.0])
        minutes = np.array([600, 601, 602])

        trade = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=98.0,
            target_price=105.0,
            time_stop_bars=100,
        )

        assert trade is not None
        assert trade.exit_reason == "target"
        assert trade.exit_price == 105.0

    def test_time_stop(self) -> None:
        """Time stop triggers after specified bars."""
        highs = np.array([101.0, 101.0, 101.0])
        lows = np.array([99.5, 99.5, 99.5])
        closes = np.array([100.5, 100.5, 100.5])
        minutes = np.array([600, 601, 602])

        trade = _find_exit_vectorized(
            highs, lows, closes, minutes,
            entry_price=100.0,
            stop_price=98.0,
            target_price=110.0,
            time_stop_bars=2,
        )

        assert trade is not None
        assert trade.exit_reason == "time_stop"


class TestComputeMetrics:
    """Test trade metrics computation."""

    def test_empty_trades(self) -> None:
        """Empty trade list returns zero metrics."""
        metrics = _compute_metrics([])
        assert metrics["total_trades"] == 0
        assert metrics["win_rate"] == 0.0

    def test_all_winners(self) -> None:
        """All winning trades produce 100% win rate."""
        trades = [
            PatternTradeInfo(100, 102, 2, 2, 1.0, 5, "target"),
            PatternTradeInfo(100, 103, 2, 3, 1.5, 8, "target"),
        ]
        metrics = _compute_metrics(trades)
        assert metrics["total_trades"] == 2
        assert metrics["win_rate"] == 1.0
        assert metrics["avg_r_multiple"] == 1.25
