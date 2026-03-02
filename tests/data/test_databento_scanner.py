"""Tests for DatabentoScanner.

Tests the Databento-based pre-market gap scanner implementation.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from argus.data.databento_scanner import (
    DatabentoScanner,
    DatabentoScannerConfig,
    _AVAILABLE_END_PATTERN,
)


class TestDatabentoScannerConfig:
    """Tests for DatabentoScannerConfig."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = DatabentoScannerConfig()

        assert config.universe_symbols == []
        assert config.min_gap_pct == 0.02
        assert config.min_price == 10.0
        assert config.max_price == 500.0
        assert config.min_volume == 1_000_000
        assert config.max_symbols_returned == 10
        assert config.dataset == "EQUS.MINI"  # DEC-237: Standard plan default

    def test_custom_config(self) -> None:
        """Test custom configuration values."""
        config = DatabentoScannerConfig(
            universe_symbols=["AAPL", "MSFT"],
            min_gap_pct=0.05,
            min_price=20.0,
            max_price=300.0,
            min_volume=500_000,
            max_symbols_returned=5,
            dataset="DBEQ.BASIC",
        )

        assert config.universe_symbols == ["AAPL", "MSFT"]
        assert config.min_gap_pct == 0.05
        assert config.min_price == 20.0
        assert config.max_price == 300.0
        assert config.min_volume == 500_000
        assert config.max_symbols_returned == 5
        assert config.dataset == "DBEQ.BASIC"


class TestDatabentoScannerInit:
    """Tests for DatabentoScanner initialization."""

    def test_init_with_config(self) -> None:
        """Test scanner initializes with config."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL", "NVDA"])
        scanner = DatabentoScanner(config)

        assert scanner._config is config
        assert scanner._databento_config is None
        assert scanner._hist_client is None

    def test_init_with_databento_config(self) -> None:
        """Test scanner initializes with databento config."""
        config = DatabentoScannerConfig()
        mock_db_config = MagicMock()
        mock_db_config.api_key_env_var = "TEST_API_KEY"

        scanner = DatabentoScanner(config, databento_config=mock_db_config)

        assert scanner._databento_config is mock_db_config


class TestDatabentoScannerClientLazyInit:
    """Tests for lazy client initialization."""

    def test_client_initialized_on_first_access(self) -> None:
        """Test Historical client is lazily initialized."""
        config = DatabentoScannerConfig()
        scanner = DatabentoScanner(config)

        # Mock databento module and environment
        mock_historical = MagicMock()
        mock_db = MagicMock()
        mock_db.Historical.return_value = mock_historical

        with (
            patch.dict("os.environ", {"DATABENTO_API_KEY": "test_key"}),
            patch.dict("sys.modules", {"databento": mock_db}),
        ):
            client = scanner._client

        assert client is mock_historical
        mock_db.Historical.assert_called_once_with(key="test_key")

    def test_client_raises_without_api_key(self) -> None:
        """Test RuntimeError raised when API key not available."""
        config = DatabentoScannerConfig()
        scanner = DatabentoScanner(config)

        # Mock empty environment and databento module
        mock_db = MagicMock()
        with (  # noqa: SIM117
            patch.dict("os.environ", {}, clear=True),
            patch.dict(sys.modules, {"databento": mock_db}),
        ):
            with pytest.raises(RuntimeError, match="API key not available"):
                _ = scanner._client

    def test_client_uses_config_env_var(self) -> None:
        """Test client uses env var from databento config."""
        config = DatabentoScannerConfig()
        mock_db_config = MagicMock()
        mock_db_config.api_key_env_var = "CUSTOM_DB_KEY"

        scanner = DatabentoScanner(config, databento_config=mock_db_config)

        mock_historical = MagicMock()
        mock_db = MagicMock()
        mock_db.Historical.return_value = mock_historical

        with (
            patch.dict("os.environ", {"CUSTOM_DB_KEY": "custom_test_key"}),
            patch.dict("sys.modules", {"databento": mock_db}),
        ):
            client = scanner._client

        assert client is mock_historical
        mock_db.Historical.assert_called_once_with(key="custom_test_key")


class TestDatabentoScannerScan:
    """Tests for the scan method."""

    @pytest.mark.asyncio
    async def test_scan_returns_empty_for_no_universe(self) -> None:
        """Test scan returns empty list when no universe symbols configured."""
        config = DatabentoScannerConfig(universe_symbols=[])
        scanner = DatabentoScanner(config)

        result = await scanner.scan([])

        assert result == []

    @pytest.mark.asyncio
    async def test_scan_returns_candidates_from_universe(self) -> None:
        """Test scan returns candidates based on universe symbols."""
        config = DatabentoScannerConfig(
            universe_symbols=["AAPL", "MSFT", "NVDA"],
            max_symbols_returned=2,
        )
        scanner = DatabentoScanner(config)

        result = await scanner.scan([])

        assert len(result) == 2  # Limited by max_symbols_returned
        assert result[0].symbol == "AAPL"
        assert result[1].symbol == "MSFT"

    @pytest.mark.asyncio
    async def test_scan_creates_watchlist_items(self) -> None:
        """Test scan creates proper WatchlistItem objects."""
        config = DatabentoScannerConfig(universe_symbols=["TSLA"])
        scanner = DatabentoScanner(config)

        result = await scanner.scan([])

        assert len(result) == 1
        item = result[0]
        assert item.symbol == "TSLA"
        assert item.gap_pct == 0.0  # V1 placeholder
        assert item.premarket_volume == 0  # V1 placeholder


class TestDatabentoScannerLifecycle:
    """Tests for scanner start/stop lifecycle."""

    @pytest.mark.asyncio
    async def test_start_logs_info(self) -> None:
        """Test start logs scanner info."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL", "MSFT"])
        scanner = DatabentoScanner(config)

        # Should not raise
        await scanner.start()

    @pytest.mark.asyncio
    async def test_stop_clears_client(self) -> None:
        """Test stop clears the client reference."""
        config = DatabentoScannerConfig()
        scanner = DatabentoScanner(config)

        # Set a mock client
        scanner._hist_client = MagicMock()

        await scanner.stop()

        assert scanner._hist_client is None


