"""Tests for UniverseManager.

Sprint 23, Session 1b: Universe Manager Core
Sprint 23, Session 3a: Routing Table Construction
"""

from __future__ import annotations

import logging
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.config import StrategyConfig, UniverseFilterConfig
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


# =============================================================================
# Sprint 23, Session 3a: Routing Table Tests
# =============================================================================


class TestRouteCandleSingleStrategyMatch:
    """Tests for route_candle with single strategy matching."""

    @pytest.mark.asyncio
    async def test_route_candle_single_strategy_match(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol matches exactly one strategy based on filter."""
        reference_data = {
            "TECH": SymbolReferenceData(
                symbol="TECH",
                sector="Technology",
                prev_close=100.0,
                market_cap=10_000_000_000,
                avg_volume=5_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["TECH"])

        # Create strategies with different filters
        strategy_configs = {
            "tech_strategy": StrategyConfig(
                strategy_id="tech_strategy",
                name="Tech Strategy",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
            "healthcare_strategy": StrategyConfig(
                strategy_id="healthcare_strategy",
                name="Healthcare Strategy",
                universe_filter=UniverseFilterConfig(
                    sectors=["Healthcare"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # TECH should only match tech_strategy
        routed = manager.route_candle("TECH")
        assert routed == {"tech_strategy"}


class TestRouteCandleMultiStrategyMatch:
    """Tests for route_candle with multiple strategy matching."""

    @pytest.mark.asyncio
    async def test_route_candle_multi_strategy_match(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol matches multiple strategies with overlapping filters."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                prev_close=175.0,
                market_cap=3_000_000_000_000,
                avg_volume=50_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["AAPL"])

        # Both strategies have filters that AAPL matches
        strategy_configs = {
            "large_cap": StrategyConfig(
                strategy_id="large_cap",
                name="Large Cap Strategy",
                universe_filter=UniverseFilterConfig(
                    min_market_cap=1_000_000_000_000,  # > 1T
                ),
            ),
            "tech_focus": StrategyConfig(
                strategy_id="tech_focus",
                name="Tech Focus Strategy",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # AAPL should match both strategies
        routed = manager.route_candle("AAPL")
        assert routed == {"large_cap", "tech_focus"}


class TestRouteCandleNoMatch:
    """Tests for route_candle with no matches."""

    @pytest.mark.asyncio
    async def test_route_candle_no_match(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol matches no strategies → empty set."""
        reference_data = {
            "SMALLCAP": SymbolReferenceData(
                symbol="SMALLCAP",
                sector="Industrials",
                prev_close=25.0,
                market_cap=500_000_000,  # 500M (small cap)
                avg_volume=1_000_000,
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
        await manager.build_viable_universe(initial_symbols=["SMALLCAP"])

        # Strategies with filters that exclude SMALLCAP
        strategy_configs = {
            "mega_cap": StrategyConfig(
                strategy_id="mega_cap",
                name="Mega Cap Strategy",
                universe_filter=UniverseFilterConfig(
                    min_market_cap=1_000_000_000_000,  # > 1T
                ),
            ),
            "tech_only": StrategyConfig(
                strategy_id="tech_only",
                name="Tech Only Strategy",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # SMALLCAP matches neither strategy
        routed = manager.route_candle("SMALLCAP")
        assert routed == set()

    @pytest.mark.asyncio
    async def test_route_candle_unknown_symbol(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Unknown symbol returns empty set."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                prev_close=175.0,
                market_cap=3_000_000_000_000,
                avg_volume=50_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["AAPL"])

        strategy_configs = {
            "test_strategy": StrategyConfig(
                strategy_id="test_strategy",
                name="Test Strategy",
                universe_filter=None,  # Matches all
            ),
        }

        manager.build_routing_table(strategy_configs)

        # Unknown symbol returns empty set
        routed = manager.route_candle("UNKNOWN")
        assert routed == set()


class TestSectorIncludeFilter:
    """Tests for sector inclusion filter."""

    @pytest.mark.asyncio
    async def test_sector_include_filter(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Only symbols in specified sectors match."""
        reference_data = {
            "TECH": SymbolReferenceData(
                symbol="TECH",
                sector="Technology",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "HEALTH": SymbolReferenceData(
                symbol="HEALTH",
                sector="Healthcare",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NYSE",
                is_otc=False,
            ),
            "ENERGY": SymbolReferenceData(
                symbol="ENERGY",
                sector="Energy",
                prev_close=100.0,
                avg_volume=5_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "tech_health": StrategyConfig(
                strategy_id="tech_health",
                name="Tech and Healthcare",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology", "Healthcare"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # TECH and HEALTH should match, ENERGY should not
        assert "tech_health" in manager.route_candle("TECH")
        assert "tech_health" in manager.route_candle("HEALTH")
        assert "tech_health" not in manager.route_candle("ENERGY")


class TestSectorExcludeFilter:
    """Tests for sector exclusion filter."""

    @pytest.mark.asyncio
    async def test_sector_exclude_filter(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbols in excluded sectors don't match."""
        reference_data = {
            "TECH": SymbolReferenceData(
                symbol="TECH",
                sector="Technology",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "ENERGY": SymbolReferenceData(
                symbol="ENERGY",
                sector="Energy",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NYSE",
                is_otc=False,
            ),
            "UTILITY": SymbolReferenceData(
                symbol="UTILITY",
                sector="Utilities",
                prev_close=100.0,
                avg_volume=5_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "no_utilities": StrategyConfig(
                strategy_id="no_utilities",
                name="No Utilities Strategy",
                universe_filter=UniverseFilterConfig(
                    exclude_sectors=["Utilities", "Energy"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # TECH should match, ENERGY and UTILITY should not
        assert "no_utilities" in manager.route_candle("TECH")
        assert "no_utilities" not in manager.route_candle("ENERGY")
        assert "no_utilities" not in manager.route_candle("UTILITY")


class TestMissingReferenceDataPasses:
    """Tests for missing reference data handling in routing."""

    @pytest.mark.asyncio
    async def test_missing_reference_data_passes(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol with None market_cap passes min_market_cap filter."""
        reference_data = {
            "NULLCAP": SymbolReferenceData(
                symbol="NULLCAP",
                sector="Technology",
                prev_close=100.0,
                market_cap=None,  # Missing market cap data
                avg_volume=5_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["NULLCAP"])

        strategy_configs = {
            "large_cap": StrategyConfig(
                strategy_id="large_cap",
                name="Large Cap Strategy",
                universe_filter=UniverseFilterConfig(
                    min_market_cap=1_000_000_000_000,  # > 1T
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # Symbol with None market_cap should PASS the filter
        assert "large_cap" in manager.route_candle("NULLCAP")

    @pytest.mark.asyncio
    async def test_null_sector_fails_sector_include(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol with None sector fails sector inclusion filter."""
        reference_data = {
            "NULLSECTOR": SymbolReferenceData(
                symbol="NULLSECTOR",
                sector=None,  # Missing sector
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["NULLSECTOR"])

        strategy_configs = {
            "tech_only": StrategyConfig(
                strategy_id="tech_only",
                name="Tech Only",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # Symbol with None sector should FAIL sector inclusion
        assert "tech_only" not in manager.route_candle("NULLSECTOR")

    @pytest.mark.asyncio
    async def test_null_sector_passes_sector_exclude(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Symbol with None sector passes sector exclusion filter."""
        reference_data = {
            "NULLSECTOR": SymbolReferenceData(
                symbol="NULLSECTOR",
                sector=None,  # Missing sector
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["NULLSECTOR"])

        strategy_configs = {
            "no_energy": StrategyConfig(
                strategy_id="no_energy",
                name="No Energy",
                universe_filter=UniverseFilterConfig(
                    exclude_sectors=["Energy"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # Symbol with None sector should PASS sector exclusion
        assert "no_energy" in manager.route_candle("NULLSECTOR")


class TestNoFilterMatchesAll:
    """Tests for strategy with no universe_filter."""

    @pytest.mark.asyncio
    async def test_no_filter_matches_all(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Strategy with universe_filter=None matches all viable symbols."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                prev_close=175.0,
                avg_volume=50_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "XOM": SymbolReferenceData(
                symbol="XOM",
                sector="Energy",
                prev_close=100.0,
                avg_volume=20_000_000,
                exchange="NYSE",
                is_otc=False,
            ),
            "JNJ": SymbolReferenceData(
                symbol="JNJ",
                sector="Healthcare",
                prev_close=150.0,
                avg_volume=10_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "all_stocks": StrategyConfig(
                strategy_id="all_stocks",
                name="All Stocks Strategy",
                universe_filter=None,  # No filter = match all
            ),
        }

        manager.build_routing_table(strategy_configs)

        # All viable symbols should match
        assert "all_stocks" in manager.route_candle("AAPL")
        assert "all_stocks" in manager.route_candle("XOM")
        assert "all_stocks" in manager.route_candle("JNJ")


class TestGetStrategyUniverseSize:
    """Tests for get_strategy_universe_size method."""

    @pytest.mark.asyncio
    async def test_get_strategy_universe_size(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """get_strategy_universe_size returns correct counts per strategy."""
        reference_data = {
            "TECH1": SymbolReferenceData(
                symbol="TECH1",
                sector="Technology",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "TECH2": SymbolReferenceData(
                symbol="TECH2",
                sector="Technology",
                prev_close=200.0,
                avg_volume=3_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "HEALTH1": SymbolReferenceData(
                symbol="HEALTH1",
                sector="Healthcare",
                prev_close=150.0,
                avg_volume=4_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "tech_only": StrategyConfig(
                strategy_id="tech_only",
                name="Tech Only",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
            "all_sectors": StrategyConfig(
                strategy_id="all_sectors",
                name="All Sectors",
                universe_filter=None,  # No filter
            ),
        }

        manager.build_routing_table(strategy_configs)

        # tech_only should have 2 symbols (TECH1, TECH2)
        assert manager.get_strategy_universe_size("tech_only") == 2

        # all_sectors should have 3 symbols (all)
        assert manager.get_strategy_universe_size("all_sectors") == 3

        # Unknown strategy should have 0
        assert manager.get_strategy_universe_size("unknown") == 0


class TestGetStrategySymbols:
    """Tests for get_strategy_symbols method."""

    @pytest.mark.asyncio
    async def test_get_strategy_symbols(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """get_strategy_symbols returns correct symbol set per strategy."""
        reference_data = {
            "TECH1": SymbolReferenceData(
                symbol="TECH1",
                sector="Technology",
                prev_close=100.0,
                avg_volume=5_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "TECH2": SymbolReferenceData(
                symbol="TECH2",
                sector="Technology",
                prev_close=200.0,
                avg_volume=3_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "HEALTH1": SymbolReferenceData(
                symbol="HEALTH1",
                sector="Healthcare",
                prev_close=150.0,
                avg_volume=4_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "tech_only": StrategyConfig(
                strategy_id="tech_only",
                name="Tech Only",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
        }

        manager.build_routing_table(strategy_configs)

        # tech_only should have TECH1 and TECH2
        tech_symbols = manager.get_strategy_symbols("tech_only")
        assert tech_symbols == {"TECH1", "TECH2"}

        # Unknown strategy should return empty set
        assert manager.get_strategy_symbols("unknown") == set()


class TestGetUniverseStats:
    """Tests for get_universe_stats method."""

    @pytest.mark.asyncio
    async def test_get_universe_stats(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """get_universe_stats returns correct statistics."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                prev_close=175.0,
                avg_volume=50_000_000,
                exchange="NASDAQ",
                is_otc=False,
            ),
            "XOM": SymbolReferenceData(
                symbol="XOM",
                sector="Energy",
                prev_close=100.0,
                avg_volume=20_000_000,
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
        await manager.build_viable_universe(
            initial_symbols=list(reference_data.keys())
        )

        strategy_configs = {
            "tech_only": StrategyConfig(
                strategy_id="tech_only",
                name="Tech Only",
                universe_filter=UniverseFilterConfig(
                    sectors=["Technology"],
                ),
            ),
            "all_stocks": StrategyConfig(
                strategy_id="all_stocks",
                name="All Stocks",
                universe_filter=None,
            ),
        }

        manager.build_routing_table(strategy_configs)

        stats = manager.get_universe_stats()

        # Verify structure
        assert "total_viable" in stats
        assert "per_strategy_counts" in stats
        assert "last_build_time" in stats
        assert "last_routing_build_time" in stats
        assert "cache_age_minutes" in stats

        # Verify values
        assert stats["total_viable"] == 2
        assert stats["per_strategy_counts"]["tech_only"] == 1
        assert stats["per_strategy_counts"]["all_stocks"] == 2
        assert stats["last_build_time"] is not None
        assert stats["last_routing_build_time"] is not None
        assert stats["cache_age_minutes"] is not None
        assert stats["cache_age_minutes"] >= 0


class TestRoutingTableRebuild:
    """Tests for routing table rebuild capability."""

    @pytest.mark.asyncio
    async def test_routing_table_rebuildable(
        self,
        mock_reference_client: MagicMock,
        mock_scanner: MagicMock,
    ) -> None:
        """Routing table can be rebuilt with new strategy configs."""
        reference_data = {
            "AAPL": SymbolReferenceData(
                symbol="AAPL",
                sector="Technology",
                prev_close=175.0,
                avg_volume=50_000_000,
                exchange="NASDAQ",
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
        await manager.build_viable_universe(initial_symbols=["AAPL"])

        # First build with one strategy
        strategy_configs_v1 = {
            "strategy_a": StrategyConfig(
                strategy_id="strategy_a",
                name="Strategy A",
                universe_filter=None,
            ),
        }

        manager.build_routing_table(strategy_configs_v1)
        assert manager.route_candle("AAPL") == {"strategy_a"}

        # Rebuild with different strategies
        strategy_configs_v2 = {
            "strategy_b": StrategyConfig(
                strategy_id="strategy_b",
                name="Strategy B",
                universe_filter=None,
            ),
            "strategy_c": StrategyConfig(
                strategy_id="strategy_c",
                name="Strategy C",
                universe_filter=UniverseFilterConfig(
                    sectors=["Healthcare"],  # Won't match AAPL
                ),
            ),
        }

        manager.build_routing_table(strategy_configs_v2)

        # Should now route to strategy_b only (strategy_c doesn't match)
        assert manager.route_candle("AAPL") == {"strategy_b"}
