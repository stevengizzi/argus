"""VIX Data Service — daily VIX/SPX data persistence and staleness tracking.

Stores daily VIX and SPX OHLC data plus derived metrics in a separate SQLite
database (data/vix_landscape.db) following the DEC-345 separate DB pattern.

Sprint 27.9, Session 1a — skeleton + persistence.
Sprint 27.9, Session 1b — yfinance integration + derived metrics.
"""

from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import aiosqlite
import numpy as np
import pandas as pd
import yfinance as yf
from scipy.stats import percentileofscore

from argus.data.migrations import apply_migrations
from argus.data.migrations.vix_landscape import MIGRATIONS, SCHEMA_NAME
from argus.data.vix_config import VixRegimeConfig

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

_MARKET_OPEN = time(9, 30)
_MARKET_CLOSE_BUFFER = time(16, 15)

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS vix_daily (
    date TEXT PRIMARY KEY,
    vix_open REAL,
    vix_high REAL,
    vix_low REAL,
    vix_close REAL,
    spx_open REAL,
    spx_high REAL,
    spx_low REAL,
    spx_close REAL,
    vol_of_vol_ratio REAL,
    vix_percentile REAL,
    term_structure_proxy REAL,
    realized_vol_20d REAL,
    variance_risk_premium REAL
)
"""

_COLUMNS = [
    "date",
    "vix_open",
    "vix_high",
    "vix_low",
    "vix_close",
    "spx_open",
    "spx_high",
    "spx_low",
    "spx_close",
    "vol_of_vol_ratio",
    "vix_percentile",
    "term_structure_proxy",
    "realized_vol_20d",
    "variance_risk_premium",
]


class VIXDataUnavailable(Exception):
    """Raised when yfinance returns no data for VIX or SPX."""


class VIXDataService:
    """Daily VIX/SPX data persistence and staleness tracking.

    Manages a SQLite database of daily VIX and SPX OHLC data plus derived
    metrics (vol-of-vol ratio, VIX percentile, term structure proxy,
    realized vol, variance risk premium).

    Args:
        config: VixRegimeConfig with staleness and window parameters.
        db_path: Filesystem path for the SQLite database.
    """

    def __init__(
        self,
        config: VixRegimeConfig,
        db_path: str = "data/vix_landscape.db",
    ) -> None:
        """Initialize the VIX data service.

        Args:
            config: VIX regime configuration.
            db_path: Path to the SQLite database file.
        """
        self._config = config
        self._db_path = db_path
        self._ready = False
        self._update_task: asyncio.Task[None] | None = None
        self._init_db()

    def _init_db(self) -> None:
        """Create the database table if it does not exist. Enable WAL mode."""
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self._db_path)
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute(_CREATE_TABLE_SQL)
            conn.commit()
        finally:
            conn.close()

    def persist_daily(self, rows: list[dict[str, Any]]) -> None:
        """Batch insert or replace daily VIX/SPX rows.

        Args:
            rows: List of dicts with keys matching vix_daily column names.
                  Each dict must include at least a 'date' key.
        """
        if not rows:
            return

        placeholders = ", ".join(["?"] * len(_COLUMNS))
        sql = (
            f"INSERT OR REPLACE INTO vix_daily "
            f"({', '.join(_COLUMNS)}) VALUES ({placeholders})"
        )

        conn = sqlite3.connect(self._db_path)
        try:
            values = [
                tuple(row.get(col) for col in _COLUMNS)
                for row in rows
            ]
            conn.executemany(sql, values)
            conn.commit()
            self._ready = True
            logger.info("VIXDataService: persisted %d daily rows", len(rows))
        finally:
            conn.close()

    def load_from_db(self) -> pd.DataFrame:
        """Load all daily rows from the database.

        Returns:
            DataFrame with columns matching vix_daily schema, indexed by date.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            df = pd.read_sql_query(
                "SELECT * FROM vix_daily ORDER BY date ASC",
                conn,
            )
            if not df.empty:
                self._ready = True
            return df
        finally:
            conn.close()

    def get_latest_daily(self) -> dict[str, Any] | None:
        """Return the last completed trading day's data.

        Returns:
            Dict with all vix_daily columns plus a 'data_date' field.
            If stale, returns dict with 'data_date' and 'vix_close' but
            None for all derived metrics. Returns None entirely if no data.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM vix_daily ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row is None:
                return None

            result = dict(row)
            result["data_date"] = result["date"]

            if self.is_stale:
                return {
                    "data_date": result["date"],
                    "vix_close": result.get("vix_close"),
                    "vol_of_vol_ratio": None,
                    "vix_percentile": None,
                    "term_structure_proxy": None,
                    "realized_vol_20d": None,
                    "variance_risk_premium": None,
                }

            return result
        finally:
            conn.close()

    def get_history(self, days_back: int) -> list[dict[str, Any]] | None:
        """Return the last N daily records, ordered by date descending.

        Args:
            days_back: Number of most recent records to return.

        Returns:
            List of dicts (most recent first), or None if no data.
        """
        if days_back < 1:
            return None

        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM vix_daily ORDER BY date DESC LIMIT ?",
                (days_back,),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_history_range(
        self, start_date: str, end_date: str
    ) -> list[dict[str, Any]] | None:
        """Return daily records within a date range, ordered by date ascending.

        Args:
            start_date: Start date inclusive (YYYY-MM-DD format).
            end_date: End date inclusive (YYYY-MM-DD format).

        Returns:
            List of dicts (oldest first), or None if no data in range.
        """
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        try:
            cursor = conn.execute(
                "SELECT * FROM vix_daily WHERE date >= ? AND date <= ? "
                "ORDER BY date ASC",
                (start_date, end_date),
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            return [dict(row) for row in rows]
        finally:
            conn.close()

    @property
    def config(self) -> VixRegimeConfig:
        """Public read-only access to the underlying VixRegimeConfig.

        Added FIX-05 (DEF-091/DEF-170): RegimeClassifierV2 previously reached
        into ``_config`` to extract boundary parameters. This property
        replaces that private-attr access with a supported surface.
        """
        return self._config

    @property
    def is_ready(self) -> bool:
        """True after initial data load is complete."""
        return self._ready

    @property
    def is_stale(self) -> bool:
        """True when last data_date is more than max_staleness_days business days ago.

        Uses pd.bdate_range to count business days between the last data date
        and the last completed trading day.
        """
        conn = sqlite3.connect(self._db_path)
        try:
            cursor = conn.execute(
                "SELECT date FROM vix_daily ORDER BY date DESC LIMIT 1"
            )
            row = cursor.fetchone()
            if row is None:
                return True

            last_data_date = date.fromisoformat(row[0])
            last_trading = self._last_trading_day()

            if last_data_date >= last_trading:
                return False

            # Count business days between last data and last trading day
            bdays = pd.bdate_range(
                start=last_data_date + timedelta(days=1),
                end=last_trading,
            )
            return len(bdays) > self._config.max_staleness_days
        finally:
            conn.close()

    def _last_trading_day(self) -> date:
        """Return the last completed US trading day.

        If before 4:15 PM ET today, returns yesterday's trading day.
        Adjusts for weekends (Saturday/Sunday -> Friday).
        """
        now_et = datetime.now(_ET)
        market_close_plus_buffer = time(16, 15)

        if now_et.time() < market_close_plus_buffer:
            candidate = now_et.date() - timedelta(days=1)
        else:
            candidate = now_et.date()

        # Roll back from weekends to Friday
        weekday = candidate.weekday()
        if weekday == 5:  # Saturday
            candidate -= timedelta(days=1)
        elif weekday == 6:  # Sunday
            candidate -= timedelta(days=2)

        return candidate

    # ------------------------------------------------------------------
    # yfinance fetch methods (Session 1b)
    # ------------------------------------------------------------------

    def fetch_historical(self, years: int | None = None) -> pd.DataFrame:
        """Download historical VIX and SPX daily OHLCV from yfinance.

        Args:
            years: Number of years of history to fetch. Defaults to
                   config.history_years.

        Returns:
            DataFrame with vix_* and spx_* OHLC columns, indexed by date string.

        Raises:
            VIXDataUnavailable: If yfinance returns empty data for both symbols.
        """
        if years is None:
            years = self._config.history_years

        end_date = date.today() + timedelta(days=1)
        start_date = date.today() - timedelta(days=years * 365)

        return self._fetch_range(start_date, end_date)

    def fetch_incremental(self, last_date: date) -> pd.DataFrame:
        """Download VIX/SPX data from last_date + 1 day to today.

        Args:
            last_date: Last date already in the database.

        Returns:
            DataFrame with new rows only. May be empty if no new data.

        Raises:
            VIXDataUnavailable: If yfinance returns empty data for both symbols.
        """
        start_date = last_date + timedelta(days=1)
        end_date = date.today() + timedelta(days=1)

        if start_date > date.today():
            return pd.DataFrame()

        return self._fetch_range(start_date, end_date)

    def _fetch_range(self, start_date: date, end_date: date) -> pd.DataFrame:
        """Download and merge VIX + SPX data for a date range.

        Args:
            start_date: Start of range (inclusive).
            end_date: End of range (exclusive, yfinance convention).

        Returns:
            Merged DataFrame with vix_* and spx_* columns.

        Raises:
            VIXDataUnavailable: If yfinance returns empty data for both symbols.
        """
        vix_symbol = self._config.yahoo_symbol_vix
        spx_symbol = self._config.yahoo_symbol_spx

        start_str = start_date.isoformat()
        end_str = end_date.isoformat()

        vix_df = yf.download(
            vix_symbol, start=start_str, end=end_str, progress=False
        )
        spx_df = yf.download(
            spx_symbol, start=start_str, end=end_str, progress=False
        )

        if vix_df.empty and spx_df.empty:
            raise VIXDataUnavailable(
                f"yfinance returned no data for {vix_symbol} and "
                f"{spx_symbol} from {start_str} to {end_str}"
            )

        if vix_df.empty:
            logger.warning(
                "VIXDataService: no VIX data from yfinance for %s to %s",
                start_str, end_str,
            )
        if spx_df.empty:
            logger.warning(
                "VIXDataService: no SPX data from yfinance for %s to %s",
                start_str, end_str,
            )

        # Flatten MultiIndex columns if present (yfinance >=0.2.31)
        vix_df = self._flatten_columns(vix_df)
        spx_df = self._flatten_columns(spx_df)

        # Rename columns with vix_/spx_ prefix
        vix_renamed = pd.DataFrame({
            "vix_open": vix_df["Open"] if "Open" in vix_df.columns else np.nan,
            "vix_high": vix_df["High"] if "High" in vix_df.columns else np.nan,
            "vix_low": vix_df["Low"] if "Low" in vix_df.columns else np.nan,
            "vix_close": (
                vix_df["Close"] if "Close" in vix_df.columns else np.nan
            ),
        }, index=vix_df.index) if not vix_df.empty else pd.DataFrame()

        spx_renamed = pd.DataFrame({
            "spx_open": spx_df["Open"] if "Open" in spx_df.columns else np.nan,
            "spx_high": spx_df["High"] if "High" in spx_df.columns else np.nan,
            "spx_low": spx_df["Low"] if "Low" in spx_df.columns else np.nan,
            "spx_close": (
                spx_df["Close"] if "Close" in spx_df.columns else np.nan
            ),
        }, index=spx_df.index) if not spx_df.empty else pd.DataFrame()

        # Merge on date index (outer join to keep partial data)
        if vix_renamed.empty:
            merged = spx_renamed
        elif spx_renamed.empty:
            merged = vix_renamed
        else:
            merged = vix_renamed.join(spx_renamed, how="outer")

        # Convert DatetimeIndex to date strings
        merged["date"] = merged.index.strftime("%Y-%m-%d")
        merged = merged.reset_index(drop=True)

        logger.info(
            "VIXDataService: fetched %d rows from yfinance (%s to %s)",
            len(merged), start_date, end_date,
        )

        return merged

    @staticmethod
    def _flatten_columns(df: pd.DataFrame) -> pd.DataFrame:
        """Flatten MultiIndex columns from yfinance (e.g., ('Close', '^VIX')).

        Args:
            df: DataFrame potentially with MultiIndex columns.

        Returns:
            DataFrame with single-level column names.
        """
        if isinstance(df.columns, pd.MultiIndex):
            df = df.copy()
            df.columns = df.columns.get_level_values(0)
        return df

    # ------------------------------------------------------------------
    # Derived metrics (Session 1b)
    # ------------------------------------------------------------------

    def compute_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute 5 derived metric columns on a VIX/SPX DataFrame.

        Columns added:
        - vol_of_vol_ratio: rolling short/long std of VIX close
        - vix_percentile: rolling 252-day percentile rank
        - term_structure_proxy: VIX close / rolling MA of VIX close
        - realized_vol_20d: annualized 20-day rolling std of SPX log returns
        - variance_risk_premium: VIX^2 - (RV_20d * 100)^2

        Args:
            df: DataFrame with at least 'vix_close' and 'spx_close' columns.

        Returns:
            DataFrame with 5 additional derived metric columns.
        """
        df = df.copy()

        short_w = self._config.vol_short_window
        long_w = self._config.vol_long_window
        pct_w = self._config.percentile_window
        ma_w = self._config.ma_window
        rv_w = self._config.rv_window

        # 1. Vol-of-vol ratio: sigma_short / sigma_long
        if "vix_close" in df.columns:
            sigma_short = df["vix_close"].rolling(short_w).std()
            sigma_long = df["vix_close"].rolling(long_w).std()

            epsilon = 1e-10
            # Guard sigma_long == 0: set ratio to NaN and log warning
            zero_mask = sigma_long.abs() < epsilon
            if zero_mask.any():
                logger.warning(
                    "VIXDataService: sigma_long is zero for %d rows, "
                    "setting vol_of_vol_ratio to NaN",
                    int(zero_mask.sum()),
                )
            safe_sigma_long = sigma_long.where(~zero_mask, np.nan)
            df["vol_of_vol_ratio"] = sigma_short / safe_sigma_long
        else:
            df["vol_of_vol_ratio"] = np.nan

        # 2. VIX percentile: rolling 252-day percentile rank
        if "vix_close" in df.columns:
            df["vix_percentile"] = df["vix_close"].rolling(pct_w).apply(
                lambda x: percentileofscore(x, x.iloc[-1]) / 100.0,
                raw=False,
            )
        else:
            df["vix_percentile"] = np.nan

        # 3. Term structure proxy: VIX close / rolling MA of VIX close
        if "vix_close" in df.columns:
            vix_ma = df["vix_close"].rolling(ma_w).mean()
            epsilon = 1e-10
            safe_ma = vix_ma.where(vix_ma.abs() >= epsilon, np.nan)
            df["term_structure_proxy"] = df["vix_close"] / safe_ma
        else:
            df["term_structure_proxy"] = np.nan

        # 4. Realized vol 20d: annualized rolling std of SPX log returns
        if "spx_close" in df.columns:
            log_returns = np.log(
                df["spx_close"] / df["spx_close"].shift(1)
            )
            df["realized_vol_20d"] = (
                log_returns.rolling(rv_w).std() * np.sqrt(252)
            )
        else:
            df["realized_vol_20d"] = np.nan

        # 5. Variance risk premium: VIX^2 - (RV_20d * 100)^2
        #    Both VIX and RV are in percentage-point units.
        #    VIX is already in % points (e.g., 20 = 20%).
        #    RV_20d is a decimal (e.g., 0.15 = 15%), so multiply by 100.
        if "vix_close" in df.columns and "realized_vol_20d" in df.columns:
            rv_pct = df["realized_vol_20d"] * 100.0
            df["variance_risk_premium"] = (
                df["vix_close"] ** 2 - rv_pct ** 2
            )
        else:
            df["variance_risk_premium"] = np.nan

        return df

    # ------------------------------------------------------------------
    # Initialization and daily update (Session 1b)
    # ------------------------------------------------------------------

    async def initialize(self) -> None:
        """Load cached data from SQLite, fetch missing data, compute metrics.

        Trust-cache-on-startup pattern: loads existing DB data first, then
        determines how much new data to fetch based on staleness.
        """
        # Sprint 31.91 Impromptu C: schema managed by the migration framework.
        # Sync ``_init_db()`` already created the table via CREATE TABLE IF NOT
        # EXISTS so applying v1 here only records schema_version=1.
        async with aiosqlite.connect(self._db_path) as conn:
            await apply_migrations(
                conn, schema_name=SCHEMA_NAME, migrations=MIGRATIONS
            )

        # Step 1: Load from SQLite (trust cache)
        df = self.load_from_db()
        last_date: date | None = None

        if not df.empty:
            last_date_str = df["date"].iloc[-1]
            last_date = date.fromisoformat(last_date_str)
            logger.info(
                "VIXDataService: loaded %d cached rows, last date: %s",
                len(df), last_date_str,
            )

        # Step 2: Determine missing data gap
        today = date.today()
        if last_date is not None:
            missing_days = (today - last_date).days
        else:
            missing_days = 9999  # Force full historical fetch

        # Step 3: Fetch missing data
        try:
            if missing_days > 30 or last_date is None:
                logger.info(
                    "VIXDataService: fetching full historical data "
                    "(%d days missing)",
                    missing_days,
                )
                new_df = await asyncio.to_thread(self.fetch_historical)
            elif missing_days > 0:
                logger.info(
                    "VIXDataService: fetching incremental data "
                    "(%d days missing since %s)",
                    missing_days, last_date,
                )
                new_df = await asyncio.to_thread(
                    self.fetch_incremental, last_date
                )
            else:
                new_df = pd.DataFrame()
        except VIXDataUnavailable:
            logger.warning(
                "VIXDataService: yfinance unavailable, using cached data"
            )
            new_df = pd.DataFrame()

        # Step 4: Merge new data with cached, compute derived, persist
        if not new_df.empty:
            if not df.empty:
                # Combine cached + new, dedup by date keeping new
                combined = pd.concat([df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(
                    subset=["date"], keep="last"
                )
                combined = combined.sort_values("date").reset_index(drop=True)
            else:
                combined = new_df.sort_values("date").reset_index(drop=True)

            combined = self.compute_derived_metrics(combined)
            rows = combined.to_dict("records")
            self.persist_daily(rows)
        elif not df.empty:
            self._ready = True

        self._start_daily_update_task()
        logger.info("VIXDataService: initialization complete, ready=%s", self._ready)

    def _start_daily_update_task(self) -> None:
        """Start an asyncio background task for periodic incremental updates.

        Runs fetch_incremental + compute_derived_metrics + persist every
        update_interval_seconds, but only during US market hours (9:30-16:15 ET).
        """
        if self._update_task is not None:
            return

        async def _update_loop() -> None:
            interval = self._config.update_interval_seconds
            while True:
                await asyncio.sleep(interval)
                try:
                    now_et = datetime.now(_ET)
                    if not (
                        _MARKET_OPEN
                        <= now_et.time()
                        <= _MARKET_CLOSE_BUFFER
                    ):
                        continue

                    # Weekday check (Mon=0 .. Fri=4)
                    if now_et.weekday() > 4:
                        continue

                    df = self.load_from_db()
                    if df.empty:
                        continue

                    last_date_str = df["date"].iloc[-1]
                    last_date = date.fromisoformat(last_date_str)

                    new_df = await asyncio.to_thread(
                        self.fetch_incremental, last_date
                    )
                    if new_df.empty:
                        continue

                    combined = pd.concat([df, new_df], ignore_index=True)
                    combined = combined.drop_duplicates(
                        subset=["date"], keep="last"
                    )
                    combined = combined.sort_values(
                        "date"
                    ).reset_index(drop=True)
                    combined = self.compute_derived_metrics(combined)

                    rows = combined.to_dict("records")
                    self.persist_daily(rows)
                    logger.info(
                        "VIXDataService: daily update added %d new rows",
                        len(new_df),
                    )
                except VIXDataUnavailable:
                    logger.warning(
                        "VIXDataService: daily update skipped — "
                        "yfinance unavailable"
                    )
                except Exception:
                    logger.exception(
                        "VIXDataService: daily update failed"
                    )

        self._update_task = asyncio.create_task(_update_loop())

    async def shutdown(self) -> None:
        """Cancel the background update task and await its termination.

        Public cleanup hook for lifespan handlers. Prefer this over reaching
        into ``_update_task`` from outside the service (DEF-091 contract).
        Safe to call when no task is running.
        """
        import contextlib

        task = self._update_task
        if task is None:
            return
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task
        self._update_task = None
