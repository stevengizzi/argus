"""IBKR contract resolution.

Converts ARGUS symbol strings to qualified ib_async Contract objects.
V1 handles US equities only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ib_async import Contract, Stock

if TYPE_CHECKING:
    from ib_async import IB


class IBKRContractResolver:
    """Resolves ARGUS symbols to qualified IBKR Contract objects.

    Caches resolved contracts by symbol to avoid redundant qualifications.
    V1 supports US equities only (Stock contracts with SMART routing).

    Example:
        resolver = IBKRContractResolver()
        contract = resolver.get_stock_contract("AAPL")
        # Contract is Stock("AAPL", "SMART", "USD")

        # For full qualification with conId resolution:
        await resolver.qualify_contracts(ib, ["AAPL", "NVDA", "MSFT"])
    """

    def __init__(self) -> None:
        """Initialize the contract resolver with empty cache."""
        self._cache: dict[str, Contract] = {}

    def get_stock_contract(
        self,
        symbol: str,
        exchange: str = "SMART",
        currency: str = "USD",
    ) -> Stock:
        """Create a Stock contract for the given symbol.

        Uses SMART routing by default (IBKR SmartRouting across 20+ venues).
        Returns cached contract if available.

        Args:
            symbol: The stock ticker symbol (e.g., "AAPL").
            exchange: Exchange routing. Defaults to "SMART" for SmartRouting.
            currency: Contract currency. Defaults to "USD".

        Returns:
            Stock contract object (cached if previously created).
        """
        if symbol not in self._cache:
            self._cache[symbol] = Stock(symbol, exchange, currency)
        return self._cache[symbol]

    async def qualify_contracts(
        self,
        ib: IB,
        symbols: list[str],
    ) -> dict[str, Contract]:
        """Qualify contracts with IBKR to get full conId resolution.

        Call once at startup for the watchlist. Caches results.
        Qualified contracts have their conId populated by IBKR,
        enabling unambiguous order routing.

        Args:
            ib: Connected IB instance.
            symbols: List of ticker symbols to qualify.

        Returns:
            Dict mapping symbol to qualified Contract.
        """
        contracts = [self.get_stock_contract(s) for s in symbols]
        qualified = await ib.qualifyContractsAsync(*contracts)
        for contract in qualified:
            self._cache[contract.symbol] = contract
        return self._cache.copy()

    def clear_cache(self) -> None:
        """Clear the contract cache.

        Use when symbols may need requalification (e.g., after reconnect
        or when switching accounts).
        """
        self._cache.clear()

    def get_cached_contract(self, symbol: str) -> Contract | None:
        """Get a contract from cache without creating it.

        Args:
            symbol: The stock ticker symbol.

        Returns:
            Cached Contract if exists, None otherwise.
        """
        return self._cache.get(symbol)

    @property
    def cached_symbols(self) -> list[str]:
        """Return list of currently cached symbols."""
        return list(self._cache.keys())
