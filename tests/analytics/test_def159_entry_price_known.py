"""Tests for DEF-159: entry_price_known flag on reconstructed trades.

Verifies:
1. Reconstruction path marks unrecoverable-entry trades correctly.
2. Performance calculator excludes unrecoverable-entry trades.
3. Normal reconstruction with recoverable entry still logs normally.
4. TradeLogger.get_todays_pnl excludes unrecoverable-entry trades.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from argus.analytics.performance import compute_metrics
from argus.analytics.trade_logger import TradeLogger
from argus.db.manager import DatabaseManager
from argus.models.trading import (
    AssetClass,
    ExitReason,
    OrderSide,
    Trade,
    TradeOutcome,
)


@pytest.fixture
async def trade_logger(tmp_path):
    """Create an in-memory trade logger with initialized schema."""
    db_path = str(tmp_path / "test.db")
    db = DatabaseManager(db_path)
    await db.initialize()
    return TradeLogger(db)


@pytest.mark.asyncio
async def test_unrecoverable_entry_trade_marked_correctly(trade_logger: TradeLogger) -> None:
    """A trade with entry_price_known=False is stored and read back correctly."""
    now = datetime.now(UTC)
    trade = Trade(
        strategy_id="reconstructed",
        symbol="DHR",
        side=OrderSide.BUY,
        entry_price=0.0,
        entry_time=now - timedelta(hours=1),
        exit_price=194.10,
        exit_time=now,
        shares=14,
        stop_price=0.0,
        target_prices=[0.0, 0.0],
        exit_reason=ExitReason.TIME_STOP,
        gross_pnl=2717.40,
        entry_price_known=False,
    )
    trade_id = await trade_logger.log_trade(trade)

    # Read it back
    stored = await trade_logger.get_trade(trade_id)
    assert stored is not None
    assert stored.entry_price_known is False
    assert stored.entry_price == 0.0
    assert stored.exit_price == 194.10


@pytest.mark.asyncio
async def test_normal_reconstruction_with_valid_entry(trade_logger: TradeLogger) -> None:
    """A reconstructed trade with a real entry price is marked entry_price_known=True."""
    now = datetime.now(UTC)
    trade = Trade(
        strategy_id="reconstructed",
        symbol="AAPL",
        side=OrderSide.BUY,
        entry_price=150.0,
        entry_time=now - timedelta(hours=1),
        exit_price=152.0,
        exit_time=now,
        shares=100,
        stop_price=148.0,
        target_prices=[154.0, 156.0],
        exit_reason=ExitReason.TIME_STOP,
        gross_pnl=200.0,
        entry_price_known=True,
    )
    trade_id = await trade_logger.log_trade(trade)

    stored = await trade_logger.get_trade(trade_id)
    assert stored is not None
    assert stored.entry_price_known is True
    assert stored.outcome == TradeOutcome.WIN


@pytest.mark.asyncio
async def test_performance_calculator_excludes_unrecoverable_entries() -> None:
    """compute_metrics filters out trades with entry_price_known=0."""
    normal_trade = {
        "exit_price": 152.0,
        "net_pnl": 200.0,
        "r_multiple": 1.5,
        "commission": 2.0,
        "hold_duration_seconds": 3600,
        "exit_time": "2026-04-20T15:00:00",
        "entry_price_known": 1,
    }
    bogus_trade = {
        "exit_price": 194.10,
        "net_pnl": 2717.40,
        "r_multiple": 0.0,
        "commission": 0.0,
        "hold_duration_seconds": 3600,
        "exit_time": "2026-04-20T15:00:00",
        "entry_price_known": 0,  # Unrecoverable entry
    }

    # With both trades — bogus should be excluded
    metrics = compute_metrics([normal_trade, bogus_trade])
    assert metrics.total_trades == 1
    assert metrics.net_pnl == 200.0
    assert metrics.wins == 1

    # Without the flag (legacy trades) — should still be included
    legacy_trade = {
        "exit_price": 155.0,
        "net_pnl": 500.0,
        "r_multiple": 2.0,
        "commission": 2.0,
        "hold_duration_seconds": 3600,
        "exit_time": "2026-04-20T15:00:00",
        # No entry_price_known key — defaults to 1 (included)
    }
    metrics_legacy = compute_metrics([legacy_trade])
    assert metrics_legacy.total_trades == 1
    assert metrics_legacy.net_pnl == 500.0


@pytest.mark.asyncio
async def test_get_todays_pnl_excludes_unrecoverable(trade_logger: TradeLogger) -> None:
    """get_todays_pnl does not include trades with entry_price_known=False.

    FIX-05 (DEF-163): ``now`` is ET-aligned so ``exit_time``'s date matches
    the ET "today" used by ``get_todays_pnl``. The prior UTC-based ``now``
    failed deterministically during the ~4h window when UTC date drifted
    one day ahead of ET date.
    """
    from zoneinfo import ZoneInfo

    now = datetime.now(UTC).astimezone(ZoneInfo("America/New_York"))

    # Log a normal trade
    normal = Trade(
        strategy_id="strat_orb_breakout",
        symbol="TSLA",
        side=OrderSide.BUY,
        entry_price=200.0,
        entry_time=now - timedelta(hours=1),
        exit_price=202.0,
        exit_time=now,
        shares=50,
        stop_price=198.0,
        target_prices=[204.0],
        exit_reason=ExitReason.TARGET_1,
        gross_pnl=100.0,
        entry_price_known=True,
    )
    await trade_logger.log_trade(normal)

    # Log a bogus reconstruction trade
    bogus = Trade(
        strategy_id="reconstructed",
        symbol="DHR",
        side=OrderSide.BUY,
        entry_price=0.0,
        entry_time=now - timedelta(hours=2),
        exit_price=194.10,
        exit_time=now,
        shares=14,
        stop_price=0.0,
        target_prices=[0.0],
        exit_reason=ExitReason.TIME_STOP,
        gross_pnl=2717.40,
        entry_price_known=False,
    )
    await trade_logger.log_trade(bogus)

    # get_todays_pnl should only include the normal trade
    pnl = await trade_logger.get_todays_pnl()
    assert pnl == pytest.approx(100.0, abs=0.01)
