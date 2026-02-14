"""Scanner abstraction for stock selection.

Scanners take criteria from active strategies and produce a merged
watchlist of stocks to trade for the day.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod

from argus.core.events import WatchlistItem
from argus.models.strategy import ScannerCriteria

logger = logging.getLogger(__name__)


class Scanner(ABC):
    """Abstract base class for stock scanners.

    The Scanner takes ScannerCriteria from active strategies and produces
    a merged watchlist. Published as a WatchlistEvent on the Event Bus.
    """

    @abstractmethod
    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Run the scanner with criteria from all active strategies.

        Args:
            criteria_list: Scanner criteria from each active strategy.

        Returns:
            Merged, deduplicated list of WatchlistItems.
        """

    @abstractmethod
    async def start(self) -> None:
        """Initialize scanner resources."""

    @abstractmethod
    async def stop(self) -> None:
        """Clean up scanner resources."""


class StaticScanner(Scanner):
    """Scanner that returns a fixed list of symbols from configuration.

    Used for backtesting, replay, and development. Symbols are defined
    in config/scanner.yaml or injected at construction.

    The StaticScanner ignores ScannerCriteria filters — it always returns
    its configured symbol list. This is intentional: during replay/backtest,
    the watchlist is predetermined from historical data.
    """

    def __init__(self, symbols: list[str]) -> None:
        """Initialize with a fixed symbol list.

        Args:
            symbols: List of ticker symbols to always return.
        """
        # Deduplicate while preserving order
        seen: set[str] = set()
        self._symbols: list[str] = []
        for symbol in symbols:
            upper_symbol = symbol.upper()
            if upper_symbol not in seen:
                seen.add(upper_symbol)
                self._symbols.append(upper_symbol)

    @property
    def symbols(self) -> list[str]:
        """Return the configured symbol list."""
        return self._symbols.copy()

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Return the static symbol list as WatchlistItems.

        Args:
            criteria_list: Ignored by StaticScanner.

        Returns:
            WatchlistItems for each configured symbol.
        """
        logger.info(
            "StaticScanner returning %d symbols (criteria ignored)",
            len(self._symbols),
        )
        return [WatchlistItem(symbol=symbol) for symbol in self._symbols]

    async def start(self) -> None:
        """No-op for StaticScanner."""
        logger.info("StaticScanner started with %d symbols", len(self._symbols))

    async def stop(self) -> None:
        """No-op for StaticScanner."""
        logger.info("StaticScanner stopped")
