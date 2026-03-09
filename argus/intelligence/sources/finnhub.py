"""Finnhub client for fetching company news and analyst recommendations.

Fetches news and recommendation data from Finnhub API. Requires Finnhub
API key (free tier provides 60 calls/min).

Sprint 23.5 Session 2 — DEC-164
"""

from __future__ import annotations

import asyncio
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import aiohttp

from argus.intelligence.config import FinnhubConfig
from argus.intelligence.models import CatalystRawItem
from argus.intelligence.sources import CatalystSource

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class FinnhubClient(CatalystSource):
    """Client for fetching news from Finnhub API.

    Implements CatalystSource ABC for Finnhub company news and analyst
    recommendation trends. Rate limited to 60 calls/min (free tier).

    Features:
        - Company news: Last 24 hours of news per symbol
        - Recommendation trends: Analyst rating changes
        - Rate limiting: 60 calls/min with token bucket

    Usage:
        config = FinnhubConfig()
        client = FinnhubClient(config)
        await client.start()
        catalysts = await client.fetch_catalysts(["AAPL", "MSFT"])
        await client.stop()
    """

    _BASE_URL = "https://finnhub.io/api/v1"

    def __init__(self, config: FinnhubConfig) -> None:
        """Initialize Finnhub client.

        Args:
            config: Finnhub configuration.
        """
        self._config = config
        self._session: aiohttp.ClientSession | None = None
        self._api_key: str | None = None
        self._disabled_for_cycle = False

        # Rate limiting: 60 calls/min = 1 call/second
        self._last_request_time: float = 0.0
        self._min_interval = 60.0 / config.rate_limit_per_minute

    @property
    def source_name(self) -> str:
        """Return the source identifier."""
        return "finnhub"

    async def start(self) -> None:
        """Initialize HTTP session and validate API key.

        Reads API key from environment. Does not raise on missing key -
        fetch_catalysts will return empty list instead.
        """
        self._api_key = os.getenv(self._config.api_key_env_var)
        if not self._api_key:
            logger.warning(
                "Finnhub API key not found (%s not set). "
                "Finnhub will return empty results.",
                self._config.api_key_env_var,
            )

        self._session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30.0),
        )
        self._disabled_for_cycle = False

        logger.info("FinnhubClient started")

    async def stop(self) -> None:
        """Close HTTP session and clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._api_key = None
        logger.info("FinnhubClient stopped")

    async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
        """Fetch news and recommendations for the given symbols.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            List of CatalystRawItem from news and recommendations.
        """
        if not self._session:
            logger.error("FinnhubClient not started - call start() first")
            return []

        if not self._api_key:
            logger.debug("Finnhub API key not configured, returning empty")
            return []

        if self._disabled_for_cycle:
            logger.debug("Finnhub disabled for this cycle (auth error)")
            return []

        if not symbols:
            return []

        catalysts: list[CatalystRawItem] = []
        fetch_time = datetime.now(_ET)

        for symbol in symbols:
            # Fetch company news (last 24 hours)
            news = await self._fetch_company_news(symbol, fetch_time)
            catalysts.extend(news)

            # Fetch recommendation trends
            recommendations = await self._fetch_recommendations(symbol, fetch_time)
            catalysts.extend(recommendations)

        logger.debug(
            "Fetched %d catalysts from Finnhub for %d symbols",
            len(catalysts),
            len(symbols),
        )
        return catalysts

    async def _fetch_company_news(
        self,
        symbol: str,
        fetch_time: datetime,
    ) -> list[CatalystRawItem]:
        """Fetch company news for a single symbol.

        Args:
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            List of CatalystRawItem from company news.
        """
        # Date range: last 24 hours
        now = datetime.now(_ET)
        from_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        to_date = now.strftime("%Y-%m-%d")

        url = f"{self._BASE_URL}/company-news"
        params = {
            "symbol": symbol,
            "from": from_date,
            "to": to_date,
            "token": self._api_key,
        }

        data = await self._make_rate_limited_request(url, params)
        if data is None:
            return []

        catalysts: list[CatalystRawItem] = []
        for item in data:
            catalyst = self._parse_news_item(item, symbol, fetch_time)
            if catalyst:
                catalysts.append(catalyst)

        return catalysts

    async def _fetch_recommendations(
        self,
        symbol: str,
        fetch_time: datetime,
    ) -> list[CatalystRawItem]:
        """Fetch analyst recommendation trends for a single symbol.

        Args:
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            List of CatalystRawItem from recommendation changes.
        """
        url = f"{self._BASE_URL}/stock/recommendation"
        params = {
            "symbol": symbol,
            "token": self._api_key,
        }

        data = await self._make_rate_limited_request(url, params)
        if data is None:
            return []

        catalysts: list[CatalystRawItem] = []
        for item in data:
            catalyst = self._parse_recommendation(item, symbol, fetch_time)
            if catalyst:
                catalysts.append(catalyst)

        return catalysts

    async def _make_rate_limited_request(
        self,
        url: str,
        params: dict[str, str | int],
        max_retries: int = 3,
    ) -> list[dict] | None:
        """Make HTTP GET request with rate limiting and retries.

        Implements rate limiting (60 calls/min) and exponential backoff
        on 429 errors. Disables source for cycle on 401 errors.

        Args:
            url: URL to fetch.
            params: Query parameters.
            max_retries: Maximum retry attempts.

        Returns:
            Parsed JSON list or None on failure.
        """
        if not self._session:
            return None

        # Rate limiting
        current_time = asyncio.get_event_loop().time()
        elapsed = current_time - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = asyncio.get_event_loop().time()

        for attempt in range(max_retries):
            try:
                async with self._session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if isinstance(data, list):
                            return data
                        return None

                    if response.status == 401:
                        logger.error("Finnhub API key invalid (HTTP 401)")
                        self._disabled_for_cycle = True
                        return None

                    if response.status == 403:
                        logger.error("Finnhub API access denied (HTTP 403)")
                        self._disabled_for_cycle = True
                        return None

                    if response.status == 429:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** (attempt + 1)
                            logger.debug(
                                "Finnhub 429 rate limit, backing off %ds (attempt %d/%d)",
                                wait_time,
                                attempt + 1,
                                max_retries,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        logger.warning("Finnhub 429 after %d retries", max_retries)
                        return None

                    logger.warning("Finnhub HTTP %d for %s", response.status, url)
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
        symbol: str,
        fetch_time: datetime,
    ) -> CatalystRawItem | None:
        """Parse a single company news item.

        Args:
            item: Raw news item from Finnhub API.
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            CatalystRawItem or None if parsing fails.
        """
        try:
            headline = item.get("headline", "")
            if not headline:
                return None

            # Parse datetime (Unix timestamp)
            timestamp = item.get("datetime", 0)
            try:
                published_at = datetime.fromtimestamp(timestamp, tz=_ET)
            except (ValueError, OSError):
                published_at = fetch_time

            return CatalystRawItem(
                headline=headline,
                symbol=symbol,
                source="finnhub",
                source_url=item.get("url"),
                published_at=published_at,
                fetched_at=fetch_time,
                metadata={
                    "category": item.get("category", ""),
                    "source": item.get("source", ""),
                    "summary": item.get("summary", "")[:500] if item.get("summary") else "",
                    "finnhub_id": item.get("id"),
                    "related": item.get("related", ""),
                },
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.debug("Failed to parse Finnhub news item: %s", e)
            return None

    def _parse_recommendation(
        self,
        item: dict,
        symbol: str,
        fetch_time: datetime,
    ) -> CatalystRawItem | None:
        """Parse a single recommendation trend item.

        Args:
            item: Raw recommendation from Finnhub API.
            symbol: Stock ticker symbol.
            fetch_time: Timestamp for fetched_at field.

        Returns:
            CatalystRawItem or None if parsing fails.
        """
        try:
            period = item.get("period", "")
            if not period:
                return None

            # Build headline from recommendation counts
            strong_buy = item.get("strongBuy", 0)
            buy = item.get("buy", 0)
            hold = item.get("hold", 0)
            sell = item.get("sell", 0)
            strong_sell = item.get("strongSell", 0)

            headline = (
                f"Analyst recommendations for {symbol}: "
                f"{strong_buy} Strong Buy, {buy} Buy, {hold} Hold, "
                f"{sell} Sell, {strong_sell} Strong Sell"
            )

            # Parse period date
            try:
                published_at = datetime.strptime(period, "%Y-%m-%d")
                published_at = published_at.replace(tzinfo=_ET)
            except ValueError:
                published_at = fetch_time

            return CatalystRawItem(
                headline=headline,
                symbol=symbol,
                source="finnhub",
                published_at=published_at,
                fetched_at=fetch_time,
                metadata={
                    "category": "analyst_recommendation",
                    "strong_buy": strong_buy,
                    "buy": buy,
                    "hold": hold,
                    "sell": sell,
                    "strong_sell": strong_sell,
                    "period": period,
                },
            )

        except (KeyError, TypeError, ValueError) as e:
            logger.debug("Failed to parse Finnhub recommendation: %s", e)
            return None

    def reset_disabled_flag(self) -> None:
        """Reset the disabled-for-cycle flag (for testing)."""
        self._disabled_for_cycle = False
