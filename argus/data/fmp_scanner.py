"""Scanner using Financial Modeling Prep (FMP) data for gap-based candidate selection.

Implements the Scanner ABC using FMP's biggest-gainers, biggest-losers, and
most-actives REST endpoints (stable API). Provides pre-market scanning for
gap-up/gap-down stocks across the full US equity universe.

Sprint 21.7: FMP Scanner Integration.
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field

import aiohttp

from argus.core.events import WatchlistItem
from argus.data.scanner import Scanner
from argus.models.strategy import ScannerCriteria

logger = logging.getLogger(__name__)


@dataclass
class FMPScannerConfig:
    """Configuration for FMPScannerSource.

    Attributes:
        base_url: FMP API base URL (stable API).
        api_key_env_var: Environment variable name for the API key.
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.
        max_symbols_returned: Maximum candidates to return.
        fallback_symbols: Static symbol list used when FMP API fails.
    """

    base_url: str = "https://financialmodelingprep.com/stable"
    api_key_env_var: str = "FMP_API_KEY"
    min_price: float = 10.0
    max_price: float = 500.0
    # ``min_volume`` removed by FIX-16 (audit 2026-04-21, H2-S10): the field
    # was always ignored — current FMP endpoints do not return volume — but
    # appeared editable in scanner.yaml, misleading operators tuning a value
    # that had no runtime effect. Restore when an FMP volume-aware endpoint
    # (Premium screener, Sprint 23+) is integrated.
    max_symbols_returned: int = 15
    fallback_symbols: list[str] = field(default_factory=list)


class FMPScannerSource(Scanner):
    """Scanner using FMP for pre-market gap and activity scanning.

    Queries three FMP endpoints concurrently:
    - biggest-gainers: Stocks with largest positive % change
    - biggest-losers: Stocks with largest negative % change
    - most-actives: Stocks with highest trading activity

    Results are deduplicated (gainers/losers win over actives), filtered by
    price range, and sorted by absolute gap percentage.

    Falls back to a static symbol list if the FMP API is unavailable.
    """

    def __init__(self, config: FMPScannerConfig) -> None:
        """Initialize FMPScannerSource.

        Args:
            config: Scanner configuration.
        """
        self._config = config
        self._api_key: str | None = None

    async def start(self) -> None:
        """Initialize scanner resources.

        Reads the FMP API key from the environment.

        Raises:
            RuntimeError: If FMP API key is not found in environment.
        """
        self._api_key = os.getenv(self._config.api_key_env_var)
        if self._api_key is None:
            raise RuntimeError("FMP API key not found. Set FMP_API_KEY.")
        logger.info("FMPScannerSource started")

    async def stop(self) -> None:
        """Clean up scanner resources."""
        self._api_key = None
        logger.info("FMPScannerSource stopped")

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan for candidates using FMP biggest-gainers/losers/actives.

        Args:
            criteria_list: Scanner criteria from active strategies. Currently
                unused — FMP biggest-gainers / biggest-losers / most-actives
                endpoints are pre-filtered on the API side and do not accept
                ARGUS-level criteria. Strategy-specific filtering happens
                downstream at the UniverseManager routing layer.

                Tracked by DEF-032 (re-verified FIX-06 audit 2026-04-21,
                P1-C2-14): will be wired when the Premium FMP screener
                endpoint is integrated or when an FMP-volume-aware
                scanner source is added.

        Returns:
            List of WatchlistItems sorted by gap percentage descending.
        """
        logger.info("FMPScannerSource starting scan")

        try:
            candidates = await self._fetch_candidates()
            if candidates:
                logger.info(
                    "FMPScannerSource found %d candidates",
                    len(candidates),
                )
                return candidates
        except Exception as e:
            logger.warning(
                "FMP API error, falling back to static list: %s",
                e,
            )

        # Fallback on error or empty response
        fallback = await self._fallback_candidates()
        logger.info(
            "FMPScannerSource returning %d fallback candidates",
            len(fallback),
        )
        return fallback

    async def _fetch_candidates(self) -> list[WatchlistItem]:
        """Fetch candidates from FMP endpoints.

        Makes concurrent requests to biggest-gainers, biggest-losers, and
        most-actives endpoints. Deduplicates, filters, and sorts results.

        Returns:
            Filtered and sorted list of WatchlistItems.

        Raises:
            aiohttp.ClientError: On network or API errors.
        """
        async with aiohttp.ClientSession() as session:
            # Fetch all three endpoints concurrently
            gainers_task = self._fetch_endpoint(session, "biggest-gainers")
            losers_task = self._fetch_endpoint(session, "biggest-losers")
            actives_task = self._fetch_endpoint(session, "most-actives")

            gainers, losers, actives = await asyncio.gather(
                gainers_task, losers_task, actives_task
            )

        # Process and deduplicate
        seen_symbols: set[str] = set()
        candidates: list[WatchlistItem] = []

        # Gainers and losers take priority over actives
        for item_data in gainers:
            item = self._process_item(item_data, "gap_up")
            if item and item.symbol not in seen_symbols:
                seen_symbols.add(item.symbol)
                candidates.append(item)

        for item_data in losers:
            item = self._process_item(item_data, "gap_down")
            if item and item.symbol not in seen_symbols:
                seen_symbols.add(item.symbol)
                candidates.append(item)

        for item_data in actives:
            item = self._process_item(item_data, "high_volume")
            if item and item.symbol not in seen_symbols:
                seen_symbols.add(item.symbol)
                candidates.append(item)

        if not candidates:
            return []

        # Sort: gainers and losers (by abs gap_pct) first, then actives at end
        # Items with gap data (gap_up/gap_down) sorted by abs(gap_pct) desc
        # "high_volume" items have gap_pct=0 so naturally sort last
        candidates.sort(key=lambda x: abs(x.gap_pct), reverse=True)

        return candidates[: self._config.max_symbols_returned]

    async def _fetch_endpoint(
        self, session: aiohttp.ClientSession, endpoint: str
    ) -> list[dict]:
        """Fetch data from a single FMP endpoint.

        Args:
            session: aiohttp client session.
            endpoint: FMP endpoint name (biggest-gainers, biggest-losers, most-actives).

        Returns:
            List of item dictionaries from the endpoint.

        Raises:
            aiohttp.ClientError: On network errors.
        """
        url = f"{self._config.base_url}/{endpoint}?apikey={self._api_key}"
        async with session.get(url) as response:
            response.raise_for_status()
            return await response.json()

    def _process_item(
        self, item_data: dict, selection_type: str
    ) -> WatchlistItem | None:
        """Process a single item from FMP response.

        Applies price filters and creates WatchlistItem.

        Args:
            item_data: Raw item dictionary from FMP API.
            selection_type: One of "gap_up", "gap_down", or "high_volume".

        Returns:
            WatchlistItem if item passes filters, None otherwise.
        """
        try:
            symbol = item_data.get("symbol", "")
            price = float(item_data.get("price", 0))
            changes_pct = float(item_data.get("changesPercentage", 0))

            # Apply price filter
            if price < self._config.min_price or price > self._config.max_price:
                return None

            # Build selection reason
            if selection_type == "gap_up":
                selection_reason = f"gap_up_{abs(changes_pct):.1f}%"
                gap_pct = changes_pct / 100.0
            elif selection_type == "gap_down":
                selection_reason = f"gap_down_{abs(changes_pct):.1f}%"
                gap_pct = changes_pct / 100.0
            else:
                selection_reason = "high_volume"
                gap_pct = changes_pct / 100.0

            return WatchlistItem(
                symbol=symbol,
                gap_pct=gap_pct,
                scan_source="fmp",
                selection_reason=selection_reason,
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.debug("Failed to process FMP item: %s - %s", item_data, e)
            return None

    async def _fallback_candidates(self) -> list[WatchlistItem]:
        """Return fallback candidates from static symbol list.

        Returns:
            List of WatchlistItems from fallback_symbols config.
        """
        return [
            WatchlistItem(symbol=s, scan_source="fmp_fallback")
            for s in self._config.fallback_symbols[: self._config.max_symbols_returned]
        ]
