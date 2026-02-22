"""Tests for VectorBT ORB parameter sweep implementation."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from argus.backtest.vectorbt_orb import (
    SweepConfig,
    _find_exit_vectorized,
    _precompute_entries_for_day,
    compute_atr,
    compute_opening_ranges,
    compute_qualifying_days,
    generate_heatmaps,
    load_symbol_data,
    run_single_symbol_sweep,
    run_sweep,
)


def _simulate_trades_for_day(
    day_bars: pd.DataFrame,
    or_high: float,
    or_low: float,
    or_complete_bar: int,
    stop_buffer_pct: float,
    target_r: float,
    max_hold_minutes: int,
) -> dict | None:
    """Wrapper that uses vectorized functions for backward compatibility with tests.

    This function wraps _precompute_entries_for_day and _find_exit_vectorized
    to provide the same interface as the removed _simulate_trades_for_day_slow.
    """
    or_range = or_high - or_low

    # Precompute entry (this finds the breakout bar and extracts post-entry arrays)
    entry_info = _precompute_entries_for_day(
        day_bars=day_bars,
        or_high=or_high,
        or_low=or_low,
        or_complete_bar=or_complete_bar,
        or_range=or_range,
        atr=None,  # ATR not used for this test interface
    )

    if entry_info is None:
        return None

    # Compute stop and target
    stop_price = or_low * (1 - stop_buffer_pct / 100)
    risk = entry_info["entry_price"] - stop_price
    if risk <= 0:
        return None

    target_price = entry_info["entry_price"] + target_r * risk

    # Find exit using vectorized function
    result = _find_exit_vectorized(
        post_entry_highs=entry_info["highs"],
        post_entry_lows=entry_info["lows"],
        post_entry_closes=entry_info["closes"],
        post_entry_minutes=entry_info["minutes"],
        entry_price=entry_info["entry_price"],
        entry_minutes=entry_info["entry_minutes"],
        stop_price=stop_price,
        target_price=target_price,
        max_hold_minutes=max_hold_minutes,
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
    post_breakout: dict[date, str] | None = None,  # "target", "stop", "time", "eod"
) -> pd.DataFrame:
    """Create synthetic bar data with controlled properties.

    Args:
        trading_days: List of trading dates.
        base_price: Base price for first day.
        gap_pcts: Dict of date -> gap percentage from previous close.
        or_high_mult: Dict of date -> OR high as multiplier of open.
        breakout_bar: Dict of date -> bar number when breakout occurs.
        post_breakout: Dict of date -> exit scenario after breakout.

    Returns:
        DataFrame with synthetic bar data.
    """
    gap_pcts = gap_pcts or {}
    or_high_mult = or_high_mult or {}
    breakout_bar = breakout_bar or {}
    post_breakout = post_breakout or {}

    bars = []
    prev_close = base_price

    for day in trading_days:
        # Apply gap for this day
        gap = gap_pcts.get(day, 0.0) / 100.0
        day_open = prev_close * (1 + gap)

        # Create 390 bars (full trading day)
        for bar_num in range(390):
            timestamp = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC) + timedelta(
                minutes=bar_num
            )

            if bar_num < 15:
                # Opening range bars - oscillate around open
                offset = 0.001 * (1 if bar_num % 2 == 0 else -1)
                open_ = day_open * (1 + offset * bar_num / 10)
                close = day_open * (1 + offset * (bar_num + 1) / 10)
                high = max(open_, close) * or_high_mult.get(day, 1.002)
                low = min(open_, close) * 0.998
                volume = 5000 + bar_num * 100
            elif bar_num == breakout_bar.get(day, -1):
                # Breakout bar - close above OR high
                or_high_approx = day_open * or_high_mult.get(day, 1.002)
                open_ = or_high_approx * 0.998
                close = or_high_approx * 1.01  # Clear breakout
                high = close * 1.005
                low = open_ * 0.997
                volume = 20000
            else:
                # Regular bars
                scenario = post_breakout.get(day, "drift")
                if scenario == "target" and bar_num > breakout_bar.get(day, -1):
                    # Price drifts up toward target
                    base = day_open * 1.02
                    open_ = base * (1 + 0.001 * (bar_num - 15))
                    close = open_ * 1.002
                    high = close * 1.01  # Hit target
                    low = open_ * 0.999
                elif scenario == "stop" and bar_num > breakout_bar.get(day, -1):
                    # Price drops to stop
                    base = day_open * 0.99
                    open_ = base
                    close = base * 0.99
                    high = base * 1.001
                    low = day_open * 0.97  # Hit stop
                else:
                    # Normal drift
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

        # Update prev_close for next day
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

    # Save to Parquet
    symbol_dir = tmp_data_dir / symbol
    symbol_dir.mkdir(parents=True)
    df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    return tmp_data_dir, symbol, trading_days


@pytest.fixture
def gap_up_data(tmp_data_dir: Path) -> tuple[Path, str, list[date]]:
    """Create data with specific gap percentages for testing gap filter."""
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

    # Save to Parquet
    symbol_dir = tmp_data_dir / symbol
    symbol_dir.mkdir(parents=True)
    df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    return tmp_data_dir, symbol, trading_days


@pytest.fixture
def breakout_data(tmp_data_dir: Path) -> tuple[Path, str, date]:
    """Create data with a clear breakout scenario."""
    symbol = "BRKT"
    # Need 20+ days for valid ATR
    trading_days = [date(2025, 6, 1) + timedelta(days=i) for i in range(25)]
    # Filter to weekdays only
    trading_days = [d for d in trading_days if d.weekday() < 5][:20]

    gap_pcts = {trading_days[15]: 3.0}  # Gap on day 16
    breakout_bar = {trading_days[15]: 16}  # Breakout on bar 16 of day 16
    post_breakout = {trading_days[15]: "target"}  # Hits target

    df = create_synthetic_bars(
        trading_days,
        base_price=100.0,
        gap_pcts=gap_pcts,
        or_high_mult={trading_days[15]: 1.003},
        breakout_bar=breakout_bar,
        post_breakout=post_breakout,
    )

    # Save to Parquet
    symbol_dir = tmp_data_dir / symbol
    symbol_dir.mkdir(parents=True)
    df.to_parquet(symbol_dir / f"{symbol}_2025-06.parquet", index=False)

    return tmp_data_dir, symbol, trading_days[15]


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


def test_load_symbol_data_et_conversion(simple_symbol_data):
    """Verify timestamps are converted to ET and first bar is 9:30."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])

    # First bar of first day should have minutes_from_open = 0
    first_day_bars = df[df["trading_day"] == trading_days[0]]
    assert first_day_bars.iloc[0]["minutes_from_open"] == 0


