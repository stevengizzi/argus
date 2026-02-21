"""Historical data fetcher for Alpaca and Databento 1-minute bars.

Downloads historical bar data from Alpaca's StockHistoricalDataClient
or Databento's Historical API, saves as Parquet files (one per symbol
per month), tracks progress in a manifest, and validates data quality
after download.

Usage (Alpaca):
    python -m argus.backtest.data_fetcher \\
        --symbols TSLA,NVDA,AAPL \\
        --start 2025-03-01 \\
        --end 2026-02-01

Or use the backtest_universe.yaml for the full symbol list:
    python -m argus.backtest.data_fetcher \\
        --start 2025-03-01 \\
        --end 2026-02-01

For Databento, use fetch_symbol_month_databento() programmatically.
"""

import asyncio
import calendar
import logging
import time
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd
from alpaca.data.enums import Adjustment, DataFeed
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

from argus.backtest.config import DataFetcherConfig
from argus.backtest.data_validator import validate_parquet_file
from argus.backtest.manifest import (
    Manifest,
    SymbolMonthEntry,
    load_manifest,
    save_manifest,
)
from argus.data.databento_utils import normalize_databento_df

logger = logging.getLogger(__name__)


def _generate_month_ranges(
    start_date: date, end_date: date
) -> list[tuple[int, int, date, date]]:
    """Generate (year, month, first_day, last_day) tuples for the date range.

    The range is inclusive of start_date's month and exclusive of end_date's month
    if end_date is the 1st of a month, otherwise inclusive.

    Args:
        start_date: Beginning of desired range.
        end_date: End of desired range.

    Returns:
        List of (year, month, month_start, month_end) tuples.
    """
    ranges = []
    current = date(start_date.year, start_date.month, 1)
    while current < end_date:
        year, month = current.year, current.month
        last_day = calendar.monthrange(year, month)[1]
        month_end = date(year, month, last_day)
        # Don't go past end_date
        if month_end > end_date:
            month_end = end_date
        ranges.append((year, month, current, month_end))
        # Advance to next month
        current = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    return ranges


def _bars_to_dataframe(bars, symbol: str) -> pd.DataFrame:
    """Convert Alpaca bar response to a standardized DataFrame.

    Normalizes the Alpaca SDK's bar objects into our standard schema:
    timestamp (UTC), open, high, low, close, volume.

    Args:
        bars: Response from StockHistoricalDataClient.get_stock_bars().
              This is a BarSet object that supports subscript access.
        symbol: The symbol to extract from the BarSet.

    Returns:
        DataFrame with columns: timestamp, open, high, low, close, volume.
        Empty DataFrame if no bars.
    """
    empty_df = pd.DataFrame(
        columns=["timestamp", "open", "high", "low", "close", "volume"]
    )

    # Debug: check what we have
    logger.debug(
        "_bars_to_dataframe: symbol=%s, bars type=%s",
        symbol,
        type(bars).__name__,
    )

    # Try using the .df property first (returns MultiIndex DataFrame)
    if hasattr(bars, "df") and not bars.df.empty:
        df = bars.df
        logger.debug("  Using bars.df, shape=%s, index levels=%s", df.shape, df.index.names)

        # Reset the multi-index to get symbol and timestamp as columns
        df = df.reset_index()

        # Filter to just the symbol we want (in case of multi-symbol response)
        if "symbol" in df.columns:
            df = df[df["symbol"] == symbol]

        if df.empty:
            logger.debug("  No data for symbol %s after filtering", symbol)
            return empty_df

        # Rename columns to our standard schema
        df = df.rename(columns={"timestamp": "timestamp"})

        # Ensure we have the expected columns
        expected_cols = ["timestamp", "open", "high", "low", "close", "volume"]
        for col in expected_cols:
            if col not in df.columns:
                logger.warning("  Missing expected column: %s", col)
                return empty_df

        # Select and order columns
        df = df[expected_cols].copy()

        # Ensure timestamps are UTC-aware
        if df["timestamp"].dt.tz is None:
            df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
        elif str(df["timestamp"].dt.tz) != "UTC":
            df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

        return df.sort_values("timestamp").reset_index(drop=True)

    # Fallback to subscript access
    if symbol not in bars:
        logger.debug("  symbol %s not in bars (subscript access)", symbol)
        return empty_df

    rows = []
    for bar in bars[symbol]:
        rows.append(
            {
                "timestamp": bar.timestamp,
                "open": float(bar.open),
                "high": float(bar.high),
                "low": float(bar.low),
                "close": float(bar.close),
                "volume": int(bar.volume),
            }
        )

    if not rows:
        return empty_df

    df = pd.DataFrame(rows)

    # Ensure timestamps are UTC-aware
    if df["timestamp"].dt.tz is None:
        df["timestamp"] = df["timestamp"].dt.tz_localize("UTC")
    elif str(df["timestamp"].dt.tz) != "UTC":
        df["timestamp"] = df["timestamp"].dt.tz_convert("UTC")

    return df.sort_values("timestamp").reset_index(drop=True)


