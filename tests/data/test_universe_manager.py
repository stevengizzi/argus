"""Tests for UniverseManager.

Sprint 23, Session 1b: Universe Manager Core
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.data.fmp_reference import FMPReferenceClient, SymbolReferenceData
from argus.data.scanner import Scanner
from argus.data.universe_manager import UniverseManager, UniverseManagerConfig


@pytest.fixture
def mock_reference_client() -> MagicMock:
    """Create a mock FMPReferenceClient."""
    client = MagicMock(spec=FMPReferenceClient)
    client._cache = {}
    return client


@pytest.fixture
def mock_scanner() -> MagicMock:
    """Create a mock Scanner."""
    return MagicMock(spec=Scanner)


@pytest.fixture
def default_config() -> UniverseManagerConfig:
    """Create default UniverseManagerConfig."""
    return UniverseManagerConfig(
        enabled=True,
        min_price=5.0,
        max_price=500.0,
        min_avg_volume=100000,
        exclude_otc=True,
    )


@pytest.fixture
def sample_reference_data() -> dict[str, SymbolReferenceData]:
    """Create sample reference data for testing."""
    return {
        "AAPL": SymbolReferenceData(
            symbol="AAPL",
            sector="Technology",
            industry="Consumer Electronics",
            market_cap=3000000000000,
            prev_close=175.50,
            avg_volume=50000000,
            exchange="NASDAQ",
            is_otc=False,
        ),
        "MSFT": SymbolReferenceData(
            symbol="MSFT",
            sector="Technology",
            industry="Software",
            market_cap=2500000000000,
            prev_close=380.25,
            avg_volume=25000000,
            exchange="NASDAQ",
            is_otc=False,
        ),
        "NVDA": SymbolReferenceData(
            symbol="NVDA",
            sector="Technology",
            industry="Semiconductors",
            market_cap=1500000000000,
            prev_close=450.00,
            avg_volume=40000000,
            exchange="NASDAQ",
            is_otc=False,
        ),
    }


class TestBuildViableUniverseSuccess:
    """Tests for successful viable universe construction."""

    @pytest.mark.asyncio
    async def test_build_viable_universe_success(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """build_viable_universe applies filters and returns viable symbols."""
        # Setup mock to return sample data
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)

        # Build universe with initial symbols
        initial_symbols = ["AAPL", "MSFT", "NVDA"]
        result = await manager.build_viable_universe(initial_symbols=initial_symbols)

        # All 3 symbols should pass filters
        assert len(result) == 3
        assert "AAPL" in result
        assert "MSFT" in result
        assert "NVDA" in result

        # Verify reference client was called
        mock_reference_client.build_reference_cache.assert_called_once_with(
            initial_symbols
        )

    @pytest.mark.asyncio
    async def test_build_viable_universe_filters_applied(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """build_viable_universe correctly applies all filters."""
        # Create reference data with some failing symbols
        reference_data = {
            "GOOD": SymbolReferenceData(
                symbol="GOOD",
                prev_close=50.0,
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "LOWPRICE": SymbolReferenceData(
                symbol="LOWPRICE",
                prev_close=2.0,  # Below min_price
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "HIGHPRICE": SymbolReferenceData(
                symbol="HIGHPRICE",
                prev_close=600.0,  # Above max_price
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "LOWVOL": SymbolReferenceData(
                symbol="LOWVOL",
                prev_close=50.0,
                avg_volume=50000,  # Below min_avg_volume
                exchange="NYSE",
                is_otc=False,
            ),
            "OTC": SymbolReferenceData(
                symbol="OTC",
                prev_close=50.0,
                avg_volume=500000,
                exchange="OTC",
                is_otc=True,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Only GOOD should pass
        assert result == {"GOOD"}


class TestSystemFilterExcludeOtc:
    """Tests for OTC exclusion filter."""

    @pytest.mark.asyncio
    async def test_system_filter_exclude_otc(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """OTC symbols excluded when exclude_otc=True."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                prev_close=175.0,
                avg_volume=50000000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "PINK1": SymbolReferenceData(
                symbol="PINK1",
                prev_close=10.0,
                avg_volume=1000000,
                exchange="PINK",
                is_otc=True,
            ),
            "OTC1": SymbolReferenceData(
                symbol="OTC1",
                prev_close=15.0,
                avg_volume=2000000,
                exchange="OTC",
                is_otc=True,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Only AAPL should be included
        assert result == {"AAPL"}
        assert "PINK1" not in result
        assert "OTC1" not in result

    @pytest.mark.asyncio
    async def test_system_filter_include_otc_when_disabled(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """OTC symbols included when exclude_otc=False."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                prev_close=175.0,
                avg_volume=50000000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "PINK1": SymbolReferenceData(
                symbol="PINK1",
                prev_close=10.0,
                avg_volume=1000000,
                exchange="PINK",
                is_otc=True,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=False,  # Allow OTC
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Both should be included
        assert "AAPL" in result
        assert "PINK1" in result


class TestSystemFilterPriceRange:
    """Tests for price range filter."""

    @pytest.mark.asyncio
    async def test_system_filter_price_range(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbols outside price range are excluded."""
        reference_data = {
            "INRANGE": SymbolReferenceData(
                symbol="INRANGE",
                prev_close=50.0,
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "TOOCHEAP": SymbolReferenceData(
                symbol="TOOCHEAP",
                prev_close=3.0,  # Below min_price of 10
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "TOOEXPENSIVE": SymbolReferenceData(
                symbol="TOOEXPENSIVE",
                prev_close=150.0,  # Above max_price of 100
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=10.0,
            max_price=100.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Only INRANGE should pass
        assert result == {"INRANGE"}

    @pytest.mark.asyncio
    async def test_system_filter_price_boundary(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbols at exact price boundaries pass."""
        reference_data = {
            "ATMIN": SymbolReferenceData(
                symbol="ATMIN",
                prev_close=5.0,  # Exactly at min_price
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "ATMAX": SymbolReferenceData(
                symbol="ATMAX",
                prev_close=500.0,  # Exactly at max_price
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Both should pass (at boundaries)
        assert "ATMIN" in result
        assert "ATMAX" in result


class TestSystemFilterMinVolume:
    """Tests for minimum volume filter."""

    @pytest.mark.asyncio
    async def test_system_filter_min_volume(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Low-volume symbols are excluded."""
        reference_data = {
            "HIGHVOL": SymbolReferenceData(
                symbol="HIGHVOL",
                prev_close=50.0,
                avg_volume=5000000,  # Above min_avg_volume
                exchange="NYSE",
                is_otc=False,
            ),
            "LOWVOL": SymbolReferenceData(
                symbol="LOWVOL",
                prev_close=50.0,
                avg_volume=50000,  # Below min_avg_volume of 100000
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Only HIGHVOL should pass
        assert result == {"HIGHVOL"}

    @pytest.mark.asyncio
    async def test_system_filter_volume_boundary(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol at exact volume boundary passes."""
        reference_data = {
            "ATMIN": SymbolReferenceData(
                symbol="ATMIN",
                prev_close=50.0,
                avg_volume=100000,  # Exactly at min_avg_volume
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Should pass (at boundary)
        assert result == {"ATMIN"}


class TestBuildViableUniverseFmpFailure:
    """Tests for fallback behavior when FMP fails."""

    @pytest.mark.asyncio
    async def test_build_viable_universe_fmp_failure(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
    ) -> None:
        """Fallback to scanner symbols when FMP reference client fails."""
        # Setup mock to raise exception
        mock_reference_client.build_reference_cache = AsyncMock(
            side_effect=Exception("FMP API error")
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)

        # build_viable_universe returns empty set on error
        result = await manager.build_viable_universe(
            initial_symbols=["AAPL", "MSFT"]
        )
        assert result == set()

        # Now test fallback method
        mock_reference_client.build_reference_cache = AsyncMock(return_value={})
        scanner_symbols = ["TSLA", "NVDA", "AMD"]

        result = await manager.build_viable_universe_fallback(scanner_symbols)

        # Fallback uses scanner symbols directly
        assert result == {"TSLA", "NVDA", "AMD"}
        assert manager.is_built

    @pytest.mark.asyncio
    async def test_fallback_with_partial_reference_data(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
    ) -> None:
        """Fallback fetches partial reference data successfully."""
        # Simulate partial success - only some symbols have data
        partial_data = {
            "TSLA": SymbolReferenceData(
                symbol="TSLA",
                prev_close=200.0,
                avg_volume=10000000,
                exchange="NASDAQ",
                is_otc=False,
            ),
        }
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=partial_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)
        scanner_symbols = ["TSLA", "NVDA", "AMD"]

        result = await manager.build_viable_universe_fallback(scanner_symbols)

        # All scanner symbols should be in viable universe
        assert result == {"TSLA", "NVDA", "AMD"}

        # But only TSLA has reference data
        assert manager.get_reference_data("TSLA") is not None
        assert manager.get_reference_data("NVDA") is None
        assert manager.get_reference_data("AMD") is None


class TestViableUniverseProperties:
    """Tests for UniverseManager properties."""

    @pytest.mark.asyncio
    async def test_viable_universe_properties(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """Verify count, is_built, last_build_time properties."""
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)

        # Before build
        assert manager.viable_count == 0
        assert manager.is_built is False
        assert manager.last_build_time is None

        # Build universe
        await manager.build_viable_universe(
            initial_symbols=list(sample_reference_data.keys())
        )

        # After build
        assert manager.viable_count == 3
        assert manager.is_built is True
        assert manager.last_build_time is not None
        assert isinstance(manager.last_build_time, datetime)

    @pytest.mark.asyncio
    async def test_viable_symbols_returns_copy(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """viable_symbols returns a copy, not the internal set."""
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)
        await manager.build_viable_universe(
            initial_symbols=list(sample_reference_data.keys())
        )

        # Modify the returned set
        symbols = manager.viable_symbols
        symbols.add("FAKE")

        # Internal set should be unchanged
        assert "FAKE" not in manager.viable_symbols

    @pytest.mark.asyncio
    async def test_reference_cache_returns_copy(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """reference_cache returns a copy, not the internal dict."""
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)
        await manager.build_viable_universe(
            initial_symbols=list(sample_reference_data.keys())
        )

        # Modify the returned dict
        cache = manager.reference_cache
        cache["FAKE"] = SymbolReferenceData(symbol="FAKE")

        # Internal cache should be unchanged
        assert "FAKE" not in manager.reference_cache


class TestGetReferenceData:
    """Tests for get_reference_data method."""

    @pytest.mark.asyncio
    async def test_get_reference_data(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """Lookup cached reference data for viable symbol."""
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)
        await manager.build_viable_universe(
            initial_symbols=list(sample_reference_data.keys())
        )

        # Lookup existing symbol
        data = manager.get_reference_data("AAPL")
        assert data is not None
        assert data.symbol == "AAPL"
        assert data.sector == "Technology"
        assert data.prev_close == 175.50

    @pytest.mark.asyncio
    async def test_get_reference_data_not_found(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        sample_reference_data: dict[str, SymbolReferenceData],
    ) -> None:
        """get_reference_data returns None for unknown symbol."""
        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=sample_reference_data
        )

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)
        await manager.build_viable_universe(
            initial_symbols=list(sample_reference_data.keys())
        )

        # Lookup non-existent symbol
        data = manager.get_reference_data("FAKE")
        assert data is None


class TestEmptyUniverse:
    """Tests for empty universe scenarios."""

    @pytest.mark.asyncio
    async def test_empty_universe(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """All symbols filtered out results in empty set with warning."""
        # All symbols fail filters
        reference_data = {
            "PENNY": SymbolReferenceData(
                symbol="PENNY",
                prev_close=1.0,  # Below min_price
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
            "ILLIQUID": SymbolReferenceData(
                symbol="ILLIQUID",
                prev_close=50.0,
                avg_volume=1000,  # Below min_avg_volume
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)

        with caplog.at_level(logging.WARNING):
            result = await manager.build_viable_universe(
                initial_symbols=list(reference_data.keys())
            )

        # Result should be empty set
        assert result == set()
        assert manager.viable_count == 0

        # Warning should be logged
        assert any("filtered out" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_empty_reference_data(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Empty reference data returns empty set."""
        mock_reference_client.build_reference_cache = AsyncMock(return_value={})

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)

        with caplog.at_level(logging.WARNING):
            result = await manager.build_viable_universe(
                initial_symbols=["AAPL", "MSFT"]
            )

        assert result == set()
        assert manager.is_built  # Still marks as built

    @pytest.mark.asyncio
    async def test_no_initial_symbols_empty_cache(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
        default_config: UniverseManagerConfig,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """No initial symbols and empty cache returns empty set."""
        mock_reference_client._cache = {}

        manager = UniverseManager(mock_reference_client, default_config, mock_scanner)

        with caplog.at_level(logging.WARNING):
            result = await manager.build_viable_universe()

        assert result == set()


class TestUniverseManagerConfig:
    """Tests for UniverseManagerConfig dataclass."""

    def test_config_defaults(self) -> None:
        """UniverseManagerConfig has sensible defaults."""
        config = UniverseManagerConfig()

        assert config.enabled is False
        assert config.min_price == 5.0
        assert config.max_price == 10000.0
        assert config.min_avg_volume == 100000
        assert config.exclude_otc is True
        assert config.reference_cache_ttl_hours == 24
        assert config.fmp_batch_size == 50

    def test_config_custom_values(self) -> None:
        """UniverseManagerConfig accepts custom values."""
        config = UniverseManagerConfig(
            enabled=True,
            min_price=10.0,
            max_price=200.0,
            min_avg_volume=500000,
            exclude_otc=False,
            reference_cache_ttl_hours=12,
            fmp_batch_size=100,
        )

        assert config.enabled is True
        assert config.min_price == 10.0
        assert config.max_price == 200.0
        assert config.min_avg_volume == 500000
        assert config.exclude_otc is False
        assert config.reference_cache_ttl_hours == 12
        assert config.fmp_batch_size == 100


class TestNullDataHandling:
    """Tests for handling None values in reference data."""

    @pytest.mark.asyncio
    async def test_null_price_passes_filter(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol with None prev_close passes price filter (data unavailable)."""
        reference_data = {
            "NULLPRICE": SymbolReferenceData(
                symbol="NULLPRICE",
                prev_close=None,  # No price data
                avg_volume=500000,
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Should pass - we don't filter out symbols with missing price data
        assert "NULLPRICE" in result

    @pytest.mark.asyncio
    async def test_null_volume_passes_filter(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol with None avg_volume passes volume filter (data unavailable)."""
        reference_data = {
            "NULLVOL": SymbolReferenceData(
                symbol="NULLVOL",
                prev_close=50.0,
                avg_volume=None,  # No volume data
                exchange="NYSE",
                is_otc=False,
            ),
        }

        mock_reference_client.build_reference_cache = AsyncMock(
            return_value=reference_data
        )

        config = UniverseManagerConfig(
            min_price=5.0,
            max_price=500.0,
            min_avg_volume=100000,
            exclude_otc=True,
        )

        manager = UniverseManager(mock_reference_client, config, mock_scanner)
        result = await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        # Should pass - we don't filter out symbols with missing volume data
        assert "NULLVOL" in result
