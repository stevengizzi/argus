"""Tests for VectorBT ORB Scalp parameter sweep implementation."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from argus.backtest.vectorbt_orb_scalp import (
    ScalpSweepConfig,
    _find_scalp_exit_vectorized,
    _precompute_scalp_entries_for_day,
    compute_opening_ranges,
    compute_qualifying_days,
    generate_heatmap,
    load_symbol_data,
    run_single_symbol_sweep,
    run_sweep,
)


def _simulate_scalp_trade_for_day(
    day_bars: pd.DataFrame,
    or_high: float,
    or_low: float,
    or_complete_bar: int,
    scalp_target_r: float,
    max_hold_bars: int,
) -> dict | None:
    """Wrapper for testing that combines entry precomputation and exit finding.

    Stop is at OR midpoint (scalp strategy rule).
    """
    or_midpoint = (or_high + or_low) / 2

    # Precompute entry
    entry_info = _precompute_scalp_entries_for_day(
        day_bars=day_bars,
        or_high=or_high,
        or_low=or_low,
        or_complete_bar=or_complete_bar,
        or_midpoint=or_midpoint,
    )

    if entry_info is None:
        return None

    # Compute target
    stop_price = or_midpoint
    risk = entry_info["entry_price"] - stop_price
    if risk <= 0:
        return None

    target_price = entry_info["entry_price"] + scalp_target_r * risk

    # Find exit using vectorized function
    result = _find_scalp_exit_vectorized(
        post_entry_highs=entry_info["highs"],
        post_entry_lows=entry_info["lows"],
        post_entry_closes=entry_info["closes"],
        post_entry_bar_indices=entry_info["bar_indices"],
        entry_price=entry_info["entry_price"],
        entry_bar_idx=entry_info["entry_bar_idx"],
        stop_price=stop_price,
        target_price=target_price,
        max_hold_bars=max_hold_bars,
    )

    return result


# =============================================================================
# Test Fixtures
# =============================================================================


def create_synthetic_bars(
    trading_days: list[date],
    base_price: float = 100.0,
    gap_pcts: dict[date, float] | None = None,
    or_high_mult: dict[date, float] | None = None,
    breakout_bar: dict[date, int] | None = None,
    post_breakout: dict[date, str] | None = None,
) -> pd.DataFrame:
    """Create synthetic bar data with controlled properties."""
    gap_pcts = gap_pcts or {}
    or_high_mult = or_high_mult or {}
    breakout_bar = breakout_bar or {}
    post_breakout = post_breakout or {}

    bars = []
    prev_close = base_price

    for day in trading_days:
        gap = gap_pcts.get(day, 0.0) / 100.0
        day_open = prev_close * (1 + gap)

        for bar_num in range(390):
            timestamp = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC) + timedelta(
                minutes=bar_num
            )

            if bar_num < 5:  # Scalp uses 5-min OR
                offset = 0.001 * (1 if bar_num % 2 == 0 else -1)
                open_ = day_open * (1 + offset * bar_num / 10)
                close = day_open * (1 + offset * (bar_num + 1) / 10)
                high = max(open_, close) * or_high_mult.get(day, 1.002)
                low = min(open_, close) * 0.998
                volume = 5000 + bar_num * 100
            elif bar_num == breakout_bar.get(day, -1):
                or_high_approx = day_open * or_high_mult.get(day, 1.002)
                open_ = or_high_approx * 0.998
                close = or_high_approx * 1.01  # Clear breakout
                high = close * 1.005
                low = open_ * 0.997
                volume = 20000
            else:
                scenario = post_breakout.get(day, "drift")
                if scenario == "target" and bar_num > breakout_bar.get(day, -1):
                    base = day_open * 1.02
                    open_ = base * (1 + 0.001 * (bar_num - 5))
                    close = open_ * 1.002
                    high = close * 1.01  # Hit target
                    low = open_ * 0.999
                elif scenario == "stop" and bar_num > breakout_bar.get(day, -1):
                    base = day_open * 0.99
                    open_ = base
                    close = base * 0.99
                    high = base * 1.001
                    low = day_open * 0.97  # Hit stop
                else:
                    offset = 0.0005 * (1 if bar_num % 3 != 0 else -1)
                    open_ = day_open * (1 + offset * bar_num / 100)
                    close = open_ * (1 + offset)
                    high = max(open_, close) * 1.001
                    low = min(open_, close) * 0.999

                volume = 8000

            bars.append(
                {
                    "timestamp": timestamp,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": volume,
                }
            )

        prev_close = bars[-1]["close"]

    return pd.DataFrame(bars)


@pytest.fixture
def tmp_data_dir(tmp_path: Path) -> Path:
    """Create temporary data directory structure."""
    data_dir = tmp_path / "historical" / "1m"
    data_dir.mkdir(parents=True)
    return data_dir


@pytest.fixture
def simple_symbol_data(tmp_data_dir: Path) -> tuple[Path, str, list[date]]:
    """Create simple synthetic data for one symbol."""
    symbol = "TEST"
    trading_days = [date(2025, 6, 16), date(2025, 6, 17), date(2025, 6, 18)]

    df = create_synthetic_bars(trading_days, base_price=100.0)

    symbol_dir = tmp_data_dir / symbol
    symbol_dir.mkdir(parents=True)
    df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    return tmp_data_dir, symbol, trading_days


@pytest.fixture
def gap_up_data(tmp_data_dir: Path) -> tuple[Path, str, list[date]]:
    """Create data with specific gap percentages."""
    symbol = "GAPPY"
    trading_days = [
        date(2025, 6, 16),  # Day 1 - baseline
        date(2025, 6, 17),  # Day 2 - 3% gap
        date(2025, 6, 18),  # Day 3 - 1% gap
        date(2025, 6, 19),  # Day 4 - 5% gap
    ]

    gap_pcts = {
        date(2025, 6, 17): 3.0,
        date(2025, 6, 18): 1.0,
        date(2025, 6, 19): 5.0,
    }

    df = create_synthetic_bars(trading_days, base_price=50.0, gap_pcts=gap_pcts)

    symbol_dir = tmp_data_dir / symbol
    symbol_dir.mkdir(parents=True)
    df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    return tmp_data_dir, symbol, trading_days


# =============================================================================
# Config Validation Tests
# =============================================================================


def test_scalp_sweep_config_default_values():
    """Verify ScalpSweepConfig has correct default parameters."""
    config = ScalpSweepConfig(
        data_dir=Path("."),
        symbols=[],
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        output_dir=Path("."),
    )

    assert config.scalp_target_r_list == [0.2, 0.3, 0.4, 0.5]
    assert config.max_hold_bars_list == [1, 2, 3, 5]
    assert config.or_minutes == 5
    assert config.min_gap_pct == 2.0
    assert config.stop_buffer_pct == 0.0


def test_scalp_sweep_config_custom_values():
    """Custom parameter values override defaults."""
    config = ScalpSweepConfig(
        data_dir=Path("."),
        symbols=["AAPL"],
        start_date=date(2025, 1, 1),
        end_date=date(2025, 12, 31),
        output_dir=Path("."),
        scalp_target_r_list=[0.3, 0.5],
        max_hold_bars_list=[2, 3],
    )

    assert config.scalp_target_r_list == [0.3, 0.5]
    assert config.max_hold_bars_list == [2, 3]


# =============================================================================
# Data Loading Tests
# =============================================================================


def test_load_symbol_data_correct_columns(simple_symbol_data):
    """Load test Parquet data, verify expected columns exist."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])

    expected_cols = [
        "timestamp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "trading_day",
        "minutes_from_open",
        "bar_number_in_day",
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing column: {col}"


def test_load_symbol_data_nonexistent_symbol(tmp_data_dir):
    """Loading nonexistent symbol returns empty DataFrame."""
    df = load_symbol_data(tmp_data_dir, "NOSUCH", date(2025, 1, 1), date(2025, 12, 31))
    assert df.empty


# =============================================================================
# Qualifying Days Tests
# =============================================================================


def test_qualifying_days_gap_filter(gap_up_data):
    """Day with sufficient gap qualifies, day with small gap does not."""
    data_dir, symbol, trading_days = gap_up_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])

    # min_gap = 2% should qualify days with 3% and 5% gaps
    qualifying = compute_qualifying_days(df, min_gap_pct=2.0)

    assert date(2025, 6, 17) in qualifying  # 3% gap
    assert date(2025, 6, 18) not in qualifying  # 1% gap
    assert date(2025, 6, 19) in qualifying  # 5% gap


