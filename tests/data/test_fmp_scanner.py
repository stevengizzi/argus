"""Tests for FMPScannerSource.

Sprint 21.7: FMP Scanner Integration.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import aiohttp
import pytest

from argus.data.fmp_scanner import FMPScannerConfig, FMPScannerSource


def _make_fmp_item(
    symbol: str,
    price: float = 50.0,
    changes_pct: float = 5.0,
) -> dict:
    """Create a mock FMP response item with confirmed schema."""
    return {
        "symbol": symbol,
        "price": price,
        "change": price * changes_pct / 100,
        "changesPercentage": changes_pct,
        "name": f"{symbol} Inc.",
        "exchange": "NASDAQ",
    }


class TestFMPScannerSource:
    """Tests for FMPScannerSource."""

    @pytest.fixture
    def config(self) -> FMPScannerConfig:
        """Default config for tests."""
        return FMPScannerConfig(
            fallback_symbols=["AAPL", "MSFT", "GOOGL"],
        )

    @pytest.fixture
    def scanner(self, config: FMPScannerConfig) -> FMPScannerSource:
        """Scanner instance for tests."""
        return FMPScannerSource(config)

    @pytest.mark.asyncio
    async def test_scan_returns_gap_up_candidates(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that scanner returns gap-up candidates from biggest-gainers."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        with patch.object(
            scanner, "_fetch_candidates", new_callable=AsyncMock
        ) as mock_fetch:
            # Manually build expected items
            from argus.core.events import WatchlistItem

            mock_fetch.return_value = [
                WatchlistItem(
                    symbol=f"SYM{i}",
                    gap_pct=0.05,
                    scan_source="fmp",
                    selection_reason="gap_up_5.0%",
                )
                for i in range(5)
            ]
            result = await scanner.scan([])

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_scan_returns_gap_down_candidates(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that scanner returns gap-down candidates from biggest-losers."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        with patch.object(
            scanner, "_fetch_candidates", new_callable=AsyncMock
        ) as mock_fetch:
            from argus.core.events import WatchlistItem

            mock_fetch.return_value = [
                WatchlistItem(
                    symbol=f"SYM{i}",
                    gap_pct=-0.05,
                    scan_source="fmp",
                    selection_reason="gap_down_5.0%",
                )
                for i in range(5)
            ]
            result = await scanner.scan([])

        assert len(result) == 5

    @pytest.mark.asyncio
    async def test_scan_deduplicates_across_endpoints(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that symbol appearing in gainers and actives uses gainer data."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        # Mock the aiohttp session to return specific data
        gainers = [_make_fmp_item("AAPL", price=150.0, changes_pct=10.0)]
        losers: list[dict] = []
        actives = [_make_fmp_item("AAPL", price=150.0, changes_pct=2.0)]  # Same symbol

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            elif endpoint == "biggest-losers":
                return losers
            else:
                return actives

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        # AAPL should appear once with gainer data
        assert len(result) == 1
        assert result[0].symbol == "AAPL"
        assert result[0].selection_reason == "gap_up_10.0%"

    @pytest.mark.asyncio
    async def test_scan_filters_by_min_price(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that items below min_price are excluded."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        # Item with price=5.0 below default min_price=10.0
        gainers = [_make_fmp_item("CHEAP", price=5.0, changes_pct=10.0)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scan_filters_by_max_price(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that items above max_price are excluded."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        # Item with price=600.0 above default max_price=500.0
        gainers = [_make_fmp_item("EXPENSIVE", price=600.0, changes_pct=10.0)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_scan_filters_price_boundary_inclusive(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that items at exactly min_price and max_price are included."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        gainers = [
            _make_fmp_item("ATMIN", price=10.0, changes_pct=5.0),  # == min_price
            _make_fmp_item("ATMAX", price=500.0, changes_pct=3.0),  # == max_price
        ]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 2
        symbols = {item.symbol for item in result}
        assert "ATMIN" in symbols
        assert "ATMAX" in symbols

    @pytest.mark.asyncio
    async def test_scan_respects_max_symbols_returned(self) -> None:
        """Test that result is limited to max_symbols_returned."""
        config = FMPScannerConfig(max_symbols_returned=15)
        scanner = FMPScannerSource(config)

        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        # Return 20 symbols, but config limits to 15
        gainers = [_make_fmp_item(f"SYM{i}", price=50.0, changes_pct=5.0) for i in range(20)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 15

    @pytest.mark.asyncio
    async def test_scan_sets_scan_source_to_fmp(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that all successful scan results have scan_source='fmp'."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        gainers = [_make_fmp_item("AAPL", price=150.0, changes_pct=5.0)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 1
        assert result[0].scan_source == "fmp"

    @pytest.mark.asyncio
    async def test_scan_sets_selection_reason_gap_up(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test selection_reason formatting for gap-up stocks."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        gainers = [_make_fmp_item("AAPL", price=150.0, changes_pct=3.25)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-gainers":
                return gainers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 1
        assert result[0].selection_reason == "gap_up_3.2%"

    @pytest.mark.asyncio
    async def test_scan_sets_selection_reason_gap_down(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test selection_reason formatting for gap-down stocks."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        losers = [_make_fmp_item("AAPL", price=150.0, changes_pct=-1.84)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            if endpoint == "biggest-losers":
                return losers
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 1
        assert result[0].selection_reason == "gap_down_1.8%"

    @pytest.mark.asyncio
    async def test_scan_sets_selection_reason_high_volume(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test selection_reason for most-actives stocks."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        actives = [_make_fmp_item("AAPL", price=150.0, changes_pct=0.5)]

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            # Only return from actives endpoint
            if endpoint == "most-actives":
                return actives
            return []

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner._fetch_candidates()

        assert len(result) == 1
        assert result[0].selection_reason == "high_volume"

    @pytest.mark.asyncio
    async def test_scan_fallback_on_api_error(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that API errors trigger fallback to static symbols."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        with patch.object(
            scanner, "_fetch_candidates", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.side_effect = aiohttp.ClientError("Connection failed")
            result = await scanner.scan([])

        # Should get fallback symbols
        assert len(result) == 3  # Default fallback_symbols
        assert result[0].symbol == "AAPL"
        assert result[0].scan_source == "fmp_fallback"

    @pytest.mark.asyncio
    async def test_scan_fallback_on_empty_response(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that empty response triggers fallback to static symbols."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        async def mock_fetch_endpoint(
            session: aiohttp.ClientSession, endpoint: str
        ) -> list[dict]:
            return []  # All endpoints return empty

        with patch.object(
            scanner, "_fetch_endpoint", side_effect=mock_fetch_endpoint
        ):
            result = await scanner.scan([])

        # Should get fallback symbols
        assert len(result) == 3
        assert result[0].symbol == "AAPL"
        assert result[0].scan_source == "fmp_fallback"

    @pytest.mark.asyncio
    async def test_start_raises_on_missing_api_key(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that start() raises RuntimeError if API key is missing."""
        with patch.dict("os.environ", {}, clear=True):
            # Ensure FMP_API_KEY is not set
            import os
            if "FMP_API_KEY" in os.environ:
                del os.environ["FMP_API_KEY"]

            with pytest.raises(RuntimeError, match="FMP API key not found"):
                await scanner.start()

    @pytest.mark.asyncio
    async def test_start_succeeds_with_api_key(
        self, scanner: FMPScannerSource
    ) -> None:
        """Test that start() succeeds when API key is set."""
        with patch.dict("os.environ", {"FMP_API_KEY": "test_key"}):
            await scanner.start()

        assert scanner._api_key == "test_key"
