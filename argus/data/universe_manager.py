"""Universe Manager for viable trading universe construction.

Orchestrates FMP reference data fetching, applies system-level filters
to construct the viable trading universe, and provides the foundation
for strategy-specific routing (added in Session 3a).

Sprint 23: NLP Catalyst + Universe Manager
"""

from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

from argus.core.config import StrategyConfig, UniverseFilterConfig, UniverseManagerConfig
from argus.data.fmp_reference import FMPReferenceClient, SymbolReferenceData
from argus.data.scanner import Scanner

logger = logging.getLogger(__name__)


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
        self._routing_table: dict[str, set[str]] = {}
        self._last_build_time: datetime | None = None
        self._last_routing_build_time: datetime | None = None

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

        # Fetch reference data for all symbols (incremental - uses cache)
        try:
            reference_data = await self._reference_client.fetch_reference_data_incremental(
                symbols
            )
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
        - Missing data: Exclude symbols with None prev_close or avg_volume (fail-closed)
        - exclude_otc: Exclude OTC-traded symbols
        - min_price / max_price: Filter on previous close price
        - min_avg_volume: Filter on average trading volume

        Args:
            reference_data: Dictionary of symbol to reference data.

        Returns:
            Set of symbols that pass all filters.
        """
        viable: set[str] = set()
        excluded_missing_data = 0
        excluded_otc = 0
        excluded_price = 0
        excluded_volume = 0

        for symbol, data in reference_data.items():
            # Fail-closed: exclude symbols missing essential reference data (DEC-277)
            if data.prev_close is None or data.avg_volume is None:
                excluded_missing_data += 1
                continue

            # OTC filter
            if self._config.exclude_otc and data.is_otc:
                excluded_otc += 1
                continue

            # Price filter
            if data.prev_close < self._config.min_price:
                excluded_price += 1
                continue
            if data.prev_close > self._config.max_price:
                excluded_price += 1
                continue

            # Volume filter
            if data.avg_volume < self._config.min_avg_volume:
                excluded_volume += 1
                continue

            # Passed all filters
            viable.add(symbol)

        # Log filter statistics
        logger.info(
            "Filter stats: excluded_missing_data=%d, excluded_otc=%d, "
            "excluded_price=%d, excluded_volume=%d",
            excluded_missing_data,
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

    def build_routing_table(
        self,
        strategy_configs: dict[str, StrategyConfig],
    ) -> None:
        """Build the routing table mapping symbols to qualifying strategies.

        For each viable symbol, checks each strategy's universe_filter and
        adds the strategy to the symbol's routing set if all filter criteria
        pass. Strategies with universe_filter=None match all viable symbols.

        Filter matching rule: when a symbol has None for a field and the
        filter has a constraint on that field, the symbol PASSES the filter.
        We don't want to exclude symbols just because FMP didn't return
        complete data.

        Args:
            strategy_configs: Dictionary mapping strategy_id to StrategyConfig.
        """
        import time

        start_time = time.monotonic()

        # Clear and rebuild
        self._routing_table.clear()

        # Initialize routing sets for all viable symbols
        for symbol in self._viable_symbols:
            self._routing_table[symbol] = set()

        # Track per-strategy match counts for logging
        strategy_match_counts: dict[str, int] = {}

        for strategy_id, config in strategy_configs.items():
            match_count = 0

            for symbol in self._viable_symbols:
                if self._symbol_matches_filter(symbol, config.universe_filter):
                    self._routing_table[symbol].add(strategy_id)
                    match_count += 1

            strategy_match_counts[strategy_id] = match_count

        self._last_routing_build_time = datetime.now(ZoneInfo("UTC"))
        elapsed = time.monotonic() - start_time

        # Log per-strategy match counts
        for strategy_id, count in strategy_match_counts.items():
            logger.info(
                "Routing table: strategy %s matches %d/%d symbols",
                strategy_id,
                count,
                len(self._viable_symbols),
            )

        logger.info(
            "Routing table built: %d strategies, %d symbols, %.3fs",
            len(strategy_configs),
            len(self._viable_symbols),
            elapsed,
        )

    def _symbol_matches_filter(
        self,
        symbol: str,
        universe_filter: UniverseFilterConfig | None,
    ) -> bool:
        """Check if a symbol matches a strategy's universe filter.

        Args:
            symbol: Symbol to check.
            universe_filter: The filter to apply, or None for match-all.

        Returns:
            True if the symbol matches all filter criteria.
        """
        # No filter means match all viable symbols
        if universe_filter is None:
            return True

        # Get reference data for this symbol
        ref_data = self._reference_cache.get(symbol)
        if ref_data is None:
            # Fail-closed: no reference data means symbol is excluded (DEC-277)
            return False

        # Check price constraints (None reference data = pass)
        if universe_filter.min_price is not None:
            if ref_data.prev_close is not None:
                if ref_data.prev_close < universe_filter.min_price:
                    return False

        if universe_filter.max_price is not None:
            if ref_data.prev_close is not None:
                if ref_data.prev_close > universe_filter.max_price:
                    return False

        # Check market cap constraints (None reference data = pass)
        if universe_filter.min_market_cap is not None:
            if ref_data.market_cap is not None:
                if ref_data.market_cap < universe_filter.min_market_cap:
                    return False

        if universe_filter.max_market_cap is not None:
            if ref_data.market_cap is not None:
                if ref_data.market_cap > universe_filter.max_market_cap:
                    return False

        # Check float shares constraint (None reference data = pass)
        if universe_filter.min_float is not None:
            if ref_data.float_shares is not None:
                if ref_data.float_shares < universe_filter.min_float:
                    return False

        # Check avg volume constraint (None reference data = pass)
        if universe_filter.min_avg_volume is not None:
            if ref_data.avg_volume is not None:
                if ref_data.avg_volume < universe_filter.min_avg_volume:
                    return False

        # Check sector inclusion (non-empty list = symbol's sector must be in list)
        if universe_filter.sectors:
            # None sector = FAIL (we require a specific sector)
            if ref_data.sector is None:
                return False
            if ref_data.sector not in universe_filter.sectors:
                return False

        # Check sector exclusion (non-empty list = symbol's sector must NOT be in list)
        if universe_filter.exclude_sectors:
            # None sector = PASS (can't exclude what we don't know)
            if ref_data.sector is not None:
                if ref_data.sector in universe_filter.exclude_sectors:
                    return False

        return True

    def route_candle(self, symbol: str) -> set[str]:
        """Get the set of strategy IDs that should receive candles for this symbol.

        O(1) dictionary lookup.

        Args:
            symbol: The stock symbol.

        Returns:
            Set of strategy IDs that match this symbol, empty set if not found.
        """
        return self._routing_table.get(symbol, set())

    def get_strategy_universe_size(self, strategy_id: str) -> int:
        """Get the number of symbols routed to a specific strategy.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            Count of symbols in the routing table that include this strategy.
        """
        count = 0
        for strategies in self._routing_table.values():
            if strategy_id in strategies:
                count += 1
        return count

    def get_strategy_symbols(self, strategy_id: str) -> set[str]:
        """Get all symbols routed to a specific strategy.

        Args:
            strategy_id: The strategy identifier.

        Returns:
            Set of symbols that route to this strategy.
        """
        return {
            symbol
            for symbol, strategies in self._routing_table.items()
            if strategy_id in strategies
        }

    def get_universe_stats(self) -> dict:
        """Get statistics about the universe and routing table.

        Returns:
            Dictionary with:
                - total_viable: Number of viable symbols
                - per_strategy_counts: Dict mapping strategy_id to symbol count
                - last_build_time: ISO timestamp of last viable universe build
                - last_routing_build_time: ISO timestamp of last routing table build
                - cache_age_minutes: Minutes since last viable universe build
        """
        # Compute per-strategy counts
        strategy_counts: dict[str, int] = {}
        for strategies in self._routing_table.values():
            for strategy_id in strategies:
                strategy_counts[strategy_id] = strategy_counts.get(strategy_id, 0) + 1

        # Compute cache age
        cache_age_minutes: float | None = None
        if self._last_build_time is not None:
            delta = datetime.now(ZoneInfo("UTC")) - self._last_build_time
            cache_age_minutes = delta.total_seconds() / 60.0

        return {
            "total_viable": len(self._viable_symbols),
            "per_strategy_counts": strategy_counts,
            "last_build_time": (
                self._last_build_time.isoformat() if self._last_build_time else None
            ),
            "last_routing_build_time": (
                self._last_routing_build_time.isoformat()
                if self._last_routing_build_time
                else None
            ),
            "cache_age_minutes": cache_age_minutes,
        }
