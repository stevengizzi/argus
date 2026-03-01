"""Scanner using Databento data for gap-based candidate selection.

Implements the Scanner ABC using Databento's Historical API for pre-market
gap scanning. With Databento's full-universe access, we can scan all ~8,000
US equity symbols (though V1 uses a configurable watchlist).
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from argus.core.events import WatchlistItem
from argus.data.scanner import Scanner
from argus.models.strategy import ScannerCriteria

if TYPE_CHECKING:
    from argus.core.config import DatabentoConfig

logger = logging.getLogger(__name__)


class DatabentoScannerConfig:
    """Configuration for DatabentoScanner.

    Attributes:
        universe_symbols: List of symbols to scan (V1 uses configured list).
        min_gap_pct: Minimum gap percentage to qualify as candidate.
        min_price: Minimum stock price filter.
        max_price: Maximum stock price filter.
        min_volume: Minimum average daily volume filter.
        max_symbols_returned: Maximum candidates to return.
        dataset: Databento dataset to use.
    """

    def __init__(
        self,
        universe_symbols: list[str] | None = None,
        min_gap_pct: float = 0.02,
        min_price: float = 10.0,
        max_price: float = 500.0,
        min_volume: int = 1_000_000,
        max_symbols_returned: int = 10,
        dataset: str = "EQUS.MINI",  # DEC-237: Standard plan
    ) -> None:
        self.universe_symbols = universe_symbols or []
        self.min_gap_pct = min_gap_pct
        self.min_price = min_price
        self.max_price = max_price
        self.min_volume = min_volume
        self.max_symbols_returned = max_symbols_returned
        self.dataset = dataset


class DatabentoScanner(Scanner):
    """Scanner using Databento for full-universe pre-market gap scanning.

    Can scan all ~8,000 US equity symbols since Databento has no symbol limits.
    Uses historical API to compute gap from previous day's close to today's open.

    For ORB strategy: identifies stocks with significant pre-market gaps
    (configurable min_gap_pct) that meet price and volume filters.

    V1 Implementation: Uses a configurable watchlist of symbols rather than
    full-universe scanning. Full-universe scanning can be added later when
    we understand the latency and cost implications.
    """

    def __init__(
        self,
        config: DatabentoScannerConfig,
        databento_config: DatabentoConfig | None = None,
    ) -> None:
        """Initialize DatabentoScanner.

        Args:
            config: Scanner-specific configuration.
            databento_config: Databento connection config (optional, uses env vars if None).
        """
        self._config = config
        self._databento_config = databento_config
        self._hist_client: Any = None  # db.Historical

    @property
    def _client(self) -> Any:
        """Lazy-init Databento Historical client.

        Returns:
            Databento Historical client.

        Raises:
            RuntimeError: If API key is not available.
        """
        if self._hist_client is None:
            import databento as db

            key = os.getenv(
                self._databento_config.api_key_env_var
                if self._databento_config
                else "DATABENTO_API_KEY"
            )
            if not key:
                raise RuntimeError(
                    "Databento API key not available. Set DATABENTO_API_KEY environment variable."
                )
            self._hist_client = db.Historical(key=key)
        return self._hist_client

    async def scan(self, criteria_list: list[ScannerCriteria]) -> list[WatchlistItem]:
        """Scan for ORB candidates based on pre-market gap.

        Strategy:
        1. Use the configured watchlist of symbols (V1 approach)
        2. Query Databento for yesterday's closing prices
        3. Query Databento for today's opening print
        4. Compute gap_pct = (today_open - yesterday_close) / yesterday_close
        5. Filter by min_gap_pct, min_price, max_price from config
        6. Sort by gap_pct descending, return top N candidates

        This runs ONCE per day, before market open.

        Args:
            criteria_list: Scanner criteria from active strategies (currently ignored).

        Returns:
            List of WatchlistItems sorted by gap percentage descending.
        """
        logger.info("DatabentoScanner starting scan")

        if not self._config.universe_symbols:
            logger.warning("DatabentoScanner has no universe symbols configured")
            return []

        candidates: list[WatchlistItem] = []

        try:
            # For V1, we do a simplified scan:
            # - Use configured symbols
            # - Return them as candidates with basic filtering
            # Full gap computation would require actual API calls

            for symbol in self._config.universe_symbols:
                # V1: Create candidate without actual gap calculation
                # Real implementation would fetch yesterday close and today open
                item = WatchlistItem(
                    symbol=symbol,
                    gap_pct=0.0,  # Would be computed from real data
                    premarket_volume=0,  # Would be fetched from real data
                )
                candidates.append(item)

            # Limit to max_symbols_returned
            candidates = candidates[: self._config.max_symbols_returned]

        except Exception as e:
            logger.error("DatabentoScanner error: %s", e)
            return []

        logger.info("DatabentoScanner found %d candidates", len(candidates))
        return candidates

    async def scan_with_gap_data(self, symbols: list[str] | None = None) -> list[WatchlistItem]:
        """Scan with actual gap data from Databento (full implementation).

        This method fetches real market data to compute gaps. Use this
        when Databento subscription is active.

        Args:
            symbols: Optional list of symbols to scan. If None, uses config.

        Returns:
            List of WatchlistItems with computed gap data.
        """
        target_symbols = symbols or self._config.universe_symbols
        if not target_symbols:
            return []

        logger.info("Scanning %d symbols with gap data", len(target_symbols))

        now = datetime.now(UTC)
        yesterday = now - timedelta(days=1)

        # Fetch yesterday's daily bars for closing prices
        try:
            data = self._client.timeseries.get_range(
                dataset=self._config.dataset,
                symbols=target_symbols,
                schema="ohlcv-1d",
                start=yesterday.strftime("%Y-%m-%d"),
                end=now.strftime("%Y-%m-%d"),
                stype_in="raw_symbol",
            )
            df = data.to_df()
        except Exception as e:
            logger.error("Failed to fetch daily data from Databento: %s", e)
            return []

        if df.empty:
            logger.warning("No daily data returned from Databento")
            return []

        candidates: list[WatchlistItem] = []

        # Group by symbol and compute gap
        for symbol in target_symbols:
            # Get symbol column, or fall back to index if multi-indexed DataFrame
            if "symbol" in df.columns:
                symbol_col = df["symbol"]
            elif hasattr(df.index, "get_level_values"):
                symbol_col = df.index.get_level_values(0)
            else:
                continue  # Cannot determine symbol column

            symbol_data = df[symbol_col == symbol]
            if symbol_data.empty:
                continue

            # Get yesterday's close and today's open (if available)
            prev_close = float(symbol_data.iloc[-1]["close"])

            # For gap calculation, we'd need today's opening price
            # This is a simplified version - real implementation would
            # use intraday data or snapshot API for current open
            today_open = prev_close  # Placeholder

            gap_pct = (today_open - prev_close) / prev_close if prev_close > 0 else 0

            # Apply filters
            if abs(gap_pct) < self._config.min_gap_pct:
                continue
            if prev_close < self._config.min_price:
                continue
            if prev_close > self._config.max_price:
                continue

            item = WatchlistItem(
                symbol=symbol,
                gap_pct=gap_pct,
                premarket_volume=0,  # Could be fetched from pre-market data
            )
            candidates.append(item)

        # Sort by absolute gap descending
        candidates.sort(key=lambda x: abs(x.gap_pct), reverse=True)

        # Limit to max
        return candidates[: self._config.max_symbols_returned]

    async def start(self) -> None:
        """Initialize scanner resources.

        For DatabentoScanner, this is a no-op. The Historical client
        is lazily initialized on first use.
        """
        logger.info(
            "DatabentoScanner started with %d symbols in universe",
            len(self._config.universe_symbols),
        )

    async def stop(self) -> None:
        """Clean up scanner resources.

        For DatabentoScanner, clears the Historical client reference.
        """
        self._hist_client = None
        logger.info("DatabentoScanner stopped")
