"""Catalyst data source clients for the NLP Catalyst Pipeline.

This module provides abstract and concrete implementations for fetching
catalyst data from various external sources: SEC EDGAR, FMP News, and Finnhub.

Sprint 23.5 Session 2 — DEC-164
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.intelligence.models import CatalystRawItem


class CatalystSource(ABC):
    """Abstract base class for catalyst data sources.

    All catalyst data sources must implement this interface. Sources are
    responsible for fetching raw catalyst items from external APIs and
    returning them in a normalized format.

    Lifecycle:
        1. Create instance with config
        2. Call start() to initialize HTTP session and resources
        3. Call fetch_catalysts() as needed
        4. Call stop() to clean up resources
    """

    @abstractmethod
    async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
        """Fetch raw catalyst items for the given symbols.

        Args:
            symbols: List of stock ticker symbols to fetch catalysts for.

        Returns:
            List of raw catalyst items from this source. May be empty
            if no catalysts found or on API error.
        """
        ...

    @abstractmethod
    async def start(self) -> None:
        """Initialize the source (create HTTP session, etc.).

        Called once before fetch_catalysts(). Implementations should
        validate API keys and set up any required resources.
        """
        ...

    @abstractmethod
    async def stop(self) -> None:
        """Clean up resources.

        Called when the source is no longer needed. Implementations
        should close HTTP sessions and release any held resources.
        """
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Return the source identifier.

        Returns:
            Source name string (e.g., 'sec_edgar', 'fmp_news', 'finnhub').
        """
        ...


__all__ = ["CatalystSource"]
