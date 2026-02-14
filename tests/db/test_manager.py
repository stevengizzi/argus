"""Tests for the database manager."""

import pytest

from argus.db.manager import DatabaseManager


@pytest.fixture
async def db() -> DatabaseManager:
    """Create an in-memory database for testing."""
    manager = DatabaseManager(":memory:")
    await manager.initialize()
    yield manager
    await manager.close()


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    async def test_initialize_creates_tables(self, db: DatabaseManager) -> None:
        """initialize() creates all required tables."""
        # Query the sqlite_master to see what tables exist
        rows = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        table_names = [row["name"] for row in rows]

        assert "trades" in table_names
        assert "orders" in table_names
        assert "positions" in table_names
        assert "daily_summaries" in table_names
        assert "risk_events" in table_names
        assert "system_events" in table_names

    async def test_execute_and_fetch(self, db: DatabaseManager) -> None:
        """execute() and fetch methods work correctly."""
        # Insert a trade
        await db.execute(
            """
            INSERT INTO trades (
                id, strategy_id, symbol, side, entry_price, entry_time,
                exit_price, exit_time, shares, stop_price, exit_reason,
                gross_pnl, net_pnl, outcome
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "test_id_001",
                "strat_orb",
                "AAPL",
                "buy",
                150.0,
                "2026-02-15T10:00:00",
                152.0,
                "2026-02-15T10:30:00",
                100,
                148.0,
                "target_1",
                200.0,
                198.0,
                "win",
            ),
        )
        await db.commit()

        # Fetch the trade
        row = await db.fetch_one("SELECT * FROM trades WHERE id = ?", ("test_id_001",))
        assert row is not None
        assert row["symbol"] == "AAPL"
        assert row["strategy_id"] == "strat_orb"

    async def test_fetch_all(self, db: DatabaseManager) -> None:
        """fetch_all() returns all matching rows."""
        # Insert multiple trades
        for i in range(3):
            await db.execute(
                """
                INSERT INTO trades (
                    id, strategy_id, symbol, side, entry_price, entry_time,
                    exit_price, exit_time, shares, stop_price, exit_reason,
                    gross_pnl, net_pnl, outcome
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"test_id_{i:03d}",
                    "strat_orb",
                    "AAPL",
                    "buy",
                    150.0,
                    "2026-02-15T10:00:00",
                    152.0,
                    "2026-02-15T10:30:00",
                    100,
                    148.0,
                    "target_1",
                    200.0,
                    198.0,
                    "win",
                ),
            )
        await db.commit()

        rows = await db.fetch_all("SELECT * FROM trades WHERE symbol = ?", ("AAPL",))
        assert len(rows) == 3

    async def test_is_connected(self, db: DatabaseManager) -> None:
        """is_connected property reflects connection state."""
        assert db.is_connected is True

        await db.close()
        assert db.is_connected is False

    async def test_not_initialized_raises(self) -> None:
        """Operations on uninitialized database raise RuntimeError."""
        db = DatabaseManager(":memory:")

        with pytest.raises(RuntimeError, match="not initialized"):
            await db.execute("SELECT 1")

        with pytest.raises(RuntimeError, match="not initialized"):
            async with db.connection():
                pass
