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
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
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

    def to_dict(self, cached_at: datetime | None = None) -> dict[str, Any]:
        """Serialize to dictionary for JSON caching.

        Args:
            cached_at: Timestamp when this entry is being cached.
                If None, uses current UTC time.

        Returns:
            Dictionary with all fields plus cached_at timestamp.
        """
        if cached_at is None:
            cached_at = datetime.now(ZoneInfo("UTC"))

        return {
            "symbol": self.symbol,
            "sector": self.sector,
            "industry": self.industry,
            "market_cap": self.market_cap,
            "float_shares": self.float_shares,
            "exchange": self.exchange,
            "prev_close": self.prev_close,
            "avg_volume": self.avg_volume,
            "is_otc": self.is_otc,
            "fetched_at": self.fetched_at.isoformat(),
            "cached_at": cached_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> tuple[SymbolReferenceData, str]:
        """Reconstruct from dictionary loaded from cache.

        Args:
            data: Dictionary with serialized fields.

        Returns:
            Tuple of (SymbolReferenceData, cached_at ISO string).
            The cached_at string is returned separately as cache metadata.
        """
        fetched_at_str = data.get("fetched_at")
        if fetched_at_str:
            fetched_at = datetime.fromisoformat(fetched_at_str)
        else:
            fetched_at = datetime.now(ZoneInfo("UTC"))

        cached_at = data.get("cached_at", datetime.now(ZoneInfo("UTC")).isoformat())

        return (
            cls(
                symbol=data["symbol"],
                sector=data.get("sector"),
                industry=data.get("industry"),
                market_cap=data.get("market_cap"),
                float_shares=data.get("float_shares"),
                exchange=data.get("exchange"),
                prev_close=data.get("prev_close"),
                avg_volume=data.get("avg_volume"),
                is_otc=data.get("is_otc", False),
                fetched_at=fetched_at,
            ),
            cached_at,
        )


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
        cache_file: Path to the file-based cache JSON file.
        cache_max_age_hours: Maximum age for cached entries before considered stale.
    """

    base_url: str = "https://financialmodelingprep.com/stable"
    api_key_env_var: str = "FMP_API_KEY"
    batch_size: int = 50
    cache_ttl_hours: int = 24
    max_retries: int = 3
    request_timeout_seconds: float = 30.0
    cache_file: str = "data/reference_cache.json"
    cache_max_age_hours: int = 24


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
        self._cached_at_timestamps: dict[str, str] = {}

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

        # Canary test: validate API schema with AAPL profile
        await self._run_canary_test()

    async def _run_canary_test(self) -> None:
        """Run canary test to validate FMP API schema.

        Fetches profile for AAPL and verifies expected keys are present.
        Logs INFO on success, WARNING on failure. Non-blocking — does not raise.
        """
        required_keys = {"symbol", "companyName", "marketCap", "price"}

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._config.request_timeout_seconds)
            ) as session:
                result = await self._fetch_single_profile_with_retry(session, "AAPL")

                if result is None:
                    logger.warning(
                        "FMP canary test failed — no data returned for AAPL"
                    )
                    return

                # Re-fetch raw response to check for required keys
                url = f"{self._config.base_url}/profile"
                params = {"symbol": "AAPL", "apikey": self._api_key}

                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.warning(
                            "FMP canary test failed — HTTP %d for AAPL profile",
                            response.status,
                        )
                        return

                    data = await response.json()
                    if not isinstance(data, list) or not data:
                        logger.warning(
                            "FMP canary test failed — unexpected response format"
                        )
                        return

                    profile = data[0]
                    missing_keys = required_keys - set(profile.keys())

                    if missing_keys:
                        logger.warning(
                            "FMP canary test failed — missing keys: %s",
                            sorted(missing_keys),
                        )
                        return

                    logger.info("FMP canary test passed — API schema validated")

        except aiohttp.ClientError as e:
            logger.warning("FMP canary test failed — network error: %s", e)
        except TimeoutError:
            logger.warning("FMP canary test failed — request timeout")
        except Exception as e:
            logger.warning("FMP canary test failed — unexpected error: %s", e)

    async def stop(self) -> None:
        """Clean up client resources."""
        self._api_key = None
        logger.info("FMPReferenceClient stopped")

    async def fetch_stock_list(self) -> list[str]:
        """Fetch complete stock list from FMP.

        Calls the FMP stable stock-list endpoint to get all available symbols.
        This is the starting point for Universe Manager's full-universe mode.

        FMP Stock List Endpoint:
            GET /stable/stock-list?apikey=KEY

        Returns:
            List of symbol strings. Empty list on failure.
        """
        if self._api_key is None:
            logger.error("FMPReferenceClient not started - call start() first")
            return []

        url = f"{self._config.base_url}/stock-list"
        params = {"apikey": self._api_key}

        try:
            async with aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self._config.request_timeout_seconds)
            ) as session:
                async with session.get(url, params=params) as response:
                    if response.status != 200:
                        logger.error(
                            "FMP stock-list request failed: status=%d",
                            response.status,
                        )
                        return []

                    data = await response.json()

                    if not isinstance(data, list):
                        logger.error("FMP stock-list returned invalid data type")
                        return []

                    # Extract symbol field from each object
                    symbols = [
                        item.get("symbol")
                        for item in data
                        if isinstance(item, dict) and item.get("symbol")
                    ]

                    logger.info("Fetched %d symbols from FMP stock-list", len(symbols))
                    return symbols

        except aiohttp.ClientError as e:
            logger.error("FMP stock-list network error: %s", e)
            return []
        except Exception as e:
            logger.error("FMP stock-list unexpected error: %s", e)
            return []

    async def fetch_reference_data(
        self, symbols: list[str]
    ) -> dict[str, SymbolReferenceData]:
        """Fetch company profile data for symbols with async concurrency.

        Uses concurrent requests with rate limiting to efficiently fetch
        profile data for large symbol lists (up to ~8,000). Handles partial
        failures gracefully - failed symbols are logged but don't prevent
        other symbols from being processed.

        FMP Stable Profile Endpoint:
            GET /stable/profile?symbol={sym}&apikey=KEY

        Rate limiting strategy:
            - Semaphore limits to 5 concurrent requests
            - 0.2s minimum spacing per call (well under 300/min)
            - Exponential backoff retry on transient errors (429, 5xx)

        Progress logging every 500 symbols shows:
            - Completed count / total (percentage)
            - Succeeded vs failed counts
            - Elapsed time

        Args:
            symbols: List of stock symbols to fetch.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
            Symbols that failed to fetch are not included (fail-closed, DEC-277).
        """
        import time

        if not symbols:
            return {}

        if self._api_key is None:
            logger.error("FMPReferenceClient not started - call start() first")
            return {}

        total = len(symbols)
        logger.info("Starting reference data fetch for %d symbols", total)

        # Tracking counters
        results: dict[str, SymbolReferenceData] = {}
        succeeded = 0
        failed = 0
        processed = 0
        start_time = time.monotonic()

        # Semaphore for concurrent request limiting
        semaphore = asyncio.Semaphore(5)

        # Lock for thread-safe counter updates
        counter_lock = asyncio.Lock()

        async def fetch_single(
            session: aiohttp.ClientSession,
            symbol: str,
        ) -> SymbolReferenceData | None:
            """Fetch profile for a single symbol with rate limiting and retries."""
            nonlocal succeeded, failed, processed

            async with semaphore:
                # Rate limiting: 0.2s minimum spacing
                await asyncio.sleep(0.2)

                result = await self._fetch_single_profile_with_retry(session, symbol)

                # Update counters
                async with counter_lock:
                    processed += 1
                    if result is not None:
                        succeeded += 1
                    else:
                        failed += 1

                    # Progress logging every 500 symbols
                    if processed % 500 == 0 or processed == total:
                        elapsed = time.monotonic() - start_time
                        pct = (processed / total) * 100
                        mins = int(elapsed // 60)
                        secs = int(elapsed % 60)
                        logger.info(
                            "Fetching reference data: %d/%d (%.0f%%) — "
                            "%d succeeded, %d failed [%dm %ds elapsed]",
                            processed,
                            total,
                            pct,
                            succeeded,
                            failed,
                            mins,
                            secs,
                        )

                return result

        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self._config.request_timeout_seconds)
        ) as session:
            # Create tasks for all symbols
            tasks = [fetch_single(session, sym) for sym in symbols]

            # Gather results (exceptions are returned, not raised)
            fetched = await asyncio.gather(*tasks, return_exceptions=True)

            # Collect successful results
            for sym, result in zip(symbols, fetched):
                if isinstance(result, SymbolReferenceData):
                    results[sym] = result

        # Final summary
        elapsed = time.monotonic() - start_time
        mins = int(elapsed // 60)
        secs = int(elapsed % 60)
        logger.info(
            "Reference data fetch complete: %d/%d succeeded in %dm %ds (%d failed)",
            len(results),
            total,
            mins,
            secs,
            total - len(results),
        )

        return results

    async def _fetch_single_profile_with_retry(
        self, session: aiohttp.ClientSession, symbol: str
    ) -> SymbolReferenceData | None:
        """Fetch profile for a single symbol with retry logic.

        Retries on transient errors (HTTP 429, 5xx, network timeout) with
        exponential backoff (2s, 4s, 8s). Non-retryable errors (4xx other
        than 429) fail immediately.

        Args:
            session: aiohttp client session.
            symbol: Stock symbol to fetch.

        Returns:
            SymbolReferenceData if successful, None on failure.
        """
        url = f"{self._config.base_url}/profile"
        params = {"symbol": symbol, "apikey": self._api_key}

        for attempt in range(self._config.max_retries):
            try:
                async with session.get(url, params=params) as response:
                    status = response.status

                    # Success
                    if status == 200:
                        data = await response.json()
                        if isinstance(data, list) and data:
                            parsed = self._parse_profile_response(data)
                            return parsed.get(symbol)
                        return None

                    # Transient errors: 429 (rate limit) or 5xx (server error)
                    if status == 429 or status >= 500:
                        if attempt < self._config.max_retries - 1:
                            wait_time = 2 ** (attempt + 1)  # 2s, 4s, 8s
                            logger.debug(
                                "FMP %d for %s (attempt %d/%d), retrying in %ds",
                                status,
                                symbol,
                                attempt + 1,
                                self._config.max_retries,
                                wait_time,
                            )
                            await asyncio.sleep(wait_time)
                            continue

                    # Non-retryable 4xx errors (except 429) — fail immediately
                    if 400 <= status < 500:
                        logger.debug(
                            "FMP %d for %s — non-retryable, skipping",
                            status,
                            symbol,
                        )
                        return None

            except asyncio.TimeoutError:
                # Network timeout — retryable
                if attempt < self._config.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.debug(
                        "FMP timeout for %s (attempt %d/%d), retrying in %ds",
                        symbol,
                        attempt + 1,
                        self._config.max_retries,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

            except aiohttp.ClientError as e:
                # Network error — retryable
                if attempt < self._config.max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    logger.debug(
                        "FMP network error for %s (attempt %d/%d): %s, retrying in %ds",
                        symbol,
                        attempt + 1,
                        self._config.max_retries,
                        e,
                        wait_time,
                    )
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted
        logger.warning("Failed to fetch profile for %s after %d attempts", symbol, self._config.max_retries)
        return None

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

    def save_cache(self) -> None:
        """Save the internal reference cache to a JSON file.

        Serializes the internal _cache dict to JSON format with per-symbol
        cached_at timestamps. Uses atomic write (temp file + os.replace)
        to prevent corruption.

        Creates parent directories if they don't exist.
        Logs INFO with file path and symbol count on success.
        """
        cache_path = Path(self._config.cache_file)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Serialize cache with current timestamp as cached_at
        cached_at = datetime.now(ZoneInfo("UTC"))
        serialized: dict[str, dict[str, Any]] = {}

        for symbol, data in self._cache.items():
            serialized[symbol] = data.to_dict(cached_at=cached_at)

        # Atomic write: write to temp file, then replace
        temp_path = cache_path.with_suffix(".json.tmp")

        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)

            os.replace(temp_path, cache_path)

            logger.info(
                "Reference cache saved: %d symbols to %s",
                len(serialized),
                cache_path,
            )
        except OSError as e:
            logger.error("Failed to save reference cache: %s", e)
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()

    def load_cache(self) -> dict[str, SymbolReferenceData]:
        """Load reference cache from JSON file.

        Reads the cache file and reconstructs SymbolReferenceData objects.
        Stores cached_at timestamps internally for staleness checking.

        Returns:
            Dictionary mapping symbol to SymbolReferenceData.
            Returns empty dict if file doesn't exist or is corrupt.
        """
        cache_path = Path(self._config.cache_file)

        # Initialize internal cached_at storage
        self._cached_at_timestamps: dict[str, str] = {}

        if not cache_path.exists():
            logger.info("No cache file found at %s", cache_path)
            return {}

        try:
            with open(cache_path, encoding="utf-8") as f:
                raw_data = json.load(f)

            if not isinstance(raw_data, dict):
                logger.warning("Cache file has invalid format (expected dict)")
                return {}

            result: dict[str, SymbolReferenceData] = {}

            for symbol, entry in raw_data.items():
                if not isinstance(entry, dict):
                    continue

                try:
                    data, cached_at = SymbolReferenceData.from_dict(entry)
                    result[symbol] = data
                    self._cached_at_timestamps[symbol] = cached_at
                except (KeyError, TypeError, ValueError) as e:
                    logger.debug("Failed to parse cache entry for %s: %s", symbol, e)
                    continue

            logger.info("Loaded %d symbols from cache file %s", len(result), cache_path)
            return result

        except json.JSONDecodeError as e:
            logger.warning("Cache file is corrupt (invalid JSON): %s", e)
            return {}
        except OSError as e:
            logger.warning("Failed to read cache file: %s", e)
            return {}

    def get_stale_symbols(
        self,
        cached: dict[str, SymbolReferenceData],
        all_symbols: list[str],
        max_age_hours: int,
    ) -> list[str]:
        """Identify symbols that need refreshing.

        Returns symbols that are either:
        - Not present in the cache
        - In the cache but older than max_age_hours

        Must be called after load_cache() which populates internal
        cached_at timestamps.

        Args:
            cached: Dictionary of cached symbol data (from load_cache).
            all_symbols: Complete list of symbols to check.
            max_age_hours: Maximum age in hours before data is stale.

        Returns:
            List of symbols that need refreshing.
        """
        now = datetime.now(ZoneInfo("UTC"))
        max_age_seconds = max_age_hours * 3600
        stale: list[str] = []

        for symbol in all_symbols:
            # Check if missing from cache
            if symbol not in cached:
                stale.append(symbol)
                continue

            # Check if older than max_age
            cached_at_str = self._cached_at_timestamps.get(symbol)
            if cached_at_str is None:
                # No cached_at timestamp means we can't verify age
                stale.append(symbol)
                continue

            try:
                cached_at = datetime.fromisoformat(cached_at_str)
                age_seconds = (now - cached_at).total_seconds()

                if age_seconds > max_age_seconds:
                    stale.append(symbol)
            except ValueError:
                # Invalid timestamp format
                stale.append(symbol)

        return stale
