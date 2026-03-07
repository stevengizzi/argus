"""Universe Manager for viable trading universe construction.

Orchestrates FMP reference data fetching, applies system-level filters
to construct the viable trading universe, and provides the foundation
for strategy-specific routing (added in Session 3a).

Sprint 23: NLP Catalyst + Universe Manager
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from argus.data.fmp_reference import FMPReferenceClient, SymbolReferenceData
from argus.data.scanner import Scanner

logger = logging.getLogger(__name__)


@dataclass
class UniverseManagerConfig:
    """Temporary configuration for UniverseManager.

    This dataclass will be replaced by a Pydantic model in Session 4a.
    Designed for trivial swap when the real config is integrated.

    Attributes:
        enabled: Whether the Universe Manager is active.
        min_price: Minimum previous close price for viable symbols.
        max_price: Maximum previous close price for viable symbols.
        min_avg_volume: Minimum average daily volume for viable symbols.
        exclude_otc: Whether to exclude OTC-traded symbols.
        reference_cache_ttl_hours: Hours before reference cache is stale.
        fmp_batch_size: Number of symbols per FMP batch request.
    """

    enabled: bool = False
    min_price: float = 5.0
    max_price: float = 10000.0
    min_avg_volume: int = 100000
    exclude_otc: bool = True
    reference_cache_ttl_hours: int = 24
    fmp_batch_size: int = 50


class UniverseManager:
    """Manager for constructing and maintaining the viable trading universe.

    The Universe Manager orchestrates:
    1. Fetching reference data from FMP (company profiles, float data)
    2. Applying system-level filters (price, volume, OTC exclusion)
    3. Building the viable universe (symbols that pass all filters)

    Routing table construction for strategy-specific universes is handled
    in Session 3a.

    Usage:
        config = UniverseManagerConfig()
        manager = UniverseManager(reference_client, config, scanner)
        await manager.build_viable_universe()
        viable = manager.viable_symbols
    """

    def __init__(
        self,
        reference_client: FMPReferenceClient,
        config: UniverseManagerConfig,
        scanner: Scanner,
    ) -> None:
        """Initialize UniverseManager.

        Args:
            reference_client: FMPReferenceClient for fetching reference data.
            config: Configuration for universe filtering.
            scanner: Scanner for fallback symbol list.
        """
        self._reference_client = reference_client
        self._config = config
        self._scanner = scanner

        # Internal state
        self._viable_symbols: set[str] = set()
        self._reference_cache: dict[str, SymbolReferenceData] = {}
        self._routing_table: dict[str, set[str]] = {}  # Populated in Session 3a
        self._last_build_time: datetime | None = None

    async def build_viable_universe(
        self,
        initial_symbols: list[str] | None = None,
    ) -> set[str]:
        """Build the viable trading universe.

        Fetches reference data for all symbols, applies system-level filters,
        and stores the result. If initial_symbols is not provided, this method
        expects the reference_client cache to be pre-populated.

        Args:
            initial_symbols: Starting list of symbols to filter. If None,
                attempts to use symbols already in reference client cache.

        Returns:
            Set of symbols that pass all system-level filters.
        """
        import time

        start_time = time.monotonic()

        # Get initial symbol list
        if initial_symbols is not None:
            symbols = initial_symbols
            logger.info(
                "Building viable universe from %d initial symbols",
                len(symbols),
            )
        else:
            # Use reference client's existing cache if available
            symbols = list(self._reference_client._cache.keys())
            if not symbols:
                logger.warning(
                    "No initial symbols provided and reference cache is empty"
                )
                return set()

        # Fetch reference data for all symbols
        try:
            reference_data = await self._reference_client.build_reference_cache(symbols)
        except Exception as e:
            logger.error("Failed to fetch reference data: %s", e)
            return set()

        if not reference_data:
            logger.warning("No reference data fetched - viable universe is empty")
            self._viable_symbols = set()
            self._reference_cache = {}
            self._last_build_time = datetime.now(ZoneInfo("UTC"))
            return set()

        # Apply system-level filters
        viable_symbols = self._apply_system_filters(reference_data)

        # Store results
        self._viable_symbols = viable_symbols
        self._reference_cache = reference_data
        self._last_build_time = datetime.now(ZoneInfo("UTC"))

        elapsed = time.monotonic() - start_time

        # Log filter pass rates
        total_fetched = len(reference_data)
        viable_count = len(viable_symbols)
        pass_rate = (viable_count / total_fetched * 100) if total_fetched > 0 else 0

        logger.info(
            "Viable universe built: %d fetched, %d viable (%.1f%% pass rate), %.2fs",
            total_fetched,
            viable_count,
            pass_rate,
            elapsed,
        )

        return viable_symbols

    async def build_viable_universe_fallback(
        self,
        scanner_symbols: list[str],
    ) -> set[str]:
        """Fallback universe construction when FMP fails.

        Uses scanner results as the viable universe and attempts to fetch
        reference data for these symbols (may partially succeed).

        Args:
            scanner_symbols: Symbols from scanner to use as viable universe.

        Returns:
            Set of scanner symbols (used as-is for viable universe).
        """
        logger.warning(
            "Using fallback universe construction with %d scanner symbols - "
            "reference data may be incomplete",
            len(scanner_symbols),
        )

        # Convert to set for consistency
        viable_symbols = set(scanner_symbols)

        # Attempt to fetch reference data (best effort)
        try:
            reference_data = await self._reference_client.build_reference_cache(
                scanner_symbols
            )
            self._reference_cache = reference_data
            logger.info(
                "Fallback mode: fetched reference data for %d/%d symbols",
                len(reference_data),
                len(scanner_symbols),
            )
        except Exception as e:
            logger.warning("Failed to fetch reference data in fallback mode: %s", e)
            self._reference_cache = {}

        # Store results
        self._viable_symbols = viable_symbols
        self._last_build_time = datetime.now(ZoneInfo("UTC"))

        return viable_symbols

    def _apply_system_filters(
        self,
        reference_data: dict[str, SymbolReferenceData],
    ) -> set[str]:
        """Apply system-level filters to reference data.

        Filters:
        - exclude_otc: Exclude OTC-traded symbols
        - min_price / max_price: Filter on previous close price
        - min_avg_volume: Filter on average trading volume

        Args:
            reference_data: Dictionary of symbol to reference data.

        Returns:
            Set of symbols that pass all filters.
        """
        viable: set[str] = set()
        excluded_otc = 0
        excluded_price = 0
        excluded_volume = 0

        for symbol, data in reference_data.items():
            # OTC filter
            if self._config.exclude_otc and data.is_otc:
                excluded_otc += 1
                continue

            # Price filter (skip if prev_close is None)
            if data.prev_close is not None:
                if data.prev_close < self._config.min_price:
                    excluded_price += 1
                    continue
                if data.prev_close > self._config.max_price:
                    excluded_price += 1
                    continue

            # Volume filter (skip if avg_volume is None)
            if (
                data.avg_volume is not None
                and data.avg_volume < self._config.min_avg_volume
            ):
                excluded_volume += 1
                continue

            # Passed all filters
            viable.add(symbol)

        # Log filter statistics
        logger.debug(
            "Filter stats: excluded_otc=%d, excluded_price=%d, excluded_volume=%d",
            excluded_otc,
            excluded_price,
            excluded_volume,
        )

        if not viable:
            logger.warning(
                "All %d symbols filtered out - viable universe is empty. "
                "Check filter settings: min_price=%.2f, max_price=%.2f, "
                "min_avg_volume=%d, exclude_otc=%s",
                len(reference_data),
                self._config.min_price,
                self._config.max_price,
                self._config.min_avg_volume,
                self._config.exclude_otc,
            )

        return viable

    @property
    def viable_symbols(self) -> set[str]:
        """Get the current viable symbol set.

        Returns:
            Set of symbols that passed all system-level filters.
        """
        return self._viable_symbols.copy()

    @property
    def viable_count(self) -> int:
        """Get the count of viable symbols.

        Returns:
            Number of symbols in the viable universe.
        """
        return len(self._viable_symbols)

    @property
    def reference_cache(self) -> dict[str, SymbolReferenceData]:
        """Get the reference data cache.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
        """
        return self._reference_cache.copy()

    @property
    def last_build_time(self) -> datetime | None:
        """Get the timestamp of the last universe build.

        Returns:
            UTC datetime of last build, or None if never built.
        """
        return self._last_build_time

    @property
    def is_built(self) -> bool:
        """Check if the viable universe has been built.

        Returns:
            True if build_viable_universe has been called at least once.
        """
        return self._last_build_time is not None

    def get_reference_data(self, symbol: str) -> SymbolReferenceData | None:
        """Get cached reference data for a symbol.

        Args:
            symbol: Stock symbol to look up.

        Returns:
            SymbolReferenceData if cached, None otherwise.
        """
        return self._reference_cache.get(symbol)
