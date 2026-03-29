"""Pytest fixtures for backtest tests."""

import logging
from collections.abc import Generator
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest


@pytest.fixture(autouse=True)
def _restore_argus_logger_level() -> Generator[None, None, None]:
    """Restore the argus logger level after each test.

    BacktestEngine._setup() sets logging.getLogger("argus").setLevel(WARNING)
    which persists across tests since loggers are module-level singletons.
    This pollutes subsequent tests that assert on INFO-level log capture.
    """
    argus_logger = logging.getLogger("argus")
    original_level = argus_logger.level
    yield
    argus_logger.setLevel(original_level)


@pytest.fixture
def tmp_parquet_dir(tmp_path: Path) -> Path:
    """Create a temporary directory for Parquet files."""
    return tmp_path / "historical" / "1m"


def generate_test_bars(
    symbol: str,
    trading_date: date,
    start_time: datetime | None = None,
    num_bars: int = 390,  # Full trading day (9:30-16:00)
    base_price: float = 100.0,
    volatility: float = 0.005,
    volume_base: int = 10000,
) -> list[dict]:
    """Generate synthetic bar data for testing.

    Args:
        symbol: Ticker symbol.
        trading_date: The trading date.
        start_time: Start time (default: 9:30 AM ET).
        num_bars: Number of 1-minute bars to generate.
        base_price: Starting price.
        volatility: Price change per bar as percentage.
        volume_base: Base volume per bar.

    Returns:
        List of bar dictionaries with OHLCV data.
    """
    if start_time is None:
        start_time = datetime(
            trading_date.year, trading_date.month, trading_date.day, 9, 30, 0, tzinfo=UTC
        )

    bars = []
    price = base_price

    for i in range(num_bars):
        timestamp = start_time + timedelta(minutes=i)

        # Generate OHLC with some variance
        open_ = price
        change = price * volatility * (1 if i % 2 == 0 else -1)
        close = price + change
        high = max(open_, close) + abs(change) * 0.3
        low = min(open_, close) - abs(change) * 0.3
        volume = volume_base + (i * 100)

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

        price = close

    return bars


def generate_gap_up_bars(
    symbol: str,
    trading_date: date,
    prev_close: float,
    gap_pct: float = 0.05,
    num_bars: int = 30,
) -> list[dict]:
    """Generate bars for a stock that gaps up and breaks out.

    Creates a scenario where:
    - First 15 bars form the opening range
    - Bar 16+ has a breakout above the OR high with volume

    Args:
        symbol: Ticker symbol.
        trading_date: The trading date.
        prev_close: Previous day's closing price.
        gap_pct: Gap percentage from prev_close to open.
        num_bars: Number of bars to generate.

    Returns:
        List of bar dictionaries.
    """
    start_time = datetime(
        trading_date.year, trading_date.month, trading_date.day, 9, 30, 0, tzinfo=UTC
    )

    # Calculate gap open
    open_price = prev_close * (1 + gap_pct)

    bars = []
    or_high = open_price
    or_low = open_price

    for i in range(num_bars):
        timestamp = start_time + timedelta(minutes=i)

        if i < 15:
            # OR formation - oscillate within range
            offset = 0.002 * (1 if i % 2 == 0 else -1)
            open_ = open_price * (1 + offset * i / 10)
            close = open_ * (1 + offset)
            high = max(open_, close) * 1.001
            low = min(open_, close) * 0.999
            volume = 5000 + i * 200

            or_high = max(or_high, high)
            or_low = min(or_low, low)
        elif i == 15:
            # Breakout bar - closes above OR high with volume
            open_ = or_high * 0.998
            close = or_high * 1.005
            high = close * 1.002
            low = open_ * 0.998
            volume = 20000  # High volume breakout
        else:
            # Post-breakout drift
            prev = bars[-1]["close"]
            offset = 0.001 * (1 if i % 3 != 0 else -1)
            open_ = prev
            close = prev * (1 + offset)
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

    return bars


