"""Tests for clean asyncio shutdown task cancellation (Sprint 29.5 S5).

Verifies that all background tasks are cancelled cleanly during shutdown,
eliminating 'Task was destroyed but it is pending!' warnings.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from argus.main import ArgusSystem


@pytest.mark.asyncio
async def test_shutdown_tasks_cancelled_cleanly() -> None:
    """Verify no pending tasks after shutdown cancels background tasks."""
    system = ArgusSystem.__new__(ArgusSystem)

    # Minimal state for shutdown to run without errors
    system._clock = MagicMock()
    system._clock.now.return_value = MagicMock(
        astimezone=MagicMock(return_value=MagicMock(strftime=MagicMock(return_value="2026-03-31")))
    )
    system._event_bus = None
    system._db = None
    system._trade_logger = None
    system._broker = None
    system._data_service = None
    system._scanner = None
    system._risk_manager = None
    system._order_manager = None
    system._health_monitor = None
    system._orchestrator = None
    system._api_task = None
    system._config = MagicMock()
    system._config.system.data_dir = "data"
    system._universe_manager = None
    system._strategies = {}
    system._quality_engine = None
    system._position_sizer = None
    system._catalyst_storage = None
    system._regime_history_store = None
    system._counterfactual_tracker = None
    system._counterfactual_store = None
    system._candle_store = None
    system._eval_store = None
    system._action_manager = None
    system._conversation_manager = None
    system._usage_tracker = None

    # Create real asyncio tasks that sleep forever (simulating background loops)
    async def infinite_loop() -> None:
        while True:
            await asyncio.sleep(3600)

    eval_task = asyncio.create_task(infinite_loop())
    recon_task = asyncio.create_task(infinite_loop())
    bg_task = asyncio.create_task(infinite_loop())
    cf_task = asyncio.create_task(infinite_loop())

    system._eval_check_task = eval_task
    system._reconciliation_task = recon_task
    system._bg_refresh_task = bg_task
    system._counterfactual_task = cf_task
    # _regime_task removed FIX-03 P1-A1-M10 / DEF-074 — Orchestrator._poll_loop
    # owns regime reclassification cadence.

    # Patch the debrief export import inside shutdown
    with patch(
        "argus.analytics.debrief_export.export_debrief_data",
        new_callable=AsyncMock,
        return_value=None,
    ):
        await system.shutdown()

    # All tasks should be done (cancelled)
    for task, name in [
        (eval_task, "eval_check"),
        (recon_task, "reconciliation"),
        (bg_task, "bg_refresh"),
        (cf_task, "counterfactual"),
    ]:
        assert task.done(), f"{name} task should be done after shutdown"
        assert task.cancelled(), f"{name} task should be cancelled after shutdown"