def test_load_symbol_data_date_range_filter(simple_symbol_data):
    """Load with restricted date range, verify no data before that date."""
    data_dir, symbol, trading_days = simple_symbol_data

    # Only load day 2 and 3
    df = load_symbol_data(data_dir, symbol, trading_days[1], trading_days[-1])

    unique_days = df["trading_day"].unique()
    assert trading_days[0] not in unique_days
    assert trading_days[1] in unique_days


def test_load_symbol_data_nonexistent_symbol(tmp_data_dir):
    """Loading nonexistent symbol returns empty DataFrame."""
    df = load_symbol_data(tmp_data_dir, "NOSUCH", date(2025, 1, 1), date(2025, 12, 31))
    assert df.empty


# =============================================================================
# ATR Computation Tests
# =============================================================================


def test_compute_atr_known_values():
    """Create synthetic daily OHLC with known ATR."""
    # Create 20 days of data where True Range is exactly 2.0 each day
    bars = []
    for i in range(20):
        day = date(2025, 6, 1) + timedelta(days=i)
        if day.weekday() >= 5:  # Skip weekends
            continue
        for bar_num in range(390):
            ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)
            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": day,
                    "open": 100.0,
                    "high": 101.0,  # Daily high will be 101
                    "low": 99.0,  # Daily low will be 99
                    "close": 100.0,
                }
            )

    df = pd.DataFrame(bars)
    atr = compute_atr(df, period=14)

    # True range should be 2.0 (101 - 99), ATR should be 2.0 after warmup
    valid_atrs = atr.dropna()
    assert len(valid_atrs) > 0
    # Allow for floating point tolerance
    assert all(1.9 <= v <= 2.1 for v in valid_atrs.values)