# =============================================================================
# Opening Range Tests
# =============================================================================


def test_opening_range_5min_computes_midpoint(simple_symbol_data):
    """Verify OR midpoint is computed (scalp uses midpoint as stop)."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    or_df = compute_opening_ranges(df, or_minutes=5)

    assert not or_df.empty
    assert "or_high" in or_df.columns
    assert "or_low" in or_df.columns
    assert "or_midpoint" in or_df.columns

    # Midpoint should be average of high and low
    for _, row in or_df.iterrows():
        expected_mid = (row["or_high"] + row["or_low"]) / 2
        assert row["or_midpoint"] == pytest.approx(expected_mid, rel=1e-6)


def test_opening_range_complete_bar_is_4_for_5min(simple_symbol_data):
    """5-min OR completes at bar 4 (0-indexed)."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    or_df = compute_opening_ranges(df, or_minutes=5)

    # OR complete bar should be 4 (bars 0-4 = 5 bars)
    assert all(or_df["or_complete_bar"] == 4)


# =============================================================================
# Exit Detection Tests
# =============================================================================


def test_target_hit_exits_at_target_price():
    """Verify trade exits at target price when target is hit."""
    day = date(2025, 6, 16)
    bars = []

    # Create bars where:
    # OR high = 102.0, OR low = 98.0, midpoint (stop) = 100.0
    # Entry at 102.50 (close above OR high)
    # Target = 102.50 + 0.3 * (102.50 - 100.0) = 102.50 + 0.75 = 103.25
    # Bar with high >= 103.25 should trigger target exit

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 5:  # OR bars
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 2 else 100.5
            low = 98.0 if bar_num == 3 else 99.5
            volume = 5000
        elif bar_num == 6:  # Breakout bar
            open_ = 101.5
            close = 102.50
            high = 103.0
            low = 101.0
            volume = 20000
        elif bar_num == 8:  # Target hit bar
            open_ = 103.0
            close = 103.5
            high = 104.0  # Above target of 103.25
            low = 102.8
            volume = 15000
        else:
            open_ = 102.0
            close = 102.5
            high = 103.0  # Below target
            low = 101.0  # Above stop (100.0)
            volume = 8000

        bars.append(
            {
                "timestamp": timestamp,
                "trading_day": day,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "minutes_from_open": bar_num,
                "bar_number_in_day": bar_num,
            }
        )

    day_bars = pd.DataFrame(bars)

    result = _simulate_scalp_trade_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=4,
        scalp_target_r=0.3,
        max_hold_bars=10,
    )

    assert result is not None
    assert result["exit_reason"] == "target"
    assert result["exit_price"] == pytest.approx(103.25, rel=0.01)
    assert result["r_multiple"] == pytest.approx(0.3, rel=0.01)