class DataFetcher:
    """Downloads and stores historical 1-minute bar data from Alpaca or Databento.

    Uses Alpaca's StockHistoricalDataClient or Databento's Historical API
    to fetch bars. Saves them as Parquet files organized by symbol and month,
    tracks progress in a manifest for resume capability, and validates data quality.

    Args:
        config: DataFetcherConfig with storage and rate limit settings.
        api_key: Alpaca API key (from environment).
        api_secret: Alpaca API secret (from environment).
        databento_key: Databento API key (optional, for Databento fetches).
    """

    def __init__(
        self,
        config: DataFetcherConfig,
        api_key: str | None = None,
        api_secret: str | None = None,
        databento_key: str | None = None,
    ) -> None:
        self._config = config
        self._client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=api_secret,
        )
        self._manifest = load_manifest(config.manifest_path)
        self._request_timestamps: list[float] = []

        # Databento client (lazy init)
        self._databento_key = databento_key
        self._databento_client = None  # Created on first use

    @property
    def manifest(self) -> Manifest:
        """Access the current manifest (for testing and reporting)."""
        return self._manifest

    @property
    def _db_client(self):
        """Lazy-init Databento Historical client.

        Returns:
            Databento Historical client.

        Raises:
            RuntimeError: If Databento API key is not available.
        """
        if self._databento_client is None:
            import os

            import databento as db

            key = self._databento_key or os.getenv("DATABENTO_API_KEY")
            if not key:
                raise RuntimeError(
                    "Databento API key not available. Set DATABENTO_API_KEY environment "
                    "variable or pass databento_key to DataFetcher constructor."
                )
            self._databento_client = db.Historical(key=key)
        return self._databento_client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting by sleeping if necessary.

        Maintains a sliding window of request timestamps. If we've hit
        the per-minute limit, sleep until the oldest request falls out
        of the window.
        """
        now = time.monotonic()
        # Remove timestamps older than 60 seconds
        self._request_timestamps = [
            t for t in self._request_timestamps if now - t < 60.0
        ]
        if len(self._request_timestamps) >= self._config.max_requests_per_minute:
            sleep_time = 60.0 - (now - self._request_timestamps[0]) + 0.1
            if sleep_time > 0:
                logger.debug("Rate limit: sleeping %.1f seconds", sleep_time)
                await asyncio.sleep(sleep_time)
        self._request_timestamps.append(time.monotonic())

    def _fetch_bars_sync(
        self,
        symbol: str,
        start: datetime,
        end: datetime,
    ) -> pd.DataFrame:
        """Fetch bars for a single symbol and date range (synchronous).

        Handles pagination if the response exceeds the per-request limit.
        Retries on 429 (rate limit) responses.

        Args:
            symbol: Ticker symbol.
            start: Start datetime (inclusive).
            end: End datetime (inclusive).

        Returns:
            DataFrame with all bars for the range.
        """
        adjustment = (
            Adjustment.SPLIT
            if self._config.adjustment == "split"
            else (Adjustment.ALL if self._config.adjustment == "all" else Adjustment.RAW)
        )
        feed = DataFeed.IEX if self._config.feed == "iex" else DataFeed.SIP

        request = StockBarsRequest(
            symbol_or_symbols=symbol,
            start=start,
            end=end,
            timeframe=TimeFrame.Minute,
            adjustment=adjustment,
            feed=feed,
        )

        for attempt in range(self._config.retry_max_attempts):
            try:
                bars = self._client.get_stock_bars(request)
                # Debug logging to trace API response
                logger.debug(
                    "API response for %s: type=%s, keys=%s",
                    symbol,
                    type(bars).__name__,
                    list(bars.data.keys()) if hasattr(bars, "data") else "no data attr",
                )
                return _bars_to_dataframe(bars, symbol)
            except Exception as e:
                error_str = str(e).lower()
                if "429" in error_str or "too many" in error_str or "rate" in error_str:
                    delay = self._config.retry_base_delay_seconds * (2**attempt)
                    logger.warning(
                        "Rate limited fetching %s (attempt %d/%d), sleeping %.1fs",
                        symbol,
                        attempt + 1,
                        self._config.retry_max_attempts,
                        delay,
                    )
                    # Synchronous sleep in sync context
                    import time as time_mod

                    time_mod.sleep(delay)
                else:
                    logger.error(
                        "Error fetching %s (attempt %d/%d): %s",
                        symbol,
                        attempt + 1,
                        self._config.retry_max_attempts,
                        e,
                    )
                    if attempt == self._config.retry_max_attempts - 1:
                        raise

        return pd.DataFrame()  # Should not reach here

    def _save_parquet(
        self, df: pd.DataFrame, symbol: str, year: int, month: int
    ) -> Path:
        """Save a DataFrame as a Parquet file in the expected directory structure.

        Creates directories as needed. File path:
        {data_dir}/{SYMBOL}/{SYMBOL}_{YYYY}-{MM}.parquet

        Args:
            df: DataFrame to save.
            symbol: Ticker symbol.
            year: Year of data.
            month: Month of data.

        Returns:
            Path to the saved file.
        """
        symbol_dir = self._config.data_dir / symbol
        symbol_dir.mkdir(parents=True, exist_ok=True)
        file_path = symbol_dir / f"{symbol}_{year}-{month:02d}.parquet"
        df.to_parquet(file_path, index=False)
        logger.info("Saved %d bars to %s", len(df), file_path)
        return file_path

    async def fetch_symbol_month(
        self,
        symbol: str,
        year: int,
        month: int,
        month_start: date,
        month_end: date,
        force: bool = False,
    ) -> SymbolMonthEntry | None:
        """Fetch and save one symbol-month of data.

        Skips if already in manifest (unless force=True).
        Validates after saving. Updates manifest.

        Args:
            symbol: Ticker symbol.
            year: Year.
            month: Month.
            month_start: First day of the month range.
            month_end: Last day of the month range.
            force: If True, re-download even if already in manifest.

        Returns:
            SymbolMonthEntry if downloaded, None if skipped.
        """
        if not force and self._manifest.has_entry(symbol, year, month):
            logger.debug(
                "Skipping %s %d-%02d (already in manifest)", symbol, year, month
            )
            return None

        await self._rate_limit()

        start_dt = datetime(
            month_start.year, month_start.month, month_start.day, tzinfo=UTC
        )
        end_dt = datetime(
            month_end.year, month_end.month, month_end.day, 23, 59, 59, tzinfo=UTC
        )

        logger.info("Fetching %s %d-%02d ...", symbol, year, month)

        # Run the synchronous Alpaca call in a thread to not block the event loop
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, self._fetch_bars_sync, symbol, start_dt, end_dt
        )

        if df.empty:
            logger.warning("No data returned for %s %d-%02d", symbol, year, month)
            entry = SymbolMonthEntry(
                symbol=symbol,
                year=year,
                month=month,
                row_count=0,
                file_path="",
                downloaded_at=datetime.now(UTC).isoformat(),
                source="alpaca_free",
                adjustment=self._config.adjustment,
                feed=self._config.feed,
                data_quality_issues=["No data returned from API"],
            )
            self._manifest.add_entry(entry)
            return entry

        file_path = self._save_parquet(df, symbol, year, month)

        # Validate
        validation = validate_parquet_file(file_path, symbol, year, month)

        entry = SymbolMonthEntry(
            symbol=symbol,
            year=year,
            month=month,
            row_count=validation.row_count,
            file_path=str(file_path),
            downloaded_at=datetime.now(UTC).isoformat(),
            source="alpaca_free",
            adjustment=self._config.adjustment,
            feed=self._config.feed,
            data_quality_issues=validation.issues,
        )
        self._manifest.add_entry(entry)
        return entry

    def _get_parquet_path_databento(
        self, symbol: str, year: int, month: int
    ) -> Path:
        """Get the Parquet cache path for Databento data.

        Uses a separate cache directory from Alpaca to avoid mixing providers.

        Args:
            symbol: Ticker symbol.
            year: Year of data.
            month: Month of data.

        Returns:
            Path to the Parquet file.
        """
        cache_dir = self._config.databento_cache_dir
        symbol_dir = cache_dir / symbol
        return symbol_dir / f"{symbol}_{year}-{month:02d}.parquet"

    async def fetch_symbol_month_databento(
        self,
        symbol: str,
        year: int,
        month: int,
    ) -> pd.DataFrame:
        """Fetch one month of 1-minute bars from Databento Historical API.

        Checks Parquet cache first. If not cached, fetches from Databento,
        normalizes to standard schema, and caches as Parquet.

        Args:
            symbol: Ticker symbol (e.g., "AAPL").
            year: Year (e.g., 2025).
            month: Month (1-12).

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume.
            Same schema as fetch_symbol_month() (Alpaca version).
        """
        from datetime import timedelta

        # Check cache
        cache_path = self._get_parquet_path_databento(symbol, year, month)
        if cache_path.exists():
            logger.debug("Cache hit: %s", cache_path)
            return pd.read_parquet(cache_path)

        # Calculate date range
        start_date = date(year, month, 1)
        _, last_day = calendar.monthrange(year, month)
        end_date = date(year, month, last_day)

        # Rate limit
        await self._rate_limit()

        # Fetch from Databento
        logger.info("Fetching %s %d-%02d from Databento", symbol, year, month)

        data = self._db_client.timeseries.get_range(
            dataset=self._config.databento_dataset,
            symbols=symbol,
            schema="ohlcv-1m",
            start=start_date.isoformat(),
            end=(end_date + timedelta(days=1)).isoformat(),  # Exclusive end
            stype_in="raw_symbol",
        )

        df = data.to_df()

        if df.empty:
            logger.warning("No data returned for %s %d-%02d", symbol, year, month)
            return pd.DataFrame(
                columns=["timestamp", "open", "high", "low", "close", "volume"]
            )

        # Normalize to standard schema
        result = self._normalize_databento_df(df)

        # Save to cache
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        result.to_parquet(cache_path, index=False)
        logger.info("Cached %d bars for %s %d-%02d", len(result), symbol, year, month)

        # Update manifest for tracking
        entry = SymbolMonthEntry(
            symbol=symbol,
            year=year,
            month=month,
            row_count=len(result),
            file_path=str(cache_path),
            downloaded_at=datetime.now(UTC).isoformat(),
            source="databento",
            adjustment="raw",
            feed=self._config.databento_dataset,
            data_quality_issues=[],
        )
        self._manifest.add_entry(entry)

        return result

    @staticmethod
    def _normalize_databento_df(df: pd.DataFrame) -> pd.DataFrame:
        """Normalize Databento DataFrame to ARGUS standard schema.

        Delegates to shared utility function for consistency with DatabentoDataService.

        Args:
            df: DataFrame from Databento's to_df() method.

        Returns:
            Normalized DataFrame with standard schema.
        """
        return normalize_databento_df(df)

    async def fetch_all(
        self,
        symbols: list[str],
        start_date: date,
        end_date: date,
        force: bool = False,
    ) -> Manifest:
        """Fetch historical data for all symbols across the full date range.

        Iterates through each symbol and each month in the range.
        Saves manifest after each symbol completes (crash recovery).

        Args:
            symbols: List of ticker symbols.
            start_date: Start date of the range.
            end_date: End date of the range.
            force: If True, re-download everything ignoring manifest.

        Returns:
            Updated manifest with all entries.
        """
        month_ranges = _generate_month_ranges(start_date, end_date)
        total = len(symbols) * len(month_ranges)
        completed = 0
        skipped = 0

        logger.info(
            "Starting download: %d symbols x %d months = %d symbol-months",
            len(symbols),
            len(month_ranges),
            total,
        )

        for symbol in symbols:
            for year, month, m_start, m_end in month_ranges:
                entry = await self.fetch_symbol_month(
                    symbol, year, month, m_start, m_end, force=force
                )
                if entry is None:
                    skipped += 1
                completed += 1

                if completed % 10 == 0:
                    logger.info(
                        "Progress: %d/%d (%.0f%%), skipped %d",
                        completed,
                        total,
                        100 * completed / total,
                        skipped,
                    )

            # Save manifest after each symbol (crash recovery)
            save_manifest(self._manifest, self._config.manifest_path)
            logger.info(
                "Completed %s. Manifest saved (%d entries total).",
                symbol,
                self._manifest.total_files(),
            )

        # Final save
        save_manifest(self._manifest, self._config.manifest_path)
        logger.info(
            "Download complete. %d files, %d total bars, %d skipped.",
            self._manifest.total_files(),
            self._manifest.total_rows(),
            skipped,
        )
        return self._manifest

    def print_summary(self) -> None:
        """Print a human-readable summary of the manifest."""
        m = self._manifest
        print(f"\n{'=' * 60}")
        print("ARGUS Historical Data Summary")
        print(f"{'=' * 60}")
        print(f"Total files:  {m.total_files()}")
        print(f"Total bars:   {m.total_rows():,}")
        print(f"Symbols:      {len(m.get_symbols())}")
        print("\nSymbol Details:")
        for symbol in m.get_symbols():
            date_range = m.get_date_range(symbol)
            if date_range:
                print(f"  {symbol:8s}  {date_range[0]} -> {date_range[1]}")
        issues = m.entries_with_issues()
        if issues:
            print(f"\nData Quality Issues ({len(issues)} files):")
            for entry in issues:
                print(f"  {entry.symbol} {entry.year}-{entry.month:02d}:")
                for issue in entry.data_quality_issues:
                    print(f"    - {issue}")
        else:
            print("\nNo data quality issues found.")
        print(f"{'=' * 60}\n")


def main() -> None:
    """CLI entry point for the data fetcher."""
    import argparse
    import os

    import yaml
    from dotenv import load_dotenv

    # Load environment variables from .env file
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Download historical 1-minute bar data from Alpaca.",
        prog="python -m argus.backtest.data_fetcher",
    )
    parser.add_argument(
        "--symbols",
        type=str,
        default=None,
        help="Comma-separated list of symbols (e.g., TSLA,NVDA,AAPL). "
        "If omitted, reads from config/backtest_universe.yaml.",
    )
    parser.add_argument(
        "--start",
        type=str,
        required=True,
        help="Start date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--end",
        type=str,
        required=True,
        help="End date in YYYY-MM-DD format.",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/historical/1m",
        help="Directory to store Parquet files (default: data/historical/1m).",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-download even if data exists in manifest.",
    )
    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # Resolve symbols
    if args.symbols:
        symbols = [s.strip().upper() for s in args.symbols.split(",")]
    else:
        universe_path = Path("config/backtest_universe.yaml")
        if not universe_path.exists():
            logger.error("No --symbols provided and %s not found", universe_path)
            raise SystemExit(1)
        with open(universe_path) as f:
            data = yaml.safe_load(f)
        symbols = data.get("symbols", [])
        if not symbols:
            logger.error("No symbols found in %s", universe_path)
            raise SystemExit(1)
        logger.info("Loaded %d symbols from %s", len(symbols), universe_path)

    # Parse dates
    start_date = date.fromisoformat(args.start)
    end_date = date.fromisoformat(args.end)

    if end_date <= start_date:
        logger.error("End date must be after start date")
        raise SystemExit(1)

    # Build config
    config = DataFetcherConfig(
        data_dir=Path(args.data_dir),
        manifest_path=Path(args.data_dir).parent / "manifest.json",
    )

    # Get API credentials from environment
    # Supports both APCA_* (alpaca-py default) and ALPACA_* (project convention)
    api_key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get(
        "ALPACA_SECRET_KEY"
    )

    if not api_key or not api_secret:
        logger.error(
            "Alpaca API credentials not found. Set ALPACA_API_KEY and "
            "ALPACA_SECRET_KEY environment variables (or APCA_API_KEY_ID/APCA_API_SECRET_KEY)."
        )
        raise SystemExit(1)

    fetcher = DataFetcher(config, api_key=api_key, api_secret=api_secret)

    logger.info(
        "Fetching %d symbols from %s to %s (data_dir: %s, force: %s)",
        len(symbols),
        start_date,
        end_date,
        config.data_dir,
        args.force,
    )

    asyncio.run(fetcher.fetch_all(symbols, start_date, end_date, force=args.force))
    fetcher.print_summary()


def debug_single_request() -> None:
    """Debug helper to test a single API request and show raw response."""
    import os

    from dotenv import load_dotenv

    load_dotenv()

    logging.basicConfig(level=logging.DEBUG, format="%(levelname)s: %(message)s")

    api_key = os.environ.get("APCA_API_KEY_ID") or os.environ.get("ALPACA_API_KEY")
    api_secret = os.environ.get("APCA_API_SECRET_KEY") or os.environ.get(
        "ALPACA_SECRET_KEY"
    )

    if not api_key or not api_secret:
        print("ERROR: Set ALPACA_API_KEY and ALPACA_SECRET_KEY env vars")
        return

    print(f"Using API key: {api_key[:8]}...")

    client = StockHistoricalDataClient(api_key=api_key, secret_key=api_secret)

    # Test a single request for a well-known symbol and safe past date
    symbol = "AAPL"
    start = datetime(2025, 12, 15, 14, 30, tzinfo=UTC)  # Safe past trading day
    end = datetime(2025, 12, 15, 21, 0, tzinfo=UTC)

    print(f"\nRequesting {symbol} bars from {start} to {end}...")

    request = StockBarsRequest(
        symbol_or_symbols=symbol,
        start=start,
        end=end,
        timeframe=TimeFrame.Minute,
        feed=DataFeed.IEX,
    )

    bars = client.get_stock_bars(request)

    print(f"\nResponse type: {type(bars).__name__}")
    print(f"Has 'data' attr: {hasattr(bars, 'data')}")
    print(f"Has 'df' attr: {hasattr(bars, 'df')}")

    if hasattr(bars, "data"):
        print(f"bars.data type: {type(bars.data).__name__}")
        print(f"bars.data keys: {list(bars.data.keys())}")

    if hasattr(bars, "df"):
        df = bars.df
        print(f"\nbars.df shape: {df.shape}")
        print(f"bars.df empty: {df.empty}")
        if not df.empty:
            print(f"bars.df head:\n{df.head()}")

    print(f"\n'{symbol}' in bars: {symbol in bars}")

    if symbol in bars:
        bar_list = bars[symbol]
        print(f"bars['{symbol}'] length: {len(bar_list)}")
        if bar_list:
            print(f"First bar: {bar_list[0]}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--debug":
        debug_single_request()
    else:
        main()
