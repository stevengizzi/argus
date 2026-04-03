"""Historical Query Service — read-only DuckDB layer over the Parquet cache.

Provides SQL access to ARGUS's existing Databento Parquet cache
(`data/databento_cache/`) without ever modifying it.  A DuckDB in-memory
connection is created at startup; the Parquet files are the sole persistent
store.

Cache directory layout expected:
    {cache_dir}/{SYMBOL}/{YYYY-MM}.parquet

The VIEW exposes columns: symbol, ts_event, date, open, high, low, close, volume.
Symbol is extracted from the directory path; date is CAST(ts_event AS DATE).

Sprint 31A.5, Session 1.
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

from argus.data.historical_query_config import HistoricalQueryConfig

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exception types
# ---------------------------------------------------------------------------


class ServiceUnavailableError(Exception):
    """Raised when the Historical Query Service is not initialized or the cache
    directory is missing/empty."""


class QueryExecutionError(Exception):
    """Raised when a DuckDB query fails."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

_SYMBOLS_TTL_SECONDS = 60.0


class HistoricalQueryService:
    """Read-only DuckDB query layer over the Parquet historical cache.

    Initializes an in-memory DuckDB connection and creates a VIEW named
    ``historical`` that unions all Parquet files in the cache directory.
    The symbol column is derived from the directory structure; the raw
    Parquet files are never written to.

    Args:
        config: HistoricalQueryConfig with resource limits and cache path.
    """

    def __init__(self, config: HistoricalQueryConfig) -> None:
        """Initialize the service, connect to DuckDB, and create the VIEW.

        Args:
            config: HistoricalQueryConfig controlling enabled flag, cache dir,
                    memory limit, and thread count.
        """
        self._config = config
        self._conn: object | None = None  # duckdb.DuckDBPyConnection
        self._available: bool = False
        self._symbols_cache: list[str] | None = None
        self._symbols_cache_ts: float = 0.0

        if not config.enabled:
            logger.info(
                "HistoricalQueryService: disabled via config (enabled=false)"
            )
            return

        cache_path = Path(config.cache_dir)
        if not cache_path.exists():
            logger.info(
                "HistoricalQueryService: cache_dir does not exist: %s — service unavailable",
                config.cache_dir,
            )
            return

        try:
            import duckdb  # lazy import — only used by this module

            conn = duckdb.connect(database=":memory:")
            conn.execute(f"SET memory_limit='{config.max_memory_mb}MB'")
            conn.execute(f"SET threads TO {config.default_threads}")
            self._conn = conn

            self._initialize_view(cache_path)
        except ImportError:
            logger.error(
                "HistoricalQueryService: duckdb package not installed — "
                "service unavailable"
            )
        except Exception:
            logger.exception(
                "HistoricalQueryService: unexpected error during initialization"
            )

    def _initialize_view(self, cache_path: Path) -> None:
        """Create the ``historical`` VIEW over all Parquet files.

        Discovers the schema from the first Parquet file found, logs it at
        INFO level for operational visibility, then creates a VIEW that adds
        a ``symbol`` column (extracted from the directory path) and a ``date``
        column (CAST of ts_event).

        Args:
            cache_path: Absolute or relative path to the Parquet cache root.
        """
        # Discover at least one Parquet file to validate the cache isn't empty
        parquet_files = list(cache_path.glob("**/*.parquet"))
        if not parquet_files:
            logger.warning(
                "HistoricalQueryService: cache_dir contains no Parquet files (%s) "
                "— service unavailable",
                cache_path,
            )
            return

        # Inspect the schema of the first file and log it
        first_file = str(parquet_files[0])
        try:
            schema_df = self._conn.execute(  # type: ignore[union-attr]
                f"DESCRIBE SELECT * FROM read_parquet('{first_file}')"
            ).fetchdf()
            col_names = schema_df["column_name"].tolist() if "column_name" in schema_df.columns else []
            logger.info(
                "HistoricalQueryService: discovered Parquet schema — columns: %s",
                col_names,
            )
        except Exception:
            logger.warning(
                "HistoricalQueryService: could not inspect Parquet schema of %s",
                first_file,
            )

        # Build the glob pattern for all Parquet files in the cache
        glob_pattern = str(cache_path.resolve()) + "/**/*.parquet"

        # The VIEW extracts symbol from the parent directory name.
        # Path layout: {cache_dir}/{SYMBOL}/{YYYY-MM}.parquet
        view_sql = f"""
        CREATE OR REPLACE VIEW historical AS
        SELECT
            regexp_extract(filename, '.*/([^/]+)/[^/]+\\.parquet$', 1) AS symbol,
            "timestamp" AS ts_event,
            CAST("timestamp" AS DATE) AS date,
            "open",
            "high",
            "low",
            "close",
            "volume"
        FROM read_parquet('{glob_pattern}', filename=true, union_by_name=true)
        """

        try:
            self._conn.execute(view_sql)  # type: ignore[union-attr]
            # Validate the view by querying one row
            self._conn.execute("SELECT * FROM historical LIMIT 1").fetchdf()  # type: ignore[union-attr]
            self._available = True
            logger.info(
                "HistoricalQueryService: VIEW 'historical' created over %s "
                "(%d Parquet files found)",
                cache_path,
                len(parquet_files),
            )
        except Exception:
            logger.warning(
                "HistoricalQueryService: failed to create or validate VIEW "
                "— service unavailable",
                exc_info=True,
            )

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_available(self) -> bool:
        """True when the DuckDB VIEW is initialized and queryable."""
        return self._available

    # ------------------------------------------------------------------
    # Query methods
    # ------------------------------------------------------------------

    def query(self, sql: str, params: list | None = None) -> pd.DataFrame:
        """Execute raw SQL against the DuckDB in-memory database.

        For internal/CLI use only. REST endpoints MUST use parameterized
        template methods (get_symbol_bars, validate_symbol_coverage, etc.)
        and never pass client-supplied SQL here.

        Args:
            sql: SQL query string. May reference the ``historical`` VIEW.
            params: Optional positional parameters (``?`` placeholders).

        Returns:
            Query result as a pandas DataFrame.

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If DuckDB raises an error executing the SQL.
        """
        if not self._available or self._conn is None:
            raise ServiceUnavailableError(
                "HistoricalQueryService is not available"
            )
        try:
            if params:
                return self._conn.execute(sql, params).fetchdf()  # type: ignore[union-attr]
            return self._conn.execute(sql).fetchdf()  # type: ignore[union-attr]
        except Exception as exc:
            logger.error("HistoricalQueryService: query failed: %s", exc)
            raise QueryExecutionError(str(exc)) from exc

    def get_symbol_bars(
        self,
        symbol: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """Return OHLCV bars for a symbol within a date range.

        Args:
            symbol: Ticker symbol (e.g., ``"AAPL"``).
            start_date: Inclusive start date in YYYY-MM-DD format.
            end_date: Inclusive end date in YYYY-MM-DD format.

        Returns:
            DataFrame with columns (symbol, ts_event, date, open, high, low,
            close, volume), ordered by ts_event. Empty DataFrame if no data.

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If the underlying query fails.
        """
        sql = (
            "SELECT * FROM historical "
            "WHERE symbol = ? AND date >= ? AND date <= ? "
            "ORDER BY ts_event"
        )
        return self.query(sql, [symbol, start_date, end_date])

    def get_available_symbols(self) -> list[str]:
        """Return a sorted list of all symbols present in the cache.

        Result is cached for 60 seconds to avoid repeated full scans.

        Returns:
            Sorted list of ticker symbols.

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If the underlying query fails.
        """
        now = time.monotonic()
        if (
            self._symbols_cache is not None
            and (now - self._symbols_cache_ts) < _SYMBOLS_TTL_SECONDS
        ):
            return self._symbols_cache

        df = self.query("SELECT DISTINCT symbol FROM historical ORDER BY symbol")
        symbols: list[str] = df["symbol"].tolist() if not df.empty else []
        self._symbols_cache = symbols
        self._symbols_cache_ts = now
        return symbols

    def get_date_coverage(self, symbol: str | None = None) -> dict:
        """Return date coverage statistics for the cache or a single symbol.

        Args:
            symbol: If provided, returns per-symbol stats. If None, returns
                    aggregate stats across the entire cache.

        Returns:
            Dict with keys:
            - ``symbol_count`` (only when symbol is None)
            - ``min_date`` (ISO date string or None)
            - ``max_date`` (ISO date string or None)
            - ``bar_count`` (int)

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If the underlying query fails.
        """
        if symbol is not None:
            df = self.query(
                "SELECT MIN(ts_event) AS min_ts, MAX(ts_event) AS max_ts, "
                "COUNT(*) AS bar_count FROM historical WHERE symbol = ?",
                [symbol],
            )
            row = df.iloc[0] if not df.empty else None
            return {
                "min_date": str(row["min_ts"].date()) if row is not None and pd.notna(row["min_ts"]) else None,
                "max_date": str(row["max_ts"].date()) if row is not None and pd.notna(row["max_ts"]) else None,
                "bar_count": int(row["bar_count"]) if row is not None else 0,
            }

        df = self.query(
            "SELECT COUNT(DISTINCT symbol) AS symbol_count, "
            "MIN(ts_event) AS min_ts, MAX(ts_event) AS max_ts, "
            "COUNT(*) AS bar_count FROM historical"
        )
        row = df.iloc[0] if not df.empty else None
        return {
            "symbol_count": int(row["symbol_count"]) if row is not None else 0,
            "min_date": str(row["min_ts"].date()) if row is not None and pd.notna(row["min_ts"]) else None,
            "max_date": str(row["max_ts"].date()) if row is not None and pd.notna(row["max_ts"]) else None,
            "bar_count": int(row["bar_count"]) if row is not None else 0,
        }

    def validate_symbol_coverage(
        self,
        symbols: list[str],
        start_date: str,
        end_date: str,
        min_bars: int = 100,
    ) -> dict[str, bool]:
        """Check whether each symbol has enough bars in the date range.

        Designed for ExperimentRunner pre-filtering (Sprint 31.5).
        Executes a single batch query across all symbols.

        Args:
            symbols: List of ticker symbols to check.
            start_date: Inclusive start date in YYYY-MM-DD format.
            end_date: Inclusive end date in YYYY-MM-DD format.
            min_bars: Minimum bar count required to pass (default 100).

        Returns:
            Dict mapping each symbol to True (passes threshold) or False.

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If the underlying query fails.
        """
        if not symbols:
            return {}

        placeholders = ", ".join(["?" for _ in symbols])
        sql = (
            f"SELECT symbol, COUNT(*) AS bars FROM historical "
            f"WHERE symbol IN ({placeholders}) AND date >= ? AND date <= ? "
            f"GROUP BY symbol"
        )
        params: list = list(symbols) + [start_date, end_date]
        df = self.query(sql, params)

        bar_counts: dict[str, int] = {}
        if not df.empty:
            for _, row in df.iterrows():
                bar_counts[row["symbol"]] = int(row["bars"])

        return {sym: bar_counts.get(sym, 0) >= min_bars for sym in symbols}

    def get_cache_health(self) -> dict:
        """Return high-level health stats for the cache.

        Combines DuckDB aggregate stats with a filesystem size calculation.

        Returns:
            Dict with keys: total_symbols, date_range, total_bars,
            cache_dir, cache_size_bytes.

        Raises:
            ServiceUnavailableError: If the service is not available.
            QueryExecutionError: If the underlying query fails.
        """
        coverage = self.get_date_coverage()

        cache_size_bytes = 0
        cache_dir = self._config.cache_dir
        for root, _dirs, files in os.walk(cache_dir):
            for fname in files:
                try:
                    cache_size_bytes += os.path.getsize(os.path.join(root, fname))
                except OSError:
                    pass

        return {
            "total_symbols": coverage.get("symbol_count", 0),
            "date_range": {
                "min_date": coverage.get("min_date"),
                "max_date": coverage.get("max_date"),
            },
            "total_bars": coverage.get("bar_count", 0),
            "cache_dir": cache_dir,
            "cache_size_bytes": cache_size_bytes,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the DuckDB connection. Idempotent."""
        if self._conn is not None:
            try:
                self._conn.close()  # type: ignore[union-attr]
            except Exception:
                logger.debug("HistoricalQueryService: error closing DuckDB connection", exc_info=True)
            finally:
                self._conn = None
                self._available = False
                logger.info("HistoricalQueryService: DuckDB connection closed")