class TestDatabentoScannerScanWithGapData:
    """Tests for the scan_with_gap_data method (full implementation)."""

    @pytest.mark.asyncio
    async def test_returns_empty_for_no_symbols(self) -> None:
        """Test returns empty when no symbols provided."""
        config = DatabentoScannerConfig(universe_symbols=[])
        scanner = DatabentoScanner(config)

        result = await scanner.scan_with_gap_data([])

        assert result == []

    @pytest.mark.asyncio
    async def test_uses_config_symbols_when_none_provided(self) -> None:
        """Test uses config symbols when none provided to method."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        # Mock the client and response
        mock_df = MagicMock()
        mock_df.empty = True  # No data returned

        mock_data = MagicMock()
        mock_data.to_df.return_value = mock_df

        mock_client = MagicMock()
        mock_client.timeseries.get_range.return_value = mock_data

        scanner._hist_client = mock_client

        result = await scanner.scan_with_gap_data()

        assert result == []
        mock_client.timeseries.get_range.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_api_error(self) -> None:
        """Test handles API error gracefully."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        mock_client = MagicMock()
        mock_client.timeseries.get_range.side_effect = Exception("API Error")

        scanner._hist_client = mock_client

        result = await scanner.scan_with_gap_data()

        assert result == []


class TestAvailableEndDatePattern:
    """Tests for the _AVAILABLE_END_PATTERN regex."""

    def test_extracts_date_from_standard_error_message(self) -> None:
        """Test pattern extracts date from standard Databento 422 error."""
        error_msg = (
            "The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'. "
            "The `end` in the query ('2026-03-03 00:00:00+00:00') is after the available range."
        )
        match = _AVAILABLE_END_PATTERN.search(error_msg)

        assert match is not None
        assert match.group(1) == "2026-02-28"

    def test_extracts_date_from_different_dataset(self) -> None:
        """Test pattern works with different dataset names."""
        error_msg = "The dataset XNAS.ITCH has data available up to '2026-01-15 00:00:00+00:00'."
        match = _AVAILABLE_END_PATTERN.search(error_msg)

        assert match is not None
        assert match.group(1) == "2026-01-15"

    def test_no_match_for_unrelated_message(self) -> None:
        """Test pattern doesn't match unrelated error messages."""
        error_msg = "Authentication failed: Invalid API key"
        match = _AVAILABLE_END_PATTERN.search(error_msg)

        assert match is None