def test_stop_hit_exits_at_stop_price():
    """Verify trade exits at stop price (OR midpoint) when stop is hit."""
    day = date(2025, 6, 16)
    bars = []

    # Stop = OR midpoint = (102.0 + 98.0) / 2 = 100.0

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 5:
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 2 else 100.5
            low = 98.0 if bar_num == 3 else 99.5
            volume = 5000
        elif bar_num == 6:  # Breakout bar
            open_ = 101.5
            close = 102.50
            high = 103.0
            low = 101.0
            volume = 20000
        elif bar_num == 8:  # Stop hit bar
            open_ = 101.0
            close = 99.0
            high = 101.5
            low = 98.0  # Below stop of 100.0
            volume = 25000
        else:
            open_ = 102.0
            close = 102.5
            high = 103.0
            low = 101.0
            volume = 8000

        bars.append(
            {
                "timestamp": timestamp,
                "trading_day": day,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "minutes_from_open": bar_num,
                "bar_number_in_day": bar_num,
            }
        )

    day_bars = pd.DataFrame(bars)

    result = _simulate_scalp_trade_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=4,
        scalp_target_r=0.3,
        max_hold_bars=10,
    )

    assert result is not None
    assert result["exit_reason"] == "stop"
    assert result["exit_price"] == pytest.approx(100.0, rel=0.01)  # OR midpoint
    assert result["r_multiple"] == pytest.approx(-1.0, rel=0.01)


