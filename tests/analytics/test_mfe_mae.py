"""Tests for MFE/MAE persistence and debrief export (Sprint 29.5 S6)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from argus.analytics.debrief_export import _export_trades
from argus.analytics.trade_logger import TradeLogger
from argus.db.manager import DatabaseManager
from argus.models.trading import ExitReason, OrderSide, Trade


def make_trade_with_mfe_mae(
    mfe_r: float = 1.5,
    mae_r: float = -0.5,
    mfe_price: float = 153.0,
    mae_price: float = 149.0,
) -> Trade:
    """Create a trade with MFE/MAE populated."""
    entry_time = datetime(2026, 3, 15, 10, 0, 0)
    exit_time = datetime(2026, 3, 15, 10, 30, 0)
    return Trade(
        strategy_id="orb_breakout",
        symbol="AAPL",
        side=OrderSide.BUY,
        entry_price=150.0,
        entry_time=entry_time,
        exit_price=153.0,
        exit_time=exit_time,
        shares=100,
        stop_price=148.0,
        exit_reason=ExitReason.TARGET_1,
        gross_pnl=300.0,
        commission=1.0,
        mfe_r=mfe_r,
        mae_r=mae_r,
        mfe_price=mfe_price,
        mae_price=mae_price,
    )


@pytest.mark.asyncio
async def test_mfe_mae_in_debrief_export(db: DatabaseManager, tmp_path: Path) -> None:
    """Debrief export trade dict includes mfe_r, mae_r, mfe_price, mae_price."""
    from datetime import UTC, datetime

    today_utc = datetime.now(UTC).date().isoformat()
    trade = make_trade_with_mfe_mae()
    logger = TradeLogger(db)
    await logger.log_trade(trade)

    rows = await _export_trades(db, today_utc)

    assert isinstance(rows, list)
    assert len(rows) == 1
    row = rows[0]

    assert "mfe_r" in row
    assert "mae_r" in row
    assert "mfe_price" in row
    assert "mae_price" in row
    assert row["mfe_r"] == pytest.approx(1.5)
    assert row["mae_r"] == pytest.approx(-0.5)
    assert row["mfe_price"] == pytest.approx(153.0)
    assert row["mae_price"] == pytest.approx(149.0)


@pytest.mark.asyncio
async def test_mfe_mae_null_for_legacy_trades(db: DatabaseManager) -> None:
    """Legacy trade inserted without mfe/mae columns returns None for those fields."""
    # Insert a trade row directly without mfe/mae columns — simulates a pre-S6 row
    await db.execute(
        """
        INSERT INTO trades (
            id, strategy_id, symbol, asset_class, side,
            entry_price, entry_time, exit_price, exit_time,
            shares, stop_price, target_prices, exit_reason,
            gross_pnl, commission, net_pnl, r_multiple,
            hold_duration_seconds, outcome, rationale, notes,
            quality_grade, quality_score
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            "legacy-trade-id-001",
            "orb_breakout",
            "MSFT",
            "us_stocks",
            "buy",
            200.0,
            "2025-01-10T10:00:00",
            205.0,
            "2025-01-10T10:30:00",
            50,
            198.0,
            json.dumps([205.0, 208.0]),
            "target_1",
            250.0,
            0.5,
            249.5,
            1.25,
            1800,
            "win",
            "",
            "",
            "",
            None,
        ),
    )
    await db.commit()

    logger = TradeLogger(db)
    trade = await logger.get_trade("legacy-trade-id-001")

    assert trade is not None
    assert trade.mfe_r is None
    assert trade.mae_r is None
    assert trade.mfe_price is None
    assert trade.mae_price is None
