"""Tests for the historical data fetcher.

All Alpaca API calls are mocked. These tests verify:
- Month range generation
- DataFrame conversion from Alpaca bar format
- File saving in correct directory structure
- Manifest tracking and resume behavior
- Rate limit logic
- CLI argument parsing
"""

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from argus.backtest.config import DataFetcherConfig
from argus.backtest.data_fetcher import (
    DataFetcher,
    _bars_to_dataframe,
    _generate_month_ranges,
)
from argus.backtest.manifest import load_manifest


class TestGenerateMonthRanges:
    """Tests for _generate_month_ranges helper."""

    def test_single_month(self) -> None:
        """Single month range generates one entry."""
        ranges = _generate_month_ranges(date(2025, 6, 1), date(2025, 7, 1))
        assert len(ranges) == 1
        year, month, start, end = ranges[0]
        assert (year, month) == (2025, 6)
        assert start == date(2025, 6, 1)
        assert end == date(2025, 6, 30)

    def test_multiple_months(self) -> None:
        """Multi-month range generates correct entries."""
        ranges = _generate_month_ranges(date(2025, 3, 1), date(2025, 6, 1))
        assert len(ranges) == 3  # March, April, May
        assert (ranges[0][0], ranges[0][1]) == (2025, 3)
        assert (ranges[1][0], ranges[1][1]) == (2025, 4)
        assert (ranges[2][0], ranges[2][1]) == (2025, 5)

    def test_cross_year_boundary(self) -> None:
        """Range crossing year boundary works correctly."""
        ranges = _generate_month_ranges(date(2025, 11, 1), date(2026, 2, 1))
        assert len(ranges) == 3  # Nov, Dec, Jan
        assert (ranges[0][0], ranges[0][1]) == (2025, 11)
        assert (ranges[1][0], ranges[1][1]) == (2025, 12)
        assert (ranges[2][0], ranges[2][1]) == (2026, 1)

    def test_full_year(self) -> None:
        """Full year generates 12 entries."""
        ranges = _generate_month_ranges(date(2025, 1, 1), date(2026, 1, 1))
        assert len(ranges) == 12

    def test_empty_range(self) -> None:
        """Same start and end produces empty list."""
        ranges = _generate_month_ranges(date(2025, 6, 1), date(2025, 6, 1))
        assert len(ranges) == 0

    def test_partial_month_end(self) -> None:
        """End date in middle of month is respected."""
        ranges = _generate_month_ranges(date(2025, 6, 1), date(2025, 6, 15))
        assert len(ranges) == 1
        _, _, _, end = ranges[0]
        assert end == date(2025, 6, 15)