def test_time_stop_exits_at_bar_close():
    """Verify trade exits at close when max_hold_bars is reached."""
    day = date(2025, 6, 16)
    bars = []

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 5:
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 2 else 100.5
            low = 98.0 if bar_num == 3 else 99.5
            volume = 5000
        elif bar_num == 6:  # Breakout bar (entry)
            open_ = 101.5
            close = 102.50  # Entry price
            high = 103.0
            low = 101.0
            volume = 20000
        else:
            # All bars stay between stop (100.0) and target (~103.25)
            open_ = 102.0
            close = 102.0  # Close for time stop exit
            high = 103.0  # Below target
            low = 101.0  # Above stop
            volume = 8000

        bars.append(
            {
                "timestamp": timestamp,
                "trading_day": day,
                "open": open_,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume,
                "minutes_from_open": bar_num,
                "bar_number_in_day": bar_num,
            }
        )

    day_bars = pd.DataFrame(bars)

    result = _simulate_scalp_trade_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=4,
        scalp_target_r=0.3,
        max_hold_bars=3,  # 3 bars = exit at bar 9 (entry at bar 6)
    )

    assert result is not None
    assert result["exit_reason"] == "time_stop"
    assert result["hold_bars"] == 3
    assert result["exit_price"] == 102.0  # Close of time stop bar


# =============================================================================
# Full Sweep Tests
# =============================================================================


def test_single_symbol_single_combo_produces_correct_trade_count():
    """Single param combo on synthetic data produces expected trade count."""
    # Create 3 days where day 2 has a gap and breakout
    trading_days = [date(2025, 6, 16), date(2025, 6, 17), date(2025, 6, 18)]
    bars = []
    prev_close = 100.0

    for day in trading_days:
        # Apply 3% gap on day 2
        gap_mult = 1.03 if day == date(2025, 6, 17) else 1.001
        day_open = prev_close * gap_mult

        for bar_num in range(390):
            ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)

            if bar_num < 5:  # OR bars
                high = day_open * 1.002
                low = day_open * 0.998
                open_ = day_open
                close = day_open
            elif bar_num == 6 and day == date(2025, 6, 17):  # Breakout on day 2
                open_ = day_open * 1.001
                close = day_open * 1.005  # Above OR high
                high = close * 1.001
                low = open_ * 0.999
            else:
                open_ = day_open * 1.001
                close = day_open * 1.001
                high = close * 1.002
                low = open_ * 0.998

            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": day,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 10000,
                    "minutes_from_open": bar_num,
                    "bar_number_in_day": bar_num,
                }
            )

        prev_close = bars[-1]["close"]

    df = pd.DataFrame(bars)

    config = ScalpSweepConfig(
        data_dir=Path("."),
        symbols=["TEST"],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=Path("."),
        scalp_target_r_list=[0.3],
        max_hold_bars_list=[5],
        min_gap_pct=2.0,
    )

    results = run_single_symbol_sweep(df, "TEST", config)

    # Should have exactly 1 result (1 param combo)
    assert len(results) == 1
    # Day 2 has gap >= 2% and breakout, so should have 1 trade
    assert results[0].total_trades == 1


