"""SEC EDGAR client for fetching SEC filings.

Fetches 8-K, Form 4, and other filings from the SEC EDGAR REST API.
No API key required, but SEC requires a User-Agent header with contact email.

Rate limited to 10 requests/second per SEC fair-access policy.

Sprint 23.5 Session 2 — DEC-164
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import aiohttp

from argus.intelligence.config import SECEdgarConfig
from argus.intelligence.models import CatalystRawItem
from argus.intelligence.sources import CatalystSource

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")


class SECEdgarClient(CatalystSource):
    """Client for fetching SEC filings from EDGAR.

    Implements CatalystSource ABC for SEC EDGAR data. Fetches recent
    filings (8-K, Form 4, etc.) and converts them to CatalystRawItem format.

    Features:
        - CIK mapping: Ticker → CIK lookup with 24-hour cache
        - Rate limiting: 10 requests/second per SEC policy
        - Retries: Exponential backoff on 403/rate limit errors

    Usage:
        config = SECEdgarConfig(user_agent_email="user@example.com")
        client = SECEdgarClient(config)
        await client.start()
        catalysts = await client.fetch_catalysts(["AAPL", "MSFT"])
        await client.stop()
    """

    # SEC EDGAR base URLs
    _TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
    _SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
    _FILING_URL = "https://www.sec.gov/Archives/edgar/data/{cik}/{accession}/{doc}"

    def __init__(self, config: SECEdgarConfig) -> None:
        """Initialize SEC EDGAR client.

        Args:
            config: SEC EDGAR configuration with user_agent_email and filing_types.
        """
        self._config = config
        self._session: aiohttp.ClientSession | None = None
        self._cik_map: dict[str, str] = {}
        self._cik_cache_time: datetime | None = None

        # Rate limiter: token bucket at 10 req/sec
        self._rate_semaphore = asyncio.Semaphore(10)
        self._last_request_time: float = 0.0

    @property
    def source_name(self) -> str:
        """Return the source identifier."""
        return "sec_edgar"

    async def start(self) -> None:
        """Initialize HTTP session and load CIK mapping.

        Creates aiohttp session with required User-Agent header.
        Pre-loads the ticker→CIK mapping for efficient lookups.

        Raises:
            ValueError: If user_agent_email is empty or whitespace-only.
        """
        if not self._config.user_agent_email.strip():
            raise ValueError(
                "SEC EDGAR source enabled but user_agent_email is empty. "
                "Set catalyst.sources.sec_edgar.user_agent_email in config."
            )

        user_agent = f"ARGUS Trading System ({self._config.user_agent_email})"
        headers = {"User-Agent": user_agent}

        self._session = aiohttp.ClientSession(
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30.0, sock_connect=10.0, sock_read=20.0),
        )

        # Pre-load CIK mapping
        await self._refresh_cik_map()

        logger.info(
            "SECEdgarClient started with %d ticker mappings",
            len(self._cik_map),
        )

    async def stop(self) -> None:
        """Close HTTP session and clean up resources."""
        if self._session:
            await self._session.close()
            self._session = None
        self._cik_map.clear()
        logger.info("SECEdgarClient stopped")

    async def fetch_catalysts(self, symbols: list[str]) -> list[CatalystRawItem]:
        """Fetch recent SEC filings for the given symbols.

        Args:
            symbols: List of stock ticker symbols.

        Returns:
            List of CatalystRawItem for matching filings.
        """
        if not self._session:
            logger.error("SECEdgarClient not started - call start() first")
            return []

        if not symbols:
            return []

        # Refresh CIK map if stale (>24 hours)
        await self._ensure_cik_map_fresh()

        catalysts: list[CatalystRawItem] = []
        fetch_time = datetime.now(_ET)

        for symbol in symbols:
            cik = self._cik_map.get(symbol.upper())
            if not cik:
                logger.debug("No CIK mapping for symbol %s, skipping", symbol)
                continue

            try:
                filings = await self._fetch_filings(cik, symbol.upper())
                for filing in filings:
                    filing.fetched_at = fetch_time
                    catalysts.append(filing)
            except Exception as e:
                logger.warning("Failed to fetch filings for %s: %s", symbol, e)

        logger.debug(
            "Fetched %d catalysts from SEC EDGAR for %d symbols",
            len(catalysts),
            len(symbols),
        )
        return catalysts

    async def _refresh_cik_map(self) -> None:
        """Fetch and parse the SEC company tickers JSON.

        Populates self._cik_map with ticker → CIK (zero-padded to 10 digits).
        """
        if not self._session:
            return

        try:
            async with self._session.get(self._TICKERS_URL) as response:
                if response.status != 200:
                    logger.error(
                        "Failed to fetch SEC company tickers: status=%d",
                        response.status,
                    )
                    return

                data = await response.json()

                # Format: {"0": {"cik_str": "320193", "ticker": "AAPL", ...}, ...}
                self._cik_map.clear()
                for entry in data.values():
                    ticker = entry.get("ticker", "").upper()
                    cik_str = str(entry.get("cik_str", ""))
                    if ticker and cik_str:
                        # Zero-pad CIK to 10 digits
                        self._cik_map[ticker] = cik_str.zfill(10)

                self._cik_cache_time = datetime.now(_ET)
                logger.info(
                    "Loaded %d ticker→CIK mappings from SEC",
                    len(self._cik_map),
                )

        except aiohttp.ClientError as e:
            logger.error("Network error fetching SEC tickers: %s", e)
        except Exception as e:
            logger.error("Error parsing SEC tickers response: %s", e)

    async def _ensure_cik_map_fresh(self) -> None:
        """Refresh CIK map if older than 24 hours."""
        if self._cik_cache_time is None:
            await self._refresh_cik_map()
            return

        age = datetime.now(_ET) - self._cik_cache_time
        if age > timedelta(hours=24):
            logger.info("CIK map stale (%.1f hours), refreshing", age.total_seconds() / 3600)
            await self._refresh_cik_map()

    async def _fetch_filings(self, cik: str, symbol: str) -> list[CatalystRawItem]:
        """Fetch recent filings for a single CIK.

        Args:
            cik: Zero-padded 10-digit CIK.
            symbol: Stock ticker symbol.

        Returns:
            List of CatalystRawItem for filtered filings.
        """
        url = self._SUBMISSIONS_URL.format(cik=cik)
        response_data = await self._make_rate_limited_request(url)
        if response_data is None:
            return []

        return self._parse_filings(response_data, cik, symbol)

    async def _make_rate_limited_request(
        self,
        url: str,
        max_retries: int = 3,
    ) -> dict[str, Any] | None:
        """Make a rate-limited HTTP GET request with retries.

        Implements SEC fair-access rate limiting (10 req/sec) with
        exponential backoff on 403 errors.

        Args:
            url: URL to fetch.
            max_retries: Maximum retry attempts.

        Returns:
            Parsed JSON response or None on failure.
        """
        if not self._session:
            return None

        for attempt in range(max_retries):
            # Rate limiting: ensure minimum 0.1s between requests
            async with self._rate_semaphore:
                current_time = asyncio.get_event_loop().time()
                min_interval = 1.0 / self._config.rate_limit_per_second
                elapsed = current_time - self._last_request_time
                if elapsed < min_interval:
                    await asyncio.sleep(min_interval - elapsed)
                self._last_request_time = asyncio.get_event_loop().time()

                try:
                    async with self._session.get(url) as response:
                        if response.status == 200:
                            return await response.json()

                        if response.status == 403:
                            # Rate limited - back off
                            if attempt < max_retries - 1:
                                wait_time = 2 ** (attempt + 1)
                                logger.debug(
                                    "SEC 403 for %s (attempt %d/%d), "
                                    "backing off %ds",
                                    url,
                                    attempt + 1,
                                    max_retries,
                                    wait_time,
                                )
                                await asyncio.sleep(wait_time)
                                continue
                            logger.warning("SEC 403 for %s after %d retries", url, max_retries)
                            return None

                        if response.status == 404:
                            logger.debug("SEC 404 - CIK not found: %s", url)
                            return None

                        logger.warning("SEC HTTP %d for %s", response.status, url)
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

    def _parse_filings(
        self,
        data: dict[str, Any],
        cik: str,
        symbol: str,
    ) -> list[CatalystRawItem]:
        """Parse SEC submissions JSON into CatalystRawItem list.

        Filters by filing_types from config and extracts relevant fields.

        Args:
            data: Raw SEC submissions JSON.
            cik: CIK (zero-padded).
            symbol: Stock ticker symbol.

        Returns:
            List of CatalystRawItem for matching filing types.
        """
        catalysts: list[CatalystRawItem] = []

        filings = data.get("filings", {}).get("recent", {})
        if not filings:
            return []

        # Extract parallel arrays
        forms = filings.get("form", [])
        filing_dates = filings.get("filingDate", [])
        accession_numbers = filings.get("accessionNumber", [])
        primary_docs = filings.get("primaryDocument", [])
        descriptions = filings.get("primaryDocDescription", [])

        # Items array for 8-K (if present)
        items = filings.get("items", [])

        allowed_forms = set(self._config.filing_types)

        for i, form in enumerate(forms):
            if form not in allowed_forms:
                continue

            if i >= len(filing_dates) or i >= len(accession_numbers):
                continue

            filing_date_str = filing_dates[i]
            accession = accession_numbers[i]
            primary_doc = primary_docs[i] if i < len(primary_docs) else ""
            description = descriptions[i] if i < len(descriptions) else ""

            # Parse filing date
            try:
                published_at = datetime.strptime(filing_date_str, "%Y-%m-%d")
                published_at = published_at.replace(tzinfo=_ET)
            except ValueError:
                published_at = datetime.now(_ET)

            # Build headline
            if form == "4":
                headline = f"SEC Form 4 (Insider Transaction) filed by {symbol}"
            elif form == "8-K":
                item_str = items[i] if i < len(items) and items[i] else ""
                if item_str:
                    headline = f"SEC 8-K ({item_str}): {description}"
                else:
                    if description:
                        headline = f"SEC 8-K filed: {description}"
                    else:
                        headline = f"SEC 8-K filed by {symbol}"
            else:
                headline = f"SEC {form} filed by {symbol}"

            # Build URL
            accession_nodash = accession.replace("-", "")
            cik_nodash = cik.lstrip("0") or "0"
            source_url = self._FILING_URL.format(
                cik=cik_nodash,
                accession=accession_nodash,
                doc=primary_doc,
            )

            # Build metadata
            metadata: dict[str, Any] = {
                "accession_number": accession,
                "cik": cik,
            }
            if form == "8-K" and i < len(items) and items[i]:
                metadata["items"] = items[i].split(",")

            catalysts.append(
                CatalystRawItem(
                    headline=headline,
                    symbol=symbol,
                    source="sec_edgar",
                    source_url=source_url,
                    filing_type=form,
                    published_at=published_at,
                    fetched_at=datetime.now(_ET),  # Will be overwritten
                    metadata=metadata,
                )
            )

        return catalysts

    def get_cik(self, symbol: str) -> str | None:
        """Get CIK for a symbol (for testing).

        Args:
            symbol: Stock ticker symbol.

        Returns:
            Zero-padded CIK or None if not found.
        """
        return self._cik_map.get(symbol.upper())