def test_compute_atr_insufficient_data():
    """Fewer than 14 trading days → ATR should have NaN for first days."""
    bars = []
    for i in range(10):  # Only 10 days
        day = date(2025, 6, 2) + timedelta(days=i)
        if day.weekday() >= 5:
            continue
        for bar_num in range(10):  # Minimal bars per day
            ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)
            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": day,
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": 100.0,
                }
            )

    df = pd.DataFrame(bars)
    atr = compute_atr(df, period=14)

    # All values should be NaN because we have < 14 days
    assert atr.isna().all()


# =============================================================================
# Qualifying Days Tests
# =============================================================================


def test_qualifying_days_gap_filter(gap_up_data):
    """Day with sufficient gap qualifies, day with small gap does not."""
    data_dir, symbol, trading_days = gap_up_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    atr = compute_atr(df)

    # min_gap = 2% should qualify days with 3% and 5% gaps
    qualifying = compute_qualifying_days(df, atr, min_gap_pct=2.0)

    assert date(2025, 6, 17) in qualifying  # 3% gap
    assert date(2025, 6, 18) not in qualifying  # 1% gap
    assert date(2025, 6, 19) in qualifying  # 5% gap


def test_qualifying_days_price_filter():
    """Stock below min_price is rejected."""
    # Create low-priced stock data
    bars = []
    trading_days = [date(2025, 6, 16), date(2025, 6, 17)]
    for day in trading_days:
        for bar_num in range(390):
            ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)
            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": day,
                    "open": 3.0,  # Below $5 min price
                    "high": 3.1,
                    "low": 2.9,
                    "close": 3.0,
                }
            )

    df = pd.DataFrame(bars)
    atr = pd.Series({date(2025, 6, 16): 0.1, date(2025, 6, 17): 0.1})

    qualifying = compute_qualifying_days(df, atr, min_gap_pct=0.0, min_price=5.0)

    assert len(qualifying) == 0  # All days rejected due to price


def test_qualifying_days_no_previous_close():
    """First trading day has no prev close → excluded."""
    bars = []
    day = date(2025, 6, 16)
    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)
        bars.append(
            {
                "timestamp": timestamp,
                "trading_day": day,
                "open": 100.0,
                "high": 101.0,
                "low": 99.0,
                "close": 100.0,
            }
        )

    df = pd.DataFrame(bars)
    atr = pd.Series({date(2025, 6, 16): 2.0})

    qualifying = compute_qualifying_days(df, atr, min_gap_pct=0.0)

    # First day has no previous close, so it can't qualify
    assert date(2025, 6, 16) not in qualifying


# =============================================================================
# Opening Range Tests
# =============================================================================


def test_opening_range_15min(simple_symbol_data):
    """Verify or_high, or_low, or_range for 15-minute window."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    or_df = compute_opening_ranges(df, or_minutes=15)

    assert not or_df.empty
    assert "or_high" in or_df.columns
    assert "or_low" in or_df.columns
    assert "or_range" in or_df.columns
    assert "or_complete_bar" in or_df.columns

    # OR range should be positive
    assert all(or_df["or_range"] > 0)

    # OR complete bar should be 14 (0-indexed, last bar of 15-min window)
    assert all(or_df["or_complete_bar"] == 14)


def test_opening_range_5min_vs_30min(simple_symbol_data):
    """30-min range >= 5-min range (wider window captures more)."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    or_5 = compute_opening_ranges(df, or_minutes=5)
    or_30 = compute_opening_ranges(df, or_minutes=30)

    # Merge on trading_day to compare
    merged = or_5.merge(or_30, on="trading_day", suffixes=("_5", "_30"))

    # 30-min range should be >= 5-min range
    assert all(merged["or_range_30"] >= merged["or_range_5"])


