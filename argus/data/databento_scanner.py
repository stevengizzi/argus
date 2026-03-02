"""Scanner using Databento data for gap-based candidate selection.

Implements the Scanner ABC using Databento's Historical API for pre-market
gap scanning. With Databento's full-universe access, we can scan all ~8,000
US equity symbols (though V1 uses a configurable watchlist).
"""

from __future__ import annotations

import logging
import os
import re
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

import pandas as pd

from argus.core.events import WatchlistItem
from argus.data.scanner import Scanner
from argus.models.strategy import ScannerCriteria

if TYPE_CHECKING:
    from argus.core.config import DatabentoConfig

logger = logging.getLogger(__name__)

# Pattern to extract available end date from Databento 422 error messages
# Example: "The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'."
_AVAILABLE_END_PATTERN = re.compile(
    r"data available up to '(\d{4}-\d{2}-\d{2})"
)


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
        2. Query Databento for yesterday's closing prices and today's opens
        3. Compute gap_pct = (today_open - yesterday_close) / yesterday_close
        4. Filter by min_gap_pct, min_price, max_price from config
        5. Sort by gap_pct descending, return top N candidates

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

        # Try to use full gap calculation with Databento data
        try:
            candidates = await self.scan_with_gap_data()
            if candidates:
                logger.info(
                    "DatabentoScanner found %d candidates with gap data",
                    len(candidates),
                )
                return candidates
        except Exception as e:
            logger.warning(
                "Gap data fetch failed, falling back to static list: %s", e
            )

        # Fallback: return configured symbols without gap filtering
        # (used when Databento API is unavailable or before market open)
        logger.info("Using fallback static symbol list")
        candidates = [
            WatchlistItem(
                symbol=symbol,
                gap_pct=0.0,
                premarket_volume=0,
            )
            for symbol in self._config.universe_symbols[: self._config.max_symbols_returned]
        ]

        logger.info("DatabentoScanner found %d candidates (fallback)", len(candidates))
        return candidates

    async def scan_with_gap_data(
        self,
        symbols: list[str] | None = None,
        reference_date: datetime | None = None,
    ) -> list[WatchlistItem]:
        """Scan with actual gap data from Databento (full implementation).

        Computes gaps by fetching daily bars and comparing:
        - Gap = (today's open - yesterday's close) / yesterday's close

        For live pre-market scanning: reference_date should be today's date.
        For historical testing: reference_date can be any past trading date.

        Handles Databento historical data lag gracefully:
        - If the API returns 422 "data_end_after_available_end", extracts the
          available end date and retries the query
        - For gap scanning, we need YESTERDAY's daily bar, so 1-2 days of lag
          is acceptable

        Args:
            symbols: Optional list of symbols to scan. If None, uses config.
            reference_date: Date to compute gaps for. If None, uses current date.

        Returns:
            List of WatchlistItems with computed gap data, filtered and sorted.
        """
        target_symbols = symbols or self._config.universe_symbols
        if not target_symbols:
            return []

        # Use provided reference date or current time
        ref_date = reference_date or datetime.now(UTC)
        ref_date_str = ref_date.strftime("%Y-%m-%d")

        logger.info(
            "Scanning %d symbols with gap data for %s",
            len(target_symbols),
            ref_date_str,
        )

        # Fetch daily bars with historical data lag handling
        df = await self._fetch_daily_bars_with_lag_handling(
            target_symbols, ref_date
        )
        if df is None or df.empty:
            logger.warning("No daily data available from Databento")
            return []

        # Reset index to get ts_event and symbol as columns
        df = df.reset_index()

        candidates: list[WatchlistItem] = []

        # Process each symbol
        for symbol in target_symbols:
            try:
                # Filter to this symbol
                if "symbol" in df.columns:
                    symbol_data = df[df["symbol"] == symbol].copy()
                else:
                    # Databento may use instrument_id instead
                    continue

                if symbol_data.empty or len(symbol_data) < 2:
                    logger.debug("Insufficient data for %s (need 2+ days)", symbol)
                    continue

                # Sort by timestamp to ensure chronological order
                symbol_data = symbol_data.sort_values("ts_event")

                # Get the last two days
                # Last row = reference date (today), second-to-last = previous day
                today_row = symbol_data.iloc[-1]
                prev_row = symbol_data.iloc[-2]

                today_open = float(today_row["open"])
                prev_close = float(prev_row["close"])

                if prev_close <= 0:
                    continue

                # Compute gap percentage
                gap_pct = (today_open - prev_close) / prev_close

                # Apply filters
                if abs(gap_pct) < self._config.min_gap_pct:
                    continue
                if prev_close < self._config.min_price:
                    continue
                if prev_close > self._config.max_price:
                    continue

                # Volume filter on previous day's volume
                prev_volume = int(prev_row.get("volume", 0))
                if prev_volume < self._config.min_volume:
                    logger.debug(
                        "%s filtered: volume %d < min %d",
                        symbol,
                        prev_volume,
                        self._config.min_volume,
                    )
                    continue

                item = WatchlistItem(
                    symbol=symbol,
                    gap_pct=gap_pct,
                    premarket_volume=0,  # Would be populated from live trades in pre-market
                )
                candidates.append(item)

                logger.debug(
                    "%s: prev_close=%.2f, today_open=%.2f, gap=%.2f%%",
                    symbol,
                    prev_close,
                    today_open,
                    gap_pct * 100,
                )

            except (KeyError, IndexError, ValueError) as e:
                logger.warning("Error processing %s: %s", symbol, e)
                continue

        # Sort by absolute gap descending (strongest gaps first)
        candidates.sort(key=lambda x: abs(x.gap_pct), reverse=True)

        logger.info(
            "Gap scan complete: %d candidates from %d symbols (min_gap=%.1f%%)",
            len(candidates),
            len(target_symbols),
            self._config.min_gap_pct * 100,
        )

        # Limit to max
        return candidates[: self._config.max_symbols_returned]

    async def _fetch_daily_bars_with_lag_handling(
        self,
        symbols: list[str],
        ref_date: datetime,
    ) -> pd.DataFrame | None:
        """Fetch daily bars, handling Databento historical data lag gracefully.

        Databento historical data typically has ~15-minute lag during market hours.
        If querying for today's data returns a 422 error with "data_end_after_available_end",
        this method:
        1. Extracts the available end date from the error message
        2. Retries the query using the available date range
        3. Returns whatever data is available (which is sufficient for gap calculation
           since we need yesterday's close, not today's)

        Args:
            symbols: List of symbols to fetch.
            ref_date: Reference date for the query.

        Returns:
            DataFrame with daily bars, or None if fetch failed.
        """
        import databento as db

        # Calculate date range: 7 days back to capture prev trading day across weekends
        start_date = ref_date - timedelta(days=7)
        end_date = ref_date + timedelta(days=1)  # Exclusive end

        try:
            data = self._client.timeseries.get_range(
                dataset=self._config.dataset,
                symbols=symbols,
                schema="ohlcv-1d",
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                stype_in="raw_symbol",
            )
            return data.to_df()

        except db.BentoHttpError as e:
            # Check for 422 with data lag message
            if e.http_status == 422 and "data_end_after_available_end" in str(e):
                logger.warning(
                    "Databento historical data lag detected (422). "
                    "Extracting available end date from error."
                )

                # Extract available end date from error message
                available_end = self._extract_available_end_date(str(e))
                if available_end:
                    logger.info(
                        "Retrying with available end date: %s",
                        available_end.strftime("%Y-%m-%d"),
                    )
                    return await self._fetch_daily_bars_retry(
                        symbols, start_date, available_end
                    )
                else:
                    # Couldn't parse date - try with yesterday
                    yesterday = ref_date - timedelta(days=1)
                    logger.info(
                        "Could not parse available date; retrying with yesterday: %s",
                        yesterday.strftime("%Y-%m-%d"),
                    )
                    return await self._fetch_daily_bars_retry(
                        symbols, start_date, yesterday
                    )

            # Re-raise other HTTP errors
            logger.error("Databento HTTP error fetching daily data: %s", e)
            return None

        except Exception as e:
            logger.error("Failed to fetch daily data from Databento: %s", e)
            return None

    def _extract_available_end_date(self, error_message: str) -> datetime | None:
        """Extract the available end date from a Databento 422 error message.

        Parses messages like:
        "The dataset EQUS.MINI has data available up to '2026-02-28 00:00:00+00:00'."

        Args:
            error_message: The error message string from BentoHttpError.

        Returns:
            datetime if successfully parsed, None otherwise.
        """
        match = _AVAILABLE_END_PATTERN.search(error_message)
        if match:
            date_str = match.group(1)
            try:
                return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=UTC)
            except ValueError:
                logger.warning("Failed to parse date from error: %s", date_str)
        return None

    async def _fetch_daily_bars_retry(
        self,
        symbols: list[str],
        start_date: datetime,
        end_date: datetime,
    ) -> pd.DataFrame | None:
        """Retry fetching daily bars with adjusted end date.

        Args:
            symbols: List of symbols to fetch.
            start_date: Start date for the query.
            end_date: Adjusted end date (exclusive).

        Returns:
            DataFrame with daily bars, or None if fetch failed.
        """
        try:
            # Add 1 day to end_date since Databento uses exclusive end
            query_end = end_date + timedelta(days=1)

            data = self._client.timeseries.get_range(
                dataset=self._config.dataset,
                symbols=symbols,
                schema="ohlcv-1d",
                start=start_date.strftime("%Y-%m-%d"),
                end=query_end.strftime("%Y-%m-%d"),
                stype_in="raw_symbol",
            )
            df = data.to_df()

            if not df.empty:
                logger.info(
                    "Retry successful: fetched %d daily bar records",
                    len(df),
                )
            return df

        except Exception as e:
            logger.error("Retry fetch also failed: %s", e)
            return None

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
