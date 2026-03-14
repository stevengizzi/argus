"""Tests for quality column wiring through trades persistence chain (Sprint 24.1 S1a)."""

from datetime import datetime
from pathlib import Path

import pytest

from argus.analytics.trade_logger import TradeLogger
from argus.db.manager import DatabaseManager
from argus.execution.order_manager import ManagedPosition
from argus.models.trading import ExitReason, OrderSide, Trade


# ---------------------------------------------------------------------------
# ManagedPosition quality fields
# ---------------------------------------------------------------------------


class TestManagedPositionQualityFields:
    """ManagedPosition dataclass stores quality data from signal."""

    def test_managed_position_with_quality_populated(self) -> None:
        """ManagedPosition accepts quality_grade and quality_score."""
        pos = ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=150.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            shares_total=100,
            shares_remaining=100,
            stop_price=148.0,
            original_stop_price=148.0,
            stop_order_id="stop_1",
            t1_price=152.0,
            t1_order_id="t1_1",
            t1_shares=50,
            t1_filled=False,
            t2_price=154.0,
            high_watermark=150.0,
            quality_grade="B+",
            quality_score=72.5,
        )
        assert pos.quality_grade == "B+"
        assert pos.quality_score == 72.5

    def test_managed_position_default_quality(self) -> None:
        """ManagedPosition defaults quality fields when not provided."""
        pos = ManagedPosition(
            symbol="AAPL",
            strategy_id="orb_breakout",
            entry_price=150.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            shares_total=100,
            shares_remaining=100,
            stop_price=148.0,
            original_stop_price=148.0,
            stop_order_id="stop_1",
            t1_price=152.0,
            t1_order_id="t1_1",
            t1_shares=50,
            t1_filled=False,
            t2_price=154.0,
            high_watermark=150.0,
        )
        assert pos.quality_grade == ""
        assert pos.quality_score == 0.0


# ---------------------------------------------------------------------------
# Trade model quality fields
# ---------------------------------------------------------------------------


class TestTradeModelQualityFields:
    """Trade model accepts and serializes quality data."""

    def test_trade_with_quality_fields(self) -> None:
        """Trade model accepts quality_grade and quality_score."""
        trade = Trade(
            strategy_id="orb_breakout",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            exit_price=152.0,
            exit_time=datetime(2026, 3, 14, 10, 30),
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.0,
            quality_grade="A-",
            quality_score=85.3,
        )
        assert trade.quality_grade == "A-"
        assert trade.quality_score == 85.3
        # model_post_init still calculates derived fields correctly
        assert trade.net_pnl == 200.0  # no commission
        assert trade.outcome.value == "win"

    def test_trade_without_quality_fields_uses_defaults(self) -> None:
        """Trade model defaults quality fields for backward compatibility."""
        trade = Trade(
            strategy_id="orb_breakout",
            symbol="AAPL",
            side=OrderSide.BUY,
            entry_price=150.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            exit_price=149.0,
            exit_time=datetime(2026, 3, 14, 10, 30),
            shares=100,
            stop_price=148.0,
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-100.0,
        )
        assert trade.quality_grade == ""
        assert trade.quality_score == 0.0


# ---------------------------------------------------------------------------
# TradeLogger round-trip
# ---------------------------------------------------------------------------


class TestTradeLoggerQualityRoundTrip:
    """TradeLogger persists and reads quality data correctly."""

    async def test_log_trade_with_quality_data_round_trips(
        self, trade_logger: TradeLogger
    ) -> None:
        """Insert Trade with quality data, read back, verify fields match."""
        trade = Trade(
            strategy_id="orb_breakout",
            symbol="NVDA",
            side=OrderSide.BUY,
            entry_price=200.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            exit_price=204.0,
            exit_time=datetime(2026, 3, 14, 11, 0),
            shares=50,
            stop_price=198.0,
            exit_reason=ExitReason.TARGET_1,
            gross_pnl=200.0,
            quality_grade="B+",
            quality_score=72.5,
        )
        trade_id = await trade_logger.log_trade(trade)
        retrieved = await trade_logger.get_trade(trade_id)

        assert retrieved is not None
        assert retrieved.quality_grade == "B+"
        assert retrieved.quality_score == 72.5

    async def test_log_trade_without_quality_data_round_trips(
        self, trade_logger: TradeLogger
    ) -> None:
        """Insert Trade with default quality, read back, verify defaults."""
        trade = Trade(
            strategy_id="orb_breakout",
            symbol="TSLA",
            side=OrderSide.BUY,
            entry_price=300.0,
            entry_time=datetime(2026, 3, 14, 10, 0),
            exit_price=298.0,
            exit_time=datetime(2026, 3, 14, 10, 30),
            shares=30,
            stop_price=296.0,
            exit_reason=ExitReason.STOP_LOSS,
            gross_pnl=-60.0,
        )
        trade_id = await trade_logger.log_trade(trade)
        retrieved = await trade_logger.get_trade(trade_id)

        assert retrieved is not None
        assert retrieved.quality_grade == ""
        assert retrieved.quality_score == 0.0

    async def test_row_to_trade_with_null_quality_columns(
        self, db: DatabaseManager
    ) -> None:
        """Legacy rows with NULL quality columns load without error."""
        # Insert a row with raw SQL, omitting quality columns entirely
        await db.execute(
            """
            INSERT INTO trades (
                id, strategy_id, symbol, asset_class, side,
                entry_price, entry_time, exit_price, exit_time,
                shares, stop_price, target_prices, exit_reason,
                gross_pnl, commission, net_pnl, r_multiple,
                hold_duration_seconds, outcome, rationale, notes
            ) VALUES (
                'legacy_001', 'orb_breakout', 'AAPL', 'us_stocks', 'buy',
                150.0, '2026-03-14T10:00:00', 151.0, '2026-03-14T10:30:00',
                100, 148.0, '[]', 'target_1',
                100.0, 1.0, 99.0, 0.5,
                1800, 'win', '', ''
            )
            """
        )
        await db.commit()

        logger = TradeLogger(db)
        trade = await logger.get_trade("legacy_001")

        assert trade is not None
        assert trade.quality_grade == ""
        assert trade.quality_score == 0.0


# ---------------------------------------------------------------------------
# Schema migration idempotency
# ---------------------------------------------------------------------------


class TestSchemaMigrationIdempotent:
    """Schema migration adds columns safely on existing databases."""

    async def test_migration_runs_twice_without_error(
        self, tmp_path: Path
    ) -> None:
        """Running initialize() twice succeeds (ALTER TABLE is no-op on repeat)."""
        db = DatabaseManager(tmp_path / "migration_test.db")
        await db.initialize()  # First run — creates everything
        await db.initialize()  # Second run — ALTER TABLE should be no-op
        # Verify columns exist
        cols = await db.fetch_all("PRAGMA table_info(trades)")
        col_names = [c["name"] for c in cols]
        assert "quality_grade" in col_names
        assert "quality_score" in col_names
        await db.close()