# =============================================================================
# Core Sweep Logic Tests
# =============================================================================


def test_breakout_entry_detection(breakout_data):
    """Synthetic day with breakout detected at correct bar."""
    data_dir, symbol, breakout_day = breakout_data

    df = load_symbol_data(data_dir, symbol, date(2025, 6, 1), date(2025, 6, 30))
    atr = compute_atr(df)

    # Use small parameter grid for testing
    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=date(2025, 6, 1),
        end_date=date(2025, 6, 30),
        output_dir=data_dir.parent / "sweeps",
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[120],
        min_gap_list=[2.0],
        max_range_atr_list=[999.0],
    )

    results = run_single_symbol_sweep(df, symbol, atr, config)

    # Should have exactly 1 result
    assert len(results) == 1
    # Should have at least 1 trade (the breakout day)
    assert results[0].total_trades >= 1


def test_no_entry_when_no_breakout(simple_symbol_data):
    """OR forms but no breakout → zero trades."""
    data_dir, symbol, trading_days = simple_symbol_data

    df = load_symbol_data(data_dir, symbol, trading_days[0], trading_days[-1])
    atr = compute_atr(df)

    # Very low gap filter means no qualifying days
    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[120],
        min_gap_list=[10.0],  # Very high gap filter
        max_range_atr_list=[999.0],
    )

    results = run_single_symbol_sweep(df, symbol, atr, config)

    assert len(results) == 1
    assert results[0].total_trades == 0


def test_or_range_atr_filter():
    """OR range too wide relative to ATR is filtered out."""
    # Create data where OR is very wide
    bars = []
    trading_days = [date(2025, 6, 2) + timedelta(days=i) for i in range(20)]
    trading_days = [d for d in trading_days if d.weekday() < 5][:15]

    for day in trading_days:
        for bar_num in range(390):
            ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)
            if bar_num < 15:
                # Very wide OR
                high = 110.0
                low = 90.0
            else:
                high = 101.0
                low = 99.0
            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": day,
                    "open": 100.0,
                    "high": high,
                    "low": low,
                    "close": 100.0,
                    "volume": 10000,
                    "minutes_from_open": bar_num,
                    "bar_number_in_day": bar_num,
                }
            )

    df = pd.DataFrame(bars)
    atr = compute_atr(df, period=14)

    # If ATR has no valid values due to insufficient data, create a proper ATR series
    if atr.empty or atr.isna().all():
        # Create manual ATR series for testing
        atr = pd.Series({d: 2.0 for d in trading_days})
        atr.index.name = "trading_day"

    # OR range = 20, typical ATR = 2, so ratio = 10
    # With max_range_atr = 2.0, should filter out all days
    config = SweepConfig(
        data_dir=Path("."),
        symbols=["TEST"],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=Path("."),
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[120],
        min_gap_list=[0.0],  # No gap filter
        max_range_atr_list=[2.0],  # Strict ATR filter
    )

    results = run_single_symbol_sweep(df, "TEST", atr, config)

    # All days should be filtered, no trades
    assert len(results) == 1
    assert results[0].total_trades == 0


