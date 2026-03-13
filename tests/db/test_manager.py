"""Tests for the database manager."""

import pytest

from argus.db.manager import DatabaseManager


class TestDatabaseManager:
    """Tests for DatabaseManager."""

    async def test_initialize_creates_tables(self, db: DatabaseManager) -> None:
        """initialize() creates all required tables."""
        # Query the sqlite_master to see what tables exist
        rows = await db.fetch_all("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        table_names = [row["name"] for row in rows]

        assert "trades" in table_names
        assert "orders" in table_names
        assert "positions" in table_names
        assert "daily_summaries" in table_names
        assert "risk_events" in table_names
        assert "system_events" in table_names
        # Tables from Architecture doc Section 3.8
        assert "strategy_daily_performance" in table_names
        assert "account_daily_snapshot" in table_names
        assert "orchestrator_decisions" in table_names
        assert "approval_log" in table_names
        assert "journal_entries" in table_names
        # Quality Engine (Sprint 24)
        assert "quality_history" in table_names
        # Note: system_health is deferred to Step 10

    async def test_quality_history_table_created(self, db: DatabaseManager) -> None:
        """quality_history table has expected columns and indexes."""
        # Verify columns via pragma
        cols = await db.fetch_all("PRAGMA table_info(quality_history)")
        col_names = [c["name"] for c in cols]
        expected_cols = [
            "id", "symbol", "strategy_id", "scored_at",
            "pattern_strength", "catalyst_quality", "volume_profile",
            "historical_match", "regime_alignment",
            "composite_score", "grade", "risk_tier",
            "entry_price", "stop_price", "calculated_shares",
            "signal_context",
            "outcome_trade_id", "outcome_realized_pnl", "outcome_r_multiple",
            "created_at",
        ]
        for col in expected_cols:
            assert col in col_names, f"Missing column: {col}"

        # Verify indexes exist
        indexes = await db.fetch_all(
            "SELECT name FROM sqlite_master WHERE type='index' "
            "AND tbl_name='quality_history'"
        )
        idx_names = [i["name"] for i in indexes]
        assert "idx_quality_history_symbol" in idx_names
        assert "idx_quality_history_strategy" in idx_names
        assert "idx_quality_history_scored_at" in idx_names
        assert "idx_quality_history_grade" in idx_names

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