class TestExtractAvailableEndDate:
    """Tests for _extract_available_end_date method."""

    def test_extracts_datetime_from_error_message(self) -> None:
        """Test extracts datetime object from error message."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        error_msg = (
            "The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'."
        )
        result = scanner._extract_available_end_date(error_msg)

        assert result is not None
        assert result.year == 2026
        assert result.month == 2
        assert result.day == 28
        assert result.tzinfo == UTC

    def test_returns_none_for_unparseable_message(self) -> None:
        """Test returns None when date cannot be extracted."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        error_msg = "Some other error without a date"
        result = scanner._extract_available_end_date(error_msg)

        assert result is None


class TestFetchDailyBarsWithLagHandling:
    """Tests for _fetch_daily_bars_with_lag_handling method."""

    @pytest.mark.asyncio
    async def test_returns_dataframe_on_success(self) -> None:
        """Test returns DataFrame when API call succeeds."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        mock_df = pd.DataFrame({
            "ts_event": [1],
            "symbol": ["AAPL"],
            "open": [150.0],
            "close": [152.0],
        })
        mock_data = MagicMock()
        mock_data.to_df.return_value = mock_df

        mock_client = MagicMock()
        mock_client.timeseries.get_range.return_value = mock_data
        scanner._hist_client = mock_client

        ref_date = datetime(2026, 2, 28, tzinfo=UTC)
        result = await scanner._fetch_daily_bars_with_lag_handling(["AAPL"], ref_date)

        assert result is not None
        assert len(result) == 1
        assert result["symbol"].iloc[0] == "AAPL"

    @pytest.mark.asyncio
    async def test_handles_422_with_retry(self) -> None:
        """Test handles 422 error by retrying with available date."""
        import databento as db

        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        # Create real BentoHttpError with 422 status
        error_msg = (
            "The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'. "
            "data_end_after_available_end"
        )
        http_error = db.BentoHttpError(
            http_status=422,
            message=error_msg,
        )

        # Create mock successful response for retry
        mock_df = pd.DataFrame({
            "ts_event": [1, 2],
            "symbol": ["AAPL", "AAPL"],
            "open": [150.0, 151.0],
            "close": [152.0, 153.0],
        })
        mock_data = MagicMock()
        mock_data.to_df.return_value = mock_df

        mock_client = MagicMock()
        # First call raises 422, second call succeeds
        mock_client.timeseries.get_range.side_effect = [http_error, mock_data]
        scanner._hist_client = mock_client

        ref_date = datetime(2026, 3, 3, tzinfo=UTC)
        result = await scanner._fetch_daily_bars_with_lag_handling(["AAPL"], ref_date)

        # Should have made 2 calls - original and retry
        assert mock_client.timeseries.get_range.call_count == 2
        assert result is not None
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_returns_none_for_non_422_http_error(self) -> None:
        """Test returns None for non-422 HTTP errors."""
        import databento as db

        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        # Create real BentoHttpError with 500 status
        http_error = db.BentoHttpError(
            http_status=500,
            message="Internal Server Error",
        )

        mock_client = MagicMock()
        mock_client.timeseries.get_range.side_effect = http_error
        scanner._hist_client = mock_client

        ref_date = datetime(2026, 3, 3, tzinfo=UTC)
        result = await scanner._fetch_daily_bars_with_lag_handling(["AAPL"], ref_date)

        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_general_exception(self) -> None:
        """Test returns None for general exceptions."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        mock_client = MagicMock()
        mock_client.timeseries.get_range.side_effect = Exception("Network error")
        scanner._hist_client = mock_client

        ref_date = datetime(2026, 3, 3, tzinfo=UTC)
        result = await scanner._fetch_daily_bars_with_lag_handling(["AAPL"], ref_date)

        assert result is None


