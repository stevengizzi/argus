"""Tests for the Scanner module."""

import pytest

from argus.core.events import WatchlistItem
from argus.data.scanner import Scanner, StaticScanner
from argus.models.strategy import ScannerCriteria


class TestStaticScanner:
    """Tests for the StaticScanner implementation."""

    @pytest.mark.asyncio
    async def test_returns_all_configured_symbols(self) -> None:
        """StaticScanner returns all configured symbols regardless of criteria."""
        scanner = StaticScanner(symbols=["AAPL", "MSFT", "NVDA"])
        await scanner.start()

        # Criteria are ignored
        criteria = [ScannerCriteria(min_price=50.0)]
        results = await scanner.scan(criteria)

        await scanner.stop()

        assert len(results) == 3
        symbols = [item.symbol for item in results]
        assert "AAPL" in symbols
        assert "MSFT" in symbols
        assert "NVDA" in symbols

    @pytest.mark.asyncio
    async def test_returns_watchlist_items(self) -> None:
        """StaticScanner returns WatchlistItem instances."""
        scanner = StaticScanner(symbols=["AAPL"])
        results = await scanner.scan([])

        assert len(results) == 1
        assert isinstance(results[0], WatchlistItem)
        assert results[0].symbol == "AAPL"

    @pytest.mark.asyncio
    async def test_handles_empty_symbol_list(self) -> None:
        """StaticScanner handles empty symbol list gracefully."""
        scanner = StaticScanner(symbols=[])
        results = await scanner.scan([])

        assert results == []

    @pytest.mark.asyncio
    async def test_deduplicates_symbols(self) -> None:
        """StaticScanner removes duplicate symbols."""
        scanner = StaticScanner(symbols=["AAPL", "MSFT", "AAPL", "nvda", "NVDA"])
        results = await scanner.scan([])

        # Should have AAPL, MSFT, NVDA (deduplicated, case-insensitive)
        assert len(results) == 3
        symbols = [item.symbol for item in results]
        assert symbols == ["AAPL", "MSFT", "NVDA"]

    @pytest.mark.asyncio
    async def test_uppercase_symbols(self) -> None:
        """StaticScanner uppercases all symbols."""
        scanner = StaticScanner(symbols=["aapl", "msft"])
        results = await scanner.scan([])

        symbols = [item.symbol for item in results]
        assert symbols == ["AAPL", "MSFT"]

    @pytest.mark.asyncio
    async def test_ignores_scanner_criteria(self) -> None:
        """StaticScanner ignores all scanner criteria filters."""
        scanner = StaticScanner(symbols=["AAPL", "MSFT"])

        # Very restrictive criteria that would filter out everything
        criteria = [
            ScannerCriteria(
                min_price=1000.0,  # Very high minimum
                max_price=1001.0,
                min_volume_avg_daily=1_000_000_000,  # Unrealistic volume
                min_gap_pct=0.50,  # 50% gap requirement
            )
        ]
        results = await scanner.scan(criteria)

        # Should still return all configured symbols
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_start_and_stop_are_noop(self) -> None:
        """StaticScanner start and stop are safe no-ops."""
        scanner = StaticScanner(symbols=["AAPL"])

        # Should not raise
        await scanner.start()
        await scanner.start()  # Multiple starts OK
        await scanner.stop()
        await scanner.stop()  # Multiple stops OK

    def test_symbols_property_returns_copy(self) -> None:
        """Symbols property returns a copy of the list."""
        scanner = StaticScanner(symbols=["AAPL", "MSFT"])
        symbols = scanner.symbols
        symbols.append("NVDA")  # Modify the copy

        # Original should be unchanged
        assert "NVDA" not in scanner.symbols

    def test_preserves_symbol_order(self) -> None:
        """StaticScanner preserves the order of symbols."""
        scanner = StaticScanner(symbols=["TSLA", "AAPL", "MSFT", "NVDA", "AMD"])
        assert scanner.symbols == ["TSLA", "AAPL", "MSFT", "NVDA", "AMD"]


class TestScannerABC:
    """Tests for the Scanner ABC interface."""

    def test_scanner_is_abstract(self) -> None:
        """Scanner cannot be instantiated directly."""
        with pytest.raises(TypeError, match="abstract"):
            Scanner()  # type: ignore[abstract]

    def test_static_scanner_is_subclass(self) -> None:
        """StaticScanner is a subclass of Scanner."""
        assert issubclass(StaticScanner, Scanner)