def test_sweep_result_count(simple_symbol_data):
    """1 symbol, 4×4 grid = 16 combinations."""
    data_dir, symbol, trading_days = simple_symbol_data

    config = ScalpSweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        # Default 4×4 = 16 combinations
    )

    results = run_sweep(config)

    assert len(results) == 16


def test_sweep_output_columns(simple_symbol_data):
    """Run small sweep, verify ScalpSweepResult has all expected fields."""
    data_dir, symbol, trading_days = simple_symbol_data

    config = ScalpSweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        scalp_target_r_list=[0.3],
        max_hold_bars_list=[3],
    )

    results = run_sweep(config)

    expected_cols = [
        "symbol",
        "scalp_target_r",
        "max_hold_bars",
        "total_trades",
        "win_rate",
        "total_return_pct",
        "avg_r_multiple",
        "max_drawdown_pct",
        "sharpe_ratio",
        "profit_factor",
        "avg_hold_bars",
        "qualifying_days",
    ]

    for col in expected_cols:
        assert col in results.columns, f"Missing column: {col}"


def test_multi_symbol_aggregation(tmp_data_dir):
    """Multiple symbols produce separate results that are aggregated."""
    symbols = ["AAPL", "TSLA"]
    trading_days = [date(2025, 6, 16), date(2025, 6, 17)]

    for symbol in symbols:
        df = create_synthetic_bars(trading_days, base_price=100.0)
        symbol_dir = tmp_data_dir / symbol
        symbol_dir.mkdir(parents=True)
        df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    config = ScalpSweepConfig(
        data_dir=tmp_data_dir,
        symbols=symbols,
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=tmp_data_dir.parent / "sweeps",
        scalp_target_r_list=[0.3],
        max_hold_bars_list=[3],
    )

    results = run_sweep(config)

    # 2 symbols × 1 combo = 2 results
    assert len(results) == 2
    assert set(results["symbol"].unique()) == {"AAPL", "TSLA"}


# =============================================================================
# Heatmap Generation Tests
# =============================================================================


def test_heatmap_html_created(simple_symbol_data):
    """Run sweep → call generate_heatmap → HTML file exists."""
    pytest.importorskip("plotly")
    data_dir, symbol, trading_days = simple_symbol_data

    output_dir = data_dir.parent / "sweeps"

    config = ScalpSweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=output_dir,
    )

    results = run_sweep(config)
    generate_heatmap(results, output_dir)

    assert (output_dir / "scalp_heatmap.html").exists()


def test_heatmap_empty_results_handles_gracefully(tmp_data_dir):
    """Empty results don't crash heatmap generation."""
    pytest.importorskip("plotly")
    output_dir = tmp_data_dir.parent / "sweeps"
    output_dir.mkdir(parents=True, exist_ok=True)

    empty_results = pd.DataFrame()
    generate_heatmap(empty_results, output_dir)

    # Should not crash; heatmap file may not be created for empty results


# =============================================================================
# CLI Tests
# =============================================================================


def test_cli_runs_without_error(simple_symbol_data, monkeypatch, capsys):
    """Call main() with small synthetic dataset and minimal params."""
    pytest.importorskip("plotly")
    import sys

    from argus.backtest.vectorbt_orb_scalp import main

    data_dir, symbol, trading_days = simple_symbol_data
    output_dir = data_dir.parent / "sweeps"

    test_args = [
        "vectorbt_orb_scalp",
        "--data-dir",
        str(data_dir),
        "--symbols",
        symbol,
        "--start",
        str(trading_days[0]),
        "--end",
        str(trading_days[-1]),
        "--output-dir",
        str(output_dir),
        "--target-r",
        "0.3",
        "--max-hold-bars",
        "3",
    ]

    monkeypatch.setattr(sys, "argv", test_args)

    main()

    captured = capsys.readouterr()
    assert "Sweep complete" in captured.out