class TestFetchDailyBarsRetry:
    """Tests for _fetch_daily_bars_retry method."""

    @pytest.mark.asyncio
    async def test_retry_succeeds(self) -> None:
        """Test retry returns DataFrame on success."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        mock_df = pd.DataFrame({
            "ts_event": [1],
            "symbol": ["AAPL"],
            "open": [150.0],
            "close": [152.0],
        })
        mock_data = MagicMock()
        mock_data.to_df.return_value = mock_df

        mock_client = MagicMock()
        mock_client.timeseries.get_range.return_value = mock_data
        scanner._hist_client = mock_client

        start_date = datetime(2026, 2, 21, tzinfo=UTC)
        end_date = datetime(2026, 2, 28, tzinfo=UTC)

        result = await scanner._fetch_daily_bars_retry(["AAPL"], start_date, end_date)

        assert result is not None
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_retry_returns_none_on_failure(self) -> None:
        """Test retry returns None when API call fails."""
        config = DatabentoScannerConfig(universe_symbols=["AAPL"])
        scanner = DatabentoScanner(config)

        mock_client = MagicMock()
        mock_client.timeseries.get_range.side_effect = Exception("Still failing")
        scanner._hist_client = mock_client

        start_date = datetime(2026, 2, 21, tzinfo=UTC)
        end_date = datetime(2026, 2, 28, tzinfo=UTC)

        result = await scanner._fetch_daily_bars_retry(["AAPL"], start_date, end_date)

        assert result is None


class TestScanFallbackBehavior:
    """Tests for scan() fallback to static list."""

    @pytest.mark.asyncio
    async def test_scan_falls_back_on_gap_data_failure(self) -> None:
        """Test scan falls back to static list when gap data fetch fails."""
        config = DatabentoScannerConfig(
            universe_symbols=["AAPL", "MSFT", "NVDA"],
            max_symbols_returned=2,
        )
        scanner = DatabentoScanner(config)

        # Make scan_with_gap_data return empty (simulating failure)
        mock_client = MagicMock()
        mock_client.timeseries.get_range.side_effect = Exception("API Error")
        scanner._hist_client = mock_client

        result = await scanner.scan([])

        # Should fall back to static list
        assert len(result) == 2
        assert result[0].symbol == "AAPL"
        assert result[1].symbol == "MSFT"
        # Fallback items have gap_pct=0.0
        assert result[0].gap_pct == 0.0

    @pytest.mark.asyncio
    async def test_scan_uses_gap_data_when_available(self) -> None:
        """Test scan uses gap data when available."""
        config = DatabentoScannerConfig(
            universe_symbols=["AAPL", "MSFT"],
            min_gap_pct=0.01,  # 1%
            min_price=10.0,
            max_price=1000.0,
            min_volume=100,  # Low threshold for test
            max_symbols_returned=10,
        )
        scanner = DatabentoScanner(config)

        # Create mock DataFrame with gap data
        # AAPL: prev_close=150, today_open=153 → 2% gap
        # MSFT: prev_close=300, today_open=303 → 1% gap
        mock_df = pd.DataFrame({
            "ts_event": [1, 2, 3, 4],  # 2 days × 2 symbols
            "symbol": ["AAPL", "AAPL", "MSFT", "MSFT"],
            "open": [148.0, 153.0, 298.0, 303.0],  # prev day, today
            "close": [150.0, 155.0, 300.0, 305.0],
            "volume": [1000, 1100, 2000, 2100],
        })
        mock_data = MagicMock()
        mock_data.to_df.return_value = mock_df

        mock_client = MagicMock()
        mock_client.timeseries.get_range.return_value = mock_data
        scanner._hist_client = mock_client

        result = await scanner.scan([])

        # Should have found both stocks with gaps
        assert len(result) == 2
        # AAPL has larger gap (2% vs 1%), should be first
        assert result[0].symbol == "AAPL"
        assert result[0].gap_pct == pytest.approx(0.02, rel=0.01)  # ~2%
        assert result[1].symbol == "MSFT"
        assert result[1].gap_pct == pytest.approx(0.01, rel=0.01)  # ~1%
