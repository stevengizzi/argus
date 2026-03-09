"""FMP Reference Data Client for batch company profile and float data.

Fetches reference data from Financial Modeling Prep (FMP) API for use by
the Universe Manager. Provides company sector, market cap, float shares,
and other reference data needed for position sizing and filtering.

FMP API Endpoints Used:
- Company Profile: GET /stable/profile?symbol={sym}&apikey=KEY
  Returns: symbol, sector, industry, mktCap, exchangeShortName, price, volAvg
- Share Float: GET /stable/shares-float?symbol={sym}&apikey=KEY
  Returns: floatShares

Sprint 23: NLP Catalyst + Universe Manager
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class SymbolReferenceData:
    """Reference data for a single symbol.

    Combines company profile data (sector, market cap, exchange) with
    share float data for comprehensive symbol information.

    Attributes:
        symbol: The stock ticker symbol.
        sector: GICS sector from Company Profile (e.g., "Technology").
        industry: Industry classification (e.g., "Consumer Electronics").
        market_cap: Market capitalization in USD.
        float_shares: Number of floating shares from Share Float endpoint.
        exchange: Exchange short name (e.g., "NASDAQ", "NYSE", "OTC").
        prev_close: Previous closing price.
        avg_volume: Average trading volume.
        is_otc: True if the symbol trades on OTC markets.
        fetched_at: Timestamp when this data was fetched.
    """

    symbol: str
    sector: str | None = None
    industry: str | None = None
    market_cap: float | None = None
    float_shares: float | None = None
    exchange: str | None = None
    prev_close: float | None = None
    avg_volume: float | None = None
    is_otc: bool = False
    fetched_at: datetime = field(default_factory=lambda: datetime.now(ZoneInfo("UTC")))


@dataclass
class FMPReferenceConfig:
    """Configuration for FMPReferenceClient.

    Attributes:
        base_url: FMP API base URL (v3 API for batch profile endpoint).
        api_key_env_var: Environment variable name containing the API key.
        batch_size: Number of symbols per batch request (max 50 for FMP).
        cache_ttl_hours: Hours before cache is considered stale.
        max_retries: Maximum retry attempts for failed requests.
        request_timeout_seconds: HTTP request timeout in seconds.
    """

    base_url: str = "https://financialmodelingprep.com/stable"
    api_key_env_var: str = "FMP_API_KEY"
    batch_size: int = 50
    cache_ttl_hours: int = 24
    max_retries: int = 3
    request_timeout_seconds: float = 30.0


class FMPReferenceClient:
    """Client for fetching reference data from FMP API.

    Provides batch fetching of company profiles and share float data
    with caching and graceful degradation on API failures.

    Usage:
        config = FMPReferenceConfig()
        client = FMPReferenceClient(config)
        await client.start()  # Validates API key
        data = await client.build_reference_cache(["AAPL", "MSFT", "NVDA"])
    """

    # OTC exchange identifiers from FMP data
    _OTC_EXCHANGES: frozenset[str] = frozenset({
        "OTC",
        "OTCQX",
        "OTCQB",
        "PINK",
        "GREY",
        "OTC MARKETS",
    })

    def __init__(self, config: FMPReferenceConfig) -> None:
        """Initialize FMPReferenceClient.

        Args:
            config: Configuration for the client.
        """
        self._config = config
        self._api_key: str | None = None
        self._cache: dict[str, SymbolReferenceData] = {}
        self._cache_built_at: datetime | None = None

    async def start(self) -> None:
        """Initialize the client and validate API key.

        Raises:
            RuntimeError: If FMP API key is not found in environment.
        """
        self._api_key = os.getenv(self._config.api_key_env_var)
        if self._api_key is None:
            raise RuntimeError(
                f"FMP API key not found. Set {self._config.api_key_env_var}."
            )
        logger.info("FMPReferenceClient started")

    async def stop(self) -> None:
        """Clean up client resources."""
        self._api_key = None
        logger.info("FMPReferenceClient stopped")

    async def fetch_reference_data(
        self, symbols: list[str]
    ) -> dict[str, SymbolReferenceData]:
        """Fetch company profile data for symbols in batches.

        Splits symbols into batches and fetches company profiles from FMP.
        Handles partial failures gracefully - failed batches are logged but
        don't prevent other batches from being processed.

        FMP Batch Profile Endpoint:
            GET /api/v3/profile/{sym1,sym2,...}?apikey=KEY

        FMP Response Fields:
            - symbol: Stock ticker
            - sector: GICS sector
            - industry: Industry classification
            - mktCap: Market capitalization
            - exchangeShortName: Exchange (NASDAQ, NYSE, OTC, etc.)
            - price: Current/previous close price
            - volAvg: Average volume

        Args:
            symbols: List of stock symbols to fetch.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
            Symbols that failed to fetch are not included.
        """
        if not symbols:
            return {}

        if self._api_key is None:
            logger.error("FMPReferenceClient not started - call start() first")
            return {}

        # Split into batches
        batches = [
            symbols[i : i + self._config.batch_size]
            for i in range(0, len(symbols), self._config.batch_size)
        ]

        logger.debug(
            "Fetching reference data for %d symbols in %d batches",
            len(symbols),
            len(batches),
        )

        results: dict[str, SymbolReferenceData] = {}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._config.request_timeout_seconds)
        ) as session:
            for batch_idx, batch in enumerate(batches):
                try:
                    batch_results = await self._fetch_batch(session, batch)
                    results.update(batch_results)
                    logger.debug(
                        "Batch %d/%d: fetched %d symbols",
                        batch_idx + 1,
                        len(batches),
                        len(batch_results),
                    )
                except Exception as e:
                    logger.warning(
                        "Batch %d/%d failed: %s",
                        batch_idx + 1,
                        len(batches),
                        e,
                    )
                    # Continue with other batches

                # Rate limiting: FMP allows 300 calls/min (~5/sec)
                # Sleep briefly between batches to stay well under limit
                if batch_idx < len(batches) - 1:
                    await asyncio.sleep(0.25)

        return results

    async def _fetch_batch(
        self, session: aiohttp.ClientSession, symbols: list[str]
    ) -> dict[str, SymbolReferenceData]:
        """Fetch a batch of company profiles (per-symbol on stable API).

        The FMP stable API does not support comma-separated batch profile
        requests on Starter plans, so symbols are fetched individually.

        Args:
            session: aiohttp client session.
            symbols: Batch of symbols to fetch.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
        """
        results: dict[str, SymbolReferenceData] = {}

        for symbol in symbols:
            last_error: Exception | None = None

            for attempt in range(self._config.max_retries):
                try:
                    url = f"{self._config.base_url}/profile"
                    params = {"symbol": symbol, "apikey": self._api_key}

                    async with session.get(url, params=params) as response:
                        logger.debug(
                            "FMP profile request: %s, status=%d",
                            symbol,
                            response.status,
                        )
                        response.raise_for_status()
                        data = await response.json()

                        if isinstance(data, list) and data:
                            parsed = self._parse_profile_response(data)
                            results.update(parsed)
                        break  # Success, move to next symbol

                except aiohttp.ClientError as e:
                    last_error = e
                    if attempt < self._config.max_retries - 1:
                        wait_time = 2**attempt
                        logger.debug(
                            "FMP request for %s failed (attempt %d/%d), retrying in %ds: %s",
                            symbol,
                            attempt + 1,
                            self._config.max_retries,
                            wait_time,
                            e,
                        )
                        await asyncio.sleep(wait_time)

            if last_error and symbol not in results:
                logger.debug("Failed to fetch profile for %s: %s", symbol, last_error)

            # Rate limiting between individual requests
            await asyncio.sleep(0.25)

        return results

    def _parse_profile_response(
        self, data: list[dict]
    ) -> dict[str, SymbolReferenceData]:
        """Parse FMP company profile response.

        Args:
            data: List of profile dictionaries from FMP API.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
        """
        results: dict[str, SymbolReferenceData] = {}

        for item in data:
            try:
                symbol = item.get("symbol")
                if not symbol:
                    continue

                exchange = item.get("exchange")
                is_otc = self._is_otc_exchange(exchange)

                results[symbol] = SymbolReferenceData(
                    symbol=symbol,
                    sector=item.get("sector") or None,
                    industry=item.get("industry") or None,
                    market_cap=self._safe_float(item.get("marketCap")),
                    exchange=exchange,
                    prev_close=self._safe_float(item.get("price")),
                    avg_volume=self._safe_float(item.get("averageVolume")),
                    is_otc=is_otc,
                )

            except (TypeError, ValueError) as e:
                logger.debug("Failed to parse profile item: %s - %s", item, e)

        return results

    def _is_otc_exchange(self, exchange: str | None) -> bool:
        """Check if exchange indicates OTC trading.

        Args:
            exchange: Exchange short name from FMP.

        Returns:
            True if the exchange is an OTC market.
        """
        if not exchange:
            return False
        return exchange.upper() in self._OTC_EXCHANGES

    @staticmethod
    def _safe_float(value: object) -> float | None:
        """Safely convert value to float.

        Args:
            value: Value to convert.

        Returns:
            Float value or None if conversion fails.
        """
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    async def fetch_float_data(self, symbols: list[str]) -> dict[str, float]:
        """Fetch share float data for symbols.

        FMP Share Float Endpoint:
            GET /api/v4/shares_float?symbol={sym}&apikey=KEY

        Note: This endpoint may not support batching, so symbols are
        fetched sequentially with rate limiting.

        Args:
            symbols: List of stock symbols to fetch.

        Returns:
            Dictionary mapping symbol to float shares.
            Returns empty dict on API failure (graceful degradation).
        """
        if not symbols:
            return {}

        if self._api_key is None:
            logger.warning("FMPReferenceClient not started - cannot fetch float data")
            return {}

        results: dict[str, float] = {}

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._config.request_timeout_seconds)
        ) as session:
            for symbol in symbols:
                try:
                    float_shares = await self._fetch_single_float(session, symbol)
                    if float_shares is not None:
                        results[symbol] = float_shares
                except Exception as e:
                    logger.debug("Failed to fetch float for %s: %s", symbol, e)
                    # Continue with other symbols

                # Rate limiting between requests
                await asyncio.sleep(0.25)

        logger.debug("Fetched float data for %d/%d symbols", len(results), len(symbols))
        return results

    async def _fetch_single_float(
        self, session: aiohttp.ClientSession, symbol: str
    ) -> float | None:
        """Fetch float data for a single symbol.

        Args:
            session: aiohttp client session.
            symbol: Stock symbol.

        Returns:
            Float shares or None if not available.
        """
        # v4 API endpoint for share float
        url = f"{self._config.base_url}/shares-float"
        params = {"symbol": symbol, "apikey": self._api_key}

        async with session.get(url, params=params) as response:
            logger.debug("FMP float request for %s: status=%d", symbol, response.status)
            if response.status != 200:
                return None

            data = await response.json()
            if not data or not isinstance(data, list) or len(data) == 0:
                return None

            return self._safe_float(data[0].get("floatShares"))

    async def build_reference_cache(
        self, symbols: list[str]
    ) -> dict[str, SymbolReferenceData]:
        """Build complete reference cache for symbols.

        Orchestrates fetching company profiles and share float data,
        merges the results, and stores them in the internal cache.

        Args:
            symbols: List of stock symbols to cache.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
        """
        import time

        start_time = time.monotonic()

        logger.info("Building reference cache for %d symbols", len(symbols))

        # Fetch company profiles (batch)
        profile_data = await self.fetch_reference_data(symbols)

        # Fetch float data (sequential, only for symbols we got profiles for)
        successful_symbols = list(profile_data.keys())
        float_data = await self.fetch_float_data(successful_symbols)

        # Merge float data into profile data
        for symbol, float_shares in float_data.items():
            if symbol in profile_data:
                # Create new instance with float_shares set
                existing = profile_data[symbol]
                profile_data[symbol] = SymbolReferenceData(
                    symbol=existing.symbol,
                    sector=existing.sector,
                    industry=existing.industry,
                    market_cap=existing.market_cap,
                    float_shares=float_shares,
                    exchange=existing.exchange,
                    prev_close=existing.prev_close,
                    avg_volume=existing.avg_volume,
                    is_otc=existing.is_otc,
                    fetched_at=existing.fetched_at,
                )

        # Update cache
        self._cache = profile_data
        self._cache_built_at = datetime.now(ZoneInfo("UTC"))

        elapsed = time.monotonic() - start_time
        failed_count = len(symbols) - len(profile_data)

        logger.info(
            "Reference cache built: %d successful, %d failed, %.2fs elapsed",
            len(profile_data),
            failed_count,
            elapsed,
        )

        return profile_data

    def get_cached(self, symbol: str) -> SymbolReferenceData | None:
        """Get cached reference data for a symbol.

        Args:
            symbol: Stock symbol to look up.

        Returns:
            SymbolReferenceData if cached, None otherwise.
        """
        return self._cache.get(symbol)

    def is_cache_fresh(self) -> bool:
        """Check if the cache is still within TTL.

        Returns:
            True if cache was built within cache_ttl_hours, False otherwise.
        """
        if self._cache_built_at is None:
            return False

        age_hours = self.cache_age_minutes / 60
        return age_hours < self._config.cache_ttl_hours

    @property
    def cache_age_minutes(self) -> float:
        """Get the age of the cache in minutes.

        Returns:
            Age in minutes, or infinity if cache was never built.
        """
        if self._cache_built_at is None:
            return float("inf")

        now = datetime.now(ZoneInfo("UTC"))
        delta = now - self._cache_built_at
        return delta.total_seconds() / 60

    @property
    def cached_symbol_count(self) -> int:
        """Get the number of symbols in the cache.

        Returns:
            Number of cached symbols.
        """
        return len(self._cache)
