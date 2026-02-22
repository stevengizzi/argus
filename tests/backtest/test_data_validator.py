"""Tests for the historical data validator."""

from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

from argus.backtest.data_validator import (
    get_expected_trading_days,
    validate_parquet_file,
)


class TestGetExpectedTradingDays:
    """Tests for trading day calendar logic."""

    def test_january_2025(self) -> None:
        """January 2025 has correct trading days (excludes New Year's + MLK)."""
        days = get_expected_trading_days(2025, 1)
        assert date(2025, 1, 1) not in days  # New Year's
        assert date(2025, 1, 20) not in days  # MLK Day
        assert date(2025, 1, 2) in days  # First trading day
        assert date(2025, 1, 4) not in days  # Saturday
        assert date(2025, 1, 5) not in days  # Sunday

    def test_november_2025(self) -> None:
        """November 2025 excludes Thanksgiving."""
        days = get_expected_trading_days(2025, 11)
        assert date(2025, 11, 27) not in days  # Thanksgiving

    def test_december_2025(self) -> None:
        """December 2025 excludes Christmas."""
        days = get_expected_trading_days(2025, 12)
        assert date(2025, 12, 25) not in days  # Christmas

    def test_no_future_dates(self) -> None:
        """Expected trading days don't include dates after today."""
        days = get_expected_trading_days(2027, 1)
        for d in days:
            assert d <= date.today()

    def test_june_2025_count(self) -> None:
        """June 2025 has approximately 21 trading days."""
        days = get_expected_trading_days(2025, 6)
        # June 2025: 19th is Juneteenth (holiday), 21-22 weekend, etc.
        # Should be around 20-22 trading days
        assert 20 <= len(days) <= 22


class TestValidateParquetFile:
    """Tests for Parquet file validation."""

    def _make_valid_parquet(self, tmp_path: Path, symbol: str, year: int, month: int) -> Path:
        """Helper to create a valid Parquet file for testing."""
        # Generate bars for every trading day, every minute 9:30-16:00 ET
        days = get_expected_trading_days(year, month)
        rows = []
        for d in days:
            for hour in range(14, 21):  # UTC hours covering 9:30-16:00 ET (EST)
                for minute in range(60):
                    # Rough mapping: 14:30 UTC = 9:30 ET (EST)
                    if hour == 14 and minute < 30:
                        continue
                    if hour >= 21:
                        continue
                    ts = pd.Timestamp(
                        year=d.year,
                        month=d.month,
                        day=d.day,
                        hour=hour,
                        minute=minute,
                        tz="UTC",
                    )
                    price = 150.0 + np.random.uniform(-1, 1)
                    rows.append(
                        {
                            "timestamp": ts,
                            "open": price,
                            "high": price + 0.5,
                            "low": price - 0.5,
                            "close": price + 0.1,
                            "volume": int(np.random.uniform(1000, 50000)),
                        }
                    )
        df = pd.DataFrame(rows)
        file_dir = tmp_path / symbol
        file_dir.mkdir(parents=True, exist_ok=True)
        file_path = file_dir / f"{symbol}_{year}-{month:02d}.parquet"
        df.to_parquet(file_path, index=False)
        return file_path

    def test_valid_file_passes(self, tmp_path: Path) -> None:
        """A well-formed Parquet file passes validation."""
        # Use a past month to avoid future-date filtering
        path = self._make_valid_parquet(tmp_path, "AAPL", 2025, 6)
        result = validate_parquet_file(path, "AAPL", 2025, 6)
        assert result.is_valid
        assert result.row_count > 0

    def test_missing_file(self, tmp_path: Path) -> None:
        """Missing file is flagged."""
        result = validate_parquet_file(tmp_path / "nope.parquet", "AAPL", 2025, 6)
        assert not result.is_valid
        assert any("not found" in i for i in result.issues)

    def test_empty_file(self, tmp_path: Path) -> None:
        """Empty file is flagged."""
        df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])
        path = tmp_path / "EMPTY" / "EMPTY_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "EMPTY", 2025, 6)
        assert not result.is_valid
        assert any("zero rows" in i for i in result.issues)

    def test_ohlc_inconsistency_detected(self, tmp_path: Path) -> None:
        """Bars where high < open are flagged."""
        df = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2025-06-02 14:30:00", tz="UTC"),
                    "open": 150.0,
                    "high": 149.0,  # BAD: high < open
                    "low": 148.0,
                    "close": 149.5,
                    "volume": 1000,
                }
            ]
        )
        path = tmp_path / "BAD" / "BAD_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "BAD", 2025, 6)
        assert any("OHLC inconsistency" in i for i in result.issues)

    def test_zero_volume_market_hours_detected(self, tmp_path: Path) -> None:
        """Zero-volume bars during market hours are flagged."""
        df = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2025-06-02 15:00:00", tz="UTC"),  # 10 AM ET
                    "open": 150.0,
                    "high": 151.0,
                    "low": 149.0,
                    "close": 150.5,
                    "volume": 0,  # BAD: zero volume during market hours
                }
            ]
        )
        path = tmp_path / "ZV" / "ZV_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "ZV", 2025, 6)
        assert any("zero-volume" in i.lower() for i in result.issues)

    def test_duplicate_timestamps_detected(self, tmp_path: Path) -> None:
        """Duplicate timestamps are flagged."""
        ts = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        df = pd.DataFrame(
            [
                {
                    "timestamp": ts,
                    "open": 150.0,
                    "high": 151.0,
                    "low": 149.0,
                    "close": 150.5,
                    "volume": 1000,
                },
                {
                    "timestamp": ts,
                    "open": 150.1,
                    "high": 151.1,
                    "low": 149.1,
                    "close": 150.6,
                    "volume": 2000,
                },
            ]
        )
        path = tmp_path / "DUP" / "DUP_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "DUP", 2025, 6)
        assert any("duplicate" in i.lower() for i in result.issues)

    def test_missing_columns_detected(self, tmp_path: Path) -> None:
        """Missing required columns are flagged."""
        df = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2025-06-02 14:30:00", tz="UTC"),
                    "open": 150.0,
                    "high": 151.0,
                    # Missing: low, close, volume
                }
            ]
        )
        path = tmp_path / "MISS" / "MISS_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "MISS", 2025, 6)
        assert any("Missing columns" in i for i in result.issues)

    def test_timezone_naive_detected(self, tmp_path: Path) -> None:
        """Timezone-naive timestamps are flagged."""
        df = pd.DataFrame(
            [
                {
                    "timestamp": pd.Timestamp("2025-06-02 14:30:00"),  # No tz - naive
                    "open": 150.0,
                    "high": 151.0,
                    "low": 149.0,
                    "close": 150.5,
                    "volume": 1000,
                }
            ]
        )
        path = tmp_path / "NAIVE" / "NAIVE_2025-06.parquet"
        path.parent.mkdir(parents=True)
        df.to_parquet(path, index=False)
        result = validate_parquet_file(path, "NAIVE", 2025, 6)
        assert any("timezone-naive" in i.lower() for i in result.issues)
