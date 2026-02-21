"""Tests for argus.data.databento_utils."""

import pandas as pd

from argus.data.databento_utils import normalize_databento_df


class TestNormalizeDatabentoDf:
    """Tests for normalize_databento_df function."""

    def test_basic_normalization(self):
        """Test that ts_event is renamed to timestamp and correct columns selected."""
        # Simulate Databento to_df() output with extra columns
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-01-15 14:30:00",
                "2025-01-15 14:31:00",
            ]).tz_localize("UTC"),
            "rtype": [1, 1],
            "publisher_id": [123, 123],
            "instrument_id": [456, 456],
            "open": [150.0, 150.5],
            "high": [151.0, 151.5],
            "low": [149.5, 150.0],
            "close": [150.5, 151.0],
            "volume": [1000, 1500],
        })

        result = normalize_databento_df(df)

        # Check column names
        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]

        # Check values preserved
        assert result["open"].tolist() == [150.0, 150.5]
        assert result["close"].tolist() == [150.5, 151.0]
        assert result["volume"].tolist() == [1000, 1500]

        # Check timestamp is UTC-aware
        assert result["timestamp"].dt.tz is not None
        assert str(result["timestamp"].dt.tz) == "UTC"

    def test_empty_dataframe(self):
        """Test that empty DataFrame returns empty with correct schema."""
        df = pd.DataFrame()

        result = normalize_databento_df(df)

        assert list(result.columns) == ["timestamp", "open", "high", "low", "close", "volume"]
        assert len(result) == 0

    def test_timezone_localization_naive(self):
        """Test that naive timestamps get localized to UTC."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-01-15 14:30:00",
                "2025-01-15 14:31:00",
            ]),  # Naive timestamps (no timezone)
            "open": [150.0, 150.5],
            "high": [151.0, 151.5],
            "low": [149.5, 150.0],
            "close": [150.5, 151.0],
            "volume": [1000, 1500],
        })

        result = normalize_databento_df(df)

        assert result["timestamp"].dt.tz is not None
        assert str(result["timestamp"].dt.tz) == "UTC"

    def test_timezone_conversion_non_utc(self):
        """Test that non-UTC timestamps get converted to UTC."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-01-15 09:30:00",
                "2025-01-15 09:31:00",
            ]).tz_localize("America/New_York"),  # ET timezone
            "open": [150.0, 150.5],
            "high": [151.0, 151.5],
            "low": [149.5, 150.0],
            "close": [150.5, 151.0],
            "volume": [1000, 1500],
        })

        result = normalize_databento_df(df)

        assert str(result["timestamp"].dt.tz) == "UTC"
        # 09:30 ET = 14:30 UTC
        assert result["timestamp"].iloc[0].hour == 14

    def test_sorting_by_timestamp(self):
        """Test that output is sorted by timestamp ascending."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-01-15 14:32:00",  # Out of order
                "2025-01-15 14:30:00",
                "2025-01-15 14:31:00",
            ]).tz_localize("UTC"),
            "open": [150.0, 149.0, 149.5],
            "high": [151.0, 150.0, 150.5],
            "low": [149.5, 148.5, 149.0],
            "close": [150.5, 149.5, 150.0],
            "volume": [1000, 800, 900],
        })

        result = normalize_databento_df(df)

        # Should be sorted by timestamp
        assert result["timestamp"].iloc[0] < result["timestamp"].iloc[1]
        assert result["timestamp"].iloc[1] < result["timestamp"].iloc[2]

        # Open values should be reordered to match sorted timestamps
        assert result["open"].tolist() == [149.0, 149.5, 150.0]

    def test_index_reset(self):
        """Test that index is reset to 0-based integers."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-01-15 14:30:00",
                "2025-01-15 14:31:00",
            ]).tz_localize("UTC"),
            "open": [150.0, 150.5],
            "high": [151.0, 151.5],
            "low": [149.5, 150.0],
            "close": [150.5, 151.0],
            "volume": [1000, 1500],
        }, index=[10, 20])  # Non-standard index

        result = normalize_databento_df(df)

        assert list(result.index) == [0, 1]