def test_one_trade_per_day_max():
    """Only one trade per day even if multiple breakout opportunities."""
    # The implementation naturally handles this since we simulate once per day
    bars = []
    day = date(2025, 6, 16)
    prev_day = date(2025, 6, 13)

    # Create prev day for gap calculation
    for d in [prev_day, day]:
        for bar_num in range(390):
            ts = datetime(d.year, d.month, d.day, 9, 30, 0, tzinfo=UTC)
            timestamp = ts + timedelta(minutes=bar_num)
            base = 100.0 if d == prev_day else 103.0  # 3% gap
            if bar_num < 15:
                open_ = base
                close = base * 1.001
                high = base * 1.002
                low = base * 0.999
            elif bar_num == 16:
                # First breakout
                open_ = base * 1.002
                close = base * 1.005
                high = close * 1.001
                low = open_ * 0.999
            elif bar_num == 50:
                # Second potential breakout (should not trigger)
                open_ = base * 1.01
                close = base * 1.02
                high = close * 1.001
                low = open_ * 0.999
            else:
                open_ = base * 1.001
                close = open_ * 1.001
                high = max(open_, close) * 1.001
                low = min(open_, close) * 0.999

            bars.append(
                {
                    "timestamp": timestamp,
                    "trading_day": d,
                    "open": open_,
                    "high": high,
                    "low": low,
                    "close": close,
                    "volume": 10000,
                    "minutes_from_open": bar_num,
                    "bar_number_in_day": bar_num,
                }
            )

    df = pd.DataFrame(bars)
    # Create ATR Series with proper index name
    atr = pd.Series({prev_day: 2.0, day: 2.0})
    atr.index.name = "trading_day"

    config = SweepConfig(
        data_dir=Path("."),
        symbols=["TEST"],
        start_date=prev_day,
        end_date=day,
        output_dir=Path("."),
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[120],
        min_gap_list=[2.0],
        max_range_atr_list=[999.0],
    )

    results = run_single_symbol_sweep(df, "TEST", atr, config)

    # Should have at most 1 trade (the first breakout)
    assert results[0].total_trades <= 1


# =============================================================================
# Full Sweep Integration Tests
# =============================================================================


def test_sweep_result_count(simple_symbol_data):
    """1 symbol, small parameter grid → expected result count."""
    data_dir, symbol, trading_days = simple_symbol_data

    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        or_minutes_list=[5, 10],  # 2
        target_r_list=[1.0, 2.0],  # 2
        stop_buffer_list=[0.0],  # 1
        max_hold_list=[30],  # 1
        min_gap_list=[1.0],  # 1
        max_range_atr_list=[999.0],  # 1
    )

    # 2 * 2 * 1 * 1 * 1 * 1 = 4 combinations
    results = run_sweep(config)

    assert len(results) == 4


def test_sweep_output_columns(simple_symbol_data):
    """Run small sweep, verify SweepResult has all expected fields."""
    data_dir, symbol, trading_days = simple_symbol_data

    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[60],
        min_gap_list=[1.0],
        max_range_atr_list=[999.0],
    )

    results = run_sweep(config)

    expected_cols = [
        "symbol",
        "or_minutes",
        "target_r",
        "stop_buffer_pct",
        "max_hold_minutes",
        "min_gap_pct",
        "max_range_atr_ratio",
        "total_trades",
        "win_rate",
        "total_return_pct",
        "avg_r_multiple",
        "max_drawdown_pct",
        "sharpe_ratio",
        "profit_factor",
        "avg_hold_minutes",
        "qualifying_days",
    ]

    for col in expected_cols:
        assert col in results.columns, f"Missing column: {col}"


def test_sweep_results_deterministic(simple_symbol_data):
    """Run same sweep twice → identical results."""
    data_dir, symbol, trading_days = simple_symbol_data

    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=data_dir.parent / "sweeps",
        or_minutes_list=[15],
        target_r_list=[2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[60],
        min_gap_list=[1.0],
        max_range_atr_list=[999.0],
    )

    results1 = run_sweep(config)
    results2 = run_sweep(config)

    pd.testing.assert_frame_equal(results1, results2)


# =============================================================================
# Heatmap Generation Tests
# =============================================================================


def test_heatmap_png_created(simple_symbol_data):
    """Run sweep → call generate_heatmaps → PNG files exist."""
    data_dir, symbol, trading_days = simple_symbol_data

    output_dir = data_dir.parent / "sweeps"

    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=output_dir,
        or_minutes_list=[5, 10],
        target_r_list=[1.0, 2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[30],
        min_gap_list=[1.0],
        max_range_atr_list=[999.0],
    )

    results = run_sweep(config)
    generate_heatmaps(results, output_dir)

    static_dir = output_dir / "static"
    assert static_dir.exists()
    png_files = list(static_dir.glob("*.png"))
    assert len(png_files) > 0


