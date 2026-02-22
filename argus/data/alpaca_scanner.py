"""AlpacaScanner — live pre-market gap scanner using Alpaca snapshots.

Replaces StaticScanner for live trading. Scans a configurable universe
of symbols for gap percentage, volume, and price criteria matching
active strategies' requirements.

Uses Alpaca's StockHistoricalDataClient.get_stock_snapshot() for
batch snapshot retrieval.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Any

from argus.core.config import AlpacaConfig, AlpacaScannerConfig
from argus.core.events import WatchlistItem
from argus.data.scanner import Scanner
from argus.models.strategy import ScannerCriteria

if TYPE_CHECKING:
    from alpaca.data.historical import StockHistoricalDataClient

logger = logging.getLogger(__name__)


class AlpacaScanner(Scanner):
    """Live stock scanner using Alpaca's snapshot API.

    Scans a configured universe of symbols to find gap candidates
    matching the criteria from active strategies.
    """

    def __init__(
        self,
        config: AlpacaScannerConfig,
        alpaca_config: AlpacaConfig,
    ) -> None:
        """Initialize the scanner.

        Args:
            config: Scanner-specific configuration.
            alpaca_config: Alpaca API configuration.
        """
        self._config = config
        self._alpaca_config = alpaca_config
        self._client: StockHistoricalDataClient | None = None

    async def start(self) -> None:
        """Initialize the Alpaca data client."""
        from alpaca.data.historical import StockHistoricalDataClient

        # Get API keys from environment
        api_key = os.environ.get(self._alpaca_config.api_key_env)
        secret_key = os.environ.get(self._alpaca_config.secret_key_env)

        if not api_key or not secret_key:
            raise ConnectionError(
                f"Alpaca API keys not found in environment. "
                f"Expected {self._alpaca_config.api_key_env} and "
                f"{self._alpaca_config.secret_key_env}"
            )

        self._client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key,
        )
        logger.info(
            "AlpacaScanner started with %d universe symbols",
            len(self._config.universe_symbols),
        )

    async def stop(self) -> None:
        """Clean up client resources."""
        self._client = None
        logger.info("AlpacaScanner stopped")

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan universe using Alpaca snapshots, filter by criteria.

        Steps:
        1. Merge criteria from all active strategies (use widest ranges)
        2. Fetch snapshots for universe symbols
        3. Filter by merged criteria
        4. Sort by gap_pct descending
        5. Return top max_symbols_returned as WatchlistItems

        Args:
            criteria_list: Scanner criteria from each active strategy.

        Returns:
            Merged, filtered list of WatchlistItems.
        """
        if not self._client:
            logger.error("AlpacaScanner not started")
            return []

        if not self._config.universe_symbols:
            logger.warning("AlpacaScanner has empty universe")
            return []

        # Merge criteria: use the widest acceptable ranges
        merged = self._merge_criteria(criteria_list)

        # Fetch snapshots
        try:
            from alpaca.data.requests import StockSnapshotRequest

            request = StockSnapshotRequest(symbol_or_symbols=self._config.universe_symbols)
            snapshots = self._client.get_stock_snapshot(request)
        except Exception:
            logger.exception("Failed to fetch Alpaca snapshots")
            return []

        # Filter and build watchlist
        items: list[WatchlistItem] = []
        for symbol, snapshot in snapshots.items():
            item = self._evaluate_snapshot(symbol, snapshot, merged)
            if item is not None:
                items.append(item)

        # Sort by gap_pct descending (strongest gappers first)
        items.sort(key=lambda x: abs(x.gap_pct), reverse=True)

        # Cap results
        result = items[: self._config.max_symbols_returned]
        logger.info(
            "AlpacaScanner found %d candidates (returning %d)",
            len(items),
            len(result),
        )
        return result

    def _evaluate_snapshot(
        self, symbol: str, snapshot: Any, merged: ScannerCriteria
    ) -> WatchlistItem | None:
        """Evaluate a single snapshot against criteria.

        Args:
            symbol: The stock symbol.
            snapshot: Alpaca snapshot object.
            merged: Merged criteria from all strategies.

        Returns:
            WatchlistItem if passes filters, None otherwise.
        """
        try:
            daily_bar = snapshot.daily_bar
            prev_bar = snapshot.previous_daily_bar

            if daily_bar is None or prev_bar is None:
                return None
            if prev_bar.close is None or prev_bar.close <= 0:
                return None

            # Gap calculation
            open_price = daily_bar.open
            if open_price is None or open_price <= 0:
                # Pre-market: use latest trade as proxy
                if snapshot.latest_trade and snapshot.latest_trade.price:
                    open_price = snapshot.latest_trade.price
                else:
                    return None

            gap_pct = (open_price - prev_bar.close) / prev_bar.close

            # Price filter
            if open_price < self._config.min_price:
                return None
            if open_price > self._config.max_price:
                return None

            # Gap filter (from merged criteria)
            if merged.min_gap_pct is not None and gap_pct < merged.min_gap_pct:
                return None
            if merged.max_gap_pct is not None and gap_pct > merged.max_gap_pct:
                return None

            # Volume filter
            yesterday_volume = prev_bar.volume or 0
            if yesterday_volume < self._config.min_volume_yesterday:
                return None

            # Calculate premarket volume from daily bar
            premarket_volume = int(daily_bar.volume or 0)

            return WatchlistItem(
                symbol=symbol,
                gap_pct=gap_pct,
                premarket_volume=premarket_volume,
            )

        except (AttributeError, TypeError, ZeroDivisionError):
            logger.debug("Incomplete snapshot data for %s, skipping", symbol)
            return None

    def _merge_criteria(self, criteria_list: list[ScannerCriteria]) -> ScannerCriteria:
        """Merge criteria from multiple strategies using widest ranges.

        Takes the minimum of all min values and maximum of all max values
        so any symbol that ANY strategy wants gets through.

        Args:
            criteria_list: List of criteria from active strategies.

        Returns:
            Merged ScannerCriteria with widest acceptable ranges.
        """
        if not criteria_list:
            return ScannerCriteria()

        min_gap: float | None = None
        max_gap: float | None = None

        for c in criteria_list:
            if c.min_gap_pct is not None and (min_gap is None or c.min_gap_pct < min_gap):
                min_gap = c.min_gap_pct
            if c.max_gap_pct is not None and (max_gap is None or c.max_gap_pct > max_gap):
                max_gap = c.max_gap_pct

        return ScannerCriteria(
            min_gap_pct=min_gap,
            max_gap_pct=max_gap,
        )
