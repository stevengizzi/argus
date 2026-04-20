"""Database connection manager for Argus.

Provides async SQLite database access using aiosqlite with WAL mode.
All database operations should go through this manager.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite

logger = logging.getLogger(__name__)

# Path to the schema file
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


class DatabaseManager:
    """Async SQLite database manager.

    Provides connection pooling and schema initialization for the
    Argus trading database.

    Usage:
        db = DatabaseManager("data/argus.db")
        await db.initialize()

        async with db.connection() as conn:
            await conn.execute("SELECT * FROM trades")
            rows = await conn.fetchall()

        await db.close()
    """

    def __init__(self, db_path: str | Path) -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file.
                Use ":memory:" for an in-memory database (testing).
        """
        self._db_path = str(db_path)
        self._connection: aiosqlite.Connection | None = None

    async def initialize(self) -> None:
        """Initialize the database connection and schema.

        Creates the database file if it doesn't exist, enables WAL mode,
        and applies the schema.

        Raises:
            aiosqlite.Error: If database initialization fails.
        """
        # Ensure parent directory exists for file-based databases
        if self._db_path != ":memory:":
            db_file = Path(self._db_path)
            db_file.parent.mkdir(parents=True, exist_ok=True)

        self._connection = await aiosqlite.connect(self._db_path)

        # Enable row factory for dict-like access
        self._connection.row_factory = aiosqlite.Row

        # Enable WAL mode for concurrent access
        await self._connection.execute("PRAGMA journal_mode = WAL")
        await self._connection.execute("PRAGMA foreign_keys = ON")

        # Apply schema
        await self._apply_schema()

        logger.info("Database initialized: %s", self._db_path)

    async def _apply_schema(self) -> None:
        """Apply the database schema from the SQL file."""
        if self._connection is None:
            raise RuntimeError("Database not initialized")

        schema_sql = SCHEMA_PATH.read_text()
        await self._connection.executescript(schema_sql)
        await self._connection.commit()

        # Migration: add quality columns to trades (Sprint 24.1)
        try:
            await self._connection.execute(
                "ALTER TABLE trades ADD COLUMN quality_grade TEXT"
            )
            await self._connection.commit()
        except Exception:
            pass  # Column already exists
        try:
            await self._connection.execute(
                "ALTER TABLE trades ADD COLUMN quality_score REAL"
            )
            await self._connection.commit()
        except Exception:
            pass  # Column already exists

        # Migration: add MFE/MAE columns to trades (Sprint 29.5 S6)
        for col_def in (
            "mfe_r REAL",
            "mae_r REAL",
            "mfe_price REAL",
            "mae_price REAL",
        ):
            try:
                await self._connection.execute(
                    f"ALTER TABLE trades ADD COLUMN {col_def}"
                )
                await self._connection.commit()
            except Exception:
                pass  # Column already exists

        # Migration: add config_fingerprint column to trades (Sprint 32 S3)
        try:
            await self._connection.execute(
                "ALTER TABLE trades ADD COLUMN config_fingerprint TEXT"
            )
            await self._connection.commit()
        except Exception:
            pass  # Column already exists

        # Migration: add entry_price_known column to trades (DEF-159)
        try:
            await self._connection.execute(
                "ALTER TABLE trades ADD COLUMN entry_price_known INTEGER NOT NULL DEFAULT 1"
            )
            await self._connection.commit()
        except Exception:
            pass  # Column already exists

    @asynccontextmanager
    async def connection(self) -> AsyncIterator[aiosqlite.Connection]:
        """Get a database connection context manager.

        Yields:
            The active database connection.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")
        yield self._connection

    async def execute(
        self, sql: str, parameters: tuple[object, ...] | dict[str, object] | None = None
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement.

        Args:
            sql: The SQL statement to execute.
            parameters: Optional parameters for the statement.

        Returns:
            The cursor from the execution.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        if parameters is None:
            return await self._connection.execute(sql)
        return await self._connection.execute(sql, parameters)

    async def execute_many(
        self, sql: str, parameters: list[tuple[object, ...]]
    ) -> aiosqlite.Cursor:
        """Execute a SQL statement with multiple parameter sets.

        Args:
            sql: The SQL statement to execute.
            parameters: List of parameter tuples.

        Returns:
            The cursor from the execution.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        return await self._connection.executemany(sql, parameters)

    async def fetch_one(
        self, sql: str, parameters: tuple[object, ...] | dict[str, object] | None = None
    ) -> aiosqlite.Row | None:
        """Execute a query and fetch one row.

        Args:
            sql: The SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            The first row, or None if no results.

        Raises:
            RuntimeError: If database is not initialized.
        """
        cursor = await self.execute(sql, parameters)
        return await cursor.fetchone()

    async def fetch_all(
        self, sql: str, parameters: tuple[object, ...] | dict[str, object] | None = None
    ) -> list[aiosqlite.Row]:
        """Execute a query and fetch all rows.

        Args:
            sql: The SQL query to execute.
            parameters: Optional parameters for the query.

        Returns:
            List of all rows.

        Raises:
            RuntimeError: If database is not initialized.
        """
        cursor = await self.execute(sql, parameters)
        return await cursor.fetchall()

    async def commit(self) -> None:
        """Commit the current transaction.

        Raises:
            RuntimeError: If database is not initialized.
        """
        if self._connection is None:
            raise RuntimeError("Database not initialized. Call initialize() first.")

        await self._connection.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._connection is not None:
            await self._connection.close()
            self._connection = None
            logger.info("Database connection closed")

    @property
    def is_connected(self) -> bool:
        """Check if the database is connected."""
        return self._connection is not None
