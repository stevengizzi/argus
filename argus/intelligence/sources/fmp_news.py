"""FMP News client for fetching stock news and press releases.

Fetches news from Financial Modeling Prep (FMP) API using the stock_news
and press-releases endpoints. Requires FMP API key (Starter plan or higher).

Sprint 23.5 Session 2 — DEC-164
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime
from zoneinfo import ZoneInfo

import aiohttp

from argus.intelligence.config import FMPNewsConfig
from argus.intelligence.models import CatalystRawItem, compute_headline_hash
from argus.intelligence.sources import CatalystSource

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class FMPNewsClient(CatalystSource):
    """Client for fetching news from FMP API.

    Implements CatalystSource ABC for FMP stock news and press releases.
    Deduplicates headlines within a batch using SHA-256 hashing.

    Features:
        - Stock news: Batched multi-ticker queries (up to 5 per call)
        - Press releases: Single-symbol queries
        - Deduplication: Filters duplicate headlines within batch
        - Graceful degradation: Returns empty list on API errors

    Usage:
        config = FMPNewsConfig()
        client = FMPNewsClient(config)
        await client.start()
        catalysts = await client.fetch_catalysts(["AAPL", "MSFT", "NVDA"])
        await client.stop()
    """

    _BASE_URL = "https://financialmodelingprep.com/api/v3"
    _BATCH_SIZE = 5  # Max tickers per stock_news call

    def __init__(self, config: FMPNewsConfig) -> None:
        """Initialize FMP News client.

        Args:
            config: FMP News configuration.
        """
        self._config = config
        self._session: aiohttp.ClientSession | None = None
        self._api_key: str | None = None
        self._disabled_for_cycle = False

    @property
    def source_name(self) -> str:
        """Return the source identifier."""
        return "fmp_news"

    async def start(self) -> None:
        """Initialize HTTP session and validate API key.

        Reads API key from environment. Does not raise on missing key -
        fetch_catalysts will return empty list instead.
        """
        self._api_key = os.getenv(self._config.api_key_env_var)
        if not self._api_key:
            logger.warning(
                "FMP API key not found (%s not set). "
                "FMP news will return empty results.",
                self._config.api_key_env_var,
            )

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30.0, sock_connect=10.0, sock_read=20.0),
        )
        self._disabled_for_cycle = False

        logger.info("FMPNewsClient started")

    async def stop(self) -> None:
        """Close HTTP session and clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._api_key = None
        logger.info("FMPNewsClient stopped")

    async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
        """Fetch news and press releases for the given symbols.

        Resets the circuit breaker at the start of each cycle. If a 403
        (plan restriction) is encountered, remaining symbols are skipped
        for this cycle only — the next call retries from scratch.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            List of CatalystRawItem from news and press releases.
        """
        if not self._session:
            logger.error("FMPNewsClient not started - call start() first")
            return []

        if not self._api_key:
            logger.debug("FMP API key not configured, returning empty")
            return []

        if not symbols:
            return []

        # Reset circuit breaker at start of each poll cycle
        self._disabled_for_cycle = False

        catalysts: list[CatalystRawItem] = []
        seen_hashes: set[str] = set()
        fetch_time = datetime.now(_ET)
        skipped_count = 0

        # Fetch stock news (batched)
        if "stock_news" in self._config.endpoints and not self._disabled_for_cycle:
            news = await self._fetch_stock_news(symbols, fetch_time)
            for item in news:
                h = compute_headline_hash(item.headline)
                if h not in seen_hashes:
                    seen_hashes.add(h)
                    catalysts.append(item)

        # Fetch press releases (per symbol)
        if "press_releases" in self._config.endpoints:
            for symbol in symbols:
                if self._disabled_for_cycle:
                    skipped_count += 1
                    continue
                releases = await self._fetch_press_releases(symbol, fetch_time)
                for item in releases:
                    h = compute_headline_hash(item.headline)
                    if h not in seen_hashes:
                        seen_hashes.add(h)
                        catalysts.append(item)

        if self._disabled_for_cycle and skipped_count > 0:
            logger.warning(
                "FMP news circuit breaker: skipped %d symbols after 403",
                skipped_count,
            )

        logger.debug(
            "Fetched %d catalysts from FMP news for %d symbols",
            len(catalysts),
            len(symbols),
        )
        return catalysts

    async def _fetch_stock_news(
        self,
        symbols: list[str],
        fetch_time: datetime,
    ) -> list[CatalystRawItem]:
        """Fetch stock news for multiple symbols in batches.

        Args:
            symbols: List of symbols to fetch.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            List of CatalystRawItem from stock news.
        """
        catalysts: list[CatalystRawItem] = []

        # Batch symbols in groups of 5
        for i in range(0, len(symbols), self._BATCH_SIZE):
            if self._disabled_for_cycle:
                break
            batch = symbols[i : i + self._BATCH_SIZE]
            tickers = ",".join(batch)

            url = f"{self._BASE_URL}/stock_news"
            params = {
                "tickers": tickers,
                "limit": 50,
                "apikey": self._api_key,
            }

            data = await self._make_request(url, params)
            if data is None:
                continue

            for item in data:
                catalyst = self._parse_news_item(item, fetch_time)
                if catalyst:
                    catalysts.append(catalyst)

        return catalysts

    async def _fetch_press_releases(
        self,
        symbol: str,
        fetch_time: datetime,
    ) -> list[CatalystRawItem]:
        """Fetch press releases for a single symbol.

        Args:
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            List of CatalystRawItem from press releases.
        """
        url = f"{self._BASE_URL}/press-releases/{symbol}"
        params = {
            "limit": 10,
            "apikey": self._api_key,
        }

        data = await self._make_request(url, params)
        if data is None:
            return []

        catalysts: list[CatalystRawItem] = []
        for item in data:
            catalyst = self._parse_press_release(item, symbol, fetch_time)
            if catalyst:
                catalysts.append(catalyst)

        return catalysts

    async def _make_request(
        self,
        url: str,
        params: dict[str, str | int],
        max_retries: int = 3,
    ) -> list[dict] | None:
        """Make HTTP GET request with retry logic.

        Implements exponential backoff on 429 (rate limit) errors.
        Disables source for cycle on 401/403 (auth errors).

        Args:
            url: URL to fetch.
            params: Query parameters.
            max_retries: Maximum retry attempts.

        Returns:
            Parsed JSON list or None on failure.
        """
        if not self._session:
            return None

        for attempt in range(max_retries):
            try:
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            return data
                        return None

                    if response.status == 401:
                        logger.error("FMP API key invalid (HTTP 401)")
                        self._disabled_for_cycle = True
                        return None

                    if response.status == 403:
                        logger.error(
                            "FMP API key invalid (HTTP 403) — disabling "
                            "FMP news source for this poll cycle"
                        )
                        self._disabled_for_cycle = True
                        return None

                    if response.status == 429:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** (attempt + 1)
                            logger.debug(
                                "FMP 429 rate limit, backing off %ds (attempt %d/%d)",
                                wait_time,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        logger.warning("FMP 429 after %d retries", max_retries)
                        return None

                    logger.warning("FMP HTTP %d for %s", response.status, url)
                    return None

            except TimeoutError:
                logger.warning("Timeout fetching %s", url)
                return None

            except aiohttp.ClientError as e:
                logger.warning("Network error fetching %s: %s", url, e)
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** (attempt + 1))
                    continue
                return None

        return None

    def _parse_news_item(
        self,
        item: dict,
        fetch_time: datetime,
    ) -> CatalystRawItem | None:
        """Parse a single stock news item.

        Args:
            item: Raw news item from FMP API.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            CatalystRawItem or None if parsing fails.
        """
        try:
            symbol = item.get("symbol", "")
            title = item.get("title", "")
            if not symbol or not title:
                return None

            # Parse publishedDate (ISO format)
            published_str = item.get("publishedDate", "")
            try:
                # FMP format: "2024-03-01 08:30:00"
                published_at = datetime.strptime(published_str, "%Y-%m-%d %H:%M:%S")
                published_at = published_at.replace(tzinfo=_ET)
            except ValueError:
                published_at = fetch_time

            return CatalystRawItem(
                headline=title,
                symbol=symbol,
                source="fmp_news",
                source_url=item.get("url"),
                published_at=published_at,
                fetched_at=fetch_time,
                metadata={
                    "site": item.get("site", ""),
                    "text": item.get("text", "")[:500] if item.get("text") else "",
                },
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.debug("Failed to parse FMP news item: %s", e)
            return None

    def _parse_press_release(
        self,
        item: dict,
        symbol: str,
        fetch_time: datetime,
    ) -> CatalystRawItem | None:
        """Parse a single press release item.

        Args:
            item: Raw press release from FMP API.
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            CatalystRawItem or None if parsing fails.
        """
        try:
            title = item.get("title", "")
            if not title:
                return None

            # Parse date (date only, no time)
            date_str = item.get("date", "")
            try:
                published_at = datetime.strptime(date_str, "%Y-%m-%d")
                published_at = published_at.replace(tzinfo=_ET)
            except ValueError:
                published_at = fetch_time

            return CatalystRawItem(
                headline=title,
                symbol=symbol,
                source="fmp_press_release",
                published_at=published_at,
                fetched_at=fetch_time,
                metadata={
                    "text": item.get("text", "")[:500] if item.get("text") else "",
                },
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.debug("Failed to parse FMP press release: %s", e)
            return None

    def reset_disabled_flag(self) -> None:
        """Reset the disabled-for-cycle flag (for testing)."""
        self._disabled_for_cycle = False