def write_parquet_for_symbol(
    data_dir: Path,
    symbol: str,
    bars: list[dict],
    year_month: str = "2025-06",
) -> Path:
    """Write bar data to a Parquet file in the expected directory structure.

    Creates: data_dir/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet

    Args:
        data_dir: Base directory (e.g., tmp_path/historical/1m).
        symbol: Ticker symbol.
        bars: List of bar dictionaries.
        year_month: Year-month string for filename.

    Returns:
        Path to the created Parquet file.
    """
    symbol_dir = data_dir / symbol.upper()
    symbol_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{symbol.upper()}_{year_month}.parquet"
    filepath = symbol_dir / filename

    df = pd.DataFrame(bars)
    df.to_parquet(filepath, index=False)

    return filepath


@pytest.fixture
def single_day_parquet(tmp_parquet_dir: Path) -> tuple[Path, date]:
    """Create a single day of test data for one symbol.

    Returns:
        Tuple of (data_dir, trading_date).
    """
    trading_date = date(2025, 6, 16)
    bars = generate_test_bars("AAPL", trading_date, num_bars=30)
    write_parquet_for_symbol(tmp_parquet_dir, "AAPL", bars)
    return tmp_parquet_dir, trading_date


@pytest.fixture
def multi_day_parquet(tmp_parquet_dir: Path) -> tuple[Path, list[date]]:
    """Create two trading days of test data.

    Returns:
        Tuple of (data_dir, [day1, day2]).
    """
    day1 = date(2025, 6, 16)
    day2 = date(2025, 6, 17)

    # Day 1 bars
    bars1 = generate_test_bars("AAPL", day1, num_bars=30, base_price=100.0)

    # Day 2 bars - continues from day 1's close
    day1_close = bars1[-1]["close"]
    bars2 = generate_test_bars("AAPL", day2, num_bars=30, base_price=day1_close)

    # Combine and write
    all_bars = bars1 + bars2
    write_parquet_for_symbol(tmp_parquet_dir, "AAPL", all_bars)

    return tmp_parquet_dir, [day1, day2]


@pytest.fixture
def breakout_scenario_parquet(tmp_parquet_dir: Path) -> tuple[Path, date]:
    """Create data that should trigger an ORB breakout.

    Returns:
        Tuple of (data_dir, trading_date).
    """
    day1 = date(2025, 6, 16)
    day2 = date(2025, 6, 17)

    # Day 1 - establish previous close
    bars1 = generate_test_bars("TSLA", day1, num_bars=30, base_price=200.0)
    prev_close = bars1[-1]["close"]

    # Day 2 - gap up and breakout
    bars2 = generate_gap_up_bars("TSLA", day2, prev_close=prev_close, gap_pct=0.05)

    all_bars = bars1 + bars2
    write_parquet_for_symbol(tmp_parquet_dir, "TSLA", all_bars)

    return tmp_parquet_dir, day2


@pytest.fixture
def multi_symbol_parquet(tmp_parquet_dir: Path) -> tuple[Path, date]:
    """Create data for multiple symbols with different gap percentages.

    Returns:
        Tuple of (data_dir, trading_date).
    """
    day1 = date(2025, 6, 16)
    day2 = date(2025, 6, 17)

    symbols = {
        "AAPL": {"base_price": 150.0, "gap_pct": 0.03},  # 3% gap
        "TSLA": {"base_price": 200.0, "gap_pct": 0.05},  # 5% gap
        "MSFT": {"base_price": 300.0, "gap_pct": 0.01},  # 1% gap (below threshold)
    }

    for symbol, params in symbols.items():
        # Day 1
        bars1 = generate_test_bars(symbol, day1, num_bars=30, base_price=params["base_price"])
        prev_close = bars1[-1]["close"]

        # Day 2 with gap
        open_price = prev_close * (1 + params["gap_pct"])
        bars2 = generate_test_bars(symbol, day2, num_bars=30, base_price=open_price)

        all_bars = bars1 + bars2
        write_parquet_for_symbol(tmp_parquet_dir, symbol, all_bars)

    return tmp_parquet_dir, day2
