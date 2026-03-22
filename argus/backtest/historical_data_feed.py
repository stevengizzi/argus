"""Historical data feed for downloading and caching Databento OHLCV-1m data.

Provides the HistoricalDataFeed class that manages Parquet-cached historical
bar data for backtesting. Downloads from Databento's Historical API with
cost validation (DEC-353) and incremental update support.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from argus.data.databento_utils import normalize_databento_df

logger = logging.getLogger(__name__)

ET = ZoneInfo("America/New_York")

EXPECTED_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]


class HistoricalDataFeedError(Exception):
    """Raised when historical data download or validation fails."""


class HistoricalDataFeed:
    """Downloads and caches Databento OHLCV-1m historical data.

    Data is cached as Parquet files: {cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet
    Incremental updates download only missing months.
    Cost validation ensures $0.00 before every download (DEC-353).

    Args:
        cache_dir: Directory for Parquet cache files.
        dataset: Databento dataset identifier.
        verify_zero_cost: If True, validate $0.00 cost before each download.
    """

    def __init__(
        self,
        cache_dir: Path,
        dataset: str = "EQUS.MINI",
        verify_zero_cost: bool = True,
    ) -> None:
        self._cache_dir = cache_dir
        self._dataset = dataset
        self._verify_zero_cost = verify_zero_cost
        self._client: Any = None

    @property
    def _db_client(self) -> Any:
        """Lazy-init Databento Historical client.

        Returns:
            Databento Historical client.

        Raises:
            RuntimeError: If DATABENTO_API_KEY is not set.
        """
        if self._client is None:
            import os

            import databento as db

            key = os.getenv("DATABENTO_API_KEY")
            if not key:
                raise RuntimeError(
                    "Databento API key not available. Set DATABENTO_API_KEY "
                    "environment variable."
                )
            self._client = db.Historical(key=key)
        return self._client

    async def download(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, Path]:
        """Download OHLCV-1m data for symbols in date range.

        Checks cache first. Downloads only missing symbol-months.
        Returns mapping of symbol -> cache directory path.

        Args:
            symbols: List of ticker symbols to download.
            start_date: First date of requested range.
            end_date: Last date of requested range.

        Returns:
            Mapping of symbol to its cache directory path.
        """
        needed_months = self._month_range(start_date, end_date)
        result: dict[str, Path] = {}

        for symbol in symbols:
            symbol_dir = self._cache_dir / symbol
            cached = set(self.get_cached_months(symbol))

            for year, month in needed_months:
                if (year, month) in cached:
                    logger.debug("Cache hit: %s %d-%02d", symbol, year, month)
                    continue

                await self._download_month(symbol, year, month)

            result[symbol] = symbol_dir

        return result

    async def load(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
    ) -> dict[str, pd.DataFrame]:
        """Load cached data for symbols in date range.

        Returns mapping of symbol -> DataFrame with columns:
        [timestamp, open, high, low, close, volume, trading_date]
        timestamp is UTC-aware. trading_date is ET date.

        Args:
            symbols: List of ticker symbols to load.
            start_date: First date of requested range.
            end_date: Last date of requested range.

        Returns:
            Mapping of symbol to DataFrame with standard schema.
        """
        needed_months = self._month_range(start_date, end_date)
        result: dict[str, pd.DataFrame] = {}

        for symbol in symbols:
            frames: list[pd.DataFrame] = []

            for year, month in needed_months:
                parquet_path = self._parquet_path(symbol, year, month)
                if parquet_path.exists():
                    df = pd.read_parquet(parquet_path)
                    if not df.empty:
                        frames.append(df)

            if not frames:
                result[symbol] = pd.DataFrame(
                    columns=EXPECTED_COLUMNS + ["trading_date"]
                )
                continue

            combined = pd.concat(frames, ignore_index=True)
            combined = combined.sort_values("timestamp").reset_index(drop=True)

            # Ensure timestamp is datetime
            if not pd.api.types.is_datetime64_any_dtype(combined["timestamp"]):
                combined["timestamp"] = pd.to_datetime(combined["timestamp"])

            # Ensure UTC-aware
            if combined["timestamp"].dt.tz is None:
                combined["timestamp"] = combined["timestamp"].dt.tz_localize("UTC")

            # Add trading_date (ET date from UTC timestamp)
            combined["trading_date"] = (
                combined["timestamp"].dt.tz_convert(ET).dt.date
            )

            # Filter to requested date range
            mask = (combined["trading_date"] >= start_date) & (
                combined["trading_date"] <= end_date
            )
            filtered = combined[mask].reset_index(drop=True)

            result[symbol] = filtered

        return result

    def get_cached_months(self, symbol: str) -> list[tuple[int, int]]:
        """Return list of (year, month) tuples cached for a symbol.

        Args:
            symbol: Ticker symbol.

        Returns:
            List of (year, month) tuples with cached Parquet files.
        """
        symbol_dir = self._cache_dir / symbol
        if not symbol_dir.exists():
            return []

        months: list[tuple[int, int]] = []
        for path in sorted(symbol_dir.glob("*.parquet")):
            # Parse filename: YYYY-MM.parquet
            stem = path.stem
            parts = stem.split("-")
            if len(parts) == 2:
                try:
                    year = int(parts[0])
                    month = int(parts[1])
                    months.append((year, month))
                except ValueError:
                    continue
        return months

    def _month_range(self, start_date: date, end_date: date) -> list[tuple[int, int]]:
        """Generate list of (year, month) tuples in date range.

        Args:
            start_date: First date of range.
            end_date: Last date of range.

        Returns:
            List of (year, month) tuples covering the range.
        """
        months: list[tuple[int, int]] = []
        current = date(start_date.year, start_date.month, 1)
        end_month = date(end_date.year, end_date.month, 1)

        while current <= end_month:
            months.append((current.year, current.month))
            # Advance to next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)

        return months

    def _parquet_path(self, symbol: str, year: int, month: int) -> Path:
        """Get the Parquet cache path for a symbol-month.

        Args:
            symbol: Ticker symbol.
            year: Year of data.
            month: Month of data (1-12).

        Returns:
            Path: {cache_dir}/{SYMBOL}/{YYYY}-{MM}.parquet
        """
        return self._cache_dir / symbol / f"{year}-{month:02d}.parquet"

    async def _download_month(
        self, symbol: str, year: int, month: int
    ) -> None:
        """Download and cache a single symbol-month from Databento.

        Args:
            symbol: Ticker symbol.
            year: Year of data.
            month: Month of data (1-12).

        Raises:
            HistoricalDataFeedError: If cost validation fails or API errors occur.
        """
        month_start = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        month_end = date(year, month, last_day) + timedelta(days=1)  # exclusive

        start_str = month_start.isoformat()
        end_str = month_end.isoformat()

        # Cost validation (DEC-353, AR-3)
        if self._verify_zero_cost:
            try:
                cost = self._db_client.metadata.get_cost(
                    dataset=self._dataset,
                    symbols=[symbol],
                    schema="ohlcv-1m",
                    start=start_str,
                    end=end_str,
                )
                if cost > 0.00:
                    raise HistoricalDataFeedError(
                        f"Cost validation failed for {symbol} {year}-{month:02d}: "
                        f"expected $0.00 but got ${cost:.2f}. "
                        f"Set verify_zero_cost=False to bypass."
                    )
            except HistoricalDataFeedError:
                raise
            except Exception as exc:
                raise HistoricalDataFeedError(
                    f"Cost validation failed for {symbol} {year}-{month:02d}: "
                    f"{exc}. Set verify_zero_cost=False to bypass."
                ) from exc

        # Download data
        logger.info("Downloading %s %d-%02d...", symbol, year, month)

        try:
            data = self._db_client.timeseries.get_range(
                dataset=self._dataset,
                symbols=[symbol],
                schema="ohlcv-1m",
                start=start_str,
                end=end_str,
            )
            df = data.to_df()
        except Exception as exc:
            # Symbol not found or API error — check if it's a "not found" case
            error_msg = str(exc).lower()
            if "not found" in error_msg or "no data" in error_msg:
                logger.warning(
                    "Symbol %s not found in Databento for %d-%02d, skipping",
                    symbol, year, month,
                )
                return
            raise HistoricalDataFeedError(
                f"API error downloading {symbol} {year}-{month:02d}: {exc}"
            ) from exc

        if df.empty:
            logger.info(
                "No data for %s %d-%02d, writing empty cache file",
                symbol, year, month,
            )
            empty_df = pd.DataFrame(columns=EXPECTED_COLUMNS)
            cache_path = self._parquet_path(symbol, year, month)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            empty_df.to_parquet(cache_path, index=False)
            return

        # Normalize via shared utility
        result = normalize_databento_df(df)

        # Save to cache
        cache_path = self._parquet_path(symbol, year, month)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(cache_path, index=False)

        logger.info(
            "Cached %s %d-%02d (%d bars)", symbol, year, month, len(result)
        )