class TestBarsToDataFrame:
    """Tests for _bars_to_dataframe conversion."""

    def test_converts_alpaca_bars(self) -> None:
        """Alpaca bar objects are converted to standard DataFrame."""
        mock_bar = MagicMock()
        mock_bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        mock_bar.open = 150.0
        mock_bar.high = 151.0
        mock_bar.low = 149.0
        mock_bar.close = 150.5
        mock_bar.volume = 10000

        # BarSet uses subscript access: bars[symbol]
        bars = MagicMock()
        bars.__contains__ = MagicMock(return_value=True)
        bars.__getitem__ = MagicMock(return_value=[mock_bar])

        df = _bars_to_dataframe(bars, "AAPL")

        assert len(df) == 1
        assert list(df.columns) == [
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
        assert df.iloc[0]["open"] == 150.0
        assert df.iloc[0]["volume"] == 10000

    def test_empty_bars_returns_empty_df(self) -> None:
        """Empty bar response returns empty DataFrame with correct columns."""
        bars = MagicMock()
        bars.__contains__ = MagicMock(return_value=False)

        df = _bars_to_dataframe(bars, "AAPL")
        assert len(df) == 0
        assert "timestamp" in df.columns

    def test_timestamps_are_utc(self) -> None:
        """Output timestamps are always UTC-aware."""
        mock_bar = MagicMock()
        mock_bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        mock_bar.open = 150.0
        mock_bar.high = 151.0
        mock_bar.low = 149.0
        mock_bar.close = 150.5
        mock_bar.volume = 10000

        bars = MagicMock()
        bars.__contains__ = MagicMock(return_value=True)
        bars.__getitem__ = MagicMock(return_value=[mock_bar])

        df = _bars_to_dataframe(bars, "AAPL")
        assert str(df["timestamp"].dt.tz) == "UTC"

    def test_multiple_bars_sorted(self) -> None:
        """Multiple bars are sorted by timestamp."""
        bar1 = MagicMock()
        bar1.timestamp = pd.Timestamp("2025-06-02 14:31:00", tz="UTC")
        bar1.open = bar1.high = bar1.low = bar1.close = 150.0
        bar1.volume = 1000

        bar2 = MagicMock()
        bar2.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        bar2.open = bar2.high = bar2.low = bar2.close = 149.0
        bar2.volume = 2000

        bars = MagicMock()
        bars.__contains__ = MagicMock(return_value=True)
        bars.__getitem__ = MagicMock(return_value=[bar1, bar2])  # Out of order

        df = _bars_to_dataframe(bars, "AAPL")

        assert len(df) == 2
        # Should be sorted: 14:30 before 14:31
        assert df.iloc[0]["close"] == 149.0
        assert df.iloc[1]["close"] == 150.0


class TestDataFetcher:
    """Tests for the DataFetcher class.

    Alpaca client is mocked - no real API calls.
    """

    @pytest.fixture
    def config(self, tmp_path: Path) -> DataFetcherConfig:
        """DataFetcherConfig pointing at tmp_path."""
        return DataFetcherConfig(
            data_dir=tmp_path / "1m",
            manifest_path=tmp_path / "manifest.json",
        )

    @pytest.fixture
    def mock_bar(self) -> MagicMock:
        """Create a mock Alpaca Bar object."""
        bar = MagicMock()
        bar.timestamp = pd.Timestamp("2025-06-02 14:30:00", tz="UTC")
        bar.open = 150.0
        bar.high = 151.0
        bar.low = 149.0
        bar.close = 150.5
        bar.volume = 10000
        return bar

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_saves_parquet(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fetch_symbol_month downloads and saves a Parquet file."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )

        assert entry is not None
        assert entry.symbol == "AAPL"
        assert entry.row_count == 1
        parquet_path = tmp_path / "1m" / "AAPL" / "AAPL_2025-06.parquet"
        assert parquet_path.exists()

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_skips_if_already_in_manifest(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fetch_symbol_month skips download if manifest has the entry."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        # First download
        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        # Second download - should skip
        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        assert entry is None
        # Alpaca should have been called only once
        assert mock_client.get_stock_bars.call_count == 1

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_force_redownloads(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """force=True re-downloads even if in manifest."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )
        await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30), force=True
        )
        assert mock_client.get_stock_bars.call_count == 2

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_manifest_persists_after_fetch_all(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fetch_all saves the manifest to disk."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        await fetcher.fetch_all(["AAPL"], date(2025, 6, 1), date(2025, 7, 1))

        # Load manifest from disk
        loaded = load_manifest(config.manifest_path)
        assert loaded.has_entry("AAPL", 2025, 6)
        assert loaded.total_files() == 1

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_empty_api_response_tracked(
        self, mock_client_cls: MagicMock, config: DataFetcherConfig, tmp_path: Path
    ) -> None:
        """Empty API response is recorded in manifest with quality issue."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        entry = await fetcher.fetch_symbol_month(
            "AAPL", 2025, 6, date(2025, 6, 1), date(2025, 6, 30)
        )

        assert entry is not None
        assert entry.row_count == 0
        assert "No data returned" in entry.data_quality_issues[0]

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_multiple_symbols_fetch_all(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """fetch_all handles multiple symbols."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"AAPL": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        manifest = await fetcher.fetch_all(
            ["AAPL", "TSLA"], date(2025, 6, 1), date(2025, 7, 1)
        )

        # 2 symbols * 1 month = 2 entries
        assert manifest.total_files() == 2
        assert mock_client.get_stock_bars.call_count == 2

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_parquet_file_structure(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        mock_bar: MagicMock,
        tmp_path: Path,
    ) -> None:
        """Parquet files are saved in the correct directory structure."""
        mock_client = mock_client_cls.return_value
        mock_client.get_stock_bars.return_value = {"NVDA": [mock_bar]}

        fetcher = DataFetcher(config)
        fetcher._client = mock_client

        await fetcher.fetch_symbol_month(
            "NVDA", 2025, 3, date(2025, 3, 1), date(2025, 3, 31)
        )

        expected_path = tmp_path / "1m" / "NVDA" / "NVDA_2025-03.parquet"
        assert expected_path.exists()

        # Verify content
        df = pd.read_parquet(expected_path)
        assert len(df) == 1
        assert "timestamp" in df.columns


# ========================================================================
# Databento Backend Tests (Sprint 12 Component 5)
# ========================================================================


class MockDBNStore:
    """Mock Databento DBNStore for testing."""

    def __init__(self, df: pd.DataFrame | None = None) -> None:
        self._df = df

    def to_df(self) -> pd.DataFrame:
        if self._df is not None:
            return self._df
        return pd.DataFrame(
            columns=["ts_event", "open", "high", "low", "close", "volume"]
        )


class MockDatabentoTimeseries:
    """Mock Databento timeseries API."""

    def __init__(self) -> None:
        self._data: pd.DataFrame | None = None

    def get_range(self, **kwargs) -> MockDBNStore:
        return MockDBNStore(self._data)


class MockDatabentoHistorical:
    """Mock Databento Historical client."""

    def __init__(self, key: str = "") -> None:
        self.key = key
        self.timeseries = MockDatabentoTimeseries()


class TestDataFetcherDatabentoInit:
    """Tests for DataFetcher Databento initialization."""

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    def test_constructor_accepts_databento_key(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Constructor accepts databento_key parameter."""
        config = DataFetcherConfig()
        fetcher = DataFetcher(
            config,
            api_key="test-alpaca-key",
            api_secret="test-alpaca-secret",
            databento_key="test-databento-key",
        )
        assert fetcher._databento_key == "test-databento-key"
        assert fetcher._databento_client is None  # Not initialized yet

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    def test_lazy_databento_client_not_created_until_first_use(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Databento client is not created until first use."""
        config = DataFetcherConfig()
        fetcher = DataFetcher(config, databento_key="test-key")

        # Client should not be created yet
        assert fetcher._databento_client is None

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    def test_missing_databento_key_raises_runtime_error(
        self, mock_client_cls: MagicMock
    ) -> None:
        """Missing Databento key raises RuntimeError on first use."""
        import sys

        config = DataFetcherConfig()
        fetcher = DataFetcher(config)

        # Mock databento module and clear environment variable
        with (  # noqa: SIM117
            patch.dict(sys.modules, {"databento": MagicMock()}),
            patch.dict("os.environ", {}, clear=True),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                _ = fetcher._db_client
            assert "Databento API key not available" in str(exc_info.value)


class TestDataFetcherDatabentoBackend:
    """Tests for DataFetcher Databento backend."""

    @pytest.fixture
    def tmp_path(self, tmp_path: Path) -> Path:
        return tmp_path

    @pytest.fixture
    def config(self, tmp_path: Path) -> DataFetcherConfig:
        return DataFetcherConfig(
            data_dir=tmp_path / "1m",
            manifest_path=tmp_path / "manifest.json",
            databento_cache_dir=tmp_path / "databento_cache",
        )

    @pytest.fixture
    def sample_databento_df(self) -> pd.DataFrame:
        """Sample Databento-format DataFrame."""
        return pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-06-15 14:30:00+00:00",
                "2025-06-15 14:31:00+00:00",
                "2025-06-15 14:32:00+00:00",
            ]),
            "rtype": [1, 1, 1],
            "publisher_id": [1, 1, 1],
            "instrument_id": [100, 100, 100],
            "open": [100.0, 101.0, 102.0],
            "high": [101.0, 102.0, 103.0],
            "low": [99.0, 100.0, 101.0],
            "close": [100.5, 101.5, 102.5],
            "volume": [1000, 2000, 3000],
        })

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_databento_cache_hit(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        sample_databento_df: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Cache hit returns cached data without API call."""
        fetcher = DataFetcher(config, databento_key="test-key")

        # Pre-populate cache
        cache_path = config.databento_cache_dir / "AAPL" / "AAPL_2025-06.parquet"
        cache_path.parent.mkdir(parents=True)

        cached_df = pd.DataFrame({
            "timestamp": pd.to_datetime(["2025-06-15 14:30:00+00:00"]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })
        cached_df.to_parquet(cache_path)

        result = await fetcher.fetch_symbol_month_databento("AAPL", 2025, 6)

        assert len(result) == 1
        assert result["close"].iloc[0] == 100.5
        # No Databento client created (cache hit)
        assert fetcher._databento_client is None

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_databento_cache_miss(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        sample_databento_df: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Cache miss fetches from API and caches result."""
        fetcher = DataFetcher(config, databento_key="test-key")

        # Mock Databento client
        mock_db = MockDatabentoHistorical()
        mock_db.timeseries._data = sample_databento_df
        fetcher._databento_client = mock_db

        result = await fetcher.fetch_symbol_month_databento("AAPL", 2025, 6)

        assert len(result) == 3
        assert "timestamp" in result.columns
        assert "open" in result.columns
        # Result saved to cache
        cache_path = config.databento_cache_dir / "AAPL" / "AAPL_2025-06.parquet"
        assert cache_path.exists()

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_databento_empty_response(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        tmp_path: Path,
    ) -> None:
        """Empty API response returns empty DataFrame."""
        fetcher = DataFetcher(config, databento_key="test-key")

        # Mock empty response
        mock_db = MockDatabentoHistorical()
        mock_db.timeseries._data = pd.DataFrame()
        fetcher._databento_client = mock_db

        result = await fetcher.fetch_symbol_month_databento("AAPL", 2025, 6)

        assert result.empty
        assert list(result.columns) == [
            "timestamp", "open", "high", "low", "close", "volume"
        ]

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_fetch_symbol_month_databento_saves_to_cache(
        self,
        mock_client_cls: MagicMock,
        config: DataFetcherConfig,
        sample_databento_df: pd.DataFrame,
        tmp_path: Path,
    ) -> None:
        """Result is saved to Parquet cache."""
        fetcher = DataFetcher(config, databento_key="test-key")

        mock_db = MockDatabentoHistorical()
        mock_db.timeseries._data = sample_databento_df
        fetcher._databento_client = mock_db

        await fetcher.fetch_symbol_month_databento("TSLA", 2025, 3)

        cache_path = config.databento_cache_dir / "TSLA" / "TSLA_2025-03.parquet"
        assert cache_path.exists()

        # Verify content
        df = pd.read_parquet(cache_path)
        assert len(df) == 3
        assert "timestamp" in df.columns


class TestNormalizeDatabentoDF:
    """Tests for _normalize_databento_df static method."""

    def test_correct_column_rename(self) -> None:
        """ts_event is renamed to timestamp."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime(["2025-06-15 14:30:00+00:00"]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })

        result = DataFetcher._normalize_databento_df(df)

        assert "timestamp" in result.columns
        assert "ts_event" not in result.columns

    def test_timestamps_converted_to_utc(self) -> None:
        """Timestamps are converted to UTC."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime(["2025-06-15 14:30:00"]),  # Naive
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })

        result = DataFetcher._normalize_databento_df(df)

        assert result["timestamp"].dt.tz is not None
        assert str(result["timestamp"].dt.tz) == "UTC"

    def test_sorted_by_timestamp(self) -> None:
        """Result is sorted by timestamp."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime([
                "2025-06-15 14:32:00+00:00",
                "2025-06-15 14:30:00+00:00",
                "2025-06-15 14:31:00+00:00",
            ]),
            "open": [102.0, 100.0, 101.0],
            "high": [103.0, 101.0, 102.0],
            "low": [101.0, 99.0, 100.0],
            "close": [102.5, 100.5, 101.5],
            "volume": [3000, 1000, 2000],
        })

        result = DataFetcher._normalize_databento_df(df)

        # First row should be earliest timestamp
        assert result["close"].iloc[0] == 100.5
        # Last row should be latest timestamp
        assert result["close"].iloc[2] == 102.5

    def test_extra_columns_dropped(self) -> None:
        """Extra columns (rtype, publisher_id, etc.) are dropped."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime(["2025-06-15 14:30:00+00:00"]),
            "rtype": [1],
            "publisher_id": [1],
            "instrument_id": [100],
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })

        result = DataFetcher._normalize_databento_df(df)

        expected_columns = ["timestamp", "open", "high", "low", "close", "volume"]
        assert list(result.columns) == expected_columns

    def test_output_schema_matches_alpaca(self) -> None:
        """Output schema matches Alpaca fetch output exactly."""
        df = pd.DataFrame({
            "ts_event": pd.to_datetime(["2025-06-15 14:30:00+00:00"]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })

        result = DataFetcher._normalize_databento_df(df)

        # Same columns as Alpaca output
        assert list(result.columns) == [
            "timestamp", "open", "high", "low", "close", "volume"
        ]
        # Correct dtypes
        assert result["timestamp"].dtype.name == "datetime64[ns, UTC]"
        assert result["open"].dtype == float
        assert result["volume"].dtype in (int, "int64")

    @patch("argus.backtest.data_fetcher.StockHistoricalDataClient")
    @pytest.mark.asyncio
    async def test_parquet_cache_directory_created(
        self, mock_client_cls: MagicMock, tmp_path: Path
    ) -> None:
        """Parquet cache directory is created if missing."""
        config = DataFetcherConfig(
            data_dir=tmp_path / "1m",
            databento_cache_dir=tmp_path / "new_databento_cache",
        )
        fetcher = DataFetcher(config, databento_key="test-key")

        # Mock Databento client
        mock_db = MockDatabentoHistorical()
        mock_db.timeseries._data = pd.DataFrame({
            "ts_event": pd.to_datetime(["2025-06-15 14:30:00+00:00"]),
            "open": [100.0],
            "high": [101.0],
            "low": [99.0],
            "close": [100.5],
            "volume": [1000],
        })
        fetcher._databento_client = mock_db

        await fetcher.fetch_symbol_month_databento("AAPL", 2025, 6)

        # Directory should have been created
        assert (tmp_path / "new_databento_cache" / "AAPL").exists()
