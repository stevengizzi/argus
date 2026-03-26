"""Tests for Order Manager reconciliation log consolidation."""

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, MagicMock

import pytest

from argus.core.clock import Clock
from argus.core.config import BrokerSource, OrderManagerConfig
from argus.core.event_bus import EventBus
from argus.execution.order_manager import OrderManager


@pytest.fixture()
def order_manager() -> OrderManager:
    """Create an OrderManager for reconciliation testing."""
    config = OrderManagerConfig()
    event_bus = EventBus()
    broker = AsyncMock()
    clock = MagicMock(spec=Clock)
    clock.now.return_value = MagicMock(isoformat=MagicMock(return_value="2026-03-25T10:00:00"))

    om = OrderManager(
        config=config,
        event_bus=event_bus,
        broker=broker,
        clock=clock,
        broker_source=BrokerSource.SIMULATED,
    )
    return om


@pytest.mark.asyncio
async def test_reconciliation_summary_single_line(
    order_manager: OrderManager, caplog: pytest.LogCaptureFixture
) -> None:
    """Multiple mismatches produce a single consolidated WARNING."""
    # Broker reports positions that ARGUS doesn't have
    broker_positions = {"AAPL": 100.0, "TSLA": 50.0, "NVDA": 25.0, "AMD": 10.0}

    with caplog.at_level(logging.WARNING):
        discrepancies = await order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 4

    # Should be exactly one WARNING line (consolidated summary)
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_messages) == 1
    assert "4 mismatch(es)" in warning_messages[0]
    assert "ARGUS vs IBKR" in warning_messages[0]
    # First 3 symbols shown, then "..."
    assert "..." in warning_messages[0]


@pytest.mark.asyncio
async def test_reconciliation_detail_at_debug(
    order_manager: OrderManager, caplog: pytest.LogCaptureFixture
) -> None:
    """Per-symbol mismatch detail is logged at DEBUG level."""
    broker_positions = {"AAPL": 100.0, "TSLA": 50.0}

    with caplog.at_level(logging.DEBUG):
        discrepancies = await order_manager.reconcile_positions(broker_positions)

    assert len(discrepancies) == 2

    debug_messages = [r.message for r in caplog.records if r.levelno == logging.DEBUG]
    # Should have per-symbol debug lines
    aapl_debug = [m for m in debug_messages if "AAPL" in m]
    tsla_debug = [m for m in debug_messages if "TSLA" in m]
    assert len(aapl_debug) >= 1
    assert len(tsla_debug) >= 1


@pytest.mark.asyncio
async def test_reconciliation_no_warning_when_synced(
    order_manager: OrderManager, caplog: pytest.LogCaptureFixture
) -> None:
    """No WARNING emitted when positions are in sync (no mismatches)."""
    # Empty broker positions, no internal positions → synced
    with caplog.at_level(logging.WARNING):
        discrepancies = await order_manager.reconcile_positions({})

    assert len(discrepancies) == 0
    warning_messages = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warning_messages) == 0