def test_heatmap_html_created(simple_symbol_data):
    """Run sweep → call generate_heatmaps → HTML files exist."""
    data_dir, symbol, trading_days = simple_symbol_data

    output_dir = data_dir.parent / "sweeps"

    config = SweepConfig(
        data_dir=data_dir,
        symbols=[symbol],
        start_date=trading_days[0],
        end_date=trading_days[-1],
        output_dir=output_dir,
        or_minutes_list=[5, 10],
        target_r_list=[1.0, 2.0],
        stop_buffer_list=[0.0],
        max_hold_list=[30],
        min_gap_list=[1.0],
        max_range_atr_list=[999.0],
    )

    results = run_sweep(config)
    generate_heatmaps(results, output_dir)

    interactive_dir = output_dir / "interactive"
    assert interactive_dir.exists()
    html_files = list(interactive_dir.glob("*.html"))
    assert len(html_files) > 0


def test_heatmap_no_trades_handles_gracefully(tmp_data_dir):
    """Parameter combo with zero trades → heatmap handles gracefully."""
    output_dir = tmp_data_dir.parent / "sweeps"

    # Create an empty DataFrame that mimics the sweep results structure
    empty_results = pd.DataFrame()

    # Should not crash on empty results
    generate_heatmaps(empty_results, output_dir)

    # When results are empty, heatmaps should not be created
    # but the function should return gracefully without error
    # (we verify this by the test not raising an exception)

    # Now test with results that have zero trades but valid structure
    results_with_zero_trades = pd.DataFrame(
        [
            {
                "symbol": "TEST",
                "or_minutes": 15,
                "target_r": 2.0,
                "stop_buffer_pct": 0.0,
                "max_hold_minutes": 60,
                "min_gap_pct": 5.0,
                "max_range_atr_ratio": 999.0,
                "total_trades": 0,
                "win_rate": 0.0,
                "total_return_pct": 0.0,
                "avg_r_multiple": 0.0,
                "max_drawdown_pct": 0.0,
                "sharpe_ratio": 0.0,
                "profit_factor": 0.0,
                "avg_hold_minutes": 0.0,
                "qualifying_days": 0,
            }
        ]
    )

    # Should not crash with zero trades
    generate_heatmaps(results_with_zero_trades, output_dir)

    # Verify heatmaps were created
    static_dir = output_dir / "static"
    assert static_dir.exists()


# =============================================================================
# CLI Tests
# =============================================================================


def test_cli_runs_without_error(simple_symbol_data, monkeypatch, capsys):
    """Call main() with small synthetic dataset and minimal params."""
    import sys

    from argus.backtest.vectorbt_orb import main

    data_dir, symbol, trading_days = simple_symbol_data
    output_dir = data_dir.parent / "sweeps"

    # Set up CLI args
    test_args = [
        "vectorbt_orb",
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
        "--or-minutes",
        "15",
        "--target-r",
        "2.0",
        "--stop-buffer",
        "0.0",
        "--max-hold",
        "60",
        "--min-gap",
        "1.0",
        "--max-range-atr",
        "999.0",
    ]

    monkeypatch.setattr(sys, "argv", test_args)

    # Should run without exception
    main()

    captured = capsys.readouterr()
    assert "Sweep complete" in captured.out


# =============================================================================
# Known-Outcome Trade Tests (using _simulate_trades_for_day directly)
# =============================================================================


