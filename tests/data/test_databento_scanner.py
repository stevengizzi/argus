"""Tests for DatabentoScanner.

Tests the Databento-based pre-market gap scanner implementation.
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from argus.data.databento_scanner import DatabentoScanner, DatabentoScannerConfig


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
        assert config.dataset == "XNAS.ITCH"

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
