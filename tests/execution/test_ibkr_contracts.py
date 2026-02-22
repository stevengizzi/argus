"""Tests for IBKR contract resolution.

Tests:
1. Stock contract creation with correct parameters
2. Cache hit returns same contract instance
3. Qualification with mock IB instance
4. SMART exchange default
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from ib_async import Stock

from argus.execution.ibkr_contracts import IBKRContractResolver


class TestIBKRContractResolver:
    """Test suite for IBKRContractResolver."""

    def test_get_stock_contract_creates_stock_with_correct_params(self) -> None:
        """Stock contract is created with symbol, SMART exchange, USD currency."""
        resolver = IBKRContractResolver()

        contract = resolver.get_stock_contract("AAPL")

        assert isinstance(contract, Stock)
        assert contract.symbol == "AAPL"
        assert contract.exchange == "SMART"
        assert contract.currency == "USD"

    def test_get_stock_contract_cache_hit_returns_same_instance(self) -> None:
        """Getting the same symbol twice returns the cached instance."""
        resolver = IBKRContractResolver()

        contract1 = resolver.get_stock_contract("NVDA")
        contract2 = resolver.get_stock_contract("NVDA")

        # Same object, not just equal
        assert contract1 is contract2
        assert len(resolver.cached_symbols) == 1
        assert "NVDA" in resolver.cached_symbols

    def test_smart_exchange_is_default(self) -> None:
        """SMART exchange (SmartRouting) is used by default."""
        resolver = IBKRContractResolver()

        # Without specifying exchange
        contract = resolver.get_stock_contract("TSLA")

        assert contract.exchange == "SMART"

    def test_custom_exchange_can_be_specified(self) -> None:
        """Custom exchange can be specified if needed."""
        resolver = IBKRContractResolver()

        contract = resolver.get_stock_contract("MSFT", exchange="NASDAQ")

        assert contract.exchange == "NASDAQ"
        assert contract.currency == "USD"

    @pytest.mark.asyncio
    async def test_qualify_contracts_with_mock_ib(self) -> None:
        """Qualify contracts calls IB.qualifyContractsAsync and caches results."""
        resolver = IBKRContractResolver()

        # Create mock IB instance
        mock_ib = MagicMock()

        # Create qualified contracts (IB adds conId during qualification)
        qualified_aapl = Stock("AAPL", "SMART", "USD")
        qualified_aapl.conId = 265598  # AAPL conId
        qualified_nvda = Stock("NVDA", "SMART", "USD")
        qualified_nvda.conId = 4815747  # NVDA conId

        mock_ib.qualifyContractsAsync = AsyncMock(return_value=[qualified_aapl, qualified_nvda])

        # Qualify the contracts
        result = await resolver.qualify_contracts(mock_ib, ["AAPL", "NVDA"])

        # Verify qualifyContractsAsync was called with Stock contracts
        mock_ib.qualifyContractsAsync.assert_called_once()
        call_args = mock_ib.qualifyContractsAsync.call_args[0]
        assert len(call_args) == 2
        assert all(isinstance(c, Stock) for c in call_args)
        symbols = {c.symbol for c in call_args}
        assert symbols == {"AAPL", "NVDA"}

        # Verify cache was updated with qualified contracts
        assert "AAPL" in result
        assert "NVDA" in result
        assert result["AAPL"].conId == 265598
        assert result["NVDA"].conId == 4815747

    def test_clear_cache_empties_cache(self) -> None:
        """Clear cache removes all cached contracts."""
        resolver = IBKRContractResolver()

        # Add some contracts to cache
        resolver.get_stock_contract("AAPL")
        resolver.get_stock_contract("NVDA")
        assert len(resolver.cached_symbols) == 2

        # Clear the cache
        resolver.clear_cache()

        assert len(resolver.cached_symbols) == 0
        assert resolver.get_cached_contract("AAPL") is None

    def test_get_cached_contract_returns_none_if_not_cached(self) -> None:
        """Get cached contract returns None for symbols not in cache."""
        resolver = IBKRContractResolver()

        result = resolver.get_cached_contract("UNKNOWN")

        assert result is None

    def test_multiple_symbols_cached_independently(self) -> None:
        """Different symbols are cached independently."""
        resolver = IBKRContractResolver()

        aapl = resolver.get_stock_contract("AAPL")
        nvda = resolver.get_stock_contract("NVDA")
        msft = resolver.get_stock_contract("MSFT")

        assert len(resolver.cached_symbols) == 3
        assert aapl.symbol == "AAPL"
        assert nvda.symbol == "NVDA"
        assert msft.symbol == "MSFT"

        # Each is its own contract
        assert aapl is not nvda
        assert nvda is not msft