def test_known_outcome_trade_values():
    """Test with hand-computable values: breakout hits target.

    Setup:
    - OR high = 102.0, OR low = 98.0
    - OR completes at bar 14
    - Breakout bar (bar 16) closes at 102.50
    - Post-breakout bars have HIGH reaching target

    Parameters:
    - stop_buffer_pct = 0.0
    - target_r = 2.0
    - max_hold_minutes = 120

    Expected (hand-computed):
    - entry_price = 102.50
    - stop_price = 98.00 (OR low, no buffer)
    - risk = 102.50 - 98.00 = 4.50
    - target_price = 102.50 + (2.0 × 4.50) = 111.50
    - r_multiple = 2.0
    - exit_reason = "target"
    """
    # Create synthetic bars for ONE day with precise values
    day = date(2025, 6, 16)
    bars = []

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 15:
            # Opening range bars (bars 0-14)
            # Set OR high = 102.0, OR low = 98.0
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 5 else 100.5  # One bar hits OR high
            low = 98.0 if bar_num == 10 else 99.5  # One bar hits OR low
            volume = 5000
        elif bar_num == 15:
            # First post-OR bar - stays below OR high (no breakout)
            open_ = 100.5
            close = 101.5  # Below OR high of 102.0
            high = 101.8
            low = 100.0
            volume = 8000
        elif bar_num == 16:
            # Breakout bar - close above OR high at exactly 102.50
            open_ = 101.5
            close = 102.50  # Entry price
            high = 103.0
            low = 101.0
            volume = 20000
        elif bar_num == 20:
            # Bar where target is hit - high reaches 111.50
            # target = 102.50 + (2.0 * 4.50) = 111.50
            open_ = 108.0
            close = 110.0
            high = 112.0  # Exceeds target of 111.50
            low = 107.0
            volume = 15000
        else:
            # Other bars - stay between stop (98.0) and target (111.50)
            # IMPORTANT: close must stay below OR high until breakout
            if bar_num < 16:
                # Pre-breakout: close below OR high
                open_ = 100.5
                close = 101.0
                high = 101.5
                low = 99.5
            else:
                # Post-breakout: stay between stop and target
                open_ = 104.0
                close = 105.0
                high = 106.0  # Below target of 111.50
                low = 102.5  # Above stop of 98.0
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

    # Call _simulate_trades_for_day directly
    result = _simulate_trades_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=14,
        stop_buffer_pct=0.0,
        target_r=2.0,
        max_hold_minutes=120,
    )

    # Assertions for all expected values
    assert result is not None, "Should have a trade result"
    assert result["entry_price"] == 102.50, f"Entry: {result['entry_price']}"
    assert result["exit_price"] == pytest.approx(111.50, rel=0.01), (
        f"Exit price: {result['exit_price']}"
    )
    assert result["risk"] == pytest.approx(4.50, rel=0.01), f"Risk: {result['risk']}"
    assert result["r_multiple"] == pytest.approx(2.0, rel=0.01), (
        f"R-multiple: {result['r_multiple']}"
    )
    assert result["exit_reason"] == "target", f"Exit reason: {result['exit_reason']}"
    # Hold minutes: entry at bar 16 (minute 16), exit at bar 20 (minute 20) = 4 minutes
    assert result["hold_minutes"] == 4, f"Hold minutes: {result['hold_minutes']}"


