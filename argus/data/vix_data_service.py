"""VIX Data Service — daily VIX/SPX data persistence and staleness tracking.

Stores daily VIX and SPX OHLC data plus derived metrics in a separate SQLite
database (data/vix_landscape.db) following the DEC-345 separate DB pattern.

Sprint 27.9, Session 1a — skeleton only. yfinance fetch methods added in
Session 1b.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from argus.data.vix_config import VixRegimeConfig

logger = logging.getLogger(__name__)

_ET = ZoneInfo("America/New_York")

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
        sql = f"INSERT OR REPLACE INTO vix_daily ({', '.join(_COLUMNS)}) VALUES ({placeholders})"

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
        Adjusts for weekends (Saturday/Sunday → Friday).
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

    def fetch_historical(self) -> None:
        """Fetch full historical VIX/SPX data. Not implemented yet.

        Raises:
            NotImplementedError: Always — Session 1b adds yfinance fetch.
        """
        raise NotImplementedError("yfinance fetch added in Session 1b")

    def fetch_incremental(self) -> None:
        """Fetch incremental VIX/SPX data since last persisted date.

        Raises:
            NotImplementedError: Always — Session 1b adds yfinance fetch.
        """
        raise NotImplementedError("yfinance fetch added in Session 1b")