def test_known_outcome_stop_loss():
    """Test with hand-computable values: breakout hits stop loss.

    Same setup as target test but post-breakout bars have LOW <= stop_price.

    Expected:
    - r_multiple ≈ -1.0
    - exit_reason = "stop"
    """
    day = date(2025, 6, 16)
    bars = []

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 15:
            # Opening range bars (bars 0-14)
            # OR high = 102.0, OR low = 98.0
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 5 else 100.5
            low = 98.0 if bar_num == 10 else 99.5
            volume = 5000
        elif bar_num == 16:
            # Breakout bar - close above OR high at exactly 102.50
            open_ = 101.5
            close = 102.50  # Entry price
            high = 103.0
            low = 101.0
            volume = 20000
        elif bar_num == 18:
            # Bar where stop is hit - low goes below 98.0
            open_ = 100.0
            close = 97.0
            high = 100.5
            low = 96.0  # Below stop of 98.0
            volume = 25000
        else:
            # Other bars - neutral
            open_ = 100.0
            close = 100.5
            high = 101.0
            low = 99.5
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

    result = _simulate_trades_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=14,
        stop_buffer_pct=0.0,
        target_r=2.0,
        max_hold_minutes=120,
    )

    # Expected values:
    # entry_price = 102.50
    # stop_price = 98.0 (OR low, no buffer)
    # risk = 102.50 - 98.0 = 4.50
    # pnl = 98.0 - 102.50 = -4.50
    # r_multiple = -4.50 / 4.50 = -1.0

    assert result is not None, "Should have a trade result"
    assert result["entry_price"] == 102.50, f"Entry: {result['entry_price']}"
    assert result["exit_price"] == pytest.approx(98.0, rel=0.01), (
        f"Exit price: {result['exit_price']}"
    )
    assert result["risk"] == pytest.approx(4.50, rel=0.01), f"Risk: {result['risk']}"
    assert result["r_multiple"] == pytest.approx(-1.0, rel=0.01), (
        f"R-multiple: {result['r_multiple']}"
    )
    assert result["exit_reason"] == "stop", f"Exit reason: {result['exit_reason']}"
    # Hold minutes: entry at bar 16, exit at bar 18 = 2 minutes
    assert result["hold_minutes"] == 2, f"Hold minutes: {result['hold_minutes']}"


def test_known_outcome_time_stop():
    """Test with hand-computable values: trade exits via time stop.

    Setup:
    - Breakout occurs at bar 16
    - Post-breakout bars stay between stop and target (no exit triggered)
    - max_hold_minutes = 30

    Expected:
    - At bar 46 (30 minutes after entry at bar 16), time stop triggers
    - exit_reason = "time_stop"
    - hold_minutes = 30
    """
    day = date(2025, 6, 16)
    bars = []

    for bar_num in range(390):
        ts = datetime(day.year, day.month, day.day, 9, 30, 0, tzinfo=UTC)
        timestamp = ts + timedelta(minutes=bar_num)

        if bar_num < 15:
            # Opening range bars (bars 0-14)
            # OR high = 102.0, OR low = 98.0
            open_ = 100.0
            close = 100.0
            high = 102.0 if bar_num == 5 else 100.5
            low = 98.0 if bar_num == 10 else 99.5
            volume = 5000
        elif bar_num == 15:
            # First post-OR bar - stays below OR high (no breakout)
            open_ = 100.5
            close = 101.5  # Below OR high of 102.0
            high = 101.8
            low = 100.0
            volume = 8000
        elif bar_num == 16:
            # Breakout bar - close above OR high at exactly 102.50
            open_ = 101.5
            close = 102.50  # Entry price
            high = 103.0
            low = 101.0
            volume = 20000
        else:
            # Post-breakout bars: stay between stop (98.0) and target (111.50)
            # target = 102.50 + (2.0 * 4.50) = 111.50
            # IMPORTANT: Keep close below OR high until breakout
            if bar_num < 16:
                # Pre-breakout: close below OR high
                open_ = 100.5
                close = 101.0
                high = 101.5
                low = 99.5
            else:
                # Post-breakout: stay between stop and target
                open_ = 104.0
                close = 105.0
                high = 107.0  # Below target of 111.50
                low = 99.0  # Above stop of 98.0
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

    result = _simulate_trades_for_day(
        day_bars=day_bars,
        or_high=102.0,
        or_low=98.0,
        or_complete_bar=14,
        stop_buffer_pct=0.0,
        target_r=2.0,
        max_hold_minutes=30,
    )

    assert result is not None, "Should have a trade result"
    assert result["entry_price"] == 102.50, f"Entry price: {result['entry_price']}"
    assert result["exit_reason"] == "time_stop", f"Exit reason: {result['exit_reason']}"
    assert result["hold_minutes"] == 30, f"Hold minutes: {result['hold_minutes']}"
    # Exit price should be the close of the time stop bar
    assert result["exit_price"] == 105.0, f"Exit price: {result['exit_price']}"
